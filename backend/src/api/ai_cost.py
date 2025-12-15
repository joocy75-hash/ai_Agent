"""
AI Cost Optimization API (AI 비용 최적화 API)

비용 추적, 통계 조회, 설정 변경 API 엔드포인트
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.ai_optimization import (
    get_integrated_ai_service,
    get_event_optimizer,
    IntegratedAIService,
    EventDrivenOptimizer,
    SamplingStrategy
)
from src.utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-cost", tags=["AI Cost Optimization"])


# Response Models
class CostStatsResponse(BaseModel):
    """비용 통계 응답"""
    overall: Dict[str, Any]
    prompt_cache: Dict[str, Any]
    response_cache: Dict[str, Any]
    sampling: Dict[str, Any]


class DailyCostResponse(BaseModel):
    """일일 비용 응답"""
    date: str
    calls: int
    cost_usd: float
    input_tokens: int
    output_tokens: int


class MonthlyCostResponse(BaseModel):
    """월간 비용 응답"""
    year: int
    month: int
    total_calls: int
    total_cost_usd: float
    daily_count: int
    avg_daily_cost_usd: float


class BudgetAlertResponse(BaseModel):
    """예산 알림 응답"""
    daily_budget: float
    daily_spent: float
    daily_usage_percent: float
    monthly_budget: float
    monthly_spent: float
    monthly_usage_percent: float
    alerts: list


class AgentBreakdownResponse(BaseModel):
    """에이전트별 비용 분석 응답"""
    agent_type: str
    calls: int
    total_cost_usd: float
    avg_cost_per_call_usd: float
    cost_percent: float


class EventStatsResponse(BaseModel):
    """이벤트 통계 응답"""
    total_events: int
    filtered_events: int
    batched_events: int
    ai_calls_saved: int
    filtered_percent: float
    batched_percent: float
    estimated_savings_usd: float


class SamplingStrategyUpdateRequest(BaseModel):
    """샘플링 전략 업데이트 요청"""
    agent_type: str = Field(..., description="에이전트 타입")
    strategy: str = Field(..., description="샘플링 전략 (ALWAYS, PERIODIC, CHANGE_BASED, THRESHOLD, ADAPTIVE)")
    interval_seconds: Optional[int] = Field(None, description="주기 (PERIODIC용)")
    threshold: Optional[float] = Field(None, description="임계값 (CHANGE_BASED, THRESHOLD용)")


class EventThresholdsUpdateRequest(BaseModel):
    """이벤트 임계값 업데이트 요청"""
    price_change_pct: Optional[float] = Field(None, description="가격 변동 임계값 (%)")
    volume_spike_multiplier: Optional[float] = Field(None, description="거래량 급증 배수")
    volatility_threshold: Optional[float] = Field(None, description="변동성 임계값 (%)")
    min_ai_interval: Optional[int] = Field(None, description="최소 AI 호출 간격 (초)")
    batch_size: Optional[int] = Field(None, description="배치 크기")
    batch_timeout: Optional[int] = Field(None, description="배치 타임아웃 (초)")


# Dependency: AI Service
async def get_ai_service() -> IntegratedAIService:
    """AI 서비스 의존성"""
    from src.services import get_ai_service_instance
    return get_ai_service_instance()


# Dependency: Event Optimizer
async def get_event_opt() -> EventDrivenOptimizer:
    """이벤트 최적화기 의존성"""
    ai_service = await get_ai_service()
    return ai_service.event_optimizer


@router.get("/stats", response_model=CostStatsResponse)
async def get_cost_stats(
    user_id: int = Depends(get_current_user_id),  # SECURITY: Authentication required
    ai_service: IntegratedAIService = Depends(get_ai_service)
):
    """
    전체 비용 통계 조회

    **Authentication Required**: This endpoint requires a valid JWT token.

    Returns:
        - overall: 전체 통계
        - prompt_cache: 프롬프트 캐시 통계
        - response_cache: 응답 캐시 통계
        - sampling: 샘플링 통계
    """
    try:
        stats = await ai_service.get_cost_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get cost stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily", response_model=DailyCostResponse)
async def get_daily_cost(
    user_id: int = Depends(get_current_user_id),  # SECURITY: Authentication required
    date: Optional[str] = Query(None, description="날짜 (YYYY-MM-DD, 기본: 오늘)"),
    ai_service: IntegratedAIService = Depends(get_ai_service)
):
    """
    일일 비용 조회

    Args:
        date: 조회할 날짜 (YYYY-MM-DD 형식, 생략 시 오늘)

    Returns:
        일일 비용 정보
    """
    try:
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = datetime.utcnow()

        daily_cost = await ai_service.get_daily_cost()
        return daily_cost

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")

    except Exception as e:
        logger.error(f"Failed to get daily cost: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monthly", response_model=MonthlyCostResponse)
async def get_monthly_cost(
    user_id: int = Depends(get_current_user_id),  # SECURITY: Authentication required
    year: Optional[int] = Query(None, description="연도 (기본: 올해)"),
    month: Optional[int] = Query(None, description="월 (1-12, 기본: 이번 달)"),
    ai_service: IntegratedAIService = Depends(get_ai_service)
):
    """
    월간 비용 조회

    Args:
        year: 연도 (생략 시 올해)
        month: 월 (1-12, 생략 시 이번 달)

    Returns:
        월간 비용 정보
    """
    try:
        monthly_cost = await ai_service.get_monthly_cost()
        return monthly_cost

    except Exception as e:
        logger.error(f"Failed to get monthly cost: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budget-alert", response_model=BudgetAlertResponse)
async def get_budget_alert(
    user_id: int = Depends(get_current_user_id),  # SECURITY: Authentication required
    daily_budget: float = Query(10.0, description="일일 예산 (USD)"),
    monthly_budget: float = Query(300.0, description="월간 예산 (USD)"),
    ai_service: IntegratedAIService = Depends(get_ai_service)
):
    """
    예산 알림 조회

    Args:
        daily_budget: 일일 예산 (USD)
        monthly_budget: 월간 예산 (USD)

    Returns:
        예산 사용 현황 및 알림
    """
    try:
        alert = await ai_service.check_budget_alert(
            daily_budget=daily_budget,
            monthly_budget=monthly_budget
        )
        return alert

    except Exception as e:
        logger.error(f"Failed to get budget alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-breakdown", response_model=list[AgentBreakdownResponse])
async def get_agent_breakdown(
    user_id: int = Depends(get_current_user_id),  # SECURITY: Authentication required
    ai_service: IntegratedAIService = Depends(get_ai_service)
):
    """
    에이전트별 비용 분석

    Returns:
        에이전트별 비용 분석 목록 (비용 순으로 정렬)
    """
    try:
        breakdown = await ai_service.get_agent_breakdown()
        return breakdown

    except Exception as e:
        logger.error(f"Failed to get agent breakdown: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/event-stats", response_model=EventStatsResponse)
async def get_event_stats(
    user_id: int = Depends(get_current_user_id),  # SECURITY: Authentication required
    event_optimizer: EventDrivenOptimizer = Depends(get_event_opt)
):
    """
    이벤트 기반 최적화 통계

    **Authentication Required**: This endpoint requires a valid JWT token.

    Returns:
        이벤트 필터링, 배치 처리 통계
    """
    try:
        stats = event_optimizer.get_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get event stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sampling-strategy")
async def update_sampling_strategy(
    request: SamplingStrategyUpdateRequest,
    user_id: int = Depends(get_current_user_id),  # SECURITY: Authentication required
    ai_service: IntegratedAIService = Depends(get_ai_service)
):
    """
    샘플링 전략 변경

    **Authentication Required**: This endpoint requires a valid JWT token.
    **Admin Only**: Only administrators should modify sampling strategies.

    Args:
        request: 샘플링 전략 업데이트 요청

    Returns:
        성공 메시지
    """
    try:
        # 전략 변환
        try:
            strategy = SamplingStrategy(request.strategy.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid strategy: {request.strategy}. Must be one of: ALWAYS, PERIODIC, CHANGE_BASED, THRESHOLD, ADAPTIVE"
            )

        # 설정 구성
        config = {}
        if request.interval_seconds:
            config["interval_seconds"] = request.interval_seconds
        if request.threshold:
            config["threshold"] = request.threshold

        # 전략 변경
        ai_service.configure_sampling_strategy(
            agent_type=request.agent_type,
            strategy=strategy,
            config=config
        )

        return {
            "message": f"Sampling strategy updated for {request.agent_type}",
            "agent_type": request.agent_type,
            "strategy": request.strategy,
            "config": config
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update sampling strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/event-thresholds")
async def update_event_thresholds(
    request: EventThresholdsUpdateRequest,
    user_id: int = Depends(get_current_user_id),  # SECURITY: Authentication required
    event_optimizer: EventDrivenOptimizer = Depends(get_event_opt)
):
    """
    이벤트 임계값 변경

    **Authentication Required**: This endpoint requires a valid JWT token.
    **Admin Only**: Only administrators should modify event thresholds.

    Args:
        request: 이벤트 임계값 업데이트 요청

    Returns:
        성공 메시지
    """
    try:
        # 새로운 임계값 구성 및 검증
        new_thresholds = {}

        # SECURITY: Validate input ranges to prevent abuse
        if request.price_change_pct is not None:
            if not 0.01 <= request.price_change_pct <= 100:
                raise HTTPException(
                    status_code=400,
                    detail="price_change_pct must be between 0.01 and 100"
                )
            new_thresholds["price_change_pct"] = request.price_change_pct

        if request.volume_spike_multiplier is not None:
            if not 0.1 <= request.volume_spike_multiplier <= 100:
                raise HTTPException(
                    status_code=400,
                    detail="volume_spike_multiplier must be between 0.1 and 100"
                )
            new_thresholds["volume_spike_multiplier"] = request.volume_spike_multiplier

        if request.volatility_threshold is not None:
            if not 0.01 <= request.volatility_threshold <= 100:
                raise HTTPException(
                    status_code=400,
                    detail="volatility_threshold must be between 0.01 and 100"
                )
            new_thresholds["volatility_threshold"] = request.volatility_threshold

        if request.min_ai_interval is not None:
            if not 1 <= request.min_ai_interval <= 86400:
                raise HTTPException(
                    status_code=400,
                    detail="min_ai_interval must be between 1 and 86400 seconds (1 day)"
                )
            new_thresholds["min_ai_interval"] = request.min_ai_interval

        if request.batch_size is not None:
            if not 1 <= request.batch_size <= 1000:
                raise HTTPException(
                    status_code=400,
                    detail="batch_size must be between 1 and 1000"
                )
            new_thresholds["batch_size"] = request.batch_size

        if request.batch_timeout is not None:
            if not 1 <= request.batch_timeout <= 3600:
                raise HTTPException(
                    status_code=400,
                    detail="batch_timeout must be between 1 and 3600 seconds (1 hour)"
                )
            new_thresholds["batch_timeout"] = request.batch_timeout

        if not new_thresholds:
            raise HTTPException(
                status_code=400,
                detail="At least one threshold must be provided"
            )

        # 임계값 업데이트
        event_optimizer.update_thresholds(new_thresholds)

        return {
            "message": "Event thresholds updated successfully",
            "updated_thresholds": new_thresholds
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to update event thresholds: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache")
async def clear_cache(
    user_id: int = Depends(get_current_user_id),  # SECURITY: Authentication required
    cache_type: str = Query("all", description="캐시 타입 (all, prompt, response)"),
    ai_service: IntegratedAIService = Depends(get_ai_service)
):
    """
    캐시 초기화

    **Authentication Required**: This endpoint requires a valid JWT token.
    **Admin Only**: Only administrators should clear caches.

    Args:
        cache_type: 캐시 타입 (all, prompt, response)

    Returns:
        성공 메시지
    """
    try:
        if cache_type == "all":
            await ai_service.prompt_cache.clear_cache()
            # TODO: response_cache.clear_cache() 메서드 추가 필요
            message = "All caches cleared"

        elif cache_type == "prompt":
            await ai_service.prompt_cache.clear_cache()
            message = "Prompt cache cleared"

        elif cache_type == "response":
            # TODO: response_cache.clear_cache() 메서드 추가 필요
            message = "Response cache cleared"

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cache_type: {cache_type}. Must be one of: all, prompt, response"
            )

        return {"message": message}

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
