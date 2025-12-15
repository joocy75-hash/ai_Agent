"""
Agent Orchestrator (에이전트 오케스트레이터)

모든 AI 에이전트를 조율하고 이벤트 기반으로 협업하게 만드는 핵심 레이어
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from .models import (
    EventType,
    OrchestrationEvent,
    OrchestrationResult,
    OrchestrationRule,
    AgentAction,
    AgentHealthStatus,
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    에이전트 오케스트레이터

    주요 기능:
    1. 이벤트 기반 에이전트 협업 조율
    2. 규칙 기반 자동 액션 실행
    3. 에이전트 헬스 체크
    4. Redis Pub/Sub를 통한 실시간 이벤트 브로드캐스트

    아키텍처:
    ```
    Event발생 → Orchestrator → 규칙매칭 → 에이전트실행 → 결과집계
    ```

    예시 플로우:
    1. Signal Generated → SignalValidator → RiskMonitor → 최종 승인/거부
    2. Anomaly Detected → RiskMonitor → 자동 포지션 축소
    3. Rebalancing Due → PortfolioOptimizer → 할당 조정
    """

    def __init__(
        self,
        redis_client=None,
        db_session=None,
    ):
        self.redis_client = redis_client
        self.db_session = db_session

        # 등록된 에이전트들
        self._agents: Dict[str, Any] = {}

        # 오케스트레이션 규칙들
        self._rules: List[OrchestrationRule] = []

        # 에이전트 상태
        self._agent_health: Dict[str, AgentHealthStatus] = {}

        # 이벤트 핸들러 매핑
        self._event_handlers: Dict[EventType, List[Callable]] = {}

        # 기본 규칙 초기화
        self._initialize_default_rules()

        logger.info("AgentOrchestrator initialized")

    def register_agent(self, agent_id: str, agent_instance: Any):
        """에이전트 등록"""
        self._agents[agent_id] = agent_instance
        self._agent_health[agent_id] = AgentHealthStatus(
            agent_id=agent_id,
            agent_name=getattr(agent_instance, "name", agent_id),
        )
        logger.info(f"Agent registered: {agent_id}")

    def add_rule(self, rule: OrchestrationRule):
        """오케스트레이션 규칙 추가"""
        self._rules.append(rule)
        logger.info(f"Orchestration rule added: {rule.name}")

    def add_event_handler(self, event_type: EventType, handler: Callable):
        """이벤트 핸들러 추가"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def handle_event(self, event: OrchestrationEvent) -> OrchestrationResult:
        """
        이벤트 처리 (메인 엔트리 포인트)

        Args:
            event: 처리할 이벤트

        Returns:
            오케스트레이션 결과
        """
        logger.info(
            f"Handling event: {event.event_type.value} "
            f"from {event.source_agent} (priority={event.priority})"
        )

        result = OrchestrationResult(
            event_id=event.event_id,
            event_type=event.event_type,
        )

        try:
            # 1. 매칭되는 규칙 찾기
            matching_rules = self._find_matching_rules(event)

            if not matching_rules:
                logger.debug(f"No matching rules for event {event.event_type.value}")
                result.final_decision = "no_action"
                return result

            # 2. 우선순위 순으로 정렬
            matching_rules.sort(key=lambda r: r.priority, reverse=True)

            # 3. 각 규칙 실행
            for rule in matching_rules:
                if not rule.enabled:
                    continue

                logger.debug(f"Executing rule: {rule.name}")

                # 규칙의 액션들 순차 실행
                for action in rule.actions:
                    action_result = await self._execute_action(action, event)
                    result.actions_executed.append(action)
                    result.action_results[action.agent_id] = action_result

            # 4. 결과 집계 및 최종 결정
            result.final_decision = self._aggregate_results(event, result.action_results)

            # 5. Redis에 결과 저장
            await self._save_result_to_redis(result)

            # 6. 커스텀 이벤트 핸들러 실행
            await self._run_event_handlers(event, result)

            logger.info(
                f"Event processed: {event.event_id}, "
                f"decision={result.final_decision}, "
                f"actions={len(result.actions_executed)}"
            )

        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}", exc_info=True)
            result.success = False
            result.errors.append(str(e))
            result.final_decision = "error"

        return result

    async def publish_event(self, event: OrchestrationEvent):
        """
        이벤트 발행 (Redis Pub/Sub)

        다른 서비스/봇들이 구독하여 실시간으로 반응할 수 있음
        """
        if not self.redis_client:
            return

        try:
            channel = f"orchestration:events:{event.event_type.value}"
            await self.redis_client.publish(channel, event.model_dump_json())
            logger.debug(f"Event published to {channel}: {event.event_id}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    async def subscribe_to_events(self):
        """
        이벤트 구독 (Redis Pub/Sub)

        백그라운드에서 실행되며 이벤트를 수신하여 처리
        """
        if not self.redis_client:
            logger.warning("Redis client not available, cannot subscribe to events")
            return

        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.psubscribe("orchestration:events:*")

            logger.info("Subscribed to orchestration events")

            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        event_data = message["data"]
                        if isinstance(event_data, bytes):
                            event_data = event_data.decode("utf-8")

                        event = OrchestrationEvent.model_validate_json(event_data)
                        await self.handle_event(event)

                    except Exception as e:
                        logger.error(f"Error processing subscribed event: {e}")

        except Exception as e:
            logger.error(f"Event subscription error: {e}")

    async def check_agent_health(self) -> Dict[str, AgentHealthStatus]:
        """모든 에이전트의 상태 체크"""
        for agent_id, agent in self._agents.items():
            try:
                # Ping test (간단한 작업 실행)
                if hasattr(agent, "process_task"):
                    # BaseAgent의 경우
                    from ..base import AgentTask

                    ping_task = AgentTask(
                        task_id=f"health_check_{agent_id}",
                        task_type="health_check",
                        params={},
                    )

                    # 3초 타임아웃
                    await asyncio.wait_for(
                        agent.process_task(ping_task), timeout=3.0
                    )

                # 성공
                self._agent_health[agent_id].is_healthy = True
                self._agent_health[agent_id].last_heartbeat = datetime.utcnow()
                self._agent_health[agent_id].error_count = 0

            except asyncio.TimeoutError:
                self._agent_health[agent_id].is_healthy = False
                self._agent_health[agent_id].error_count += 1
                self._agent_health[agent_id].last_error = "Health check timeout"

            except Exception as e:
                self._agent_health[agent_id].is_healthy = False
                self._agent_health[agent_id].error_count += 1
                self._agent_health[agent_id].last_error = str(e)

        return self._agent_health

    # ==================== Private Methods ====================

    def _initialize_default_rules(self):
        """기본 오케스트레이션 규칙 초기화"""

        # 규칙 1: 신호 생성 시 검증 파이프라인
        self.add_rule(
            OrchestrationRule(
                rule_id="signal_validation_pipeline",
                name="Signal Validation Pipeline",
                description="전략 신호 생성 시 SignalValidator → RiskMonitor 순차 검증",
                trigger_event_types=[EventType.SIGNAL_GENERATED],
                actions=[
                    AgentAction(
                        agent_id="signal_validator",
                        action="validate_signal",
                        params={},
                        timeout_seconds=5,
                    ),
                    AgentAction(
                        agent_id="risk_monitor",
                        action="monitor_position",
                        params={},
                        timeout_seconds=5,
                    ),
                ],
                priority=5,
            )
        )

        # 규칙 2: 이상 징후 감지 시 리스크 모니터 알림
        self.add_rule(
            OrchestrationRule(
                rule_id="anomaly_risk_alert",
                name="Anomaly → Risk Monitor Alert",
                description="이상 징후 감지 시 리스크 모니터에게 알림",
                trigger_event_types=[EventType.ANOMALY_DETECTED],
                actions=[
                    AgentAction(
                        agent_id="risk_monitor",
                        action="check_emergency_stop",
                        params={},
                        timeout_seconds=3,
                    ),
                ],
                priority=5,
            )
        )

        # 규칙 3: 서킷 브레이커 발동 시 즉시 모든 봇 중지
        self.add_rule(
            OrchestrationRule(
                rule_id="circuit_breaker_emergency",
                name="Circuit Breaker Emergency Stop",
                description="서킷 브레이커 발동 시 즉시 모든 봇 중지",
                trigger_event_types=[EventType.CIRCUIT_BREAKER_TRIGGERED],
                actions=[
                    AgentAction(
                        agent_id="risk_monitor",
                        action="emergency_stop_all",
                        params={"reason": "circuit_breaker"},
                        timeout_seconds=10,
                    ),
                ],
                priority=10,  # 최고 우선순위
            )
        )

        # 규칙 4: 리밸런싱 제안 시 검증
        self.add_rule(
            OrchestrationRule(
                rule_id="rebalancing_validation",
                name="Rebalancing Validation",
                description="리밸런싱 제안 시 SignalValidator로 검증",
                trigger_event_types=[EventType.REBALANCING_DUE],
                actions=[
                    AgentAction(
                        agent_id="portfolio_optimizer",
                        action="suggest_rebalancing",
                        params={},
                        timeout_seconds=10,
                    ),
                    AgentAction(
                        agent_id="signal_validator",
                        action="validate_rebalancing",
                        params={},
                        timeout_seconds=5,
                    ),
                ],
                priority=3,
            )
        )

        # 규칙 5: 시장 환경 변화 시 포트폴리오 재분석
        self.add_rule(
            OrchestrationRule(
                rule_id="market_regime_portfolio_reanalysis",
                name="Market Regime → Portfolio Reanalysis",
                description="시장 환경 급변 시 포트폴리오 재분석",
                trigger_event_types=[EventType.MARKET_REGIME_CHANGED],
                actions=[
                    AgentAction(
                        agent_id="portfolio_optimizer",
                        action="analyze_portfolio",
                        params={},
                        timeout_seconds=15,
                    ),
                ],
                priority=2,
            )
        )

        logger.info(f"Initialized {len(self._rules)} default orchestration rules")

    def _find_matching_rules(self, event: OrchestrationEvent) -> List[OrchestrationRule]:
        """이벤트에 매칭되는 규칙 찾기"""
        matching = []

        for rule in self._rules:
            if event.event_type in rule.trigger_event_types:
                # 추가 조건 체크 (있으면)
                if self._check_rule_conditions(event, rule):
                    matching.append(rule)

        return matching

    def _check_rule_conditions(
        self, event: OrchestrationEvent, rule: OrchestrationRule
    ) -> bool:
        """규칙의 추가 조건 체크"""
        if not rule.trigger_conditions:
            return True

        # TODO: 복잡한 조건 로직 구현
        # 예: rule.trigger_conditions = {"severity": "high", "symbol": "BTCUSDT"}
        # event.data와 비교하여 모든 조건이 일치하는지 확인

        for key, expected_value in rule.trigger_conditions.items():
            if event.data.get(key) != expected_value:
                return False

        return True

    async def _execute_action(
        self, action: AgentAction, event: OrchestrationEvent
    ) -> Any:
        """액션 실행"""
        agent = self._agents.get(action.agent_id)

        if not agent:
            logger.warning(f"Agent not found: {action.agent_id}")
            return {"error": "agent_not_found"}

        try:
            # BaseAgent의 경우
            if hasattr(agent, "process_task"):
                from ..base import AgentTask

                # 이벤트 데이터를 파라미터에 병합
                params = {**action.params, **event.data}
                params["event_id"] = event.event_id
                params["event_type"] = event.event_type.value

                task = AgentTask(
                    task_id=f"{event.event_id}_{action.agent_id}",
                    task_type=action.action,
                    params=params,
                )

                # 타임아웃 적용
                result = await asyncio.wait_for(
                    agent.process_task(task), timeout=action.timeout_seconds
                )

                logger.debug(
                    f"Action executed: {action.agent_id}.{action.action} → {result}"
                )

                return result

            else:
                # 커스텀 에이전트
                method = getattr(agent, action.action, None)
                if method and callable(method):
                    result = await asyncio.wait_for(
                        method(**action.params), timeout=action.timeout_seconds
                    )
                    return result
                else:
                    logger.warning(
                        f"Method not found: {action.agent_id}.{action.action}"
                    )
                    return {"error": "method_not_found"}

        except asyncio.TimeoutError:
            logger.error(
                f"Action timeout: {action.agent_id}.{action.action} "
                f"({action.timeout_seconds}s)"
            )
            return {"error": "timeout"}

        except Exception as e:
            logger.error(
                f"Action execution error: {action.agent_id}.{action.action} - {e}",
                exc_info=True,
            )
            return {"error": str(e)}

    def _aggregate_results(
        self, event: OrchestrationEvent, action_results: Dict[str, Any]
    ) -> str:
        """
        액션 결과들을 집계하여 최종 결정

        이 메서드는 비즈니스 로직에 따라 커스터마이징 필요!
        """

        # TODO: 사용자 정의 로직
        # 여기서는 간단한 예시만 제공

        # 신호 검증 플로우
        if event.event_type == EventType.SIGNAL_GENERATED:
            validator_result = action_results.get("signal_validator", {})
            risk_result = action_results.get("risk_monitor", {})

            # SignalValidator가 거부하면 차단
            if not validator_result.get("approved", False):
                return "block_signal"

            # RiskMonitor가 high/critical이면 차단
            risk_level = risk_result.get("risk_level", "safe")
            if risk_level in ["high", "critical"]:
                return "block_risk"

            # 모두 통과
            return "allow"

        # 이상 징후 플로우
        elif event.event_type == EventType.ANOMALY_DETECTED:
            anomaly_data = event.data
            severity = anomaly_data.get("severity", "low")

            if severity == "critical":
                return "emergency_stop"
            elif severity == "high":
                return "reduce_positions"
            else:
                return "monitor"

        # 서킷 브레이커
        elif event.event_type == EventType.CIRCUIT_BREAKER_TRIGGERED:
            return "stop_all_bots"

        # 리밸런싱
        elif event.event_type == EventType.REBALANCING_DUE:
            optimizer_result = action_results.get("portfolio_optimizer", {})
            validator_result = action_results.get("signal_validator", {})

            if validator_result.get("approved", True):
                return "apply_rebalancing"
            else:
                return "skip_rebalancing"

        # 기본
        return "no_action"

    async def _save_result_to_redis(self, result: OrchestrationResult):
        """결과를 Redis에 저장"""
        if not self.redis_client:
            return

        try:
            key = f"orchestration:result:{result.event_id}"
            await self.redis_client.setex(key, 3600, result.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to save result to Redis: {e}")

    async def _run_event_handlers(
        self, event: OrchestrationEvent, result: OrchestrationResult
    ):
        """커스텀 이벤트 핸들러 실행"""
        handlers = self._event_handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                await handler(event, result)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
