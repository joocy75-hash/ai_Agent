"""
Redis 클라이언트 (Redis Client)

에이전트 시스템의 Redis 연동 관리
- 비동기 Redis 클라이언트
- 연결 풀 관리
- 데이터 캐싱
- Pub/Sub 메시징

관련 문서: AGENT_SYSTEM_WORK_PLAN.md
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, List, Callable
from datetime import timedelta

try:
    import redis.asyncio as aioredis
    from redis.asyncio import Redis, ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None
    ConnectionPool = None

from .config import get_agent_config, RedisConfig

logger = logging.getLogger(__name__)


class RedisClient:
    """
    비동기 Redis 클라이언트 (Async Redis Client)

    에이전트 간 데이터 공유 및 메시징을 위한 Redis 클라이언트

    주요 기능:
    - 연결 풀 관리
    - 키-값 저장/조회
    - 해시맵 관리
    - Pub/Sub 메시징
    - TTL 관리

    사용 예:
    ```python
    redis_client = await get_redis_client()
    await redis_client.set("key", "value", ttl=60)
    value = await redis_client.get("key")
    ```
    """

    def __init__(self, config: Optional[RedisConfig] = None):
        """
        Redis 클라이언트 초기화

        Args:
            config: Redis 설정 (None이면 전역 설정 사용)
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "redis package is not installed. "
                "Install it with: pip install redis"
            )

        self.config = config or get_agent_config().redis
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._pubsub = None
        self._subscriptions: Dict[str, List[Callable]] = {}

    async def connect(self):
        """Redis 서버에 연결"""
        if self._client:
            logger.warning("Redis client is already connected")
            return

        try:
            # 연결 풀 생성
            self._pool = ConnectionPool(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                decode_responses=self.config.decode_responses,
            )

            # Redis 클라이언트 생성
            self._client = Redis(connection_pool=self._pool)

            # 연결 테스트
            await self._client.ping()

            logger.info(
                f"✅ Redis connected: {self.config.host}:{self.config.port}/{self.config.db}"
            )

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """
        Redis 연결 종료 및 리소스 정리

        적절한 순서로 정리하여 리소스 누수 방지:
        1. Pub/Sub 채널 정리
        2. 클라이언트 연결 종료 및 대기
        3. 연결 풀 정리
        """
        # 1. Pub/Sub 정리
        if self._pubsub:
            try:
                # 모든 채널에서 unsubscribe
                await self._pubsub.unsubscribe()
                await self._pubsub.close()
                logger.info("Pub/Sub connection closed")
            except Exception as e:
                logger.error(f"Error closing Pub/Sub: {e}")
            finally:
                self._pubsub = None

        # 2. 클라이언트 정리 (연결 드레이닝)
        if self._client:
            try:
                # close()는 즉시 반환, aclose()는 대기
                await self._client.aclose()
                logger.info("Redis client closed")
            except Exception as e:
                logger.error(f"Error closing Redis client: {e}")
            finally:
                self._client = None

        # 3. 연결 풀 정리 (모든 연결 해제)
        if self._pool:
            try:
                # disconnect()는 풀의 모든 연결을 정리
                await self._pool.disconnect()
                logger.info("Redis connection pool disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Redis pool: {e}")
            finally:
                self._pool = None

        logger.info("✅ Redis fully disconnected and cleaned up")

    def _ensure_connected(self):
        """연결 상태 확인"""
        if not self._client:
            raise RuntimeError("Redis client is not connected. Call connect() first.")

    # ============================================================
    # 기본 키-값 작업
    # ============================================================

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """
        키-값 저장

        Args:
            key: 키
            value: 값
            ttl: Time To Live (초)
            serialize: JSON 직렬화 여부

        Returns:
            성공 여부
        """
        self._ensure_connected()

        try:
            if serialize and not isinstance(value, str):
                value = json.dumps(value)

            if ttl:
                await self._client.setex(key, ttl, value)
            else:
                await self._client.set(key, value)

            return True

        except Exception as e:
            logger.error(f"Failed to set key '{key}': {e}")
            return False

    async def get(
        self,
        key: str,
        deserialize: bool = True,
        default: Any = None
    ) -> Any:
        """
        키로 값 조회

        Args:
            key: 키
            deserialize: JSON 역직렬화 여부
            default: 키가 없을 때 반환할 기본값

        Returns:
            값 (없으면 default)
        """
        self._ensure_connected()

        try:
            value = await self._client.get(key)

            if value is None:
                return default

            if deserialize and isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

            return value

        except Exception as e:
            logger.error(f"Failed to get key '{key}': {e}")
            return default

    async def delete(self, *keys: str) -> int:
        """
        키 삭제

        Args:
            *keys: 삭제할 키 목록

        Returns:
            삭제된 키 개수
        """
        self._ensure_connected()

        try:
            return await self._client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """
        키 존재 여부 확인

        Args:
            *keys: 확인할 키 목록

        Returns:
            존재하는 키 개수
        """
        self._ensure_connected()

        try:
            return await self._client.exists(*keys)
        except Exception as e:
            logger.error(f"Failed to check existence of keys {keys}: {e}")
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        """
        키 만료 시간 설정

        Args:
            key: 키
            seconds: 만료 시간 (초)

        Returns:
            성공 여부
        """
        self._ensure_connected()

        try:
            return await self._client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Failed to set expiration for key '{key}': {e}")
            return False

    # ============================================================
    # 해시맵 작업
    # ============================================================

    async def hset(
        self,
        name: str,
        key: str,
        value: Any,
        serialize: bool = True
    ) -> int:
        """
        해시맵에 필드 저장

        Args:
            name: 해시맵 이름
            key: 필드 키
            value: 필드 값
            serialize: JSON 직렬화 여부

        Returns:
            새로 생성된 필드 수
        """
        self._ensure_connected()

        try:
            if serialize and not isinstance(value, str):
                value = json.dumps(value)

            return await self._client.hset(name, key, value)

        except Exception as e:
            logger.error(f"Failed to hset '{name}':'{key}': {e}")
            return 0

    async def hget(
        self,
        name: str,
        key: str,
        deserialize: bool = True,
        default: Any = None
    ) -> Any:
        """
        해시맵에서 필드 조회

        Args:
            name: 해시맵 이름
            key: 필드 키
            deserialize: JSON 역직렬화 여부
            default: 필드가 없을 때 반환할 기본값

        Returns:
            필드 값 (없으면 default)
        """
        self._ensure_connected()

        try:
            value = await self._client.hget(name, key)

            if value is None:
                return default

            if deserialize and isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value

            return value

        except Exception as e:
            logger.error(f"Failed to hget '{name}':'{key}': {e}")
            return default

    async def hgetall(
        self,
        name: str,
        deserialize: bool = True
    ) -> Dict[str, Any]:
        """
        해시맵 전체 조회

        Args:
            name: 해시맵 이름
            deserialize: JSON 역직렬화 여부

        Returns:
            해시맵 딕셔너리
        """
        self._ensure_connected()

        try:
            data = await self._client.hgetall(name)

            if deserialize:
                result = {}
                for key, value in data.items():
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value
                return result

            return data

        except Exception as e:
            logger.error(f"Failed to hgetall '{name}': {e}")
            return {}

    async def hdel(self, name: str, *keys: str) -> int:
        """
        해시맵 필드 삭제

        Args:
            name: 해시맵 이름
            *keys: 삭제할 필드 키 목록

        Returns:
            삭제된 필드 수
        """
        self._ensure_connected()

        try:
            return await self._client.hdel(name, *keys)
        except Exception as e:
            logger.error(f"Failed to hdel '{name}': {e}")
            return 0

    # ============================================================
    # Pub/Sub 메시징
    # ============================================================

    async def publish(self, channel: str, message: Any) -> int:
        """
        채널에 메시지 발행

        Args:
            channel: 채널 이름
            message: 메시지 (자동으로 JSON 직렬화)

        Returns:
            메시지를 받은 구독자 수
        """
        self._ensure_connected()

        try:
            if not isinstance(message, str):
                message = json.dumps(message)

            return await self._client.publish(channel, message)

        except Exception as e:
            logger.error(f"Failed to publish to channel '{channel}': {e}")
            return 0

    async def subscribe(self, channel: str, callback: Callable[[Dict], None]):
        """
        채널 구독

        Args:
            channel: 채널 이름
            callback: 메시지 수신 시 호출할 콜백 함수
        """
        self._ensure_connected()

        if not self._pubsub:
            self._pubsub = self._client.pubsub()

        # 구독 등록
        await self._pubsub.subscribe(channel)

        # 콜백 저장
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        self._subscriptions[channel].append(callback)

        logger.info(f"Subscribed to channel '{channel}'")

    async def listen(self):
        """
        Pub/Sub 메시지 리스닝 (백그라운드 태스크로 실행 권장)
        """
        if not self._pubsub:
            logger.warning("No active subscriptions")
            return

        try:
            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]

                    # JSON 역직렬화
                    try:
                        data = json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        pass

                    # 콜백 호출
                    if channel in self._subscriptions:
                        for callback in self._subscriptions[channel]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                            except Exception as e:
                                logger.error(f"Error in subscription callback: {e}")

        except Exception as e:
            logger.error(f"Error in pub/sub listener: {e}")

    # ============================================================
    # 유틸리티
    # ============================================================

    async def ping(self) -> bool:
        """Redis 서버 핑 테스트"""
        self._ensure_connected()

        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    async def info(self) -> Dict[str, Any]:
        """Redis 서버 정보 조회"""
        self._ensure_connected()

        try:
            return await self._client.info()
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}


# 전역 Redis 클라이언트 인스턴스 (싱글톤)
_global_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """
    전역 Redis 클라이언트 가져오기 (싱글톤 패턴)

    Returns:
        Redis 클라이언트
    """
    global _global_redis_client

    if _global_redis_client is None:
        _global_redis_client = RedisClient()
        await _global_redis_client.connect()

    return _global_redis_client


async def close_redis_client():
    """전역 Redis 클라이언트 종료"""
    global _global_redis_client

    if _global_redis_client:
        await _global_redis_client.disconnect()
        _global_redis_client = None
