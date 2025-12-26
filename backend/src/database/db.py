from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings

# 비동기 엔진 - 커넥션 풀 설정 (20명 기준)
engine_args = {
    "echo": settings.debug,
    "future": True,
}

# SQLite가 아닐 경우에만 pool 설정 추가
if "sqlite" not in settings.database_url:
    engine_args.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }
    )

engine = create_async_engine(settings.database_url, **engine_args)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan - startup and shutdown logic"""
    import asyncio
    import logging
    from ..database.models import Base
    from ..services.chart_data_service import get_chart_service

    logger = logging.getLogger(__name__)

    # Startup
    logger.info("🚀 Starting application...")

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created")

    # Get market queue and bot manager from app state
    market_queue = app.state.market_queue
    bot_manager = app.state.bot_manager
    logger.info(f"📊 Market queue created: {market_queue}")

    # Start CCXT price collector for real-time market data (reliable alternative)
    from ..services.ccxt_price_collector import ccxt_price_collector

    # Create separate queue for chart service to avoid competition with bot
    chart_queue = asyncio.Queue(maxsize=1000)

    # Start collector - it will feed both queues
    asyncio.create_task(ccxt_price_collector(market_queue, chart_queue))
    logger.info("✅ CCXT price collector started (production mode)")

    # Start chart data service with dedicated queue
    chart_service = await get_chart_service(chart_queue)
    logger.info(f"✅ Chart data service started: {chart_service}")

    # Initialize cache manager (Redis with in-memory fallback)
    from ..utils.cache_manager import cache_manager

    await cache_manager.initialize()
    logger.info("✅ Cache manager initialized")

    # Initialize AI Cost Optimization Service
    from ..services import initialize_ai_service

    await initialize_ai_service()
    logger.info("✅ AI Cost Optimization Service initialized")

    # Bootstrap bot manager
    await bot_manager.bootstrap()
    logger.info("✅ Bot manager bootstrapped")

    # Start alert scheduler
    from ..services.alert_scheduler import alert_scheduler

    asyncio.create_task(alert_scheduler.start())
    logger.info("✅ Alert scheduler started")

    # Start price alert service (for chart annotations)
    from ..services.price_alert_service import price_alert_service

    await price_alert_service.start()
    logger.info("✅ Price alert service started")

    # Start Telegram bot handler (for responding to button clicks)
    from ..services.telegram.bot_handler import start_telegram_bot

    asyncio.create_task(start_telegram_bot())
    logger.info("✅ Telegram bot handler started")

    # Start snapshot worker for dashboard pre-caching (Phase 0 - Zero-Wait UX)
    from ..services.snapshot_worker import start_snapshot_worker

    asyncio.create_task(start_snapshot_worker())
    logger.info("✅ Dashboard snapshot worker started")

    logger.info("🎉 Application startup complete!")

    try:
        yield
    finally:
        # Shutdown
        logger.info("🛑 Shutting down application...")

        # Stop price alert service
        from ..services.price_alert_service import price_alert_service

        await price_alert_service.stop()
        logger.info("✅ Price alert service stopped")

        # Issue #2.2: Close all Bitget REST clients (aiohttp sessions)
        from ..services.bitget_rest import close_all_rest_clients

        await close_all_rest_clients()
        logger.info("✅ Bitget REST clients closed")

        # Shutdown AI Cost Optimization Service
        from ..services import shutdown_ai_service

        await shutdown_ai_service()
        logger.info("✅ AI Cost Optimization Service stopped")

        # Close cache manager
        from ..utils.cache_manager import cache_manager

        await cache_manager.close()
        logger.info("✅ Cache manager closed")

        await engine.dispose()
        logger.info("✅ Application shutdown complete")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
