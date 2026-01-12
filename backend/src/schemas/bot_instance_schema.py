"""
다중 봇 시스템 Pydantic 스키마

관련 문서: docs/MULTI_BOT_01_OVERVIEW.md, MULTI_BOT_03_IMPLEMENTATION.md
관련 모델: database/models.py - BotInstance, GridBotConfig, GridOrder
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# ============================================================
# Enum 정의
# ============================================================


class BotTypeEnum(str, Enum):
    """봇 유형"""
    AI_TREND = "ai_trend"
    GRID = "grid"


class GridModeEnum(str, Enum):
    """그리드 간격 모드"""
    ARITHMETIC = "arithmetic"
    GEOMETRIC = "geometric"


class GridOrderStatusEnum(str, Enum):
    """그리드 주문 상태"""
    PENDING = "pending"
    BUY_PLACED = "buy_placed"
    BUY_FILLED = "buy_filled"
    SELL_PLACED = "sell_placed"
    SELL_FILLED = "sell_filled"


# ============================================================
# 봇 인스턴스 스키마
# ============================================================


class BotInstanceCreate(BaseModel):
    """봇 인스턴스 생성 요청"""
    name: str = Field(..., min_length=1, max_length=100, description="봇 이름")
    description: Optional[str] = Field(None, max_length=500, description="봇 설명")
    bot_type: BotTypeEnum = Field(default=BotTypeEnum.AI_TREND, description="봇 유형")
    strategy_id: Optional[int] = Field(None, gt=0, description="전략 ID (AI 봇만 필요)")
    symbol: str = Field(default="BTCUSDT", max_length=20, description="거래 심볼")
    allocation_percent: float = Field(
        default=10.0,
        gt=0,
        le=100,
        description="잔고 할당 비율 (%)"
    )
    max_leverage: int = Field(default=10, ge=1, le=100, description="최대 레버리지")
    max_positions: int = Field(default=3, ge=1, le=20, description="최대 포지션 수")
    stop_loss_percent: Optional[float] = Field(
        default=5.0,
        ge=0,
        le=100,
        description="손절 비율 (%)"
    )
    take_profit_percent: Optional[float] = Field(
        default=10.0,
        ge=0,
        le=100,
        description="익절 비율 (%)"
    )
    telegram_notify: bool = Field(default=True, description="텔레그램 알림 여부")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """봇 이름 검증"""
        v = v.strip()
        if not v:
            raise ValueError("봇 이름은 필수입니다")
        if len(v) > 100:
            raise ValueError("봇 이름은 100자 이내여야 합니다")
        return v

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """심볼 검증"""
        v = v.upper().strip()
        if not v.endswith("USDT"):
            raise ValueError("현재 USDT 마진 거래만 지원합니다 (예: BTCUSDT)")
        return v

    @field_validator('allocation_percent')
    @classmethod
    def validate_allocation(cls, v: float) -> float:
        """할당 비율 검증"""
        if v <= 0 or v > 100:
            raise ValueError("할당 비율은 0% 초과 100% 이하여야 합니다")
        # 소수점 2자리까지만 허용
        return round(v, 2)

    @field_validator('strategy_id')
    @classmethod
    def validate_strategy_id(cls, v: Optional[int], info) -> Optional[int]:
        """전략 ID 검증 (AI 봇인 경우 필수)"""
        # bot_type이 ai_trend인 경우 strategy_id 필수
        # Note: pydantic v2에서는 model_validator를 사용해야 하지만
        # 단순화를 위해 API 레벨에서 추가 검증
        return v


class BotInstanceUpdate(BaseModel):
    """봇 인스턴스 수정 요청 (실행 중이 아닐 때만)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    strategy_id: Optional[int] = Field(None, gt=0)
    symbol: Optional[str] = Field(None, max_length=20)
    allocation_percent: Optional[float] = Field(None, gt=0, le=100)
    max_leverage: Optional[int] = Field(None, ge=1, le=100)
    max_positions: Optional[int] = Field(None, ge=1, le=20)
    stop_loss_percent: Optional[float] = Field(None, ge=0, le=100)
    take_profit_percent: Optional[float] = Field(None, ge=0, le=100)
    telegram_notify: Optional[bool] = None

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.upper().strip()
        if not v.endswith("USDT"):
            raise ValueError("현재 USDT 마진 거래만 지원합니다")
        return v


class BotInstanceResponse(BaseModel):
    """봇 인스턴스 응답"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    bot_type: str
    strategy_id: Optional[int]
    symbol: str
    allocation_percent: float
    max_leverage: int
    max_positions: int
    stop_loss_percent: Optional[float]
    take_profit_percent: Optional[float]
    telegram_notify: bool
    is_running: bool
    is_active: bool
    last_started_at: Optional[datetime]
    last_stopped_at: Optional[datetime]
    last_trade_at: Optional[datetime]
    last_error: Optional[str]
    total_trades: int
    winning_trades: int
    total_pnl: float
    created_at: datetime
    updated_at: datetime

    # 연결된 전략 정보 (선택적)
    strategy_name: Optional[str] = None

    class Config:
        from_attributes = True


class BotInstanceListResponse(BaseModel):
    """봇 목록 응답"""
    bots: List[BotInstanceResponse]
    total_allocation: float  # 현재 사용 중인 총 할당률
    available_allocation: float  # 사용 가능한 할당률
    running_count: int  # 실행 중인 봇 수
    total_count: int  # 전체 봇 수


# ============================================================
# 그리드 봇 스키마
# ============================================================


class GridBotConfigCreate(BaseModel):
    """그리드 봇 설정 생성"""
    lower_price: float = Field(..., gt=0, description="하한가")
    upper_price: float = Field(..., gt=0, description="상한가")
    grid_count: int = Field(default=10, ge=2, le=100, description="그리드 수")
    grid_mode: GridModeEnum = Field(
        default=GridModeEnum.ARITHMETIC,
        description="그리드 모드"
    )
    total_investment: float = Field(..., gt=0, description="총 투자금 (USDT)")
    trigger_price: Optional[float] = Field(None, gt=0, description="트리거 가격")
    stop_upper: Optional[float] = Field(None, gt=0, description="상한 돌파 중지 가격")
    stop_lower: Optional[float] = Field(None, gt=0, description="하한 돌파 중지 가격")

    @field_validator('upper_price')
    @classmethod
    def validate_price_range(cls, v: float, info) -> float:
        """가격 범위 검증"""
        # lower_price가 이미 검증되었다면 비교
        if 'lower_price' in info.data and v <= info.data['lower_price']:
            raise ValueError("상한가는 하한가보다 커야 합니다")
        return v

    @field_validator('total_investment')
    @classmethod
    def validate_investment(cls, v: float) -> float:
        """투자금 검증"""
        if v < 10:
            raise ValueError("최소 투자금은 10 USDT입니다")
        return round(v, 2)


class GridBotConfigResponse(BaseModel):
    """그리드 봇 설정 응답"""
    id: int
    bot_instance_id: int
    lower_price: float
    upper_price: float
    grid_count: int
    grid_mode: str
    total_investment: float
    per_grid_amount: Optional[float]
    trigger_price: Optional[float]
    stop_upper: Optional[float]
    stop_lower: Optional[float]
    current_price: Optional[float]
    active_buy_orders: int
    active_sell_orders: int
    filled_buy_count: int
    filled_sell_count: int
    realized_profit: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GridOrderResponse(BaseModel):
    """그리드 주문 응답"""
    id: int
    grid_index: int
    grid_price: float
    status: str
    buy_order_id: Optional[str]
    sell_order_id: Optional[str]
    buy_filled_price: Optional[float]
    buy_filled_qty: Optional[float]
    buy_filled_at: Optional[datetime]
    sell_filled_price: Optional[float]
    sell_filled_qty: Optional[float]
    sell_filled_at: Optional[datetime]
    profit: float

    class Config:
        from_attributes = True


class GridStatusResponse(BaseModel):
    """그리드 상태 전체 응답"""
    config: GridBotConfigResponse
    grids: List[GridOrderResponse]
    total_profit: float
    active_orders: int


# ============================================================
# 봇 통계 스키마
# ============================================================


class BotStatsResponse(BaseModel):
    """개별 봇 통계"""
    bot_id: int
    bot_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float  # 승률 (%)
    total_pnl: float
    avg_pnl: float
    max_profit: float
    max_loss: float
    running_time_hours: float  # 총 실행 시간


class AllBotsSummaryResponse(BaseModel):
    """전체 봇 통계 요약"""
    total_bots: int
    running_bots: int
    total_allocation: float
    total_pnl: float
    total_trades: int
    overall_win_rate: float
    best_performing_bot: Optional[str]
    worst_performing_bot: Optional[str]


# ============================================================
# API 응답 래퍼
# ============================================================


class SuccessResponse(BaseModel):
    """성공 응답"""
    success: bool = True
    message: str
    bot_id: Optional[int] = None


class ErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = False
    error: str
    detail: Optional[str] = None
