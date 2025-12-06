from dataclasses import dataclass
from decimal import Decimal

MIN_ORDER_SIZE = 0.001


def calculate_position_size(balance: float, risk_percent: float, entry_price: float, leverage: int) -> float:
    risk_amount = balance * (risk_percent / 100)
    qty = risk_amount * leverage / entry_price
    return max(round(qty, 6), MIN_ORDER_SIZE)


def should_stop_loss(position_entry: float, current_price: float, sl_percent: float) -> bool:
    pnl = (current_price - position_entry) / position_entry * 100
    return pnl <= -abs(sl_percent)


def should_take_profit(position_entry: float, current_price: float, tp_percent: float) -> bool:
    pnl = (current_price - position_entry) / position_entry * 100
    return pnl >= abs(tp_percent)


def liquidation_check(entry_price: float, current_price: float, leverage: int) -> bool:
    diff = abs(current_price - entry_price)
    threshold = entry_price / leverage * 0.85
    return diff >= threshold
