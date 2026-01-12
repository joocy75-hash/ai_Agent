"""
Redis Client Utility

분산 환경에서 Rate Limiting 및 캐싱을 위한 Redis 클라이언트.
"""
import logging
import os
from typing import Optional

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# Redis 연결 상태
_redis_client: Optional[Redis] = None
_redis_available: bool = False


async def get_redis_client() -> Optional[Redis]:
    """
    Redis 클라이언트 인스턴스 반환

    Returns:
        Redis 클라이언트 또는 None (연결 실패 시)
    """
    global _redis_client, _redis_available

    if _redis_client is not None:
        return _redis_client if _redis_available else None

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        import redis.asyncio as redis
        _redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # 연결 테스트
        await _redis_client.ping()
        _redis_available = True
        logger.info("Redis connection established")
        return _redis_client
    except ImportError:
        logger.warning("redis package not installed, falling back to in-memory")
        _redis_available = False
        return None
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}, falling back to in-memory")
        _redis_available = False
        return None


async def check_redis_health() -> bool:
    """
    Redis 연결 상태 확인

    Returns:
        연결 상태 (True: 정상, False: 비정상)
    """
    global _redis_client, _redis_available

    if _redis_client is None:
        return False

    try:
        await _redis_client.ping()
        _redis_available = True
        return True
    except Exception:
        _redis_available = False
        return False


async def close_redis_connection():
    """Redis 연결 종료"""
    global _redis_client, _redis_available

    if _redis_client is not None:
        try:
            await _redis_client.close()
        except Exception:
            pass
        finally:
            _redis_client = None
            _redis_available = False
