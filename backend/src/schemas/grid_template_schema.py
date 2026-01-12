"""
Grid Bot Template Schemas
- 관리자 템플릿 CRUD용 스키마
- 사용자 조회/사용용 스키마
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from ..database.models import GridMode, PositionDirection

# ===== 기본 스키마 =====


class GridTemplateBase(BaseModel):
    """템플릿 기본 필드"""

    name: str = Field(..., min_length=1, max_length=100)
    symbol: str = Field(..., min_length=3, max_length=20)
    direction: PositionDirection
    leverage: int = Field(default=5, ge=1, le=125)

    lower_price: Decimal = Field(..., gt=0)
    upper_price: Decimal = Field(..., gt=0)
    grid_count: int = Field(..., ge=2, le=200)
    grid_mode: GridMode = GridMode.ARITHMETIC

    min_investment: Decimal = Field(..., gt=0)
    recommended_investment: Optional[Decimal] = None

    recommended_period: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("upper_price")
    @classmethod
    def upper_must_be_greater_than_lower(cls, v, info):
        if "lower_price" in info.data and v <= info.data["lower_price"]:
            raise ValueError("upper_price must be greater than lower_price")
        return v

    @field_validator("symbol")
    @classmethod
    def symbol_must_be_uppercase(cls, v):
        return v.upper()


# ===== 관리자용 스키마 =====


class GridTemplateCreate(GridTemplateBase):
    """템플릿 생성 요청 (관리자)"""

    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0


class GridTemplateUpdate(BaseModel):
    """템플릿 수정 요청 (관리자)"""

    name: Optional[str] = None
    lower_price: Optional[Decimal] = None
    upper_price: Optional[Decimal] = None
    grid_count: Optional[int] = None
    grid_mode: Optional[GridMode] = None
    leverage: Optional[int] = None

    min_investment: Optional[Decimal] = None
    recommended_investment: Optional[Decimal] = None

    recommended_period: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None


class BacktestResultSchema(BaseModel):
    """백테스트 결과"""

    roi_30d: Decimal  # 30일 ROI %
    max_drawdown: Decimal  # 최대 낙폭 %
    total_trades: int  # 총 거래 수
    win_rate: Decimal  # 승률 %
    roi_history: List[float]  # 일별 ROI 배열 (30개)

    model_config = {"from_attributes": True}


# ===== 사용자용 스키마 =====


class GridTemplateListItem(BaseModel):
    """템플릿 목록 아이템 (사용자)"""

    id: int
    name: str
    symbol: str
    direction: PositionDirection
    leverage: int

    # 백테스트 결과
    backtest_roi_30d: Optional[float] = None
    backtest_max_drawdown: Optional[float] = None
    roi_chart: Optional[List[float]] = None  # roi_history를 차트용으로 변환

    # 추천 정보
    recommended_period: Optional[str] = None
    min_investment: float

    # 통계
    active_users: int = 0
    total_funds_in_use: float = 0

    # 상태
    is_featured: bool = False

    model_config = {"from_attributes": True}


class GridTemplateDetail(GridTemplateListItem):
    """템플릿 상세 정보 (사용자)"""

    # 추가 필드
    upper_price: float
    lower_price: float
    grid_count: int
    grid_mode: GridMode
    recommended_investment: Optional[float] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

    backtest_total_trades: Optional[int] = None
    backtest_win_rate: Optional[float] = None
    backtest_updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UseTemplateRequest(BaseModel):
    """템플릿 사용 요청 (봇 생성)"""

    investment_amount: Decimal = Field(..., gt=0)
    leverage: Optional[int] = Field(
        default=None, ge=1, le=125
    )  # None이면 템플릿 기본값

    @field_validator("investment_amount")
    @classmethod
    def validate_investment(cls, v):
        if v < 10:  # 최소 $10
            raise ValueError("Minimum investment is $10")
        return v


class UseTemplateResponse(BaseModel):
    """템플릿 사용 응답 (생성된 봇 정보)"""

    bot_instance_id: int
    grid_config_id: int
    message: str = "Bot created successfully from template"


# ===== 관리자 응답용 =====


class GridTemplateAdminDetail(BaseModel):
    """관리자용 상세 정보"""

    id: int
    name: str
    symbol: str
    direction: PositionDirection
    leverage: int

    # 그리드 설정
    lower_price: float
    upper_price: float
    grid_count: int
    grid_mode: GridMode

    # 투자 설정
    min_investment: float
    recommended_investment: Optional[float] = None

    # 백테스트 결과
    backtest_roi_30d: Optional[float] = None
    backtest_max_drawdown: Optional[float] = None
    backtest_total_trades: Optional[int] = None
    backtest_win_rate: Optional[float] = None
    backtest_roi_history: Optional[List[float]] = None
    backtest_updated_at: Optional[datetime] = None

    # 추천 정보
    recommended_period: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

    # 통계
    active_users: int = 0
    total_users: int = 0
    total_funds_in_use: float = 0

    # 상태
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0

    # 관리
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ===== 응답 래퍼 =====


class GridTemplateListResponse(BaseModel):
    """템플릿 목록 응답"""

    success: bool = True
    data: List[GridTemplateListItem]
    total: int


class GridTemplateDetailResponse(BaseModel):
    """템플릿 상세 응답"""

    success: bool = True
    data: GridTemplateDetail
