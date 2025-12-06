from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import BotStatus, Strategy
from ..schemas.strategy_schema import StrategyCreate, StrategySelect, StrategyUpdate
from ..utils.jwt_auth import get_current_user_id

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.post("/create")
async def create_strategy(
    payload: StrategyCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 생성 (JWT 인증 필요, 관리자 전용 - 공용 전략 생성)"""
    import json

    # Frontend에서 parameters로 보낸 경우 params로 변환
    params_str = payload.params
    if payload.parameters and not params_str:
        params_str = json.dumps(payload.parameters)

    # user_id를 NULL로 설정하여 공용 전략 생성 (관리자가 만든 전략)
    strategy = Strategy(
        user_id=None,  # NULL = 관리자가 만든 공용 전략
        name=payload.name,
        description=payload.description or "",
        code=payload.code or "",  # 기본값 설정
        params=params_str,
    )
    session.add(strategy)
    await session.commit()
    await session.refresh(strategy)
    return strategy


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
        .where(Strategy.user_id == None)  # 공용 전략만 수정 가능
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
        .where(Strategy.user_id == None)
        .where(Strategy.is_active == True)
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
        .where(Strategy.user_id == None)  # 공용 전략만 조회
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
        .where(Strategy.user_id == None)  # 공용 전략만 삭제 가능
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
    result = await session.execute(
        select(Strategy).where(Strategy.id == strategy_id)
    )
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
