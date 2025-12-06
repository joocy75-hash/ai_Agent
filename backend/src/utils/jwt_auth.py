"""
JWT 인증 유틸리티

실사용자 20명 규모에 맞춘 JWT 기반 인증 시스템.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token
security = HTTPBearer()


class JWTAuth:
    """JWT 인증 헬퍼 클래스"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        JWT Access Token 생성

        Args:
            data: 토큰에 포함할 데이터 (user_id, email 등)
            expires_delta: 만료 시간 (기본: 24시간)

        Returns:
            JWT 토큰 문자열
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(seconds=settings.jwt_expires_seconds)

        to_encode.update({"exp": expire})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm
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
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


class TokenData:
    """토큰에서 추출한 사용자 정보"""
    def __init__(self, user_id: int, email: str):
        self.user_id = user_id
        self.email = email


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    """
    JWT 토큰에서 현재 사용자 ID 추출

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
    token = credentials.credentials
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
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    JWT 토큰에서 현재 사용자 정보 추출 (전체)

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
    token = credentials.credentials
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
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
    if credentials is None:
        return None

    try:
        return get_current_user_id(credentials)
    except HTTPException:
        return None
