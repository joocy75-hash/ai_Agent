"""
JWT 인증 테스트
"""
import pytest
from datetime import timedelta
from jose import jwt

from src.utils.jwt_auth import JWTAuth
from src.config import settings


class TestJWTAuth:
    """JWT 인증 유틸리티 테스트"""

    def test_password_hashing(self):
        """비밀번호 해싱 및 검증 테스트"""
        password = "test_password_123"

        # 해싱
        hashed = JWTAuth.get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0

        # 검증 성공
        assert JWTAuth.verify_password(password, hashed) is True

        # 검증 실패
        assert JWTAuth.verify_password("wrong_password", hashed) is False

    def test_create_access_token(self):
        """액세스 토큰 생성 테스트"""
        user_id = 123
        email = "test@example.com"

        token = JWTAuth.create_access_token(
            data={"user_id": user_id, "email": email}
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # 토큰 디코드 검증
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["user_id"] == user_id
        assert payload["email"] == email
        assert "exp" in payload

    def test_create_access_token_with_custom_expiry(self):
        """커스텀 만료 시간을 가진 토큰 생성 테스트"""
        user_id = 456
        custom_expiry = timedelta(minutes=5)

        token = JWTAuth.create_access_token(
            data={"user_id": user_id},
            expires_delta=custom_expiry
        )

        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["user_id"] == user_id

    def test_decode_token_success(self):
        """토큰 디코드 성공 테스트"""
        user_id = 789
        email = "decode@example.com"

        token = JWTAuth.create_access_token(
            data={"user_id": user_id, "email": email}
        )

        payload = JWTAuth.decode_token(token)
        assert payload["user_id"] == user_id
        assert payload["email"] == email

    def test_decode_token_invalid(self):
        """잘못된 토큰 디코드 테스트"""
        from fastapi import HTTPException

        invalid_token = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            JWTAuth.decode_token(invalid_token)

        assert exc_info.value.status_code == 401
        assert "Invalid" in exc_info.value.detail or "Could not validate" in exc_info.value.detail

    def test_decode_token_expired(self):
        """만료된 토큰 디코드 테스트"""
        from fastapi import HTTPException

        # 이미 만료된 토큰 생성 (음수 시간)
        token = JWTAuth.create_access_token(
            data={"user_id": 999},
            expires_delta=timedelta(seconds=-10)
        )

        with pytest.raises(HTTPException) as exc_info:
            JWTAuth.decode_token(token)

        assert exc_info.value.status_code == 401

    def test_decode_token_wrong_secret(self):
        """잘못된 시크릿으로 서명된 토큰 테스트"""
        from fastapi import HTTPException

        # 다른 시크릿으로 토큰 생성
        fake_token = jwt.encode(
            {"user_id": 111},
            "wrong_secret_key",
            algorithm=settings.jwt_algorithm
        )

        with pytest.raises(HTTPException) as exc_info:
            JWTAuth.decode_token(fake_token)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestJWTDependencies:
    """JWT 의존성 함수 테스트"""

    def test_get_current_user_id(self):
        """현재 사용자 ID 추출 테스트"""
        from unittest.mock import MagicMock
        from fastapi.security import HTTPAuthorizationCredentials
        from src.utils.jwt_auth import get_current_user_id

        user_id = 555
        token = JWTAuth.create_access_token(data={"user_id": user_id})

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        # Mock request object
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.jwt_decoded = False  # Force direct decoding
        mock_request.cookies = {}
        
        extracted_user_id = get_current_user_id(mock_request, credentials)

        assert extracted_user_id == user_id

    def test_get_current_user_id_missing_user_id(self):
        """user_id가 없는 토큰 테스트"""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        from src.utils.jwt_auth import get_current_user_id

        # user_id 없이 토큰 생성
        token = JWTAuth.create_access_token(data={"email": "test@example.com"})

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        # Mock request object
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.jwt_decoded = False  # Force direct decoding
        mock_request.cookies = {}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_id(mock_request, credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail

    def test_get_current_user_id_invalid_token(self):
        """잘못된 토큰으로 사용자 ID 추출 테스트"""
        from unittest.mock import MagicMock
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        from src.utils.jwt_auth import get_current_user_id

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )
        
        # Mock request object
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        mock_request.state.jwt_decoded = False  # Force direct decoding
        mock_request.cookies = {}

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_id(mock_request, credentials)

        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestJWTIntegration:
    """JWT 통합 테스트"""

    async def test_full_auth_flow(self, async_session):
        """전체 인증 플로우 테스트"""
        from src.database.models import User

        # 1. 사용자 생성
        email = "integration@example.com"
        password = "secure_password_123"
        hashed_password = JWTAuth.get_password_hash(password)

        user = User(email=email, password_hash=hashed_password)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # 2. 로그인 (비밀번호 검증)
        assert JWTAuth.verify_password(password, user.password_hash) is True

        # 3. 토큰 생성
        token = JWTAuth.create_access_token(
            data={"user_id": user.id, "email": user.email}
        )

        # 4. 토큰 검증
        payload = JWTAuth.decode_token(token)
        assert payload["user_id"] == user.id
        assert payload["email"] == user.email

    async def test_user_isolation(self, async_session):
        """사용자별 토큰 격리 테스트"""
        from src.database.models import User

        # 두 사용자 생성
        user1 = User(email="user1@example.com", password_hash=JWTAuth.get_password_hash("pw1"))
        user2 = User(email="user2@example.com", password_hash=JWTAuth.get_password_hash("pw2"))

        async_session.add_all([user1, user2])
        await async_session.commit()
        await async_session.refresh(user1)
        await async_session.refresh(user2)

        # 각각 토큰 생성
        token1 = JWTAuth.create_access_token(data={"user_id": user1.id})
        token2 = JWTAuth.create_access_token(data={"user_id": user2.id})

        # 토큰 검증
        payload1 = JWTAuth.decode_token(token1)
        payload2 = JWTAuth.decode_token(token2)

        # 사용자 ID가 다름을 확인
        assert payload1["user_id"] == user1.id
        assert payload2["user_id"] == user2.id
        assert payload1["user_id"] != payload2["user_id"]
