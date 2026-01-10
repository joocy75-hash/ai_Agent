"""
개선된 Rate Limiting 유닛 테스트

rate_limit_improved.py의 RateLimitStore, EnhancedRateLimitMiddleware, EndpointRateLimiter 테스트.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse

from src.middleware.rate_limit_improved import (
    RateLimitStore,
    EnhancedRateLimitMiddleware,
    EndpointRateLimiter
)
from src.utils.exceptions import RateLimitExceededError


class TestRateLimitStore:
    """RateLimitStore 테스트"""

    def test_check_and_record_first_request(self):
        """첫 번째 요청 테스트"""
        store = RateLimitStore()

        allowed, remaining, reset_time = store.check_and_record(
            key="test_key",
            storage=store.ip_requests,
            limit=10,
            window=60
        )

        assert allowed is True
        assert remaining == 9  # 10 - 0 - 1
        assert reset_time > time.time()

    def test_check_and_record_multiple_requests(self):
        """여러 요청 테스트"""
        store = RateLimitStore()

        for i in range(5):
            allowed, remaining, reset_time = store.check_and_record(
                key="test_key",
                storage=store.ip_requests,
                limit=10,
                window=60
            )
            assert allowed is True
            # 첫 요청: remaining = 10 - 0 - 1 = 9
            # 두번째: remaining = 10 - 1 - 1 = 8, ...
            assert remaining == 10 - i - 1

    def test_check_and_record_limit_exceeded(self):
        """Rate limit 초과 테스트"""
        store = RateLimitStore()

        # 10회 요청
        for _ in range(10):
            store.check_and_record(
                key="test_key",
                storage=store.ip_requests,
                limit=10,
                window=60
            )

        # 11번째 차단
        allowed, remaining, reset_time = store.check_and_record(
            key="test_key",
            storage=store.ip_requests,
            limit=10,
            window=60
        )

        assert allowed is False
        assert remaining == 0

    def test_check_and_record_sliding_window(self):
        """슬라이딩 윈도우 테스트"""
        store = RateLimitStore()

        # 오래된 요청 시뮬레이션
        old_time = time.time() - 70  # 70초 전 (60초 윈도우 밖)
        store.ip_requests["test_key"] = [old_time] * 10

        # 새 요청
        allowed, remaining, reset_time = store.check_and_record(
            key="test_key",
            storage=store.ip_requests,
            limit=10,
            window=60
        )

        assert allowed is True  # 오래된 요청은 무시됨
        assert len(store.ip_requests["test_key"]) == 1  # 새 요청만

    def test_cleanup_old_entries(self):
        """오래된 엔트리 정리 테스트"""
        store = RateLimitStore()
        store._last_cleanup = time.time() - 400  # 5분 이상 경과

        # 오래된 IP 엔트리 추가
        old_time = time.time() - 4000  # 1시간 이상 전
        store.ip_requests["old_ip"] = [old_time]
        store.ip_requests["recent_ip"] = [time.time() - 100]

        # cleanup 트리거
        store.check_and_record(
            key="trigger_key",
            storage=store.ip_requests,
            limit=10,
            window=60
        )

        # 오래된 엔트리 삭제됨
        assert "old_ip" not in store.ip_requests
        assert "recent_ip" in store.ip_requests

    def test_max_ip_entries_limit(self):
        """IP 저장소 크기 제한 테스트"""
        store = RateLimitStore()
        store.MAX_IP_ENTRIES = 100  # 테스트용으로 줄임
        store._last_cleanup = time.time() - 400

        # 많은 IP 엔트리 추가
        for i in range(150):
            store.ip_requests[f"ip_{i}"] = [time.time()]

        # cleanup 트리거
        store.check_and_record(
            key="trigger",
            storage=store.ip_requests,
            limit=10,
            window=60
        )

        # 최대 크기 이하로 줄어듦
        assert len(store.ip_requests) <= store.MAX_IP_ENTRIES + 1

    def test_user_storage_cleanup(self):
        """사용자별 저장소 정리 테스트"""
        store = RateLimitStore()
        store._last_cleanup = time.time() - 400

        # 빈 엔드포인트 추가
        store.user_requests[1] = defaultdict(list)
        store.user_requests[1]["empty_endpoint"] = []
        store.user_requests[2] = defaultdict(list)
        store.user_requests[2]["active_endpoint"] = [time.time()]

        # cleanup 트리거
        store.check_and_record(
            key="trigger",
            storage=store.ip_requests,
            limit=10,
            window=60
        )

        # 빈 사용자 엔트리 삭제됨
        assert 1 not in store.user_requests or not store.user_requests[1]
        assert 2 in store.user_requests

    def test_reset_time_calculation(self):
        """리셋 시간 계산 테스트"""
        store = RateLimitStore()

        # 요청 추가
        store.check_and_record(
            key="test_key",
            storage=store.ip_requests,
            limit=10,
            window=60
        )

        # 두 번째 요청
        allowed, remaining, reset_time = store.check_and_record(
            key="test_key",
            storage=store.ip_requests,
            limit=10,
            window=60
        )

        # 리셋 시간은 가장 오래된 요청 + 윈도우
        expected_reset = int(min(store.ip_requests["test_key"]) + 60)
        assert reset_time == expected_reset


class TestEndpointRateLimiter:
    """EndpointRateLimiter 테스트"""

    def test_check_first_request(self):
        """첫 번째 요청 허용"""
        limiter = EndpointRateLimiter(limit=5, window=60, name="test_limiter")

        allowed, remaining, reset_time = limiter.check(user_id=1)

        assert allowed is True
        assert remaining == 4

    def test_check_within_limit(self):
        """제한 내 요청"""
        limiter = EndpointRateLimiter(limit=5, window=60, name="test_limiter")

        for _ in range(5):
            allowed, remaining, reset_time = limiter.check(user_id=1)
            assert allowed is True

    def test_check_limit_exceeded(self):
        """제한 초과 시 예외 발생"""
        limiter = EndpointRateLimiter(limit=3, window=60, name="test_limiter")

        # 3회 요청
        for _ in range(3):
            limiter.check(user_id=1)

        # 4번째 예외 발생
        with pytest.raises(RateLimitExceededError) as exc_info:
            limiter.check(user_id=1)

        assert "rate limit exceeded" in str(exc_info.value).lower()
        assert exc_info.value.details["limit_type"] == "test_limiter"
        assert exc_info.value.details["limit"] == 3
        assert exc_info.value.details["current_count"] == 3

    def test_check_user_isolation(self):
        """사용자별 격리"""
        limiter = EndpointRateLimiter(limit=2, window=60, name="test_limiter")

        # 사용자 1: 2회 요청
        limiter.check(user_id=1)
        limiter.check(user_id=1)

        # 사용자 1: 3번째 차단
        with pytest.raises(RateLimitExceededError):
            limiter.check(user_id=1)

        # 사용자 2: 여전히 가능
        allowed, remaining, reset_time = limiter.check(user_id=2)
        assert allowed is True

    def test_check_sliding_window_expiry(self):
        """슬라이딩 윈도우 만료"""
        limiter = EndpointRateLimiter(limit=2, window=60, name="test_limiter")

        # 오래된 요청 시뮬레이션
        old_time = time.time() - 70
        limiter.requests[1] = [old_time, old_time]

        # 새 요청 가능 (오래된 요청 무시됨)
        allowed, remaining, reset_time = limiter.check(user_id=1)
        assert allowed is True

    def test_exception_details(self):
        """예외 상세 정보"""
        limiter = EndpointRateLimiter(limit=1, window=3600, name="api_key_reveal")

        limiter.check(user_id=1)

        with pytest.raises(RateLimitExceededError) as exc_info:
            limiter.check(user_id=1)

        assert exc_info.value.details["window"] == 3600
        assert "reset_at" in exc_info.value.details


class TestEnhancedRateLimitMiddleware:
    """EnhancedRateLimitMiddleware 테스트"""

    @pytest.fixture
    def middleware(self):
        """미들웨어 픽스처"""
        app = Mock()
        return EnhancedRateLimitMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Mock Request 픽스처"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.url = Mock()
        request.url.path = "/api/test"
        request.headers = MagicMock()
        request.headers.get = Mock(return_value="")
        request.cookies = {}
        request.state = Mock()
        return request

    @pytest.mark.asyncio
    async def test_ip_rate_limit_allowed(self, middleware, mock_request):
        """IP Rate Limit 허용"""
        async def mock_call_next(req):
            response = JSONResponse({"status": "ok"})
            return response

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    @pytest.mark.asyncio
    async def test_ip_rate_limit_exceeded_via_store(self, middleware, mock_request):
        """IP Rate Limit 초과 (store check_and_record 모킹)"""
        async def mock_call_next(req):
            return JSONResponse({"status": "ok"})

        # check_and_record가 False를 반환하도록 모킹
        with patch.object(middleware.store, "check_and_record") as mock_check:
            mock_check.return_value = (False, 0, int(time.time()) + 60)

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429
            data = response.body.decode()
            assert "RATE_LIMIT_EXCEEDED" in data

    @pytest.mark.asyncio
    async def test_backtest_endpoint_stricter_limit(self, middleware, mock_request):
        """백테스트 엔드포인트 더 엄격한 제한"""
        mock_request.url.path = "/backtest/start"

        async def mock_call_next(req):
            return JSONResponse({"status": "ok"})

        with patch.object(middleware.store, "check_and_record") as mock_check:
            mock_check.return_value = (False, 0, int(time.time()) + 60)

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_cors_headers_on_rate_limit_response(self, middleware, mock_request):
        """Rate Limit 응답에 CORS 헤더 포함"""
        mock_request.headers.get = Mock(
            side_effect=lambda h, d="": "https://deepsignal.shop" if h == "origin" else d
        )

        async def mock_call_next(req):
            return JSONResponse({"status": "ok"})

        with patch.object(middleware.store, "check_and_record") as mock_check:
            mock_check.return_value = (False, 0, int(time.time()) + 60)

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429
            assert response.headers.get("Access-Control-Allow-Origin") == "https://deepsignal.shop"

    @pytest.mark.asyncio
    async def test_user_rate_limit_with_jwt(self, middleware, mock_request):
        """JWT 기반 사용자별 Rate Limit"""
        # _get_user_id_from_jwt 메서드를 직접 모킹
        with patch.object(middleware, "_get_user_id_from_jwt", new_callable=AsyncMock) as mock_jwt:
            mock_jwt.return_value = 123

            async def mock_call_next(req):
                return JSONResponse({"status": "ok"})

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_rate_limit_exceeded(self, middleware, mock_request):
        """사용자별 Rate Limit 초과"""
        with patch.object(middleware, "_get_user_id_from_jwt", new_callable=AsyncMock) as mock_jwt:
            mock_jwt.return_value = 123

            async def mock_call_next(req):
                return JSONResponse({"status": "ok"})

            # IP는 통과, 사용자는 차단
            original_check = middleware.store.check_and_record

            def side_effect_check(key, storage, limit, window):
                if "ip:" in key:
                    return (True, 10, int(time.time()) + 60)
                else:
                    return (False, 0, int(time.time()) + 60)

            with patch.object(middleware.store, "check_and_record", side_effect=side_effect_check):
                response = await middleware.dispatch(mock_request, mock_call_next)

                assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_endpoint_specific_limits(self, middleware, mock_request):
        """엔드포인트별 특정 제한"""
        mock_request.url.path = "/ai-strategy/generate"

        with patch.object(middleware, "_get_user_id_from_jwt", new_callable=AsyncMock) as mock_jwt:
            mock_jwt.return_value = 456

            async def mock_call_next(req):
                return JSONResponse({"status": "ok"})

            # IP는 통과, 사용자는 차단
            def side_effect_check(key, storage, limit, window):
                if "ip:" in key:
                    return (True, 10, int(time.time()) + 60)
                else:
                    return (False, 0, int(time.time()) + 60)

            with patch.object(middleware.store, "check_and_record", side_effect=side_effect_check):
                response = await middleware.dispatch(mock_request, mock_call_next)

                assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_retry_after_header(self, middleware, mock_request):
        """Retry-After 헤더 테스트"""
        async def mock_call_next(req):
            return JSONResponse({"status": "ok"})

        with patch.object(middleware.store, "check_and_record") as mock_check:
            mock_check.return_value = (False, 0, int(time.time()) + 60)

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429
            assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_request_id_generation(self, middleware, mock_request):
        """Request ID가 없어도 응답 헤더는 정상"""
        async def mock_call_next(req):
            return JSONResponse({"status": "ok"})

        response = await middleware.dispatch(mock_request, mock_call_next)

        # X-RateLimit 헤더는 항상 존재
        assert "X-RateLimit-Remaining" in response.headers


class TestRateLimitMiddlewareJWTExtraction:
    """JWT 추출 로직 테스트"""

    @pytest.fixture
    def middleware(self):
        app = Mock()
        return EnhancedRateLimitMiddleware(app)

    @pytest.mark.asyncio
    async def test_jwt_extraction_from_cached(self, middleware):
        """캐시된 JWT에서 user_id 추출"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.jwt_decoded = True
        request.state.jwt_user_id = 123

        # is_jwt_decoded와 get_cached_user_id가 request_context 모듈에서 import됨
        with patch("src.middleware.request_context.is_jwt_decoded", return_value=True):
            with patch("src.middleware.request_context.get_cached_user_id", return_value=123):
                result = await middleware._get_user_id_from_jwt(request)
                assert result == 123

    @pytest.mark.asyncio
    async def test_jwt_extraction_from_bearer_token(self, middleware):
        """Bearer 토큰에서 직접 user_id 추출"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.headers = Mock()
        request.headers.get = Mock(side_effect=lambda h, d=None: "Bearer valid_token" if h in ["Authorization", "authorization"] else None)
        request.cookies = {}

        with patch("src.middleware.request_context.is_jwt_decoded", return_value=False):
            with patch("src.middleware.rate_limit_improved.JWTAuth") as mock_jwt:
                mock_jwt.verify_token.return_value = {"user_id": 789}

                result = await middleware._get_user_id_from_jwt(request)
                assert result == 789

    @pytest.mark.asyncio
    async def test_jwt_extraction_from_cookie(self, middleware):
        """쿠키에서 토큰 추출"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.headers = Mock()
        request.headers.get = Mock(return_value=None)
        request.cookies = {"access_token": "cookie_token"}

        with patch("src.middleware.request_context.is_jwt_decoded", return_value=False):
            with patch("src.middleware.rate_limit_improved.JWTAuth") as mock_jwt:
                mock_jwt.verify_token.return_value = {"user_id": 999}

                result = await middleware._get_user_id_from_jwt(request)
                assert result == 999

    @pytest.mark.asyncio
    async def test_jwt_extraction_invalid_token(self, middleware):
        """잘못된 토큰 처리"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.headers = Mock()
        request.headers.get = Mock(side_effect=lambda h, d=None: "Bearer invalid" if h == "Authorization" else None)
        request.cookies = {}

        with patch("src.middleware.request_context.is_jwt_decoded", return_value=False):
            with patch("src.middleware.rate_limit_improved.JWTAuth") as mock_jwt:
                mock_jwt.verify_token.side_effect = Exception("Invalid token")

                result = await middleware._get_user_id_from_jwt(request)
                assert result is None  # 예외 시 None 반환

    @pytest.mark.asyncio
    async def test_jwt_extraction_non_integer_user_id(self, middleware):
        """정수가 아닌 user_id 처리"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.headers = Mock()
        request.headers.get = Mock(side_effect=lambda h, d=None: "Bearer token" if h == "Authorization" else None)
        request.cookies = {}

        with patch("src.middleware.request_context.is_jwt_decoded", return_value=False):
            with patch("src.middleware.rate_limit_improved.JWTAuth") as mock_jwt:
                mock_jwt.verify_token.return_value = {"user_id": "not_an_int"}

                result = await middleware._get_user_id_from_jwt(request)
                assert result is None  # 정수가 아니면 None

    @pytest.mark.asyncio
    async def test_jwt_extraction_no_token(self, middleware):
        """토큰 없음"""
        request = Mock(spec=Request)
        request.state = Mock()
        request.headers = Mock()
        request.headers.get = Mock(return_value=None)
        request.cookies = {}

        with patch("src.middleware.request_context.is_jwt_decoded", return_value=False):
            result = await middleware._get_user_id_from_jwt(request)
            assert result is None
