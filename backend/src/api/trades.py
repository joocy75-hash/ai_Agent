"""
거래 포지션 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ..database.db import get_session
from ..database.models import Trade
from ..utils.jwt_auth import get_current_user_id

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("/positions")
async def get_trade_positions(
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    거래 포지션 목록 조회 (차트 마커용)

    Returns:
        롱/숏 진입 및 청산 포지션 목록
    """
    result = await session.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(desc(Trade.created_at))
        .limit(limit)
    )
    trades_list = result.scalars().all()

    positions = []

    for trade in trades_list:
        # 진입 포지션
        if trade.created_at:
            entry_timestamp = int(trade.created_at.timestamp() * 1000)
            positions.append(
                {
                    "timestamp": entry_timestamp,
                    "side": trade.side.lower()
                    if trade.side
                    else "long",  # buy -> long, sell -> short
                    "type": "entry",
                    "price": float(trade.entry_price) if trade.entry_price else 0,
                    "pair": trade.symbol or "BTC/USDT",
                    "amount": float(trade.qty) if trade.qty else 0,
                }
            )

        # 청산 포지션 (exit_price가 있는 경우)
        if trade.exit_price and trade.created_at:
            # 실제로는 청산 시간이 따로 있어야 하지만, 임시로 created_at + 1시간 사용
            exit_timestamp = int(trade.created_at.timestamp() * 1000) + 3600000

            # PnL 사용
            pnl_percent = float(trade.pnl_percent) if trade.pnl_percent else 0.0
            pnl_usdt = float(trade.pnl) if trade.pnl else 0.0

            positions.append(
                {
                    "timestamp": exit_timestamp,
                    "side": trade.side.lower() if trade.side else "long",
                    "type": "exit",
                    "price": float(trade.exit_price) if trade.exit_price else 0,
                    "pair": trade.symbol or "BTC/USDT",
                    "pnlPercent": pnl_percent,
                    "pnl": pnl_usdt,
                }
            )

    return {"positions": positions}


@router.get("/recent-trades")
async def get_recent_trades(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """최근 거래 내역 (간단한 형식)"""
    result = await session.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(desc(Trade.created_at))
        .limit(limit)
    )
    trades_list = result.scalars().all()

    trades = []
    for trade in trades_list:
        trades.append(
            {
                "id": trade.id,
                "timestamp": int(trade.created_at.timestamp() * 1000)
                if trade.created_at
                else 0,
                "pair": trade.symbol or "BTC/USDT",
                "side": trade.side,
                "type": "trade",
                "price": float(trade.entry_price) if trade.entry_price else 0,
                "amount": float(trade.qty) if trade.qty else 0,
                "status": "closed" if trade.exit_price else "open",
            }
        )

    return {"trades": trades}
