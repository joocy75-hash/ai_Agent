from typing import Any, Dict, Optional

from .base import StrategyBase
from .eth_ai_fusion import EthAIFusionBacktestStrategy


def get_strategy(
    name: Optional[str], params: Optional[Dict[str, Any]] = None
) -> StrategyBase:
    """
    문자열로 들어온 strategy 이름과 params를 받아 실제 Strategy 인스턴스로 변환.
    - name: "eth_ai_fusion"
    - params: strategy-specific parameters
    """
    _ = name
    _ = params
    return EthAIFusionBacktestStrategy()
