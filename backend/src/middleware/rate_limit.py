"""
Rate Limiting Middleware

사용자별 API 요청 제한을 위한 미들웨어.
20명 규모에 맞춰 적절한 제한 설정.
Redis 기반 분산 Rate Limiting 지원.
"""
import logging
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# Rate Limit 설정
RATE_LIMIT_CONFIG = {
    "default": {"limit": 60, "period": 60},  # 60 req/min
    "backtest": {"limit": 5, "period": 60},  # 5 req/min
    "api_key": {"limit": 3, "period": 3600},  # 3 req/hour
    "anonymous": {"limit": 30, "period": 60},  # 30 req/min
}


class DistributedRateLimiter:
    """
    Redis 기반 분산 Rate Limiter

    분산 환경에서 일관된 Rate Limiting을 제공합니다.
    Redis 연결 실패 시 인메모리 폴백을 사용합니다.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        초기화

        Args:
            redis_url: Redis 연결 URL (None이면 환경변수 사용)
        """
        self._redis_url = redis_url
        self._redis_client = None
        self._memory_storage = defaultdict(list)  # 폴백용 인메모리 저장소
        self._initialized = False

    async def _get_redis(self):
        """Redis 클라이언트 가져오기"""
        if not self._initialized:
            from ..utils.redis_client import get_redis_client
            self._redis_client = await get_redis_client()
            self._initialized = True
        return self._redis_client

    async def is_rate_limited(
        self,
        key: str,
        limit: int,
        period: int
    ) -> tuple[bool, int]:
        """
        Rate Limit 확인

        Args:
            key: Rate limit 키 (예: "user_123", "anon_192.168.1.1")
            limit: 허용 요청 수
            period: 시간 윈도우 (초)

        Returns:
            (제한 여부, retry_after 초) 튜플
        """
        redis = await self._get_redis()

        if redis is not None:
            try:
                return await self._redis_check(redis, key, limit, period)
            except Exception as e:
                logger.warning(f"Redis rate limit check failed: {e}, falling back to in-memory")

        # 인메모리 폴백
        return self._memory_check(key, limit, period)

    async def _redis_check(
        self,
        redis,
        key: str,
        limit: int,
        period: int
    ) -> tuple[bool, int]:
        """Redis 기반 Rate Limit 확인"""
        redis_key = f"rate_limit:{key}"
        now = int(time.time())

        # Lua 스크립트로 원자적 연산
        pipe = redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - period)
        pipe.zadd(redis_key, {str(now): now})
        pipe.zcard(redis_key)
        pipe.expire(redis_key, period)
        results = await pipe.execute()

        count = results[2]

        if count > limit:
            # TTL 확인하여 retry_after 계산
            ttl = await redis.ttl(redis_key)
            retry_after = max(1, ttl) if ttl > 0 else period
            return True, retry_after

        return False, 0

    def _memory_check(
        self,
        key: str,
        limit: int,
        period: int
    ) -> tuple[bool, int]:
        """인메모리 폴백 Rate Limit 확인"""
        now = time.time()
        requests = self._memory_storage[key]

        # 오래된 요청 제거
        requests = [req_time for req_time in requests if now - req_time < period]
        self._memory_storage[key] = requests

        if len(requests) >= limit:
            # 가장 오래된 요청 기준으로 retry_after 계산
            oldest = min(requests) if requests else now
            retry_after = int(period - (now - oldest))
            return True, max(1, retry_after)

        requests.append(now)
        return False, 0

    async def get_remaining(
        self,
        key: str,
        limit: int
    ) -> int:
        """
        남은 요청 수 조회

        Args:
            key: Rate limit 키
            limit: 허용 요청 수

        Returns:
            남은 요청 수
        """
        redis = await self._get_redis()

        if redis is not None:
            try:
                redis_key = f"rate_limit:{key}"
                count = await redis.zcard(redis_key)
                return max(0, limit - count)
            except Exception:
                pass

        # 인메모리 폴백
        count = len(self._memory_storage.get(key, []))
        return max(0, limit - count)


# 싱글톤 인스턴스
distributed_rate_limiter = DistributedRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate Limiter Middleware with Redis support.

    실사용자 20명 기준:
    - 일반 API: 분당 60회
    - 백테스트: 분당 5회

    Rate limit key format:
    - "user_{user_id}" for authenticated requests
    - "anon_{client_ip}" for anonymous requests
    """

    def __init__(self, app, use_distributed: bool = True):
        super().__init__(app)
        self.use_distributed = use_distributed
        self.requests = defaultdict(list)  # 폴백용 인메모리 저장소
        self.backtest_requests = defaultdict(list)

    def _get_user_id_from_request(self, request: Request) -> str:
        """
        Extract user ID from JWT token for accurate per-user rate limiting.

        Args:
            request: FastAPI Request object

        Returns:
            Rate limit key in format:
            - "user_{user_id}" for authenticated requests
            - "anon_{client_ip}" for anonymous requests
        """
        # 1. Check cached user_id from RequestContextMiddleware
        if hasattr(request.state, "jwt_user_id") and request.state.jwt_user_id:
            return f"user_{request.state.jwt_user_id}"

        # 2. Try to extract from Authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                from ..utils.jwt_auth import JWTAuth
                payload = JWTAuth.verify_token(token)
                user_id = payload.get("user_id")
                if user_id:
                    return f"user_{user_id}"
            except Exception:
                logger.warning(f"Invalid JWT token for rate limiting: {request.url.path}")

        # 3. Try cookie-based token
        token = request.cookies.get("access_token")
        if token:
            try:
                from ..utils.jwt_auth import JWTAuth
                payload = JWTAuth.verify_token(token)
                user_id = payload.get("user_id")
                if user_id:
                    return f"user_{user_id}"
            except Exception:
                logger.warning(f"Invalid cookie token for rate limiting: {request.url.path}")

        # 4. Fall back to IP-based limiting for anonymous users
        client_ip = request.client.host if request.client else "unknown"
        return f"anon_{client_ip}"

    async def dispatch(self, request: Request, call_next):
        # Get user-based rate limit key
        rate_limit_key = self._get_user_id_from_request(request)

        # 백테스트 API는 더 엄격하게 제한
        if "/backtest/start" in request.url.path:
            config = RATE_LIMIT_CONFIG["backtest"]
            if self.use_distributed:
                is_limited, retry_after = await distributed_rate_limiter.is_rate_limited(
                    f"{rate_limit_key}:backtest",
                    config["limit"],
                    config["period"]
                )
                if is_limited:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Too many backtest requests. Limit: {config['limit']} per minute",
                        headers={"Retry-After": str(retry_after)}
                    )
            else:
                if not self._check_rate_limit(
                    rate_limit_key,
                    self.backtest_requests,
                    limit=config["limit"],
                    window=config["period"]
                ):
                    raise HTTPException(
                        status_code=429,
                        detail=f"Too many backtest requests. Limit: {config['limit']} per minute",
                        headers={"Retry-After": str(config["period"])}
                    )

        # 일반 API
        else:
            # anonymous 사용자는 더 낮은 제한
            if rate_limit_key.startswith("anon_"):
                config = RATE_LIMIT_CONFIG["anonymous"]
            else:
                config = RATE_LIMIT_CONFIG["default"]

            if self.use_distributed:
                is_limited, retry_after = await distributed_rate_limiter.is_rate_limited(
                    f"{rate_limit_key}:default",
                    config["limit"],
                    config["period"]
                )
                if is_limited:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Too many requests. Limit: {config['limit']} per minute",
                        headers={"Retry-After": str(retry_after)}
                    )
            else:
                if not self._check_rate_limit(
                    rate_limit_key,
                    self.requests,
                    limit=config["limit"],
                    window=config["period"]
                ):
                    raise HTTPException(
                        status_code=429,
                        detail=f"Too many requests. Limit: {config['limit']} per minute",
                        headers={"Retry-After": str(config["period"])}
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
            key: 구분자 (user_{id} or anon_{ip})
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

    Rate limit key format:
    - "user_{user_id}" for authenticated requests
    - "anon_{client_ip}" for anonymous requests
    """

    def __init__(self, app):
        super().__init__(app)
        self.user_requests = defaultdict(lambda: defaultdict(list))

    async def dispatch(self, request: Request, call_next):
        # JWT에서 user_id 추출
        rate_limit_key = self._get_user_id_from_request(request)

        # 사용자별 백테스트 제한: 시간당 10회
        if "/backtest/start" in request.url.path:
            if not self._check_rate_limit(
                rate_limit_key,
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

    def _get_user_id_from_request(self, request: Request) -> str:
        """
        Extract user ID from JWT token for accurate per-user rate limiting.

        Args:
            request: FastAPI Request object

        Returns:
            Rate limit key in format:
            - "user_{user_id}" for authenticated requests
            - "anon_{client_ip}" for anonymous requests
        """
        # 1. Check cached user_id from RequestContextMiddleware
        if hasattr(request.state, "jwt_user_id") and request.state.jwt_user_id:
            return f"user_{request.state.jwt_user_id}"

        # 2. Try to extract from Authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                from ..utils.jwt_auth import JWTAuth
                payload = JWTAuth.verify_token(token)
                user_id = payload.get("user_id")
                if user_id:
                    return f"user_{user_id}"
            except Exception:
                logger.warning(f"Invalid JWT token for rate limiting: {request.url.path}")

        # 3. Try cookie-based token
        token = request.cookies.get("access_token")
        if token:
            try:
                from ..utils.jwt_auth import JWTAuth
                payload = JWTAuth.verify_token(token)
                user_id = payload.get("user_id")
                if user_id:
                    return f"user_{user_id}"
            except Exception:
                logger.warning(f"Invalid cookie token for rate limiting: {request.url.path}")

        # 4. Fall back to IP-based limiting for anonymous users
        client_ip = request.client.host if request.client else "unknown"
        return f"anon_{client_ip}"

    def _check_rate_limit(
        self,
        rate_limit_key: str,
        endpoint: str,
        limit: int,
        window: int
    ) -> bool:
        """사용자별 endpoint Rate limit 체크"""
        now = time.time()
        requests = self.user_requests[rate_limit_key][endpoint]

        # 오래된 요청 제거
        requests = [req_time for req_time in requests if now - req_time < window]
        self.user_requests[rate_limit_key][endpoint] = requests

        if len(requests) >= limit:
            return False

        requests.append(now)
        return True
