from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json

from ..database.db import get_session
from ..database.models import BotStatus, Strategy
from ..schemas.strategy_schema import StrategyCreate, StrategySelect, StrategyUpdate
from ..utils.jwt_auth import get_current_user_id
from ..utils.auth_dependencies import require_admin

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

        # 전략 코드 결정 (code가 없으면 type 기반으로 자동 매핑)
        strategy_code = payload.code
        if not strategy_code and payload.type:
            # type을 code로 매핑 (프론트엔드 호환성)
            type_to_code_map = {
                # 3가지 대표 전략 (검증된 전략)
                "proven_conservative": "proven_conservative",
                "proven_balanced": "proven_balanced",
                "proven_aggressive": "proven_aggressive",
                # AI 전략
                "autonomous_30pct": "autonomous_30pct",
                "adaptive_market_regime_fighter": "adaptive_market_regime_fighter",
                # 레거시 매핑 (호환성 유지)
                "golden_cross": "ma_cross",  # 골든크로스 → MA 크로스 전략
                "rsi_reversal": "rsi_strategy",  # RSI 반전 → RSI 전략
                "trend_following": "ema",  # 추세추종 → EMA 전략
                "breakout": "breakout",  # 돌파 → 돌파 전략
                "aggressive": "ultra_aggressive",  # 공격적 → 울트라 공격적 전략
                "ultra_aggressive": "ultra_aggressive",
                "ma_cross": "ma_cross",
            }
            strategy_code = type_to_code_map.get(payload.type, payload.type)
            logger.info(
                f"[Strategy Create] Auto-mapped type '{payload.type}' to code '{strategy_code}'"
            )

        # 현재 로그인한 사용자의 전략으로 저장
        strategy = Strategy(
            user_id=user_id,  # 현재 사용자 ID 저장
            name=payload.name,
            description=payload.description or "",
            code=strategy_code,  # 매핑된 전략 코드 저장
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
    admin_id: int = Depends(require_admin),
):
    """전략 수정 (JWT 인증 필요, 관리자 전용 - 공용 전략 수정)"""
    result = await session.execute(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .where(Strategy.user_id.is_(None))  # 공용 전략만 수정 가능
    )
    strategy = result.scalars().first()

    if not strategy:
        # 🔒 SECURITY AUDIT: 존재하지 않는 전략 수정 시도
        logger.warning(
            f"🔒 SECURITY AUDIT: Admin {admin_id} attempted to update non-existent or unauthorized strategy {strategy_id}"
        )
        raise HTTPException(
            status_code=404, detail="Strategy not found or access denied"
        )

    # 🔒 SECURITY AUDIT: 전략 수정 기록
    logger.info(
        f"🔒 SECURITY AUDIT: Admin {admin_id} updating strategy {strategy_id} (name: {strategy.name}). "
        f"Changes: {payload.model_dump(exclude_unset=True)}"
    )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(strategy, field, value)

    await session.commit()
    await session.refresh(strategy)

    logger.info(f"✅ SECURITY AUDIT: Admin {admin_id} successfully updated strategy {strategy_id}")
    return strategy


@router.get("/list")
async def list_strategies(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """전략 목록 조회 (JWT 인증 필요)

    반환하는 전략:
    1. 공용 전략 (user_id=NULL, is_active=True)
    2. 현재 사용자가 생성한 전략 (user_id=현재사용자)
    """
    from sqlalchemy import or_

    # 공용 전략 (is_active=True) + 현재 사용자의 전략 모두 반환
    result = await session.execute(
        select(Strategy).where(
            or_(
                # 공용 전략 (관리자가 만든 활성화된 전략)
                (Strategy.user_id.is_(None)) & (Strategy.is_active.is_(True)),
                # 현재 사용자가 직접 만든 전략 (활성화 여부 무관)
                Strategy.user_id == user_id,
            )
        )
    )
    strategies = result.scalars().all()
    logger.info(f"[Strategy List] User {user_id}: Found {len(strategies)} strategies")
    return strategies


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
    """전략 상세 조회 (JWT 인증 필요)

    조회 가능한 전략:
    1. 공용 전략 (user_id=NULL)
    2. 현재 사용자가 생성한 전략
    """
    from sqlalchemy import or_

    result = await session.execute(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .where(
            or_(
                Strategy.user_id.is_(None),  # 공용 전략
                Strategy.user_id == user_id,  # 본인 전략
            )
        )
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
    admin_id: int = Depends(require_admin),
):
    """전략 삭제 (JWT 인증 필요, 관리자 전용 - 공용 전략 삭제)"""
    result = await session.execute(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .where(Strategy.user_id.is_(None))  # 공용 전략만 삭제 가능
    )
    strategy = result.scalars().first()

    if not strategy:
        # 🔒 SECURITY AUDIT: 존재하지 않는 전략 삭제 시도
        logger.warning(
            f"🔒 SECURITY AUDIT: Admin {admin_id} attempted to delete non-existent or unauthorized strategy {strategy_id}"
        )
        raise HTTPException(
            status_code=404, detail="Strategy not found or access denied"
        )

    # 🔒 SECURITY AUDIT: 전략 삭제 전 기록 (복구 가능하도록)
    strategy_info = {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "code": strategy.code,
    }
    logger.warning(
        f"🔒 SECURITY AUDIT: Admin {admin_id} deleting strategy {strategy_id}. "
        f"Strategy info: {strategy_info}"
    )

    await session.delete(strategy)
    await session.commit()

    logger.info(f"✅ SECURITY AUDIT: Admin {admin_id} successfully deleted strategy {strategy_id}")
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
