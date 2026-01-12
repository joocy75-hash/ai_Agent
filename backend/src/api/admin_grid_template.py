"""
Grid Template Admin API - 관리자용
- 템플릿 CRUD
- 공개/비공개 전환
- 백테스트 실행 트리거
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..schemas.backtest_schema import GridBacktestRequest, GridBacktestResponse
from ..schemas.grid_template_schema import (
    GridTemplateAdminDetail,
    GridTemplateCreate,
    GridTemplateUpdate,
)
from ..services.grid_backtester import get_grid_backtester
from ..services.grid_template_service import GridTemplateService
from ..utils.auth_dependencies import require_admin
from ..utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/grid-templates",
    tags=["Admin - Grid Templates"],
    dependencies=[Depends(require_admin)]  # 관리자만 접근 가능
)


def template_to_admin_detail(t) -> GridTemplateAdminDetail:
    """GridTemplate 모델을 관리자용 상세 DTO로 변환합니다.

    데이터베이스에서 조회한 GridTemplate ORM 객체를 API 응답에 사용할
    GridTemplateAdminDetail Pydantic 스키마로 변환합니다. Decimal 타입의
    필드들은 float로 변환하고, None 값은 적절히 처리합니다.

    Args:
        t: GridTemplate ORM 모델 인스턴스. 다음 속성들을 포함해야 합니다:
            - id, name, symbol, direction, leverage: 기본 설정
            - lower_price, upper_price, grid_count, grid_mode: 그리드 설정
            - min_investment, recommended_investment: 투자금 설정
            - backtest_*: 백테스트 결과 필드들
            - active_users, total_users, total_funds_in_use: 사용 통계
            - is_active, is_featured, sort_order: 상태 및 정렬
            - created_by, created_at, updated_at: 메타데이터

    Returns:
        GridTemplateAdminDetail: 관리자 API 응답용 DTO 객체.
            모든 Decimal 필드가 float로 변환되고, None 값이 적절히 처리됨.
    """
    return GridTemplateAdminDetail(
        id=t.id,
        name=t.name,
        symbol=t.symbol,
        direction=t.direction,
        leverage=t.leverage,
        lower_price=float(t.lower_price),
        upper_price=float(t.upper_price),
        grid_count=t.grid_count,
        grid_mode=t.grid_mode,
        min_investment=float(t.min_investment),
        recommended_investment=float(t.recommended_investment) if t.recommended_investment else None,
        backtest_roi_30d=float(t.backtest_roi_30d) if t.backtest_roi_30d else None,
        backtest_max_drawdown=float(t.backtest_max_drawdown) if t.backtest_max_drawdown else None,
        backtest_total_trades=t.backtest_total_trades,
        backtest_win_rate=float(t.backtest_win_rate) if t.backtest_win_rate else None,
        backtest_roi_history=t.backtest_roi_history,
        backtest_updated_at=t.backtest_updated_at,
        recommended_period=t.recommended_period,
        description=t.description,
        tags=t.tags,
        active_users=t.active_users or 0,
        total_users=t.total_users or 0,
        total_funds_in_use=float(t.total_funds_in_use or 0),
        is_active=t.is_active,
        is_featured=t.is_featured,
        sort_order=t.sort_order,
        created_by=t.created_by,
        created_at=t.created_at,
        updated_at=t.updated_at
    )


@router.get("", response_model=List[GridTemplateAdminDetail])
async def list_all_templates(
    include_inactive: bool = Query(False, description="Include inactive templates"),
    db: AsyncSession = Depends(get_session)
):
    """모든 템플릿 조회 (관리자)"""
    service = GridTemplateService(db)
    templates = await service.get_all_templates(include_inactive=include_inactive)

    return [template_to_admin_detail(t) for t in templates]


@router.post("", response_model=GridTemplateAdminDetail)
async def create_template(
    data: GridTemplateCreate,
    db: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id)
):
    """새 템플릿 생성 (관리자)"""
    service = GridTemplateService(db)
    template = await service.create_template(
        data=data,
        created_by=current_user_id
    )

    return template_to_admin_detail(template)


@router.get("/{template_id}", response_model=GridTemplateAdminDetail)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_session)
):
    """템플릿 상세 조회 (관리자)"""
    service = GridTemplateService(db)
    template = await service.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template_to_admin_detail(template)


@router.put("/{template_id}", response_model=GridTemplateAdminDetail)
async def update_template(
    template_id: int,
    data: GridTemplateUpdate,
    db: AsyncSession = Depends(get_session)
):
    """템플릿 수정 (관리자)"""
    service = GridTemplateService(db)
    template = await service.update_template(template_id, data)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template_to_admin_detail(template)


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_session)
):
    """템플릿 삭제 (비활성화)"""
    service = GridTemplateService(db)
    success = await service.delete_template(template_id)

    if not success:
        raise HTTPException(status_code=404, detail="Template not found")

    return {"success": True, "message": "Template deactivated"}


@router.patch("/{template_id}/toggle")
async def toggle_template(
    template_id: int,
    db: AsyncSession = Depends(get_session)
):
    """템플릿 공개/비공개 전환"""
    service = GridTemplateService(db)
    template = await service.toggle_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "success": True,
        "is_active": template.is_active,
        "message": f"Template {'activated' if template.is_active else 'deactivated'}"
    }


@router.post("/{template_id}/backtest", response_model=GridBacktestResponse)
async def run_backtest(
    template_id: int,
    days: int = Query(30, ge=7, le=90, description="Backtest period in days"),
    granularity: str = Query("5m", description="Candle granularity"),
    db: AsyncSession = Depends(get_session)
):
    """
    템플릿 백테스트 실행 (관리자)

    - 과거 데이터로 그리드 시뮬레이션
    - 결과를 템플릿에 자동 저장
    """
    service = GridTemplateService(db)
    template = await service.get_template_by_id(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # 백테스트 실행
    backtester = get_grid_backtester()

    try:
        result = await backtester.run_backtest(
            symbol=template.symbol,
            direction=template.direction,
            lower_price=template.lower_price,
            upper_price=template.upper_price,
            grid_count=template.grid_count,
            grid_mode=template.grid_mode,
            leverage=template.leverage,
            investment=template.min_investment,  # 최소 투자금액 기준
            days=days,
            granularity=granularity
        )

        # 결과를 템플릿에 저장
        await service.save_backtest_result(
            template_id=template_id,
            roi_30d=result.roi_30d,
            max_drawdown=result.max_drawdown,
            total_trades=result.total_trades,
            win_rate=result.win_rate,
            roi_history=result.daily_roi
        )

        return GridBacktestResponse(
            success=True,
            roi_30d=float(result.roi_30d),
            max_drawdown=float(result.max_drawdown),
            total_trades=result.total_trades,
            win_rate=float(result.win_rate),
            total_profit=float(result.total_profit),
            avg_profit_per_trade=float(result.avg_profit_per_trade),
            daily_roi=result.daily_roi,
            backtest_days=result.backtest_days,
            total_candles=result.total_candles,
            grid_cycles_completed=result.grid_cycles_completed
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Backtest failed")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}") from e


@router.post("/backtest/preview", response_model=GridBacktestResponse)
async def preview_backtest(
    request: GridBacktestRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    백테스트 미리보기 (템플릿 저장 전 테스트)

    - 템플릿 생성 전에 설정값 검증용
    - 결과 저장 안함
    """
    backtester = get_grid_backtester()

    try:
        result = await backtester.run_backtest(
            symbol=request.symbol,
            direction=request.direction,
            lower_price=request.lower_price,
            upper_price=request.upper_price,
            grid_count=request.grid_count,
            grid_mode=request.grid_mode,
            leverage=request.leverage,
            investment=request.investment,
            days=request.days,
            granularity=request.granularity
        )

        return GridBacktestResponse(
            success=True,
            roi_30d=float(result.roi_30d),
            max_drawdown=float(result.max_drawdown),
            total_trades=result.total_trades,
            win_rate=float(result.win_rate),
            total_profit=float(result.total_profit),
            avg_profit_per_trade=float(result.avg_profit_per_trade),
            daily_roi=result.daily_roi,
            backtest_days=result.backtest_days,
            total_candles=result.total_candles,
            grid_cycles_completed=result.grid_cycles_completed
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Backtest preview failed")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}") from e
