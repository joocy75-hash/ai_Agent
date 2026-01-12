"""
Prompt Cache Manager (프롬프트 캐싱 매니저)

반복되는 프롬프트를 캐싱하여 AI API 호출 비용 절감
"""

import hashlib
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PromptCacheManager:
    """
    프롬프트 캐싱 매니저

    핵심 아이디어:
    1. 시스템 프롬프트는 거의 변하지 않음 → 캐싱
    2. 동일한 컨텍스트 재사용 → 토큰 비용 절감
    3. Anthropic Prompt Caching 활용

    비용 절감 효과:
    - 캐시된 토큰: 90% 할인 (예: $15/MTok → $1.50/MTok)
    - 반복되는 시스템 프롬프트 재사용
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

        # 캐싱 전략
        self.cache_ttl = {
            "system_prompt": 3600 * 24,  # 24시간 (시스템 프롬프트)
            "agent_prompt": 3600 * 12,  # 12시간 (에이전트 프롬프트)
            "market_data": 300,  # 5분 (시장 데이터)
            "strategy_context": 1800,  # 30분 (전략 컨텍스트)
        }

        # 통계
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "tokens_saved": 0,
        }

        logger.info("PromptCacheManager initialized")

    def get_cache_key(
        self, prompt_type: str, context_data: Dict[str, Any]
    ) -> str:
        """
        캐시 키 생성

        Args:
            prompt_type: 프롬프트 타입 (system, agent, market_data, strategy)
            context_data: 컨텍스트 데이터

        Returns:
            해시된 캐시 키
        """
        # 컨텍스트를 정렬된 문자열로 변환
        context_str = str(sorted(context_data.items()))

        # SHA-256 해시
        hash_obj = hashlib.sha256(
            f"{prompt_type}:{context_str}".encode("utf-8")
        )
        cache_key = f"prompt_cache:{prompt_type}:{hash_obj.hexdigest()[:16]}"

        return cache_key

    async def get_cached_prompt(
        self, prompt_type: str, context_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        캐시된 프롬프트 조회

        Args:
            prompt_type: 프롬프트 타입
            context_data: 컨텍스트 데이터

        Returns:
            캐시된 프롬프트 (없으면 None)
        """
        if not self.redis_client:
            return None

        cache_key = self.get_cache_key(prompt_type, context_data)

        try:
            cached = await self.redis_client.get(cache_key)

            if cached:
                self.stats["cache_hits"] += 1
                logger.debug(f"Prompt cache HIT: {prompt_type}")
                return cached.decode("utf-8") if isinstance(cached, bytes) else cached
            else:
                self.stats["cache_misses"] += 1
                logger.debug(f"Prompt cache MISS: {prompt_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to get cached prompt: {e}")
            return None

    async def set_cached_prompt(
        self, prompt_type: str, context_data: Dict[str, Any], prompt: str
    ):
        """
        프롬프트 캐싱

        Args:
            prompt_type: 프롬프트 타입
            context_data: 컨텍스트 데이터
            prompt: 캐싱할 프롬프트
        """
        if not self.redis_client:
            return

        cache_key = self.get_cache_key(prompt_type, context_data)
        ttl = self.cache_ttl.get(prompt_type, 3600)

        try:
            await self.redis_client.setex(cache_key, ttl, prompt)

            # 토큰 수 추정 (간단히 단어 수 * 1.3)
            estimated_tokens = len(prompt.split()) * 1.3
            self.stats["tokens_saved"] += estimated_tokens

            logger.debug(f"Prompt cached: {prompt_type}, TTL={ttl}s")

        except Exception as e:
            logger.error(f"Failed to cache prompt: {e}")

    def build_cacheable_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        cache_system: bool = True,
    ) -> Dict[str, Any]:
        """
        Anthropic Prompt Caching용 메시지 구조 생성

        Args:
            system_prompt: 시스템 프롬프트 (캐싱 대상)
            user_prompt: 사용자 프롬프트
            cache_system: 시스템 프롬프트 캐싱 여부

        Returns:
            Anthropic API용 메시지 구조
        """
        messages = []

        # 시스템 프롬프트 (캐싱 가능)
        if cache_system:
            messages.append({
                "role": "system",
                "content": system_prompt,
                "cache_control": {"type": "ephemeral"},  # Anthropic 캐싱
            })
        else:
            messages.append({
                "role": "system",
                "content": system_prompt,
            })

        # 사용자 프롬프트
        messages.append({
            "role": "user",
            "content": user_prompt,
        })

        return {"messages": messages}

    async def get_agent_system_prompt(
        self, agent_type: str, config: Dict[str, Any] = None
    ) -> str:
        """
        에이전트별 시스템 프롬프트 조회 (캐싱)

        Args:
            agent_type: 에이전트 타입 (market_regime, signal_validator, etc.)
            config: 설정 (임계값 등)

        Returns:
            시스템 프롬프트
        """
        config = config or {}

        # 캐시 조회
        cached = await self.get_cached_prompt(
            "agent_prompt",
            {"agent_type": agent_type, **config},
        )

        if cached:
            return cached

        # 캐시 미스: 프롬프트 생성
        prompt = self._generate_agent_prompt(agent_type, config)

        # 캐싱
        await self.set_cached_prompt(
            "agent_prompt",
            {"agent_type": agent_type, **config},
            prompt,
        )

        return prompt

    def _generate_agent_prompt(
        self, agent_type: str, config: Dict[str, Any]
    ) -> str:
        """에이전트별 시스템 프롬프트 생성"""

        if agent_type == "market_regime":
            return f"""You are a Market Regime Analysis AI.

Analyze market conditions and classify into:
- TRENDING: ADX > {config.get('trending_threshold', 25)}
- RANGING: ADX < {config.get('ranging_threshold', 20)}
- VOLATILE: ATR ratio > {config.get('volatile_threshold', 2.0)}
- LOW_VOLUME: Volume < {config.get('low_volume_threshold', 0.3)} of average

Return JSON format:
{{"regime": "TRENDING", "confidence": 0.85, "indicators": {{...}}}}"""

        elif agent_type == "signal_validator":
            return f"""You are a Trading Signal Validator AI.

Validate trading signals with these rules:
- Min confidence: {config.get('min_confidence', 0.65)}
- Check market regime alignment
- Detect false signals
- Risk level assessment

Return JSON format:
{{"approved": true, "confidence": 0.85, "reason": "..."}}"""

        elif agent_type == "anomaly_detector":
            return f"""You are an Anomaly Detection AI.

Detect trading bot anomalies:
- Excessive trading: > {config.get('max_trades_per_10min', 20)} trades/10min
- Losing streak: {config.get('losing_streak', 7)}/10 losses
- High slippage: > {config.get('max_slippage', 0.5)}%
- API errors: > {config.get('max_error_rate', 0.3)} error rate

Return JSON format:
{{"anomaly_type": "excessive_trading", "severity": "high", "action": "..."}}"""

        else:
            return f"You are a {agent_type} AI assistant."

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        total = self.stats["cache_hits"] + self.stats["cache_misses"]
        hit_rate = (
            self.stats["cache_hits"] / total * 100 if total > 0 else 0
        )

        # 비용 절감 추정
        # 가정: 캐시된 토큰은 90% 할인
        tokens_saved = self.stats["tokens_saved"]
        cost_per_million = 15.0  # $15/MTok (Claude Sonnet 기준)
        savings = (tokens_saved / 1_000_000) * cost_per_million * 0.9

        return {
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "hit_rate_percent": hit_rate,
            "tokens_saved": int(tokens_saved),
            "estimated_savings_usd": round(savings, 2),
        }

    async def clear_cache(self, prompt_type: Optional[str] = None):
        """캐시 초기화"""
        if not self.redis_client:
            return

        try:
            if prompt_type:
                pattern = f"prompt_cache:{prompt_type}:*"
            else:
                pattern = "prompt_cache:*"

            # Redis SCAN으로 키 찾기
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

            logger.info(f"Cleared {deleted} cached prompts")

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
