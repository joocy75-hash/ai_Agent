from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import User
from ..schemas.auth_schema import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from ..utils.jwt_auth import JWTAuth, get_current_user_id
from ..utils.exceptions import DuplicateResourceError, AuthenticationError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_session)
):
    """사용자 회원가입 및 JWT 토큰 발급

    필수 필드:
    - email: 이메일 주소
    - password: 비밀번호 (최소 8자, 대/소문자, 숫자, 특수문자 포함)
    - password_confirm: 비밀번호 확인
    - name: 이름 (2-50자)
    - phone: 전화번호 (10-13자리)
    """
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalars().first():
        raise DuplicateResourceError("User", "email", payload.email)

    # 비밀번호 해싱
    hashed_password = JWTAuth.get_password_hash(payload.password)

    user = User(
        email=payload.email,
        password_hash=hashed_password,
        name=payload.name,
        phone=payload.phone,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # JWT 토큰 생성 (user_id + email + role 포함)
    token = JWTAuth.create_access_token(
        data={"user_id": user.id, "email": user.email, "role": user.role or "user"}
    )

    return TokenResponse(access_token=token, token_type="bearer")


@router.post("/login")
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    """
    사용자 로그인 및 JWT 토큰 발급

    2FA가 활성화된 경우:
    1. 첫 번째 요청: email + password -> requires_2fa: true, user_id 반환
    2. 두 번째 요청: email + password + totp_code -> access_token 반환
    """
    from ..services.totp_service import totp_service

    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalars().first()

    # 사용자가 존재하지 않는 경우
    if not user:
        raise AuthenticationError("Invalid email or password")

    # 소셜 로그인 사용자가 비밀번호로 로그인 시도
    if user.oauth_provider and not user.password_hash:
        provider_name = "Google" if user.oauth_provider == "google" else "카카오"
        raise AuthenticationError(
            f"이 계정은 {provider_name} 소셜 로그인으로 가입되었습니다. "
            f"{provider_name}로 로그인해주세요."
        )

    # 비밀번호 검증
    if not user.password_hash or not JWTAuth.verify_password(
        payload.password, user.password_hash
    ):
        raise AuthenticationError("Invalid email or password")

    # 계정 정지 확인
    if not user.is_active:
        raise AuthenticationError("계정이 정지되었습니다. 관리자에게 문의하세요.")

    # 2FA 활성화 확인
    if user.is_2fa_enabled:
        # 2FA 코드가 제출되지 않은 경우
        if not payload.totp_code:
            return {
                "access_token": "",
                "token_type": "bearer",
                "requires_2fa": True,
                "user_id": user.id,
            }

        # 2FA 코드 검증
        secret = totp_service.decrypt_secret(user.totp_secret)
        if not secret or not totp_service.verify_totp(secret, payload.totp_code):
            raise AuthenticationError("유효하지 않은 2FA 코드입니다")

    # JWT 토큰 생성 (user_id + email + role 포함)
    token = JWTAuth.create_access_token(
        data={"user_id": user.id, "email": user.email, "role": user.role or "user"}
    )

    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/users")
async def get_users(
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id),
):
    """모든 사용자 목록 조회 (인증 필요)"""
    result = await session.execute(select(User))
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            for user in users
        ]
    }


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    사용자 비밀번호 변경 (JWT 인증 필요)

    Args:
        current_password: 현재 비밀번호
        new_password: 새 비밀번호 (최소 8자, 대/소문자, 숫자, 특수문자 포함)

    Returns:
        성공 메시지
    """
    try:
        # 사용자 조회
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("사용자를 찾을 수 없습니다")

        # 현재 비밀번호 확인
        if not JWTAuth.verify_password(payload.current_password, user.password_hash):
            raise AuthenticationError("현재 비밀번호가 일치하지 않습니다")

        # 새 비밀번호와 현재 비밀번호가 같은지 확인
        if payload.current_password == payload.new_password:
            raise AuthenticationError("새 비밀번호는 현재 비밀번호와 달라야 합니다")

        # 새 비밀번호 해시 및 저장
        user.password_hash = JWTAuth.get_password_hash(payload.new_password)
        await session.commit()

        return {"message": "비밀번호가 성공적으로 변경되었습니다"}

    except AuthenticationError:
        raise
    except Exception as e:
        await session.rollback()
        raise AuthenticationError(f"비밀번호 변경 실패: {str(e)}")
