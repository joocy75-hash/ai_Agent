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
    - Initializes IntegratedAIService with DeepSeek-V3.2
    - Enables 5-layer cost optimization (caching, sampling, event-driven, batching)
    """
    global _ai_service, _redis_client

    try:
        # Initialize Redis client
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))

        _redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

        # Test Redis connection
        await _redis_client.ping()
        logger.info(f" Redis connected: {redis_host}:{redis_port}")

        # Initialize AI service with Redis
        _ai_service = get_integrated_ai_service(redis_client=_redis_client)

        logger.info("="*60)
        logger.info("AI Cost Optimization System Initialized")
        logger.info("="*60)
        logger.info(f"Model: {_ai_service.MODEL_VERSION}")
        logger.info(f"API Base: {_ai_service.BASE_URL}")
        logger.info("Optimizations Enabled:")
        logger.info("   Prompt Caching (90% discount)")
        logger.info("   Response Caching (100% savings)")
        logger.info("   Smart Sampling (50-70% reduction)")
        logger.info("   Event Filtering (80% reduction)")
        logger.info("   Batch Processing (50% reduction)")
        logger.info("Expected Cost Reduction: 85%+")
        logger.info("="*60)

    except redis.ConnectionError as e:
