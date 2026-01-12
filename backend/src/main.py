import asyncio
import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging to output bot execution logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # Override any existing configuration
)
# Set bot_runner logger to INFO
logging.getLogger("src.services.bot_runner").setLevel(logging.INFO)
logging.getLogger("src.workers.manager").setLevel(logging.INFO)

from .api import (
    account,
    admin_analytics,
    admin_bots,
    admin_diagnostics,
    admin_grid_template,  # 그리드 템플릿 관리자 API (NEW)
    admin_logs,
    admin_monitoring,
    admin_users,
    ai_cost,  # AI 비용 최적화 API (NEW)
    ai_strategy,
    alerts,
    analytics,
    annotations,  # 차트 어노테이션 API (NEW)
    api_status,
    auth,
    backtest,
    backtest_history,
    backtest_result,
    bitget_market,
    bot,
    bot_instances,  # 다중 봇 시스템 API (NEW)
    chart,
    grid_bot,  # 그리드 봇 API (NEW)
    grid_template,  # 그리드 템플릿 사용자 API (NEW)
    health,
    multibot,  # 멀티봇 트레이딩 API v2.0 (NEW)
    oauth,
    order,
    positions,
    strategy,
    telegram,
    trades,
    trend_template,  # AI 추세 템플릿 사용자 API (NEW)
    two_factor,
    upload,
    user_backtest,  # 일반 회원용 캐시 백테스트 (NEW)
)
from .config import RateLimitConfig, settings
from .database import db
from .database.db import lifespan
from .middleware.admin_ip_whitelist import AdminIPWhitelistMiddleware
from .middleware.csrf import CSRFMiddleware
from .middleware.error_handler import register_exception_handlers
from .middleware.rate_limit_improved import EnhancedRateLimitMiddleware
from .middleware.request_context import RequestContextMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .websockets import ws_server
from .workers.manager import BotManager


def create_app() -> FastAPI:
    # 🔒 보안 검증: JWT_SECRET 필수 확인
    if not settings.jwt_secret or settings.jwt_secret == "change_me":
        if not RateLimitConfig.IS_DEVELOPMENT:
            raise RuntimeError(
                "❌ CRITICAL: JWT_SECRET must be set in production! "
                "Set JWT_SECRET environment variable with a secure random string (at least 32 characters)."
            )
        else:
            logging.warning(
                "⚠️ WARNING: JWT_SECRET is not set. Using insecure default for development only!"
            )
    # 프로덕션에서 JWT_SECRET 길이 검증 (최소 32자)
    elif not RateLimitConfig.IS_DEVELOPMENT and not settings.is_jwt_secret_secure():
        raise RuntimeError(
            f"❌ CRITICAL: JWT_SECRET is too short ({len(settings.jwt_secret)} chars). "
            "Minimum 32 characters required for production security."
        )

    market_queue: asyncio.Queue = asyncio.Queue()
    bot_manager = BotManager(market_queue, db.AsyncSessionLocal)

    app = FastAPI(
        title=settings.app_name,
        description="""
        ## 암호화폐 자동 거래 시스템 API

        ### 주요 기능
        - 🔐 **인증**: JWT 기반 사용자 인증
        - 📊 **거래**: 실시간 거래 및 포지션 관리
        - 🤖 **전략**: AI 기반 트레이딩 전략 생성 및 백테스트
        - 📈 **차트**: 실시간 시장 데이터 및 차트
        - 👨‍💼 **관리**: 사용자 및 시스템 관리 (관리자 전용)

        ### 인증 방법
        1. `/auth/register` - 회원가입
        2. `/auth/login` - 로그인하여 JWT 토큰 받기
        3. **Authorize** 버튼을 클릭하여 `Bearer <token>` 입력
        4. 인증된 API 사용 가능

        ### Rate Limiting
        - IP 기반: 분당 60회
        - 사용자 기반: 분당 100회
        - 백테스트: 시간당 10회
        - API 키 조회: 시간당 3회
        """,
        version="1.0.0",
        contact={
            "name": "Auto Dashboard Team",
            "email": "support@example.com",
        },
        license_info={
            "name": "MIT",
        },
        lifespan=lifespan,
        # 프로덕션 환경에서 API 문서 비활성화 (보안)
        docs_url=None if not RateLimitConfig.IS_DEVELOPMENT else "/docs",
        redoc_url=None if not RateLimitConfig.IS_DEVELOPMENT else "/redoc",
        openapi_tags=[
            {"name": "health", "description": "시스템 상태 확인 및 헬스 체크"},
            {"name": "auth", "description": "인증 및 회원가입 (JWT 기반)"},
            {"name": "2fa", "description": "2단계 인증 (TOTP)"},
            {"name": "account", "description": "계정 정보, 잔고, 포지션 조회"},
            {"name": "order", "description": "거래 내역 및 주문 관리"},
            {"name": "bot", "description": "자동 거래 봇 제어"},
            {
                "name": "Grid Bot",
                "description": "그리드 트레이딩 봇 (가격 범위 자동 매매)",
            },
            {"name": "strategy", "description": "트레이딩 전략 관리"},
            {"name": "ai_strategy", "description": "AI 기반 전략 생성 (DeepSeek)"},
            {
                "name": "AI Cost Optimization",
                "description": "AI 비용 최적화: 통계, 모니터링, 설정 관리 (DeepSeek-V3.2)",
            },
            {"name": "backtest", "description": "백테스트 실행 및 결과 조회"},
            {"name": "chart", "description": "시장 차트 및 캔들 데이터"},
            {"name": "trades", "description": "거래 기록 관리"},
            {"name": "analytics", "description": "성과 분석 및 리스크 지표"},
            {"name": "positions", "description": "포지션 및 미실현 손익 조회"},
            {"name": "alerts", "description": "시스템 알림 관리"},
            {"name": "admin", "description": "관리자 전용 기능 (RBAC 필요)"},
            {"name": "admin-bots", "description": "관리자 전용: 봇 제어 및 모니터링"},
            {"name": "telegram", "description": "텔레그램 알림 봇 설정 및 제어"},
        ],
    )
    app.state.market_queue = market_queue
    app.state.bot_manager = bot_manager

    # ============================================================
    # 🔒 CORS 설정 - 환경별 보안 강화
    # ============================================================
    # 개발 환경: localhost 허용
    # 프로덕션 환경: CORS_ORIGINS 환경변수로만 허용 도메인 설정
    # ============================================================

    if RateLimitConfig.IS_DEVELOPMENT:
        # 개발 환경: localhost 변형들 허용
        allowed_origins = [
            "http://localhost:3000",  # React 개발 서버
            "http://localhost:3001",  # Vite (port 3001)
            "http://localhost:3002",  # Vite (port 3002)
            "http://localhost:3003",  # Vite (port 3003)
            "http://localhost:4000",  # Admin Frontend
            "http://localhost:5173",  # Vite default
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:3003",
            "http://127.0.0.1:4000",
            "http://127.0.0.1:5173",
        ]
        logging.info("🔧 CORS: Development mode - localhost origins allowed")
    else:
        # 프로덕션 환경: 환경변수로만 허용 도메인 설정 (하드코딩 제거)
        allowed_origins = []
        logging.info("🔒 CORS: Production mode - only CORS_ORIGINS env var allowed")

    # 환경 변수로 추가 도메인 설정 (개발/프로덕션 모두)
    # CORS_ORIGINS 환경변수: 쉼표로 구분된 도메인 목록
    # 예: "https://example.com,https://admin.example.com"
    if settings.cors_origins:
        additional_origins = [
            origin.strip()
            for origin in settings.cors_origins.split(",")
            if origin.strip()  # 빈 문자열 제외
        ]
        allowed_origins.extend(additional_origins)
        logging.info(
            f"🔒 CORS: Added {len(additional_origins)} origins from CORS_ORIGINS env"
        )

    # 프로덕션에서 CORS_ORIGINS가 설정되지 않은 경우 에러 (보안 강화)
    if not RateLimitConfig.IS_DEVELOPMENT and not allowed_origins:
        raise RuntimeError(
            "❌ CRITICAL: CORS_ORIGINS must be set in production! "
            "Set CORS_ORIGINS environment variable (comma-separated domains). "
            "Example: CORS_ORIGINS=https://example.com,https://admin.example.com"
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # Request Context Middleware 추가 (먼저 등록 - request_id 생성)
    app.add_middleware(RequestContextMiddleware)

    # 관리자 IP 화이트리스트 미들웨어 (프로덕션 환경에서만)
    # 개발 환경에서는 비활성화하여 모든 IP 허용
    if not RateLimitConfig.IS_DEVELOPMENT:
        app.add_middleware(AdminIPWhitelistMiddleware)

    # Rate Limiting Middleware 추가 (개선된 버전)
    app.add_middleware(EnhancedRateLimitMiddleware)

    # 보안 헤더 미들웨어 추가 (OWASP 권장)
    app.add_middleware(SecurityHeadersMiddleware)

    # CSRF 보호 (쿠키 기반 인증용)
    # NOTE: refresh 엔드포인트는 CSRF 검증에서 제외해야 함
    # (access_token 만료 시 refresh_token만으로 갱신해야 하므로)
    csrf_exempt_paths = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",  # 토큰 갱신은 CSRF 제외 (refresh_token 자체가 인증)
        "/api/v1/auth/google/callback",
        "/api/v1/auth/kakao/callback",
    }
    app.add_middleware(CSRFMiddleware, exempt_paths=csrf_exempt_paths)

    # 전역 에러 핸들러 등록
    register_exception_handlers(app)

    # ============================================================
    # API 라우터 등록 - /api/v1 접두사로 표준화
    # ============================================================
    from fastapi import APIRouter

    api_v1_router = APIRouter(prefix="/api/v1")

    # 인증 관련
    api_v1_router.include_router(auth.router)
    api_v1_router.include_router(oauth.router)  # OAuth (Google, Kakao)
    api_v1_router.include_router(two_factor.router)  # 2FA

    # 봇 관리
    api_v1_router.include_router(bot.router)
    api_v1_router.include_router(bot_instances.router)  # 다중 봇 시스템
    api_v1_router.include_router(multibot.router)  # 멀티봇 트레이딩 v2.0
    api_v1_router.include_router(grid_bot.router)  # 그리드 봇

    # 전략 및 백테스트
    api_v1_router.include_router(strategy.router)
    api_v1_router.include_router(ai_strategy.router)
    api_v1_router.include_router(backtest.router)
    api_v1_router.include_router(backtest_result.router)
    api_v1_router.include_router(backtest_history.router)
    api_v1_router.include_router(user_backtest.router)  # 캐시 백테스트

    # 거래 및 계정
    api_v1_router.include_router(account.router)
    api_v1_router.include_router(order.router)
    api_v1_router.include_router(trades.router)
    api_v1_router.include_router(positions.router)
    api_v1_router.include_router(bitget_market.router)  # Bitget Market

    # 차트 및 분석
    api_v1_router.include_router(chart.router)
    api_v1_router.include_router(annotations.router)  # 차트 어노테이션
    api_v1_router.include_router(analytics.router)

    # 템플릿
    api_v1_router.include_router(grid_template.router)  # Grid 템플릿 (사용자)
    api_v1_router.include_router(trend_template.router)  # Trend 템플릿 (사용자)

    # 알림 및 설정
    api_v1_router.include_router(alerts.router)
    api_v1_router.include_router(telegram.router)
    api_v1_router.include_router(upload.router)
    api_v1_router.include_router(api_status.router)

    # AI 비용 최적화
    api_v1_router.include_router(ai_cost.router)  # AI Cost Optimization

    # 관리자 전용
    api_v1_router.include_router(admin_diagnostics.router)
    api_v1_router.include_router(admin_monitoring.router)
    api_v1_router.include_router(admin_users.router)
    api_v1_router.include_router(admin_bots.router)
    api_v1_router.include_router(admin_analytics.router)
    api_v1_router.include_router(admin_logs.router)
    api_v1_router.include_router(admin_grid_template.router)  # Grid 템플릿 (관리자)

    # API v1 라우터 등록
    app.include_router(api_v1_router)

    # 루트 레벨 라우터 (prefix 없음)
    app.include_router(health.router)  # /health - 헬스체크
    app.include_router(ws_server.router)  # /ws - 웹소켓

    # Note: Startup logic has been moved to lifespan in db.py
    # @app.on_event("startup") is ignored when lifespan is used

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host=settings.host, port=settings.port, reload=True)
