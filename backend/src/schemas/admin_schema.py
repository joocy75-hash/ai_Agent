from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    """관리자용 사용자 생성 스키마"""

    email: EmailStr
    password: str
    role: str = "user"  # "user" 또는 "admin"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """역할 유효성 검증"""
        if v not in ["user", "admin"]:
            raise ValueError("역할은 'user' 또는 'admin'이어야 합니다")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """비밀번호 최소 요구사항 검증"""
        if len(v) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        return v


class ApiKeyCreate(BaseModel):
    api_key: str
    secret_key: str
    passphrase: Optional[str] = None


class ApiKeyUpdate(BaseModel):
    api_key: Optional[str] = None
    secret_key: Optional[str] = None
    passphrase: Optional[str] = None
