"""
에이전트 시스템 (Agent System)

자율 실행 에이전트를 위한 프레임워크

주요 구성 요소:
- BaseAgent: 에이전트 베이스 클래스
- AgentTask: 에이전트 작업 정의
- AgentState: 에이전트 상태 관리
- RedisClient: 에이전트 간 통신
- Models: 데이터베이스 모델

에이전트 타입:
- MarketRegimeAgent: 시장 환경 분석 에이전트
- SignalValidatorAgent: 시그널 검증 에이전트
- RiskMonitorAgent: 리스크 모니터링 에이전트

사용 예:
```python
from agents import BaseAgent, AgentTask, TaskPriority
from agents.market_regime import MarketRegimeAgent
from agents.signal_validator import SignalValidatorAgent
from agents.risk_monitor import RiskMonitorAgent

# 시장 환경 분석 에이전트
market_agent = MarketRegimeAgent(
    agent_id="market_1",
    name="Market Analyzer"
)
await market_agent.start()

# 시그널 검증 에이전트
validator_agent = SignalValidatorAgent(
    agent_id="validator_1",
    name="Signal Validator"
)
await validator_agent.start()

# 리스크 모니터링 에이전트
risk_agent = RiskMonitorAgent(
    agent_id="risk_1",
    name="Risk Monitor",
    config={"max_daily_loss": 1000.0}
)
await risk_agent.start()
```
"""

# Base components
from .base import (
    AgentMetrics,
    AgentState,
    AgentTask,
    BaseAgent,
    TaskPriority,
)

# Config
from .config import (
    AgentSystemConfig,
    AgentType,
    RedisConfig,
    get_agent_config,
    set_agent_config,
)

# Database models (공통 모델은 models.py에 유지)
try:
    from .models import (
        AgentCommunication,
        AgentEvent,
        AgentInstance,
        AgentMetric,
        AgentSchedule,
        AgentStatus,
        AgentTaskLog,
        AgentTaskStatus,
    )
except ImportError:
    # models.py가 없을 경우 무시
    pass

# Specialized agents
from .market_regime import (
    MarketRegime,
    MarketRegimeAgent,
    RegimeType,
)
from .risk_monitor import (
    RiskAction,
    RiskAlert,
    RiskLevel,
    RiskMonitorAgent,
)
from .signal_validator import (
    SignalValidation,
    SignalValidatorAgent,
    ValidationResult,
)

# 버전 정보
__version__ = "0.2.0"

# Public API
__all__ = [
    # Base
    "BaseAgent",
    "AgentState",
    "AgentTask",
    "TaskPriority",
    "AgentMetrics",
    # Config
    "AgentSystemConfig",
    "AgentType",
    "RedisConfig",
    "get_agent_config",
    "set_agent_config",
    # Database Models
    "AgentCommunication",
    "AgentEvent",
    "AgentInstance",
    "AgentMetric",
    "AgentSchedule",
    "AgentStatus",
    "AgentTaskLog",
    "AgentTaskStatus",
    # Market Regime Agent
    "MarketRegimeAgent",
    "MarketRegime",
    "RegimeType",
    # Signal Validator Agent
    "SignalValidatorAgent",
    "SignalValidation",
    "ValidationResult",
    # Risk Monitor Agent
    "RiskMonitorAgent",
    "RiskAlert",
    "RiskLevel",
    "RiskAction",
]
