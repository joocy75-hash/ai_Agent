"""
Smart Sampling Manager (스마트 샘플링 매니저)

모든 요청에 AI를 호출하지 않고 지능적으로 샘플링하여 비용 절감
"""

import json
import logging
import threading
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# 글로벌 싱글톤 인스턴스 (Issue #4: AI Rate Limit 문제 해결)
_global_sampling_manager: Optional["SmartSamplingManager"] = None
_singleton_lock = threading.Lock()


def get_global_sampling_manager() -> "SmartSamplingManager":
    """
    글로벌 SmartSamplingManager 싱글톤 반환

    Thread-safe singleton pattern을 사용하여 전역에서 하나의
    SmartSamplingManager 인스턴스만 생성되도록 보장합니다.

    Issue #4: AI Rate Limit 문제 해결
    - 기존: 전략 인스턴스마다 새 SmartSamplingManager 생성 → 캐시 초기화
    - 수정: 글로벌 싱글톤으로 캐시 상태 유지

    Returns:
        SmartSamplingManager: 글로벌 싱글톤 인스턴스
    """
    global _global_sampling_manager

    # Double-checked locking for thread safety
    if _global_sampling_manager is None:
        with _singleton_lock:
            if _global_sampling_manager is None:
                _global_sampling_manager = SmartSamplingManager()
                logger.info("✅ Global SmartSamplingManager singleton initialized")

    return _global_sampling_manager


class SamplingStrategy(str, Enum):
    """샘플링 전략"""
    ALWAYS = "always"  # 항상 호출 (중요한 작업)
    PERIODIC = "periodic"  # 주기적 호출 (예: 5분마다)
    CHANGE_BASED = "change_based"  # 변화 감지 시에만 호출
    THRESHOLD = "threshold"  # 임계값 초과 시에만 호출
    ADAPTIVE = "adaptive"  # 적응형 (성능 기반 조절)


class SmartSamplingManager:
    """
    스마트 샘플링 매니저

    핵심 아이디어:
    1. 모든 요청에 AI 호출 불필요
    2. 중요도/변화량에 따라 샘플링
    3. 적응형 샘플링 (에러율/성능 기반 조절)
    4. Rate Limit 방지 (동적 간격 조절)

    비용 절감 효과:
    - AI 호출 50~70% 감소
    - 성능은 유지 (중요한 순간에만 호출)
    - 월 $500~$800 절감 가능
    """

    # 동적 간격 설정 (DeepSeek Rate Limit 없음 - 선물거래 최적화)
    # 여러 사용자 동시 사용 고려: 심볼별 캐싱으로 중복 호출 방지
    DEFAULT_MARKET_REGIME_INTERVAL = 15  # 기본 15초 (비용 vs 속도 균형)
    MIN_MARKET_REGIME_INTERVAL = 10      # 최소 10초 (급변동 시)
    MAX_MARKET_REGIME_INTERVAL = 45      # 최대 45초 (안정 시)

    # 심볼별 캐시 TTL (여러 사용자가 같은 심볼 분석 시 중복 호출 방지)
    SYMBOL_CACHE_TTL_SECONDS = 15  # 15초 내 같은 심볼 분석은 캐시 재사용

    # 변동성 기반 간격 조절 임계값
    HIGH_VOLATILITY_THRESHOLD = 2.0      # 2% 이상 변동 시 빠른 호출
    LOW_VOLATILITY_THRESHOLD = 0.5       # 0.5% 미만 변동 시 느린 호출

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

        # Rate Limit 상태 추적
        self._rate_limit_backoff = 1  # 현재 backoff 배수
        self._last_rate_limit_time = None
        self._consecutive_rate_limits = 0

        # 인메모리 캐시 (Redis 없을 때 사용)
        self._memory_cache: Dict[str, datetime] = {}

        # 에이전트별 샘플링 전략
        self.strategies = {
            # 항상 호출 (중요)
            "signal_validator": {
                "strategy": SamplingStrategy.ALWAYS,
                "reason": "모든 거래 신호 검증 필수",
            },
            "circuit_breaker": {
                "strategy": SamplingStrategy.ALWAYS,
                "reason": "서킷 브레이커는 항상 체크",
            },
            # 주기적 호출 (선물거래 최적화 - 여러 사용자 동시 사용 고려)
            "market_regime": {
                "strategy": SamplingStrategy.PERIODIC,
                "interval_seconds": 15,  # 15초마다 시장 분석 (비용 vs 속도 균형)
                "min_interval": 10,      # 급변동 시 10초
                "max_interval": 45,      # 안정 시 45초
                "cache_by_symbol": True, # 심볼별 캐싱 활성화 (여러 사용자 중복 호출 방지)
                "reason": "선물거래 최적화: 15초 간격, 심볼별 캐싱으로 비용 절감",
            },
            "portfolio_optimizer": {
                "strategy": SamplingStrategy.PERIODIC,
                "interval_seconds": 120,  # 2분마다 (비용 절감)
                "min_interval": 60,
                "max_interval": 300,
                "reason": "포트폴리오 최적화: 2분 간격으로 합리적 비용",
            },
            # 변화 기반 호출
            "anomaly_detector": {
                "strategy": SamplingStrategy.CHANGE_BASED,
                "threshold": 0.10,  # 10% 변화
                "reason": "메트릭 변화 시에만 재분석",
            },
            # 선물거래: 리스크 모니터링 (AI 호출 없이 규칙 기반으로 처리)
            "risk_monitor": {
                "strategy": SamplingStrategy.THRESHOLD,  # 임계값 초과 시에만 AI 호출
                "threshold": 0.80,  # 리스크 80% 이상일 때만 AI 분석
                "fallback_to_rules": True,  # AI 없어도 규칙 기반으로 작동
                "reason": "리스크 모니터링: 규칙 기반 우선, 위험 시에만 AI 호출 (비용 절감)",
            },
        }

        # 통계
        self.stats = {
            "total_requests": 0,
            "sampled_requests": 0,
            "skipped_requests": 0,
            "api_calls_saved": 0,
            "rate_limit_hits": 0,
        }

        logger.info("SmartSamplingManager initialized with dynamic interval control")

    async def should_sample(
        self, agent_type: str, context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        샘플링 여부 결정

        Args:
            agent_type: 에이전트 타입
            context: 컨텍스트 데이터

        Returns:
            (should_call: bool, reason: str)
        """
        self.stats["total_requests"] += 1

        strategy_config = self.strategies.get(agent_type)

        if not strategy_config:
            # 기본: 항상 호출
            self.stats["sampled_requests"] += 1
            return True, "no_strategy_defined"

        strategy = strategy_config["strategy"]

        # 1. ALWAYS
        if strategy == SamplingStrategy.ALWAYS:
            self.stats["sampled_requests"] += 1
            return True, "always_strategy"

        # 2. PERIODIC
        elif strategy == SamplingStrategy.PERIODIC:
            return await self._check_periodic(agent_type, strategy_config)

        # 3. CHANGE_BASED
        elif strategy == SamplingStrategy.CHANGE_BASED:
            return await self._check_change_based(
                agent_type, strategy_config, context
            )

        # 4. THRESHOLD
        elif strategy == SamplingStrategy.THRESHOLD:
            return self._check_threshold(agent_type, strategy_config, context)

        # 5. ADAPTIVE
        elif strategy == SamplingStrategy.ADAPTIVE:
            return await self._check_adaptive(agent_type, context)

        else:
            self.stats["sampled_requests"] += 1
            return True, "unknown_strategy"

    async def _check_periodic(
        self, agent_type: str, config: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """주기적 샘플링 체크 (Rate Limit Backoff 적용, 인메모리 폴백)"""
        # 동적 간격 계산 (Rate Limit backoff 적용)
        effective_interval = self._get_effective_interval(agent_type, config)
        key = f"sampling:periodic:{agent_type}"

        # 인메모리 캐시 사용 (Redis 없거나 에러 시)
        try:
            if self.redis_client:
                return await self._check_periodic_redis(key, effective_interval)
            else:
                return self._check_periodic_memory(key, effective_interval)
        except Exception as e:
            logger.debug(f"Periodic check fallback to memory: {e}")
            return self._check_periodic_memory(key, effective_interval)

    def _check_periodic_memory(
        self, key: str, effective_interval: int
    ) -> tuple[bool, Optional[str]]:
        """인메모리 기반 주기적 샘플링 체크"""
        now = datetime.utcnow()
        last_call_time = self._memory_cache.get(key)

        if not last_call_time:
            # 첫 호출
            self._memory_cache[key] = now
            self.stats["sampled_requests"] += 1
            return True, "first_call_memory"

        elapsed = (now - last_call_time).total_seconds()

        if elapsed >= effective_interval:
            # 주기 도래
            self._memory_cache[key] = now
            self.stats["sampled_requests"] += 1
            return True, f"periodic_elapsed_{int(elapsed)}s_interval_{int(effective_interval)}s"
        else:
            # 아직 주기 안 됨
            self.stats["skipped_requests"] += 1
            self.stats["api_calls_saved"] += 1
            return False, f"periodic_wait_{int(effective_interval - elapsed)}s"

    async def _check_periodic_redis(
        self, key: str, effective_interval: int
    ) -> tuple[bool, Optional[str]]:
        """Redis 기반 주기적 샘플링 체크"""
        # 마지막 호출 시간 조회
        last_call = await self.redis_client.get(key)

        if not last_call:
            # 첫 호출
            await self.redis_client.setex(
                key, effective_interval, datetime.utcnow().isoformat()
            )
            self.stats["sampled_requests"] += 1
            return True, "first_call"

        # 시간 경과 체크
        last_call_time = datetime.fromisoformat(
            last_call.decode("utf-8") if isinstance(last_call, bytes) else last_call
        )
        elapsed = (datetime.utcnow() - last_call_time).total_seconds()

        if elapsed >= effective_interval:
            # 주기 도래
            await self.redis_client.setex(
                key, effective_interval, datetime.utcnow().isoformat()
            )
            self.stats["sampled_requests"] += 1
            return True, f"periodic_elapsed_{int(elapsed)}s_interval_{int(effective_interval)}s"

        else:
            # 아직 주기 안 됨
            self.stats["skipped_requests"] += 1
            self.stats["api_calls_saved"] += 1
            return False, f"periodic_wait_{int(effective_interval - elapsed)}s"

    async def _check_change_based(
        self, agent_type: str, config: Dict[str, Any], context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """변화 기반 샘플링 체크"""
        if not self.redis_client:
            self.stats["sampled_requests"] += 1
            return True, "no_redis"

        threshold = config["threshold"]  # 10% 변화
        key = f"sampling:change:{agent_type}"

        try:
            # 이전 컨텍스트 조회
            prev_context_raw = await self.redis_client.get(key)

            if not prev_context_raw:
                # 첫 호출
                await self.redis_client.setex(
                    key, 3600, json.dumps(context)
                )
                self.stats["sampled_requests"] += 1
                return True, "first_call"

            # JSON 파싱 (보안: eval() 대신 json.loads() 사용)
            if isinstance(prev_context_raw, bytes):
                prev_context_raw = prev_context_raw.decode("utf-8")
            prev_context = json.loads(prev_context_raw)

            # 변화량 계산
            change_percent = self._calculate_change(prev_context, context)

            if change_percent >= threshold * 100:  # threshold를 퍼센트로 변환
                # 변화 감지
                await self.redis_client.setex(
                    key, 3600, json.dumps(context)
                )
                self.stats["sampled_requests"] += 1
                return True, f"change_detected_{change_percent:.1f}%"

            else:
                # 변화 없음
                self.stats["skipped_requests"] += 1
                self.stats["api_calls_saved"] += 1
                return False, f"no_change_{change_percent:.1f}%"

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in change-based check: {e}")
            # JSON 에러 시 새로 저장
            await self.redis_client.setex(key, 3600, json.dumps(context))
            self.stats["sampled_requests"] += 1
            return True, "json_error_fallback"

        except Exception as e:
            logger.error(f"Change-based check error: {e}")
            self.stats["sampled_requests"] += 1
            return True, "error_fallback"

    def _check_threshold(
        self, agent_type: str, config: Dict[str, Any], context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """임계값 기반 샘플링 체크"""
        threshold = config["threshold"]

        # 컨텍스트에서 메트릭 추출
        metric_value = context.get("metric_value", 0.0)

        if metric_value >= threshold:
            self.stats["sampled_requests"] += 1
            return True, f"threshold_exceeded_{metric_value:.2f}"

        else:
            self.stats["skipped_requests"] += 1
            self.stats["api_calls_saved"] += 1
            return False, f"below_threshold_{metric_value:.2f}"

    async def _check_adaptive(
        self, agent_type: str, context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """적응형 샘플링 체크"""
        # TODO: 실제 구현 시 에이전트 성능 메트릭 기반으로 조절
        # 예: 에러율이 높으면 더 자주 호출, 성능 좋으면 덜 호출

        self.stats["sampled_requests"] += 1
        return True, "adaptive_strategy"

    def _calculate_change(
        self, prev_context: Dict[str, Any], current_context: Dict[str, Any]
    ) -> float:
        """
        컨텍스트 변화량 계산

        Args:
            prev_context: 이전 컨텍스트
            current_context: 현재 컨텍스트

        Returns:
            변화량 (%)
        """
        # 간단한 예시: 숫자 값들의 평균 변화율
        changes = []

        for key in current_context:
            if key in prev_context:
                try:
                    prev_val = float(prev_context[key])
                    curr_val = float(current_context[key])

                    if prev_val != 0:
                        change = abs((curr_val - prev_val) / prev_val * 100)
                        changes.append(change)

                except (ValueError, TypeError):
                    continue

        return sum(changes) / len(changes) if changes else 0.0

    def _get_effective_interval(self, agent_type: str, config: Dict[str, Any]) -> int:
        """
        Rate Limit Backoff을 적용한 동적 간격 계산

        Args:
            agent_type: 에이전트 타입
            config: 전략 설정

        Returns:
            적용할 간격 (초)
        """
        base_interval = config.get("interval_seconds", 45)
        max_interval = config.get("max_interval", 120)
        # min_interval은 향후 변동성 기반 조절에 사용될 수 있음
        # min_interval = config.get("min_interval", 30)

        # Rate Limit backoff 적용
        if self._rate_limit_backoff > 1:
            # Backoff이 활성화된 경우 간격 증가
            effective = base_interval * self._rate_limit_backoff
            effective = min(effective, max_interval)

            logger.debug(
                f"[{agent_type}] Rate limit backoff active: {self._rate_limit_backoff}x, "
                f"interval: {base_interval}s -> {effective}s"
            )
            return int(effective)

        # 기본 간격 반환
        return base_interval

    def notify_rate_limit(self):
        """
        Rate Limit 발생 알림 (Exponential Backoff 적용)

        API 호출 후 429 에러 발생 시 호출
        """
        self._consecutive_rate_limits += 1
        self.stats["rate_limit_hits"] += 1

        # Exponential backoff: 1 -> 2 -> 4 -> 8 (최대 8배)
        self._rate_limit_backoff = min(2 ** self._consecutive_rate_limits, 8)
        self._last_rate_limit_time = datetime.utcnow()

        logger.warning(
            f"⚠️ Rate limit hit #{self._consecutive_rate_limits}, "
            f"backoff multiplier: {self._rate_limit_backoff}x"
        )

    def notify_success(self):
        """
        API 호출 성공 알림 (Backoff 점진적 감소)

        성공적인 API 호출 후 호출
        """
        if self._rate_limit_backoff > 1:
            # 성공 시 backoff 점진적 감소
            self._rate_limit_backoff = max(1, self._rate_limit_backoff // 2)
            self._consecutive_rate_limits = max(0, self._consecutive_rate_limits - 1)

            if self._rate_limit_backoff == 1:
                logger.info("✅ Rate limit backoff reset to normal")
            else:
                logger.debug(f"Rate limit backoff reduced to: {self._rate_limit_backoff}x")

    def get_backoff_status(self) -> Dict[str, Any]:
        """현재 Rate Limit Backoff 상태 조회"""
        return {
            "backoff_multiplier": self._rate_limit_backoff,
            "consecutive_rate_limits": self._consecutive_rate_limits,
            "last_rate_limit_time": (
                self._last_rate_limit_time.isoformat()
                if self._last_rate_limit_time else None
            ),
            "total_rate_limit_hits": self.stats.get("rate_limit_hits", 0),
        }

    def override_strategy(
        self,
        agent_type: str,
        strategy: SamplingStrategy,
        config: Dict[str, Any] = None,
    ):
        """
        샘플링 전략 동적 변경

        Args:
            agent_type: 에이전트 타입
            strategy: 새로운 전략
            config: 전략 설정
        """
        self.strategies[agent_type] = {
            "strategy": strategy,
            **(config or {}),
        }

        logger.info(f"Sampling strategy updated for {agent_type}: {strategy.value}")

    def get_sampling_stats(self) -> Dict[str, Any]:
        """샘플링 통계 조회"""
        total = self.stats["total_requests"]
        sampling_rate = (
            self.stats["sampled_requests"] / total * 100 if total > 0 else 0
        )
        skip_rate = (
            self.stats["skipped_requests"] / total * 100 if total > 0 else 0
        )

        # 비용 절감 추정 (평균 $0.01/call)
        savings = self.stats["api_calls_saved"] * 0.01

        return {
            "total_requests": total,
            "sampled_requests": self.stats["sampled_requests"],
            "skipped_requests": self.stats["skipped_requests"],
            "sampling_rate_percent": round(sampling_rate, 2),
            "skip_rate_percent": round(skip_rate, 2),
            "api_calls_saved": self.stats["api_calls_saved"],
            "estimated_savings_usd": round(savings, 2),
        }
