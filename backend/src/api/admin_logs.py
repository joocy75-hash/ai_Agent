from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database.db import get_session
from ..database.models import BotLog, Trade, User
from ..utils.auth_dependencies import require_admin
from ..utils.structured_logging import get_logger
import logging

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

router = APIRouter(prefix="/admin/logs", tags=["admin-logs"])


@router.get("/system")
async def get_system_logs(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
    level: Optional[str] = Query(None, description="Log level filter: CRITICAL, ERROR, WARNING, INFO"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
):
    """
    관리자 전용: 시스템 로그 조회

    시스템 로그 필터링:
    - 레벨별 필터 (CRITICAL, ERROR, WARNING, INFO)
    - 최신순 정렬
    - BotLog 테이블에서 시스템 관련 로그 조회

    Args:
        level: 로그 레벨 필터 (선택)
        limit: 조회할 최대 로그 수 (기본값: 100)

    Returns:
        시스템 로그 목록
    """
    try:
        # BotLog 테이블에서 시스템 로그 조회
        # event_type에 'error', 'warning', 'critical', 'system' 등이 포함된 로그
        query = select(BotLog).where(
            or_(
                BotLog.event_type.like('%error%'),
                BotLog.event_type.like('%warning%'),
                BotLog.event_type.like('%critical%'),
                BotLog.event_type.like('%system%'),
            )
        )

        # 레벨 필터 적용
        if level:
            level_lower = level.lower()
            query = query.where(BotLog.event_type.like(f'%{level_lower}%'))

        # 최신순 정렬 및 limit 적용
        query = query.order_by(desc(BotLog.created_at)).limit(limit)

        result = await session.execute(query)
        logs = result.scalars().all()

        # 사용자 정보 함께 조회
        log_list = []
        for log in logs:
            user_result = await session.execute(
                select(User.email).where(User.id == log.user_id)
            )
            user_email = user_result.scalar()

            log_list.append({
                "id": log.id,
                "user_id": log.user_id,
                "user_email": user_email,
                "event_type": log.event_type,
                "message": log.message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })

        structured_logger.info(
            "admin_system_logs_accessed",
            f"Admin {admin_id} accessed system logs",
            admin_id=admin_id,
            level_filter=level,
            log_count=len(log_list)
        )

        return {
            "logs": log_list,
            "total_count": len(log_list),
            "level_filter": level,
            "limit": limit,
        }

    except Exception as e:
        structured_logger.error(
            "admin_system_logs_error",
            "Failed to get system logs",
            admin_id=admin_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to get system logs: {str(e)}")


@router.get("/bot")
async def get_bot_logs(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
):
    """
    관리자 전용: 봇 로그 조회

    봇 로그 필터링:
    - 사용자별 필터 (선택)
    - 최신순 정렬
    - BotLog 테이블에서 봇 관련 로그 조회

    Args:
        user_id: 사용자 ID 필터 (선택)
        limit: 조회할 최대 로그 수 (기본값: 100)

    Returns:
        봇 로그 목록
    """
    try:
        # BotLog 테이블에서 봇 로그 조회
        # event_type에 'bot', 'start', 'stop', 'trade' 등이 포함된 로그
        query = select(BotLog).where(
            or_(
                BotLog.event_type.like('%bot%'),
                BotLog.event_type.like('%start%'),
                BotLog.event_type.like('%stop%'),
                BotLog.event_type.like('%trade%'),
                BotLog.event_type.like('%signal%'),
            )
        )

        # 사용자 필터 적용
        if user_id:
            query = query.where(BotLog.user_id == user_id)

        # 최신순 정렬 및 limit 적용
        query = query.order_by(desc(BotLog.created_at)).limit(limit)

        result = await session.execute(query)
        logs = result.scalars().all()

        # 사용자 정보 함께 조회
        log_list = []
        for log in logs:
            user_result = await session.execute(
                select(User.email).where(User.id == log.user_id)
            )
            user_email = user_result.scalar()

            log_list.append({
                "id": log.id,
                "user_id": log.user_id,
                "user_email": user_email,
                "event_type": log.event_type,
                "message": log.message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })

        structured_logger.info(
            "admin_bot_logs_accessed",
            f"Admin {admin_id} accessed bot logs",
            admin_id=admin_id,
            user_id_filter=user_id,
            log_count=len(log_list)
        )

        return {
            "logs": log_list,
            "total_count": len(log_list),
            "user_id_filter": user_id,
            "limit": limit,
        }

    except Exception as e:
        structured_logger.error(
            "admin_bot_logs_error",
            "Failed to get bot logs",
            admin_id=admin_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to get bot logs: {str(e)}")


@router.get("/trading")
async def get_trading_logs(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTCUSDT)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
):
    """
    관리자 전용: 거래 로그 조회

    거래 로그 필터링:
    - 사용자별 필터 (선택)
    - 심볼별 필터 (선택)
    - 최신순 정렬
    - Trade 테이블에서 최근 거래 내역 조회

    Args:
        user_id: 사용자 ID 필터 (선택)
        symbol: 심볼 필터 (선택)
        limit: 조회할 최대 로그 수 (기본값: 100)

    Returns:
        거래 로그 목록
    """
    try:
        # Trade 테이블에서 거래 로그 조회
        query = select(Trade)

        # 사용자 필터 적용
        if user_id:
            query = query.where(Trade.user_id == user_id)

        # 심볼 필터 적용
        if symbol:
            query = query.where(Trade.symbol == symbol.upper())

        # 최신순 정렬 및 limit 적용
        query = query.order_by(desc(Trade.created_at)).limit(limit)

        result = await session.execute(query)
        trades = result.scalars().all()

        # 사용자 정보 함께 조회
        trade_list = []
        for trade in trades:
            user_result = await session.execute(
                select(User.email).where(User.id == trade.user_id)
            )
            user_email = user_result.scalar()

            trade_list.append({
                "id": trade.id,
                "user_id": trade.user_id,
                "user_email": user_email,
                "symbol": trade.symbol,
                "side": trade.side,
                "qty": trade.qty,
                "entry_price": float(trade.entry_price) if trade.entry_price else None,
                "exit_price": float(trade.exit_price) if trade.exit_price else None,
                "pnl": float(trade.pnl) if trade.pnl else 0.0,
                "pnl_percent": trade.pnl_percent,
                "leverage": trade.leverage,
                "exit_reason": trade.exit_reason.value if trade.exit_reason else None,
                "created_at": trade.created_at.isoformat() if trade.created_at else None,
            })

        structured_logger.info(
            "admin_trading_logs_accessed",
            f"Admin {admin_id} accessed trading logs",
            admin_id=admin_id,
            user_id_filter=user_id,
            symbol_filter=symbol,
            log_count=len(trade_list)
        )

        return {
            "trades": trade_list,
            "total_count": len(trade_list),
            "user_id_filter": user_id,
            "symbol_filter": symbol,
            "limit": limit,
        }

    except Exception as e:
        structured_logger.error(
            "admin_trading_logs_error",
            "Failed to get trading logs",
            admin_id=admin_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to get trading logs: {str(e)}")
