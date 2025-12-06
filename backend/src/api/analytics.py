"""
Analytics API endpoints

성과 분석, 리스크 지표, 자산 곡선 등 분석 데이터 제공
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import Equity, Trade
from ..utils.jwt_auth import get_current_user_id
from ..utils.structured_logging import get_logger

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/equity-curve")
async def get_equity_curve(
    period: str = Query(default="1m", description="기간: 1d, 1w, 1m, 3m, 1y, all"),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    자산 곡선 데이터 가져오기

    Args:
        period: 조회 기간
        - 1d: 1일
        - 1w: 1주
        - 1m: 1개월
        - 3m: 3개월
        - 1y: 1년
        - all: 전체

    Returns:
        자산 곡선 데이터 (시간별 equity 값)
    """
    from ..utils.cache_manager import cache_manager, make_cache_key

    # 캐시 확인 (60초 TTL)
    cache_key = make_cache_key("equity_curve", user_id, period)
    cached_data = await cache_manager.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for equity_curve user {user_id} period {period}")
        return cached_data

    try:
        structured_logger.info(
            "equity_curve_requested",
            f"Equity curve requested for period {period}",
            user_id=user_id,
            period=period,
        )

        # 기간 검증
        period_map = {
            "1d": 1,
            "1w": 7,
            "1m": 30,
            "3m": 90,
            "1y": 365,
            "all": 3650,  # 10년
        }

        if period not in period_map:
            structured_logger.warning(
                "equity_curve_invalid_period",
                f"Invalid period requested: {period}",
                user_id=user_id,
                period=period,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period: {period}. Must be one of {list(period_map.keys())}",
            )

        days = period_map[period]
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Equity 데이터 조회
        result = await session.execute(
            select(Equity)
            .where(
                Equity.user_id == user_id,
                Equity.timestamp >= cutoff_date,
            )
            .order_by(Equity.timestamp.asc())
        )
        equities = result.scalars().all()

        # 데이터 포맷팅 및 검증
        data = []
        for equity in equities:
            try:
                data.append(
                    {
                        "date": equity.timestamp.strftime("%Y-%m-%d"),
                        "equity": float(equity.value)
                        if equity.value is not None
                        else 0.0,
                        "timestamp": int(equity.timestamp.timestamp()),
                    }
                )
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid equity data: {e}")
                continue

        response = {
            "period": period,
            "data": data,
            "count": len(data),
        }

        # 캐시에 저장 (60초 TTL)
        await cache_manager.set(cache_key, response, ttl=60)
        logger.debug(f"Cached equity_curve for user {user_id} period {period}")

        structured_logger.info(
            "equity_curve_fetched",
            f"Equity curve fetched: {len(data)} points",
            user_id=user_id,
            period=period,
            data_points=len(data),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(
            "equity_curve_failed",
            "Failed to fetch equity curve",
            user_id=user_id,
            period=period,
            error=str(e),
        )
        return {
            "period": period,
            "data": [],
            "count": 0,
            "error": "데이터 조회에 실패했습니다.",
        }


@router.get("/risk-metrics")
async def get_risk_metrics(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    리스크 지표 가져오기

    Returns:
        - max_drawdown: 최대 낙폭 (%)
        - sharpe_ratio: 샤프 비율
        - win_rate: 승률 (%)
        - profit_loss_ratio: 평균 손익비
        - daily_volatility: 일일 변동성 (%)
        - total_trades: 총 거래 수
    """
    from ..utils.cache_manager import cache_manager, make_cache_key

    # 캐시 확인 (30초 TTL - 리스크 지표는 자주 변경됨)
    cache_key = make_cache_key("risk_metrics", user_id)
    cached_data = await cache_manager.get(cache_key)
    if cached_data is not None:
        logger.debug(f"Cache hit for risk_metrics user {user_id}")
        return cached_data

    try:
        structured_logger.info(
            "risk_metrics_requested",
            "Risk metrics calculation requested",
            user_id=user_id,
        )
        # 거래 통계 조회
        result = await session.execute(
            select(Trade).where(
                Trade.user_id == user_id,
                Trade.exit_price.isnot(None),  # 청산된 거래만
            )
        )
        trades = result.scalars().all()

        if not trades:
            return {
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "win_rate": 0.0,
                "profit_loss_ratio": 0.0,
                "daily_volatility": 0.0,
                "total_trades": 0,
            }

        # 승리/패배 거래 분리 (Null 체크 강화)
        winning_trades = [t for t in trades if t.pnl is not None and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl is not None and t.pnl < 0]

        total_trades = len(trades)

        # 승률 계산
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0

        # 평균 손익비 계산 (ZeroDivisionError 방지)
        avg_win = 0.0
        if winning_trades:
            try:
                avg_win = sum(float(t.pnl) for t in winning_trades) / len(
                    winning_trades
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Error calculating avg_win: {e}")
                avg_win = 0.0

        avg_loss = 1.0  # 기본값 (나누기 0 방지)
        if losing_trades:
            try:
                avg_loss = abs(
                    sum(float(t.pnl) for t in losing_trades) / len(losing_trades)
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Error calculating avg_loss: {e}")
                avg_loss = 1.0

        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

        # Equity 데이터로 MDD 및 변동성 계산
        equity_result = await session.execute(
            select(Equity)
            .where(Equity.user_id == user_id)
            .order_by(Equity.timestamp.asc())
        )
        equities = equity_result.scalars().all()

        max_drawdown = 0.0
        daily_volatility = 0.0
        sharpe_ratio = 0.0

        if equities and len(equities) > 1:
            try:
                # MDD 계산 (Null 체크 강화)
                peak = (
                    float(equities[0].value) if equities[0].value is not None else 0.0
                )
                for equity in equities:
                    if equity.value is None:
                        continue

                    equity_val = float(equity.value)
                    if equity_val > peak:
                        peak = equity_val

                    if peak > 0:
                        drawdown = ((equity_val - peak) / peak) * 100
                        if drawdown < max_drawdown:
                            max_drawdown = drawdown

                # 일일 수익률 계산 (Null 및 0 체크)
                returns = []
                for i in range(1, len(equities)):
                    if equities[i].value is None or equities[i - 1].value is None:
                        continue

                    prev_equity = float(equities[i - 1].value)
                    curr_equity = float(equities[i].value)

                    if prev_equity > 0:
                        daily_return = ((curr_equity - prev_equity) / prev_equity) * 100
                        returns.append(daily_return)

                # 변동성 (표준편차)
                if returns and len(returns) > 1:
                    mean_return = sum(returns) / len(returns)
                    variance = sum((r - mean_return) ** 2 for r in returns) / len(
                        returns
                    )
                    daily_volatility = variance**0.5

                    # 샤프 비율 (간단 계산: 평균 수익률 / 변동성)
                    sharpe_ratio = (
                        mean_return / daily_volatility if daily_volatility > 0 else 0.0
                    )

            except (ValueError, TypeError, ZeroDivisionError) as e:
                logger.warning(f"Error calculating MDD/volatility: {e}")
                max_drawdown = 0.0
                daily_volatility = 0.0
                sharpe_ratio = 0.0

        response = {
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "win_rate": round(win_rate, 2),
            "profit_loss_ratio": round(profit_loss_ratio, 2),
            "daily_volatility": round(daily_volatility, 2),
            "total_trades": total_trades,
            "data_sufficient": total_trades >= 10,  # 최소 10거래 필요
        }

        # 캐시에 저장 (30초 TTL)
        await cache_manager.set(cache_key, response, ttl=30)
        logger.debug(f"Cached risk_metrics for user {user_id}")

        structured_logger.info(
            "risk_metrics_calculated",
            f"Risk metrics calculated: {total_trades} trades",
            user_id=user_id,
            total_trades=total_trades,
            win_rate=round(win_rate, 2),
        )

        return response

    except Exception as e:
        structured_logger.error(
            "risk_metrics_failed",
            "Failed to calculate risk metrics",
            user_id=user_id,
            error=str(e),
        )
        return {
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "win_rate": 0.0,
            "profit_loss_ratio": 0.0,
            "daily_volatility": 0.0,
            "total_trades": 0,
            "data_sufficient": False,
            "error": "리스크 지표 계산에 실패했습니다.",
        }


@router.get("/performance")
async def get_performance_metrics(
    period: str = Query(default="1m", description="기간: 1d, 1w, 1m, 3m, 1y, all"),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    성과 지표 가져오기

    Returns:
        - total_return: 총 수익률 (%)
        - total_pnl: 총 손익 (USDT)
        - total_trades: 총 거래 수
        - winning_trades: 승리 거래 수
        - losing_trades: 패배 거래 수
        - best_trade: 최고 수익 거래
        - worst_trade: 최악 손실 거래
    """
    from ..utils.cache_manager import cache_manager, make_cache_key

    # 캐시 확인 (60초 TTL)
    cache_key = make_cache_key("performance_metrics", user_id, period)
    cached_data = await cache_manager.get(cache_key)
    if cached_data is not None:
        logger.debug(
            f"Cache hit for performance_metrics user {user_id} period {period}"
        )
        return cached_data

    try:
        structured_logger.info(
            "performance_metrics_requested",
            f"Performance metrics requested for period {period}",
            user_id=user_id,
            period=period,
        )

        # 기간 검증
        period_map = {
            "1d": 1,
            "1w": 7,
            "1m": 30,
            "3m": 90,
            "1y": 365,
            "all": 3650,
        }

        if period not in period_map:
            structured_logger.warning(
                "performance_metrics_invalid_period",
                f"Invalid period requested: {period}",
                user_id=user_id,
                period=period,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period: {period}. Must be one of {list(period_map.keys())}",
            )

        days = period_map[period]
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # 거래 조회
        result = await session.execute(
            select(Trade).where(
                Trade.user_id == user_id,
                Trade.created_at >= cutoff_date,
                Trade.exit_price.isnot(None),
            )
        )
        trades = result.scalars().all()

        if not trades:
            response = {
                "period": period,
                "total_return": 0.0,
                "total_pnl": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "best_trade": None,
                "worst_trade": None,
            }
            # 빈 데이터도 캐시 (60초 TTL)
            await cache_manager.set(cache_key, response, ttl=60)
            return response

        # 통계 계산 (Null 체크 강화)
        total_pnl = 0.0
        try:
            total_pnl = sum(float(t.pnl) for t in trades if t.pnl is not None)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error calculating total_pnl: {e}")
            total_pnl = 0.0

        winning_trades = [t for t in trades if t.pnl is not None and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl is not None and t.pnl < 0]

        # 최고/최악 거래 (안전한 계산)
        best_trade = None
        worst_trade = None
        try:
            valid_pnl_trades = [t for t in trades if t.pnl is not None]
            if valid_pnl_trades:
                best_trade = max(valid_pnl_trades, key=lambda t: float(t.pnl))
                worst_trade = min(valid_pnl_trades, key=lambda t: float(t.pnl))
        except (ValueError, TypeError) as e:
            logger.warning(f"Error finding best/worst trades: {e}")

        # Equity로 총 수익률 계산 (Null 및 0 체크)
        equity_result = await session.execute(
            select(Equity)
            .where(
                Equity.user_id == user_id,
                Equity.timestamp >= cutoff_date,
            )
            .order_by(Equity.timestamp.asc())
        )
        equities = equity_result.scalars().all()

        total_return = 0.0
        if equities and len(equities) > 1:
            try:
                initial_equity = equities[0].value
                final_equity = equities[-1].value

                if (
                    initial_equity is not None
                    and final_equity is not None
                    and initial_equity > 0
                ):
                    total_return = (
                        (float(final_equity) - float(initial_equity))
                        / float(initial_equity)
                    ) * 100
            except (ValueError, TypeError, ZeroDivisionError) as e:
                logger.warning(f"Error calculating total_return: {e}")
                total_return = 0.0

        response = {
            "period": period,
            "total_return": round(total_return, 2),
            "total_pnl": round(total_pnl, 2),
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "best_trade": {
                "symbol": best_trade.symbol,
                "pnl": float(best_trade.pnl) if best_trade.pnl is not None else 0.0,
                "pnl_percent": float(best_trade.pnl_percent)
                if best_trade.pnl_percent is not None
                else 0.0,
            }
            if best_trade
            else None,
            "worst_trade": {
                "symbol": worst_trade.symbol,
                "pnl": float(worst_trade.pnl) if worst_trade.pnl is not None else 0.0,
                "pnl_percent": float(worst_trade.pnl_percent)
                if worst_trade.pnl_percent is not None
                else 0.0,
            }
            if worst_trade
            else None,
        }

        # 캐시에 저장 (60초 TTL)
        await cache_manager.set(cache_key, response, ttl=60)
        logger.debug(f"Cached performance_metrics for user {user_id} period {period}")

        structured_logger.info(
            "performance_metrics_calculated",
            f"Performance metrics calculated: {len(trades)} trades",
            user_id=user_id,
            period=period,
            total_trades=len(trades),
            total_pnl=round(total_pnl, 2),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error(
            "performance_metrics_failed",
            "Failed to calculate performance metrics",
            user_id=user_id,
            period=period,
            error=str(e),
        )
        return {
            "period": period,
            "total_return": 0.0,
            "total_pnl": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "best_trade": None,
            "worst_trade": None,
            "error": "성과 지표 계산에 실패했습니다.",
        }
