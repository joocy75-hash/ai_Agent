"""
Chart data service - Integrates WebSocket ticks with candle generation

This service bridges the LBank WebSocket client and the candle generator,
converting real-time tick data into OHLCV candles for chart visualization.
"""

import asyncio
import logging
from typing import List, Optional

from ..websockets.ws_server import broadcast_to_all
from .candle_generator import get_candle_generator

logger = logging.getLogger(__name__)


class ChartDataService:
    """
    Manages real-time chart data flow

    Responsibilities:
    - Consume tick data from market queue
    - Generate OHLCV candles
    - Broadcast candle updates to connected frontend clients
    """

    def __init__(self, market_queue: asyncio.Queue, candle_interval: int = 60):
        """
        Args:
            market_queue: Queue receiving tick data from WebSocket
            candle_interval: Candle interval in seconds (default: 60 = 1 minute)
        """
        self.market_queue = market_queue
        self.candle_generator = get_candle_generator(candle_interval)
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

        logger.info(f"ChartDataService initialized with {candle_interval}s candles")

    async def start(self):
        """Start processing tick data"""
        if self.is_running:
            logger.warning("ChartDataService already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._process_ticks())
        logger.info("ChartDataService started")

    async def stop(self):
        """Stop processing tick data"""
        self.is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("ChartDataService stopped")

    async def _process_ticks(self):
        """Main processing loop - consume ticks and generate candles"""
        logger.info("🚀 Starting tick processing loop")

        while self.is_running:
            try:
                # Get tick data from queue (with timeout to allow graceful shutdown)
                try:
                    tick_data = await asyncio.wait_for(
                        self.market_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Extract tick information
                symbol = tick_data.get("symbol", "BTCUSDT")
                price = tick_data.get("price")
                timestamp = tick_data.get("timestamp")
                volume = tick_data.get("volume", 0.0)

                if price is None:
                    logger.warning(f"⚠️ Tick data missing price: {tick_data}")
                    continue

                logger.debug(f"📊 Processing tick: {symbol} @ ${price}")

                # Process tick and check if candle completed
                completed_candle = self.candle_generator.process_tick(
                    symbol=symbol,
                    price=float(price),
                    volume=float(volume),
                    timestamp=timestamp
                )

                if completed_candle:
                    logger.info(f"✅ Candle completed for {symbol}: {completed_candle.to_dict()}")

                # Broadcast updates to frontend
                await self._broadcast_updates(symbol, completed_candle)

            except asyncio.CancelledError:
                logger.info("Tick processing cancelled")
                break

            except Exception as e:
                logger.error(f"Error processing tick: {e}", exc_info=True)
                # Continue processing despite errors
                await asyncio.sleep(0.1)

    async def _broadcast_updates(self, symbol: str, completed_candle: Optional[dict]):
        """
        Broadcast candle updates to connected frontend clients

        Args:
            symbol: Trading pair symbol
            completed_candle: Completed candle if any (from Candle object)
        """
        try:
            # Get current candle
            current_candle = self.candle_generator.get_current_candle(symbol)

            # Prepare update message
            update = {
                "type": "candle_update",
                "symbol": symbol,
                "current_candle": current_candle
            }

            # Include completed candle if available
            if completed_candle:
                update["completed_candle"] = completed_candle.to_dict()

            # Broadcast to all connected users
            # TODO: Make this user-specific based on their active trading pairs
            await self._broadcast_to_all_users(update)

        except Exception as e:
            logger.error(f"Error broadcasting updates: {e}", exc_info=True)

    async def _broadcast_to_all_users(self, message: dict):
        """
        Broadcast message to all connected users

        Note: In production, filter by user's active symbols
        """
        try:
            # Broadcast to all connected WebSocket clients
            await broadcast_to_all(message)
            logger.info(f"📡 Broadcasted: {message.get('type')} for {message.get('symbol')} - candle: {message.get('current_candle')}")

        except Exception as e:
            logger.error(f"Broadcast error: {e}", exc_info=True)

    def get_candles(self, symbol: str, limit: int = 100,
                   include_current: bool = True) -> List[dict]:
        """
        Get candles for a symbol

        Args:
            symbol: Trading pair symbol
            limit: Maximum number of candles
            include_current: Include current incomplete candle

        Returns:
            List of candle dictionaries
        """
        return self.candle_generator.get_all_candles(symbol, limit, include_current)

    def get_status(self) -> dict:
        """Get service status"""
        return {
            "is_running": self.is_running,
            "queue_size": self.market_queue.qsize(),
            "candle_generator": self.candle_generator.get_status()
        }


# Global instance
_chart_service: Optional[ChartDataService] = None


async def get_chart_service(market_queue: Optional[asyncio.Queue] = None) -> ChartDataService:
    """
    Get or create the global chart data service

    Args:
        market_queue: Market data queue (required on first call)

    Returns:
        ChartDataService singleton
    """
    global _chart_service

    if _chart_service is None:
        if market_queue is None:
            raise ValueError("market_queue required for first initialization")

        _chart_service = ChartDataService(market_queue)
        await _chart_service.start()
        logger.info("Created and started global ChartDataService")

    return _chart_service


async def stop_chart_service():
    """Stop the global chart data service"""
    global _chart_service

    if _chart_service:
        await _chart_service.stop()
        _chart_service = None
        logger.info("Stopped global ChartDataService")
