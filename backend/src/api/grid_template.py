"""
Grid Template API - 사용자용
- 템플릿 목록 조회
- 템플릿 상세 조회
- 템플릿으로 봇 생성
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import User
from ..schemas.grid_template_schema import (
    GridTemplateDetail,
    GridTemplateDetailResponse,
    GridTemplateListItem,
    GridTemplateListResponse,
    UseTemplateRequest,
    UseTemplateResponse,
)
from ..services.grid_template_service import GridTemplateService
from ..utils.jwt_auth import TokenData, get_current_user

router = APIRouter(prefix="/grid-templates", tags=["Grid Templates"])


@router.get("", response_model=GridTemplateListResponse)
async def list_templates(
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTCUSDT)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    공개된 그리드봇 템플릿 목록 조회

    - AI 탭에 표시될 템플릿들
    - is_featured 템플릿이 상단에 표시
    - ROI 높은 순으로 정렬
    """
    service = GridTemplateService(db)
    templates = await service.get_active_templates(
        symbol=symbol, limit=limit, offset=offset
    )

    items = []
    for t in templates:
        items.append(
            GridTemplateListItem(
                id=t.id,
                name=t.name,
                symbol=t.symbol,
                direction=t.direction,
                leverage=t.leverage,
                backtest_roi_30d=float(t.backtest_roi_30d)
                if t.backtest_roi_30d
                else None,
                backtest_max_drawdown=float(t.backtest_max_drawdown)
                if t.backtest_max_drawdown
                else None,
                roi_chart=t.backtest_roi_history[-30:]
                if t.backtest_roi_history
                else None,
                recommended_period=t.recommended_period,
                min_investment=float(t.min_investment),
                active_users=t.active_users or 0,
                total_funds_in_use=float(t.total_funds_in_use or 0),
                is_featured=t.is_featured,
            )
        )

    return GridTemplateListResponse(success=True, data=items, total=len(items))


@router.get("/{template_id}", response_model=GridTemplateDetailResponse)
async def get_template_detail(
    template_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    템플릿 상세 정보 조회

    - 그리드 설정 상세
    - 백테스트 결과 상세
    - 사용자가 "Use" 전에 확인하는 정보
    """
    service = GridTemplateService(db)
    template = await service.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if not template.is_active:
        raise HTTPException(status_code=404, detail="Template is not available")

    return GridTemplateDetailResponse(
        success=True,
        data=GridTemplateDetail(
            id=template.id,
            name=template.name,
            symbol=template.symbol,
            direction=template.direction,
            leverage=template.leverage,
            lower_price=float(template.lower_price),
            upper_price=float(template.upper_price),
            grid_count=template.grid_count,
            grid_mode=template.grid_mode,
            min_investment=float(template.min_investment),
            recommended_investment=float(template.recommended_investment)
            if template.recommended_investment
            else None,
            backtest_roi_30d=float(template.backtest_roi_30d)
            if template.backtest_roi_30d
            else None,
            backtest_max_drawdown=float(template.backtest_max_drawdown)
            if template.backtest_max_drawdown
            else None,
            backtest_total_trades=template.backtest_total_trades,
            backtest_win_rate=float(template.backtest_win_rate)
            if template.backtest_win_rate
            else None,
            backtest_updated_at=template.backtest_updated_at,
            roi_chart=template.backtest_roi_history[-30:]
            if template.backtest_roi_history
            else None,
            recommended_period=template.recommended_period,
            description=template.description,
            tags=template.tags,
            active_users=template.active_users or 0,
            total_funds_in_use=float(template.total_funds_in_use or 0),
            is_featured=template.is_featured,
        ),
    )


@router.post("/{template_id}/use", response_model=UseTemplateResponse)
async def use_template(
    template_id: int,
    request: UseTemplateRequest,
    db: AsyncSession = Depends(get_session),
    current_user: TokenData = Depends(get_current_user),
):
    """
    템플릿으로 그리드봇 생성

    - 투자 금액과 레버리지만 입력
    - 나머지 설정은 템플릿에서 복사
    - 생성 후 바로 시작 가능한 상태

    Request:
    - investment_amount: 투자할 금액 (USDT)
    - leverage: 레버리지 (선택, 미입력시 템플릿 기본값)
    """
    service = GridTemplateService(db)

    try:
        bot_instance, grid_config = await service.use_template(
            template_id=template_id, user_id=current_user.user_id, request=request
        )

        return UseTemplateResponse(
            bot_instance_id=bot_instance.id,
            grid_config_id=grid_config.id,
            message="Grid bot created from template. Ready to start!",
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create bot: {str(e)}") from e
