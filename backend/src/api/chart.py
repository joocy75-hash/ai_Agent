"""
Chart data API endpoints

Provides real-time OHLCV candle data and position markers for chart visualization.
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import Position, Trade
from ..services.candle_generator import get_candle_generator
from ..utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chart", tags=["chart"])


@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    limit: int = Query(default=100, ge=1, le=500),
    include_current: bool = Query(default=True),
    timeframe: str = Query(
        default="1m", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"
    ),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get OHLCV candles for a trading pair

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        limit: Number of candles to return (1-500)
        include_current: Include current incomplete candle
        timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)

    Returns:
        List of candle data with OHLCV values
    """
    try:
        candles = []

        # Only use candle generator for 1m timeframe (real-time updates)
        if timeframe == "1m":
            candle_gen = get_candle_generator()
            candles = candle_gen.get_all_candles(
                symbol=symbol.upper(), limit=limit, include_current=include_current
            )

        # If no candles from generator or different timeframe, fetch from Bitget API
        if not candles or len(candles) < min(50, limit):
            logger.info(f"Fetching {timeframe} candles from Bitget API for {symbol}")
            import ccxt.async_support as ccxt

            try:
                # Use public API without authentication
                exchange = ccxt.bitget(
                    {"enableRateLimit": True, "options": {"defaultType": "swap"}}
                )

                # Convert symbol format: BTCUSDT -> BTC/USDT:USDT
                if symbol.upper().endswith("USDT"):
                    base = symbol.upper().replace("USDT", "")
                    bitget_symbol = f"{base}/USDT:USDT"
                else:
                    bitget_symbol = symbol

                # Fetch candles from Bitget
                ohlcv = await exchange.fetch_ohlcv(
                    bitget_symbol, timeframe=timeframe, limit=limit
                )

                await exchange.close()

                if ohlcv:
                    candles = []
                    for candle in ohlcv:
                        # CCXT format: [timestamp, open, high, low, close, volume]
                        candles.append(
                            {
                                "time": int(candle[0] / 1000),  # ms to seconds
                                "open": float(candle[1]),
                                "high": float(candle[2]),
                                "low": float(candle[3]),
                                "close": float(candle[4]),
                                "volume": float(candle[5]) if len(candle) > 5 else 0.0,
                                "tick_count": 1,
                            }
                        )

                    logger.info(
                        f"Fetched {len(candles)} {timeframe} candles from Bitget for {symbol}"
                    )

            except Exception as e:
                logger.warning(f"Bitget API failed: {e}")

        # If still no candles, return error
        if not candles:
            logger.warning(f"No candle data available for {symbol}")
            raise HTTPException(
                status_code=503,
                detail=f"No market data available for {symbol}. Please ensure market data service is running.",
            )

        # Timeframe을 밀리초로 변환
        timeframe_ms_map = {
            "1m": 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000,
        }
        timeframe_ms = timeframe_ms_map.get(timeframe, 60 * 1000)

        return {
            "symbol": symbol.upper(),
            "interval": timeframe,
            "timeframe_ms": timeframe_ms,
            "candles": candles,
            "count": len(candles),
        }

    except Exception as e:
        logger.error(f"Error fetching candles for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/positions/{symbol}")
async def get_position_markers(
    symbol: str,
    days_back: int = Query(default=7, ge=1, le=30),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get position entry/exit markers for chart overlay

    Returns trade history for the specified symbol to display on chart.
    Each trade includes entry/exit prices and timestamps for marker placement.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        days_back: Number of days of history to fetch (1-30)

    Returns:
        List of position events with:
        - timestamp: Unix timestamp
        - type: "entry" or "exit"
        - side: "long" or "short"
        - price: Entry/exit price
        - pnl: P&L for exit events
        - pnl_percent: P&L percentage for exit events
    """
    try:
        # Calculate time range
        cutoff_time = datetime.utcnow() - timedelta(days=days_back)

        # Query closed trades
        result = await session.execute(
            select(Trade)
            .where(
                and_(
                    Trade.user_id == user_id,
                    Trade.symbol == symbol.upper(),
                    Trade.created_at >= cutoff_time,
                    Trade.exit_price.isnot(None),  # Only closed trades
                )
            )
            .order_by(Trade.created_at.asc())
        )
        trades = result.scalars().all()

        # Convert trades to position markers
        markers = []

        for trade in trades:
            # Entry marker
            markers.append(
                {
                    "timestamp": int(trade.created_at.timestamp()),
                    "type": "entry",
                    "side": trade.side.lower(),
                    "price": float(trade.entry_price),
                    "qty": float(trade.qty),
                    "trade_id": trade.id,
                    "enter_tag": trade.enter_tag if trade.enter_tag else None,
                    "order_tag": trade.order_tag if trade.order_tag else None,
                }
            )

            # Exit marker
            if trade.exit_price:
                markers.append(
                    {
                        "timestamp": int(
                            trade.created_at.timestamp()
                        ),  # Approximate exit time
                        "type": "exit",
                        "side": trade.side.lower(),
                        "price": float(trade.exit_price),
                        "qty": float(trade.qty),
                        "pnl": float(trade.pnl) if trade.pnl else 0.0,
                        "pnl_percent": float(trade.pnl_percent)
                        if trade.pnl_percent
                        else 0.0,
                        "exit_reason": trade.exit_reason.value
                        if trade.exit_reason
                        else "manual",
                        "exit_tag": trade.exit_tag if trade.exit_tag else None,
                        "trade_id": trade.id,
                    }
                )

        # Sort by timestamp
        markers.sort(key=lambda x: x["timestamp"])

        return {
            "symbol": symbol.upper(),
            "markers": markers,
            "count": len(markers),
            "days_back": days_back,
        }

    except Exception as e:
        logger.error(
            f"Error fetching position markers for {symbol}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/positions/current/{symbol}")
async def get_current_positions(
    symbol: str,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get current open positions for a symbol

    Returns active positions to display on chart as reference lines.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")

    Returns:
        List of open positions with entry price and current P&L
    """
    try:
        # Query open positions
        result = await session.execute(
            select(Position).where(
                and_(Position.user_id == user_id, Position.symbol == symbol.upper())
            )
        )
        positions = result.scalars().all()

        # Format positions for chart display
        position_data = []
        for pos in positions:
            position_data.append(
                {
                    "id": pos.id,
                    "side": pos.side.lower(),
                    "entry_price": float(pos.entry_price),
                    "size": float(pos.size),
                    "pnl": float(pos.pnl) if pos.pnl else 0.0,
                    "updated_at": int(pos.updated_at.timestamp()),
                }
            )

        return {
            "symbol": symbol.upper(),
            "positions": position_data,
            "count": len(position_data),
        }

    except Exception as e:
        logger.error(
            f"Error fetching current positions for {symbol}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status")
async def get_chart_status(
    user_id: int = Depends(get_current_user_id),
):
    """
    Get chart data service status

    Returns:
        Service status including candle generator statistics
    """
    try:
        candle_gen = get_candle_generator()
        status = candle_gen.get_status()

        return {
            "status": "operational",
            "candle_generator": status,
            "timestamp": int(datetime.utcnow().timestamp()),
        }

    except Exception as e:
        logger.error(f"Error getting chart status: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": int(datetime.utcnow().timestamp()),
        }
