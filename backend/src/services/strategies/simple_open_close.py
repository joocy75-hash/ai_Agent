from .base import StrategyBase


class SimpleOpenCloseStrategy(StrategyBase):
    """
    Basic strategy:
        close > open = buy
        close < open = sell
        else = hold
    """

    def on_candle(self, candle: dict, position: dict | None) -> str:
        o = candle["open"]
        c = candle["close"]

        if c > o:
            return "buy"
        elif c < o:
            return "sell"
        return "hold"
