from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import User
from ..schemas.auth_schema import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UserInfo,
)
from ..utils.auth_cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from ..utils.auth_dependencies import require_admin
from ..utils.exceptions import AuthenticationError, DuplicateResourceError
from ..utils.jwt_auth import JWTAuth, get_current_user_id

router = APIRouter(prefix="/auth", tags=["auth"])



@router.post("/register", response_model=AuthResponse)
async def register(
    payload: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """사용자 회원가입 및 JWT 토큰 발급

    필수 필드:
    - email: 사용자명/ID (4-20자, 영문자/숫자/밑줄(_)/하이픈(-) 허용)
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
    access_token = JWTAuth.create_access_token(
        data={"user_id": user.id, "email": user.email, "role": user.role or "user"}
    )
    refresh_token = JWTAuth.create_refresh_token(
        data={"user_id": user.id, "email": user.email, "role": user.role or "user"}
    )
    set_auth_cookies(response, access_token, refresh_token)

    return AuthResponse(
        user=UserInfo(id=user.id, email=user.email, role=user.role or "user")
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """
    사용자 로그인 및 JWT 토큰 발급

    🔒 보안 기능:
    - Brute Force 방지: 5회 연속 실패 시 15분간 계정 잠금
    - 2FA 지원: TOTP 기반 2단계 인증

    2FA가 활성화된 경우:
    1. 첫 번째 요청: email + password -> requires_2fa: true, user_id 반환
    2. 두 번째 요청: email + password + totp_code -> access_token 반환
    """
    from ..services.login_security import login_security
    from ..services.totp_service import totp_service

    # 🔒 Step 1: 계정 잠금 확인
    (
        is_allowed,
        lockout_message,
        remaining_seconds,
    ) = await login_security.check_login_allowed(payload.email)

    if not is_allowed:
        raise AuthenticationError(lockout_message)

    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalars().first()

    # 사용자가 존재하지 않는 경우
    if not user:
        # 🔒 실패 기록 (사용자 존재 여부를 노출하지 않기 위해 동일한 에러 메시지)
        await login_security.record_failed_attempt(payload.email)
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
        # 🔒 Step 2: 실패 기록 및 잠금 처리
        failed_count, is_locked = await login_security.record_failed_attempt(
            payload.email
        )

        if is_locked:
            raise AuthenticationError(
                "로그인 시도가 너무 많습니다. 15분 후에 다시 시도해주세요."
            )

        remaining_attempts = 5 - failed_count
        if remaining_attempts > 0 and remaining_attempts <= 2:
            raise AuthenticationError(
                f"Invalid email or password (남은 시도: {remaining_attempts}회)"
            )

        raise AuthenticationError("Invalid email or password")

    # 계정 정지 확인
    if not user.is_active:
        raise AuthenticationError("계정이 정지되었습니다. 관리자에게 문의하세요.")

    # 2FA 활성화 확인
    if user.is_2fa_enabled:
        # 2FA 코드가 제출되지 않은 경우
        if not payload.totp_code:
            return AuthResponse(requires_2fa=True, user_id=user.id)

        # 2FA 코드 검증
        secret = totp_service.decrypt_secret(user.totp_secret)
        if not secret or not totp_service.verify_totp(secret, payload.totp_code):
            # 🔒 2FA 실패도 기록
            await login_security.record_failed_attempt(payload.email)
            raise AuthenticationError("유효하지 않은 2FA 코드입니다")

    # 🔒 Step 3: 로그인 성공 - 실패 기록 초기화
    await login_security.record_successful_login(payload.email)

    # JWT 토큰 생성 (user_id + email + role 포함)
    user_data = {"user_id": user.id, "email": user.email, "role": user.role or "user"}

    access_token = JWTAuth.create_access_token(data=user_data)
    refresh_token = JWTAuth.create_refresh_token(data=user_data)
    set_auth_cookies(response, access_token, refresh_token)

    return AuthResponse(
        user=UserInfo(id=user.id, email=user.email, role=user.role or "user")
    )


@router.get("/users")
async def get_users(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),  # SECURITY: 관리자만 접근 가능
):
    """모든 사용자 목록 조회 (관리자 권한 필요)"""
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
        raise AuthenticationError(f"비밀번호 변경 실패: {str(e)}") from e


class RefreshTokenRequest(BaseModel):
    """Refresh Token 요청"""

    refresh_token: str | None = None


@router.post("/refresh")
async def refresh_token(
    response: Response,
    request: Request,
    payload: RefreshTokenRequest | None = None,
):
    """
    Refresh Token을 사용하여 새 Access Token 발급

    🔒 보안 기능:
    - Refresh Token 유효성 검증
    - Access Token 갱신 (1시간 유효)
    - Refresh Token 만료 임박 시 자동 갱신 (남은 시간 1일 미만)

    Args:
        refresh_token: 유효한 Refresh Token

    Returns:
        access_token: 새 Access Token
        refresh_token: 새 Refresh Token (선택적, 만료 임박 시에만)
        token_type: "bearer"
    """
    try:
        refresh_token_value = (payload.refresh_token if payload else None) or request.cookies.get(REFRESH_COOKIE)
        if not refresh_token_value:
            raise AuthenticationError("Refresh token missing")
        new_access, new_refresh = JWTAuth.refresh_access_token(refresh_token_value)

        response_payload = {"ok": True}

        # Refresh Token이 갱신된 경우에만 포함
        if new_refresh:
            refresh_token_value = new_refresh
        set_auth_cookies(response, new_access, refresh_token_value)

        return response_payload

    except Exception as e:
        raise AuthenticationError(f"토큰 갱신 실패: {str(e)}") from e


@router.get("/me")
async def get_me(user_id: int = Depends(get_current_user_id), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise AuthenticationError("사용자를 찾을 수 없습니다")
    return {"id": user.id, "email": user.email, "role": user.role or "user"}


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookies(response)
    return {"ok": True}
