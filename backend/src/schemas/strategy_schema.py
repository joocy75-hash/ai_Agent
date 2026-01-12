from typing import Optional

from pydantic import BaseModel, field_validator

from ..utils.validators import (
    ValidationRules,
    sanitize_html,
    validate_no_sql_injection,
    validate_strategy_name,
    validate_string_length,
)


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    code: Optional[str] = None  # 선택사항으로 변경
    params: Optional[str] = None
    parameters: Optional[dict] = None  # Frontend 호환성
    type: Optional[str] = None  # 전략 유형 (golden_cross, rsi_reversal 등)
    symbol: Optional[str] = None  # 거래 심볼 (BTCUSDT 등)
    timeframe: Optional[str] = None  # 타임프레임 (1h, 4h 등)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """전략 이름 검증: 영문, 숫자, 언더스코어만 허용"""
        return validate_strategy_name(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """설명 검증: XSS 방지 및 길이 제한"""
        if v is None:
            return v
        v = sanitize_html(v)
        return validate_string_length(
            v,
            min_length=0,
            max_length=ValidationRules.MEDIUM_TEXT_MAX_LENGTH,
            field_name="description",
        )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        """코드 검증: SQL Injection 방지 및 길이 제한"""
        if v is None:
            return v
        v = validate_no_sql_injection(v)
        return validate_string_length(
            v,
            min_length=0,
            max_length=ValidationRules.LONG_TEXT_MAX_LENGTH,
            field_name="code",
        )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Optional[str]) -> Optional[str]:
        """파라미터 검증: XSS 방지 및 길이 제한"""
        if v is None:
            return v
        v = sanitize_html(v)
        return validate_string_length(
            v,
            min_length=0,
            max_length=ValidationRules.MEDIUM_TEXT_MAX_LENGTH,
            field_name="params",
        )


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    params: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """전략 이름 검증"""
        if v is None:
            return v
        return validate_strategy_name(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """설명 검증"""
        if v is None:
            return v
        v = sanitize_html(v)
        return validate_string_length(
            v,
            min_length=0,
            max_length=ValidationRules.MEDIUM_TEXT_MAX_LENGTH,
            field_name="description",
        )

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: Optional[str]) -> Optional[str]:
        """코드 검증"""
        if v is None:
            return v
        v = validate_no_sql_injection(v)
        return validate_string_length(
            v,
            min_length=0,
            max_length=ValidationRules.LONG_TEXT_MAX_LENGTH,
            field_name="code",
        )

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: Optional[str]) -> Optional[str]:
        """파라미터 검증"""
        if v is None:
            return v
        v = sanitize_html(v)
        return validate_string_length(
            v,
            min_length=0,
            max_length=ValidationRules.MEDIUM_TEXT_MAX_LENGTH,
            field_name="params",
        )


class StrategySelect(BaseModel):
    strategy_id: int
