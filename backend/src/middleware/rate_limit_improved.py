"""
개선된 Rate Limiting Middleware

JWT 기반 사용자별 Rate Limiting 및 엔드포인트별 세분화된 설정.
Rate Limit 헤더 추가 지원.
"""
import time
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional, Dict, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import RateLimitConfig
from ..utils.jwt_auth import JWTAuth
from ..utils.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)


class RateLimitStore:
    """Rate Limit 요청 저장소 (메모리 기반)"""

    def __init__(self):
        # IP 기반: ip -> [timestamp, ...]
        self.ip_requests: Dict[str, list] = defaultdict(list)

        # 사용자별: user_id -> endpoint -> [timestamp, ...]
        self.user_requests: Dict[int, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

    def check_and_record(
        self,
        key: str,
        storage: dict,
        limit: int,
        window: int
    ) -> Tuple[bool, int, int]:
        """
        Rate limit 체크 및 요청 기록

        Args:
            key: 구분자 (IP 또는 user_id)
            storage: 저장소
            limit: 허용 횟수
            window: 시간 윈도우 (초)

        Returns:
            (allowed, remaining, reset_time) 튜플
            - allowed: 요청 허용 여부
            - remaining: 남은 요청 수
            - reset_time: Rate limit 리셋 시간 (Unix timestamp)
        """
        now = time.time()
        requests = storage[key]

        # 오래된 요청 제거 (Sliding Window)
        requests = [req_time for req_time in requests if now - req_time < window]
        storage[key] = requests

        # 현재 요청 수
        current_count = len(requests)

        # 리셋 시간 계산
        if requests:
            oldest_request = min(requests)
            reset_time = int(oldest_request + window)
        else:
            reset_time = int(now + window)

        # Rate limit 체크
        if current_count >= limit:
            return False, 0, reset_time

        # 요청 기록
        requests.append(now)
        remaining = limit - current_count - 1

        return True, remaining, reset_time


class EnhancedRateLimitMiddleware(BaseHTTPMiddleware):
    """
    개선된 Rate Limiting Middleware

    기능:
    - IP 기반 기본 Rate Limiting
    - JWT 기반 사용자별 Rate Limiting
    - 엔드포인트별 세분화된 설정
    - Rate Limit 헤더 추가 (X-RateLimit-*)
    """

    # 엔드포인트별 설정 (path -> (limit, window, 이름))
    ENDPOINT_LIMITS = {
        "/backtest/start": (
            RateLimitConfig.USER_BACKTEST_PER_MINUTE,
            RateLimitConfig.WINDOW_MINUTE,
            "backtest_minute"
        ),
        "/order/submit": (
            RateLimitConfig.USER_ORDER_PER_MINUTE,
            RateLimitConfig.WINDOW_MINUTE,
            "order"
        ),
        "/ai-strategy/generate": (
            RateLimitConfig.USER_AI_STRATEGY_PER_HOUR,
            RateLimitConfig.WINDOW_HOUR,
            "ai_strategy"
        ),
    }

    def __init__(self, app):
        super().__init__(app)
        self.store = RateLimitStore()

    async def dispatch(self, request: Request, call_next):
        """Rate limit 체크 및 헤더 추가"""
        client_ip = request.client.host if request.client else "unknown"

        # CORS 헤더를 위한 Origin 추출
        origin = request.headers.get("origin", "")

        # 1. IP 기반 Rate Limiting (기본 보호)
        allowed, remaining, reset_time = await self._check_ip_rate_limit(
            client_ip, request.url.path
        )

        if not allowed:
            return self._create_rate_limit_response(
                message=f"IP rate limit exceeded. Try again after {reset_time - int(time.time())} seconds",
                reset_time=reset_time,
                limit_type="ip",
                origin=origin
            )

        # 2. 사용자별 Rate Limiting (JWT 기반)
        user_id = await self._get_user_id_from_jwt(request)

        if user_id:
            user_allowed, user_remaining, user_reset = await self._check_user_rate_limit(
                user_id, request.url.path
            )

            if not user_allowed:
                return self._create_rate_limit_response(
                    message=f"User rate limit exceeded. Try again after {user_reset - int(time.time())} seconds",
                    reset_time=user_reset,
                    limit_type="user",
                    origin=origin
                )

            # 사용자별 limit이 더 엄격하므로 사용
            remaining = user_remaining
            reset_time = user_reset

        # 요청 처리
        response: Response = await call_next(request)

        # 3. Rate Limit 헤더 추가
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _create_rate_limit_response(
        self,
        message: str,
        reset_time: int,
        limit_type: str,
        origin: str
    ) -> JSONResponse:
        """
        Rate limit 초과 시 CORS 헤더가 포함된 429 응답 생성

        미들웨어에서 예외를 raise하면 FastAPI exception handler에 도달하지 못하므로
        직접 JSONResponse를 반환해야 합니다.
        """
        response = JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": message,
                    "details": {
                        "limit_type": limit_type,
                        "reset_at": reset_time
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                    "request_id": None
                }
            }
        )

        # CORS 헤더 추가 (브라우저에서 에러 응답을 읽을 수 있도록)
        allowed_origins = [
            "https://deepsignal.shop",
            "https://admin.deepsignal.shop",
            "http://localhost:5173",
            "http://localhost:3000"
        ]

        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

        response.headers["X-RateLimit-Remaining"] = "0"
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        response.headers["Retry-After"] = str(reset_time - int(time.time()))

        logger.warning(f"Rate limit exceeded for {limit_type}, reset at {reset_time}")

        return response

    async def _check_ip_rate_limit(
        self, ip: str, path: str
    ) -> Tuple[bool, int, int]:
        """IP 기반 Rate Limiting"""

        # 백테스트는 더 엄격하게
        if "/backtest/start" in path:
            return self.store.check_and_record(
                key=f"ip:{ip}:backtest",
                storage=self.store.ip_requests,
                limit=RateLimitConfig.IP_BACKTEST_PER_MINUTE,
                window=RateLimitConfig.WINDOW_MINUTE
            )

        # 일반 API
        return self.store.check_and_record(
            key=f"ip:{ip}:general",
            storage=self.store.ip_requests,
            limit=RateLimitConfig.IP_GENERAL_PER_MINUTE,
            window=RateLimitConfig.WINDOW_MINUTE
        )

    async def _check_user_rate_limit(
        self, user_id: int, path: str
    ) -> Tuple[bool, int, int]:
        """사용자별 Rate Limiting"""

        # 특정 엔드포인트 설정 확인
        for endpoint_path, (limit, window, name) in self.ENDPOINT_LIMITS.items():
            if endpoint_path in path:
                user_storage = self.store.user_requests[user_id]
                return self.store.check_and_record(
                    key=name,
                    storage=user_storage,
                    limit=limit,
                    window=window
                )

        # 기본 설정
        user_storage = self.store.user_requests[user_id]
        return self.store.check_and_record(
            key="general",
            storage=user_storage,
            limit=RateLimitConfig.USER_GENERAL_PER_MINUTE,
            window=RateLimitConfig.WINDOW_MINUTE
        )

    async def _get_user_id_from_jwt(self, request: Request) -> Optional[int]:
        """
        JWT 토큰에서 user_id 추출

        Returns:
            user_id 또는 None (인증되지 않은 경우)
        """
        try:
            # Authorization 헤더에서 토큰 추출
            auth_header = request.headers.get("Authorization") or request.headers.get("authorization")

            token = None
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]  # "Bearer " 제거
            if not token:
                token = request.cookies.get("access_token")
            if not token:
                return None

            # JWT 검증 및 디코딩
            payload = JWTAuth.verify_token(token)
            user_id = payload.get("user_id")

            return user_id if isinstance(user_id, int) else None

        except Exception as e:
            logger.debug(f"Failed to extract user_id from JWT: {e}")
            return None


# 특정 엔드포인트용 Rate Limiter 데코레이터
class EndpointRateLimiter:
    """
    특정 엔드포인트에 적용할 수 있는 Rate Limiter

    사용 예:
        limiter = EndpointRateLimiter(limit=3, window=3600)
        @limiter.check(user_id)
        async def reveal_api_keys(...):
            ...
    """

    def __init__(self, limit: int, window: int, name: str):
        self.limit = limit
        self.window = window
        self.name = name
        self.requests: Dict[int, list] = defaultdict(list)

    def check(self, user_id: int) -> Tuple[bool, int, int]:
        """
        Rate limit 체크

        Args:
            user_id: 사용자 ID

        Returns:
            (allowed, remaining, reset_time)

        Raises:
            RateLimitExceededError: Rate limit 초과 시
        """
        now = time.time()
        requests = self.requests[user_id]

        # 오래된 요청 제거
        requests = [req_time for req_time in requests if now - req_time < self.window]
        self.requests[user_id] = requests

        current_count = len(requests)

        # 리셋 시간
        if requests:
            oldest_request = min(requests)
            reset_time = int(oldest_request + self.window)
        else:
            reset_time = int(now + self.window)

        # Rate limit 체크
        if current_count >= self.limit:
            wait_seconds = reset_time - int(now)
            raise RateLimitExceededError(
                f"{self.name.replace('_', ' ').title()} rate limit exceeded. "
                f"Limit: {self.limit} per {self.window // 60} minutes. "
                f"Try again in {wait_seconds} seconds.",
                details={
                    "limit_type": self.name,
                    "limit": self.limit,
                    "window": self.window,
                    "reset_at": reset_time,
                    "current_count": current_count
                }
            )

        # 요청 기록
        requests.append(now)
        remaining = self.limit - current_count - 1

        return True, remaining, reset_time


# 전역 Rate Limiter 인스턴스
api_key_reveal_limiter = EndpointRateLimiter(
    limit=RateLimitConfig.USER_API_KEY_REVEAL_PER_HOUR,
    window=RateLimitConfig.WINDOW_HOUR,
    name="api_key_reveal"
)

ai_strategy_limiter = EndpointRateLimiter(
    limit=RateLimitConfig.USER_AI_STRATEGY_PER_HOUR,
    window=RateLimitConfig.WINDOW_HOUR,
    name="ai_strategy_generation"
)

# DeepSeek API Rate Limiters (Issue #4 - 비용 제어)
deepseek_limiter_minute = EndpointRateLimiter(
    limit=RateLimitConfig.USER_DEEPSEEK_PER_MINUTE,
    window=RateLimitConfig.WINDOW_MINUTE,
    name="deepseek_per_minute"
)

deepseek_limiter_hour = EndpointRateLimiter(
    limit=RateLimitConfig.USER_DEEPSEEK_PER_HOUR,
    window=RateLimitConfig.WINDOW_HOUR,
    name="deepseek_per_hour"
)

deepseek_limiter_day = EndpointRateLimiter(
    limit=RateLimitConfig.USER_DEEPSEEK_PER_DAY,
    window=RateLimitConfig.WINDOW_DAY,
    name="deepseek_per_day"
)
