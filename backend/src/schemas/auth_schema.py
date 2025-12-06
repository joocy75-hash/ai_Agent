from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from ..utils.validators import validate_password_strength


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    password_confirm: str  # 비밀번호 확인
    name: str  # 이름 (필수)
    phone: str  # 전화번호 (필수)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """비밀번호 강도 검증: 최소 8자, 대/소문자, 숫자, 특수문자 포함"""
        return validate_password_strength(v)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """이름 검증: 2-50자, 공백 제거"""
        v = v.strip()
        if len(v) < 2:
            raise ValueError("이름은 최소 2자 이상이어야 합니다")
        if len(v) > 50:
            raise ValueError("이름은 50자를 초과할 수 없습니다")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """전화번호 검증: 숫자와 하이픈만 허용, 10-13자"""
        import re

        v = v.strip().replace(" ", "")
        # 숫자와 하이픈만 허용
        if not re.match(r"^[\d\-]+$", v):
            raise ValueError("전화번호는 숫자와 하이픈(-)만 포함할 수 있습니다")
        # 숫자만 추출하여 길이 확인
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10 or len(digits) > 13:
            raise ValueError("올바른 전화번호 형식이 아닙니다 (10-13자리)")
        return v

    @model_validator(mode="after")
    def check_passwords_match(self) -> "RegisterRequest":
        """비밀번호와 비밀번호 확인이 일치하는지 검증"""
        if self.password != self.password_confirm:
            raise ValueError("비밀번호가 일치하지 않습니다")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None  # 2FA 코드 (2FA 활성화된 경우 필수)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_2fa: bool = False  # 2FA 필요 여부
    user_id: Optional[int] = None  # 2FA 검증이 필요한 경우 임시로 전달


class Login2FARequest(BaseModel):
    """2FA 로그인 완료 요청"""

    user_id: int
    totp_code: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """비밀번호 강도 검증: 최소 8자, 대/소문자, 숫자, 특수문자 포함"""
        return validate_password_strength(v)
