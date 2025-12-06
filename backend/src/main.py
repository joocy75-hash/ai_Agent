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
    auth,
    oauth,
    bot,
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

    # CORS 설정 - 보안을 위해 특정 도메인만 허용
    # 개발 환경: localhost
    # 프로덕션 환경: 실제 프론트엔드 도메인으로 변경 필요
    allowed_origins = [
        "http://localhost:3000",  # React 개발 서버 (User Frontend)
        "http://localhost:3001",  # Vite 개발 서버 (port 3001)
        "http://localhost:3002",  # Vite 개발 서버 (port 3002)
        "http://localhost:3003",  # Vite 개발 서버 (port 3003)
        "http://localhost:4000",  # Admin Frontend (관리자 대시보드)
        "http://localhost:5173",  # Vite 개발 서버 (default)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:4000",
        "http://127.0.0.1:5173",
    ]

    # 환경 변수로 추가 도메인 설정 가능
    if settings.cors_origins:
        # CORS_ORIGINS 환경 변수: 쉼표로 구분된 도메인 목록
        additional_origins = [
            origin.strip() for origin in settings.cors_origins.split(",")
        ]
        allowed_origins.extend(additional_origins)

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
    app.include_router(admin_diagnostics.router)
    app.include_router(admin_monitoring.router)
    app.include_router(admin_users.router)
    app.include_router(admin_bots.router)  # Admin bot control
    app.include_router(admin_analytics.router)  # Admin analytics
    app.include_router(admin_logs.router)  # Admin logs (NEW)
    app.include_router(strategy.router)
    app.include_router(chart.router)
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
    app.include_router(ws_server.router)

    # Note: Startup logic has been moved to lifespan in db.py
    # @app.on_event("startup") is ignored when lifespan is used

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host=settings.host, port=settings.port, reload=True)
