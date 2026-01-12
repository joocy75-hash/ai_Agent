"""
Admin Trend Template API - 관리자용 AI 추세 봇 템플릿 관리
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_db
from ..database.models import TrendBotTemplate, TrendDirection, User
from ..utils.auth_deps import get_current_admin_user

router = APIRouter(prefix="/admin/trend-template", tags=["Admin Trend Templates"])


# ============================================================
# Schemas
# ============================================================


class TrendTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    symbol: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = None
    strategy_type: str = "ema_crossover"
    direction: str = "long"
    leverage: int = Field(default=5, ge=1, le=125)
    stop_loss_percent: float = Field(default=2.0, ge=0.1, le=50)
    take_profit_percent: float = Field(default=4.0, ge=0.1, le=100)
    min_investment: float = Field(default=10.0, ge=10)
    recommended_investment: Optional[float] = None
    risk_level: str = "medium"
    tags: Optional[List[str]] = None
    is_active: bool = True
    is_featured: bool = False
    sort_order: int = 0


class TrendTemplateUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    description: Optional[str] = None
    strategy_type: Optional[str] = None
    direction: Optional[str] = None
    leverage: Optional[int] = None
    stop_loss_percent: Optional[float] = None
    take_profit_percent: Optional[float] = None
    min_investment: Optional[float] = None
    recommended_investment: Optional[float] = None
    risk_level: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_order: Optional[int] = None
    # 백테스트 결과
    backtest_roi_30d: Optional[float] = None
    backtest_win_rate: Optional[float] = None
    backtest_max_drawdown: Optional[float] = None
    backtest_total_trades: Optional[int] = None


class TrendTemplateResponse(BaseModel):
    id: int
    name: str
    symbol: str
    description: Optional[str]
    strategy_type: str
    direction: str
    leverage: int
    stop_loss_percent: float
    take_profit_percent: float
    min_investment: float
    recommended_investment: Optional[float]
    backtest_roi_30d: Optional[float]
    backtest_win_rate: Optional[float]
    backtest_max_drawdown: Optional[float]
    backtest_total_trades: Optional[int]
    risk_level: str
    tags: Optional[List[str]]
    active_users: int
    total_users: int
    is_active: bool
    is_featured: bool
    sort_order: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


def template_to_response(template: TrendBotTemplate) -> dict:
    """TrendBotTemplate 모델을 API 응답용 딕셔너리로 변환합니다.

    데이터베이스에서 조회한 TrendBotTemplate ORM 객체를 JSON 직렬화 가능한
    딕셔너리로 변환합니다. Decimal 타입은 float로, Enum은 문자열로,
    datetime은 ISO 형식 문자열로 변환합니다.

    Args:
        template: TrendBotTemplate ORM 모델 인스턴스. AI 추세 봇 템플릿의
            모든 설정 정보를 포함합니다:
            - 기본 정보: id, name, symbol, description
            - 전략 설정: strategy_type, direction, leverage
            - 리스크 설정: stop_loss_percent, take_profit_percent
            - 투자 설정: min_investment, recommended_investment
            - 백테스트 결과: backtest_roi_30d, backtest_win_rate 등
            - 상태: is_active, is_featured, sort_order
            - 사용 통계: active_users, total_users

    Returns:
        dict: API 응답용 딕셔너리. 모든 값이 JSON 직렬화 가능한 형태로 변환됨.
            - direction: TrendDirection enum이 문자열로 변환됨
            - Decimal 필드들: float로 변환됨
            - datetime 필드들: ISO 8601 형식 문자열로 변환됨
            - None 값: 그대로 유지되거나 기본값으로 대체됨
    """
    return {
        "id": template.id,
        "name": template.name,
        "symbol": template.symbol,
        "description": template.description,
        "strategy_type": template.strategy_type,
        "direction": template.direction.value if template.direction else "long",
        "leverage": template.leverage,
        "stop_loss_percent": float(template.stop_loss_percent or 2.0),
        "take_profit_percent": float(template.take_profit_percent or 4.0),
        "min_investment": float(template.min_investment or 50),
        "recommended_investment": float(template.recommended_investment)
        if template.recommended_investment
        else None,
        "backtest_roi_30d": float(template.backtest_roi_30d)
        if template.backtest_roi_30d
        else None,
        "backtest_win_rate": float(template.backtest_win_rate)
        if template.backtest_win_rate
        else None,
        "backtest_max_drawdown": float(template.backtest_max_drawdown)
        if template.backtest_max_drawdown
        else None,
        "backtest_total_trades": template.backtest_total_trades,
        "risk_level": template.risk_level or "medium",
        "tags": template.tags,
        "active_users": template.active_users or 0,
        "total_users": template.total_users or 0,
        "is_active": template.is_active,
        "is_featured": template.is_featured,
        "sort_order": template.sort_order or 0,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


# ============================================================
# Endpoints
# ============================================================


@router.get("/", response_model=List[TrendTemplateResponse])
async def list_trend_templates(
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
    include_inactive: bool = False,
):
    """모든 AI 추세 봇 템플릿 조회 (관리자용)"""
    query = select(TrendBotTemplate).order_by(
        desc(TrendBotTemplate.is_featured),
        TrendBotTemplate.sort_order,
        desc(TrendBotTemplate.created_at),
    )

    if not include_inactive:
        query = query.where(TrendBotTemplate.is_active is True)

    result = await session.execute(query)
    templates = result.scalars().all()

    return [template_to_response(t) for t in templates]


@router.get("/{template_id}", response_model=TrendTemplateResponse)
async def get_trend_template(
    template_id: int,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """특정 템플릿 상세 조회"""
    result = await session.execute(
        select(TrendBotTemplate).where(TrendBotTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template_to_response(template)


@router.post(
    "/", response_model=TrendTemplateResponse, status_code=status.HTTP_201_CREATED
)
async def create_trend_template(
    data: TrendTemplateCreate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """새 AI 추세 봇 템플릿 생성"""
    # direction을 Enum으로 변환
    try:
        direction = TrendDirection(data.direction)
    except ValueError:
        direction = TrendDirection.LONG

    template = TrendBotTemplate(
        name=data.name,
        symbol=data.symbol.upper(),
        description=data.description,
        strategy_type=data.strategy_type,
        direction=direction,
        leverage=data.leverage,
        stop_loss_percent=data.stop_loss_percent,
        take_profit_percent=data.take_profit_percent,
        min_investment=data.min_investment,
        recommended_investment=data.recommended_investment,
        risk_level=data.risk_level,
        tags=data.tags,
        is_active=data.is_active,
        is_featured=data.is_featured,
        sort_order=data.sort_order,
        created_by=admin.id,
    )

    session.add(template)
    await session.commit()
    await session.refresh(template)

    return template_to_response(template)


@router.put("/{template_id}", response_model=TrendTemplateResponse)
async def update_trend_template(
    template_id: int,
    data: TrendTemplateUpdate,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """템플릿 수정"""
    result = await session.execute(
        select(TrendBotTemplate).where(TrendBotTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = data.model_dump(exclude_unset=True)

    # direction 처리
    if "direction" in update_data:
        try:
            update_data["direction"] = TrendDirection(update_data["direction"])
        except ValueError:
            update_data["direction"] = TrendDirection.LONG

    # 백테스트 결과 업데이트 시 시각 기록
    if any(k.startswith("backtest_") for k in update_data.keys()):
        update_data["backtest_updated_at"] = datetime.utcnow()

    for key, value in update_data.items():
        setattr(template, key, value)

    await session.commit()
    await session.refresh(template)

    return template_to_response(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trend_template(
    template_id: int,
    session: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """템플릿 삭제"""
    result = await session.execute(
        select(TrendBotTemplate).where(TrendBotTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await session.delete(template)
    await session.commit()

    return None
