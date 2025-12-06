"""
Request Context 미들웨어
각 요청에 고유 ID를 부여하고 context에 저장
"""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from ..utils.structured_logging import set_request_id, set_user_id, clear_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Request Context 미들웨어
    - 각 요청에 고유한 request_id 생성
    - JWT에서 user_id 추출하여 context에 저장
    """

    async def dispatch(self, request: Request, call_next):
        # Request ID 생성 (헤더에 있으면 사용, 없으면 생성)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        # JWT에서 user_id 추출 시도
        try:
            from ..utils.jwt_auth import JWTAuth

            authorization = request.headers.get("Authorization", "")
            if authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
                payload = JWTAuth.decode_token(token)
                user_id = payload.get("user_id")
                if user_id:
                    set_user_id(user_id)
        except Exception:
            # JWT 디코딩 실패는 무시 (인증 미들웨어에서 처리)
            pass

        # 요청 처리
        try:
            response = await call_next(request)
            # Response 헤더에 request_id 추가
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Context 정리
            clear_context()
