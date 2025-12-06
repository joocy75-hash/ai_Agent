from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..config import PaginationConfig
from ..database.db import get_session
from ..database.models import Equity, Position, Trade
from ..schemas.order_schema import OrderResponse, OrderSubmit
from ..services.trade_executor import ensure_client
from ..utils.jwt_auth import get_current_user_id

router = APIRouter(prefix="/order", tags=["order"])


class ClosePositionRequest(BaseModel):
    position_id: int
    symbol: str
    side: str  # 현재 포지션 방향 (반대로 주문)


@router.get("/open")
async def open_orders(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """미체결 주문 조회 (JWT 인증 필요, 자신의 주문만)"""
    result = await session.execute(
        select(Position).where(Position.user_id == user_id)
    )
    return result.scalars().all()


@router.get("/history")
async def order_history(
    limit: int = Query(
        default=PaginationConfig.TRADES_DEFAULT_LIMIT,
        ge=1,
        le=PaginationConfig.TRADES_MAX_LIMIT,
        description=f"페이지 크기 (최대 {PaginationConfig.TRADES_MAX_LIMIT})"
    ),
    offset: int = Query(default=0, ge=0, description="시작 위치"),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    거래 내역 조회 (JWT 인증 필요, 자신의 거래만)

    페이지네이션 지원:
    - limit: 한 페이지에 가져올 개수 (기본 50, 최대 500)
    - offset: 건너뛸 개수 (페이지 계산: offset = (page - 1) * limit)
    """
    # 전체 개수 조회
    count_result = await session.execute(
        select(func.count()).select_from(Trade).where(Trade.user_id == user_id)
    )
    total_count = count_result.scalar()

    # 거래 내역 조회 (페이지네이션)
    result = await session.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    trades = result.scalars().all()

    return {
        "trades": [
            {
                "id": trade.id,
                "pair": trade.symbol,
                "symbol": trade.symbol,
                "side": trade.side,
                "size": str(trade.qty),
                "entry": float(trade.entry_price),
                "exit": float(trade.exit_price) if trade.exit_price else None,
                "pnl": f"{float(trade.pnl):+.2f}%",
                "time": trade.created_at.isoformat(),
                "status": "Closed",
            }
            for trade in trades
        ],
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
            "current_page": offset // limit + 1,
            "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
        }
    }


@router.get("/equity_history")
async def equity_history(
    limit: int = Query(
        default=PaginationConfig.EQUITY_DEFAULT_LIMIT,
        ge=1,
        le=PaginationConfig.EQUITY_MAX_LIMIT,
        description=f"페이지 크기 (최대 {PaginationConfig.EQUITY_MAX_LIMIT})"
    ),
    offset: int = Query(default=0, ge=0, description="시작 위치"),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    자산 변화 내역 조회 (JWT 인증 필요, 자신의 자산만)

    페이지네이션 지원:
    - limit: 한 페이지에 가져올 개수 (기본 100, 최대 1000)
    - offset: 건너뛸 개수
    """
    # 전체 개수 조회
    count_result = await session.execute(
        select(func.count()).select_from(Equity).where(Equity.user_id == user_id)
    )
    total_count = count_result.scalar()

    # 자산 내역 조회 (페이지네이션)
    result = await session.execute(
        select(Equity)
        .where(Equity.user_id == user_id)
        .order_by(Equity.timestamp)
        .limit(limit)
        .offset(offset)
    )
    equities = result.scalars().all()

    return {
        "data": [
            {"time": equity.timestamp.isoformat(), "value": float(equity.value)}
            for equity in equities
        ],
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
            "current_page": offset // limit + 1,
            "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
        }
    }


@router.post("/submit", response_model=OrderResponse)
async def submit_order(
    payload: OrderSubmit,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    주문 제출 (JWT 인증 필요)

    Args:
        payload: 주문 정보
            - symbol: 거래 심볼 (예: BTCUSDT)
            - side: buy/sell/long/short
            - leverage: 레버리지 (1-125)
            - qty: 수량
            - price_type: market/limit
            - limit_price: 지정가 (limit 주문 시 필수)

    Returns:
        OrderResponse: 주문 결과
    """
    import logging
    from ..services.trade_executor import place_market_order

    logger = logging.getLogger(__name__)

    try:
        # 거래소 클라이언트 생성 (API 키 검증 포함)
        client = await ensure_client(user_id, session, validate=True)
        logger.info(f"[Order] User {user_id} submitting {payload.side} order for {payload.symbol}")

        # 현재는 시장가 주문만 지원
        if payload.price_type != "market":
            return OrderResponse(
                order_id="error",
                status="rejected",
                symbol=payload.symbol,
                side=payload.side,
                qty=payload.qty,
                price=payload.limit_price,
            )

        # 시장가 주문 실행
        order_result = await place_market_order(
            client=client,
            symbol=payload.symbol,
            side=payload.side,
            qty=payload.qty,
            leverage=payload.leverage
        )

        logger.info(f"[Order] Order executed: {order_result}")

        # 주문 결과 반환
        return OrderResponse(
            order_id=str(order_result.get('orderId', 'unknown')),
            status="filled",
            symbol=payload.symbol,
            side=payload.side,
            qty=payload.qty,
            price=float(order_result.get('price', 0)) if order_result.get('price') else None,
        )

    except Exception as e:
        logger.error(f"[Order] Order submission failed: {e}", exc_info=True)
        return OrderResponse(
            order_id="error",
            status="error",
            symbol=payload.symbol,
            side=payload.side,
            qty=payload.qty,
            price=None,
        )


@router.post("/close_position", response_model=OrderResponse)
async def close_position(
    payload: ClosePositionRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    포지션 청산 (JWT 인증 필요)

    Args:
        payload: 청산할 포지션 정보
            - position_id: 포지션 ID
            - symbol: 거래 심볼
            - side: 현재 포지션 방향 (long/short)

    Returns:
        OrderResponse: 청산 주문 결과
    """
    import logging
    from ..services.trade_executor import place_market_order

    logger = logging.getLogger(__name__)

    try:
        # 포지션 조회
        result = await session.execute(
            select(Position).where(
                Position.id == payload.position_id,
                Position.user_id == user_id
            )
        )
        position = result.scalars().first()

        if not position:
            return OrderResponse(
                order_id="error",
                status="rejected",
                symbol=payload.symbol,
                side="close",
                qty=0,
                price=None,
            )

        # 반대 방향 주문 (청산)
        close_side = "sell" if payload.side.lower() in ['long', 'buy'] else "buy"
        qty = float(position.size)

        logger.info(f"[ClosePosition] User {user_id} closing position {position.id}: {close_side} {qty} {payload.symbol}")

        # 거래소 클라이언트 생성
        client = await ensure_client(user_id, session, validate=True)

        # 청산 주문 실행 (반대 방향 시장가)
        order_result = await place_market_order(
            client=client,
            symbol=payload.symbol,
            side=close_side,
            qty=qty,
            leverage=1  # 청산 시에는 레버리지 불필요
        )

        logger.info(f"[ClosePosition] Position closed: {order_result}")

        # 포지션 삭제 또는 상태 업데이트
        await session.delete(position)
        await session.commit()

        return OrderResponse(
            order_id=str(order_result.get('orderId', 'unknown')),
            status="filled",
            symbol=payload.symbol,
            side=close_side,
            qty=qty,
            price=float(order_result.get('price', 0)) if order_result.get('price') else None,
        )

    except Exception as e:
        logger.error(f"[ClosePosition] Failed to close position: {e}", exc_info=True)
        return OrderResponse(
            order_id="error",
            status="error",
            symbol=payload.symbol,
            side="close",
            qty=0,
            price=None,
        )
