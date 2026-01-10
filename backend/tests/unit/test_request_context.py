"""
Request Context 미들웨어 유닛 테스트

JWT 캐싱 및 Request ID 생성 기능 테스트.
"""
import pytest
import os
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import jwt

from src.middleware.request_context import (
    RequestContextMiddleware,
    get_cached_user_id,
    is_jwt_decoded
)


# 테스트용 JWT 설정
TEST_SECRET = "test-secret-key"
TEST_ALGORITHM = "HS256"


def create_test_token(user_id: int, expired: bool = False) -> str:
    """테스트용 JWT 토큰 생성"""
    import time
    payload = {
        "user_id": user_id,
        "exp": time.time() + (-3600 if expired else 3600),
        "iat": time.time()
    }
    return jwt.encode(payload, TEST_SECRET, algorithm=TEST_ALGORITHM)


@pytest.fixture
def mock_settings():
    """테스트용 settings 모킹"""
    with patch("src.config.settings") as mock:
        mock.jwt_secret = TEST_SECRET
        mock.jwt_algorithm = TEST_ALGORITHM
        yield mock


@pytest.fixture
def test_app():
    """테스트용 FastAPI 앱"""
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {
            "user_id": get_cached_user_id(request),
            "jwt_decoded": is_jwt_decoded(request)
        }

    @app.get("/check-state")
    async def check_state(request: Request):
        return {
            "jwt_user_id": getattr(request.state, "jwt_user_id", "NOT_SET"),
            "jwt_payload": getattr(request.state, "jwt_payload", "NOT_SET"),
            "jwt_decoded": getattr(request.state, "jwt_decoded", "NOT_SET")
        }

    return app


class TestRequestContextMiddleware:
    """RequestContextMiddleware 테스트"""

    def test_request_id_generation(self, test_app, mock_settings):
        """Request ID 자동 생성 테스트"""
        client = TestClient(test_app)
        response = client.get("/test")

        # X-Request-ID 헤더가 응답에 포함되어야 함
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 36  # UUID 길이

    def test_request_id_passthrough(self, test_app, mock_settings):
        """클라이언트가 제공한 Request ID 사용 테스트"""
        client = TestClient(test_app)
        custom_request_id = "custom-request-id-12345"

        response = client.get(
            "/test",
            headers={"X-Request-ID": custom_request_id}
        )

        assert response.headers["X-Request-ID"] == custom_request_id

    def test_jwt_caching_with_bearer_token(self, test_app, mock_settings):
        """Bearer 토큰으로 JWT 캐싱 테스트"""
        client = TestClient(test_app)
        token = create_test_token(user_id=123)

        response = client.get(
            "/test",
            headers={"Authorization": f"Bearer {token}"}
        )

        data = response.json()
        assert data["user_id"] == 123
        assert data["jwt_decoded"] is True

    def test_jwt_caching_with_cookie(self, test_app, mock_settings):
        """쿠키에서 JWT 추출 테스트"""
        client = TestClient(test_app)
        token = create_test_token(user_id=456)

        response = client.get(
            "/test",
            cookies={"access_token": token}
        )

        data = response.json()
        assert data["user_id"] == 456
        assert data["jwt_decoded"] is True

    def test_bearer_token_priority_over_cookie(self, test_app, mock_settings):
        """Bearer 토큰이 쿠키보다 우선 테스트"""
        client = TestClient(test_app)
        bearer_token = create_test_token(user_id=111)
        cookie_token = create_test_token(user_id=222)

        response = client.get(
            "/test",
            headers={"Authorization": f"Bearer {bearer_token}"},
            cookies={"access_token": cookie_token}
        )

        data = response.json()
        # Bearer 토큰의 user_id가 사용되어야 함
        assert data["user_id"] == 111

    def test_no_token_provided(self, test_app, mock_settings):
        """토큰 없이 요청 테스트"""
        client = TestClient(test_app)
        response = client.get("/test")

        data = response.json()
        assert data["user_id"] is None
        assert data["jwt_decoded"] is True  # 디코딩 시도는 함

    def test_invalid_token(self, test_app, mock_settings):
        """잘못된 토큰 테스트"""
        client = TestClient(test_app)

        response = client.get(
            "/test",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        data = response.json()
        assert data["user_id"] is None
        assert data["jwt_decoded"] is True

    def test_expired_token(self, test_app, mock_settings):
        """만료된 토큰 테스트"""
        client = TestClient(test_app)
        expired_token = create_test_token(user_id=789, expired=True)

        response = client.get(
            "/test",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        data = response.json()
        assert data["user_id"] is None  # 만료로 인해 None
        assert data["jwt_decoded"] is True

    def test_state_initialization(self, test_app, mock_settings):
        """request.state 초기화 테스트"""
        client = TestClient(test_app)
        response = client.get("/check-state")

        data = response.json()
        # 토큰 없이 요청했으므로
        assert data["jwt_user_id"] is None
        assert data["jwt_payload"] is None
        assert data["jwt_decoded"] is True


class TestHelperFunctions:
    """헬퍼 함수 테스트"""

    def test_get_cached_user_id_with_user(self):
        """get_cached_user_id - 캐싱된 user_id 있을 때"""
        mock_request = MagicMock()
        mock_request.state.jwt_user_id = 42

        result = get_cached_user_id(mock_request)
        assert result == 42

    def test_get_cached_user_id_without_user(self):
        """get_cached_user_id - user_id가 None일 때"""
        mock_request = MagicMock()
        mock_request.state.jwt_user_id = None

        result = get_cached_user_id(mock_request)
        assert result is None

    def test_get_cached_user_id_no_attribute(self):
        """get_cached_user_id - jwt_user_id 속성이 없을 때"""
        mock_request = MagicMock(spec=[])
        mock_request.state = MagicMock(spec=[])

        result = get_cached_user_id(mock_request)
        assert result is None

    def test_is_jwt_decoded_true(self):
        """is_jwt_decoded - 디코딩 완료"""
        mock_request = MagicMock()
        mock_request.state.jwt_decoded = True

        result = is_jwt_decoded(mock_request)
        assert result is True

    def test_is_jwt_decoded_false(self):
        """is_jwt_decoded - 아직 디코딩 안 함"""
        mock_request = MagicMock()
        mock_request.state.jwt_decoded = False

        result = is_jwt_decoded(mock_request)
        assert result is False

    def test_is_jwt_decoded_no_attribute(self):
        """is_jwt_decoded - jwt_decoded 속성이 없을 때"""
        mock_request = MagicMock(spec=[])
        mock_request.state = MagicMock(spec=[])

        result = is_jwt_decoded(mock_request)
        assert result is False


class TestJWTCachingBehavior:
    """JWT 캐싱 동작 상세 테스트"""

    def test_jwt_payload_cached(self, mock_settings):
        """JWT payload 전체가 캐싱되는지 테스트"""
        import time
        payload = {
            "user_id": 100,
            "email": "test@example.com",
            "role": "admin",
            "exp": time.time() + 3600,
            "iat": time.time()
        }
        token = jwt.encode(payload, TEST_SECRET, algorithm=TEST_ALGORITHM)

        app = FastAPI()
        app.add_middleware(RequestContextMiddleware)

        @app.get("/payload")
        async def get_payload(request: Request):
            cached_payload = getattr(request.state, "jwt_payload", None)
            if cached_payload:
                return {
                    "email": cached_payload.get("email"),
                    "role": cached_payload.get("role")
                }
            return {"error": "no payload"}

        client = TestClient(app)
        response = client.get(
            "/payload",
            headers={"Authorization": f"Bearer {token}"}
        )

        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "admin"

    def test_malformed_bearer_header(self, test_app, mock_settings):
        """잘못된 형식의 Bearer 헤더 테스트"""
        client = TestClient(test_app)

        # "Bearer " 없이 토큰만
        response = client.get(
            "/test",
            headers={"Authorization": "token-without-bearer"}
        )

        data = response.json()
        assert data["user_id"] is None

    def test_empty_bearer_token(self, test_app, mock_settings):
        """빈 Bearer 토큰 테스트"""
        client = TestClient(test_app)

        response = client.get(
            "/test",
            headers={"Authorization": "Bearer "}
        )

        data = response.json()
        assert data["user_id"] is None

    def test_non_integer_user_id(self, test_app, mock_settings):
        """정수가 아닌 user_id 테스트"""
        import time
        payload = {
            "user_id": "not-an-integer",
            "exp": time.time() + 3600,
            "iat": time.time()
        }
        token = jwt.encode(payload, TEST_SECRET, algorithm=TEST_ALGORITHM)

        client = TestClient(test_app)
        response = client.get(
            "/test",
            headers={"Authorization": f"Bearer {token}"}
        )

        data = response.json()
        assert data["user_id"] is None  # 정수가 아니므로 None

    def test_missing_user_id_in_token(self, test_app, mock_settings):
        """user_id가 없는 토큰 테스트"""
        import time
        payload = {
            "email": "test@example.com",
            "exp": time.time() + 3600,
            "iat": time.time()
        }
        token = jwt.encode(payload, TEST_SECRET, algorithm=TEST_ALGORITHM)

        client = TestClient(test_app)
        response = client.get(
            "/test",
            headers={"Authorization": f"Bearer {token}"}
        )

        data = response.json()
        assert data["user_id"] is None
