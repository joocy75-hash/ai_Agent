"""
전략 모듈

사용 가능한 전략:
1. proven_conservative - 보수적 EMA 크로스오버 전략
2. proven_balanced - 균형적 RSI 다이버전스 전략
3. proven_aggressive - 공격적 모멘텀 브레이크아웃 전략
4. ai_role_division - AI 역할분담 전략
5. deepseek_ai - DeepSeek AI 실시간 전략
6. autonomous_30pct - AI 자율 거래 전략 (30% 마진 한도)
7. adaptive_market_regime_fighter - 적응형 시장체제 전투 전략
8. eth_autonomous_40pct - ETH AI 자율 40% 마진 전략 (NEW!)
   - ETH/USDT 전용
   - 사용자 시드의 40% 한도
   - 레버리지: 8-15배 (변동성 기반 동적 조절)
   - ATR 기반 동적 손절/익절
"""

from .dynamic_strategy_executor import DynamicStrategyExecutor
from .adaptive_market_regime_fighter import AdaptiveMarketRegimeFighter
from .eth_ai_autonomous_40pct_strategy import ETHAutonomous40PctStrategy

__all__ = [
    "DynamicStrategyExecutor",
    "AdaptiveMarketRegimeFighter",
    "ETHAutonomous40PctStrategy",
]

# 전략 코드 목록
STRATEGY_CODES = [
    "proven_conservative",
    "proven_balanced",
    "proven_aggressive",
    "ai_role_division",
    "deepseek_ai",
    "autonomous_30pct",
    "adaptive_market_regime_fighter",
    "eth_autonomous_40pct",
]
