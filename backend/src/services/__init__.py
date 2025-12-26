# services/__init__.py

"""
Services initialization and dependency management

This module provides global service instances and initialization functions.
"""

import os
import logging
import redis.asyncio as redis
from typing import Optional

from src.services.ai_optimization import (
    get_integrated_ai_service,
    get_event_optimizer,
    IntegratedAIService,
    EventDrivenOptimizer
)

logger = logging.getLogger(__name__)

# Global service instances
_ai_service: Optional[IntegratedAIService] = None
_redis_client: Optional[redis.Redis] = None


async def initialize_ai_service():
    """
    Initialize AI Cost Optimization Service on application startup

    This function:
    - Creates Redis connection for caching and cost tracking
    - Initializes IntegratedAIService with Gemini 3 Pro or DeepSeek-V3
    - Enables 5-layer cost optimization (caching, sampling, event-driven, batching)
    """
    global _ai_service, _redis_client

    try:
        # Initialize Redis client
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD", None)

        _redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

        # Test Redis connection
        await _redis_client.ping()
        logger.info(f"✅ Redis connected: {redis_host}:{redis_port}")

        # Initialize AI service with Redis
        _ai_service = get_integrated_ai_service(redis_client=_redis_client)

        # Get model info based on provider
        if _ai_service.ai_provider == "gemini":
            model_name = _ai_service.GEMINI_MODEL
            api_base = _ai_service.GEMINI_BASE_URL
            provider_label = "🌟 Gemini 3 Pro (Deep Think)"
        else:
            model_name = _ai_service.DEEPSEEK_MODEL
            api_base = _ai_service.DEEPSEEK_BASE_URL
            provider_label = "🧠 DeepSeek V3"

        logger.info("="*60)
        logger.info("AI Cost Optimization System Initialized")
        logger.info("="*60)
        logger.info(f"Provider: {provider_label}")
        logger.info(f"Model: {model_name}")
        logger.info(f"API Base: {api_base}")
        logger.info("Optimizations Enabled:")
        logger.info("   ✅ Prompt Caching (90% discount)")
        logger.info("   ✅ Response Caching (100% savings)")
        logger.info("   ✅ Smart Sampling (50-70% reduction)")
        logger.info("   ✅ Event Filtering (80% reduction)")
        logger.info("   ✅ Batch Processing (50% reduction)")
        logger.info("Expected Cost Reduction: 85%+")
        logger.info("="*60)

    except redis.ConnectionError as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        logger.warning("⚠️ AI service will run without caching (reduced optimization)")

        # Initialize without Redis (degraded mode)
        try:
            _ai_service = get_integrated_ai_service(redis_client=None)
            logger.info("AI service initialized in degraded mode (no caching)")
        except ValueError as ve:
            logger.warning(f"AI features disabled: {ve}")
            _ai_service = None

    except ValueError as e:
        # API key not configured - run without AI features
        logger.warning(f"⚠️ AI service initialization skipped: {e}")
        logger.warning("⚠️ AI features will be disabled. Set GEMINI_API_KEY or DEEPSEEK_API_KEY environment variable to enable.")
        _ai_service = None

    except Exception as e:
        logger.error(f"❌ Failed to initialize AI service: {e}", exc_info=True)
        logger.warning("⚠️ Continuing without AI features...")
        _ai_service = None


async def shutdown_ai_service():
    """
    Cleanup AI service resources on application shutdown

    - Closes Redis connections
    - Saves final cost statistics
    """
    global _redis_client, _ai_service

    try:
        if _ai_service:
            # Save final statistics
            stats = await _ai_service.get_cost_stats()
            logger.info("="*60)
            logger.info("AI Service Final Statistics")
            logger.info("="*60)
            logger.info(f"Total Calls: {stats['overall']['total_calls']}")
            logger.info(f"Total Cost: ${stats['overall']['total_cost_usd']:.4f}")
            logger.info(f"Cache Hit Rate: {stats['response_cache'].get('hit_rate', 0):.1%}")
            logger.info("="*60)

        if _redis_client:
            await _redis_client.close()
            logger.info("✅ Redis connection closed")

        logger.info("✅ AI service shutdown complete")

    except Exception as e:
        logger.error(f"Error during AI service shutdown: {e}", exc_info=True)


def get_ai_service_instance() -> IntegratedAIService:
    """
    Get the global AI service instance

    Returns:
        IntegratedAIService: The singleton AI service instance

    Raises:
        RuntimeError: If AI service not initialized (call initialize_ai_service() first)

    Usage:
        ```python
        from src.services import get_ai_service_instance

        ai_service = get_ai_service_instance()
        result = await ai_service.call_ai(...)
        ```
    """
    if _ai_service is None:
        raise RuntimeError(
            "AI service not initialized. "
            "Call initialize_ai_service() during application startup."
        )
    return _ai_service


def get_redis_instance() -> Optional[redis.Redis]:
    """
    Get the global Redis client instance

    Returns:
        redis.Redis or None: The Redis client, or None if not initialized
    """
    return _redis_client


__all__ = [
    "initialize_ai_service",
    "shutdown_ai_service",
    "get_ai_service_instance",
    "get_redis_instance"
]
