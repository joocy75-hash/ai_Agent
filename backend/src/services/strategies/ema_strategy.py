from .base import StrategyBase


class EmaStrategy(StrategyBase):
    """
    EMA (Exponential Moving Average) Crossover Strategy.

    Uses two EMAs (fast and slow) to generate signals:
    - fast_length: Short-term EMA period (default 12)
    - slow_length: Long-term EMA period (default 26)

    Logic:
    - No position:
        Fast EMA crosses above Slow EMA → buy (long)
        Fast EMA crosses below Slow EMA → sell (short)
    - Has position:
        Long position and Fast EMA crosses below Slow EMA → sell (exit)
        Short position and Fast EMA crosses above Slow EMA → buy (exit)
    """

    def __init__(self, fast_length: int = 12, slow_length: int = 26):
        if fast_length >= slow_length:
            raise ValueError("fast_length must be less than slow_length")

        self.fast_length = fast_length
        self.slow_length = slow_length

        self.closes: list[float] = []
        self.fast_ema: float | None = None
        self.slow_ema: float | None = None
        self.prev_fast_ema: float | None = None
        self.prev_slow_ema: float | None = None

        # EMA multiplier: 2 / (period + 1)
        self.fast_multiplier = 2.0 / (fast_length + 1)
        self.slow_multiplier = 2.0 / (slow_length + 1)

    def _update_ema(self, close: float) -> tuple[float | None, float | None]:
        """
        Update both EMAs and return (fast_ema, slow_ema).
        Returns (None, None) if not enough data yet.
        """
        self.closes.append(close)

        # Need at least slow_length data points to start
        if len(self.closes) < self.slow_length:
            return None, None

        # Initialize EMAs with SMA on first calculation
        if self.fast_ema is None or self.slow_ema is None:
            # Fast EMA initialization
            fast_sma = sum(self.closes[-self.fast_length:]) / self.fast_length
            self.fast_ema = fast_sma

            # Slow EMA initialization
            slow_sma = sum(self.closes[-self.slow_length:]) / self.slow_length
            self.slow_ema = slow_sma
        else:
            # Update EMAs: EMA = (Close - EMA_prev) * multiplier + EMA_prev
            self.prev_fast_ema = self.fast_ema
            self.prev_slow_ema = self.slow_ema

            self.fast_ema = (close - self.fast_ema) * self.fast_multiplier + self.fast_ema
            self.slow_ema = (close - self.slow_ema) * self.slow_multiplier + self.slow_ema

        return self.fast_ema, self.slow_ema

    def _check_crossover(self) -> str | None:
        """
        Check if there's a crossover between fast and slow EMAs.
        Returns:
            'bullish' if fast crosses above slow (golden cross)
            'bearish' if fast crosses below slow (death cross)
            None if no crossover
        """
        if (self.prev_fast_ema is None or self.prev_slow_ema is None or
            self.fast_ema is None or self.slow_ema is None):
            return None

        # Bullish crossover (golden cross)
        if self.prev_fast_ema <= self.prev_slow_ema and self.fast_ema > self.slow_ema:
            return 'bullish'

        # Bearish crossover (death cross)
        if self.prev_fast_ema >= self.prev_slow_ema and self.fast_ema < self.slow_ema:
            return 'bearish'

        return None

    def on_candle(self, candle: dict, position: dict | None) -> str:
        """
        Process a candle and return trading signal.

        Args:
            candle: dict with 'close' price
            position: current position or None

        Returns:
            'buy', 'sell', or 'hold'
        """
        close = candle["close"]
        fast_ema, slow_ema = self._update_ema(close)

        # Not enough data yet
        if fast_ema is None or slow_ema is None:
            return "hold"

        crossover = self._check_crossover()

        # No position - enter on crossover
        if position is None:
            if crossover == 'bullish':
                return "buy"  # Enter long
            elif crossover == 'bearish':
                return "sell"  # Enter short
            return "hold"

        # Has position - exit on opposite crossover
        if position["direction"] == "long":
            if crossover == 'bearish':
                return "sell"  # Exit long
        elif position["direction"] == "short":
            if crossover == 'bullish':
                return "buy"  # Exit short

        return "hold"
