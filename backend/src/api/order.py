import logging
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import PaginationConfig
from ..database.db import get_session
from ..database.models import Equity, Position, RiskSettings, Trade
from ..schemas.order_schema import OrderResponse, OrderSubmit
from ..services.trade_executor import ensure_client
from ..utils.jwt_auth import get_current_user_id

router = APIRouter(prefix="/order", tags=["order"])
logger = logging.getLogger(__name__)


# ============================================================
# 🔒 보안: 주문 서버 측 검증 (Server-Side Order Validation)
# ============================================================


async def validate_order_request(
    session: AsyncSession,
    user_id: int,
    symbol: str,
    qty: float,
    leverage: int,
    client=None,
) -> Tuple[bool, Optional[str]]:
    """
    주문 요청 서버 측 검증

    검증 항목:
    1. 레버리지가 사용자 max_leverage 이하인지
    2. 현재 포지션 수가 max_positions 미만인지
    3. 주문 금액이 잔고의 합리적 범위 내인지 (선택적)

    Returns:
        Tuple[bool, Optional[str]]: (검증 통과 여부, 실패 시 에러 메시지)
    """
    try:
        # 사용자 리스크 설정 조회
        risk_result = await session.execute(
            select(RiskSettings).where(RiskSettings.user_id == user_id)
        )
        risk_settings = risk_result.scalars().first()

        # 리스크 설정이 없으면 기본값 사용
        max_leverage = 10 if not risk_settings else risk_settings.max_leverage
        max_positions = 5 if not risk_settings else risk_settings.max_positions

        # 1. 레버리지 검증
        if leverage > max_leverage:
            # 🔒 SECURITY AUDIT: 레버리지 제한 초과 시도
            logger.warning(
                f"🔒 SECURITY AUDIT: User {user_id} attempted to use leverage {leverage}x "
                f"(max allowed: {max_leverage}x) for {symbol}"
            )
            return (
                False,
                f"레버리지가 최대 허용값({max_leverage}배)을 초과합니다. 요청: {leverage}배",
            )

        # 2. 현재 포지션 수 검증
        position_count_result = await session.execute(
            select(func.count())
            .select_from(Position)
            .where(Position.user_id == user_id)
        )
        current_positions = position_count_result.scalar() or 0

        if current_positions >= max_positions:
            # 🔒 SECURITY AUDIT: 최대 포지션 수 초과 시도
            logger.warning(
                f"🔒 SECURITY AUDIT: User {user_id} attempted to exceed max positions "
                f"(current: {current_positions}, max: {max_positions}) for {symbol}"
            )
            return (
                False,
                f"최대 포지션 수({max_positions}개)에 도달했습니다. 현재: {current_positions}개",
            )

        # 3. 주문 수량 검증 (기본 검증)
        if qty <= 0:
            return False, "주문 수량은 0보다 커야 합니다"

        if qty > 1000000:  # 최대 주문 수량 제한
            return False, "주문 수량이 너무 큽니다 (최대: 1,000,000)"

        # 4. 잔고 기반 검증 (선택적 - client가 제공된 경우)
        if client:
            try:
                balance_info = await client.get_futures_balance()
                available_balance = float(balance_info.get("available", 0))

                # 레버리지 적용한 최대 허용 금액 계산
                # 예: 잔고 1000 USDT, 레버리지 10x → 최대 10000 USDT 포지션 가능
                # max_order_value = available_balance * leverage (참고용)

                # 현재 시장 가격으로 주문 금액 추정 (symbol 기반)
                # 참고: 정확한 계산을 위해서는 시장 가격 조회 필요
                # 여기서는 기본적인 수량 제한만 적용
                if qty * leverage > available_balance * 10:  # 안전 마진 적용
                    logger.warning(
                        f"[OrderValidation] Large order detected: user={user_id}, qty={qty}, leverage={leverage}, balance={available_balance}"
                    )
                    return False, "주문 금액이 가용 잔고 대비 너무 큽니다"

            except Exception as e:
                # 잔고 조회 실패 시 경고만 로그하고 계속 진행
                logger.warning(f"[OrderValidation] Balance check failed: {e}")

        logger.info(
            f"[OrderValidation] Passed: user={user_id}, symbol={symbol}, qty={qty}, leverage={leverage}"
        )
        return True, None

    except Exception as e:
        logger.error(f"[OrderValidation] Critical validation error: {e}", exc_info=True)
        # 🔒 SECURITY FIX: 검증 로직 에러 시 주문을 거부하여 안전성 우선
        # 시스템 오류 시 위험한 주문이 실행되는 것을 방지
        return False, "주문 검증 실패: 시스템 오류가 발생했습니다. 잠시 후 다시 시도해주세요."


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
    result = await session.execute(select(Position).where(Position.user_id == user_id))
    return result.scalars().all()


@router.get("/history")
async def order_history(
    limit: int = Query(
        default=PaginationConfig.TRADES_DEFAULT_LIMIT,
        ge=1,
        le=PaginationConfig.TRADES_MAX_LIMIT,
        description=f"페이지 크기 (최대 {PaginationConfig.TRADES_MAX_LIMIT})",
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
                "price": float(trade.entry_price),  # For dashboard compatibility
                "timestamp": int(trade.created_at.timestamp() * 1000),  # Milliseconds for JavaScript
                "pnl": float(trade.pnl_percent) if trade.pnl_percent is not None else 0.0,  # Numeric value
                "pnl_text": f"{float(trade.pnl_percent):+.2f}%" if trade.pnl_percent is not None else "0.00%",
                "time": trade.created_at.isoformat(),
                "status": "Closed" if trade.exit_price else "Open",
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
        },
    }


@router.get("/equity_history")
async def equity_history(
    limit: int = Query(
        default=PaginationConfig.EQUITY_DEFAULT_LIMIT,
        ge=1,
        le=PaginationConfig.EQUITY_MAX_LIMIT,
        description=f"페이지 크기 (최대 {PaginationConfig.EQUITY_MAX_LIMIT})",
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
        },
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
        logger.info(
            f"[Order] User {user_id} submitting {payload.side} order for {payload.symbol}"
        )

        # 🔒 서버 측 주문 검증 (레버리지, 포지션 수, 잔고)
        is_valid, error_message = await validate_order_request(
            session=session,
            user_id=user_id,
            symbol=payload.symbol,
            qty=payload.qty,
            leverage=payload.leverage,
            client=client,
        )

        if not is_valid:
            logger.warning(
                f"[Order] Validation failed for user {user_id}: {error_message}"
            )
            return OrderResponse(
                order_id="validation_failed",
                status="rejected",
                symbol=payload.symbol,
                side=payload.side,
                qty=payload.qty,
                price=None,
            )

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
            leverage=payload.leverage,
        )

        logger.info(f"[Order] Order executed: {order_result}")

        # 주문 결과 반환
        return OrderResponse(
            order_id=str(order_result.get("orderId", "unknown")),
            status="filled",
            symbol=payload.symbol,
            side=payload.side,
            qty=payload.qty,
            price=float(order_result.get("price", 0))
            if order_result.get("price")
            else None,
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
                Position.id == payload.position_id, Position.user_id == user_id
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
        close_side = "sell" if payload.side.lower() in ["long", "buy"] else "buy"
        qty = float(position.size)

        logger.info(
            f"[ClosePosition] User {user_id} closing position {position.id}: {close_side} {qty} {payload.symbol}"
        )

        # 거래소 클라이언트 생성
        client = await ensure_client(user_id, session, validate=True)

        # 청산 주문 실행 (반대 방향 시장가)
        order_result = await place_market_order(
            client=client,
            symbol=payload.symbol,
            side=close_side,
            qty=qty,
            leverage=1,  # 청산 시에는 레버리지 불필요
        )

        logger.info(f"[ClosePosition] Position closed: {order_result}")

        # 포지션 삭제 또는 상태 업데이트
        await session.delete(position)
        await session.commit()

        return OrderResponse(
            order_id=str(order_result.get("orderId", "unknown")),
            status="filled",
            symbol=payload.symbol,
            side=close_side,
            qty=qty,
            price=float(order_result.get("price", 0))
            if order_result.get("price")
            else None,
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
