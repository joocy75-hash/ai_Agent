"""
JWT 인증 유틸리티

실사용자 20명 규모에 맞춘 JWT 기반 인증 시스템.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token (optional by default, required endpoints must validate)
security = HTTPBearer(auto_error=False)


class JWTAuth:
    """
    JWT 인증 헬퍼 클래스

    보안 구조:
    - Access Token: 짧은 유효기간 (1시간), API 인증에 사용
    - Refresh Token: 긴 유효기간 (7일), Access Token 갱신에 사용
    """

    # Refresh Token 기본 유효기간 (7일)
    REFRESH_TOKEN_EXPIRES_DAYS = 7

    # Access Token 기본 유효기간 (1시간)
    ACCESS_TOKEN_EXPIRES_HOURS = 1

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        JWT Access Token 생성

        Args:
            data: 토큰에 포함할 데이터 (user_id, email 등)
            expires_delta: 만료 시간 (기본: 설정값 또는 1시간)

        Returns:
            JWT 토큰 문자열
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            # 설정값이 있으면 사용, 없으면 기본 1시간
            if settings.jwt_expires_seconds:
                expire = datetime.now(timezone.utc) + timedelta(
                    seconds=settings.jwt_expires_seconds
                )
            else:
                expire = datetime.now(timezone.utc) + timedelta(
                    hours=JWTAuth.ACCESS_TOKEN_EXPIRES_HOURS
                )

        to_encode.update(
            {
                "exp": expire,
                "type": "access",  # 토큰 타입 명시
            }
        )

        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )

        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        JWT Refresh Token 생성

        Access Token을 갱신하는 데 사용되는 장기 토큰입니다.

        Args:
            data: 토큰에 포함할 데이터 (user_id 필수)
            expires_delta: 만료 시간 (기본: 7일)

        Returns:
            JWT Refresh 토큰 문자열
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=JWTAuth.REFRESH_TOKEN_EXPIRES_DAYS
            )

        to_encode.update(
            {
                "exp": expire,
                "type": "refresh",  # 토큰 타입 명시
            }
        )

        encoded_jwt = jwt.encode(
            to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )

        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> dict:
        """
        JWT 토큰 디코딩

        Args:
            token: JWT 토큰 문자열

        Returns:
            토큰 페이로드 (user_id, email 등)

        Raises:
            HTTPException: 토큰이 유효하지 않은 경우
        """
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def verify_token(token: str) -> dict:
        """
        JWT 토큰 검증 (Rate Limiter 등에서 사용)

        Raises:
            HTTPException: 토큰이 유효하지 않은 경우
        """
        return JWTAuth.decode_token(token)

    @staticmethod
    def decode_refresh_token(token: str) -> dict:
        """
        Refresh Token 디코딩 및 검증

        Args:
            token: JWT Refresh 토큰 문자열

        Returns:
            토큰 페이로드 (user_id 등)

        Raises:
            HTTPException: 토큰이 유효하지 않거나 refresh 타입이 아닌 경우
        """
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )

            # Refresh Token 타입 검증
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type. Refresh token required.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return payload

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def refresh_access_token(refresh_token: str) -> tuple:
        """
        Refresh Token을 사용하여 새 Access Token 발급

        Args:
            refresh_token: 유효한 Refresh Token

        Returns:
            tuple: (new_access_token, new_refresh_token)
            - new_refresh_token은 남은 유효기간이 1일 미만일 때만 갱신

        Raises:
            HTTPException: Refresh Token이 유효하지 않은 경우
        """
        payload = JWTAuth.decode_refresh_token(refresh_token)

        user_id = payload.get("user_id")
        email = payload.get("email")
        role = payload.get("role", "user")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token: missing user_id",
            )

        # 새 Access Token 생성
        new_access_token = JWTAuth.create_access_token(
            data={"user_id": user_id, "email": email, "role": role}
        )

        # Refresh Token 남은 유효기간 확인
        exp_timestamp = payload.get("exp", 0)
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        remaining = exp_datetime - datetime.now(timezone.utc)

        # 남은 유효기간이 1일 미만이면 새 Refresh Token도 발급
        if remaining < timedelta(days=1):
            new_refresh_token = JWTAuth.create_refresh_token(
                data={"user_id": user_id, "email": email, "role": role}
            )
        else:
            new_refresh_token = None  # 기존 토큰 유지

        return new_access_token, new_refresh_token


class TokenData:
    """토큰에서 추출한 사용자 정보"""

    def __init__(self, user_id: int, email: str):
        self.user_id = user_id
        self.email = email


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if credentials is not None:
        return credentials.credentials
    return request.cookies.get("access_token")


def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> int:
    """
    JWT 토큰에서 현재 사용자 ID 추출 (캐싱된 값 우선 사용)

    FastAPI Dependency로 사용:
        @router.get("/me")
        async def get_me(user_id: int = Depends(get_current_user_id)):
            return {"user_id": user_id}

    Args:
        credentials: HTTP Authorization Bearer 토큰

    Returns:
        user_id: 사용자 ID

    Raises:
        HTTPException: 토큰이 유효하지 않거나 user_id가 없는 경우
    """
    # 1. RequestContextMiddleware에서 캐싱된 값 확인
    if hasattr(request.state, "jwt_decoded") and request.state.jwt_decoded:
        user_id = getattr(request.state, "jwt_user_id", None)
        if user_id is not None:
            return user_id
        # 캐싱되었지만 user_id가 None인 경우 (토큰 없거나 무효)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 캐싱되지 않은 경우 직접 디코딩
    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = JWTAuth.decode_token(token)

    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenData:
    """
    JWT 토큰에서 현재 사용자 정보 추출 (캐싱된 값 우선 사용)

    FastAPI Dependency로 사용:
        @router.get("/me")
        async def get_me(current_user: TokenData = Depends(get_current_user)):
            return {
                "user_id": current_user.user_id,
                "email": current_user.email
            }

    Args:
        credentials: HTTP Authorization Bearer 토큰

    Returns:
        TokenData: 사용자 정보 (user_id, email)

    Raises:
        HTTPException: 토큰이 유효하지 않거나 필수 정보가 없는 경우
    """
    # 1. RequestContextMiddleware에서 캐싱된 payload 확인
    if hasattr(request.state, "jwt_decoded") and request.state.jwt_decoded:
        payload = getattr(request.state, "jwt_payload", None)
        if payload:
            user_id = payload.get("user_id")
            email = payload.get("email")
            if user_id is not None and email is not None:
                return TokenData(user_id=user_id, email=email)
        # 캐싱되었지만 정보가 없는 경우
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 캐싱되지 않은 경우 직접 디코딩
    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = JWTAuth.decode_token(token)

    user_id: Optional[int] = payload.get("user_id")
    email: Optional[str] = payload.get("email")

    if user_id is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenData(user_id=user_id, email=email)


# Optional: 선택적 인증 (토큰이 있으면 검증, 없어도 OK)
def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[int]:
    """
    선택적 인증 - 토큰이 있으면 검증, 없으면 None 반환

    공개 + 인증 API 동시 지원 시 사용:
        @router.get("/items")
        async def get_items(user_id: Optional[int] = Depends(get_current_user_optional)):
            if user_id:
                # 로그인 사용자용 응답
            else:
                # 비로그인 사용자용 응답
    """
    try:
        return get_current_user_id(request, credentials)
    except HTTPException:
        return None
