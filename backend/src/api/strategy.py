from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json

from ..database.db import get_session
from ..database.models import BotStatus, Strategy
from ..schemas.strategy_schema import StrategyCreate, StrategySelect, StrategyUpdate
from ..utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post("/create")
async def create_strategy(
    payload: StrategyCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 생성 (JWT 인증 필요, 현재 사용자의 전략으로 저장)"""
    logger.info(f"[Strategy Create] User {user_id} creating strategy: {payload.name}")

    try:
        # Frontend에서 parameters로 보낸 경우 params로 변환
        params_str = payload.params
        if payload.parameters and not params_str:
            # type, symbol, timeframe도 params에 포함
            params_dict = payload.parameters.copy()
            if payload.type:
                params_dict["type"] = payload.type
            if payload.symbol:
                params_dict["symbol"] = payload.symbol
            if payload.timeframe:
                params_dict["timeframe"] = payload.timeframe
            params_str = json.dumps(params_dict)
            logger.debug(
                f"[Strategy Create] Converted parameters to params: {params_str}"
            )

        # 현재 로그인한 사용자의 전략으로 저장
        strategy = Strategy(
            user_id=user_id,  # 현재 사용자 ID 저장
            name=payload.name,
            description=payload.description or "",
            code=payload.code or None,  # code가 없으면 None (nullable)
            params=params_str,
            is_active=False,  # 기본적으로 비활성화
        )
        session.add(strategy)
        await session.commit()
        await session.refresh(strategy)

        logger.info(
            f"[Strategy Create] Successfully created strategy ID {strategy.id} for user {user_id}"
        )

        return {
            "success": True,
            "message": "전략이 생성되었습니다.",
            "strategy": {
                "id": strategy.id,
                "name": strategy.name,
                "description": strategy.description,
            },
        }
    except Exception as e:
        logger.error(
            f"[Strategy Create] Error creating strategy for user {user_id}: {str(e)}"
        )
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"전략 생성 실패: {str(e)}")


@router.post("/update/{strategy_id}")
async def update_strategy(
    strategy_id: int,
    payload: StrategyUpdate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 수정 (JWT 인증 필요, 관리자 전용 - 공용 전략 수정)"""
    result = await session.execute(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .where(Strategy.user_id.is_(None))  # 공용 전략만 수정 가능
    )
    strategy = result.scalars().first()

    if not strategy:
        raise HTTPException(
            status_code=404, detail="Strategy not found or access denied"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(strategy, field, value)

    await session.commit()
    await session.refresh(strategy)
    return strategy


@router.get("/list")
async def list_strategies(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 목록 조회 (JWT 인증 필요, 관리자가 만든 공용 전략만)"""
    # user_id가 NULL이고 is_active = True인 전략만 반환
    result = await session.execute(
        select(Strategy)
        .where(Strategy.user_id.is_(None))
        .where(Strategy.is_active.is_(True))
    )
    return result.scalars().all()


@router.post("/select")
async def select_strategy(
    payload: StrategySelect,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 선택 (JWT 인증 필요)"""

    result = await session.execute(
        select(BotStatus).where(BotStatus.user_id == user_id)
    )
    status = result.scalars().first()

    if not status:
        status = BotStatus(
            user_id=user_id, strategy_id=payload.strategy_id, is_running=False
        )
        session.add(status)
    else:
        status.strategy_id = payload.strategy_id

    await session.commit()
    return {"ok": True, "message": "Strategy selected successfully"}


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 상세 조회 (JWT 인증 필요, 공용 전략 조회)"""
    result = await session.execute(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .where(Strategy.user_id.is_(None))  # 공용 전략만 조회
    )
    strategy = result.scalars().first()

    if not strategy:
        raise HTTPException(
            status_code=404, detail="Strategy not found or access denied"
        )

    return strategy


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 삭제 (JWT 인증 필요, 관리자 전용 - 공용 전략 삭제)"""
    result = await session.execute(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .where(Strategy.user_id.is_(None))  # 공용 전략만 삭제 가능
    )
    strategy = result.scalars().first()

    if not strategy:
        raise HTTPException(
            status_code=404, detail="Strategy not found or access denied"
        )

    await session.delete(strategy)
    await session.commit()

    return {"ok": True, "message": "Strategy deleted successfully"}


@router.patch("/{strategy_id}/toggle")
async def toggle_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 활성화/비활성화 토글 (JWT 인증 필요)"""
    result = await session.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalars().first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 활성화 상태 토글
    strategy.is_active = not strategy.is_active
    await session.commit()
    await session.refresh(strategy)

    return {
        "ok": True,
        "message": f"Strategy {'activated' if strategy.is_active else 'deactivated'} successfully",
        "is_active": strategy.is_active,
    }
