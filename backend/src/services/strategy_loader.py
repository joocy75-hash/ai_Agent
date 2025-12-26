"""
전략 로더 - 대표 전략 로드

지원하는 전략:
1. proven_conservative - 보수적 EMA 크로스오버 전략
2. proven_balanced - 균형적 RSI 다이버전스 전략
3. proven_aggressive - 공격적 모멘텀 브레이크아웃 전략
4. ai_role_division - AI 역할분담 전략 (빠른 진입 + 스마트 대응)
5. autonomous_30pct - AI 자율 거래 전략 (30% 마진 한도)
6. deepseek_ai - DeepSeek AI 실시간 투자 판단 전략
7. adaptive_market_regime_fighter - 적응형 시장체제 전투 전략
   - Bull: Aggressive Momentum-Following
   - Bear: Controlled Short-Selling/Range Fade
   - Sideways: Mean Reversion/Oscillator Trading
   - High Volatility: Breakout Confirmation/Defensive Mode
8. eth_autonomous_40pct - ETH AI 자율 40% 마진 전략
   - ETH 전용 최적화
   - 사용자 시드의 40% 한도 (예: 1000 USDT → 400 USDT)
   - 레버리지: 8-15배 (변동성 기반 동적 조절)
   - ATR 기반 동적 손절/익절
   - 24시간 자율 운영
9. sol_volatility_regime_15m - SOL 변동성 레짐 15분 전략 (NEW!)
   - SOL 전용 15분 타임프레임
   - 4가지 변동성 레짐: COMPRESSION, EXPANSION, HIGH_VOL, EXHAUSTION
   - VCP (Volatility Contraction Pattern) 브레이크아웃 감지
   - 다단계 익절: TP1(1.5x ATR, 30%), TP2(2.5x ATR, 40%), TP3(4x ATR, 30%)
   - 35% 마진 한도 (SOL 변동성 고려)
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
        strategy_code: 전략 코드 (eth_autonomous_40pct 등)
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
        strategy_code: 전략 코드 (proven_conservative, proven_balanced, proven_aggressive)
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
        # 1. 보수적 EMA 크로스오버 전략
        if strategy_code == "proven_conservative":
            logger.info("Loading Proven Conservative Strategy (EMA Crossover + Volume)")
            strategy_code_str = _load_strategy_file("proven_conservative_strategy.py")
            if strategy_code_str is None:
                logger.warning("Falling back to None for proven_conservative strategy")
                return None
            from ..strategies.dynamic_strategy_executor import DynamicStrategyExecutor

            return DynamicStrategyExecutor(strategy_code_str, params)

        # 2. 균형적 RSI 다이버전스 전략
        elif strategy_code == "proven_balanced":
            logger.info("Loading Proven Balanced Strategy (RSI Divergence)")
            strategy_code_str = _load_strategy_file("proven_balanced_strategy.py")
            if strategy_code_str is None:
                logger.warning("Falling back to None for proven_balanced strategy")
                return None
            from ..strategies.dynamic_strategy_executor import DynamicStrategyExecutor

            return DynamicStrategyExecutor(strategy_code_str, params)

        # 3. 공격적 모멘텀 브레이크아웃 전략
        elif strategy_code == "proven_aggressive":
            logger.info("Loading Proven Aggressive Strategy (Momentum Breakout)")
            strategy_code_str = _load_strategy_file("proven_aggressive_strategy.py")
            if strategy_code_str is None:
                logger.warning("Falling back to None for proven_aggressive strategy")
                return None
            from ..strategies.dynamic_strategy_executor import DynamicStrategyExecutor

            return DynamicStrategyExecutor(strategy_code_str, params)

        # 4. AI 역할분담 전략 (빠른 진입 + 스마트 대응)
        elif strategy_code == "ai_role_division":
            logger.info("Loading AI Role Division Strategy (Fast Entry + Smart Management)")
            from ..strategies.ai_role_division_strategy import generate_signal

            class AIRoleDivisionStrategy:
                def __init__(self, params):
                    self.params = params

                def generate_signal(self, current_price, candles, current_position=None):
                    return generate_signal(candles, self.params, current_position)

            return AIRoleDivisionStrategy(params)

        # 5. DeepSeek AI 실시간 투자 판단 전략 (NEW!)
        elif strategy_code == "deepseek_ai":
            logger.info("🤖 Loading DeepSeek AI Strategy (Real-time AI Trading)")
            from ..services.deepseek_service import deepseek_service

            class DeepSeekAIStrategy:
                def __init__(self, params, user_id=None):
                    self.params = params
                    self.symbol = params.get("symbol", "BTCUSDT")
                    self.call_count = 0
                    self.user_id = user_id  # Issue #4: For Rate Limiting
                    self.last_signal = None
                    # API 비용 절약: N번에 1번만 AI 호출 (기본 5번마다)
                    self.ai_call_interval = params.get("ai_call_interval", 5)

                def generate_signal(self, current_price, candles, current_position=None):
                    self.call_count += 1

                    # AI 호출 간격 체크 (API 비용 절약)
                    if self.call_count % self.ai_call_interval != 0 and self.last_signal:
                        # 이전 시그널 재사용 (hold로 변경)
                        return {
                            **self.last_signal,
                            "action": "hold",
                            "reason": f"AI 대기 중 ({self.call_count % self.ai_call_interval}/{self.ai_call_interval})",
                        }

                    # DeepSeek AI 호출
                    try:
                        signal = deepseek_service.get_trading_signal(
                            symbol=self.symbol,
                            current_price=current_price,
                            candles=candles,
                            current_position=current_position,
                            strategy_params=self.params,
                            user_id=self.user_id,  # Issue #4: Rate Limiting
                        )
                        self.last_signal = signal
                        logger.info(f"🤖 DeepSeek AI Signal: {signal.get('action')} (confidence: {signal.get('confidence')}, reason: {signal.get('reason')})")
                        return signal
                    except Exception as e:
                        logger.error(f"DeepSeek AI error: {e}")
                        return {
                            "action": "hold",
                            "confidence": 0.0,
                            "reason": f"AI 오류: {str(e)}",
                            "stop_loss": None,
                            "take_profit": None,
                            "ai_powered": True,
                        }

            return DeepSeekAIStrategy(params, user_id=user_id)

        # 6. AI 자율 거래 전략 (30% 마진 한도)
        elif strategy_code == "autonomous_30pct":
            logger.info("🤖 Loading Autonomous 30% Margin Strategy (Full AI Autonomy)")
            from ..strategies.autonomous_30pct_strategy import Autonomous30PctStrategy

            class Autonomous30PctWrapper:
                """
                Autonomous30PctStrategy를 기존 인터페이스에 맞게 래핑
                """
                def __init__(self, params, user_id=None):
                    self.params = params
                    self.user_id = user_id
                    self.symbol = params.get("symbol", "BTCUSDT")
                    self.strategy = Autonomous30PctStrategy({
                        "symbol": self.symbol,
                        "timeframe": params.get("timeframe", "1h"),
                        "enable_ai": params.get("enable_ai", True),
                        "base_leverage": params.get("base_leverage", 10),
                        "max_leverage": params.get("max_leverage", 20),
                    })
                    self._exchange = None
                    self._last_decision = None

                def set_exchange(self, exchange):
                    """거래소 클라이언트 설정 (BotRunner에서 호출)"""
                    self._exchange = exchange

                def generate_signal(self, current_price, candles, current_position=None):
                    """
                    기존 인터페이스와 호환되는 시그널 생성

                    Note: 이 전략은 비동기 analyze_and_decide() 메서드를 사용하므로,
                    BotRunner에서 직접 호출하는 것이 권장됩니다.
                    여기서는 동기 래퍼를 제공합니다.
                    """
                    import asyncio

                    if self._exchange is None:
                        logger.warning("Exchange client not set for Autonomous30Pct strategy")
                        return {
                            "action": "hold",
                            "confidence": 0.0,
                            "reason": "Exchange client not configured",
                            "stop_loss": None,
                            "take_profit": None,
                            "ai_powered": True,
                            "strategy_type": "autonomous_30pct"
                        }

                    # 비동기 함수를 동기적으로 실행
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # 이미 이벤트 루프가 실행 중이면 태스크 생성
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    asyncio.run,
                                    self._async_generate_signal(current_price, candles, current_position)
                                )
                                return future.result(timeout=30)
                        else:
                            return loop.run_until_complete(
                                self._async_generate_signal(current_price, candles, current_position)
                            )
                    except Exception as e:
                        logger.error(f"Autonomous30Pct signal error: {e}")
                        return {
                            "action": "hold",
                            "confidence": 0.0,
                            "reason": f"Error: {str(e)}",
                            "stop_loss": None,
                            "take_profit": None,
                            "ai_powered": True,
                            "strategy_type": "autonomous_30pct"
                        }

                async def _async_generate_signal(self, current_price, candles, current_position):
                    """비동기 시그널 생성"""
                    from ..strategies.autonomous_30pct_strategy import PositionInfo
                    from datetime import datetime, timedelta

                    # 현재 포지션 변환
                    positions = []
                    if current_position and current_position.get("size", 0) > 0:
                        positions.append(PositionInfo(
                            symbol=self.symbol,
                            side=current_position.get("side", "long"),
                            size=current_position.get("size", 0),
                            entry_price=current_position.get("entry_price", current_price),
                            current_price=current_price,
                            unrealized_pnl=current_position.get("pnl", 0),
                            unrealized_pnl_percent=current_position.get("pnl_percent", 0),
                            leverage=current_position.get("leverage", 10),
                            margin_used=current_position.get("margin", 0),
                            liquidation_price=current_position.get("liquidation_price", 0),
                            holding_duration=timedelta(minutes=current_position.get("holding_minutes", 0)),
                            entry_time=datetime.now() - timedelta(minutes=current_position.get("holding_minutes", 0))
                        ))

                    # AI 자율 결정
                    decision = await self.strategy.analyze_and_decide(
                        exchange=self._exchange,
                        user_id=self.user_id or 1,
                        current_positions=positions
                    )

                    self._last_decision = decision

                    # 결정을 기존 시그널 형식으로 변환
                    action_map = {
                        "enter_long": "buy",
                        "enter_short": "sell",
                        "exit_long": "close",
                        "exit_short": "close",
                        "emergency_exit": "close",
                        "hold": "hold",
                        "increase_position": "buy",
                        "decrease_position": "close"
                    }

                    return {
                        "action": action_map.get(decision.decision.value, "hold"),
                        "confidence": decision.confidence,
                        "reason": decision.reasoning,
                        "stop_loss": decision.stop_loss_percent,
                        "take_profit": decision.take_profit_percent,
                        "leverage": decision.target_leverage,
                        "position_size_percent": decision.position_size_percent,
                        "market_regime": decision.market_regime,
                        "ai_powered": decision.ai_enhanced,
                        "strategy_type": "autonomous_30pct",
                        "warnings": decision.warnings
                    }

                def get_statistics(self):
                    """전략 통계 반환"""
                    return self.strategy.get_statistics()

            return Autonomous30PctWrapper(params, user_id=user_id)

        # 7. Adaptive Market Regime Fighter Strategy (NEW!)
        elif strategy_code == "adaptive_market_regime_fighter":
            logger.info("🎯 Loading Adaptive Market Regime Fighter Strategy")
            from ..strategies.adaptive_market_regime_fighter import AdaptiveMarketRegimeFighter

            class AdaptiveRegimeFighterWrapper:
                """
                AdaptiveMarketRegimeFighter를 기존 인터페이스에 맞게 래핑
                """
                def __init__(self, params, user_id=None):
                    self.params = params
                    self.user_id = user_id
                    self.symbol = params.get("symbol", "BTCUSDT")
                    self.strategy = AdaptiveMarketRegimeFighter({
                        "symbol": self.symbol,
                        "timeframe": params.get("timeframe", "1h"),
                        "enable_ai": params.get("enable_ai", True),
                        "base_leverage": params.get("base_leverage", 10),
                        "max_leverage": params.get("max_leverage", 15),
                    })
                    self._exchange = None

                def set_exchange(self, exchange):
                    """거래소 클라이언트 설정 (BotRunner에서 호출)"""
                    self._exchange = exchange
                    self.strategy.set_exchange(exchange)

                def set_ai_service(self, ai_service):
                    """AI 서비스 설정"""
                    self.strategy.set_ai_service(ai_service)

                def generate_signal(self, current_price, candles, current_position=None):
                    """
                    기존 인터페이스와 호환되는 시그널 생성
                    """
                    import asyncio

                    if self._exchange is None:
                        logger.warning("Exchange client not set for AdaptiveRegimeFighter strategy")
                        return {
                            "action": "hold",
                            "confidence": 0.0,
                            "reason": "Exchange client not configured",
                            "stop_loss": None,
                            "take_profit": None,
                            "ai_powered": True,
                            "strategy_type": "adaptive_market_regime_fighter"
                        }

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    asyncio.run,
                                    self._async_generate_signal(current_price, candles, current_position)
                                )
                                return future.result(timeout=30)
                        else:
                            return loop.run_until_complete(
                                self._async_generate_signal(current_price, candles, current_position)
                            )
                    except Exception as e:
                        logger.error(f"AdaptiveRegimeFighter signal error: {e}")
                        return {
                            "action": "hold",
                            "confidence": 0.0,
                            "reason": f"Error: {str(e)}",
                            "stop_loss": None,
                            "take_profit": None,
                            "ai_powered": True,
                            "strategy_type": "adaptive_market_regime_fighter"
                        }

                async def _async_generate_signal(self, current_price, candles, current_position):
                    """비동기 시그널 생성"""
                    positions = []
                    if current_position and current_position.get("size", 0) > 0:
                        positions.append(current_position)

                    return await self.strategy.analyze_and_decide(
                        exchange=self._exchange,
                        user_id=self.user_id or 1,
                        current_positions=positions
                    )

                def update_protection_mode(self, trade_result):
                    """거래 결과에 따른 보호 모드 업데이트"""
                    self.strategy.update_protection_mode(trade_result)

                def get_statistics(self):
                    """전략 통계 반환"""
                    return self.strategy.get_statistics()

            return AdaptiveRegimeFighterWrapper(params, user_id=user_id)

        # 8. ETH AI 자율 40% 마진 전략 (NEW!)
        elif strategy_code == "eth_autonomous_40pct":
            logger.info("🚀 Loading ETH AI Autonomous 40% Margin Strategy")
            from ..strategies.eth_ai_autonomous_40pct_strategy import (
                ETHAutonomous40PctStrategy,
                PositionInfo as ETHPositionInfo
            )

            class ETHAutonomous40PctWrapper:
                """
                ETHAutonomous40PctStrategy를 기존 인터페이스에 맞게 래핑

                특징:
                - ETH/USDT 전용
                - 사용자 시드의 40% 한도
                - 8-15배 동적 레버리지
                - ATR 기반 동적 SL/TP
                """
                def __init__(self, params, user_id=None):
                    self.params = params
                    self.user_id = user_id
                    self.strategy = ETHAutonomous40PctStrategy({
                        "enable_ai": params.get("enable_ai", True),
                        "timeframe": params.get("timeframe", "1h"),
                    })
                    self._exchange = None

                def set_exchange(self, exchange):
                    """거래소 클라이언트 설정 (BotRunner에서 호출)"""
                    self._exchange = exchange

                def generate_signal(self, current_price, candles, current_position=None):
                    """
                    기존 인터페이스와 호환되는 시그널 생성
                    """
                    import asyncio

                    if self._exchange is None:
                        logger.warning("Exchange client not set for ETH Autonomous 40% strategy")
                        return {
                            "action": "hold",
                            "confidence": 0.0,
                            "reason": "Exchange client not configured",
                            "stop_loss": None,
                            "take_profit": None,
                            "ai_powered": True,
                            "strategy_type": "eth_autonomous_40pct"
                        }

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    asyncio.run,
                                    self._async_generate_signal(current_price, candles, current_position)
                                )
                                return future.result(timeout=30)
                        else:
                            return loop.run_until_complete(
                                self._async_generate_signal(current_price, candles, current_position)
                            )
                    except Exception as e:
                        logger.error(f"ETH Autonomous 40% signal error: {e}")
                        return {
                            "action": "hold",
                            "confidence": 0.0,
                            "reason": f"Error: {str(e)}",
                            "stop_loss": None,
                            "take_profit": None,
                            "ai_powered": True,
                            "strategy_type": "eth_autonomous_40pct"
                        }

                async def _async_generate_signal(self, current_price, candles, current_position):
                    """비동기 시그널 생성"""
                    from datetime import datetime, timedelta

                    # 현재 포지션 변환
                    positions = []
                    if current_position and current_position.get("size", 0) > 0:
                        positions.append(ETHPositionInfo(
                            symbol="ETH/USDT",
                            side=current_position.get("side", "long"),
                            size=current_position.get("size", 0),
                            entry_price=current_position.get("entry_price", current_price),
                            current_price=current_price,
                            unrealized_pnl=current_position.get("pnl", 0),
                            unrealized_pnl_percent=current_position.get("pnl_percent", 0),
                            leverage=current_position.get("leverage", 10),
                            margin_used=current_position.get("margin", 0),
                            liquidation_price=current_position.get("liquidation_price", 0),
                            entry_time=datetime.now() - timedelta(minutes=current_position.get("holding_minutes", 0))
                        ))

                    # AI 자율 결정
                    decision = await self.strategy.analyze_and_decide(
                        exchange=self._exchange,
                        user_id=self.user_id or 1,
                        current_positions=positions
                    )

                    # 결정을 기존 시그널 형식으로 변환
                    action_map = {
                        "enter_long": "buy",
                        "enter_short": "sell",
                        "exit_long": "close",
                        "exit_short": "close",
                        "emergency_exit": "close",
                        "hold": "hold",
                        "increase_position": "buy",
                        "decrease_position": "close"
                    }

                    return {
                        "action": action_map.get(decision.decision.value, "hold"),
                        "confidence": decision.confidence,
                        "reason": decision.reasoning,
                        "stop_loss": decision.stop_loss_percent,
                        "take_profit": decision.take_profit_percent,
                        "leverage": decision.target_leverage,
                        "position_size_percent": decision.position_size_percent,
                        "market_regime": decision.market_analysis.regime_type.value if decision.market_analysis else "unknown",
                        "ai_powered": decision.ai_enhanced,
                        "strategy_type": "eth_autonomous_40pct",
                        "warnings": decision.warnings
                    }

                def update_trade_result(self, trade_result):
                    """거래 결과에 따른 상태 업데이트"""
                    self.strategy.update_trade_result(self.user_id or 1, trade_result)

                def get_statistics(self):
                    """전략 통계 반환"""
                    return self.strategy.get_statistics()

                def get_user_statistics(self):
                    """사용자별 통계 반환"""
                    return self.strategy.get_user_statistics(self.user_id or 1)

            return ETHAutonomous40PctWrapper(params, user_id=user_id)

        # 9. SOL Volatility Regime 15m Strategy (NEW!)
        elif strategy_code == "sol_volatility_regime_15m":
            logger.info("🚀 Loading SOL Volatility Regime 15m Strategy")
            from ..strategies.sol_volatility_regime_15m_strategy import (
                SOLVolatilityRegime15mStrategy,
                PositionInfo as SOLPositionInfo
            )

            class SOLVolatilityRegime15mWrapper:
                """
                SOLVolatilityRegime15mStrategy를 기존 인터페이스에 맞게 래핑

                특징:
                - SOL/USDT 전용 15분 타임프레임
                - 4가지 변동성 레짐 기반 거래
                - VCP 브레이크아웃 감지
                - 다단계 익절 (TP1, TP2, TP3)
                - 35% 마진 한도
                """
                def __init__(self, params, user_id=None):
                    self.params = params
                    self.user_id = user_id
                    self.strategy = SOLVolatilityRegime15mStrategy({
                        "enable_ai": params.get("enable_ai", True),
                        "timeframe": params.get("timeframe", "15m"),
                    })
                    self._exchange = None

                def set_exchange(self, exchange):
                    """거래소 클라이언트 설정 (BotRunner에서 호출)"""
                    self._exchange = exchange

                def generate_signal(self, current_price, candles, current_position=None):
                    """
                    기존 인터페이스와 호환되는 시그널 생성
                    """
                    import asyncio

                    if self._exchange is None:
                        logger.warning("Exchange client not set for SOL Volatility Regime 15m strategy")
                        return {
                            "action": "hold",
                            "confidence": 0.0,
                            "reason": "Exchange client not configured",
                            "stop_loss": None,
                            "take_profit": None,
                            "ai_powered": True,
                            "strategy_type": "sol_volatility_regime_15m"
                        }

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    asyncio.run,
                                    self._async_generate_signal(current_price, candles, current_position)
                                )
                                return future.result(timeout=30)
                        else:
                            return loop.run_until_complete(
                                self._async_generate_signal(current_price, candles, current_position)
                            )
                    except Exception as e:
                        logger.error(f"SOL Volatility Regime 15m signal error: {e}")
                        return {
                            "action": "hold",
                            "confidence": 0.0,
                            "reason": f"Error: {str(e)}",
                            "stop_loss": None,
                            "take_profit": None,
                            "ai_powered": True,
                            "strategy_type": "sol_volatility_regime_15m"
                        }

                async def _async_generate_signal(self, current_price, candles, current_position):
                    """비동기 시그널 생성"""
                    from datetime import datetime, timedelta

                    # 현재 포지션 변환
                    positions = []
                    if current_position and current_position.get("size", 0) > 0:
                        positions.append(SOLPositionInfo(
                            symbol="SOL/USDT",
                            side=current_position.get("side", "long"),
                            size=current_position.get("size", 0),
                            entry_price=current_position.get("entry_price", current_price),
                            current_price=current_price,
                            unrealized_pnl=current_position.get("pnl", 0),
                            unrealized_pnl_percent=current_position.get("pnl_percent", 0),
                            leverage=current_position.get("leverage", 10),
                            margin_used=current_position.get("margin", 0),
                            liquidation_price=current_position.get("liquidation_price", 0),
                            entry_time=datetime.now() - timedelta(minutes=current_position.get("holding_minutes", 0))
                        ))

                    # AI 자율 결정
                    decision = await self.strategy.analyze_and_decide(
                        exchange=self._exchange,
                        user_id=self.user_id or 1,
                        current_positions=positions
                    )

                    # 결정을 기존 시그널 형식으로 변환
                    action_map = {
                        "enter_long": "buy",
                        "enter_short": "sell",
                        "exit_long": "close",
                        "exit_short": "close",
                        "partial_exit": "partial_close",
                        "emergency_exit": "close",
                        "hold": "hold"
                    }

                    return {
                        "action": action_map.get(decision.decision.value, "hold"),
                        "confidence": decision.confidence,
                        "reason": decision.reasoning,
                        "stop_loss": decision.stop_loss_percent,
                        "take_profit": decision.take_profit_percent,
                        "tp1": decision.tp1_percent,
                        "tp2": decision.tp2_percent,
                        "tp3": decision.tp3_percent,
                        "leverage": decision.target_leverage,
                        "position_size_percent": decision.position_size_percent,
                        "market_regime": decision.market_analysis.regime_type.value if decision.market_analysis else "unknown",
                        "volatility_regime": decision.market_analysis.volatility_regime.value if decision.market_analysis else "unknown",
                        "ai_powered": decision.ai_enhanced,
                        "strategy_type": "sol_volatility_regime_15m",
                        "warnings": decision.warnings
                    }

                def update_trade_result(self, trade_result):
                    """거래 결과에 따른 상태 업데이트"""
                    self.strategy.update_trade_result(self.user_id or 1, trade_result)

                def get_statistics(self):
                    """전략 통계 반환"""
                    return self.strategy.get_statistics()

            return SOLVolatilityRegime15mWrapper(params, user_id=user_id)

        # 10. 동적 전략 코드 처리 - 보안상 비활성화
        # SECURITY: exec()를 사용한 임의 코드 실행은 심각한 보안 취약점입니다.
        # 사용자 커스텀 전략은 반드시 사전 정의된 전략 파일로 등록해야 합니다.
        elif strategy_code and len(strategy_code.strip()) > 100:
            logger.warning(
                f"[SECURITY] Dynamic strategy code execution is DISABLED for security reasons. "
                f"Code length: {len(strategy_code)}. "
                f"Please register custom strategies as pre-defined strategy files."
            )
            # 임의 코드 실행 차단 - 기본 전략으로 폴백
            return None

        # 5. 기타 - 기본 전략 엔진 사용
        else:
            code_preview = strategy_code[:100] if strategy_code else "None"
            logger.info(
                f"Using legacy strategy engine, code length: {len(strategy_code) if strategy_code else 0}, preview: {code_preview}"
            )
            return None

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
