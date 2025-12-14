"""
Signal Validator Agent (시그널 검증 에이전트)

전략 시그널을 검증하여 거래 허용 여부 결정
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional

from ..base import BaseAgent, AgentTask
from .models import SignalValidation, ValidationResult, ValidationRule
from .rules import ValidationRules

logger = logging.getLogger(__name__)


class SignalValidatorAgent(BaseAgent):
    """
    시그널 검증 에이전트

    주요 기능:
    1. 시그널 검증 (다중 규칙 체크)
    2. Market Regime Agent의 Redis 상태 읽기
    3. 신뢰도 점수 계산 및 포지션 조정
    4. 승인/거부/경고 판단
    5. 검증 결과 로깅

    작업 타입:
    - validate_signal: 시그널 검증
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        config: dict = None,
        redis_client=None
    ):
        super().__init__(agent_id, name, config)
        self.rules_engine = ValidationRules()
        self._validation_rules = self._init_rules()
        self.redis_client = redis_client

    def _init_rules(self) -> List[ValidationRule]:
        """검증 규칙 초기화"""
        return [
            ValidationRule(
                rule_id="signal_confidence",
                name="Signal Confidence",
                description="시그널 신뢰도 체크 (< 0.6 거부, < 0.7 포지션 50% 축소)",
                weight=1.5,
                is_critical=True  # 필수 규칙
            ),
            ValidationRule(
                rule_id="market_regime_alignment",
                name="Market Regime Alignment",
                description="시장 환경 체크 (volatile/low_volume 거부)",
                weight=1.5,
                is_critical=True  # 필수 규칙
            ),
            ValidationRule(
                rule_id="sudden_price_change",
                name="Sudden Price Change Filter",
                description="급등락 필터 (5분 내 2% 이상 변동 거부)",
                weight=1.2,
                is_critical=True  # 필수 규칙
            ),
            ValidationRule(
                rule_id="position_reversal",
                name="Position Reversal Check",
                description="포지션 반전 검증 (반대 포지션 + confidence < 0.8 거부)",
                weight=1.3,
                is_critical=True  # 필수 규칙
            ),
            ValidationRule(
                rule_id="consecutive_signals",
                name="Consecutive Signal Filter",
                description="연속 신호 필터 (같은 방향 3회 연속 시 거부)",
                weight=1.0,
                is_critical=False
            ),
            ValidationRule(
                rule_id="balance_limit",
                name="Balance Limit Check",
                description="잔고 검증 (주문 크기 > 잔고 30% 시 축소)",
                weight=1.2,
                is_critical=False
            ),
            ValidationRule(
                rule_id="volatility_threshold",
                name="Volatility Threshold",
                description="변동성 임계값 체크",
                weight=0.8,
                is_critical=False
            ),
            ValidationRule(
                rule_id="support_resistance",
                name="Support/Resistance Check",
                description="지지/저항선 근처 시그널 체크",
                weight=0.8,
                is_critical=False
            ),
            ValidationRule(
                rule_id="trend_strength",
                name="Trend Strength",
                description="추세 강도 체크",
                weight=0.8,
                is_critical=False
            ),
            ValidationRule(
                rule_id="trade_frequency",
                name="Trade Frequency",
                description="거래 빈도 체크 (과매매 방지)",
                weight=0.8,
                is_critical=False
            ),
            ValidationRule(
                rule_id="drawdown_limit",
                name="Drawdown Limit",
                description="최대 낙폭 한도 체크",
                weight=1.2,
                is_critical=False
            ),
        ]

    async def process_task(self, task: AgentTask) -> Any:
        """
        작업 처리 (1초 타임아웃)

        Args:
            task: 처리할 작업

        Returns:
            검증 결과
        """
        task_type = task.task_type
        params = task.params

        logger.debug(
            f"SignalValidatorAgent processing task: {task_type}"
        )

        # 타임아웃 설정 (1초)
        try:
            if task_type == "validate_signal":
                result = await asyncio.wait_for(
                    self._validate_signal(params),
                    timeout=1.0
                )
                return result
            else:
                raise ValueError(f"Unknown task type: {task_type}")

        except asyncio.TimeoutError:
            logger.error(f"Task {task.task_id} timed out after 1 second (FAIL-SAFE: REJECT)")
            # 실패 시 안전하게 거부
            return SignalValidation(
                signal_id=params.get("signal_id", "unknown"),
                symbol=params.get("symbol", "BTCUSDT"),
                action=params.get("action", "hold"),
                validation_result=ValidationResult.REJECTED,
                confidence_score=0.0,
                failed_rules=["timeout"],
                warnings=["Validation timeout - signal rejected for safety"]
            )

    async def _validate_signal(self, params: dict) -> SignalValidation:
        """
        시그널 검증

        Args:
            params: {
                "signal_id": str,
                "symbol": str,
                "action": str,  # buy/sell/close
                "confidence": float,
                "current_price": float,
                "price_change_5min": float,  # 5분간 가격 변동률 (%)
                "current_position_side": str,  # long/short/None
                "recent_signals": list,  # 최근 신호 목록
                "order_size_usd": float,  # 주문 금액
                "available_balance": float,  # 가용 잔고
                "support_level": float,
                "resistance_level": float,
                "recent_trades_count": int,
                "current_drawdown": float
            }

        Returns:
            SignalValidation 객체
        """
        signal_id = params.get("signal_id", "unknown")
        symbol = params.get("symbol", "BTCUSDT")
        action = params.get("action", "hold")
        confidence = params.get("confidence", 0.0)
        current_price = params.get("current_price", 0.0)

        # 새로운 파라미터들
        price_change_5min = params.get("price_change_5min", 0.0)
        current_position_side = params.get("current_position_side")
        recent_signals = params.get("recent_signals", [])
        order_size_usd = params.get("order_size_usd", 0.0)
        available_balance = params.get("available_balance", 0.0)

        # 기존 파라미터들
        support_level = params.get("support_level")
        resistance_level = params.get("resistance_level")
        recent_trades = params.get("recent_trades_count", 0)
        current_drawdown = params.get("current_drawdown", 0.0)

        # Redis에서 Market Regime 읽기
        market_regime = await self._get_market_regime_from_redis(symbol)

        # 검증 결과 저장
        passed_rules = []
        failed_rules = []
        warnings = []
        rule_scores = []

        # 포지션 조정 비율 (기본 100%)
        position_adjustment = 1.0
        order_size_adjustment = order_size_usd

        # 각 규칙 실행
        for rule in self._validation_rules:
            try:
                result = self._execute_rule(
                    rule=rule,
                    action=action,
                    confidence=confidence,
                    market_regime=market_regime,
                    current_price=current_price,
                    price_change_5min=price_change_5min,
                    current_position_side=current_position_side,
                    recent_signals=recent_signals,
                    order_size_usd=order_size_usd,
                    available_balance=available_balance,
                    support_level=support_level,
                    resistance_level=resistance_level,
                    recent_trades=recent_trades,
                    current_drawdown=current_drawdown
                )

                # 규칙 실행 결과 처리 (일부 규칙은 추가 데이터 반환)
                if len(result) == 2:
                    passed, message = result
                    adjustment = None
                elif len(result) == 3:
                    passed, message, adjustment = result
                else:
                    passed, message, adjustment = result[0], result[1], None

                if passed:
                    passed_rules.append(rule.rule_id)
                    rule_scores.append(rule.weight)
                    logger.debug(f"✅ {rule.name}: {message}")

                    # 포지션 조정 비율 업데이트
                    if adjustment is not None and adjustment < position_adjustment:
                        position_adjustment = adjustment
                        if rule.rule_id == "signal_confidence":
                            warnings.append(f"Position reduced to {adjustment*100:.0f}% due to low confidence")
                        elif rule.rule_id == "balance_limit":
                            order_size_adjustment = adjustment
                            warnings.append(f"Order size adjusted to ${adjustment:.2f}")

                else:
                    failed_rules.append(rule.rule_id)
                    logger.warning(f"❌ {rule.name}: {message}")

                    # 필수 규칙 실패 시 즉시 거부
                    if rule.is_critical:
                        warnings.append(f"CRITICAL: {message}")
                    else:
                        warnings.append(message)

            except Exception as e:
                logger.error(f"Error executing rule {rule.rule_id}: {e}", exc_info=True)
                failed_rules.append(rule.rule_id)
                warnings.append(f"Rule execution error: {rule.name}")

        # 신뢰도 점수 계산
        total_weight = sum(r.weight for r in self._validation_rules)
        confidence_score = sum(rule_scores) / total_weight if total_weight > 0 else 0.0

        # 검증 결과 결정
        validation_result = self._determine_result(
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            confidence_score=confidence_score
        )

        # SignalValidation 객체 생성
        validation = SignalValidation(
            signal_id=signal_id,
            symbol=symbol,
            action=action,
            validation_result=validation_result,
            confidence_score=confidence_score,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            warnings=warnings,
            metadata={
                "market_regime": market_regime.get("regime_type"),
                "volatility": market_regime.get("volatility"),
                "trend_strength": market_regime.get("trend_strength"),
                "position_adjustment": position_adjustment,
                "order_size_adjustment": order_size_adjustment,
                "original_order_size": order_size_usd,
            }
        )

        logger.info(
            f"✅ Signal validation: {signal_id} -> {validation_result.value} "
            f"(score: {confidence_score:.2f}, position: {position_adjustment*100:.0f}%, "
            f"passed: {len(passed_rules)}, failed: {len(failed_rules)})"
        )

        return validation

    def _execute_rule(
        self,
        rule: ValidationRule,
        action: str,
        confidence: float,
        market_regime: dict,
        current_price: float,
        price_change_5min: float,
        current_position_side: Optional[str],
        recent_signals: List[str],
        order_size_usd: float,
        available_balance: float,
        support_level: float,
        resistance_level: float,
        recent_trades: int,
        current_drawdown: float
    ):
        """규칙 실행 (반환값: (bool, str) 또는 (bool, str, float))"""
        rule_id = rule.rule_id

        # 새로운 규칙들 (우선 순위 높음)
        if rule_id == "signal_confidence":
            return self.rules_engine.check_signal_confidence(confidence)

        elif rule_id == "market_regime_alignment":
            return self.rules_engine.check_market_regime_alignment(action, market_regime)

        elif rule_id == "sudden_price_change":
            return self.rules_engine.check_sudden_price_change(price_change_5min)

        elif rule_id == "position_reversal":
            return self.rules_engine.check_position_reversal(
                action, current_position_side, confidence
            )

        elif rule_id == "consecutive_signals":
            return self.rules_engine.check_consecutive_signals(action, recent_signals)

        elif rule_id == "balance_limit":
            return self.rules_engine.check_balance_limit(order_size_usd, available_balance)

        # 기존 규칙들
        elif rule_id == "volatility_threshold":
            volatility = market_regime.get("volatility", 0.0)
            return self.rules_engine.check_volatility_threshold(volatility)

        elif rule_id == "support_resistance":
            return self.rules_engine.check_price_near_support_resistance(
                current_price, support_level, resistance_level, action
            )

        elif rule_id == "trend_strength":
            trend_strength = market_regime.get("trend_strength", 0.0)
            return self.rules_engine.check_trend_strength(trend_strength, action)

        elif rule_id == "trade_frequency":
            return self.rules_engine.check_recent_trade_frequency(recent_trades)

        elif rule_id == "drawdown_limit":
            return self.rules_engine.check_drawdown_limit(current_drawdown)

        else:
            return True, f"Unknown rule: {rule_id}"

    def _determine_result(
        self,
        passed_rules: List[str],
        failed_rules: List[str],
        confidence_score: float
    ) -> ValidationResult:
        """검증 결과 결정"""
        # 필수 규칙 중 하나라도 실패하면 거부
        critical_rules = {r.rule_id for r in self._validation_rules if r.is_critical}
        failed_critical = set(failed_rules) & critical_rules

        if failed_critical:
            return ValidationResult.REJECTED

        # 신뢰도 점수 기반 판단
        if confidence_score >= 0.8:
            return ValidationResult.APPROVED
        elif confidence_score >= 0.6:
            return ValidationResult.WARNING  # 조건부 승인
        else:
            return ValidationResult.REJECTED

    async def _get_market_regime_from_redis(self, symbol: str) -> dict:
        """
        Redis에서 Market Regime 데이터 읽기

        Args:
            symbol: 심볼 (예: BTCUSDT)

        Returns:
            Market Regime 딕셔너리 (없으면 기본값)
        """
        if not self.redis_client:
            logger.warning("Redis client not available, using default market regime")
            return {
                "regime_type": "unknown",
                "volatility": 0.0,
                "trend_strength": 0.0,
                "confidence": 0.0,
            }

        try:
            # Redis 키: agent:market_regime:current:{symbol}
            key = f"agent:market_regime:current:{symbol}"
            market_data = await self.redis_client.get(key, deserialize=True)

            if market_data:
                logger.debug(
                    f"✅ Market Regime from Redis: {symbol} -> {market_data.get('regime_type')}"
                )
                return market_data

            # 데이터가 없으면 기본값
            logger.warning(
                f"No Market Regime data in Redis for {symbol}, using unknown"
            )
            return {
                "regime_type": "unknown",
                "volatility": 0.0,
                "trend_strength": 0.0,
                "confidence": 0.0,
            }

        except Exception as e:
            logger.error(f"Failed to read Market Regime from Redis: {e}")
            return {
                "regime_type": "unknown",
                "volatility": 0.0,
                "trend_strength": 0.0,
                "confidence": 0.0,
            }
