import os
import warnings
from pydantic import BaseModel, model_validator


class RateLimitConfig:
    """Rate Limiting 설정"""

    # 환경 감지
    IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "development") == "development"

    # IP 기반 Rate Limits (개발 환경에서는 10배 증가)
    IP_GENERAL_PER_MINUTE = 600 if IS_DEVELOPMENT else 60  # 일반 API
    IP_BACKTEST_PER_MINUTE = 50 if IS_DEVELOPMENT else 5  # 백테스트

    # 사용자별 Rate Limits (개발 환경에서는 10배 증가)
    USER_GENERAL_PER_MINUTE = 1000 if IS_DEVELOPMENT else 100  # 일반 API
    USER_BACKTEST_PER_MINUTE = 50 if IS_DEVELOPMENT else 5  # 백테스트: 분당
    USER_BACKTEST_PER_HOUR = 100 if IS_DEVELOPMENT else 10  # 백테스트: 시간당
    USER_ORDER_PER_MINUTE = 100 if IS_DEVELOPMENT else 10  # 주문
    USER_API_KEY_REVEAL_PER_HOUR = 30 if IS_DEVELOPMENT else 3  # API 키 복호화
    USER_AI_STRATEGY_PER_HOUR = 50 if IS_DEVELOPMENT else 5  # AI 전략 생성

    # DeepSeek API Rate Limits (Issue #4 - AI API 비용 제어)
    USER_DEEPSEEK_PER_MINUTE = 10 if IS_DEVELOPMENT else 2  # DeepSeek API: 분당
    USER_DEEPSEEK_PER_HOUR = 100 if IS_DEVELOPMENT else 20  # DeepSeek API: 시간당
    USER_DEEPSEEK_PER_DAY = 1000 if IS_DEVELOPMENT else 100  # DeepSeek API: 일당

    # 시간 윈도우 (초)
    WINDOW_MINUTE = 60
    WINDOW_HOUR = 3600
    WINDOW_DAY = 86400


class PaginationConfig:
    """페이지네이션 기본 설정"""

    # 거래 내역
    TRADES_DEFAULT_LIMIT = 50
    TRADES_MAX_LIMIT = 500

    # 자산 내역
    EQUITY_DEFAULT_LIMIT = 100
    EQUITY_MAX_LIMIT = 1000

    # 백테스트 결과
    BACKTEST_DEFAULT_LIMIT = 20
    BACKTEST_MAX_LIMIT = 100


class ExchangeConfig:
    """거래소 설정"""

    # 기본 거래소
    DEFAULT_EXCHANGE = "bitget"

    # 지원하는 거래소 목록
    SUPPORTED_EXCHANGES = ["bitget", "binance", "okx"]


class BacktestConfig:
    """백테스트 설정"""

    # 데이터 모드: "offline" (캐시만) 또는 "online" (API 호출 허용)
    DATA_MODE = os.getenv("BACKTEST_DATA_MODE", "offline")
    CACHE_DIR = os.getenv("CANDLE_CACHE_DIR", "./candle_cache")

    # 오프라인 전용 모드 (API 호출 없이 캐시 데이터만 사용)
    CACHE_ONLY = DATA_MODE == "offline"

    # 기본값
    DEFAULT_INITIAL_BALANCE = 1000.0
    DEFAULT_FEE_RATE = 0.001  # 0.1%
    DEFAULT_SLIPPAGE = 0.0005  # 0.05%

    # 제한
    MIN_INITIAL_BALANCE = 1.0
    MAX_INITIAL_BALANCE = 1000000.0


class TelegramConfig:
    """텔레그램 봇 설정"""

    # 봇 토큰 (BotFather에서 발급)
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # 알림 받을 채팅 ID
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # 알림 유형별 활성화 여부
    NOTIFY_TRADES = os.getenv("TELEGRAM_NOTIFY_TRADES", "true").lower() == "true"
    NOTIFY_SYSTEM = os.getenv("TELEGRAM_NOTIFY_SYSTEM", "true").lower() == "true"
    NOTIFY_ERRORS = os.getenv("TELEGRAM_NOTIFY_ERRORS", "true").lower() == "true"

    # 활성화 여부
    ENABLED = bool(BOT_TOKEN and CHAT_ID)


class Settings(BaseModel):
    app_name: str = "Auto Trading Backend"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/trading"
    )
    # JWT_SECRET: 프로덕션에서 필수, 최소 32자 이상 권장
    jwt_secret: str = os.getenv("JWT_SECRET", "")
    jwt_algorithm: str = "HS256"
    jwt_expires_seconds: int = 60 * 60 * 24
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    # AI Provider: "gemini" or "deepseek" (기본값: deepseek - Rate Limit 없음)
    ai_provider: str = os.getenv("AI_PROVIDER", "deepseek")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    # CORS 설정: 쉼표로 구분된 허용 도메인 목록 (예: "https://example.com,https://app.example.com")
    cors_origins: str = os.getenv("CORS_ORIGINS", "")

    # Google OAuth 설정
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
    )

    # Kakao OAuth 설정
    kakao_client_id: str = os.getenv("KAKAO_CLIENT_ID", "")  # REST API 키
    kakao_client_secret: str = os.getenv("KAKAO_CLIENT_SECRET", "")  # 선택적
    kakao_redirect_uri: str = os.getenv(
        "KAKAO_REDIRECT_URI", "http://localhost:8000/auth/kakao/callback"
    )

    # Frontend URL (OAuth 후 리다이렉트)
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        """JWT Secret 검증: 프로덕션에서는 필수, 개발 환경에서는 경고만"""
        environment = os.getenv("ENVIRONMENT", "development")

        if not self.jwt_secret:
            if environment != "development":
                raise ValueError(
                    "JWT_SECRET is required in production environment. "
                    "Please set the JWT_SECRET environment variable with a secure value (minimum 32 characters)."
                )
            else:
                warnings.warn(
                    "JWT_SECRET is not set. Using empty secret is insecure and only allowed in development.",
                    UserWarning,
                    stacklevel=2,
                )
        elif len(self.jwt_secret) < 32:
            if environment != "development":
                raise ValueError(
                    f"JWT_SECRET is too short ({len(self.jwt_secret)} characters). "
                    "Minimum 32 characters required for production security."
                )
            else:
                warnings.warn(
                    f"JWT_SECRET is too short ({len(self.jwt_secret)} characters). "
                    "Minimum 32 characters recommended for security.",
                    UserWarning,
                    stacklevel=2,
                )

        return self

    def is_jwt_secret_secure(self) -> bool:
        """JWT Secret이 보안 요구사항을 충족하는지 확인 (최소 32자)"""
        return len(self.jwt_secret) >= 32


settings = Settings()
