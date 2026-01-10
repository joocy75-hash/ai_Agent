from pydantic import BaseModel, field_validator, Field
from typing import ClassVar, Optional, Set
from ..utils.validators import validate_api_key_format, validate_string_length, ValidationRules


class ApiKeyPayload(BaseModel):
    exchange: str = "bitget"
    api_key: str
    secret_key: str
    passphrase: Optional[str] = None

    # 지원하는 거래소 목록 (ClassVar로 선언하여 Pydantic 필드로 인식되지 않게 함)
    SUPPORTED_EXCHANGES: ClassVar[Set[str]] = {'bitget', 'binance', 'okx', 'bybit', 'gateio'}
    # Passphrase가 필요한 거래소
    PASSPHRASE_REQUIRED: ClassVar[Set[str]] = {'bitget', 'okx'}

    @field_validator('exchange')
    @classmethod
    def validate_exchange(cls, v: str) -> str:
        """거래소 이름 검증"""
        v = v.lower().strip()
        if v not in cls.SUPPORTED_EXCHANGES:
            raise ValueError(f"Exchange must be one of: {', '.join(sorted(cls.SUPPORTED_EXCHANGES))}")
        return v

    @field_validator('api_key', 'secret_key')
    @classmethod
    def validate_keys(cls, v: str) -> str:
        """API 키 형식 검증"""
        return validate_api_key_format(v)

    @field_validator('passphrase')
    @classmethod
    def validate_passphrase(cls, v: Optional[str]) -> Optional[str]:
        """Passphrase 검증 (일부 거래소에서 필요)"""
        if v is None:
            return v
        return validate_string_length(
            v,
            min_length=1,
            max_length=ValidationRules.SHORT_TEXT_MAX_LENGTH,
            field_name="passphrase"
        )


class RiskSettingsRequest(BaseModel):
    """리스크 설정 요청 스키마"""
    daily_loss_limit: float = Field(..., gt=0, le=1000000, description="일일 손실 한도 (USDT)")
    max_leverage: int = Field(..., ge=1, le=100, description="최대 레버리지 (1-100)")
    max_positions: int = Field(..., ge=1, le=50, description="최대 포지션 개수 (1-50)")

    @field_validator('daily_loss_limit')
    @classmethod
    def validate_daily_loss_limit(cls, v: float) -> float:
        """일일 손실 한도 검증"""
        if v <= 0:
            raise ValueError("일일 손실 한도는 0보다 커야 합니다")

        if v > 1000000:
            raise ValueError("일일 손실 한도가 너무 큽니다 (최대: 1,000,000 USDT)")

        # 소수점 2자리까지만 허용
        if round(v, 2) != v:
            raise ValueError("일일 손실 한도는 소수점 2자리까지만 입력 가능합니다")

        return v

    @field_validator('max_leverage')
    @classmethod
    def validate_max_leverage(cls, v: int) -> int:
        """최대 레버리지 검증"""
        if not 1 <= v <= 100:
            raise ValueError("레버리지는 1-100 사이여야 합니다")

        # 높은 레버리지 경고 (검증은 통과)
        if v > 20:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"높은 레버리지 설정됨: {v}x (리스크 관리에 주의하세요)")

        return v

    @field_validator('max_positions')
    @classmethod
    def validate_max_positions(cls, v: int) -> int:
        """최대 포지션 개수 검증"""
        if not 1 <= v <= 50:
            raise ValueError("최대 포지션 개수는 1-50 사이여야 합니다")

        return v


class RiskSettingsResponse(BaseModel):
    """리스크 설정 응답 스키마"""
    daily_loss_limit: float
    max_leverage: int
    max_positions: int
    is_default: bool
    updated_at: Optional[str] = None
