from typing import Optional, Dict, Any

from .base import StrategyBase
from .simple_open_close import SimpleOpenCloseStrategy
from .rsi_strategy import RsiStrategy
from .ema_strategy import EmaStrategy
from .ai_strategies import AIRoleDivisionStrategy, ProvenAggressiveStrategy


def get_strategy(
    name: Optional[str], params: Optional[Dict[str, Any]] = None
) -> StrategyBase:
    """
    문자열로 들어온 strategy 이름과 params를 받아 실제 Strategy 인스턴스로 변환.
    - name: "openclose", "rsi", "ema" 등
    - params: strategy-specific parameters

    Available strategies:
    1. openclose (simple_openclose, simple, oc)
       - No parameters
       - Simple strategy: close > open = buy, close < open = sell

    2. rsi (rsi14)
       - length: RSI period (default 14)
       - overbought: overbought threshold (default 70)
       - oversold: oversold threshold (default 30)

    3. ema (ema_crossover)
       - fast_length: fast EMA period (default 12)
       - slow_length: slow EMA period (default 26)

    4. ai_role_division (ai_role, ai)
       - EMA 크로스오버 + RSI 필터 기반 전략
       - ema_short, ema_long, rsi_period, rsi_oversold, rsi_overbought

    5. proven_aggressive (aggressive, momentum)
       - 볼린저 밴드 + EMA 기반 공격적 전략
       - bb_period, bb_std, ema_short, ema_long
    """
    if not name:
        name = "openclose"

    normalized = name.strip().lower()
    params = params or {}

    if normalized in ("openclose", "simple_openclose", "simple", "oc"):
        return SimpleOpenCloseStrategy()

    if normalized in ("rsi", "rsi14"):
        length = int(params.get("length", 14))
        overbought = float(params.get("overbought", 70))
        oversold = float(params.get("oversold", 30))
        return RsiStrategy(length=length, overbought=overbought, oversold=oversold)

    if normalized in ("ema", "ema_crossover", "emacrossover"):
        fast_length = int(params.get("fast_length", 12))
        slow_length = int(params.get("slow_length", 26))
        return EmaStrategy(fast_length=fast_length, slow_length=slow_length)

    # AI Role Division Strategy
    if normalized in ("ai_role_division", "ai_role", "ai"):
        return AIRoleDivisionStrategy(
            ema_short=int(params.get("ema_short", 9)),
            ema_long=int(params.get("ema_long", 21)),
            rsi_period=int(params.get("rsi_period", 14)),
            rsi_oversold=float(params.get("rsi_oversold", 35)),
            rsi_overbought=float(params.get("rsi_overbought", 65)),
        )

    # Proven Aggressive Strategy
    if normalized in ("proven_aggressive", "aggressive", "momentum"):
        return ProvenAggressiveStrategy(
            bb_period=int(params.get("bb_period", 20)),
            bb_std=float(params.get("bb_std", 2.0)),
            ema_short=int(params.get("ema_short", 9)),
            ema_long=int(params.get("ema_long", 21)),
        )

    raise ValueError(f"Unknown strategy: {name}")
