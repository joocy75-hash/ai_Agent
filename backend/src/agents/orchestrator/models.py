"""
Agent Orchestrator 데이터 모델
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """오케스트레이션 이벤트 타입"""

    # 트레이딩 이벤트
    SIGNAL_GENERATED = "signal_generated"  # 전략에서 신호 생성
    TRADE_EXECUTED = "trade_executed"  # 거래 실행 완료
    POSITION_OPENED = "position_opened"  # 포지션 진입
    POSITION_CLOSED = "position_closed"  # 포지션 청산

    # 시장 이벤트
    MARKET_REGIME_CHANGED = "market_regime_changed"  # 시장 환경 변화
    PRICE_ALERT = "price_alert"  # 가격 알림
    VOLUME_SPIKE = "volume_spike"  # 거래량 급증

    # 리스크 이벤트
    RISK_LEVEL_CHANGED = "risk_level_changed"  # 리스크 레벨 변화
    STOP_LOSS_TRIGGERED = "stop_loss_triggered"  # 손절 발동
    MARGIN_WARNING = "margin_warning"  # 마진 경고

    # 포트폴리오 이벤트
    REBALANCING_DUE = "rebalancing_due"  # 리밸런싱 필요
    ALLOCATION_CHANGED = "allocation_changed"  # 할당 변경

    # 이상 징후 이벤트
    ANOMALY_DETECTED = "anomaly_detected"  # 이상 징후 감지
    CIRCUIT_BREAKER_TRIGGERED = "circuit_breaker_triggered"  # 서킷 브레이커 발동


class OrchestrationEvent(BaseModel):
    """오케스트레이션 이벤트"""

    event_id: str = Field(description="이벤트 ID")
    event_type: EventType = Field(description="이벤트 타입")
    source_agent: str = Field(description="이벤트 발생 에이전트")

    # 대상
    user_id: Optional[int] = None
    bot_instance_id: Optional[int] = None
    symbol: Optional[str] = None

    # 데이터
    data: Dict[str, Any] = Field(default_factory=dict)

    # 메타데이터
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    priority: int = Field(1, description="우선순위 (1=낮음, 5=높음)")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_123456",
                "event_type": "anomaly_detected",
                "source_agent": "anomaly_detector",
                "bot_instance_id": 42,
                "data": {
                    "anomaly_type": "excessive_trading",
                    "severity": "high",
                },
                "priority": 4,
            }
        }


class AgentAction(BaseModel):
    """에이전트 액션"""

    agent_id: str = Field(description="실행할 에이전트 ID")
    action: str = Field(description="실행할 액션")
    params: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(30, description="타임아웃 (초)")


class OrchestrationResult(BaseModel):
    """오케스트레이션 결과"""

    event_id: str
    event_type: EventType
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    # 실행된 액션들
    actions_executed: List[AgentAction] = Field(default_factory=list)

    # 각 액션의 결과
    action_results: Dict[str, Any] = Field(default_factory=dict)

    # 성공 여부
    success: bool = True
    errors: List[str] = Field(default_factory=list)

    # 최종 결정
    final_decision: Optional[str] = None  # "allow", "block", "adjust", etc.

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_123456",
                "event_type": "signal_generated",
                "actions_executed": [
                    {"agent_id": "signal_validator", "action": "validate_signal"},
                    {"agent_id": "risk_monitor", "action": "check_risk"},
                ],
                "action_results": {
                    "signal_validator": {"approved": True, "confidence": 0.85},
                    "risk_monitor": {"risk_level": "safe"},
                },
                "final_decision": "allow",
            }
        }


class OrchestrationRule(BaseModel):
    """오케스트레이션 규칙"""

    rule_id: str
    name: str
    description: str

    # 트리거 조건
    trigger_event_types: List[EventType]
    trigger_conditions: Dict[str, Any] = Field(default_factory=dict)

    # 실행할 액션들 (순차 실행)
    actions: List[AgentAction]

    # 조건부 실행
    enabled: bool = True
    priority: int = 1


class AgentHealthStatus(BaseModel):
    """에이전트 상태"""

    agent_id: str
    agent_name: str
    is_healthy: bool = True
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    error_count: int = 0
    last_error: Optional[str] = None
