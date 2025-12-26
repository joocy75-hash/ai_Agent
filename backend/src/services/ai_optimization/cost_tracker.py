"""
Cost Tracker (비용 추적기)

AI API 호출 비용을 추적하고 모니터링
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class CostTracker:
    """
    AI 비용 추적기

    핵심 기능:
    1. 실시간 비용 추적 (API 호출별)
    2. 일일/주간/월간 집계
    3. 예산 알림
    4. 비용 분석 및 리포트
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

        # 모델별 토큰 가격 (USD per million tokens)
        self.pricing = {
            "claude-sonnet-4": {
                "input": 3.0,  # $3/MTok
                "output": 15.0,  # $15/MTok
                "cache_write": 3.75,  # $3.75/MTok
                "cache_read": 0.30,  # $0.30/MTok (90% 할인)
            },
            "claude-haiku-4": {
                "input": 0.8,  # $0.80/MTok
                "output": 4.0,  # $4/MTok
                "cache_write": 1.0,
                "cache_read": 0.08,
            },
            "deepseek-v3": {
                "input": 0.27,  # $0.27/MTok
                "output": 1.10,  # $1.10/MTok
                "cache_write": 0.27,
                "cache_read": 0.027,  # 90% 할인
            },
            "gemini-3-pro": {
                "input": 1.25,  # $1.25/MTok (Gemini 3 Pro Preview)
                "output": 5.00,  # $5.00/MTok
                "cache_write": 1.25,
                "cache_read": 0.125,  # 90% 할인
            },
            "gemini-2.5-pro": {
                "input": 1.25,  # $1.25/MTok
                "output": 5.00,  # $5.00/MTok
                "cache_write": 1.25,
                "cache_read": 0.125,
            },
        }

        # 통계
        self.stats = {
            "total_calls": 0,
            "total_cost_usd": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cache_read_tokens": 0,
            "total_cache_write_tokens": 0,
            "calls_by_agent": defaultdict(int),
            "cost_by_agent": defaultdict(float),
            "cost_by_model": defaultdict(float),
        }

        logger.info("CostTracker initialized")

    async def track_api_call(
        self,
        model: str,
        agent_type: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        AI API 호출 비용 추적

        Args:
            model: 모델명 (claude-sonnet-4, deepseek-v3, etc.)
            agent_type: 에이전트 타입
            input_tokens: 입력 토큰 수
            output_tokens: 출력 토큰 수
            cache_read_tokens: 캐시 읽기 토큰 수
            cache_write_tokens: 캐시 쓰기 토큰 수
            metadata: 추가 메타데이터

        Returns:
            비용 정보
        """
        # 가격 조회
        pricing = self.pricing.get(model, self.pricing["claude-sonnet-4"])

        # 비용 계산
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        cache_read_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read"]
        cache_write_cost = (cache_write_tokens / 1_000_000) * pricing["cache_write"]

        total_cost = input_cost + output_cost + cache_read_cost + cache_write_cost

        # 통계 업데이트
        self.stats["total_calls"] += 1
        self.stats["total_cost_usd"] += total_cost
        self.stats["total_input_tokens"] += input_tokens
        self.stats["total_output_tokens"] += output_tokens
        self.stats["total_cache_read_tokens"] += cache_read_tokens
        self.stats["total_cache_write_tokens"] += cache_write_tokens
        self.stats["calls_by_agent"][agent_type] += 1
        self.stats["cost_by_agent"][agent_type] += total_cost
        self.stats["cost_by_model"][model] += total_cost

        # Redis에 저장 (시계열 데이터)
        await self._save_to_redis(
            model, agent_type, total_cost, input_tokens, output_tokens, metadata
        )

        cost_info = {
            "model": model,
            "agent_type": agent_type,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "cache_read_cost_usd": round(cache_read_cost, 6),
            "cache_write_cost_usd": round(cache_write_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.debug(
            f"API call tracked: {agent_type} ({model}) - "
            f"{input_tokens + output_tokens} tokens, ${total_cost:.6f}"
        )

        return cost_info

    async def _save_to_redis(
        self,
        model: str,
        agent_type: str,
        cost: float,
        input_tokens: int,
        output_tokens: int,
        metadata: Dict[str, Any] = None,
    ):
        """Redis에 비용 데이터 저장 (ATOMIC: pipeline 사용)"""
        if not self.redis_client:
            return

        try:
            timestamp = datetime.utcnow()
            date_key = timestamp.strftime("%Y-%m-%d")
            hour_key = timestamp.strftime("%Y-%m-%d:%H")

            # SECURITY/CONCURRENCY: Use pipeline for atomic operations
            # This prevents race conditions under high concurrent load
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # 일일 집계 (atomic)
                daily_key = f"ai:cost:daily:{date_key}"
                pipe.hincrby(daily_key, "calls", 1)
                pipe.hincrbyfloat(daily_key, "cost", cost)
                pipe.hincrby(daily_key, "input_tokens", input_tokens)
                pipe.hincrby(daily_key, "output_tokens", output_tokens)
                pipe.expire(daily_key, 86400 * 90)  # 90일 보관

                # 시간별 집계 (atomic)
                hourly_key = f"ai:cost:hourly:{hour_key}"
                pipe.hincrby(hourly_key, "calls", 1)
                pipe.hincrbyfloat(hourly_key, "cost", cost)
                pipe.expire(hourly_key, 86400 * 7)  # 7일 보관

                # 에이전트별 집계 (atomic)
                agent_key = f"ai:cost:agent:{agent_type}"
                pipe.hincrby(agent_key, "calls", 1)
                pipe.hincrbyfloat(agent_key, "cost", cost)
                pipe.expire(agent_key, 86400 * 30)  # 30일 보관

                # Execute all commands atomically
                await pipe.execute()

            logger.debug(f"Cost saved to Redis atomically: {agent_type}, ${cost:.4f}")

        except Exception as e:
            logger.error(f"Failed to save cost to Redis: {e}", exc_info=True)

    async def get_daily_cost(
        self, date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """일일 비용 조회"""
        if not self.redis_client:
            return self._get_local_stats()

        date = date or datetime.utcnow()
        date_key = date.strftime("%Y-%m-%d")
        daily_key = f"ai:cost:daily:{date_key}"  # Match new key prefix

        try:
            data = await self.redis_client.hgetall(daily_key)

            if not data:
                return {
                    "date": date_key,
                    "calls": 0,
                    "cost_usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }

            return {
                "date": date_key,
                "calls": int(data.get(b"calls", 0)),
                "cost_usd": float(data.get(b"cost", 0.0)),
                "input_tokens": int(data.get(b"input_tokens", 0)),
                "output_tokens": int(data.get(b"output_tokens", 0)),
            }

        except Exception as e:
            logger.error(f"Failed to get daily cost: {e}")
            return self._get_local_stats()

    async def get_monthly_cost(
        self, year: int = None, month: int = None
    ) -> Dict[str, Any]:
        """월간 비용 조회"""
        if not self.redis_client:
            return self._get_local_stats()

        now = datetime.utcnow()
        year = year or now.year
        month = month or now.month

        try:
            # 해당 월의 모든 일일 데이터 조회
            pattern = f"ai:cost:daily:{year:04d}-{month:02d}-*"  # Match new key prefix
            cursor = 0
            daily_costs = []

            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor, match=pattern, count=100
                )

                for key in keys:
                    data = await self.redis_client.hgetall(key)
                    if data:
                        daily_costs.append({
                            "calls": int(data.get(b"calls", 0)),
                            "cost": float(data.get(b"cost", 0.0)),
                        })

                if cursor == 0:
                    break

            # 집계
            total_calls = sum(d["calls"] for d in daily_costs)
            total_cost = sum(d["cost"] for d in daily_costs)

            return {
                "year": year,
                "month": month,
                "total_calls": total_calls,
                "total_cost_usd": round(total_cost, 2),
                "daily_count": len(daily_costs),
                "avg_daily_cost_usd": round(total_cost / len(daily_costs), 2) if daily_costs else 0.0,
            }

        except Exception as e:
            logger.error(f"Failed to get monthly cost: {e}")
            return self._get_local_stats()

    async def get_agent_breakdown(self) -> List[Dict[str, Any]]:
        """에이전트별 비용 분석"""
        breakdown = []

        for agent_type, cost in self.stats["cost_by_agent"].items():
            calls = self.stats["calls_by_agent"][agent_type]

            breakdown.append({
                "agent_type": agent_type,
                "calls": calls,
                "total_cost_usd": round(cost, 2),
                "avg_cost_per_call_usd": round(cost / calls, 6) if calls > 0 else 0.0,
                "cost_percent": round(
                    cost / self.stats["total_cost_usd"] * 100, 2
                ) if self.stats["total_cost_usd"] > 0 else 0.0,
            })

        # 비용 순으로 정렬
        breakdown.sort(key=lambda x: x["total_cost_usd"], reverse=True)

        return breakdown

    async def check_budget_alert(
        self, daily_budget: float = 50.0, monthly_budget: float = 1000.0
    ) -> Dict[str, Any]:
        """예산 알림 체크"""
        today_cost = await self.get_daily_cost()
        monthly_cost = await self.get_monthly_cost()

        alerts = []

        # 일일 예산 체크
        daily_usage_percent = (
            today_cost["cost_usd"] / daily_budget * 100 if daily_budget > 0 else 0
        )

        if daily_usage_percent >= 100:
            alerts.append({
                "type": "daily_budget_exceeded",
                "severity": "critical",
                "message": f"일일 예산 초과: ${today_cost['cost_usd']:.2f} / ${daily_budget:.2f}",
            })
        elif daily_usage_percent >= 80:
            alerts.append({
                "type": "daily_budget_warning",
                "severity": "warning",
                "message": f"일일 예산 80% 도달: ${today_cost['cost_usd']:.2f} / ${daily_budget:.2f}",
            })

        # 월간 예산 체크
        monthly_usage_percent = (
            monthly_cost["total_cost_usd"] / monthly_budget * 100
            if monthly_budget > 0
            else 0
        )

        if monthly_usage_percent >= 100:
            alerts.append({
                "type": "monthly_budget_exceeded",
                "severity": "critical",
                "message": f"월간 예산 초과: ${monthly_cost['total_cost_usd']:.2f} / ${monthly_budget:.2f}",
            })
        elif monthly_usage_percent >= 80:
            alerts.append({
                "type": "monthly_budget_warning",
                "severity": "warning",
                "message": f"월간 예산 80% 도달: ${monthly_cost['total_cost_usd']:.2f} / ${monthly_budget:.2f}",
            })

        return {
            "daily_budget": daily_budget,
            "daily_spent": today_cost["cost_usd"],
            "daily_usage_percent": round(daily_usage_percent, 2),
            "monthly_budget": monthly_budget,
            "monthly_spent": monthly_cost["total_cost_usd"],
            "monthly_usage_percent": round(monthly_usage_percent, 2),
            "alerts": alerts,
        }

    def _get_local_stats(self) -> Dict[str, Any]:
        """로컬 통계 조회 (Redis 없을 때)"""
        return {
            "calls": self.stats["total_calls"],
            "cost_usd": round(self.stats["total_cost_usd"], 2),
            "input_tokens": self.stats["total_input_tokens"],
            "output_tokens": self.stats["total_output_tokens"],
        }

    def get_overall_stats(self) -> Dict[str, Any]:
        """전체 통계 조회"""
        total_tokens = (
            self.stats["total_input_tokens"]
            + self.stats["total_output_tokens"]
        )

        # 캐시 절감율
        cache_savings_percent = 0.0
        if total_tokens > 0:
            cache_savings_percent = (
                self.stats["total_cache_read_tokens"] / total_tokens * 100
            )

        return {
            "total_calls": self.stats["total_calls"],
            "total_cost_usd": round(self.stats["total_cost_usd"], 2),
            "total_tokens": total_tokens,
            "total_input_tokens": self.stats["total_input_tokens"],
            "total_output_tokens": self.stats["total_output_tokens"],
            "total_cache_read_tokens": self.stats["total_cache_read_tokens"],
            "total_cache_write_tokens": self.stats["total_cache_write_tokens"],
            "cache_savings_percent": round(cache_savings_percent, 2),
            "avg_cost_per_call_usd": round(
                self.stats["total_cost_usd"] / self.stats["total_calls"], 6
            ) if self.stats["total_calls"] > 0 else 0.0,
            "cost_by_model": dict(self.stats["cost_by_model"]),
            "cost_by_agent": dict(self.stats["cost_by_agent"]),
        }
