from .base import StrategyBase


class RsiStrategy(StrategyBase):
    """
    간단한 RSI 기반 전략.

    - length: RSI 기간 (기본 14)
    - overbought: 과매수 기준 (기본 70)
    - oversold: 과매도 기준 (기본 30)

    로직:
    - 포지션이 없을 때:
        RSI < oversold  → buy (long 진입)
        RSI > overbought → sell (short 진입)
    - 포지션이 있을 때:
        long 인데 RSI > 50 → sell (청산)
        short 인데 RSI < 50 → buy (청산)
    """

    def __init__(self, length: int = 14, overbought: float = 70.0, oversold: float = 30.0):
        self.length = length
        self.overbought = overbought
        self.oversold = oversold

        self.closes: list[float] = []
        self.avg_gain: float | None = None
        self.avg_loss: float | None = None

    def _update_rsi(self, close: float) -> float | None:
        self.closes.append(close)

        if len(self.closes) < 2:
            return None

        change = self.closes[-1] - self.closes[-2]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        if self.avg_gain is None or self.avg_loss is None:
            if len(self.closes) <= self.length:
                return None

            gains = []
            losses = []
            for i in range(len(self.closes) - self.length, len(self.closes)):
                if i <= 0:
                    continue
                diff = self.closes[i] - self.closes[i - 1]
                gains.append(max(diff, 0.0))
                losses.append(max(-diff, 0.0))

            self.avg_gain = sum(gains) / len(gains) if gains else 0.0
            self.avg_loss = sum(losses) / len(losses) if losses else 0.0
        else:
            self.avg_gain = (self.avg_gain * (self.length - 1) + gain) / self.length
            self.avg_loss = (self.avg_loss * (self.length - 1) + loss) / self.length

        if self.avg_loss == 0:
            return 100.0

        rs = self.avg_gain / self.avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi

    def on_candle(self, candle: dict, position: dict | None) -> str:
        close = candle["close"]
        rsi = self._update_rsi(close)

        if rsi is None:
            return "hold"

        if position is None:
            if rsi < self.oversold:
                return "buy"
            if rsi > self.overbought:
                return "sell"
            return "hold"

        if position["direction"] == "long":
            if rsi > 50.0:
                return "sell"
        elif position["direction"] == "short":
            if rsi < 50.0:
                return "buy"

        return "hold"
