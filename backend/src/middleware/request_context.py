"""
Request Context 미들웨어
각 요청에 고유 ID를 부여하고 context에 저장
JWT 디코딩 결과를 캐싱하여 중복 디코딩 방지
"""
import uuid
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.structured_logging import set_request_id, set_user_id, clear_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Request Context 미들웨어
    - 각 요청에 고유한 request_id 생성
    - JWT에서 user_id 추출하여 context에 저장
    - JWT 디코딩 결과를 request.state에 캐싱 (중복 디코딩 방지)
    """

    async def dispatch(self, request: Request, call_next):
        # Request ID 생성 (헤더에 있으면 사용, 없으면 생성)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # JWT 캐싱 초기화 (None = 아직 디코딩 안 함, False = 디코딩 실패)
        request.state.jwt_user_id = None
        request.state.jwt_payload = None
        request.state.jwt_decoded = False

        # JWT에서 user_id 추출 시도 (결과를 캐싱)
        user_id = await self._extract_and_cache_jwt(request)
        if user_id:
            set_user_id(user_id)

        # 요청 처리
        try:
            response = await call_next(request)
            # Response 헤더에 request_id 추가
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Context 정리
            clear_context()

    async def _extract_and_cache_jwt(self, request: Request) -> Optional[int]:
        """
        JWT 토큰에서 user_id 추출 및 request.state에 캐싱

        Returns:
            user_id 또는 None (인증되지 않은 경우)
        """
        try:
            from ..utils.jwt_auth import JWTAuth
            from jose import JWTError

            # Bearer 토큰 추출
            authorization = request.headers.get("Authorization", "")
            token = None

            if authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]

            # 쿠키에서 토큰 추출 (폴백)
            if not token:
                token = request.cookies.get("access_token")

            if not token:
                request.state.jwt_decoded = True  # 토큰 없음으로 표시
                return None

            # JWT 디코딩 (예외 발생하지 않도록 직접 디코딩)
            from jose import jwt
            from ..config import settings

            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )

            user_id = payload.get("user_id")

            # 캐싱
            request.state.jwt_user_id = user_id if isinstance(user_id, int) else None
            request.state.jwt_payload = payload
            request.state.jwt_decoded = True

            return request.state.jwt_user_id

        except Exception:
            # JWT 디코딩 실패 (만료, 잘못된 토큰 등)
            request.state.jwt_decoded = True
            request.state.jwt_user_id = None
            request.state.jwt_payload = None
            return None


def get_cached_user_id(request: Request) -> Optional[int]:
    """
    캐싱된 user_id 반환 (다른 미들웨어/의존성에서 사용)

    Returns:
        캐싱된 user_id 또는 None
    """
    if hasattr(request.state, "jwt_user_id"):
        return request.state.jwt_user_id
    return None


def is_jwt_decoded(request: Request) -> bool:
    """
    JWT 디코딩이 이미 수행되었는지 확인

    Returns:
        True if JWT 디코딩 완료, False otherwise
    """
    return getattr(request.state, "jwt_decoded", False)
