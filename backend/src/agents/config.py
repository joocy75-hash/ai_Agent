"""
에이전트 설정 (Agent Configuration)

에이전트 시스템의 전역 설정 및 환경 변수 관리

관련 문서: AGENT_SYSTEM_WORK_PLAN.md
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class AgentType(str, Enum):
    """에이전트 타입"""
    MARKET_ANALYZER = "market_analyzer"  # 시장 분석 에이전트
    SIGNAL_GENERATOR = "signal_generator"  # 시그널 생성 에이전트
    RISK_MANAGER = "risk_manager"  # 리스크 관리 에이전트
    PORTFOLIO_OPTIMIZER = "portfolio_optimizer"  # 포트폴리오 최적화 에이전트
    ALERT_NOTIFIER = "alert_notifier"  # 알림 에이전트
    DATA_COLLECTOR = "data_collector"  # 데이터 수집 에이전트


@dataclass
class RedisConfig:
    """Redis 설정"""
    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    password: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    decode_responses: bool = True

    def get_url(self) -> str:
        """Redis 연결 URL 생성"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class AgentSystemConfig:
    """
    에이전트 시스템 전역 설정

    환경 변수를 통해 설정 가능:
    - AGENT_ENABLED: 에이전트 시스템 활성화 여부 (default: true)
    - AGENT_MAX_WORKERS: 최대 워커 수 (default: 4)
    - AGENT_TASK_TIMEOUT: 작업 타임아웃 (초) (default: 300)
    - AGENT_QUEUE_SIZE: 큐 최대 크기 (default: 1000)
    """

    # 기본 설정
    enabled: bool = field(default_factory=lambda: os.getenv("AGENT_ENABLED", "true").lower() == "true")
    max_workers: int = field(default_factory=lambda: int(os.getenv("AGENT_MAX_WORKERS", "4")))
    task_timeout: float = field(default_factory=lambda: float(os.getenv("AGENT_TASK_TIMEOUT", "300")))
    queue_size: int = field(default_factory=lambda: int(os.getenv("AGENT_QUEUE_SIZE", "1000")))

    # Redis 설정
    redis: RedisConfig = field(default_factory=RedisConfig)

    # 재시도 설정
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    retry_backoff_factor: float = 2.0  # exponential backoff

    # 로깅 설정
    log_level: str = field(default_factory=lambda: os.getenv("AGENT_LOG_LEVEL", "INFO"))
    log_to_file: bool = field(default_factory=lambda: os.getenv("AGENT_LOG_TO_FILE", "false").lower() == "true")
    log_file_path: str = field(default_factory=lambda: os.getenv("AGENT_LOG_FILE", "logs/agents.log"))

    # 성능 모니터링
    enable_metrics: bool = True
    metrics_interval: float = 60.0  # seconds

    # 에이전트별 설정
    agent_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        """설정 초기화 후 검증"""
        if self.max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        if self.task_timeout <= 0:
            raise ValueError("task_timeout must be positive")
        if self.queue_size < 1:
            raise ValueError("queue_size must be at least 1")

    def get_agent_config(self, agent_type: AgentType) -> Dict[str, Any]:
        """
        특정 에이전트 타입의 설정 가져오기

        Args:
            agent_type: 에이전트 타입

        Returns:
            에이전트별 설정 딕셔너리
        """
        return self.agent_configs.get(agent_type.value, {})

    def set_agent_config(self, agent_type: AgentType, config: Dict[str, Any]):
        """
        특정 에이전트 타입의 설정 저장

        Args:
            agent_type: 에이전트 타입
            config: 에이전트별 설정
        """
        self.agent_configs[agent_type.value] = config


# 전역 설정 인스턴스 (싱글톤)
_global_config: Optional[AgentSystemConfig] = None


def get_agent_config() -> AgentSystemConfig:
    """
    전역 에이전트 설정 가져오기 (싱글톤 패턴)

    Returns:
        에이전트 시스템 설정
    """
    global _global_config
    if _global_config is None:
        _global_config = AgentSystemConfig()
    return _global_config


def set_agent_config(config: AgentSystemConfig):
    """
    전역 에이전트 설정 저장

    Args:
        config: 에이전트 시스템 설정
    """
    global _global_config
    _global_config = config


# 기본 에이전트별 설정
DEFAULT_AGENT_CONFIGS = {
    AgentType.MARKET_ANALYZER: {
        "enabled": True,
        "interval": 60.0,  # 60초마다 시장 분석
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "timeframes": ["1m", "5m", "15m", "1h"],
        "max_concurrent_analysis": 4,
    },
    AgentType.SIGNAL_GENERATOR: {
        "enabled": True,
        "interval": 30.0,  # 30초마다 시그널 생성
        "min_confidence": 0.7,
        "max_signals_per_hour": 10,
    },
    AgentType.RISK_MANAGER: {
        "enabled": True,
        "interval": 10.0,  # 10초마다 리스크 체크
        "max_drawdown_percent": 10.0,
        "max_position_size_percent": 20.0,
        "daily_loss_limit": 1000.0,  # USDT
    },
    AgentType.PORTFOLIO_OPTIMIZER: {
        "enabled": True,
        "interval": 300.0,  # 5분마다 포트폴리오 최적화
        "rebalance_threshold": 0.05,  # 5% 이상 차이나면 리밸런싱
    },
    AgentType.ALERT_NOTIFIER: {
        "enabled": True,
        "interval": 5.0,  # 5초마다 알림 체크
        "channels": ["telegram", "websocket"],
        "rate_limit": 60,  # 분당 최대 알림 수
    },
    AgentType.DATA_COLLECTOR: {
        "enabled": True,
        "interval": 1.0,  # 1초마다 데이터 수집
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "save_to_redis": True,
        "save_to_db": False,  # DB 부하 방지
    },
}


def init_default_configs():
    """기본 에이전트 설정 초기화"""
    config = get_agent_config()
    for agent_type, default_config in DEFAULT_AGENT_CONFIGS.items():
        if agent_type.value not in config.agent_configs:
            config.set_agent_config(agent_type, default_config)


# 모듈 임포트 시 기본 설정 초기화
init_default_configs()
