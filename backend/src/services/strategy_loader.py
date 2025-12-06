"""
전략 로더 - 다양한 전략을 동적으로 로드

전략 코드에 따라 적절한 전략 클래스를 반환
"""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def load_strategy_class(strategy_code: str, params_json: Optional[str] = None):
    """
    전략 코드에 따라 적절한 전략 인스턴스 반환

    Args:
        strategy_code: 전략 코드 ("safe_test_ai_strategy", "aggressive_test_strategy" 등)
        params_json: 전략 파라미터 JSON 문자열

    Returns:
        전략 인스턴스 (generate_signal 메서드를 가진 객체)
    """

    params = json.loads(params_json) if params_json else {}

    try:
        if strategy_code == "safe_test_ai_strategy":
            from ..strategies.test_live_strategy import create_test_strategy
            return create_test_strategy(params)

        elif strategy_code == "aggressive_test_strategy":
            from ..strategies.aggressive_test_strategy import create_aggressive_strategy
            return create_aggressive_strategy(params)

        elif strategy_code == "ma_cross":
            from ..strategies.ma_cross_strategy import create_ma_cross_strategy
            return create_ma_cross_strategy(params)

        elif strategy_code == "ultra_aggressive":
            from ..strategies.ultra_aggressive_strategy import create_ultra_aggressive_strategy
            return create_ultra_aggressive_strategy(params)

        elif strategy_code == "rsi_strategy":
            # RSI 전략 - params에 "type": "rsi" 추가하여 legacy engine 사용
            logger.info(f"Using legacy strategy engine for RSI strategy")
            return None

        else:
            # 기본 전략 (기존 strategy_engine 사용)
            logger.warning(f"Unknown strategy code: {strategy_code}, using default strategy engine")
            return None

    except Exception as e:
        logger.error(f"Failed to load strategy {strategy_code}: {e}", exc_info=True)
        return None


def generate_signal_with_strategy(
    strategy_code: str,
    current_price: float,
    candles: list,
    params_json: Optional[str] = None,
    current_position: Optional[Dict] = None
) -> Dict:
    """
    전략을 사용하여 시그널 생성

    Returns:
        {
            "action": "buy" | "sell" | "hold" | "close",
            "confidence": 0.0 ~ 1.0,
            "reason": str,
            "stop_loss": float,
            "take_profit": float,
            "size": float
        }
    """

    strategy = load_strategy_class(strategy_code, params_json)

    if strategy is None:
        # 기본 전략 사용 (기존 strategy_engine)
        from ..services.strategy_engine import run as run_legacy_strategy

        signal = run_legacy_strategy(
            strategy_code=strategy_code,
            price=current_price,
            candles=candles,
            params_json=params_json,
            symbol=""
        )

        # 레거시 응답 형식 변환
        return {
            "action": signal,
            "confidence": 0.5,
            "reason": "Legacy strategy engine",
            "stop_loss": None,
            "take_profit": None,
            "size": 0.001
        }

    # 새로운 전략 클래스 사용
    try:
        # 전략 종류에 따라 다른 시그니처 사용
        if strategy_code == "ultra_aggressive":
            # Ultra Aggressive는 candles만 받음
            result = strategy.generate_signal(
                candles=candles,
                current_position=current_position
            )
        else:
            # 다른 전략들은 current_price도 받음
            result = strategy.generate_signal(
                current_price=current_price,
                candles=candles,
                current_position=current_position
            )
        return result

    except Exception as e:
        logger.error(f"Strategy signal generation error: {e}", exc_info=True)
        return {
            "action": "hold",
            "confidence": 0.0,
            "reason": f"Error: {str(e)}",
            "stop_loss": None,
            "take_profit": None,
            "size": 0
        }
