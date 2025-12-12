"""
Trend Template API - 사용자용
- 템플릿 목록 조회
- 템플릿 상세 조회
- 템플릿으로 AI 추세 봇 생성
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..utils.jwt_auth import get_current_user, TokenData
from ..database.models import TrendBotTemplate, TrendDirection, BotInstance, BotType


router = APIRouter(prefix="/trend-templates", tags=["Trend Templates"])


# ============================================================
# Schemas
# ============================================================


class TrendTemplateListItem(BaseModel):
    id: int
    name: str
    symbol: str
    direction: str
    leverage: int
    strategy_type: str
    stop_loss_percent: float
    take_profit_percent: float
    backtest_roi_30d: Optional[float]
    backtest_win_rate: Optional[float]
    backtest_max_drawdown: Optional[float]
    recommended_period: Optional[str]
    min_investment: float
    risk_level: str
    active_users: int
    is_featured: bool


class TrendTemplateListResponse(BaseModel):
    success: bool
    data: List[TrendTemplateListItem]
    total: int


class TrendTemplateDetail(TrendTemplateListItem):
    description: Optional[str]
    recommended_investment: Optional[float]
    backtest_total_trades: Optional[int]
    tags: Optional[List[str]]


class TrendTemplateDetailResponse(BaseModel):
    success: bool
    data: TrendTemplateDetail


class UseTrendTemplateRequest(BaseModel):
    investment_amount: float = Field(..., gt=0, description="투자금액 (USDT)")
    leverage: Optional[int] = Field(None, ge=1, le=125, description="레버리지 (선택)")


class UseTrendTemplateResponse(BaseModel):
    bot_instance_id: int
    message: str


# ============================================================
# Helper Functions
# ============================================================


def template_to_list_item(template: TrendBotTemplate) -> dict:
    """템플릿을 목록 항목으로 변환"""
    return {
        "id": template.id,
        "name": template.name,
        "symbol": template.symbol,
        "direction": template.direction.value if template.direction else "long",
        "leverage": template.leverage,
        "strategy_type": template.strategy_type,
        "stop_loss_percent": float(template.stop_loss_percent or 2.0),
        "take_profit_percent": float(template.take_profit_percent or 4.0),
        "backtest_roi_30d": float(template.backtest_roi_30d)
        if template.backtest_roi_30d
        else None,
        "backtest_win_rate": float(template.backtest_win_rate)
        if template.backtest_win_rate
        else None,
        "backtest_max_drawdown": float(template.backtest_max_drawdown)
        if template.backtest_max_drawdown
        else None,
        "recommended_period": template.recommended_period,
        "min_investment": float(template.min_investment or 50),
        "risk_level": template.risk_level or "medium",
        "active_users": template.active_users or 0,
        "is_featured": template.is_featured,
    }


def template_to_detail(template: TrendBotTemplate) -> dict:
    """템플릿을 상세 정보로 변환"""
    item = template_to_list_item(template)
    item.update(
        {
            "description": template.description,
            "recommended_investment": float(template.recommended_investment)
            if template.recommended_investment
            else None,
            "backtest_total_trades": template.backtest_total_trades,
            "tags": template.tags,
        }
    )
    return item


# ============================================================
# Endpoints
# ============================================================


@router.get("", response_model=TrendTemplateListResponse)
async def list_trend_templates(
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTCUSDT)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    current_user: TokenData = Depends(get_current_user),
):
    """
    공개된 AI 추세 봇 템플릿 목록 조회

    - AI 탭에 표시될 템플릿들
    - is_featured 템플릿이 상단에 표시
    - ROI 높은 순으로 정렬
    """
    query = (
        select(TrendBotTemplate)
        .where(TrendBotTemplate.is_active == True)
        .order_by(
            desc(TrendBotTemplate.is_featured),
            TrendBotTemplate.sort_order,
            desc(TrendBotTemplate.backtest_roi_30d),
        )
    )

    if symbol:
        query = query.where(TrendBotTemplate.symbol == symbol.upper())

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    templates = result.scalars().all()

    items = [TrendTemplateListItem(**template_to_list_item(t)) for t in templates]

    return TrendTemplateListResponse(success=True, data=items, total=len(items))


@router.get("/{template_id}", response_model=TrendTemplateDetailResponse)
async def get_trend_template_detail(
    template_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: TokenData = Depends(get_current_user),
):
    """
    템플릿 상세 정보 조회

    - 전략 설정 상세
    - 백테스트 결과 상세
    - 사용자가 "Use" 전에 확인하는 정보
    """
    result = await db.execute(
        select(TrendBotTemplate).where(TrendBotTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not template.is_active:
        raise HTTPException(status_code=404, detail="Template is not available")

    return TrendTemplateDetailResponse(
        success=True, data=TrendTemplateDetail(**template_to_detail(template))
    )


@router.post("/{template_id}/use", response_model=UseTrendTemplateResponse)
async def use_trend_template(
    template_id: int,
    request: UseTrendTemplateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: TokenData = Depends(get_current_user),
):
    """
    템플릿으로 AI 추세 봇 생성

    - 투자 금액과 레버리지 입력
    - 나머지 설정은 템플릿에서 복사
    - 생성 후 바로 시작 가능한 상태
    """
    # 템플릿 조회
    result = await db.execute(
        select(TrendBotTemplate).where(TrendBotTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not template.is_active:
        raise HTTPException(status_code=400, detail="Template is not available")

    # 최소 투자금액 확인
    min_investment = float(template.min_investment or 50)
    if request.investment_amount < min_investment:
        raise HTTPException(
            status_code=400, detail=f"Minimum investment is {min_investment} USDT"
        )

    # 레버리지 결정 (요청 값 우선, 없으면 템플릿 기본값)
    leverage = request.leverage if request.leverage else template.leverage

    try:
        # AI 추세 봇 인스턴스 생성
        bot_instance = BotInstance(
            user_id=current_user.user_id,
            name=f"{template.name} ({template.symbol})",
            description=f"AI 추세 봇 - {template.description or template.strategy_type}",
            bot_type=BotType.AI_TREND,
            symbol=template.symbol,
            max_leverage=leverage,
            stop_loss_percent=template.stop_loss_percent,
            take_profit_percent=template.take_profit_percent,
            allocation_percent=10.0,  # 기본 할당
            is_running=False,
            is_active=True,
            telegram_notify=True,
        )

        db.add(bot_instance)
        await db.commit()
        await db.refresh(bot_instance)

        # 템플릿 사용자 수 증가
        template.active_users = (template.active_users or 0) + 1
        template.total_users = (template.total_users or 0) + 1
        await db.commit()

        return UseTrendTemplateResponse(
            bot_instance_id=bot_instance.id,
            message=f"AI 추세 봇이 생성되었습니다. 시작 준비 완료!",
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create bot: {str(e)}")
