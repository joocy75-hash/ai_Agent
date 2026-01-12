import re
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from ..utils.validators import validate_password_strength


class RegisterRequest(BaseModel):
    email: str  # username/ID (이메일 형식이 아닌 일반 ID도 허용)
    password: str
    password_confirm: str  # 비밀번호 확인
    name: str  # 이름 (필수)
    phone: str  # 전화번호 (필수)

    @field_validator("email")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """사용자명 검증: 4-20자, 영문자/숫자/밑줄(_)/하이픈(-) 허용"""
        v = v.strip()
        if len(v) < 4:
            raise ValueError("사용자명은 최소 4자 이상이어야 합니다")
        if len(v) > 20:
            raise ValueError("사용자명은 20자를 초과할 수 없습니다")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("사용자명은 영문자, 숫자, 밑줄(_), 하이픈(-)만 사용할 수 있습니다")
        return v

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
    email: str  # username/ID (이메일 형식이 아닌 일반 ID도 허용)
    password: str
    totp_code: Optional[str] = None  # 2FA 코드 (2FA 활성화된 경우 필수)

    @field_validator("email")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """사용자명 검증: 빈 값 체크"""
        v = v.strip()
        if not v:
            raise ValueError("사용자명을 입력해주세요")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    requires_2fa: bool = False  # 2FA 필요 여부
    user_id: Optional[int] = None  # 2FA 검증이 필요한 경우 임시로 전달


class UserInfo(BaseModel):
    id: int
    email: str
    role: str


class AuthResponse(BaseModel):
    user: Optional[UserInfo] = None
    requires_2fa: bool = False
    user_id: Optional[int] = None


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
