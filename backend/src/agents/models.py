"""
에이전트 데이터 모델 (Agent Data Models)

에이전트 시스템의 데이터베이스 모델 정의

관련 문서: AGENT_SYSTEM_WORK_PLAN.md
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

from ..database.models import Base


class AgentStatus(str, Enum):
    """에이전트 상태"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class AgentTaskStatus(str, Enum):
    """에이전트 작업 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class AgentInstance(Base):
    """
    에이전트 인스턴스 (Agent Instance)

    시스템에서 실행되는 에이전트 인스턴스 정보
    """
    __tablename__ = "agent_instances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # user별 에이전트 (없으면 시스템 에이전트)

    # 에이전트 정보
    agent_id = Column(String(100), unique=True, nullable=False, index=True)  # 에이전트 고유 ID
    name = Column(String(200), nullable=False)  # 에이전트 이름
    agent_type = Column(String(50), nullable=False, index=True)  # 에이전트 타입 (market_analyzer, signal_generator 등)
    description = Column(Text, nullable=True)  # 에이전트 설명

    # 상태
    status = Column(
        SQLEnum(AgentStatus),
        default=AgentStatus.IDLE,
        nullable=False,
        index=True
    )
    is_enabled = Column(Boolean, default=True, nullable=False)  # 활성화 여부

    # 설정
    config = Column(JSON, nullable=True)  # 에이전트별 설정 (JSON)

    # 메트릭
    total_tasks = Column(Integer, default=0, nullable=False)
    completed_tasks = Column(Integer, default=0, nullable=False)
    failed_tasks = Column(Integer, default=0, nullable=False)
    avg_task_duration = Column(Float, default=0.0, nullable=False)  # 평균 작업 시간 (초)
    error_count = Column(Integer, default=0, nullable=False)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)  # 마지막 시작 시각
    stopped_at = Column(DateTime, nullable=True)  # 마지막 중지 시각
    last_error_at = Column(DateTime, nullable=True)  # 마지막 에러 시각
    last_task_at = Column(DateTime, nullable=True)  # 마지막 작업 시각

    # 에러 정보
    last_error = Column(Text, nullable=True)  # 마지막 에러 메시지

    # Relationships
    tasks = relationship("AgentTaskLog", back_populates="agent", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_agent_user_type", "user_id", "agent_type"),
        Index("idx_agent_status", "status", "is_enabled"),
    )


class AgentTaskLog(Base):
    """
    에이전트 작업 로그 (Agent Task Log)

    에이전트가 처리한 작업 내역
    """
    __tablename__ = "agent_task_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_instances.id"), nullable=False)

    # 작업 정보
    task_id = Column(String(100), unique=True, nullable=False, index=True)  # 작업 고유 ID
    task_type = Column(String(50), nullable=False, index=True)  # 작업 타입
    priority = Column(String(20), default="normal", nullable=False)  # low, normal, high, critical

    # 상태
    status = Column(
        SQLEnum(AgentTaskStatus),
        default=AgentTaskStatus.PENDING,
        nullable=False,
        index=True
    )

    # 데이터
    params = Column(JSON, nullable=True)  # 작업 파라미터 (JSON)
    result = Column(JSON, nullable=True)  # 작업 결과 (JSON)
    error_message = Column(Text, nullable=True)  # 에러 메시지

    # 메트릭
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    duration_seconds = Column(Float, nullable=True)  # 작업 수행 시간 (초)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    agent = relationship("AgentInstance", back_populates="tasks")

    # Indexes
    __table_args__ = (
        Index("idx_task_agent_status", "agent_id", "status"),
        Index("idx_task_created", "created_at"),
    )


class AgentEvent(Base):
    """
    에이전트 이벤트 (Agent Event)

    에이전트 시스템의 중요 이벤트 로그
    """
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_instances.id"), nullable=True)  # 시스템 이벤트는 None

    # 이벤트 정보
    event_type = Column(String(50), nullable=False, index=True)  # started, stopped, error, task_completed 등
    severity = Column(String(20), default="info", nullable=False)  # debug, info, warning, error, critical
    message = Column(Text, nullable=False)

    # 데이터
    event_metadata = Column(JSON, nullable=True)  # 이벤트 메타데이터 (JSON)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes
    __table_args__ = (
        Index("idx_event_type_severity", "event_type", "severity"),
        Index("idx_event_created", "created_at"),
    )


class AgentMetric(Base):
    """
    에이전트 메트릭 (Agent Metric)

    에이전트 시스템의 성능 메트릭 시계열 데이터
    """
    __tablename__ = "agent_metrics"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_instances.id"), nullable=False)

    # 메트릭 데이터
    metric_type = Column(String(50), nullable=False, index=True)  # cpu_usage, memory_usage, task_rate 등
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)  # percent, seconds, count 등

    # 메타데이터
    metric_metadata = Column(JSON, nullable=True)

    # 타임스탬프
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes
    __table_args__ = (
        Index("idx_metric_agent_type", "agent_id", "metric_type"),
        Index("idx_metric_timestamp", "timestamp"),
    )


class AgentCommunication(Base):
    """
    에이전트 간 통신 로그 (Agent Communication Log)

    에이전트 간 메시지 전달 내역
    """
    __tablename__ = "agent_communications"

    id = Column(Integer, primary_key=True, index=True)

    # 송수신 정보
    sender_agent_id = Column(Integer, ForeignKey("agent_instances.id"), nullable=False)
    receiver_agent_id = Column(Integer, ForeignKey("agent_instances.id"), nullable=True)  # broadcast는 None

    # 메시지 정보
    message_type = Column(String(50), nullable=False, index=True)  # request, response, event, broadcast 등
    channel = Column(String(100), nullable=True)  # Redis Pub/Sub 채널
    payload = Column(JSON, nullable=False)  # 메시지 페이로드

    # 상태
    is_delivered = Column(Boolean, default=False, nullable=False)
    delivered_at = Column(DateTime, nullable=True)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes
    __table_args__ = (
        Index("idx_comm_sender_receiver", "sender_agent_id", "receiver_agent_id"),
        Index("idx_comm_created", "created_at"),
    )


class AgentSchedule(Base):
    """
    에이전트 스케줄 (Agent Schedule)

    에이전트의 주기적 작업 스케줄 정의
    """
    __tablename__ = "agent_schedules"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agent_instances.id"), nullable=False)

    # 스케줄 정보
    name = Column(String(200), nullable=False)  # 스케줄 이름
    task_type = Column(String(50), nullable=False)  # 실행할 작업 타입
    cron_expression = Column(String(100), nullable=True)  # Cron 표현식 (예: "*/5 * * * *")
    interval_seconds = Column(Integer, nullable=True)  # 간격 (초) - cron 대신 사용 가능

    # 상태
    is_enabled = Column(Boolean, default=True, nullable=False)

    # 설정
    params = Column(JSON, nullable=True)  # 작업 파라미터

    # 실행 정보
    last_run_at = Column(DateTime, nullable=True)  # 마지막 실행 시각
    next_run_at = Column(DateTime, nullable=True)  # 다음 실행 예정 시각
    run_count = Column(Integer, default=0, nullable=False)  # 총 실행 횟수

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_schedule_agent_enabled", "agent_id", "is_enabled"),
        Index("idx_schedule_next_run", "next_run_at"),
    )
