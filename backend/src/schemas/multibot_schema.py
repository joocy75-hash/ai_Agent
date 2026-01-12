"""
멀티봇 트레이딩 시스템 Pydantic 스키마

관련 문서: docs/MULTI_BOT_IMPLEMENTATION_PLAN.md
관련 모델: database/models.py - BotInstance, TrendBotTemplate
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# ============================================================
# 트렌드봇 템플릿 스키마
# ============================================================


class TrendTemplateResponse(BaseModel):
    """전략 템플릿 응답"""
    id: int
    name: str
    symbol: str
    description: Optional[str] = None
    strategy_type: str
    direction: str  # long/short/both
    leverage: int
    stop_loss_percent: float
    take_profit_percent: float
    min_investment: float
    recommended_investment: Optional[float] = None
    risk_level: str  # low/medium/high

    # 백테스트 결과
    backtest_roi_30d: Optional[float] = None
    backtest_win_rate: Optional[float] = None
    backtest_max_drawdown: Optional[float] = None
    backtest_total_trades: Optional[int] = None

    # 상태
    is_active: bool
    is_featured: bool
    tags: Optional[List[str]] = None

    class Config:
        from_attributes = True


class TrendTemplateListResponse(BaseModel):
    """템플릿 목록 응답"""
    templates: List[TrendTemplateResponse]
    total: int
    featured_count: int


# ============================================================
# 봇 시작/중지 요청 스키마
# ============================================================


class BotStartRequest(BaseModel):
    """봇 시작 요청"""
    template_id: int = Field(..., gt=0, description="템플릿 ID")
    amount: float = Field(..., gt=0, le=1000000, description="투자 금액 (USDT)")
    name: Optional[str] = Field(None, max_length=100, description="봇 이름 (선택)")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v < 10:
            raise ValueError("최소 투자금은 $10입니다")
        return round(v, 2)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) > 100:
                raise ValueError("봇 이름은 100자 이내여야 합니다")
        return v


class BotStopRequest(BaseModel):
    """봇 중지 요청"""
    bot_id: int = Field(..., gt=0, description="봇 인스턴스 ID")
    close_positions: bool = Field(
        default=False,
        description="True면 포지션도 청산"
    )


# ============================================================
# 봇 인스턴스 응답 스키마
# ============================================================


class BotInstanceResponse(BaseModel):
    """봇 인스턴스 응답"""
    id: int
    name: str
    symbol: str

    # 템플릿 정보
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    strategy_type: Optional[str] = None

    # 투자 정보
    allocated_amount: float
    leverage: int

    # 수익 정보
    current_pnl: float
    current_pnl_percent: float
    total_trades: int
    winning_trades: int
    win_rate: float

    # 상태
    is_running: bool
    last_error: Optional[str] = None
    last_signal_at: Optional[datetime] = None

    # 시간
    created_at: datetime
    last_started_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BotInstanceDetailResponse(BotInstanceResponse):
    """봇 인스턴스 상세 응답 (거래 내역 포함)"""
    # 추가 상세 정보
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    direction: Optional[str] = None  # long/short/both

    # 최근 거래 내역 (최대 10개)
    recent_trades: Optional[List[dict]] = None


# ============================================================
# 잔고 관련 스키마
# ============================================================


class BalanceSummaryResponse(BaseModel):
    """잔고 요약 응답"""
    total_balance: float        # 총 잔고 (거래소에서 조회)
    used_amount: float          # 사용 중인 금액 (활성 봇들의 allocated_amount 합계)
    available_amount: float     # 사용 가능 금액
    active_bot_count: int
    max_bot_count: int = 5      # 최대 5개

    # 전체 수익
    total_pnl: float
    total_pnl_percent: float

    # 봇 목록
    bots: List[BotInstanceResponse]


class BalanceCheckRequest(BaseModel):
    """잔고 확인 요청"""
    amount: float = Field(..., gt=0, description="확인할 금액")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v < 10:
            raise ValueError("최소 금액은 $10입니다")
        return round(v, 2)


class BalanceCheckResponse(BaseModel):
    """잔고 확인 응답"""
    requested_amount: float
    available: bool
    current_used: float
    total_balance: float
    after_used: float           # 승인 시 예상 사용량
    message: str


# ============================================================
# API 응답 래퍼
# ============================================================


class MultiBotSuccessResponse(BaseModel):
    """성공 응답"""
    success: bool = True
    message: str
    bot_id: Optional[int] = None
    data: Optional[dict] = None


class MultiBotErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    detail: Optional[str] = None
