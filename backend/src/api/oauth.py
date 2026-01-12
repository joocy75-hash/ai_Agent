"""
OAuth (Google, Kakao) 소셜 로그인 API
"""

import secrets
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database.db import get_session
from ..database.models import User
from ..utils.auth_cookies import set_auth_cookies
from ..utils.jwt_auth import JWTAuth
from ..utils.structured_logging import get_logger

router = APIRouter(prefix="/auth", tags=["oauth"])
logger = get_logger(__name__)

# OAuth 상태 저장소 (실제 환경에서는 Redis 사용 권장)
oauth_states: dict = {}
OAUTH_STATE_TTL_SECONDS = 600


def _cleanup_oauth_states(now: float) -> None:
    """만료된 OAuth 상태 토큰을 정리합니다.

    OAuth 인증 흐름에서 CSRF 방지를 위해 사용되는 state 토큰 중
    TTL(Time To Live)이 만료된 항목들을 oauth_states 딕셔너리에서 제거합니다.
    이 함수는 새로운 OAuth 요청이 들어올 때마다 호출되어 메모리 누수를 방지합니다.

    Args:
        now (float): 현재 시각의 Unix 타임스탬프 (초 단위).
            일반적으로 time.time()의 반환값을 전달합니다.

    Returns:
        None: 이 함수는 반환값이 없습니다. oauth_states 전역 딕셔너리를
            직접 수정합니다.

    Side Effects:
        - oauth_states 전역 딕셔너리에서 만료된 state 토큰을 제거합니다.
        - 만료 기준은 OAUTH_STATE_TTL_SECONDS (기본 600초 = 10분)입니다.

    Note:
        - 이 함수는 스레드 안전하지 않습니다. 프로덕션 환경에서는
          Redis 등의 외부 저장소 사용을 권장합니다.
        - state 토큰의 created_at 필드가 없는 경우 0으로 처리되어
          즉시 만료된 것으로 간주됩니다.

    Example:
        >>> import time
        >>> _cleanup_oauth_states(time.time())
    """
    expired = [
        state
        for state, data in oauth_states.items()
        if now - data.get("created_at", 0) > OAUTH_STATE_TTL_SECONDS
    ]
    for state in expired:
        oauth_states.pop(state, None)


# ===== Google OAuth =====

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google/login")
async def google_login():
    """Google OAuth 로그인 시작"""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=503, detail="Google OAuth가 설정되지 않았습니다"
        )

    # CSRF 방지를 위한 state 생성
    state = secrets.token_urlsafe(32)
    now = time.time()
    _cleanup_oauth_states(now)
    oauth_states[state] = {"provider": "google", "created_at": now}

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",  # 항상 계정 선택 화면 표시
    }

    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Google OAuth 콜백 처리"""
    frontend_url = settings.frontend_url

    # 에러 처리
    if error:
        logger.error("google_oauth_error", f"OAuth error: {error}")
        return RedirectResponse(url=f"{frontend_url}/login?error=google_auth_failed")

    # State 검증
    now = time.time()
    _cleanup_oauth_states(now)
    if not state or state not in oauth_states:
        return RedirectResponse(url=f"{frontend_url}/login?error=invalid_state")

    if now - oauth_states[state].get("created_at", 0) > OAUTH_STATE_TTL_SECONDS:
        del oauth_states[state]
        return RedirectResponse(url=f"{frontend_url}/login?error=state_expired")

    del oauth_states[state]  # 일회용 state 삭제

    try:
        # Access Token 요청
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

            if token_response.status_code != 200:
                # 보안: 토큰 응답 본문에 민감 정보가 포함될 수 있으므로 상태 코드만 로깅
                try:
                    error_data = token_response.json()
                    error_msg = error_data.get("error", "unknown")
                except Exception:
                    error_msg = "parse_failed"
                logger.error(
                    "google_token_error", f"Token exchange failed (status={token_response.status_code}, error={error_msg})"
                )
                return RedirectResponse(
                    url=f"{frontend_url}/login?error=token_exchange_failed"
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            # 사용자 정보 요청
            userinfo_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_response.status_code != 200:
                return RedirectResponse(
                    url=f"{frontend_url}/login?error=userinfo_failed"
                )

            userinfo = userinfo_response.json()

        # 사용자 정보 추출
        google_id = userinfo.get("id")
        email = userinfo.get("email")
        name = userinfo.get("name")
        picture = userinfo.get("picture")

        if not email:
            return RedirectResponse(url=f"{frontend_url}/login?error=email_required")

        # 기존 사용자 확인 (이메일 또는 OAuth ID)
        result = await session.execute(
            select(User).where(
                (User.email == email)
                | ((User.oauth_provider == "google") & (User.oauth_id == google_id))
            )
        )
        user = result.scalars().first()

        if user:
            # 기존 사용자: OAuth 정보 업데이트
            if not user.oauth_provider:
                # 일반 계정을 Google 계정과 연결
                user.oauth_provider = "google"
                user.oauth_id = google_id
                user.profile_image = picture
            elif user.oauth_provider == "google":
                # Google 계정 정보 업데이트
                user.profile_image = picture
                if not user.name and name:
                    user.name = name
        else:
            # 새 사용자 생성
            user = User(
                email=email,
                name=name,
                oauth_provider="google",
                oauth_id=google_id,
                profile_image=picture,
                password_hash=None,  # 소셜 로그인 사용자는 비밀번호 없음
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)

        # JWT 토큰 생성 및 쿠키 설정
        user_data = {"user_id": user.id, "email": user.email, "role": user.role or "user"}
        access_token = JWTAuth.create_access_token(data=user_data)
        refresh_token = JWTAuth.create_refresh_token(data=user_data)

        logger.info("google_login_success", f"User {user.email} logged in via Google")

        # 프론트엔드로 토큰과 함께 리다이렉트
        response = RedirectResponse(url=f"{frontend_url}/oauth/callback?provider=google")
        set_auth_cookies(response, access_token, refresh_token)
        return response

    except Exception as e:
        logger.error("google_oauth_exception", f"Exception: {str(e)}")
        return RedirectResponse(url=f"{frontend_url}/login?error=server_error")


# ===== Kakao OAuth =====

KAKAO_AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USERINFO_URL = "https://kapi.kakao.com/v2/user/me"


@router.get("/kakao/login")
async def kakao_login():
    """Kakao OAuth 로그인 시작"""
    if not settings.kakao_client_id:
        raise HTTPException(status_code=503, detail="Kakao OAuth가 설정되지 않았습니다")

    # CSRF 방지를 위한 state 생성
    state = secrets.token_urlsafe(32)
    now = time.time()
    _cleanup_oauth_states(now)
    oauth_states[state] = {"provider": "kakao", "created_at": now}

    params = {
        "client_id": settings.kakao_client_id,
        "redirect_uri": settings.kakao_redirect_uri,
        "response_type": "code",
        "scope": "profile_nickname profile_image account_email",
        "state": state,
    }

    auth_url = f"{KAKAO_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/kakao/callback")
async def kakao_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Kakao OAuth 콜백 처리"""
    frontend_url = settings.frontend_url

    # 에러 처리
    if error:
        logger.error("kakao_oauth_error", f"OAuth error: {error}")
        return RedirectResponse(url=f"{frontend_url}/login?error=kakao_auth_failed")

    # State 검증
    now = time.time()
    _cleanup_oauth_states(now)
    if not state or state not in oauth_states:
        return RedirectResponse(url=f"{frontend_url}/login?error=invalid_state")

    if now - oauth_states[state].get("created_at", 0) > OAUTH_STATE_TTL_SECONDS:
        del oauth_states[state]
        return RedirectResponse(url=f"{frontend_url}/login?error=state_expired")

    del oauth_states[state]  # 일회용 state 삭제

    try:
        # Access Token 요청
        async with httpx.AsyncClient() as client:
            token_data = {
                "grant_type": "authorization_code",
                "client_id": settings.kakao_client_id,
                "redirect_uri": settings.kakao_redirect_uri,
                "code": code,
            }

            # Client Secret이 있으면 추가
            if settings.kakao_client_secret:
                token_data["client_secret"] = settings.kakao_client_secret

            token_response = await client.post(
                KAKAO_TOKEN_URL,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_response.status_code != 200:
                # 보안: 토큰 응답 본문에 민감 정보가 포함될 수 있으므로 상태 코드만 로깅
                try:
                    error_data = token_response.json()
                    error_msg = error_data.get("error", "unknown")
                except Exception:
                    error_msg = "parse_failed"
                logger.error("kakao_token_error", f"Token exchange failed (status={token_response.status_code}, error={error_msg})")
                return RedirectResponse(
                    url=f"{frontend_url}/login?error=token_exchange_failed"
                )

            token_result = token_response.json()
            access_token = token_result.get("access_token")

            # 사용자 정보 요청
            userinfo_response = await client.get(
                KAKAO_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if userinfo_response.status_code != 200:
                return RedirectResponse(
                    url=f"{frontend_url}/login?error=userinfo_failed"
                )

            userinfo = userinfo_response.json()

        # 사용자 정보 추출
        kakao_id = str(userinfo.get("id"))
        kakao_account = userinfo.get("kakao_account", {})
        profile = kakao_account.get("profile", {})

        email = kakao_account.get("email")
        name = profile.get("nickname")
        picture = profile.get("profile_image_url")

        # 이메일이 없는 경우 임시 이메일 생성
        if not email:
            email = f"kakao_{kakao_id}@kakao.local"

        # 기존 사용자 확인 (이메일 또는 OAuth ID)
        result = await session.execute(
            select(User).where(
                (User.email == email)
                | ((User.oauth_provider == "kakao") & (User.oauth_id == kakao_id))
            )
        )
        user = result.scalars().first()

        if user:
            # 기존 사용자: OAuth 정보 업데이트
            if not user.oauth_provider:
                # 일반 계정을 Kakao 계정과 연결
                user.oauth_provider = "kakao"
                user.oauth_id = kakao_id
                user.profile_image = picture
            elif user.oauth_provider == "kakao":
                # Kakao 계정 정보 업데이트
                user.profile_image = picture
                if not user.name and name:
                    user.name = name
        else:
            # 새 사용자 생성
            user = User(
                email=email,
                name=name,
                oauth_provider="kakao",
                oauth_id=kakao_id,
                profile_image=picture,
                password_hash=None,  # 소셜 로그인 사용자는 비밀번호 없음
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)

        # JWT 토큰 생성 및 쿠키 설정
        user_data = {"user_id": user.id, "email": user.email, "role": user.role or "user"}
        access_token = JWTAuth.create_access_token(data=user_data)
        refresh_token = JWTAuth.create_refresh_token(data=user_data)

        logger.info("kakao_login_success", f"User {user.email} logged in via Kakao")

        # 프론트엔드로 토큰과 함께 리다이렉트
        response = RedirectResponse(url=f"{frontend_url}/oauth/callback?provider=kakao")
        set_auth_cookies(response, access_token, refresh_token)
        return response

    except Exception as e:
        logger.error("kakao_oauth_exception", f"Exception: {str(e)}")
        return RedirectResponse(url=f"{frontend_url}/login?error=server_error")


# ===== OAuth 상태 확인 API =====


@router.get("/oauth/status")
async def oauth_status():
    """OAuth 제공자 활성화 상태 확인"""
    return {
        "google": {
            "enabled": bool(settings.google_client_id),
            "login_url": "/auth/google/login" if settings.google_client_id else None,
        },
        "kakao": {
            "enabled": bool(settings.kakao_client_id),
            "login_url": "/auth/kakao/login" if settings.kakao_client_id else None,
        },
    }
