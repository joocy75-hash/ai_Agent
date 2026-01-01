"""
전략 로더 - 대표 전략 로드

지원하는 전략:
1. eth_ai_fusion - ETH AI/ML 융합 전략
"""

import json
import logging
import os
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# 전략 파일 경로
STRATEGIES_PATH = os.path.join(os.path.dirname(__file__), "../strategies")

# 전략 인스턴스 캐시 (user_id별로 관리)
# Issue #4: AI Rate Limit 문제 해결 - 전략 인스턴스 재사용
_strategy_cache: Dict[str, Any] = {}


def get_cached_strategy(strategy_code: str, user_id: int, params: dict) -> Any:
    """
    캐시된 전략 인스턴스 반환 또는 신규 생성

    Issue #4: AI Rate Limit 문제 해결
    - 기존: 매번 새 전략 인스턴스 생성 → AI 에이전트 캐시 초기화 → 과도한 AI 호출
    - 수정: 전략 인스턴스를 user_id별로 캐시하여 AI 에이전트 캐시 유지

    Args:
        strategy_code: 전략 코드 (eth_ai_fusion 등)
        user_id: 사용자 ID
        params: 전략 파라미터 딕셔너리

    Returns:
        캐시된 전략 인스턴스 또는 신규 생성된 인스턴스
    """
    cache_key = f"{strategy_code}:{user_id}"

    if cache_key not in _strategy_cache:
        instance = _create_strategy_instance(strategy_code, params, user_id)
        if instance is not None:
            _strategy_cache[cache_key] = instance
            logger.info(f"✅ Strategy instance created and cached: {cache_key}")
        return instance
    else:
        logger.debug(f"♻️ Reusing cached strategy: {cache_key}")
        return _strategy_cache[cache_key]


def invalidate_strategy_cache(strategy_code: str = None, user_id: int = None):
    """
    전략 캐시 무효화

    사용 시기:
    - 전략 설정 변경 시
    - 전략 중지 시
    - 사용자 로그아웃 시

    Args:
        strategy_code: 전략 코드 (None이면 모든 전략)
        user_id: 사용자 ID (None이면 모든 사용자)
    """
    global _strategy_cache

    if strategy_code and user_id:
        cache_key = f"{strategy_code}:{user_id}"
        if cache_key in _strategy_cache:
            _strategy_cache.pop(cache_key)
            logger.info(f"🗑️ Strategy cache invalidated: {cache_key}")
    elif strategy_code:
        keys_to_delete = [k for k in _strategy_cache.keys() if k.startswith(f"{strategy_code}:")]
        for key in keys_to_delete:
            _strategy_cache.pop(key)
        logger.info(f"🗑️ Strategy cache invalidated for all users: {strategy_code} ({len(keys_to_delete)} instances)")
    elif user_id:
        keys_to_delete = [k for k in _strategy_cache.keys() if k.endswith(f":{user_id}")]
        for key in keys_to_delete:
            _strategy_cache.pop(key)
        logger.info(f"🗑️ Strategy cache invalidated for user: {user_id} ({len(keys_to_delete)} instances)")
    else:
        cache_size = len(_strategy_cache)
        _strategy_cache = {}
        logger.info(f"🗑️ All strategy cache invalidated ({cache_size} instances)")


def load_strategy_class(
    strategy_code: str,
    params_json: Optional[str] = None,
    user_id: Optional[int] = None,
):
    """
    전략 코드에 따라 적절한 전략 인스턴스 반환

    Issue #4: AI Rate Limit 문제 해결 - 전략 인스턴스 캐싱
    - 기존: 매번 새 인스턴스 생성 → AI 에이전트 캐시 초기화 → 과도한 AI 호출
    - 수정: get_cached_strategy()로 전략 인스턴스 재사용

    Args:
        strategy_code: 전략 코드 (eth_ai_fusion)
        params_json: 전략 파라미터 JSON 문자열
        user_id: 사용자 ID (Issue #4: AI Rate Limiting용)

    Returns:
        전략 인스턴스 (generate_signal 메서드를 가진 객체)
    """
    params = json.loads(params_json) if params_json else {}

    # Issue #4: 전략 인스턴스 캐싱 (AI Rate Limit 문제 해결)
    if user_id is not None:
        return get_cached_strategy(strategy_code, user_id, params)
    else:
        # user_id가 없으면 캐싱하지 않음 (legacy 호환성)
        logger.warning(f"⚠️ Strategy loaded without user_id - caching disabled for {strategy_code}")
        return _create_strategy_instance_internal(strategy_code, params, user_id)


def _create_strategy_instance(strategy_code: str, params: dict, user_id: Optional[int] = None) -> Any:
    """get_cached_strategy에서 호출하는 래퍼"""
    return _create_strategy_instance_internal(strategy_code, params, user_id)


def _create_strategy_instance_internal(
    strategy_code: str,
    params: dict,
    user_id: Optional[int] = None,
):
    """
    새로운 전략 인스턴스 생성 (내부 함수)

    Args:
        strategy_code: 전략 코드
        params: 전략 파라미터
        user_id: 사용자 ID

    Returns:
        전략 인스턴스 또는 None
    """

    def _load_strategy_file(strategy_file: str) -> Optional[str]:
        """
        Issue #2.3: 전략 파일을 안전하게 로드 (FileNotFoundError 처리)

        Args:
            strategy_file: 전략 파일명

        Returns:
            전략 코드 문자열 또는 None (파일 없음)
        """
        strategy_path = os.path.join(STRATEGIES_PATH, strategy_file)
        try:
            with open(strategy_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(
                f"[Issue #2.3] Strategy file not found: {strategy_file}. "
                f"Expected path: {strategy_path}"
            )
            return None
        except PermissionError:
            logger.error(f"Permission denied reading strategy file: {strategy_path}")
            return None
        except IOError as e:
            logger.error(f"IO error reading strategy file {strategy_path}: {e}")
            return None

    try:
        normalized = (strategy_code or "eth_ai_fusion").strip()
        if not normalized:
            normalized = "eth_ai_fusion"

        # Legacy aliases 및 다양한 형태의 전략 코드 처리
        # DB에 저장된 코드 형태: "eth_ai_fusion_strategy.ETHAIFusionStrategy"
        # 또는 짧은 형태: "eth_ai_fusion"
        legacy_aliases = {
            "proven_conservative",
            "proven_balanced",
            "proven_aggressive",
            "ai_role_division",
            "deepseek_ai",
            "autonomous_30pct",
            "adaptive_market_regime_fighter",
            "eth_autonomous_40pct",
            "sol_volatility_regime_15m",
            # 전체 경로 형태도 eth_ai_fusion으로 매핑
            "eth_ai_fusion_strategy.ETHAIFusionStrategy",
            "eth_ai_fusion_strategy",
            "ETHAIFusionStrategy",
        }
        if normalized in legacy_aliases:
            normalized = "eth_ai_fusion"

        if normalized == "eth_ai_fusion":
            from ..strategies.eth_ai_fusion_strategy import ETHAIFusionStrategy
            logger.info(f"✅ Loading ETHAIFusionStrategy for user {user_id}")
            return ETHAIFusionStrategy(params, user_id=user_id)

        # 알 수 없는 전략 코드 - 경고 후 기본 전략 로드
        logger.warning(f"⚠️ Unknown strategy code '{strategy_code}', falling back to eth_ai_fusion")
        from ..strategies.eth_ai_fusion_strategy import ETHAIFusionStrategy
        return ETHAIFusionStrategy(params, user_id=user_id)

    except Exception as e:
        logger.error(f"Failed to load strategy: {e}", exc_info=True)
        return None


def generate_signal_with_strategy(
    strategy_code: Optional[str],
    current_price: float,
    candles: list,
    params_json: Optional[str] = None,
    current_position: Optional[Dict] = None,
    exchange_client=None,
    user_id: Optional[int] = None,
) -> Dict:
    """
    전략을 사용하여 시그널 생성

    Args:
        strategy_code: 전략 코드
        current_price: 현재 가격
        candles: 캔들 데이터
        params_json: 전략 파라미터 JSON
        current_position: 현재 포지션 정보
        exchange_client: Bitget REST 클라이언트 (AI 전략에 필요)
        user_id: 사용자 ID (AI Rate Limiting용)

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

    strategy = load_strategy_class(strategy_code, params_json, user_id=user_id)

    # AI 전략에 exchange client 설정 (AdaptiveRegimeFighter, Autonomous30Pct 등)
    if strategy is not None and exchange_client is not None:
        if hasattr(strategy, 'set_exchange'):
            strategy.set_exchange(exchange_client)
            logger.info(f"✅ Exchange client set for strategy: {strategy_code} (type: {type(exchange_client).__name__})")
        else:
            logger.info(f"Strategy {strategy_code} has no set_exchange method")
    elif strategy is not None and exchange_client is None:
        logger.warning(f"⚠️ exchange_client is None for strategy: {strategy_code}")

    if strategy is None:
        # 기본 전략 사용 (기존 strategy_engine)
        from ..services.strategy_engine import run as run_legacy_strategy

        safe_strategy_code = strategy_code or ""

        signal = run_legacy_strategy(
            strategy_code=safe_strategy_code,
            price=current_price,
            candles=candles,
            params_json=params_json,
            symbol="",
        )

        logger.info(
            f"Legacy strategy signal: {signal} (code: {safe_strategy_code[:50] if safe_strategy_code else 'None'})"
        )

        return {
            "action": signal,
            "confidence": 0.5,
            "reason": "Legacy strategy engine",
            "stop_loss": None,
            "take_profit": None,
            "size": 0.001,
        }

    # 새로운 전략 클래스 사용
    try:
        result = strategy.generate_signal(
            current_price=current_price,
            candles=candles,
            current_position=current_position,
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
            "size": 0,
        }
