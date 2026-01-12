"""
Response Cache Manager (응답 캐싱 매니저)

AI API 응답을 캐싱하여 동일한 쿼리에 대한 중복 호출 방지
"""

import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# SECURITY: Whitelist of valid response types to prevent injection
VALID_RESPONSE_TYPES = {
    "market_analysis",
    "signal_validation",
    "risk_assessment",
    "portfolio_optimization",
    "anomaly_detection",
    "strategy_generation",
    "test",  # For testing
    "general"  # General purpose
}


class ResponseCacheManager:
    """
    응답 캐싱 매니저

    핵심 아이디어:
    1. 동일한 입력 → 동일한 출력 (결정론적 AI 응답)
    2. 짧은 시간 내 반복 쿼리 → 캐시 재사용
    3. 컨텍스트 해시로 캐시 키 생성

    비용 절감 효과:
    - 중복 API 호출 제거
    - 응답 속도 10~100배 향상
    - 월 $500~$1,000 절감 가능
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

        # 캐싱 전략 (응답 타입별 TTL)
        self.cache_ttl = {
            "market_analysis": 300,  # 5분 (시장 분석)
            "signal_validation": 60,  # 1분 (신호 검증)
            "risk_assessment": 120,  # 2분 (리스크 평가)
            "portfolio_optimization": 1800,  # 30분 (포트폴리오 최적화)
            "anomaly_detection": 180,  # 3분 (이상 징후)
            "strategy_generation": 3600,  # 1시간 (전략 생성)
        }

        # 통계
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "api_calls_saved": 0,
            "cost_saved_usd": 0.0,
        }

        logger.info("ResponseCacheManager initialized")

    def get_cache_key(
        self, response_type: str, query_data: Dict[str, Any]
    ) -> str:
        """
        캐시 키 생성

        Args:
            response_type: 응답 타입 (market_analysis, signal_validation, etc.)
            query_data: 쿼리 데이터 (입력 파라미터)

        Returns:
            해시된 캐시 키
        """
        # SECURITY: Validate response_type against whitelist to prevent injection
        if response_type not in VALID_RESPONSE_TYPES:
            logger.warning(f"Invalid response type attempted: {response_type}")
            raise ValueError(
                f"Invalid response type: {response_type}. "
                f"Must be one of: {', '.join(sorted(VALID_RESPONSE_TYPES))}"
            )

        # SECURITY: Sanitize response_type (only alphanumeric and underscore)
        if not re.match(r'^[a-z_]+$', response_type):
            raise ValueError(f"Invalid characters in response_type: {response_type}")

        # Serialize and sanitize query data
        try:
            query_str = json.dumps(query_data, sort_keys=True)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize query_data: {e}")
            raise ValueError("Invalid query_data: cannot serialize to JSON") from e

        # SECURITY: Remove any Redis special characters from query string
        # This prevents potential command injection via crafted query data
        query_str = re.sub(r'[*?\[\]{}]', '', query_str)

        # SHA-256 해시로 안전한 캐시 키 생성
        hash_obj = hashlib.sha256(
            f"{response_type}:{query_str}".encode("utf-8")
        )
        # Use full hash to prevent collisions
        cache_key = f"ai:response:{response_type}:{hash_obj.hexdigest()}"

        return cache_key

    async def get_cached_response(
        self, response_type: str, query_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        캐시된 응답 조회

        Args:
            response_type: 응답 타입
            query_data: 쿼리 데이터

        Returns:
            캐시된 응답 (없으면 None)
        """
        if not self.redis_client:
            return None

        cache_key = self.get_cache_key(response_type, query_data)

        try:
            cached = await self.redis_client.get(cache_key)

            if cached:
                self.stats["cache_hits"] += 1
                self.stats["api_calls_saved"] += 1

                # 비용 절감 계산 (응답 타입별 추정 비용)
                cost_per_call = self._estimate_cost_per_call(response_type)
                self.stats["cost_saved_usd"] += cost_per_call

                logger.debug(f"Response cache HIT: {response_type}")

                # SECURITY: Validate size before parsing to prevent memory exhaustion
                cached_size = len(cached) if isinstance(cached, (str, bytes)) else 0
                MAX_CACHED_RESPONSE_SIZE = 1_000_000  # 1MB limit

                if cached_size > MAX_CACHED_RESPONSE_SIZE:
                    logger.warning(
                        f"Cached response too large ({cached_size} bytes), "
                        f"exceeds limit ({MAX_CACHED_RESPONSE_SIZE} bytes). Skipping cache."
                    )
                    return None

                # JSON 파싱 with validation
                if isinstance(cached, bytes):
                    cached = cached.decode("utf-8")

                try:
                    parsed = json.loads(cached)

                    # SECURITY: Validate expected structure
                    if not isinstance(parsed, dict):
                        logger.error("Invalid cached response structure: not a dict")
                        return None

                    # Validate it has expected fields (basic sanity check)
                    if 'response' not in parsed and 'result' not in parsed:
                        logger.warning("Cached response missing expected fields")
                        # Still return it, might be valid but different format

                    return parsed

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse cached response JSON: {e}")
                    # Clear corrupt cache entry
                    await self.redis_client.delete(cache_key)
                    return None

            else:
                self.stats["cache_misses"] += 1
                logger.debug(f"Response cache MISS: {response_type}")
                return None

        except RuntimeError as e:
            # Event loop closed 에러 등 런타임 에러는 조용히 처리
            if "Event loop is closed" in str(e):
                logger.debug("Event loop closed, skipping cache read")
            else:
                logger.warning(f"Runtime error in cache read: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get cached response: {e}")
            return None

    async def set_cached_response(
        self,
        response_type: str,
        query_data: Dict[str, Any],
        response: Dict[str, Any],
        custom_ttl: Optional[int] = None,
    ):
        """
        응답 캐싱

        Args:
            response_type: 응답 타입
            query_data: 쿼리 데이터
            response: 캐싱할 응답
            custom_ttl: 커스텀 TTL (초)
        """
        if not self.redis_client:
            return

        cache_key = self.get_cache_key(response_type, query_data)
        ttl = custom_ttl or self.cache_ttl.get(response_type, 300)

        try:
            # JSON 직렬화
            response_json = json.dumps(response)

            await self.redis_client.setex(cache_key, ttl, response_json)

            logger.debug(f"Response cached: {response_type}, TTL={ttl}s")

        except Exception as e:
            logger.error(f"Failed to cache response: {e}")

    async def invalidate_cache(
        self, response_type: str, query_data: Optional[Dict[str, Any]] = None
    ):
        """
        캐시 무효화

        Args:
            response_type: 응답 타입
            query_data: 특정 쿼리 (None이면 타입 전체)
        """
        if not self.redis_client:
            return

        try:
            if query_data:
                # 특정 쿼리만 무효화
                cache_key = self.get_cache_key(response_type, query_data)
                await self.redis_client.delete(cache_key)
                logger.debug(f"Cache invalidated: {cache_key}")

            else:
                # 타입 전체 무효화
                pattern = f"response_cache:{response_type}:*"
                cursor = 0
                deleted = 0

                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor, match=pattern, count=100
                    )

                    if keys:
                        await self.redis_client.delete(*keys)
                        deleted += len(keys)

                    if cursor == 0:
                        break

                logger.info(f"Invalidated {deleted} cached responses for {response_type}")

        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")

    def _estimate_cost_per_call(self, response_type: str) -> float:
        """
        응답 타입별 API 호출 비용 추정

        Args:
            response_type: 응답 타입

        Returns:
            1회 호출 비용 (USD)
        """
        # 응답 타입별 평균 토큰 수 및 비용 추정
        cost_estimates = {
            "market_analysis": 0.015,  # ~1,000 tokens
            "signal_validation": 0.010,  # ~500 tokens
            "risk_assessment": 0.012,  # ~800 tokens
            "portfolio_optimization": 0.030,  # ~2,000 tokens
            "anomaly_detection": 0.008,  # ~500 tokens
            "strategy_generation": 0.050,  # ~3,500 tokens
        }

        return cost_estimates.get(response_type, 0.010)

    async def batch_cache_responses(
        self, responses: List[Dict[str, Any]]
    ):
        """
        배치로 여러 응답 캐싱

        Args:
            responses: [
                {
                    "response_type": "market_analysis",
                    "query_data": {...},
                    "response": {...}
                },
                ...
            ]
        """
        if not self.redis_client:
            return

        try:
            # Redis Pipeline 사용 (배치 처리)
            pipe = self.redis_client.pipeline()

            for item in responses:
                response_type = item["response_type"]
                query_data = item["query_data"]
                response = item["response"]

                cache_key = self.get_cache_key(response_type, query_data)
                ttl = self.cache_ttl.get(response_type, 300)
                response_json = json.dumps(response)

                pipe.setex(cache_key, ttl, response_json)

            await pipe.execute()

            logger.info(f"Batch cached {len(responses)} responses")

        except Exception as e:
            logger.error(f"Failed to batch cache responses: {e}")

    def should_cache(
        self, response_type: str, query_data: Dict[str, Any]
    ) -> bool:
        """
        캐싱 여부 결정

        Args:
            response_type: 응답 타입
            query_data: 쿼리 데이터

        Returns:
            캐싱 여부
        """
        # 캐싱하지 않을 조건들
        no_cache_conditions = [
            # 실시간 데이터 (symbol이 있고 timeframe이 1m 이하)
            (
                "symbol" in query_data
                and query_data.get("timeframe", "5m") in ["1s", "1m"]
            ),
            # 사용자별 개인화된 데이터
            "user_specific" in query_data and query_data["user_specific"],
            # 명시적으로 캐시 비활성화
            query_data.get("no_cache", False),
        ]

        return not any(no_cache_conditions)

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        total = self.stats["cache_hits"] + self.stats["cache_misses"]
        hit_rate = (
            self.stats["cache_hits"] / total * 100 if total > 0 else 0
        )

        return {
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "api_calls_saved": self.stats["api_calls_saved"],
            "cost_saved_usd": round(self.stats["cost_saved_usd"], 2),
        }

    async def warm_up_cache(
        self, response_type: str, common_queries: List[Dict[str, Any]]
    ):
        """
        캐시 사전 워밍업

        자주 사용되는 쿼리를 미리 캐싱하여 초기 히트율 향상

        Args:
            response_type: 응답 타입
            common_queries: 자주 사용되는 쿼리 목록
        """
        logger.info(
            f"Warming up cache for {response_type}: {len(common_queries)} queries"
        )

        # TODO: 실제 구현 시 AI API 호출 후 캐싱
        # 여기서는 예시만 제공

        for _query_data in common_queries:
            # response = await call_ai_api(response_type, query_data)
            # await self.set_cached_response(response_type, query_data, response)
            pass
