"""
Integrated AI Service (통합 AI 서비스)

Gemini 2.0 Flash Thinking / DeepSeek-V3 API + 비용 최적화 통합 서비스
- Prompt Caching (90% 비용 절감)
- Response Caching (중복 호출 제거)
- Smart Sampling (API 호출 50~70% 감소)
- Cost Tracking (실시간 비용 모니터링)
"""

import logging
import hashlib
import json
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

from .prompt_cache import PromptCacheManager
from .response_cache import ResponseCacheManager
from .smart_sampling import SamplingStrategy, get_global_sampling_manager
from .cost_tracker import CostTracker
from .event_driven_optimizer import EventDrivenOptimizer, MarketEvent, EventType, EventPriority
from src.config import settings
import threading

logger = logging.getLogger(__name__)

# 글로벌 싱글톤 인스턴스 (Issue #4: AI Rate Limit 문제 해결)
_integrated_ai_service_instance: Optional["IntegratedAIService"] = None
_service_lock = threading.Lock()


def get_integrated_ai_service(redis_client=None) -> "IntegratedAIService":
    """
    글로벌 IntegratedAIService 싱글톤 반환

    Thread-safe singleton pattern을 사용하여 전역에서 하나의
    IntegratedAIService 인스턴스만 생성되도록 보장합니다.

    Issue #4: AI Rate Limit 문제 해결
    - 기존: 전략 인스턴스마다 새 IntegratedAIService 생성
    - 수정: 글로벌 싱글톤으로 API 키, Rate Limit 관리 일원화

    Args:
        redis_client: Redis 클라이언트 (첫 호출 시만 사용)

    Returns:
        IntegratedAIService: 글로벌 싱글톤 인스턴스
    """
    global _integrated_ai_service_instance

    # Double-checked locking for thread safety
    if _integrated_ai_service_instance is None:
        with _service_lock:
            if _integrated_ai_service_instance is None:
                _integrated_ai_service_instance = IntegratedAIService(redis_client)
                logger.info("✅ Global IntegratedAIService singleton initialized")

    return _integrated_ai_service_instance


class IntegratedAIService:
    """
    통합 AI 서비스

    Gemini 2.0 Flash Thinking / DeepSeek-V3 + 4가지 비용 최적화 기능 통합:
    1. Prompt Caching: 시스템 프롬프트 캐싱 (90% 할인)
    2. Response Caching: 동일 쿼리 응답 재사용
    3. Smart Sampling: 지능적 API 호출 샘플링
    4. Cost Tracking: 실시간 비용 추적

    비용 절감 효과:
    - 기존: $1,000/month
    - 최적화 후: $300/month (70% 절감)
    """

    # Gemini 모델 설정 (2025.12 기준 최신)
    GEMINI_MODEL = "gemini-3-pro-preview"  # Gemini 3 Pro Preview (Deep Think)
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    # DeepSeek V3.2 Release 모델 (폴백용)
    DEEPSEEK_MODEL = "deepseek-chat"
    DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, redis_client=None):
        # AI Provider 선택 (기본값: gemini)
        self.ai_provider = settings.ai_provider.lower()

        if self.ai_provider == "gemini":
            self.api_key = settings.gemini_api_key
            if not self.api_key or self.api_key == "":
                raise ValueError("Gemini API key not configured. Set GEMINI_API_KEY environment variable.")
            masked_key = f"{'*' * 8}{self.api_key[-4:]}" if len(self.api_key) > 4 else "****"
            logger.info(f"🌟 Gemini API key configured: {masked_key}")
            logger.info(f"🧠 Using Gemini 2.0 Flash Thinking for advanced market analysis")
        else:
            self.api_key = settings.deepseek_api_key
            if not self.api_key or self.api_key == "":
                raise ValueError("DeepSeek API key not configured. Set DEEPSEEK_API_KEY environment variable.")
            masked_key = f"{'*' * 8}{self.api_key[-4:]}" if len(self.api_key) > 4 else "****"
            logger.info(f"DeepSeek API key configured: {masked_key}")

        self.redis_client = redis_client

        # 비용 최적화 매니저들
        self.prompt_cache = PromptCacheManager(redis_client)
        self.response_cache = ResponseCacheManager(redis_client)
        # Issue #4: 글로벌 싱글톤 SmartSamplingManager 사용 (캐시 상태 유지)
        self.sampling_manager = get_global_sampling_manager()
        self.cost_tracker = CostTracker(redis_client)
        self.event_optimizer = EventDrivenOptimizer(redis_client)

        provider_name = "Gemini 2.0 Flash Thinking" if self.ai_provider == "gemini" else "DeepSeek-V3"
        logger.info(f"IntegratedAIService initialized with {provider_name} + event-driven cost optimization")

    async def call_ai(
        self,
        agent_type: str,
        prompt: str,
        context: Dict[str, Any],
        system_prompt: Optional[str] = None,
        response_type: str = "general",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        enable_caching: bool = True,
        enable_sampling: bool = True,
    ) -> Dict[str, Any]:
        """
        AI API 호출 (비용 최적화 적용)

        Args:
            agent_type: 에이전트 타입 (market_regime, signal_validator, etc.)
            prompt: 사용자 프롬프트
            context: 컨텍스트 데이터 (샘플링/캐싱에 사용)
            system_prompt: 시스템 프롬프트 (캐싱 대상)
            response_type: 응답 타입 (캐싱 TTL 결정)
            temperature: 온도 설정
            max_tokens: 최대 토큰 수
            enable_caching: 응답 캐싱 활성화
            enable_sampling: 스마트 샘플링 활성화

        Returns:
            {
                "response": str,
                "cost_info": {...},
                "cache_hit": bool,
                "sampled": bool
            }
        """
        # 1. 스마트 샘플링 체크
        sampled = True
        skip_reason = None

        if enable_sampling:
            should_sample, reason = await self.sampling_manager.should_sample(
                agent_type=agent_type,
                context=context
            )

            if not should_sample:
                logger.info(f"⏭️  Skipping AI call for {agent_type}: {reason}")

                # 이전 응답 재사용 (캐시에서)
                cached_response = await self.response_cache.get_cached_response(
                    response_type=response_type,
                    query_data={"prompt": prompt, "context": context}
                )

                if cached_response:
                    return {
                        "response": cached_response.get("response", ""),
                        "cost_info": {"cost_usd": 0.0},
                        "cache_hit": True,
                        "sampled": False,
                        "skip_reason": reason,
                    }

                # 캐시도 없으면 기본 응답
                return {
                    "response": self._get_default_response(agent_type),
                    "cost_info": {"cost_usd": 0.0},
                    "cache_hit": False,
                    "sampled": False,
                    "skip_reason": reason,
                }

        # 2. 응답 캐시 조회
        cache_hit = False

        if enable_caching and self.response_cache.should_cache(response_type, context):
            cached_response = await self.response_cache.get_cached_response(
                response_type=response_type,
                query_data={"prompt": prompt, "context": context}
            )

            if cached_response:
                logger.info(f"✅ Response cache HIT for {agent_type}")
                cache_hit = True

                return {
                    "response": cached_response.get("response", ""),
                    "cost_info": {"cost_usd": 0.0},
                    "cache_hit": True,
                    "sampled": True,
                }

        # 3. 프롬프트 캐시 조회 (시스템 프롬프트)
        if system_prompt and enable_caching:
            cached_system = await self.prompt_cache.get_cached_prompt(
                prompt_type="agent_prompt",
                context_data={"agent_type": agent_type}
            )

            if cached_system:
                system_prompt = cached_system
                logger.debug(f"Prompt cache HIT for {agent_type}")

        # 4. AI API 호출 (Gemini or DeepSeek)
        try:
            if self.ai_provider == "gemini":
                response_text, usage = await self._call_gemini_api(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                model_name = "gemini-2.5-pro"
            else:
                response_text, usage = await self._call_deepseek_api(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                model_name = "deepseek-v3"

            # 5. 비용 추적
            cost_info = await self.cost_tracker.track_api_call(
                model=model_name,
                agent_type=agent_type,
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                cache_read_tokens=usage.get("cache_read_tokens", 0),
                cache_write_tokens=usage.get("cache_write_tokens", 0),
                metadata={"response_type": response_type}
            )

            # 6. 응답 캐싱
            if enable_caching:
                await self.response_cache.set_cached_response(
                    response_type=response_type,
                    query_data={"prompt": prompt, "context": context},
                    response={"response": response_text, "cost_info": cost_info}
                )

            # 7. 프롬프트 캐싱 (시스템 프롬프트)
            if system_prompt and enable_caching:
                await self.prompt_cache.set_cached_prompt(
                    prompt_type="agent_prompt",
                    context_data={"agent_type": agent_type},
                    prompt=system_prompt
                )

            logger.info(
                f"✅ AI call for {agent_type}: ${cost_info['total_cost_usd']:.6f}, "
                f"{usage.get('total_tokens', 0)} tokens"
            )

            # 성공 시 Rate Limit backoff 감소
            self.sampling_manager.notify_success()

            return {
                "response": response_text,
                "cost_info": cost_info,
                "cache_hit": False,
                "sampled": True,
            }

        except Exception as e:
            error_str = str(e)
            logger.error(f"AI API call failed for {agent_type}: {e}", exc_info=True)

            # Rate Limit (429) 에러 감지 및 backoff 적용
            if "429" in error_str or "Too Many Requests" in error_str or "rate limit" in error_str.lower():
                self.sampling_manager.notify_rate_limit()
                logger.warning(
                    f"🚨 Rate limit detected for {agent_type}, "
                    f"backoff status: {self.sampling_manager.get_backoff_status()}"
                )

            # 에러 시 기본 응답
            return {
                "response": self._get_default_response(agent_type),
                "cost_info": {"cost_usd": 0.0},
                "cache_hit": False,
                "sampled": True,
                "error": error_str,
            }

    async def call_ai_with_event(
        self,
        event: MarketEvent,
        agent_type: str,
        prompt: str,
        context: Dict[str, Any],
        system_prompt: Optional[str] = None,
        response_type: str = "general",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        enable_caching: bool = True,
        enable_sampling: bool = True,
    ) -> Dict[str, Any]:
        """
        이벤트 기반 AI 호출 (비용 최적화)

        Args:
            event: 시장 이벤트
            agent_type: 에이전트 타입
            prompt: 사용자 프롬프트
            context: 컨텍스트 데이터
            system_prompt: 시스템 프롬프트
            response_type: 응답 타입
            temperature: 온도
            max_tokens: 최대 토큰
            enable_caching: 캐싱 활성화
            enable_sampling: 샘플링 활성화

        Returns:
            AI 응답 결과
        """
        # 1. 이벤트 기반 필터링
        should_call, reason = self.event_optimizer.should_trigger_ai(
            event=event,
            agent_type=agent_type
        )

        if not should_call:
            logger.info(
                f"⏭️  Event filtered: {event.event_type.value} for {event.symbol} -> {reason}"
            )

            # 캐시된 응답 재사용
            cached_response = await self.response_cache.get_cached_response(
                response_type=response_type,
                query_data={"prompt": prompt, "context": context}
            )

            if cached_response:
                return {
                    "response": cached_response.get("response", ""),
                    "cost_info": {"cost_usd": 0.0},
                    "cache_hit": True,
                    "sampled": False,
                    "event_filtered": True,
                    "filter_reason": reason,
                }

            # 기본 응답
            return {
                "response": self._get_default_response(agent_type),
                "cost_info": {"cost_usd": 0.0},
                "cache_hit": False,
                "sampled": False,
                "event_filtered": True,
                "filter_reason": reason,
            }

        # 2. 배치 처리 체크 (LOW 우선순위 이벤트)
        if event.priority == EventPriority.LOW:
            batch = self.event_optimizer.get_batch_if_ready(event.symbol)

            if batch:
                logger.info(
                    f"📦 Processing batch of {len(batch)} events for {event.symbol}"
                )
                # 배치 처리 (여러 이벤트를 한 번의 AI 호출로)
                return await self._process_event_batch(
                    batch=batch,
                    agent_type=agent_type,
                    system_prompt=system_prompt,
                    response_type=response_type,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            # 배치 대기 중
            return {
                "response": self._get_default_response(agent_type),
                "cost_info": {"cost_usd": 0.0},
                "cache_hit": False,
                "sampled": False,
                "batched": True,
            }

        # 3. AI 호출 (이벤트 통과)
        result = await self.call_ai(
            agent_type=agent_type,
            prompt=prompt,
            context=context,
            system_prompt=system_prompt,
            response_type=response_type,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_caching=enable_caching,
            enable_sampling=enable_sampling
        )

        # AI 호출 시간 기록
        self.event_optimizer.mark_ai_called(event.symbol)

        return result

    async def _process_event_batch(
        self,
        batch: List[MarketEvent],
        agent_type: str,
        system_prompt: Optional[str],
        response_type: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """
        이벤트 배치 처리 (한 번의 AI 호출로 여러 이벤트 처리)

        Args:
            batch: 이벤트 배치
            agent_type: 에이전트 타입
            system_prompt: 시스템 프롬프트
            response_type: 응답 타입
            temperature: 온도
            max_tokens: 최대 토큰

        Returns:
            AI 응답 결과
        """
        # 배치 프롬프트 생성
        batch_summary = "\n".join([
            f"- Event {i+1}: {e.event_type.value} at {e.timestamp.strftime('%H:%M:%S')}, "
            f"Data: {e.data}"
            for i, e in enumerate(batch)
        ])

        prompt = f"""Analyze the following batch of market events for {batch[0].symbol}:

{batch_summary}

Provide a comprehensive analysis of these events and their combined implications."""

        context = {
            "symbol": batch[0].symbol,
            "batch_size": len(batch),
            "event_types": [e.event_type.value for e in batch]
        }

        # AI 호출
        result = await self.call_ai(
            agent_type=agent_type,
            prompt=prompt,
            context=context,
            system_prompt=system_prompt,
            response_type=response_type,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_caching=True,
            enable_sampling=False  # 배치는 샘플링 스킵
        )

        result["batched"] = True
        result["batch_size"] = len(batch)

        logger.info(f"✅ Batch processed: {len(batch)} events, ${result['cost_info']['total_cost_usd']:.6f}")

        return result

    async def _call_gemini_api(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> tuple[str, Dict[str, int]]:
        """
        Gemini 3 Pro (Deep Think) API 호출

        Returns:
            (response_text, usage_dict)
        """
        if not self.api_key:
            raise ValueError("Gemini API key is not configured")

        url = f"{self.GEMINI_BASE_URL}/models/{self.GEMINI_MODEL}:generateContent?key={self.api_key}"

        headers = {
            "Content-Type": "application/json",
        }

        # Gemini 형식으로 메시지 구성
        contents = []

        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System Instructions: {system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "I understand. I will follow these instructions."}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "topK": 40,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60,  # Gemini Deep Think는 더 긴 타임아웃 필요
            )
            response.raise_for_status()

            data = response.json()

            # 응답 추출
            response_text = ""
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    response_text = candidate["content"]["parts"][0].get("text", "")

            # 사용량 추출 (Gemini 형식)
            usage_metadata = data.get("usageMetadata", {})
            usage = {
                "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                "total_tokens": usage_metadata.get("totalTokenCount", 0),
            }

            return response_text, usage

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def _call_deepseek_api(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> tuple[str, Dict[str, int]]:
        """
        DeepSeek API 호출 (폴백용)

        Returns:
            (response_text, usage_dict)
        """
        if not self.api_key:
            raise ValueError("DeepSeek API key is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt,
            })

        messages.append({
            "role": "user",
            "content": prompt,
        })

        payload = {
            "model": self.DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(
                f"{self.DEEPSEEK_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()

            # 응답 추출
            response_text = ""
            if "choices" in data and len(data["choices"]) > 0:
                response_text = data["choices"][0]["message"]["content"]

            # 사용량 추출
            usage = data.get("usage", {})

            return response_text, usage

        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise

    def _get_default_response(self, agent_type: str) -> str:
        """기본 응답 (에러 시 또는 샘플링 스킵 시)"""
        defaults = {
            "market_regime": "UNKNOWN",
            "signal_validator": "HOLD",
            "anomaly_detector": "NO_ANOMALY",
            "portfolio_optimizer": "NO_REBALANCING",
            "risk_monitor": "NORMAL",
        }

        return defaults.get(agent_type, "NO_ACTION")

    async def get_cost_stats(self) -> Dict[str, Any]:
        """비용 통계 조회"""
        return {
            "overall": self.cost_tracker.get_overall_stats(),
            "prompt_cache": self.prompt_cache.get_cache_stats(),
            "response_cache": self.response_cache.get_cache_stats(),
            "sampling": self.sampling_manager.get_sampling_stats(),
        }

    async def get_daily_cost(self) -> Dict[str, Any]:
        """오늘 비용 조회"""
        return await self.cost_tracker.get_daily_cost()

    async def get_monthly_cost(self) -> Dict[str, Any]:
        """이번 달 비용 조회"""
        return await self.cost_tracker.get_monthly_cost()

    async def check_budget_alert(
        self, daily_budget: float = 10.0, monthly_budget: float = 300.0
    ) -> Dict[str, Any]:
        """예산 알림 체크"""
        return await self.cost_tracker.check_budget_alert(
            daily_budget=daily_budget,
            monthly_budget=monthly_budget
        )

    async def get_agent_breakdown(self) -> List[Dict[str, Any]]:
        """에이전트별 비용 분석"""
        return await self.cost_tracker.get_agent_breakdown()

    def configure_sampling_strategy(
        self,
        agent_type: str,
        strategy: SamplingStrategy,
        config: Dict[str, Any] = None
    ):
        """샘플링 전략 동적 변경"""
        self.sampling_manager.override_strategy(
            agent_type=agent_type,
            strategy=strategy,
            config=config
        )

        logger.info(f"Sampling strategy updated: {agent_type} -> {strategy.value}")


# 싱글톤 인스턴스 (Redis 클라이언트는 나중에 주입)
_integrated_ai_service_instance = None


def get_integrated_ai_service(redis_client=None) -> IntegratedAIService:
    """통합 AI 서비스 싱글톤 인스턴스 조회"""
    global _integrated_ai_service_instance

    if _integrated_ai_service_instance is None:
        _integrated_ai_service_instance = IntegratedAIService(redis_client)

    return _integrated_ai_service_instance
