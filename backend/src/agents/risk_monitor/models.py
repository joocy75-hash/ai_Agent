"""
Risk Monitor Models (리스크 모니터링 데이터 모델)

리스크 알림 및 조치 데이터 모델
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    """리스크 레벨"""
    LOW = "low"  # 낮음
    MEDIUM = "medium"  # 중간
    HIGH = "high"  # 높음
    CRITICAL = "critical"  # 치명적


class RiskAction(str, Enum):
    """리스크 조치"""
    NONE = "none"  # 조치 없음
    WARNING = "warning"  # 경고만
    REDUCE_POSITION = "reduce_position"  # 포지션 축소
    CLOSE_POSITION = "close_position"  # 포지션 청산
    STOP_TRADING = "stop_trading"  # 거래 중단
    EMERGENCY_SHUTDOWN = "emergency_shutdown"  # 긴급 종료


@dataclass
class RiskAlert:
    """
    리스크 알림

    Attributes:
        alert_id: 알림 ID
        alert_type: 알림 타입 (drawdown, exposure, volatility 등)
        risk_level: 리스크 레벨
        message: 알림 메시지
        current_value: 현재 값
        threshold_value: 임계값
        recommended_action: 권장 조치
        auto_execute: 자동 실행 여부
        metadata: 추가 메타데이터
        timestamp: 알림 시각
    """
    alert_id: str
    alert_type: str
    risk_level: RiskLevel
    message: str
    current_value: float
    threshold_value: float
    recommended_action: RiskAction
    auto_execute: bool = False
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "risk_level": self.risk_level.value,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "recommended_action": self.recommended_action.value,
            "auto_execute": self.auto_execute,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def is_critical(self) -> bool:
        """치명적 리스크인지 확인"""
        return self.risk_level == RiskLevel.CRITICAL

    def requires_action(self) -> bool:
        """조치가 필요한지 확인"""
        return self.recommended_action not in {RiskAction.NONE, RiskAction.WARNING}


@dataclass
class PositionRisk:
    """
    포지션 리스크 정보

    Attributes:
        symbol: 심볼
        side: long/short
        size: 포지션 크기
        entry_price: 진입 가격
        current_price: 현재 가격
        unrealized_pnl: 미실현 손익
        unrealized_pnl_percent: 미실현 손익률 (%)
        leverage: 레버리지
        liquidation_price: 청산 가격
        distance_to_liquidation: 청산가까지 거리 (%)
    """
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    leverage: int
    liquidation_price: Optional[float] = None
    distance_to_liquidation: Optional[float] = None

    def is_losing(self) -> bool:
        """손실 포지션인지 확인"""
        return self.unrealized_pnl < 0

    def is_near_liquidation(self, threshold_percent: float = 10.0) -> bool:
        """청산가 근처인지 확인"""
        if self.distance_to_liquidation is None:
            return False
        return self.distance_to_liquidation < threshold_percent
