from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings

# 비동기 엔진 - 커넥션 풀 설정 (20명 기준)
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_size=10,  # 기본 커넥션 10개
    max_overflow=20,  # 추가로 최대 20개 (총 30개)
    pool_timeout=30,  # 30초 대기
    pool_recycle=3600,  # 1시간마다 커넥션 재생성
    pool_pre_ping=True,  # 커넥션 사용 전 유효성 체크
)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan - startup and shutdown logic"""
    import asyncio
    import logging
    from ..database.models import Base
    from ..services.bitget_ws_collector import bitget_ws_collector
    from ..services.chart_data_service import get_chart_service

    logger = logging.getLogger(__name__)

    # Startup
    print("🚀 Starting application...")
    logger.info("🚀 Starting application...")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")
    logger.info("✅ Database tables created")

    # Get market queue and bot manager from app state
    market_queue = app.state.market_queue
    bot_manager = app.state.bot_manager
    print(f"📊 Market queue created: {market_queue}")

    # Start CCXT price collector for real-time market data (reliable alternative)
    from ..services.ccxt_price_collector import ccxt_price_collector

    # Create separate queue for chart service to avoid competition with bot
    chart_queue = asyncio.Queue(maxsize=1000)

    # Start collector - it will feed both queues
    asyncio.create_task(ccxt_price_collector(market_queue, chart_queue))
    print("✅ CCXT price collector started (production mode)")
    logger.info("✅ CCXT price collector started (production mode)")

    # Start chart data service with dedicated queue
    chart_service = await get_chart_service(chart_queue)
    print(f"✅ Chart data service started: {chart_service}")
    logger.info("✅ Chart data service started")

    # Initialize cache manager (Redis with in-memory fallback)
    from ..utils.cache_manager import cache_manager

    await cache_manager.initialize()
    print("✅ Cache manager initialized")
    logger.info("✅ Cache manager initialized")

    # Bootstrap bot manager
    await bot_manager.bootstrap()
    print("✅ Bot manager bootstrapped")
    logger.info("✅ Bot manager bootstrapped")

    # Start alert scheduler
    from ..services.alert_scheduler import alert_scheduler

    asyncio.create_task(alert_scheduler.start())
    print("✅ Alert scheduler started")
    logger.info("✅ Alert scheduler started")

    # Start Telegram bot handler (for responding to button clicks)
    from ..services.telegram.bot_handler import start_telegram_bot

    asyncio.create_task(start_telegram_bot())
    print("✅ Telegram bot handler started")
    logger.info("✅ Telegram bot handler started")

    print("🎉 Application startup complete!")
    logger.info("🎉 Application startup complete!")

    try:
        yield
    finally:
        # Shutdown
        logger.info("🛑 Shutting down application...")

        # Close cache manager
        from ..utils.cache_manager import cache_manager

        await cache_manager.close()
        logger.info("✅ Cache manager closed")

        await engine.dispose()
        logger.info("✅ Application shutdown complete")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
