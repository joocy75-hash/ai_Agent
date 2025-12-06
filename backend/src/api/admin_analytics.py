from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from ..database.db import get_session
from ..database.models import User, BotStatus, Trade, Equity, Position
from ..utils.auth_dependencies import require_admin
from ..utils.structured_logging import get_logger
import logging

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


@router.get("/global-summary")
async def get_global_summary(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 전체 시스템 통계 조회

    반환 데이터:
    - 전체 사용자 수, 활성 사용자 수
    - 전체 봇 수, 실행 중인 봇 수
    - 총 AUM (Asset Under Management)
    - 전체 P&L (총 수익/손실)

    Returns:
        전체 시스템 통계
    """
    try:
        # 사용자 통계
        total_users_result = await session.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0

        active_users_result = await session.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )
        active_users = active_users_result.scalar() or 0

        # 봇 통계
        total_bots_result = await session.execute(select(func.count(BotStatus.user_id)))
        total_bots = total_bots_result.scalar() or 0

        running_bots_result = await session.execute(
            select(func.count(BotStatus.user_id)).where(BotStatus.is_running == True)
        )
        running_bots = running_bots_result.scalar() or 0

        # 총 AUM (최신 equity 값의 합)
        # 각 사용자별 최신 equity를 가져와서 합산
        subquery = (
            select(
                Equity.user_id,
                func.max(Equity.timestamp).label("max_timestamp")
            )
            .group_by(Equity.user_id)
            .subquery()
        )

        aum_result = await session.execute(
            select(func.sum(Equity.value))
            .select_from(Equity)
            .join(
                subquery,
                (Equity.user_id == subquery.c.user_id) &
                (Equity.timestamp == subquery.c.max_timestamp)
            )
        )
        total_aum = float(aum_result.scalar() or 0)

        # 전체 P&L (모든 거래의 pnl 합계)
        pnl_result = await session.execute(
            select(func.sum(Trade.pnl)).where(Trade.exit_price.isnot(None))
        )
        total_pnl = float(pnl_result.scalar() or 0)

        # 총 거래 횟수
        total_trades_result = await session.execute(select(func.count(Trade.id)))
        total_trades = total_trades_result.scalar() or 0

        # 진행 중인 포지션 수
        open_positions_result = await session.execute(select(func.count(Position.id)))
        open_positions = open_positions_result.scalar() or 0

        structured_logger.info(
            "admin_global_summary_accessed",
            f"Admin {admin_id} accessed global summary",
            admin_id=admin_id,
            total_users=total_users,
            active_users=active_users,
            running_bots=running_bots
        )

        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
            },
            "bots": {
                "total": total_bots,
                "running": running_bots,
                "stopped": total_bots - running_bots,
            },
            "financials": {
                "total_aum": round(total_aum, 2),
                "total_pnl": round(total_pnl, 2),
                "total_trades": total_trades,
                "open_positions": open_positions,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        structured_logger.error(
            "admin_global_summary_error",
            "Failed to get global summary",
            admin_id=admin_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to get global summary: {str(e)}")


@router.get("/risk-users")
async def get_risk_users(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
    limit: int = 5,
):
    """
    관리자 전용: 위험 사용자 목록 조회

    반환 데이터:
    - 손실률 높은 사용자 Top N
    - 거래 횟수가 많은 사용자 (과도한 거래)

    Args:
        limit: 조회할 사용자 수 (기본값: 5)

    Returns:
        위험 사용자 목록
    """
    try:
        # 손실률 계산 (총 거래 pnl / 총 거래 진입 금액)
        # 각 사용자별 총 PnL과 거래 횟수
        user_pnl_query = (
            select(
                Trade.user_id,
                User.email,
                func.sum(Trade.pnl).label("total_pnl"),
                func.count(Trade.id).label("trade_count"),
                func.sum(Trade.entry_price * Trade.qty).label("total_volume")
            )
            .join(User, Trade.user_id == User.id)
            .where(Trade.exit_price.isnot(None))
            .group_by(Trade.user_id, User.email)
            .order_by(desc("total_pnl"))
        )

        result = await session.execute(user_pnl_query)
        user_stats = result.all()

        # 손실 사용자 (total_pnl < 0)
        loss_users = [
            {
                "user_id": user_id,
                "email": email,
                "total_pnl": float(total_pnl or 0),
                "trade_count": trade_count or 0,
                "total_volume": float(total_volume or 0),
                "loss_rate": round((float(total_pnl or 0) / float(total_volume or 1)) * 100, 2) if total_volume else 0,
                "risk_level": "HIGH" if float(total_pnl or 0) < -1000 else "MEDIUM",
            }
            for user_id, email, total_pnl, trade_count, total_volume in user_stats
            if total_pnl and total_pnl < 0
        ]

        # 손실률 기준으로 정렬
        loss_users.sort(key=lambda x: x["total_pnl"])
        top_loss_users = loss_users[:limit]

        # 과도한 거래 사용자 (거래 횟수 많은 순)
        user_stats_sorted_by_trades = sorted(
            user_stats,
            key=lambda x: x.trade_count if x.trade_count else 0,
            reverse=True
        )[:limit]

        high_frequency_users = [
            {
                "user_id": user_id,
                "email": email,
                "trade_count": trade_count or 0,
                "total_pnl": float(total_pnl or 0),
                "avg_pnl_per_trade": round(float(total_pnl or 0) / (trade_count or 1), 2),
            }
            for user_id, email, total_pnl, trade_count, total_volume in user_stats_sorted_by_trades
        ]

        structured_logger.info(
            "admin_risk_users_accessed",
            f"Admin {admin_id} accessed risk users",
            admin_id=admin_id,
            loss_users_count=len(top_loss_users),
            high_frequency_count=len(high_frequency_users)
        )

        return {
            "top_loss_users": top_loss_users,
            "high_frequency_traders": high_frequency_users,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        structured_logger.error(
            "admin_risk_users_error",
            "Failed to get risk users",
            admin_id=admin_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to get risk users: {str(e)}")


@router.get("/trading-volume")
async def get_trading_volume(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
    days: int = 7,
):
    """
    관리자 전용: 거래량 통계 조회

    반환 데이터:
    - 일별 거래량 통계
    - 거래 횟수 통계
    - 평균 거래 크기

    Args:
        days: 조회할 일수 (기본값: 7일)

    Returns:
        거래량 통계
    """
    try:
        # 기간 설정
        start_date = datetime.utcnow() - timedelta(days=days)

        # 전체 거래량 (진입 금액 기준)
        volume_result = await session.execute(
            select(func.sum(Trade.entry_price * Trade.qty))
            .where(Trade.created_at >= start_date)
        )
        total_volume = float(volume_result.scalar() or 0)

        # 전체 거래 횟수
        trade_count_result = await session.execute(
            select(func.count(Trade.id))
            .where(Trade.created_at >= start_date)
        )
        total_trades = trade_count_result.scalar() or 0

        # 평균 거래 크기
        avg_trade_size = round(total_volume / total_trades, 2) if total_trades > 0 else 0

        # 일별 거래량 (최근 N일)
        daily_volume_query = (
            select(
                func.date(Trade.created_at).label("date"),
                func.count(Trade.id).label("trade_count"),
                func.sum(Trade.entry_price * Trade.qty).label("volume"),
            )
            .where(Trade.created_at >= start_date)
            .group_by(func.date(Trade.created_at))
            .order_by(desc("date"))
        )

        daily_result = await session.execute(daily_volume_query)
        daily_stats = daily_result.all()

        daily_breakdown = [
            {
                "date": str(date),
                "trade_count": trade_count or 0,
                "volume": float(volume or 0),
            }
            for date, trade_count, volume in daily_stats
        ]

        # 심볼별 거래량 Top 5
        symbol_volume_query = (
            select(
                Trade.symbol,
                func.count(Trade.id).label("trade_count"),
                func.sum(Trade.entry_price * Trade.qty).label("volume"),
            )
            .where(Trade.created_at >= start_date)
            .group_by(Trade.symbol)
            .order_by(desc("volume"))
            .limit(5)
        )

        symbol_result = await session.execute(symbol_volume_query)
        symbol_stats = symbol_result.all()

        top_symbols = [
            {
                "symbol": symbol,
                "trade_count": trade_count or 0,
                "volume": float(volume or 0),
            }
            for symbol, trade_count, volume in symbol_stats
        ]

        structured_logger.info(
            "admin_trading_volume_accessed",
            f"Admin {admin_id} accessed trading volume stats",
            admin_id=admin_id,
            days=days,
            total_trades=total_trades
        )

        return {
            "summary": {
                "total_volume": round(total_volume, 2),
                "total_trades": total_trades,
                "avg_trade_size": avg_trade_size,
                "period_days": days,
            },
            "daily_breakdown": daily_breakdown,
            "top_symbols": top_symbols,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        structured_logger.error(
            "admin_trading_volume_error",
            "Failed to get trading volume",
            admin_id=admin_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to get trading volume: {str(e)}")
