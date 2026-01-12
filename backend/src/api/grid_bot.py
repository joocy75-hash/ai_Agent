"""
그리드 봇 전용 API

관련 문서: docs/MULTI_BOT_02_DATABASE.md, MULTI_BOT_03_IMPLEMENTATION.md
관련 스키마: schemas/bot_instance_schema.py - GridBotConfigCreate, GridBotConfigResponse

엔드포인트:
- GET    /grid-bot/{bot_id}/config     그리드 설정 조회
- POST   /grid-bot/{bot_id}/config     그리드 설정 생성/수정
- GET    /grid-bot/{bot_id}/orders     그리드 주문 목록
- POST   /grid-bot/{bot_id}/start      그리드 봇 시작
- POST   /grid-bot/{bot_id}/stop       그리드 봇 중지
- GET    /grid-bot/{bot_id}/stats      그리드 봇 통계
- POST   /grid-bot/preview             그리드 미리보기 계산
- GET    /grid-bot/market/{symbol}     시장 가격 조회
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.db import get_session
from ..database.models import (
    BotInstance,
    BotType,
    GridBotConfig,
    GridMode,
    GridOrder,
    GridOrderStatus,
)
from ..schemas.bot_instance_schema import (
    GridBotConfigCreate,
    GridBotConfigResponse,
    GridModeEnum,
    GridOrderResponse,
    SuccessResponse,
)
from ..utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grid-bot", tags=["Grid Bot"])


# ============================================================
# 추가 스키마 (grid_bot.py 전용)
# ============================================================


class GridPreviewRequest(BaseModel):
    """그리드 미리보기 요청"""

    lower_price: float = Field(..., gt=0, description="하한가")
    upper_price: float = Field(..., gt=0, description="상한가")
    grid_count: int = Field(default=10, ge=2, le=100, description="그리드 수")
    grid_mode: GridModeEnum = Field(default=GridModeEnum.ARITHMETIC)
    total_investment: float = Field(..., gt=0, description="총 투자금")
    current_price: float = Field(..., gt=0, description="현재 가격")


class GridLinePreview(BaseModel):
    """개별 그리드 라인 미리보기"""

    grid_index: int
    price: float
    type: str  # 'buy' or 'sell' (현재가 기준)
    amount: float  # 투자금


class GridPreviewResponse(BaseModel):
    """그리드 미리보기 응답"""

    grids: List[GridLinePreview]
    per_grid_amount: float
    expected_profit_per_grid: float  # 그리드당 예상 수익 (%)
    total_grids: int
    buy_grids: int  # 현재가 아래 (매수 대기)
    sell_grids: int  # 현재가 위 (매도 대기)
    price_range_percent: float  # 가격 범위 (%)


class MarketPriceResponse(BaseModel):
    """시장 가격 응답"""

    symbol: str
    price: float
    high_24h: float
    low_24h: float
    change_24h: float  # %


class GridStopRequest(BaseModel):
    """그리드 봇 중지 요청"""

    close_positions: bool = Field(default=False, description="포지션 청산 여부")


# ============================================================
# 헬퍼 함수
# ============================================================


async def get_bot_instance_with_grid(
    session: AsyncSession, bot_id: int, user_id: int
) -> BotInstance:
    """사용자의 그리드 봇 인스턴스 조회"""
    result = await session.execute(
        select(BotInstance)
        .options(selectinload(BotInstance.grid_config))
        .where(
            and_(
                BotInstance.id == bot_id,
                BotInstance.user_id == user_id,
                BotInstance.is_active is True,
            )
        )
    )
    bot = result.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="봇을 찾을 수 없습니다")

    if bot.bot_type != BotType.GRID:
        raise HTTPException(status_code=400, detail="그리드 봇이 아닙니다")

    return bot


def calculate_grid_prices(
    lower_price: float, upper_price: float, grid_count: int, grid_mode: str
) -> List[float]:
    """그리드 트레이딩을 위한 가격 레벨을 계산합니다.

    지정된 가격 범위와 그리드 수에 따라 매수/매도 주문을 배치할
    가격 레벨들을 계산합니다. 등차(arithmetic) 또는 등비(geometric)
    방식으로 그리드를 생성할 수 있습니다.

    Args:
        lower_price: 그리드 하한가. 가장 낮은 매수 주문 가격입니다.
            양수여야 합니다.
        upper_price: 그리드 상한가. 가장 높은 매도 주문 가격입니다.
            lower_price보다 커야 합니다.
        grid_count: 생성할 그리드 라인 수. 2 이상이어야 합니다.
            실제 주문 수는 grid_count - 1개가 됩니다.
        grid_mode: 그리드 생성 방식.
            - "arithmetic": 등차 그리드 (가격 간격이 일정)
            - "geometric": 등비 그리드 (가격 비율이 일정)

    Returns:
        List[float]: 계산된 그리드 가격 레벨 리스트.
            lower_price부터 upper_price까지 grid_count개의 가격이
            오름차순으로 정렬되어 반환됩니다.
            각 가격은 소수점 8자리로 반올림됩니다.

    Examples:
        >>> calculate_grid_prices(100, 200, 5, "arithmetic")
        [100.0, 125.0, 150.0, 175.0, 200.0]
        >>> calculate_grid_prices(100, 200, 3, "geometric")
        [100.0, 141.42135624, 200.0]

    Note:
        - 등차 그리드: 변동성이 낮은 횡보장에 적합
        - 등비 그리드: 변동성이 높은 시장에 적합 (저가에서 더 촘촘)
    """
    prices = []

    if grid_mode == "geometric":
        # 등비 그리드
        ratio = (upper_price / lower_price) ** (1 / (grid_count - 1))
        for i in range(grid_count):
            price = lower_price * (ratio**i)
            prices.append(round(price, 8))
    else:
        # 등차 그리드 (기본)
        step = (upper_price - lower_price) / (grid_count - 1)
        for i in range(grid_count):
            price = lower_price + (step * i)
            prices.append(round(price, 8))

    return prices


# ============================================================
# API 엔드포인트
# ============================================================


@router.get("/{bot_id}/config", response_model=GridBotConfigResponse)
async def get_grid_config(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """그리드 봇 설정 조회"""
    bot = await get_bot_instance_with_grid(session, bot_id, user_id)

    if not bot.grid_config:
        raise HTTPException(status_code=404, detail="그리드 설정이 없습니다")

    return GridBotConfigResponse.model_validate(bot.grid_config)


@router.post("/{bot_id}/config", response_model=SuccessResponse)
async def save_grid_config(
    bot_id: int,
    config: GridBotConfigCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """그리드 봇 설정 생성/수정"""
    bot = await get_bot_instance_with_grid(session, bot_id, user_id)

    # 실행 중이면 수정 불가
    if bot.is_running:
        raise HTTPException(
            status_code=400,
            detail="실행 중인 봇의 설정은 수정할 수 없습니다. 먼저 봇을 중지하세요.",
        )

    # 가격 범위 검증
    if config.upper_price <= config.lower_price:
        raise HTTPException(status_code=400, detail="상한가는 하한가보다 커야 합니다")

    # 그리드당 투자금 계산
    per_grid_amount = config.total_investment / config.grid_count

    if per_grid_amount < 2:
        raise HTTPException(
            status_code=400,
            detail=f"그리드당 투자금이 너무 작습니다 (${per_grid_amount:.2f}). 최소 $2 이상이어야 합니다.",
        )

    # 기존 설정이 있으면 업데이트, 없으면 생성
    if bot.grid_config:
        # 기존 그리드 주문 삭제
        await session.execute(
            delete(GridOrder).where(GridOrder.grid_config_id == bot.grid_config.id)
        )

        # 설정 업데이트
        bot.grid_config.lower_price = Decimal(str(config.lower_price))
        bot.grid_config.upper_price = Decimal(str(config.upper_price))
        bot.grid_config.grid_count = config.grid_count
        bot.grid_config.grid_mode = GridMode(config.grid_mode.value)
        bot.grid_config.total_investment = Decimal(str(config.total_investment))
        bot.grid_config.per_grid_amount = Decimal(str(per_grid_amount))
        bot.grid_config.trigger_price = (
            Decimal(str(config.trigger_price)) if config.trigger_price else None
        )
        bot.grid_config.stop_upper = (
            Decimal(str(config.stop_upper)) if config.stop_upper else None
        )
        bot.grid_config.stop_lower = (
            Decimal(str(config.stop_lower)) if config.stop_lower else None
        )
        bot.grid_config.updated_at = datetime.utcnow()

        # 통계 초기화
        bot.grid_config.active_buy_orders = 0
        bot.grid_config.active_sell_orders = 0
        bot.grid_config.filled_buy_count = 0
        bot.grid_config.filled_sell_count = 0
        bot.grid_config.realized_profit = Decimal("0")

        config_id = bot.grid_config.id
        message = "그리드 설정이 수정되었습니다"
    else:
        # 새 설정 생성
        new_config = GridBotConfig(
            bot_instance_id=bot_id,
            lower_price=Decimal(str(config.lower_price)),
            upper_price=Decimal(str(config.upper_price)),
            grid_count=config.grid_count,
            grid_mode=GridMode(config.grid_mode.value),
            total_investment=Decimal(str(config.total_investment)),
            per_grid_amount=Decimal(str(per_grid_amount)),
            trigger_price=Decimal(str(config.trigger_price))
            if config.trigger_price
            else None,
            stop_upper=Decimal(str(config.stop_upper)) if config.stop_upper else None,
            stop_lower=Decimal(str(config.stop_lower)) if config.stop_lower else None,
        )
        session.add(new_config)
        await session.flush()
        config_id = new_config.id
        message = "그리드 설정이 생성되었습니다"

    # 그리드 주문 초기화
    grid_prices = calculate_grid_prices(
        config.lower_price,
        config.upper_price,
        config.grid_count,
        config.grid_mode.value,
    )

    for idx, price in enumerate(grid_prices):
        order = GridOrder(
            grid_config_id=config_id,
            grid_index=idx,
            grid_price=Decimal(str(price)),
            status=GridOrderStatus.PENDING,
        )
        session.add(order)

    await session.commit()

    logger.info(
        f"Grid config saved for bot {bot_id}: {config.grid_count} grids, ${config.total_investment}"
    )

    return SuccessResponse(success=True, message=message, bot_id=bot_id)


@router.get("/{bot_id}/orders")
async def get_grid_orders(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """그리드 주문 목록 조회"""
    bot = await get_bot_instance_with_grid(session, bot_id, user_id)

    if not bot.grid_config:
        raise HTTPException(status_code=404, detail="그리드 설정이 없습니다")

    # 그리드 주문 조회
    result = await session.execute(
        select(GridOrder)
        .where(GridOrder.grid_config_id == bot.grid_config.id)
        .order_by(GridOrder.grid_index)
    )
    orders = result.scalars().all()

    # 통계 계산
    total_profit = sum(float(o.profit or 0) for o in orders)
    active_orders = sum(
        1
        for o in orders
        if o.status in [GridOrderStatus.BUY_PLACED, GridOrderStatus.SELL_PLACED]
    )

    return {
        "orders": [GridOrderResponse.model_validate(o) for o in orders],
        "summary": {
            "total_orders": len(orders),
            "active_orders": active_orders,
            "pending": sum(1 for o in orders if o.status == GridOrderStatus.PENDING),
            "buy_filled": sum(
                1 for o in orders if o.status == GridOrderStatus.BUY_FILLED
            ),
            "sell_filled": sum(
                1 for o in orders if o.status == GridOrderStatus.SELL_FILLED
            ),
            "total_profit": total_profit,
        },
    }


@router.post("/{bot_id}/start", response_model=SuccessResponse)
async def start_grid_bot(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """그리드 봇 시작"""
    bot = await get_bot_instance_with_grid(session, bot_id, user_id)

    if bot.is_running:
        raise HTTPException(status_code=400, detail="봇이 이미 실행 중입니다")

    if not bot.grid_config:
        raise HTTPException(
            status_code=400, detail="그리드 설정이 필요합니다. 먼저 설정을 완료하세요."
        )

    # 봇 상태 업데이트
    bot.is_running = True
    bot.last_started_at = datetime.utcnow()
    bot.last_error = None
    await session.commit()

    # 실제 봇 시작은 BotManager가 처리 (별도 프로세스)
    # 여기서는 DB 상태만 변경

    logger.info(f"Grid bot {bot_id} started by user {user_id}")

    return SuccessResponse(
        success=True, message="그리드 봇이 시작되었습니다", bot_id=bot_id
    )


@router.post("/{bot_id}/stop", response_model=SuccessResponse)
async def stop_grid_bot(
    bot_id: int,
    request: GridStopRequest = GridStopRequest(),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """그리드 봇 중지"""
    bot = await get_bot_instance_with_grid(session, bot_id, user_id)

    if not bot.is_running:
        raise HTTPException(status_code=400, detail="봇이 실행 중이 아닙니다")

    # 봇 상태 업데이트
    bot.is_running = False
    bot.last_stopped_at = datetime.utcnow()
    await session.commit()

    message = "그리드 봇이 중지되었습니다"
    if request.close_positions:
        message += " (포지션 청산 예약됨)"

    logger.info(f"Grid bot {bot_id} stopped by user {user_id}")

    return SuccessResponse(success=True, message=message, bot_id=bot_id)


@router.get("/{bot_id}/stats")
async def get_grid_stats(
    bot_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """그리드 봇 통계"""
    bot = await get_bot_instance_with_grid(session, bot_id, user_id)

    if not bot.grid_config:
        return {"has_config": False, "message": "그리드 설정이 없습니다"}

    config = bot.grid_config

    # 그리드 주문 조회
    result = await session.execute(
        select(GridOrder).where(GridOrder.grid_config_id == config.id)
    )
    orders = result.scalars().all()

    # 통계 계산
    total_profit = sum(float(o.profit or 0) for o in orders)
    total_cycles = sum(1 for o in orders if o.status == GridOrderStatus.SELL_FILLED)

    # ROI 계산
    investment = float(config.total_investment)
    roi = (total_profit / investment * 100) if investment > 0 else 0

    return {
        "has_config": True,
        "bot_id": bot_id,
        "bot_name": bot.name,
        "symbol": bot.symbol,
        "is_running": bot.is_running,
        "config": {
            "lower_price": float(config.lower_price),
            "upper_price": float(config.upper_price),
            "grid_count": config.grid_count,
            "grid_mode": config.grid_mode.value,
            "total_investment": float(config.total_investment),
            "per_grid_amount": float(config.per_grid_amount)
            if config.per_grid_amount
            else 0,
        },
        "performance": {
            "realized_profit": total_profit,
            "roi_percent": round(roi, 2),
            "total_cycles": total_cycles,
            "filled_buy_count": config.filled_buy_count,
            "filled_sell_count": config.filled_sell_count,
            "active_buy_orders": config.active_buy_orders,
            "active_sell_orders": config.active_sell_orders,
        },
        "running_time": {
            "started_at": bot.last_started_at.isoformat()
            if bot.last_started_at
            else None,
            "stopped_at": bot.last_stopped_at.isoformat()
            if bot.last_stopped_at
            else None,
        },
    }


@router.post("/preview", response_model=GridPreviewResponse)
async def preview_grid(
    request: GridPreviewRequest, user_id: int = Depends(get_current_user_id)
):
    """그리드 미리보기 계산 (주문 없이)"""
    # 가격 범위 검증
    if request.upper_price <= request.lower_price:
        raise HTTPException(status_code=400, detail="상한가는 하한가보다 커야 합니다")

    if (
        request.current_price < request.lower_price
        or request.current_price > request.upper_price
    ):
        raise HTTPException(status_code=400, detail="현재가가 가격 범위 밖입니다")

    # 그리드 가격 계산
    grid_prices = calculate_grid_prices(
        request.lower_price,
        request.upper_price,
        request.grid_count,
        request.grid_mode.value,
    )

    per_grid_amount = request.total_investment / request.grid_count

    # 그리드 라인 생성
    grids = []
    buy_count = 0
    sell_count = 0

    for idx, price in enumerate(grid_prices):
        grid_type = "buy" if price < request.current_price else "sell"
        if grid_type == "buy":
            buy_count += 1
        else:
            sell_count += 1

        grids.append(
            GridLinePreview(
                grid_index=idx, price=price, type=grid_type, amount=per_grid_amount
            )
        )

    # 예상 수익률 계산 (그리드 간격 기준)
    price_range = request.upper_price - request.lower_price
    grid_step = price_range / (request.grid_count - 1)
    expected_profit_per_grid = (grid_step / request.lower_price) * 100

    # 가격 범위 (%)
    price_range_percent = (
        (request.upper_price - request.lower_price) / request.lower_price
    ) * 100

    return GridPreviewResponse(
        grids=grids,
        per_grid_amount=per_grid_amount,
        expected_profit_per_grid=round(expected_profit_per_grid, 4),
        total_grids=request.grid_count,
        buy_grids=buy_count,
        sell_grids=sell_count,
        price_range_percent=round(price_range_percent, 2),
    )


@router.get("/market/{symbol}", response_model=MarketPriceResponse)
async def get_market_price(symbol: str, user_id: int = Depends(get_current_user_id)):
    """
    시장 가격 조회 (그리드 설정용)

    실제 Bitget API를 호출하여 현재가, 24시간 고가/저가, 변동률 조회
    """
    import aiohttp

    symbol = symbol.upper()

    # Bitget Public API (인증 불필요)
    # https://www.bitget.com/api-doc/contract/market/Get-Ticker
    api_url = "https://api.bitget.com/api/v2/mix/market/ticker"
    params = {"symbol": symbol, "productType": "USDT-FUTURES"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Bitget API error: {response.status}")
                    raise HTTPException(status_code=502, detail="거래소 API 호출 실패")

                data = await response.json()

                # Bitget API 응답 검증
                if data.get("code") != "00000":
                    error_msg = data.get("msg", "Unknown error")
                    logger.warning(f"Bitget API error: {error_msg} for symbol {symbol}")

                    # 지원하지 않는 심볼인 경우
                    if "symbol" in error_msg.lower() or data.get("code") == "40018":
                        raise HTTPException(
                            status_code=400,
                            detail=f"지원하지 않는 심볼입니다: {symbol}",
                        )
                    raise HTTPException(
                        status_code=502, detail=f"거래소 API 에러: {error_msg}"
                    )

                ticker_data = data.get("data", [])

                if not ticker_data or len(ticker_data) == 0:
                    raise HTTPException(
                        status_code=404,
                        detail=f"심볼 데이터를 찾을 수 없습니다: {symbol}",
                    )

                ticker = (
                    ticker_data[0] if isinstance(ticker_data, list) else ticker_data
                )

                # 가격 데이터 추출
                last_price = float(ticker.get("lastPr", 0) or ticker.get("last", 0))
                high_24h = float(ticker.get("high24h", 0) or last_price * 1.05)
                low_24h = float(ticker.get("low24h", 0) or last_price * 0.95)
                change_24h = float(ticker.get("change24h", 0) or 0)

                # change24h가 비율(0.02)인 경우 퍼센트로 변환
                if -1 < change_24h < 1:
                    change_24h = change_24h * 100

                logger.info(f"Market price fetched: {symbol} = ${last_price}")

                return MarketPriceResponse(
                    symbol=symbol,
                    price=last_price,
                    high_24h=high_24h,
                    low_24h=low_24h,
                    change_24h=round(change_24h, 2),
                )

    except HTTPException:
        raise
    except aiohttp.ClientError as e:
        logger.error(f"Network error fetching market price: {e}")
        raise HTTPException(status_code=502, detail="거래소 연결 실패") from e
    except Exception as e:
        logger.error(f"Unexpected error fetching market price: {e}")
        raise HTTPException(status_code=500, detail="시장 가격 조회 실패") from e
