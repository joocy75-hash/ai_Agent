"""
Signal Validator Agent (시그널 검증 에이전트)

전략 시그널을 검증하여 거래 허용 여부 결정

AI Enhancement:
- DeepSeek-V3.2 API를 사용한 AI 기반 시그널 검증
- 규칙 기반 + AI 분석 결합으로 false signal 감소
- 비용 최적화 (Prompt Caching, Response Caching, Smart Sampling)
"""

import logging
import asyncio
import json
from typing import Any, Dict, List, Optional

from ..base import BaseAgent, AgentTask
from .models import SignalValidation, ValidationResult, ValidationRule
from .rules import ValidationRules
from src.ml.models import EnsemblePredictor
from src.ml.features import FeaturePipeline

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
        redis_client=None,
        ai_service=None
    ):
        super().__init__(agent_id, name, config)
        self.rules_engine = ValidationRules()
        self._validation_rules = self._init_rules()
        self.redis_client = redis_client
        self.ai_service = ai_service  # IntegratedAIService
        self.enable_ai = config.get("enable_ai", True) if config else True  # AI 활성화

        # ML 통합
        self.ml_predictor = EnsemblePredictor()
        self.feature_pipeline = FeaturePipeline()
        self.enable_ml = config.get("enable_ml", True) if config else True

        logger.info(f"SignalValidatorAgent initialized with AI={self.enable_ai}, ML={self.enable_ml}")

    async def validate_signal(self, params: dict) -> SignalValidation:
        """
        Public method for signal validation (wraps _validate_signal)

        Args:
            params: Signal parameters dict containing:
                - signal_id: str
                - symbol: str
                - action: str (buy/sell/close)
                - confidence: float
                - current_price: float
                - market_regime: str (optional)
                - volatility: float (optional)

        Returns:
            SignalValidation object with validation result
        """
        return await self._validate_signal(params)

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

        # Market Regime: 파라미터로 전달받거나 Redis에서 읽기
        # Issue Fix: ADX 0.00 문제 해결 - 파라미터로 전달된 market_regime 우선 사용
        market_regime_param = params.get("market_regime")
        if market_regime_param and isinstance(market_regime_param, dict):
            # 파라미터로 전달된 market_regime 사용 (ETH 전략에서 직접 전달)
            market_regime = market_regime_param
            logger.debug(f"Using market_regime from params: {market_regime}")
        else:
            # 레거시: Redis에서 Market Regime 읽기
            market_regime = await self._get_market_regime_from_redis(symbol)
            # 문자열로 전달된 경우 변환
            if market_regime_param and isinstance(market_regime_param, str):
                market_regime["regime_type"] = market_regime_param

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

        # 신뢰도 점수 계산 (규칙 기반)
        total_weight = sum(r.weight for r in self._validation_rules)
        confidence_score = sum(rule_scores) / total_weight if total_weight > 0 else 0.0

        # ML 기반 검증 (선택적)
        ml_confidence_adjustment = 0.0
        ml_should_reject = False

        if self.enable_ml and self.ml_predictor and params.get("candles"):
            try:
                candles = params.get("candles", [])

                # 피처 추출
                features_df = self.feature_pipeline.extract_features(
                    candles_5m=candles,
                    symbol=symbol
                )

                if not features_df.empty:
                    # ML 예측
                    ml_prediction = self.ml_predictor.predict(
                        features=features_df,
                        symbol=symbol,
                        rule_based_signal=action
                    )

                    # 1. 방향 일치 체크
                    ml_direction = ml_prediction.direction
                    direction_agrees = ml_direction.agrees_with_rule

                    if direction_agrees and ml_direction.confidence > 0.7:
                        ml_confidence_adjustment += 0.1
                        logger.info(f"🔬 ML confirms signal direction: {ml_direction.direction.value} (conf: {ml_direction.confidence:.2f}, boost: +0.1)")
                    elif not direction_agrees and ml_direction.confidence > 0.7:
                        ml_confidence_adjustment -= 0.15
                        logger.warning(f"🔬 ML disagrees with signal direction: ML={ml_direction.direction.value}, Signal={action} (penalty: -0.15)")

                    # 2. 타이밍 체크
                    ml_timing = ml_prediction.timing
                    if not ml_timing.is_good_entry and ml_timing.confidence > 0.6:
                        ml_confidence_adjustment -= 0.2
                        ml_should_reject = True
                        failed_rules.append("ml_timing")
                        warnings.append(f"ML timing check failed: {ml_timing.reason} (confidence: {ml_timing.confidence:.2f})")
                        logger.warning(f"🔬 ML rejects entry timing: {ml_timing.reason}")
                    elif ml_timing.is_good_entry and ml_timing.confidence > 0.6:
                        ml_confidence_adjustment += 0.05
                        logger.info(f"🔬 ML confirms good entry timing (boost: +0.05)")

                    # 3. 종합 신뢰도 체크
                    if ml_prediction.combined_confidence < 0.4:
                        ml_confidence_adjustment -= 0.1
                        warnings.append(f"ML combined confidence too low: {ml_prediction.combined_confidence:.2f}")
                        logger.warning(f"🔬 Low ML combined confidence: {ml_prediction.combined_confidence:.2f}")

                    logger.debug(
                        f"🔬 ML Validation: Dir={ml_direction.direction.value}({ml_direction.confidence:.0%}), "
                        f"Timing={ml_timing.is_good_entry}, Combined={ml_prediction.combined_confidence:.0%}, "
                        f"Adjustment={ml_confidence_adjustment:+.2f}"
                    )

            except Exception as e:
                logger.warning(f"ML validation failed: {e}")

        # 검증 결과 결정 (규칙 기반 + ML 조정)
        adjusted_confidence_score = max(0.0, min(1.0, confidence_score + ml_confidence_adjustment))

        validation_result = self._determine_result(
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            confidence_score=adjusted_confidence_score
        )

        # ML이 강하게 거부하면 무조건 REJECTED
        if ml_should_reject and self.enable_ml:
            validation_result = ValidationResult.REJECTED
            logger.warning("🔬 ML forces signal rejection due to poor timing")

        # AI 기반 검증 (선택적)
        ai_validation_result = validation_result
        ai_confidence_score = confidence_score

        if self.enable_ai and self.ai_service:
            try:
                ai_result = await self._validate_with_ai(
                    signal_id=signal_id,
                    symbol=symbol,
                    action=action,
                    confidence=confidence,
                    current_price=current_price,
                    market_regime=market_regime,
                    rule_based_result=validation_result.value,
                    rule_based_score=confidence_score,
                    failed_rules=failed_rules
                )

                if ai_result:
                    ai_validation_result = ai_result.get("validation_result", validation_result)
                    ai_confidence_score = ai_result.get("confidence_score", confidence_score)

                    logger.info(
                        f"🤖 AI Validation: {signal_id} -> {ai_validation_result.value if hasattr(ai_validation_result, 'value') else ai_validation_result} "
                        f"(rule: {validation_result.value}, AI conf: {ai_confidence_score:.2f})"
                    )

            except Exception as e:
                logger.warning(f"AI validation failed, using rule-based result: {e}")

        # SignalValidation 객체 생성 (AI 또는 규칙 기반)
        validation = SignalValidation(
            signal_id=signal_id,
            symbol=symbol,
            action=action,
            validation_result=ai_validation_result if isinstance(ai_validation_result, ValidationResult) else validation_result,
            confidence_score=ai_confidence_score,
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
                "ai_enhanced": self.enable_ai and self.ai_service is not None,
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

    async def _validate_with_ai(
        self,
        signal_id: str,
        symbol: str,
        action: str,
        confidence: float,
        current_price: float,
        market_regime: dict,
        rule_based_result: str,
        rule_based_score: float,
        failed_rules: List[str]
    ) -> Optional[dict]:
        """
        AI 기반 시그널 검증 (DeepSeek-V3.2)

        Args:
            signal_id: 시그널 ID
            symbol: 심볼
            action: 거래 액션 (buy/sell/hold)
            confidence: 시그널 신뢰도
            current_price: 현재가
            market_regime: 시장 환경 정보
            rule_based_result: 규칙 기반 검증 결과
            rule_based_score: 규칙 기반 신뢰도 점수
            failed_rules: 실패한 규칙 목록

        Returns:
            {"validation_result": ValidationResult, "confidence_score": float} 또는 None
        """
        if not self.ai_service:
            return None

        # 시스템 프롬프트
        system_prompt = """You are an expert trading signal validator AI.

Validate trading signals and determine if they should be:
- APPROVED: High confidence, all checks passed
- WARNING: Moderate confidence, proceed with caution
- REJECTED: Low confidence or critical issues detected

Return ONLY a valid JSON object:
{"validation_result": "APPROVED|WARNING|REJECTED", "confidence_score": 0.0-1.0, "reason": "brief explanation"}"""

        # 사용자 프롬프트
        user_prompt = f"""Validate trading signal for {symbol}:

Signal ID: {signal_id}
Action: {action}
Signal Confidence: {confidence:.2f}
Current Price: ${current_price:,.2f}

Market Regime:
- Type: {market_regime.get('regime_type', 'unknown')}
- Volatility: {market_regime.get('volatility', 0.0):.2f}%
- Trend Strength: {market_regime.get('trend_strength', 0.0):.2f}

Rule-based Validation:
- Result: {rule_based_result}
- Confidence Score: {rule_based_score:.2f}
- Failed Rules: {', '.join(failed_rules) if failed_rules else 'None'}

Provide your AI-based signal validation. Return JSON only:"""

        try:
            # AI API 호출 (비용 최적화 적용)
            result = await self.ai_service.call_ai(
                agent_type="signal_validator",
                prompt=user_prompt,
                context={
                    "symbol": symbol,
                    "action": action,
                    "confidence": confidence,
                    "market_regime": market_regime.get("regime_type"),
                },
                system_prompt=system_prompt,
                response_type="signal_validation",
                temperature=0.2,
                max_tokens=150,
                enable_caching=True,
                enable_sampling=True
            )

            response_text = result.get("response", "")

            if not response_text:
                return None

            # JSON 파싱 (ReDoS 안전한 방식)
            from ...utils.safe_json_parser import extract_json_from_text
            ai_validation = extract_json_from_text(response_text)

            if ai_validation:

                result_str = ai_validation.get("validation_result", "WARNING").upper()
                ai_confidence = float(ai_validation.get("confidence_score", 0.5))

                # ValidationResult로 변환
                try:
                    ai_result = ValidationResult(result_str)
                except ValueError:
                    ai_result = ValidationResult.WARNING

                logger.debug(
                    f"AI validation result: {result_str}, confidence: {ai_confidence:.2f}, "
                    f"reason: {ai_validation.get('reason', 'N/A')}"
                )

                return {
                    "validation_result": ai_result,
                    "confidence_score": ai_confidence,
                    "reason": ai_validation.get("reason", "")
                }

            return None

        except Exception as e:
            logger.error(f"AI validation error: {e}", exc_info=True)
            return None

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
