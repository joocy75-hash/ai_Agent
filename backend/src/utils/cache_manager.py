"""
캐싱 매니저 - Redis와 In-Memory 캐싱 지원
Redis가 없어도 In-Memory 캐시로 작동 (Graceful Degradation)
"""
import logging
import asyncio
import json
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """캐시 엔트리"""
    value: Any
    expires_at: datetime
    hits: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


class InMemoryCache:
    """In-Memory 캐시 (Redis 백업)"""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        async with self._lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]

            # 만료 확인
            if datetime.utcnow() > entry.expires_at:
                del self.cache[key]
                return None

            # 히트 카운트 증가
            entry.hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """캐시에 값 저장"""
        async with self._lock:
            # 캐시 크기 제한 체크
            if len(self.cache) >= self.max_size and key not in self.cache:
                # LRU 방식으로 가장 오래된 항목 제거
                oldest_key = min(
                    self.cache.keys(),
                    key=lambda k: self.cache[k].created_at
                )
                del self.cache[oldest_key]

            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            self.cache[key] = CacheEntry(value=value, expires_at=expires_at)
            return True

    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    async def clear(self) -> bool:
        """전체 캐시 삭제"""
        async with self._lock:
            self.cache.clear()
            return True

    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        return await self.get(key) is not None

    def get_stats(self) -> dict:
        """캐시 통계"""
        total_hits = sum(entry.hits for entry in self.cache.values())
        return {
            "type": "in-memory",
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
        }


class CacheManager:
    """
    통합 캐시 매니저
    Redis 사용 가능하면 Redis 사용, 없으면 In-Memory 캐시 사용
    """

    def __init__(self):
        self.redis_client = None
        self.memory_cache = InMemoryCache(max_size=1000)
        self.use_redis = False
        self._initialized = False

    async def initialize(self):
        """캐시 매니저 초기화"""
        if self._initialized:
            return

        # Redis 연결 시도 (optional)
        try:
            import redis.asyncio as redis

            # Redis 연결 설정 (환경변수에서 가져오기)
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )

            # Redis 연결 테스트
            await self.redis_client.ping()
            self.use_redis = True
            logger.info("✅ Redis cache initialized successfully")

        except ImportError:
            logger.info("⚠️  Redis library not installed, using in-memory cache")
            self.use_redis = False
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}, using in-memory cache")
            self.use_redis = False
            self.redis_client = None

        self._initialized = True

    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        try:
            if self.use_redis and self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    # JSON 역직렬화
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return None
            else:
                return await self.memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """캐시에 값 저장"""
        try:
            if self.use_redis and self.redis_client:
                # JSON 직렬화
                if isinstance(value, (dict, list)):
                    value_str = json.dumps(value)
                else:
                    value_str = str(value)

                await self.redis_client.setex(key, ttl, value_str)
                return True
            else:
                return await self.memory_cache.set(key, value, ttl)
        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """캐시에서 값 삭제"""
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.delete(key)
                return True
            else:
                return await self.memory_cache.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """패턴과 일치하는 키 삭제 (예: "user:*")"""
        try:
            if self.use_redis and self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    return len(keys)
                return 0
            else:
                # In-memory 캐시는 패턴 매칭 지원
                deleted = 0
                for key in list(self.memory_cache.cache.keys()):
                    if self._match_pattern(key, pattern):
                        await self.memory_cache.delete(key)
                        deleted += 1
                return deleted
        except Exception as e:
            logger.error(f"Cache clear pattern error for '{pattern}': {e}")
            return 0

    def _match_pattern(self, key: str, pattern: str) -> bool:
        """간단한 패턴 매칭 (* 와일드카드 지원)"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return key.startswith(prefix)
        if pattern.startswith("*"):
            suffix = pattern[1:]
            return key.endswith(suffix)
        return key == pattern

    async def exists(self, key: str) -> bool:
        """키 존재 여부 확인"""
        try:
            if self.use_redis and self.redis_client:
                return await self.redis_client.exists(key) > 0
            else:
                return await self.memory_cache.exists(key)
        except Exception as e:
            logger.error(f"Cache exists error for key '{key}': {e}")
            return False

    async def get_stats(self) -> dict:
        """캐시 통계"""
        try:
            if self.use_redis and self.redis_client:
                info = await self.redis_client.info("stats")
                return {
                    "type": "redis",
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "connected": True,
                }
            else:
                return self.memory_cache.get_stats()
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"type": "unknown", "error": str(e)}

    async def close(self):
        """캐시 연결 종료"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


# 전역 캐시 매니저 인스턴스
cache_manager = CacheManager()


# 유틸리티 함수들
def make_cache_key(*args) -> str:
    """캐시 키 생성 헬퍼"""
    return ":".join(str(arg) for arg in args)


async def cached(
    key_prefix: str,
    ttl: int = 300,
):
    """
    캐싱 데코레이터 (함수용)

    사용 예:
    @cached("user_data", ttl=600)
    async def get_user_data(user_id: int):
        return await fetch_from_db(user_id)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key = make_cache_key(key_prefix, *args, *kwargs.values())

            # 캐시에서 조회
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # 캐시 미스, 함수 실행
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)

            # 결과 캐싱
            await cache_manager.set(cache_key, result, ttl)
            return result

        return wrapper
    return decorator
