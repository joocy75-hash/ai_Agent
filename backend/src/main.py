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
    admin_diagnostics,
    admin_monitoring,
    admin_users,
    admin_bots,
    admin_analytics,
    admin_logs,
    admin_grid_template,  # 그리드 템플릿 관리자 API (NEW)
    annotations,  # 차트 어노테이션 API (NEW)
    auth,
    oauth,
    bot,
    bot_instances,  # 다중 봇 시스템 API (NEW)
    grid_bot,  # 그리드 봇 API (NEW)
    grid_template,  # 그리드 템플릿 사용자 API (NEW)
    strategy,
    account,
    order,
    chart,
    backtest,
    backtest_result,
    backtest_history,
    ai_strategy,
    api_status,
    trades,
    health,
    analytics,
    positions,
    alerts,
    bitget_market,
    upload,
    two_factor,
    telegram,
    user_backtest,  # 일반 회원용 캐시 백테스트 (NEW)
    trend_template,  # AI 추세 템플릿 사용자 API (NEW)
)
from .config import settings
from .database import db
from .database.models import Base
from .database.db import lifespan
from .websockets import ws_server
from .services.bitget_ws_collector import bitget_ws_collector
from .workers.manager import BotManager
from .middleware.rate_limit_improved import EnhancedRateLimitMiddleware
from .middleware.error_handler import register_exception_handlers
from .middleware.request_context import RequestContextMiddleware
from .middleware.admin_ip_whitelist import AdminIPWhitelistMiddleware
from .config import RateLimitConfig


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
        docs_url="/docs",
        redoc_url="/redoc",
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

    # 프로덕션에서 CORS_ORIGINS가 설정되지 않은 경우 경고
    if not RateLimitConfig.IS_DEVELOPMENT and not allowed_origins:
        logging.warning(
            "⚠️ CORS: No origins configured in production! "
            "Set CORS_ORIGINS environment variable (comma-separated domains)"
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

    # 전역 에러 핸들러 등록
    register_exception_handlers(app)

    # Routers
    app.include_router(health.router)  # Health check (먼저 등록 - 인증 불필요)
    app.include_router(auth.router)
    app.include_router(oauth.router)  # OAuth (Google, Kakao)
    app.include_router(two_factor.router)  # 2FA (NEW)
    app.include_router(bot.router)
    app.include_router(bot_instances.router)  # 다중 봇 시스템 API (NEW)
    app.include_router(grid_bot.router)  # 그리드 봇 API (NEW)
    app.include_router(admin_diagnostics.router)
    app.include_router(admin_monitoring.router)
    app.include_router(admin_users.router)
    app.include_router(admin_bots.router)  # Admin bot control
    app.include_router(admin_analytics.router)  # Admin analytics
    app.include_router(admin_logs.router)  # Admin logs (NEW)
    app.include_router(strategy.router)
    app.include_router(chart.router)
    app.include_router(annotations.router)  # Chart Annotations API (NEW)
    app.include_router(order.router)
    app.include_router(account.router)
    app.include_router(backtest.router)
    app.include_router(backtest_result.router)
    app.include_router(backtest_history.router)
    app.include_router(ai_strategy.router)
    app.include_router(api_status.router)
    app.include_router(trades.router)
    app.include_router(analytics.router)  # Analytics API
    app.include_router(positions.router)  # Positions API (NEW)
    app.include_router(alerts.router)  # Alerts API (NEW)
    app.include_router(bitget_market.router)  # Bitget Market API (NEW)
    app.include_router(upload.router)  # File Upload API (NEW)
    app.include_router(telegram.router)  # Telegram Bot API (NEW)
    app.include_router(grid_template.router)  # Grid Template 사용자 API (NEW)
    app.include_router(admin_grid_template.router)  # Grid Template 관리자 API (NEW)
    app.include_router(user_backtest.router)  # 일반 회원용 캐시 백테스트 (NEW)
    app.include_router(trend_template.router)  # AI 추세 템플릿 사용자 API (NEW)
    app.include_router(ws_server.router)

    # Note: Startup logic has been moved to lifespan in db.py
    # @app.on_event("startup") is ignored when lifespan is used

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host=settings.host, port=settings.port, reload=True)
