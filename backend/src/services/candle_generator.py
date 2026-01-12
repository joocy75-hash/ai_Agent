"""
Real-time OHLCV candle generator from tick data

Converts real-time price ticks from LBank WebSocket into 1-minute OHLCV candles
for chart visualization.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Candle:
    """OHLCV candle data structure"""

    def __init__(self, timestamp: int, open_price: float):
        self.timestamp = timestamp  # Unix timestamp (start of minute)
        self.open = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.volume = 0.0
        self.tick_count = 0

    def update(self, price: float, volume: float = 0.0):
        """Update candle with new tick data"""
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume
        self.tick_count += 1

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "time": self.timestamp,
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": float(self.volume),
            "tick_count": self.tick_count
        }


class CandleGenerator:
    """
    Real-time candle generator

    Converts tick data into OHLCV candles with configurable intervals.
    Default is 1-minute candles for live trading visualization.
    """

    def __init__(self, interval_seconds: int = 60):
        """
        Args:
            interval_seconds: Candle interval in seconds (default: 60 = 1 minute)
        """
        self.interval_seconds = interval_seconds

        # Symbol -> current candle
        self.current_candles: Dict[str, Candle] = {}

        # Symbol -> list of completed candles (keep last 500)
        self.completed_candles: Dict[str, List[Candle]] = defaultdict(list)

        # Max candles to keep in memory per symbol
        self.max_candles = 500

        logger.info(f"CandleGenerator initialized with {interval_seconds}s interval")

    def _get_candle_timestamp(self, tick_time: float) -> int:
        """
        Get the start timestamp of the candle for given tick time

        Args:
            tick_time: Unix timestamp (can be float)

        Returns:
            Unix timestamp aligned to candle interval
        """
        # Round down to candle interval
        return int(tick_time // self.interval_seconds * self.interval_seconds)

    def process_tick(self, symbol: str, price: float, volume: float = 0.0,
                     timestamp: Optional[float] = None) -> Optional[Candle]:
        """
        Process a new price tick and update candles

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            price: Current price
            volume: Trade volume (optional)
            timestamp: Tick timestamp (unix time), uses current time if None

        Returns:
            Completed candle if a new candle started, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).timestamp()

        candle_ts = self._get_candle_timestamp(timestamp)

        # Get or create current candle for this symbol
        current_candle = self.current_candles.get(symbol)
        completed_candle = None

        # If no current candle or new candle period started
        if current_candle is None or current_candle.timestamp != candle_ts:
            # Save completed candle if it exists
            if current_candle is not None:
                self._save_completed_candle(symbol, current_candle)
                completed_candle = current_candle
                logger.debug(f"Completed candle for {symbol}: {current_candle.to_dict()}")

            # Create new candle
            current_candle = Candle(candle_ts, price)
            self.current_candles[symbol] = current_candle
            logger.debug(f"Started new candle for {symbol} at {candle_ts}")

        # Update current candle with new tick
        current_candle.update(price, volume)

        return completed_candle

    def _save_completed_candle(self, symbol: str, candle: Candle):
        """Save completed candle and maintain size limit"""
        self.completed_candles[symbol].append(candle)

        # Keep only last max_candles
        if len(self.completed_candles[symbol]) > self.max_candles:
            self.completed_candles[symbol] = self.completed_candles[symbol][-self.max_candles:]

    def get_current_candle(self, symbol: str) -> Optional[dict]:
        """Get current (incomplete) candle for a symbol"""
        candle = self.current_candles.get(symbol)
        return candle.to_dict() if candle else None

    def get_completed_candles(self, symbol: str, limit: int = 100) -> List[dict]:
        """
        Get completed candles for a symbol

        Args:
            symbol: Trading pair symbol
            limit: Maximum number of candles to return

        Returns:
            List of candle dictionaries, newest first
        """
        candles = self.completed_candles.get(symbol, [])
        return [c.to_dict() for c in candles[-limit:]]

    def get_all_candles(self, symbol: str, limit: int = 100,
                       include_current: bool = True) -> List[dict]:
        """
        Get all candles (completed + current) for a symbol

        Args:
            symbol: Trading pair symbol
            limit: Maximum number of candles to return
            include_current: Include current incomplete candle

        Returns:
            List of candle dictionaries sorted by time
        """
        result = self.get_completed_candles(symbol, limit)

        if include_current:
            current = self.get_current_candle(symbol)
            if current:
                result.append(current)

        return result

    def get_status(self) -> dict:
        """Get generator status for monitoring"""
        return {
            "interval_seconds": self.interval_seconds,
            "symbols_tracked": list(self.current_candles.keys()),
            "total_symbols": len(self.current_candles),
            "candle_counts": {
                symbol: len(candles)
                for symbol, candles in self.completed_candles.items()
            }
        }


# Global singleton instance
_candle_generator: Optional[CandleGenerator] = None


def get_candle_generator(interval_seconds: int = 60) -> CandleGenerator:
    """
    Get or create the global candle generator instance

    Args:
        interval_seconds: Candle interval (only used on first call)

    Returns:
        CandleGenerator singleton instance
    """
    global _candle_generator

    if _candle_generator is None:
        _candle_generator = CandleGenerator(interval_seconds)
        logger.info("Created global CandleGenerator instance")

    return _candle_generator
