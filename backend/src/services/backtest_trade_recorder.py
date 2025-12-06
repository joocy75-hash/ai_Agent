class BacktestTradeRecorder:
    """
    Trade and equity recorder for backtest engine.
    Records:
    - trades (entry/exit with fees and pnl)
    - equity curve (balance + unrealized pnl at each step)
    """

    def __init__(self):
        self.trades = []
        self.equity_curve = []

    def record_trade(self, side, direction, entry, exit, fee, pnl, timestamp):
        """
        Record a completed trade.

        Args:
            side: "exit" (always exit when recording completed trade)
            direction: "long" or "short"
            entry: entry price
            exit: exit price
            fee: total fee (entry + exit)
            pnl: profit/loss
            timestamp: timestamp of the trade
        """
        self.trades.append(
            {
                "timestamp": timestamp,
                "side": side,
                "direction": direction,
                "entry_price": entry,
                "exit_price": exit,
                "qty": 1.0,
                "fee": fee,
                "pnl": pnl,
            }
        )

    def record_equity(self, value):
        """
        Record equity value at a point in time.

        Args:
            value: equity value (balance + unrealized pnl)
        """
        self.equity_curve.append(value)
