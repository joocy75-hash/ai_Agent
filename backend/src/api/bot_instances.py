"""
다중 봇 인스턴스 API

관련 문서: docs/MULTI_BOT_03_IMPLEMENTATION.md
엔드포인트:
- POST   /bot-instances/create     봇 생성
- GET    /bot-instances/list       봇 목록 조회
- GET    /bot-instances/{id}       봇 상세 조회
- PATCH  /bot-instances/{id}       봇 수정
- DELETE /bot-instances/{id}       봇 삭제
- POST   /bot-instances/{id}/start 봇 시작
- POST   /bot-instances/{id}/stop  봇 중지
- POST   /bot-instances/start-all  전체 봇 시작
- POST   /bot-instances/stop-all   전체 봇 중지
- GET    /bot-instances/{id}/stats 봇별 통계
- GET    /bot-instances/stats/summary 전체 통계
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.db import get_session
from ..database.models import (
    BotInstance,
    BotType,
    Strategy,
    Trade,
)
from ..schemas.bot_instance_schema import (
    AllBotsSummaryResponse,
    BotInstanceCreate,
    BotInstanceListResponse,
    BotInstanceResponse,
    BotInstanceUpdate,
    BotStatsResponse,
    SuccessResponse,
)
from ..utils.jwt_auth import get_current_user_id
from ..utils.structured_logging import get_logger

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

router = APIRouter(prefix="/bot-instances", tags=["Bot Instances"])

# 상수 정의
MAX_BOTS_PER_USER = 10
MAX_ALLOCATION_PERCENT = 100.0


# ============================================================
# 헬퍼 함수
# ============================================================


async def get_user_allocation_sum(
    session: AsyncSession,
    user_id: int,
    exclude_bot_id: Optional[int] = None
) -> float:
    """사용자의 현재 총 할당률 계산"""
    query = select(func.coalesce(func.sum(BotInstance.allocation_percent), 0)).where(
        and_(
            BotInstance.user_id == user_id,
            BotInstance.is_active is True
        )
    )
    if exclude_bot_id:
        query = query.where(BotInstance.id != exclude_bot_id)

    result = await session.execute(query)
    return float(result.scalar() or 0)


async def get_bot_by_id(
    session: AsyncSession,
    bot_id: int,
    user_id: int
) -> BotInstance:
    """봇 조회 (소유권 확인 포함)"""
    result = await session.execute(
        select(BotInstance)
        .options(selectinload(BotInstance.strategy))
        .where(
            and_(
                BotInstance.id == bot_id,
                BotInstance.user_id == user_id,
                BotInstance.is_active is True
            )
        )
    )
    bot = result.scalars().first()
    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다")
    return bot


def bot_to_response(bot: BotInstance) -> BotInstanceResponse:
    """BotInstance ORM 모델을 API 응답 스키마로 변환합니다.

    데이터베이스에서 조회한 BotInstance ORM 객체를 클라이언트에 반환할
    BotInstanceResponse Pydantic 스키마로 변환합니다. Decimal 타입은
    float로, Enum은 문자열로 변환하고, 연관된 Strategy 정보도 포함합니다.

    Args:
        bot: BotInstance ORM 모델 인스턴스. 봇의 모든 설정과 상태 정보를
            포함합니다:
            - id, user_id, name, description: 기본 정보
            - bot_type: 봇 유형 (BotType Enum)
            - strategy_id, symbol: 전략 및 거래 심볼
            - allocation_percent, max_leverage, max_positions: 자금 설정
            - stop_loss_percent, take_profit_percent: 리스크 설정
            - telegram_notify: 알림 설정
            - is_running, is_active: 실행 상태
            - last_started_at, last_stopped_at, last_trade_at: 시간 정보
            - last_error: 마지막 에러 메시지
            - total_trades, winning_trades, total_pnl: 성과 통계
            - strategy: 연관된 Strategy 객체 (selectinload로 로드)

    Returns:
        BotInstanceResponse: API 응답용 Pydantic 스키마 객체.
            - bot_type: Enum의 value 문자열로 변환됨
            - Decimal 필드들: float로 변환됨
            - strategy_name: 연관 Strategy의 이름 (없으면 None)
    """
    return BotInstanceResponse(
        id=bot.id,
        user_id=bot.user_id,
        name=bot.name,
        description=bot.description,
        bot_type=bot.bot_type.value if isinstance(bot.bot_type, BotType) else bot.bot_type,
        strategy_id=bot.strategy_id,
        symbol=bot.symbol,
        allocation_percent=float(bot.allocation_percent),
        max_leverage=bot.max_leverage,
        max_positions=bot.max_positions,
        stop_loss_percent=float(bot.stop_loss_percent) if bot.stop_loss_percent else None,
        take_profit_percent=float(bot.take_profit_percent) if bot.take_profit_percent else None,
        telegram_notify=bot.telegram_notify,
        is_running=bot.is_running,
        is_active=bot.is_active,
        last_started_at=bot.last_started_at,
        last_stopped_at=bot.last_stopped_at,
        last_trade_at=bot.last_trade_at,
        last_error=bot.last_error,
        total_trades=bot.total_trades,
        winning_trades=bot.winning_trades,
        total_pnl=float(bot.total_pnl),
        created_at=bot.created_at,
        updated_at=bot.updated_at,
        strategy_name=bot.strategy.name if bot.strategy else None
    )


# ============================================================
# CRUD 엔드포인트
# ============================================================


@router.post("/create", response_model=SuccessResponse)
async def create_bot_instance(
    payload: BotInstanceCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    새 봇 인스턴스 생성

    - 사용자당 최대 10개 봇 제한
    - 총 할당률 100% 초과 불가
    - AI 봇의 경우 strategy_id 필수
    """
    structured_logger.info(
        "bot_instance_create_requested",
        f"Bot instance creation requested by user {user_id}",
        user_id=user_id,
        bot_name=payload.name,
        bot_type=payload.bot_type.value,
    )

    # 1. 봇 개수 제한 확인
    count_result = await session.execute(
        select(func.count(BotInstance.id)).where(
            and_(
                BotInstance.user_id == user_id,
                BotInstance.is_active is True
            )
        )
    )
    current_count = count_result.scalar() or 0

    if current_count >= MAX_BOTS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"최대 {MAX_BOTS_PER_USER}개의 봇만 생성할 수 있습니다"
        )

    # 2. 할당률 검증
    current_allocation = await get_user_allocation_sum(session, user_id)
    if current_allocation + payload.allocation_percent > MAX_ALLOCATION_PERCENT:
        available = MAX_ALLOCATION_PERCENT - current_allocation
        raise HTTPException(
            status_code=400,
            detail=f"할당 가능한 잔고가 부족합니다. 현재 사용: {current_allocation}%, 사용 가능: {available}%"
        )

    # 3. AI 봇인 경우 전략 ID 검증
    if payload.bot_type == "ai_trend" and not payload.strategy_id:
        raise HTTPException(
            status_code=400,
            detail="AI 봇은 전략 ID가 필요합니다"
        )

    if payload.strategy_id:
        # 전략 존재 확인
        strategy_result = await session.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == payload.strategy_id,
                    # 공용 전략이거나 사용자 소유
                    (Strategy.user_id is None) | (Strategy.user_id == user_id)
                )
            )
        )
        if not strategy_result.scalars().first():
            raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다")

    # 4. 봇 이름 중복 확인 (같은 사용자 내에서)
    name_check = await session.execute(
        select(BotInstance).where(
            and_(
                BotInstance.user_id == user_id,
                BotInstance.name == payload.name,
                BotInstance.is_active is True
            )
        )
    )
    if name_check.scalars().first():
        raise HTTPException(status_code=400, detail="이미 같은 이름의 봇이 존재합니다")

    # 5. 봇 생성
    bot = BotInstance(
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        bot_type=BotType(payload.bot_type.value),
        strategy_id=payload.strategy_id,
        symbol=payload.symbol,
        allocation_percent=Decimal(str(payload.allocation_percent)),
        max_leverage=payload.max_leverage,
        max_positions=payload.max_positions,
        stop_loss_percent=Decimal(str(payload.stop_loss_percent)) if payload.stop_loss_percent else None,
        take_profit_percent=Decimal(str(payload.take_profit_percent)) if payload.take_profit_percent else None,
        telegram_notify=payload.telegram_notify,
    )
    session.add(bot)
    await session.commit()
    await session.refresh(bot)

    structured_logger.info(
        "bot_instance_created",
        f"Bot instance created: {bot.id}",
        user_id=user_id,
        bot_id=bot.id,
        bot_name=bot.name,
    )

    return SuccessResponse(
        success=True,
        message=f"봇 '{bot.name}'이(가) 생성되었습니다",
        bot_id=bot.id
    )


@router.get("/list", response_model=BotInstanceListResponse)
async def list_bot_instances(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """사용자의 모든 봇 목록 조회"""
    result = await session.execute(
        select(BotInstance)
        .options(selectinload(BotInstance.strategy))
        .where(
            and_(
                BotInstance.user_id == user_id,
                BotInstance.is_active is True
            )
        )
        .order_by(BotInstance.created_at.desc())
    )
    bots = result.scalars().all()

    # 통계 계산
    total_allocation = sum(float(b.allocation_percent) for b in bots)
    running_count = sum(1 for b in bots if b.is_running)

    return BotInstanceListResponse(
        bots=[bot_to_response(b) for b in bots],
        total_allocation=total_allocation,
        available_allocation=MAX_ALLOCATION_PERCENT - total_allocation,
        running_count=running_count,
        total_count=len(bots)
    )


@router.get("/{bot_id}", response_model=BotInstanceResponse)
async def get_bot_instance(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """봇 상세 정보 조회"""
    bot = await get_bot_by_id(session, bot_id, user_id)
    return bot_to_response(bot)


@router.patch("/{bot_id}", response_model=SuccessResponse)
async def update_bot_instance(
    bot_id: int,
    payload: BotInstanceUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """봇 설정 수정 (실행 중이 아닐 때만)"""
    bot = await get_bot_by_id(session, bot_id, user_id)

    # 실행 중인 봇은 수정 불가
    if bot.is_running:
        raise HTTPException(
            status_code=400,
            detail="실행 중인 봇은 수정할 수 없습니다. 먼저 봇을 중지해주세요."
        )

    # 할당률 변경 시 검증
    if payload.allocation_percent is not None:
        current_allocation = await get_user_allocation_sum(session, user_id, exclude_bot_id=bot_id)
        if current_allocation + payload.allocation_percent > MAX_ALLOCATION_PERCENT:
            available = MAX_ALLOCATION_PERCENT - current_allocation
            raise HTTPException(
                status_code=400,
                detail=f"할당 가능한 잔고가 부족합니다. 사용 가능: {available}%"
            )

    # 이름 변경 시 중복 확인
    if payload.name and payload.name != bot.name:
        name_check = await session.execute(
            select(BotInstance).where(
                and_(
                    BotInstance.user_id == user_id,
                    BotInstance.name == payload.name,
                    BotInstance.is_active is True,
                    BotInstance.id != bot_id
                )
            )
        )
        if name_check.scalars().first():
            raise HTTPException(status_code=400, detail="이미 같은 이름의 봇이 존재합니다")

    # 필드 업데이트 (None이 아닌 값만)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if field in ['allocation_percent', 'stop_loss_percent', 'take_profit_percent']:
                value = Decimal(str(value))
            setattr(bot, field, value)

    bot.updated_at = datetime.utcnow()
    await session.commit()

    structured_logger.info(
        "bot_instance_updated",
        f"Bot instance updated: {bot_id}",
        user_id=user_id,
        bot_id=bot_id,
        updated_fields=list(update_data.keys()),
    )

    return SuccessResponse(
        success=True,
        message=f"봇 '{bot.name}' 설정이 수정되었습니다",
        bot_id=bot_id
    )


@router.delete("/{bot_id}", response_model=SuccessResponse)
async def delete_bot_instance(
    bot_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """봇 삭제 (실행 중이면 먼저 중지)"""
    bot = await get_bot_by_id(session, bot_id, user_id)

    # 실행 중이면 먼저 중지
    if bot.is_running:
        try:
            from ..workers.manager import BotManager
            manager: BotManager = request.app.state.bot_manager
            await manager.stop_bot_instance(bot_id, user_id)
        except Exception as e:
            logger.error(f"Failed to stop bot instance {bot_id} before deletion: {e}")
        bot.is_running = False
        bot.last_stopped_at = datetime.utcnow()

    # Soft delete
    bot.is_active = False
    bot.updated_at = datetime.utcnow()
    await session.commit()

    structured_logger.info(
        "bot_instance_deleted",
        f"Bot instance deleted: {bot_id}",
        user_id=user_id,
        bot_id=bot_id,
        bot_name=bot.name,
    )

    return SuccessResponse(
        success=True,
        message=f"봇 '{bot.name}'이(가) 삭제되었습니다"
    )


# ============================================================
# 실행 제어 엔드포인트
# ============================================================


@router.post("/{bot_id}/start", response_model=SuccessResponse)
async def start_bot_instance(
    bot_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """특정 봇 시작"""
    bot = await get_bot_by_id(session, bot_id, user_id)

    if bot.is_running:
        raise HTTPException(status_code=400, detail="봇이 이미 실행 중입니다")

    # AI 봇인 경우 전략 확인
    if bot.bot_type == BotType.AI_TREND and not bot.strategy_id:
        raise HTTPException(status_code=400, detail="AI 봇에 전략이 설정되지 않았습니다")

    # BotManager를 통해 봇 시작
    try:
        from ..workers.manager import BotManager
        manager: BotManager = request.app.state.bot_manager
        await manager.start_bot_instance(bot_id, user_id)
    except Exception as e:
        logger.error(f"Failed to start bot instance {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"봇 시작 실패: {str(e)}") from e

    # 상태 업데이트
    bot.is_running = True
    bot.last_started_at = datetime.utcnow()
    bot.last_error = None
    await session.commit()

    structured_logger.info(
        "bot_instance_started",
        f"Bot instance started: {bot_id}",
        user_id=user_id,
        bot_id=bot_id,
        bot_name=bot.name,
    )

    return SuccessResponse(
        success=True,
        message=f"봇 '{bot.name}'이(가) 시작되었습니다",
        bot_id=bot_id
    )


@router.post("/{bot_id}/stop", response_model=SuccessResponse)
async def stop_bot_instance(
    bot_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """특정 봇 중지"""
    bot = await get_bot_by_id(session, bot_id, user_id)

    if not bot.is_running:
        raise HTTPException(status_code=400, detail="봇이 이미 중지되어 있습니다")

    # BotManager를 통해 봇 중지
    try:
        from ..workers.manager import BotManager
        manager: BotManager = request.app.state.bot_manager
        await manager.stop_bot_instance(bot_id, user_id)
    except Exception as e:
        logger.error(f"Failed to stop bot instance {bot_id}: {e}")
        # 에러가 발생해도 DB 상태는 업데이트

    # 상태 업데이트
    bot.is_running = False
    bot.last_stopped_at = datetime.utcnow()
    await session.commit()

    structured_logger.info(
        "bot_instance_stopped",
        f"Bot instance stopped: {bot_id}",
        user_id=user_id,
        bot_id=bot_id,
        bot_name=bot.name,
    )

    return SuccessResponse(
        success=True,
        message=f"봇 '{bot.name}'이(가) 중지되었습니다",
        bot_id=bot_id
    )


@router.post("/start-all", response_model=SuccessResponse)
async def start_all_bots(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """활성화된 모든 봇 시작"""
    result = await session.execute(
        select(BotInstance).where(
            and_(
                BotInstance.user_id == user_id,
                BotInstance.is_active is True,
                BotInstance.is_running is False
            )
        )
    )
    bots = result.scalars().all()

    # 시작 가능한 봇 ID 목록 수집
    bot_ids_to_start = []
    for bot in bots:
        # AI 봇은 전략이 있어야 시작 가능
        if bot.bot_type == BotType.AI_TREND and not bot.strategy_id:
            continue
        bot_ids_to_start.append(bot.id)

    # BotManager를 통해 여러 봇 동시 시작
    started_count = 0
    if bot_ids_to_start:
        try:
            from ..workers.manager import BotManager
            manager: BotManager = request.app.state.bot_manager
            started_count, _ = await manager.start_multiple_instances(bot_ids_to_start, user_id)
        except Exception as e:
            logger.error(f"Failed to start bots: {e}")

    # DB 상태 업데이트
    for bot in bots:
        if bot.id in bot_ids_to_start:
            bot.is_running = True
            bot.last_started_at = datetime.utcnow()
            bot.last_error = None

    await session.commit()

    structured_logger.info(
        "all_bots_started",
        f"Started {started_count} bots for user {user_id}",
        user_id=user_id,
        started_count=started_count,
    )

    return SuccessResponse(
        success=True,
        message=f"{started_count}개의 봇이 시작되었습니다"
    )


@router.post("/stop-all", response_model=SuccessResponse)
async def stop_all_bots(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """모든 봇 중지"""
    result = await session.execute(
        select(BotInstance).where(
            and_(
                BotInstance.user_id == user_id,
                BotInstance.is_active is True,
                BotInstance.is_running is True
            )
        )
    )
    bots = result.scalars().all()

    # BotManager를 통해 모든 봇 중지
    try:
        from ..workers.manager import BotManager
        manager: BotManager = request.app.state.bot_manager
        await manager.stop_all_user_instances(user_id)
    except Exception as e:
        logger.error(f"Failed to stop all bots: {e}")

    # DB 상태 업데이트
    stopped_count = 0
    for bot in bots:
        bot.is_running = False
        bot.last_stopped_at = datetime.utcnow()
        stopped_count += 1

    await session.commit()

    structured_logger.info(
        "all_bots_stopped",
        f"Stopped {stopped_count} bots for user {user_id}",
        user_id=user_id,
        stopped_count=stopped_count,
    )

    return SuccessResponse(
        success=True,
        message=f"{stopped_count}개의 봇이 중지되었습니다"
    )


# ============================================================
# 통계 엔드포인트
# ============================================================


@router.get("/{bot_id}/stats", response_model=BotStatsResponse)
async def get_bot_stats(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """봇별 상세 통계"""
    bot = await get_bot_by_id(session, bot_id, user_id)

    # 거래 통계 조회
    trades_result = await session.execute(
        select(Trade).where(Trade.bot_instance_id == bot_id)
    )
    trades = trades_result.scalars().all()

    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t.pnl and float(t.pnl) > 0)
    losing_trades = total_trades - winning_trades
    total_pnl = sum(float(t.pnl or 0) for t in trades)
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

    pnls = [float(t.pnl or 0) for t in trades]
    max_profit = max(pnls) if pnls else 0
    max_loss = min(pnls) if pnls else 0

    # 실행 시간 계산 (대략적)
    running_hours = 0
    if bot.last_started_at:
        end_time = bot.last_stopped_at or datetime.utcnow()
        if bot.is_running:
            end_time = datetime.utcnow()
        running_hours = (end_time - bot.last_started_at).total_seconds() / 3600

    return BotStatsResponse(
        bot_id=bot.id,
        bot_name=bot.name,
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=(winning_trades / total_trades * 100) if total_trades > 0 else 0,
        total_pnl=total_pnl,
        avg_pnl=avg_pnl,
        max_profit=max_profit,
        max_loss=max_loss,
        running_time_hours=round(running_hours, 2)
    )


@router.get("/stats/summary", response_model=AllBotsSummaryResponse)
async def get_all_bots_summary(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전체 봇 통계 요약"""
    # 활성 봇 목록 조회
    result = await session.execute(
        select(BotInstance).where(
            and_(
                BotInstance.user_id == user_id,
                BotInstance.is_active is True
            )
        )
    )
    bots = result.scalars().all()

    total_bots = len(bots)
    running_bots = sum(1 for b in bots if b.is_running)
    total_allocation = sum(float(b.allocation_percent) for b in bots)
    total_pnl = sum(float(b.total_pnl) for b in bots)
    total_trades = sum(b.total_trades for b in bots)

    # 승률 계산
    total_winning = sum(b.winning_trades for b in bots)
    overall_win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0

    # 최고/최저 성과 봇
    best_bot = max(bots, key=lambda b: float(b.total_pnl), default=None)
    worst_bot = min(bots, key=lambda b: float(b.total_pnl), default=None)

    return AllBotsSummaryResponse(
        total_bots=total_bots,
        running_bots=running_bots,
        total_allocation=total_allocation,
        total_pnl=total_pnl,
        total_trades=total_trades,
        overall_win_rate=round(overall_win_rate, 2),
        best_performing_bot=best_bot.name if best_bot else None,
        worst_performing_bot=worst_bot.name if worst_bot else None
    )
