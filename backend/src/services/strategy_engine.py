from collections import deque
import json
from typing import Any, Deque, List

from .risk_engine import calculate_position_size

BUFFER_SIZE = 200
_candle_buffers: dict[str, Deque[dict]] = {}


def _ensure_buffer(symbol: str) -> Deque[dict]:
    if symbol not in _candle_buffers:
        _candle_buffers[symbol] = deque(maxlen=BUFFER_SIZE)
    return _candle_buffers[symbol]


def _ema(values: List[float], period: int) -> float:
    if not values or len(values) < period:
        return values[-1] if values else 0.0
    k = 2 / (period + 1)
    ema = values[0]
    for price in values[1:]:
        ema = price * k + ema * (1 - k)
    return ema


def rsi_reversal(price: float, candles: list, params: dict | None = None) -> str:
    params = params or {}
    length = int(params.get("rsi_length", 14))
    closes = [c["close"] for c in candles[-length - 1 :]]
    gains = sum(max(0, closes[i + 1] - closes[i]) for i in range(len(closes) - 1))
    losses = sum(max(0, closes[i] - closes[i + 1]) for i in range(len(closes) - 1))
    if losses == 0:
        return "buy" if price > closes[-1] else "hold"
    rs = gains / losses
    rsi = 100 - (100 / (1 + rs))
    if rsi < 30:
        return "buy"
    if rsi > 70:
        return "sell"
    return "hold"


def ema_cross(price: float, candles: list, params: dict | None = None) -> str:
    params = params or {}
    fast = int(params.get("ema_fast", 9))
    slow = int(params.get("ema_slow", 21))
    closes = [c["close"] for c in candles]
    fast_ema = _ema(closes[-fast:], fast) if len(closes) >= fast else closes[-1]
    slow_ema = _ema(closes[-slow:], slow) if len(closes) >= slow else closes[-1]
    if fast_ema > slow_ema:
        return "buy"
    if fast_ema < slow_ema:
        return "sell"
    return "hold"


def breakout(price: float, candles: list, params: dict | None = None) -> str:
    params = params or {}
    lookback = int(params.get("lookback", 20))
    window = candles[-lookback:] if len(candles) >= lookback else candles
    highs = [c["high"] for c in window]
    lows = [c["low"] for c in window]
    if not highs or not lows:
        return "hold"
    if price > max(highs):
        return "buy"
    if price < min(lows):
        return "sell"
    return "hold"


def ai_signal(price: float, candles: list, params: dict | None = None) -> str:
    # placeholder
    return "buy" if price % 2 == 0 else "sell"


def run(strategy_code: str, price: float, candles: list, params_json: str | None = None, symbol: str = "") -> str:
    buffer = _ensure_buffer(symbol or "global")
    buffer.extend(candles[-BUFFER_SIZE:])

    params = json.loads(params_json) if params_json else {}
    strategy_type = params.get("type", "trend")

    if strategy_type == "rsi":
        signal = rsi_reversal(price, list(buffer), params)
    elif strategy_type == "ema":
        signal = ema_cross(price, list(buffer), params)
    elif strategy_type == "breakout":
        signal = breakout(price, list(buffer), params)
    elif strategy_type == "ai":
        signal = ai_signal(price, list(buffer), params)
    else:
        signal = "hold"

    # smoothing via simple filter
    fast = params.get("ema_fast", 3)
    slow = params.get("ema_slow", 7)
    closes = [c["close"] for c in buffer]
    fast_ema = _ema(closes[-fast:], fast) if len(closes) >= fast else price
    slow_ema = _ema(closes[-slow:], slow) if len(closes) >= slow else price
    if abs(fast_ema - slow_ema) < price * 0.001:
        return "hold"

    return signal
