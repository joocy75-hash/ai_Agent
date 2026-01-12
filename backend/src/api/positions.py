import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..services.exchange_service import ExchangeService
from ..utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/positions", tags=["positions"])


class PositionInfo(BaseModel):
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    leverage: int


class UnrealizedPnLResponse(BaseModel):
    unrealized_pnl: float
    unrealized_pnl_percent: float
    position_count: int
    total_position_value: float
    positions: List[PositionInfo]
    updated_at: datetime


@router.get("/unrealized-pnl", response_model=UnrealizedPnLResponse)
async def get_unrealized_pnl(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """미실현 손익 조회 (JWT 인증 필요)"""
    try:
        client, exchange_name = await ExchangeService.get_user_exchange_client(
            session, user_id
        )

        # Bitget API로 현재 포지션 조회
        positions_data = await client.fetch_positions()

        total_unrealized_pnl = 0.0
        total_position_value = 0.0
        positions = []

        for pos in positions_data:
            if pos.get("contracts", 0) == 0:
                continue  # 포지션이 없으면 스킵

            symbol = pos.get("symbol", "")
            side = pos.get("side", "long").upper()
            size = float(pos.get("contracts", 0))
            entry_price = float(pos.get("entryPrice", 0))
            current_price = float(pos.get("markPrice", entry_price))
            unrealized_pnl = float(pos.get("unrealizedPnl", 0))

            # 포지션 가치 계산
            position_value = size * current_price
            total_position_value += position_value
            total_unrealized_pnl += unrealized_pnl

            # 수익률 계산
            if position_value > 0:
                pnl_percent = (unrealized_pnl / position_value) * 100
            else:
                pnl_percent = 0.0

            positions.append(
                PositionInfo(
                    symbol=symbol,
                    side=side,
                    size=size,
                    entry_price=entry_price,
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_percent=pnl_percent,
                    leverage=int(pos.get("leverage", 1)),
                )
            )

        # 전체 수익률 계산
        if total_position_value > 0:
            total_pnl_percent = (total_unrealized_pnl / total_position_value) * 100
        else:
            total_pnl_percent = 0.0

        return UnrealizedPnLResponse(
            unrealized_pnl=total_unrealized_pnl,
            unrealized_pnl_percent=total_pnl_percent,
            position_count=len(positions),
            total_position_value=total_position_value,
            positions=positions,
            updated_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"[get_unrealized_pnl] Error: {e}", exc_info=True)
        # 에러 시 빈 데이터 반환 (프론트엔드가 계속 작동하도록)
        return UnrealizedPnLResponse(
            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
            position_count=0,
            total_position_value=0.0,
            positions=[],
            updated_at=datetime.utcnow(),
        )


@router.get("/list", response_model=List[PositionInfo])
async def get_positions(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """현재 포지션 목록 조회 (JWT 인증 필요)"""
    try:
        client, exchange_name = await ExchangeService.get_user_exchange_client(
            session, user_id
        )
        positions_data = await client.fetch_positions()

        positions = []
        for pos in positions_data:
            if pos.get("contracts", 0) == 0:
                continue

            symbol = pos.get("symbol", "")
            side = pos.get("side", "long").upper()
            size = float(pos.get("contracts", 0))
            entry_price = float(pos.get("entryPrice", 0))
            current_price = float(pos.get("markPrice", entry_price))
            unrealized_pnl = float(pos.get("unrealizedPnl", 0))

            position_value = size * current_price
            if position_value > 0:
                pnl_percent = (unrealized_pnl / position_value) * 100
            else:
                pnl_percent = 0.0

            positions.append(
                PositionInfo(
                    symbol=symbol,
                    side=side,
                    size=size,
                    entry_price=entry_price,
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_percent=pnl_percent,
                    leverage=int(pos.get("leverage", 1)),
                )
            )

        return positions

    except Exception as e:
        logger.error(f"[get_positions] Error: {e}", exc_info=True)
        return []
