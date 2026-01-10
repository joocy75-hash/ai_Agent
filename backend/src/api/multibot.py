"""
멀티봇 트레이딩 시스템 API v2.0

주요 기능:
- 전략 템플릿 조회
- 봇 시작/중지
- 잔고 요약 조회

관련 문서: docs/MULTI_BOT_IMPLEMENTATION_PLAN.md
v2.0 변경사항:
- 40% 마진 한도 제거 → 잔고 초과만 체크
- 최대 봇 10개 → 5개
- allocation_percent → allocated_amount (USDT)
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import TrendBotTemplate, BotInstance, BotType
from ..utils.jwt_auth import get_current_user_id
from ..services.balance_controller import BalanceController
from ..services.multibot_manager import MultiBotManager
from ..schemas.multibot_schema import (
    TrendTemplateResponse,
    TrendTemplateListResponse,
    BotStartRequest,
    BotStopRequest,
    BotInstanceResponse,
    BalanceSummaryResponse,
    BalanceCheckRequest,
    BalanceCheckResponse,
    MultiBotSuccessResponse,
    MultiBotErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/multibot", tags=["Multi-Bot Trading"])


# ============================================================
# 헬퍼 함수
# ============================================================


def template_to_response(template: TrendBotTemplate) -> TrendTemplateResponse:
    """TrendBotTemplate을 응답 스키마로 변환"""
    # tags 안전 처리: list가 아니면 빈 리스트
    tags = template.tags if isinstance(template.tags, list) else []

    return TrendTemplateResponse(
        id=template.id,
        name=template.name,
        symbol=template.symbol,
        description=template.description,
        strategy_type=template.strategy_type or "trend_following",
        direction=template.direction.value if template.direction else "long",
        leverage=template.leverage or 10,
        stop_loss_percent=float(template.stop_loss_percent or 2.0),
        take_profit_percent=float(template.take_profit_percent or 4.0),
        min_investment=float(template.min_investment or 10),
        recommended_investment=float(template.recommended_investment) if template.recommended_investment else None,
        risk_level=template.risk_level or "medium",
        backtest_roi_30d=float(template.backtest_roi_30d) if template.backtest_roi_30d else None,
        backtest_win_rate=float(template.backtest_win_rate) if template.backtest_win_rate else None,
        backtest_max_drawdown=float(template.backtest_max_drawdown) if template.backtest_max_drawdown else None,
        backtest_total_trades=template.backtest_total_trades,
        is_active=template.is_active,
        is_featured=template.is_featured or False,
        tags=tags,
    )


def bot_to_response(bot: BotInstance, template: Optional[TrendBotTemplate] = None) -> BotInstanceResponse:
    """BotInstance를 응답 스키마로 변환"""
    allocated = float(bot.allocated_amount or 0)
    pnl = float(bot.total_pnl or 0)
    pnl_percent = (pnl / allocated * 100) if allocated > 0 else 0

    total_trades = bot.total_trades or 0
    winning_trades = bot.winning_trades or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    return BotInstanceResponse(
        id=bot.id,
        name=bot.name,
        symbol=bot.symbol,
        template_id=bot.trend_template_id,
        template_name=template.name if template else None,
        strategy_type=template.strategy_type if template else None,
        allocated_amount=allocated,
        leverage=bot.max_leverage or 10,
        current_pnl=pnl,
        current_pnl_percent=round(pnl_percent, 2),
        total_trades=total_trades,
        winning_trades=winning_trades,
        win_rate=round(win_rate, 2),
        is_running=bot.is_running,
        last_error=bot.last_error,
        last_signal_at=bot.last_signal_at,
        created_at=bot.created_at,
        last_started_at=bot.last_started_at,
    )


# ============================================================
# 템플릿 엔드포인트
# ============================================================


@router.get("/templates", response_model=TrendTemplateListResponse)
async def get_templates(
    symbol: Optional[str] = Query(None, description="심볼로 필터 (예: BTCUSDT)"),
    featured_only: bool = Query(False, description="추천 템플릿만"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    활성화된 전략 템플릿 목록 조회

    - 추천(featured) 템플릿이 상단에 표시
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

    if featured_only:
        query = query.where(TrendBotTemplate.is_featured == True)

    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    templates = result.scalars().all()

    # 추천 템플릿 개수
    featured_count = sum(1 for t in templates if t.is_featured)

    return TrendTemplateListResponse(
        templates=[template_to_response(t) for t in templates],
        total=len(templates),
        featured_count=featured_count,
    )


@router.get("/templates/{template_id}", response_model=TrendTemplateResponse)
async def get_template_detail(
    template_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    전략 템플릿 상세 정보 조회

    - 백테스트 결과 포함
    - 봇 시작 전 확인용
    """
    template = await session.get(TrendBotTemplate, template_id)

    if not template:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다")

    if not template.is_active:
        raise HTTPException(status_code=400, detail="비활성화된 템플릿입니다")

    return template_to_response(template)


# ============================================================
# 봇 관리 엔드포인트
# ============================================================


@router.post("/bots", response_model=MultiBotSuccessResponse)
async def start_bot(
    payload: BotStartRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    새 봇 시작

    - 템플릿 선택 후 투자 금액만 입력하면 즉시 시작
    - 잔고 초과 체크 (40% 한도 없음)
    - 사용자당 최대 5개 봇
    - 동일 심볼 중복 불가
    """
    # 1. 잔고 체크
    balance_controller = BalanceController(session)
    can_start, message = await balance_controller.check_can_start(user_id, payload.amount)

    if not can_start:
        raise HTTPException(status_code=400, detail=message)

    # 2. 봇 생성
    multibot_manager = MultiBotManager(session)

    try:
        bot_instance = await multibot_manager.start_bot(
            user_id=user_id,
            template_id=payload.template_id,
            amount=payload.amount,
            name=payload.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. BotRunner에 시작 요청
    try:
        from ..workers.manager import BotManager
        manager: BotManager = request.app.state.bot_manager
        await manager.start_bot_instance(bot_instance.id, user_id)
    except Exception as e:
        logger.error(f"Failed to start bot runner for instance {bot_instance.id}: {e}")
        # 봇 러너 시작 실패해도 DB 상태는 유지 (재시작 가능)

    logger.info(f"Bot started: user={user_id}, bot_id={bot_instance.id}, amount=${payload.amount}")

    return MultiBotSuccessResponse(
        success=True,
        message=f"봇 '{bot_instance.name}'이(가) 시작되었습니다",
        bot_id=bot_instance.id,
        data={
            "symbol": bot_instance.symbol,
            "allocated_amount": float(bot_instance.allocated_amount),
        }
    )


@router.delete("/bots/{bot_id}", response_model=MultiBotSuccessResponse)
async def stop_bot(
    bot_id: int,
    close_positions: bool = Query(False, description="True면 포지션도 청산"),
    request: Request = None,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    봇 중지

    - close_positions=true 시 열린 포지션 청산
    - 봇 러너 중지 후 DB 상태 업데이트
    """
    multibot_manager = MultiBotManager(session)

    # 봇 존재 확인
    bot = await multibot_manager.get_bot_by_id(user_id, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다")

    if not bot.is_running:
        raise HTTPException(status_code=400, detail="봇이 이미 중지되어 있습니다")

    # BotRunner 중지
    try:
        from ..workers.manager import BotManager
        manager: BotManager = request.app.state.bot_manager
        await manager.stop_bot_instance(bot_id, user_id)
    except Exception as e:
        logger.error(f"Failed to stop bot runner for instance {bot_id}: {e}")

    # DB 상태 업데이트
    stopped = await multibot_manager.stop_bot(user_id, bot_id)

    if not stopped:
        raise HTTPException(status_code=500, detail="봇 중지에 실패했습니다")

    logger.info(f"Bot stopped: user={user_id}, bot_id={bot_id}")

    return MultiBotSuccessResponse(
        success=True,
        message="봇이 중지되었습니다",
        bot_id=bot_id,
    )


@router.get("/bots", response_model=List[BotInstanceResponse])
async def get_user_bots(
    running_only: bool = Query(False, description="실행 중인 봇만"),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    사용자의 봇 목록 조회
    """
    multibot_manager = MultiBotManager(session)
    bots = await multibot_manager.get_user_bots(user_id, running_only=running_only)

    # 템플릿 정보 조회
    responses = []
    for bot in bots:
        template = None
        if bot.trend_template_id:
            template = await session.get(TrendBotTemplate, bot.trend_template_id)
        responses.append(bot_to_response(bot, template))

    return responses


@router.get("/bots/{bot_id}", response_model=BotInstanceResponse)
async def get_bot_detail(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    봇 상세 정보 조회
    """
    multibot_manager = MultiBotManager(session)
    bot = await multibot_manager.get_bot_by_id(user_id, bot_id)

    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다")

    template = None
    if bot.trend_template_id:
        template = await session.get(TrendBotTemplate, bot.trend_template_id)

    return bot_to_response(bot, template)


# ============================================================
# 잔고 엔드포인트
# ============================================================


@router.get("/summary", response_model=BalanceSummaryResponse)
async def get_balance_summary(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    잔고 요약 및 활성 봇 목록 조회

    - 거래소 총 잔고
    - 사용 중인 금액 (활성 봇들의 allocated_amount 합계)
    - 전체 수익률
    - 봇별 상세 정보
    """
    balance_controller = BalanceController(session)
    summary = await balance_controller.get_balance_summary(user_id)

    # bots 데이터를 BotInstanceResponse로 변환
    bots_response = []
    for bot_data in summary.get("bots", []):
        bots_response.append(BotInstanceResponse(
            id=bot_data["id"],
            name=bot_data["name"],
            symbol=bot_data["symbol"],
            template_id=bot_data.get("template_id"),
            template_name=bot_data.get("template_name"),
            strategy_type=bot_data.get("strategy_type"),
            allocated_amount=bot_data["allocated_amount"],
            leverage=bot_data.get("leverage", 10),
            current_pnl=bot_data["current_pnl"],
            current_pnl_percent=bot_data["current_pnl_percent"],
            total_trades=bot_data["total_trades"],
            winning_trades=bot_data["winning_trades"],
            win_rate=bot_data["win_rate"],
            is_running=bot_data["is_running"],
            last_error=bot_data.get("last_error"),
            last_signal_at=bot_data.get("last_signal_at"),
            created_at=bot_data["created_at"],
            last_started_at=bot_data.get("last_started_at"),
        ))

    return BalanceSummaryResponse(
        total_balance=summary["total_balance"],
        used_amount=summary["used_amount"],
        available_amount=summary["available_amount"],
        active_bot_count=summary["active_bot_count"],
        max_bot_count=summary["max_bot_count"],
        total_pnl=summary["total_pnl"],
        total_pnl_percent=summary["total_pnl_percent"],
        bots=bots_response,
    )


@router.post("/check-balance", response_model=BalanceCheckResponse)
async def check_balance(
    payload: BalanceCheckRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    특정 금액에 대한 잔고 확인 (프리뷰용)

    - 봇 시작 전 잔고 충분한지 미리 확인
    - UI에서 실시간 피드백 제공
    """
    balance_controller = BalanceController(session)
    result = await balance_controller.check_balance_for_amount(user_id, payload.amount)

    return BalanceCheckResponse(
        requested_amount=result["requested_amount"],
        available=result["available"],
        current_used=result["current_used"],
        total_balance=result["total_balance"],
        after_used=result["after_used"],
        message=result["message"],
    )


# ============================================================
# 전체 제어 엔드포인트
# ============================================================


@router.post("/stop-all", response_model=MultiBotSuccessResponse)
async def stop_all_bots(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    모든 봇 중지

    - 비상 정지 기능
    - 모든 실행 중인 봇을 중지
    """
    multibot_manager = MultiBotManager(session)
    running_bots = await multibot_manager.get_user_bots(user_id, running_only=True)

    if not running_bots:
        return MultiBotSuccessResponse(
            success=True,
            message="실행 중인 봇이 없습니다",
        )

    # BotRunner 전체 중지
    try:
        from ..workers.manager import BotManager
        manager: BotManager = request.app.state.bot_manager
        await manager.stop_all_user_instances(user_id)
    except Exception as e:
        logger.error(f"Failed to stop all bot runners for user {user_id}: {e}")

    # DB 상태 업데이트
    stopped_count = 0
    for bot in running_bots:
        stopped = await multibot_manager.stop_bot(user_id, bot.id)
        if stopped:
            stopped_count += 1

    logger.info(f"All bots stopped: user={user_id}, count={stopped_count}")

    return MultiBotSuccessResponse(
        success=True,
        message=f"{stopped_count}개의 봇이 중지되었습니다",
        data={"stopped_count": stopped_count},
    )
