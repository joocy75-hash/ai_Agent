from pydantic import BaseModel, field_validator
from typing import Optional
from ..utils.validators import validate_string_length, sanitize_html


class OrderSubmit(BaseModel):
    symbol: str
    side: str
    leverage: int
    qty: float
    price_type: str = "market"
    limit_price: Optional[float] = None  # 지정가 주문 시 사용

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """거래 심볼 검증"""
        v = v.upper().strip()
        # 기본 형식 검증: 알파벳과 숫자, 하이픈, 언더스코어만 허용
        if not v or len(v) > 20:
            raise ValueError("Symbol must be between 1 and 20 characters")
        v = sanitize_html(v)
        return v

    @field_validator('side')
    @classmethod
    def validate_side(cls, v: str) -> str:
        """매수/매도 방향 검증"""
        allowed_sides = {'buy', 'sell', 'long', 'short'}
        v = v.lower().strip()
        if v not in allowed_sides:
            raise ValueError(f"Side must be one of: {', '.join(allowed_sides)}")
        return v

    @field_validator('leverage')
    @classmethod
    def validate_leverage(cls, v: int) -> int:
        """레버리지 검증"""
        if v < 1 or v > 125:
            raise ValueError("Leverage must be between 1 and 125")
        return v

    @field_validator('qty')
    @classmethod
    def validate_qty(cls, v: float) -> float:
        """주문 수량 검증"""
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        if v > 1_000_000:
            raise ValueError("Quantity must not exceed 1,000,000")
        return v

    @field_validator('price_type')
    @classmethod
    def validate_price_type(cls, v: str) -> str:
        """주문 타입 검증"""
        allowed_types = {'market', 'limit'}
        v = v.lower().strip()
        if v not in allowed_types:
            raise ValueError(f"Price type must be one of: {', '.join(allowed_types)}")
        return v


class OrderResponse(BaseModel):
    order_id: str
    status: str
    symbol: str
    side: str
    qty: float
    price: Optional[float] = None
