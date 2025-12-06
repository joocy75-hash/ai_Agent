"""
Rate Limiting Middleware

사용자별 API 요청 제한을 위한 미들웨어.
20명 규모에 맞춰 적절한 제한 설정.
"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    간단한 메모리 기반 Rate Limiter.

    실사용자 20명 기준:
    - 일반 API: 분당 60회
    - 백테스트: 분당 5회
    """

    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)  # ip -> [timestamp, ...]
        self.backtest_requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host

        # 백테스트 API는 더 엄격하게 제한
        if "/backtest/start" in request.url.path:
            if not self._check_rate_limit(
                client_ip,
                self.backtest_requests,
                limit=5,  # 분당 5회
                window=60
            ):
                raise HTTPException(
                    status_code=429,
                    detail="Too many backtest requests. Limit: 5 per minute"
                )

        # 일반 API
        else:
            if not self._check_rate_limit(
                client_ip,
                self.requests,
                limit=60,  # 분당 60회
                window=60
            ):
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Limit: 60 per minute"
                )

        response = await call_next(request)
        return response

    def _check_rate_limit(
        self,
        key: str,
        storage: dict,
        limit: int,
        window: int
    ) -> bool:
        """
        Rate limit 체크.

        Args:
            key: 구분자 (IP 주소)
            storage: 저장소
            limit: 허용 횟수
            window: 시간 윈도우 (초)

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        requests = storage[key]

        # 오래된 요청 제거
        requests = [req_time for req_time in requests if now - req_time < window]
        storage[key] = requests

        # 제한 체크
        if len(requests) >= limit:
            return False

        # 요청 기록
        requests.append(now)
        return True


# 사용자별 Rate Limiter (JWT 토큰 기반)
class UserRateLimitMiddleware(BaseHTTPMiddleware):
    """
    사용자별 Rate Limiting.
    JWT 토큰에서 user_id 추출하여 사용자별로 제한.
    """

    def __init__(self, app):
        super().__init__(app)
        self.user_requests = defaultdict(lambda: defaultdict(list))

    async def dispatch(self, request: Request, call_next):
        # JWT에서 user_id 추출 (간단한 구현)
        user_id = self._get_user_id(request)

        if user_id:
            # 사용자별 백테스트 제한: 시간당 10회
            if "/backtest/start" in request.url.path:
                if not self._check_rate_limit(
                    user_id,
                    "backtest",
                    limit=10,
                    window=3600
                ):
                    raise HTTPException(
                        status_code=429,
                        detail="Too many backtests. Limit: 10 per hour per user"
                    )

        response = await call_next(request)
        return response

    def _get_user_id(self, request: Request) -> str | None:
        """JWT에서 user_id 추출"""
        # Authorization 헤더에서 추출
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None

        # 간단한 구현 - 실제로는 JWT 디코딩 필요
        # TODO: JWT 토큰 파싱 구현
        return request.client.host  # 임시로 IP 사용

    def _check_rate_limit(
        self,
        user_id: str,
        endpoint: str,
        limit: int,
        window: int
    ) -> bool:
        """사용자별 endpoint Rate limit 체크"""
        now = time.time()
        requests = self.user_requests[user_id][endpoint]

        # 오래된 요청 제거
        requests = [req_time for req_time in requests if now - req_time < window]
        self.user_requests[user_id][endpoint] = requests

        if len(requests) >= limit:
            return False

        requests.append(now)
        return True
