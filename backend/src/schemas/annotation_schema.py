"""
Chart Annotation Schemas

차트 어노테이션 API 요청/응답 스키마
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AnnotationType(str, Enum):
    """어노테이션 유형"""
    NOTE = "note"                    # 텍스트 메모
    HORIZONTAL_LINE = "hline"        # 수평선 (지지/저항선)
    VERTICAL_LINE = "vline"          # 수직선 (이벤트 마커)
    TRENDLINE = "trendline"          # 추세선 (두 점 연결)
    RECTANGLE = "rectangle"          # 사각형 영역
    PRICE_LEVEL = "price_level"      # 가격 수준 (알림 설정 가능)


class AnnotationStyle(BaseModel):
    """어노테이션 스타일 설정"""
    color: Optional[str] = Field(default="#1890ff", description="색상 (hex)")
    line_width: Optional[int] = Field(default=1, ge=1, le=5, alias="lineWidth")
    line_dash: Optional[List[int]] = Field(default=None, alias="lineDash")
    font_size: Optional[int] = Field(default=12, ge=8, le=24, alias="fontSize")
    background_color: Optional[str] = Field(default=None, alias="backgroundColor")
    opacity: Optional[float] = Field(default=1.0, ge=0.1, le=1.0)

    class Config:
        populate_by_name = True


class AnnotationCreateRequest(BaseModel):
    """어노테이션 생성 요청"""
    symbol: str = Field(..., min_length=1, max_length=20, description="심볼 (예: BTCUSDT)")
    annotation_type: AnnotationType = Field(..., description="어노테이션 유형")
    label: Optional[str] = Field(default=None, max_length=100, description="라벨")
    text: Optional[str] = Field(default=None, max_length=1000, description="메모 내용")

    # 시간 위치 (Unix timestamp in seconds)
    timestamp: Optional[int] = Field(default=None, description="시간 위치 (Unix timestamp)")
    start_timestamp: Optional[int] = Field(default=None, description="시작 시간")
    end_timestamp: Optional[int] = Field(default=None, description="끝 시간")

    # 가격 위치
    price: Optional[float] = Field(default=None, gt=0, description="가격 위치")
    start_price: Optional[float] = Field(default=None, gt=0, description="시작 가격")
    end_price: Optional[float] = Field(default=None, gt=0, description="끝 가격")

    # 스타일
    style: Optional[Dict[str, Any]] = Field(default=None, description="스타일 설정")

    # 알림 설정
    alert_enabled: bool = Field(default=False, description="알림 활성화")
    alert_direction: Optional[str] = Field(
        default=None,
        pattern="^(above|below)$",
        description="알림 방향 (above/below)"
    )

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """심볼 대문자 변환"""
        return v.upper().strip()

    @field_validator('annotation_type', mode='before')
    @classmethod
    def validate_annotation_type(cls, v):
        """어노테이션 타입 검증"""
        if isinstance(v, str):
            return AnnotationType(v)
        return v


class AnnotationUpdateRequest(BaseModel):
    """어노테이션 수정 요청"""
    label: Optional[str] = Field(default=None, max_length=100)
    text: Optional[str] = Field(default=None, max_length=1000)

    timestamp: Optional[int] = None
    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None

    price: Optional[float] = Field(default=None, gt=0)
    start_price: Optional[float] = Field(default=None, gt=0)
    end_price: Optional[float] = Field(default=None, gt=0)

    style: Optional[Dict[str, Any]] = None

    alert_enabled: Optional[bool] = None
    alert_direction: Optional[str] = Field(default=None, pattern="^(above|below)$")

    is_active: Optional[bool] = None
    is_locked: Optional[bool] = None


class AnnotationResponse(BaseModel):
    """어노테이션 응답"""
    id: int
    user_id: int
    symbol: str
    annotation_type: str
    label: Optional[str] = None
    text: Optional[str] = None

    # 시간 (Unix timestamp로 변환하여 반환)
    timestamp: Optional[int] = None
    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None

    # 가격
    price: Optional[float] = None
    start_price: Optional[float] = None
    end_price: Optional[float] = None

    # 스타일
    style: Optional[Dict[str, Any]] = None

    # 알림
    alert_enabled: bool = False
    alert_triggered: bool = False
    alert_direction: Optional[str] = None

    # 상태
    is_active: bool = True
    is_locked: bool = False

    # 타임스탬프
    created_at: int  # Unix timestamp
    updated_at: int  # Unix timestamp

    class Config:
        from_attributes = True


class AnnotationListResponse(BaseModel):
    """어노테이션 목록 응답"""
    symbol: str
    annotations: List[AnnotationResponse]
    count: int


class AnnotationDeleteResponse(BaseModel):
    """어노테이션 삭제 응답"""
    success: bool
    message: str
    deleted_id: int
