"""
Orchestration Decision Logic (오케스트레이션 결정 로직)

TODO: 비즈니스 로직 커스터마이징

이 파일에서 에이전트 결과를 집계하여 최종 결정을 내리는 로직을 구현하세요.

예시:
1. 신호 검증: SignalValidator + RiskMonitor 결과 → 거래 허용/차단
2. 이상 징후: Anomaly 심각도 → 봇 중지/포지션 축소/모니터링
3. 리밸런싱: PortfolioOptimizer + SignalValidator → 적용/보류

사용자 정의 포인트:
- 각 이벤트 타입별 의사결정 규칙
- 에이전트 결과 가중치 (어떤 에이전트를 더 신뢰?)
- 임계값 설정 (언제 자동 실행?)
"""

from typing import Any, Dict

from .models import EventType, OrchestrationEvent


class OrchestrationDecisionLogic:
    """
    오케스트레이션 결정 로직

    비즈니스 요구사항에 따라 이 클래스를 커스터마이징하세요.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

        # === 사용자 정의 임계값 ===
        # TODO: 프로젝트 요구사항에 맞게 조정

        # SignalValidator 최소 신뢰도
        self.min_signal_confidence = self.config.get("min_signal_confidence", 0.65)

        # RiskMonitor 허용 리스크 레벨
        self.allowed_risk_levels = self.config.get(
            "allowed_risk_levels", ["safe", "moderate"]
        )

        # Anomaly 자동 조치 임계값
        self.anomaly_auto_stop_severities = self.config.get(
            "anomaly_auto_stop_severities", ["critical"]
        )

        # Portfolio 리밸런싱 최소 개선율
        self.min_rebalancing_improvement = self.config.get(
            "min_rebalancing_improvement", 5.0  # 5% 샤프 개선
        )

    def decide_signal_validation(
        self, event: OrchestrationEvent, action_results: Dict[str, Any]
    ) -> str:
        """
        신호 검증 결정

        Args:
            event: SIGNAL_GENERATED 이벤트
            action_results: {
                "signal_validator": {...},
                "risk_monitor": {...},
            }

        Returns:
            "allow" | "block_low_confidence" | "block_risk" | "adjust_size"

        TODO: 아래 로직을 프로젝트 요구사항에 맞게 수정하세요!
        """
        validator_result = action_results.get("signal_validator", {})
        risk_result = action_results.get("risk_monitor", {})

        # 1. SignalValidator 체크
        approved = validator_result.get("approved", False)
        confidence = validator_result.get("confidence", 0.0)

        if not approved:
            return "block_low_confidence"

        if confidence < self.min_signal_confidence:
            return "block_low_confidence"

        # 2. RiskMonitor 체크
        risk_level = risk_result.get("risk_level", "safe")

        if risk_level not in self.allowed_risk_levels:
            return "block_risk"

        # 3. 조건부 포지션 축소
        # 사용자 설정: 신뢰도 0.7 미만이어도 정상 진행 (공격적 접근)
        # if confidence < 0.7:
        #     return "adjust_size_50"

        # 모두 통과 (사용자 선택: 정상 진행)
        return "allow"

    def decide_anomaly_response(
        self, event: OrchestrationEvent, action_results: Dict[str, Any]
    ) -> str:
        """
        이상 징후 대응 결정

        Args:
            event: ANOMALY_DETECTED 이벤트
            action_results: {
                "risk_monitor": {...}
            }

        Returns:
            "emergency_stop" | "reduce_positions" | "monitor" | "ignore"

        TODO: 이상 징후 타입별로 다른 대응 전략 구현 가능
        """
        anomaly_data = event.data
        anomaly_data.get("anomaly_type", "unknown")
        severity = anomaly_data.get("severity", "low")

        # 심각도별 대응
        if severity in self.anomaly_auto_stop_severities:
            # CRITICAL → 즉시 중지
            return "emergency_stop"

        elif severity == "high":
            # HIGH → 사용자 설정: 즉시 봇 중지 (안전 우선)
            # 모든 HIGH 심각도 이상 징후는 즉시 중지
            return "emergency_stop"

        elif severity == "medium":
            # MEDIUM → 모니터링 강화
            return "monitor"

        else:
            # LOW → 로깅만
            return "ignore"

    def decide_circuit_breaker(
        self, event: OrchestrationEvent, action_results: Dict[str, Any]
    ) -> str:
        """
        서킷 브레이커 결정

        Args:
            event: CIRCUIT_BREAKER_TRIGGERED 이벤트
            action_results: {
                "risk_monitor": {...}
            }

        Returns:
            "stop_all_bots" | "stop_losing_bots" | "reduce_all_positions"

        TODO: 손실 한도 도달 시 대응 전략
        """
        circuit_data = event.data
        loss_percent = abs(circuit_data.get("daily_loss_percent", 0.0))

        # 손실 비율에 따라 단계적 대응
        # 사용자 설정: 손실 봇만 중지 (선택적 대응)
        if loss_percent >= 15.0:
            # 15% 이상 → 모든 봇 중지 (극단적 상황)
            return "stop_all_bots"

        elif loss_percent >= 10.0:
            # 10% 이상 → 사용자 선택: 손실 봇만 중지
            return "stop_losing_bots"

        else:
            # 10% 미만 → 손실 중인 봇만 중지
            return "stop_losing_bots"

    def decide_rebalancing(
        self, event: OrchestrationEvent, action_results: Dict[str, Any]
    ) -> str:
        """
        리밸런싱 결정

        Args:
            event: REBALANCING_DUE 이벤트
            action_results: {
                "portfolio_optimizer": {...},
                "signal_validator": {...}
            }

        Returns:
            "apply_rebalancing" | "skip_insufficient_improvement" | "skip_validation_failed"

        TODO: 리밸런싱 적용 조건 정의
        """
        optimizer_result = action_results.get("portfolio_optimizer", {})
        validator_result = action_results.get("signal_validator", {})

        # 1. Validator 체크 (있으면)
        if validator_result:
            approved = validator_result.get("approved", True)
            if not approved:
                return "skip_validation_failed"

        # 2. 개선율 체크
        # 사용자 설정: 5% 미만이면 건너뛰기
        sharpe_improvement = optimizer_result.get("sharpe_improvement_percent", 0.0)

        if sharpe_improvement < self.min_rebalancing_improvement:  # 기본값 5.0%
            return "skip_insufficient_improvement"  # 사용자 선택: 건너뛰기

        # 3. 리스크 증가 체크
        risk_reduction = optimizer_result.get("risk_reduction_percent", 0.0)

        # 리스크가 증가하는 경우 (risk_reduction < 0)
        if risk_reduction < -10.0:  # 10% 이상 리스크 증가
            # 샤프가 크게 개선되지 않으면 거부
            if sharpe_improvement < 15.0:
                return "skip_risk_increase"

        # 모두 통과
        return "apply_rebalancing"

    def decide_market_regime_change(
        self, event: OrchestrationEvent, action_results: Dict[str, Any]
    ) -> str:
        """
        시장 환경 변화 대응 결정

        Args:
            event: MARKET_REGIME_CHANGED 이벤트
            action_results: {
                "portfolio_optimizer": {...}
            }

        Returns:
            "trigger_rebalancing" | "adjust_risk_params" | "no_action"

        TODO: 시장 환경별 대응 전략
        """
        market_data = event.data
        new_regime = market_data.get("new_regime", "neutral")
        old_regime = market_data.get("old_regime", "neutral")

        # 급격한 환경 변화 시 리밸런싱 트리거
        if old_regime == "trending" and new_regime == "volatile":
            return "trigger_rebalancing"

        elif old_regime == "ranging" and new_regime == "trending":
            return "trigger_rebalancing"

        elif new_regime == "low_volume":
            # 저유동성 시장 → 리스크 파라미터 조정
            return "adjust_risk_params"

        else:
            # 변화가 크지 않음
            return "no_action"

    # === 메인 결정 함수 ===

    def make_decision(
        self, event: OrchestrationEvent, action_results: Dict[str, Any]
    ) -> str:
        """
        이벤트 타입에 따라 적절한 결정 로직 호출

        이 함수를 AgentOrchestrator._aggregate_results에서 사용하세요.
        """
        if event.event_type == EventType.SIGNAL_GENERATED:
            return self.decide_signal_validation(event, action_results)

        elif event.event_type == EventType.ANOMALY_DETECTED:
            return self.decide_anomaly_response(event, action_results)

        elif event.event_type == EventType.CIRCUIT_BREAKER_TRIGGERED:
            return self.decide_circuit_breaker(event, action_results)

        elif event.event_type == EventType.REBALANCING_DUE:
            return self.decide_rebalancing(event, action_results)

        elif event.event_type == EventType.MARKET_REGIME_CHANGED:
            return self.decide_market_regime_change(event, action_results)

        else:
            return "no_action"
