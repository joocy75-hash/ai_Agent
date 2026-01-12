"""
Bitget Market API 요청/응답 스키마
거래 주문 파라미터에 대한 강화된 검증 포함
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class MarketOrderRequest(BaseModel):
    """시장가 주문 요청"""
    symbol: str = Field(..., min_length=6, max_length=20, description="거래쌍 (예: BTCUSDT)")
    side: Literal["buy", "sell"] = Field(..., description="주문 방향")
    size: float = Field(..., gt=0, description="주문 수량 (양수)")
    reduce_only: bool = Field(False, description="포지션 감소 전용")

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """거래쌍 형식 검증"""
        v = v.upper().strip()

        # 기본 형식 검증
        if not v.endswith(('USDT', 'USD', 'USDC')):
            raise ValueError("Symbol must end with USDT, USD, or USDC")

        # 허용되지 않는 문자 검증
        if not v.replace('_', '').isalnum():
            raise ValueError("Symbol contains invalid characters")

        return v

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: float) -> float:
        """주문 수량 검증"""
        if v <= 0:
            raise ValueError("Size must be greater than 0")

        if v > 1000000:  # 비현실적으로 큰 수량 방지
            raise ValueError("Size is too large (max: 1,000,000)")

        # 소수점 자리수 제한 (최대 8자리)
        decimal_places = len(str(v).split('.')[-1]) if '.' in str(v) else 0
        if decimal_places > 8:
            raise ValueError("Size has too many decimal places (max: 8)")

        return v


class LimitOrderRequest(BaseModel):
    """지정가 주문 요청"""
    symbol: str = Field(..., min_length=6, max_length=20, description="거래쌍")
    side: Literal["buy", "sell"] = Field(..., description="주문 방향")
    size: float = Field(..., gt=0, description="주문 수량")
    price: float = Field(..., gt=0, description="지정가")
    reduce_only: bool = Field(False, description="포지션 감소 전용")

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """거래쌍 형식 검증"""
        v = v.upper().strip()

        if not v.endswith(('USDT', 'USD', 'USDC')):
            raise ValueError("Symbol must end with USDT, USD, or USDC")

        if not v.replace('_', '').isalnum():
            raise ValueError("Symbol contains invalid characters")

        return v

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: float) -> float:
        """주문 수량 검증"""
        if v <= 0:
            raise ValueError("Size must be greater than 0")

        if v > 1000000:
            raise ValueError("Size is too large (max: 1,000,000)")

        decimal_places = len(str(v).split('.')[-1]) if '.' in str(v) else 0
        if decimal_places > 8:
            raise ValueError("Size has too many decimal places (max: 8)")

        return v

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        """가격 검증"""
        if v <= 0:
            raise ValueError("Price must be greater than 0")

        if v > 10000000:  # 비현실적으로 높은 가격 방지
            raise ValueError("Price is too high (max: 10,000,000)")

        decimal_places = len(str(v).split('.')[-1]) if '.' in str(v) else 0
        if decimal_places > 8:
            raise ValueError("Price has too many decimal places (max: 8)")

        return v


class ClosePositionRequest(BaseModel):
    """포지션 청산 요청"""
    symbol: str = Field(..., min_length=6, max_length=20, description="거래쌍")
    side: Literal["long", "short"] = Field(..., description="포지션 방향")
    size: Optional[float] = Field(None, gt=0, description="청산 수량 (None이면 전체)")

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """거래쌍 형식 검증"""
        v = v.upper().strip()

        if not v.endswith(('USDT', 'USD', 'USDC')):
            raise ValueError("Symbol must end with USDT, USD, or USDC")

        if not v.replace('_', '').isalnum():
            raise ValueError("Symbol contains invalid characters")

        return v

    @field_validator('size')
    @classmethod
    def validate_size(cls, v: Optional[float]) -> Optional[float]:
        """청산 수량 검증"""
        if v is None:
            return v

        if v <= 0:
            raise ValueError("Size must be greater than 0")

        if v > 1000000:
            raise ValueError("Size is too large (max: 1,000,000)")

        return v


class SetLeverageRequest(BaseModel):
    """레버리지 설정 요청"""
    symbol: str = Field(..., min_length=6, max_length=20, description="거래쌍")
    leverage: int = Field(..., ge=1, le=125, description="레버리지 배수 (1-125)")

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """거래쌍 형식 검증"""
        v = v.upper().strip()

        if not v.endswith(('USDT', 'USD', 'USDC')):
            raise ValueError("Symbol must end with USDT, USD, or USDC")

        if not v.replace('_', '').isalnum():
            raise ValueError("Symbol contains invalid characters")

        return v

    @field_validator('leverage')
    @classmethod
    def validate_leverage(cls, v: int) -> int:
        """레버리지 검증"""
        if not 1 <= v <= 125:
            raise ValueError("Leverage must be between 1 and 125")

        # 권장하지 않는 높은 레버리지 경고 (검증은 통과)
        if v > 50:
            # 로깅만 하고 통과시킴
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"High leverage detected: {v}x (리스크 관리에 주의하세요)")

        return v


class CancelOrderRequest(BaseModel):
    """주문 취소 요청"""
    order_id: str = Field(..., min_length=1, max_length=100, description="주문 ID")
    symbol: str = Field(..., min_length=6, max_length=20, description="거래쌍")

    @field_validator('order_id')
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        """주문 ID 검증"""
        v = v.strip()

        if not v:
            raise ValueError("Order ID cannot be empty")

        # 주문 ID는 숫자 또는 영숫자 조합
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Order ID contains invalid characters")

        return v

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """거래쌍 형식 검증"""
        v = v.upper().strip()

        if not v.endswith(('USDT', 'USD', 'USDC')):
            raise ValueError("Symbol must end with USDT, USD, or USDC")

        if not v.replace('_', '').isalnum():
            raise ValueError("Symbol contains invalid characters")

        return v
