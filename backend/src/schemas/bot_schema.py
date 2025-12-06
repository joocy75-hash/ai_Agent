from pydantic import BaseModel, field_validator, Field
from typing import Optional


class BotStartRequest(BaseModel):
    strategy_id: int = Field(..., gt=0, description="전략 ID (양수)")

    @field_validator('strategy_id')
    @classmethod
    def validate_strategy_id(cls, v: int) -> int:
        """전략 ID 검증"""
        if v <= 0:
            raise ValueError("strategy_id must be a positive integer")
        if v > 1000000:  # 현실적인 상한선
            raise ValueError("strategy_id is too large")
        return v


class BotStatusResponse(BaseModel):
    user_id: int
    strategy_id: Optional[int] = None
    is_running: bool
    message: Optional[str] = None
