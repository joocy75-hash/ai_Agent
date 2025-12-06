class StrategyBase:
    """
    Base strategy interface.

    Every strategy must implement on_candle(candle: dict, position: dict|None)
    and return one of:
        - "buy"
        - "sell"
        - "hold"
    """

    def on_candle(self, candle: dict, position: dict | None) -> str:
        raise NotImplementedError("Strategy must implement on_candle()")
