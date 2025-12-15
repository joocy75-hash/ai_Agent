"""
Anomaly Detection Agent 데이터 모델
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AnomalyType(str, Enum):
    """이상 징후 타입"""

    # 봇 동작 이상
    EXCESSIVE_TRADING = "excessive_trading"  # 과도한 거래 빈도
    LOSING_STREAK = "losing_streak"  # 연속 손실
    HIGH_SLIPPAGE = "high_slippage"  # 높은 슬리피지
    API_ERROR_SPIKE = "api_error_spike"  # API 오류 급증
    BOT_STUCK = "bot_stuck"  # 봇 멈춤 (일정 시간 무응답)

    # 시장 이상
    FLASH_CRASH = "flash_crash"  # 급격한 가격 변동
    VOLUME_SPIKE = "volume_spike"  # 거래량 급증
    EXTREME_FUNDING = "extreme_funding"  # 극단적 펀딩 비율
    LIQUIDITY_DROP = "liquidity_drop"  # 유동성 급감

    # 리스크 이상
    CIRCUIT_BREAKER = "circuit_breaker"  # 일일 손실 한도 도달
    MARGIN_WARNING = "margin_warning"  # 마진 부족 경고
    CORRELATION_BREAKDOWN = "correlation_breakdown"  # 상관관계 붕괴


class AnomalySeverity(str, Enum):
    """이상 징후 심각도"""
    LOW = "low"  # 정보성 알림
    MEDIUM = "medium"  # 주의 필요
    HIGH = "high"  # 즉시 조치 필요
    CRITICAL = "critical"  # 자동 중지 필요


class AnomalyAlert(BaseModel):
    """이상 징후 알림"""

    alert_id: str = Field(description="알림 고유 ID")
    anomaly_type: AnomalyType = Field(description="이상 징후 타입")
    severity: AnomalySeverity = Field(description="심각도")

    # 대상
    user_id: Optional[int] = Field(None, description="사용자 ID")
    bot_instance_id: Optional[int] = Field(None, description="봇 인스턴스 ID")
    symbol: Optional[str] = Field(None, description="심볼 (시장 이상인 경우)")

    # 내용
    message: str = Field(description="알림 메시지")
    details: Dict[str, Any] = Field(default_factory=dict, description="상세 정보")
    recommended_action: str = Field(description="권장 조치")

    # 메타데이터
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    auto_executed: bool = Field(False, description="자동 조치 실행 여부")
    acknowledged: bool = Field(False, description="사용자 확인 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": "anomaly_123456",
                "anomaly_type": "excessive_trading",
                "severity": "high",
                "bot_instance_id": 42,
                "message": "비정상적으로 많은 거래: 25회/10분",
                "details": {
                    "trade_count": 25,
                    "time_window_minutes": 10,
                    "threshold": 20,
                    "recent_trades": ["order_123", "order_124"]
                },
                "recommended_action": "봇 자동 중지 권장",
                "auto_executed": True
            }
        }


class BotBehaviorMetrics(BaseModel):
    """봇 동작 메트릭"""

    bot_instance_id: int

    # 거래 빈도
    trades_last_10min: int = 0
    trades_last_1hour: int = 0

    # 손실 통계
    recent_trades_count: int = 0
    losing_trades_count: int = 0
    win_rate: float = 0.0

    # 슬리피지
    avg_slippage_percent: float = 0.0
    max_slippage_percent: float = 0.0

    # API 상태
    api_calls_last_5min: int = 0
    api_errors_last_5min: int = 0
    api_error_rate: float = 0.0

    # 응답성
    last_activity_timestamp: Optional[datetime] = None
    seconds_since_last_activity: int = 0


class MarketAnomalyMetrics(BaseModel):
    """시장 이상 메트릭"""

    symbol: str

    # 가격 변동
    price_change_1min_percent: float = 0.0
    price_change_5min_percent: float = 0.0
    price_change_15min_percent: float = 0.0

    # 거래량
    volume_1min: float = 0.0
    volume_avg_1hour: float = 0.0
    volume_ratio: float = 1.0  # 현재/평균

    # 펀딩 비율 (선물)
    funding_rate: Optional[float] = None
    funding_rate_avg: Optional[float] = None

    # 유동성
    orderbook_depth_bids: float = 0.0
    orderbook_depth_asks: float = 0.0
    orderbook_imbalance: float = 0.0  # (bids - asks) / (bids + asks)


class CircuitBreakerStatus(BaseModel):
    """서킷 브레이커 상태"""

    user_id: int

    # 손실 추적
    daily_pnl: float = 0.0
    total_equity: float = 0.0
    daily_loss_percent: float = 0.0

    # 임계값
    max_daily_loss_percent: float = 10.0

    # 상태
    is_triggered: bool = False
    triggered_at: Optional[datetime] = None
    reason: Optional[str] = None

    # 영향받은 봇들
    stopped_bot_ids: list[int] = Field(default_factory=list)
