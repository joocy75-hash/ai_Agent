"""
Smart Sampling Manager (스마트 샘플링 매니저)

모든 요청에 AI를 호출하지 않고 지능적으로 샘플링하여 비용 절감
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


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

    비용 절감 효과:
    - AI 호출 50~70% 감소
    - 성능은 유지 (중요한 순간에만 호출)
    - 월 $500~$800 절감 가능
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

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
            # 주기적 호출
            "market_regime": {
                "strategy": SamplingStrategy.PERIODIC,
                "interval_seconds": 300,  # 5분마다
                "reason": "시장 환경은 천천히 변함",
            },
            "portfolio_optimizer": {
                "strategy": SamplingStrategy.PERIODIC,
                "interval_seconds": 3600,  # 1시간마다
                "reason": "포트폴리오는 자주 변하지 않음",
            },
            # 변화 기반 호출
            "anomaly_detector": {
                "strategy": SamplingStrategy.CHANGE_BASED,
                "threshold": 0.10,  # 10% 변화
                "reason": "메트릭 변화 시에만 재분석",
            },
            # 임계값 기반 호출
            "risk_monitor": {
                "strategy": SamplingStrategy.THRESHOLD,
                "threshold": 0.70,  # 리스크 레벨 70% 이상
                "reason": "리스크 높을 때만 AI 호출",
            },
        }

        # 통계
        self.stats = {
            "total_requests": 0,
            "sampled_requests": 0,
            "skipped_requests": 0,
            "api_calls_saved": 0,
        }

        logger.info("SmartSamplingManager initialized")

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
        """주기적 샘플링 체크"""
        if not self.redis_client:
            self.stats["sampled_requests"] += 1
            return True, "no_redis"

        interval = config["interval_seconds"]
        key = f"sampling:periodic:{agent_type}"

        try:
            # 마지막 호출 시간 조회
            last_call = await self.redis_client.get(key)

            if not last_call:
                # 첫 호출
                await self.redis_client.setex(
                    key, interval, datetime.utcnow().isoformat()
                )
                self.stats["sampled_requests"] += 1
                return True, "first_call"

            # 시간 경과 체크
            last_call_time = datetime.fromisoformat(
                last_call.decode("utf-8") if isinstance(last_call, bytes) else last_call
            )
            elapsed = (datetime.utcnow() - last_call_time).total_seconds()

            if elapsed >= interval:
                # 주기 도래
                await self.redis_client.setex(
                    key, interval, datetime.utcnow().isoformat()
                )
                self.stats["sampled_requests"] += 1
                return True, f"periodic_elapsed_{int(elapsed)}s"

            else:
                # 아직 주기 안 됨
                self.stats["skipped_requests"] += 1
                self.stats["api_calls_saved"] += 1
                return False, f"periodic_wait_{int(interval - elapsed)}s"

        except Exception as e:
            logger.error(f"Periodic check error: {e}")
            self.stats["sampled_requests"] += 1
            return True, "error_fallback"

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
