"""
Bitget 시장 데이터 API
실시간 가격, 호가, 거래 정보 제공
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import ApiKey
from ..schemas.market_schema import (
    CancelOrderRequest,
    ClosePositionRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    SetLeverageRequest,
)
from ..services.bitget_rest import BitgetRestClient, get_bitget_rest
from ..utils.crypto_secrets import decrypt_secret
from ..utils.jwt_auth import get_current_user_id
from ..utils.structured_logging import get_logger

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)


router = APIRouter(prefix="/bitget", tags=["bitget", "market"])


async def get_user_bitget_client(
    user_id: int, session: AsyncSession
) -> BitgetRestClient:
    """
    사용자의 Bitget 클라이언트 반환

    Args:
        user_id: 사용자 ID
        session: DB 세션

    Returns:
        BitgetRestClient 인스턴스

    Raises:
        HTTPException: API 키 관련 에러
    """
    # API 키 조회
    from sqlalchemy import select

    result = await session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
    api_key_obj = result.scalars().first()

    if not api_key_obj:
        raise HTTPException(
            status_code=404,
            detail="API 키가 설정되지 않았습니다. Settings 페이지에서 API 키를 등록해주세요.",
        )

    # API 키 복호화
    try:
        api_key = decrypt_secret(api_key_obj.encrypted_api_key)
        api_secret = (
            decrypt_secret(api_key_obj.encrypted_secret_key)
            if api_key_obj.encrypted_secret_key
            else ""
        )
        passphrase = (
            decrypt_secret(api_key_obj.encrypted_passphrase)
            if api_key_obj.encrypted_passphrase
            else ""
        )
    except Exception as e:
        logger.error(f"Failed to decrypt API keys: {e}")
        raise HTTPException(
            status_code=500,
            detail="API 키 복호화에 실패했습니다. Settings에서 API 키를 다시 등록해주세요.",
        ) from e

    if not all([api_key, api_secret, passphrase]):
        raise HTTPException(
            status_code=400,
            detail="API 인증 정보가 불완전합니다. 모든 필드를 입력해주세요.",
        )

    return get_bitget_rest(api_key, api_secret, passphrase)


@router.get("/ticker/{symbol}")
async def get_ticker(
    symbol: str,
    _user_id: int = Depends(get_current_user_id),  # Required for auth but not used
):
    """
    현재가 조회 (Public CCXT API 사용)

    Args:
        symbol: 거래쌍 (예: BTCUSDT)

    Returns:
        현재가 정보
    """
    try:
        # Use public CCXT API without authentication
        from decimal import Decimal

        import ccxt.async_support as ccxt

        exchange = ccxt.bitget()
        ticker = await exchange.fetch_ticker(symbol)
        await exchange.close()

        return {
            "symbol": ticker["symbol"],
            "last": Decimal(str(ticker.get("last", 0))),
            "bid": Decimal(str(ticker.get("bid", 0))),
            "ask": Decimal(str(ticker.get("ask", 0))),
            "high": Decimal(str(ticker.get("high", 0))),
            "low": Decimal(str(ticker.get("low", 0))),
            "volume": Decimal(str(ticker.get("volume", 0))),
            "timestamp": ticker.get("timestamp", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting ticker {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"현재가 조회 중 예상치 못한 에러가 발생했습니다: {str(e)}",
        ) from e


@router.get("/orderbook/{symbol}")
async def get_orderbook(
    symbol: str,
    limit: int = 20,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    호가 조회

    Args:
        symbol: 거래쌍
        limit: 호가 개수 (최대 100)

    Returns:
        호가 정보 (매수/매도)
    """
    try:
        client = await get_user_bitget_client(user_id, session)
        orderbook = await client.get_orderbook(symbol, min(limit, 100))
        return orderbook

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get orderbook: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get orderbook: {str(e)}"
        ) from e


@router.get("/positions")
async def get_positions(
    symbol: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    포지션 조회

    Args:
        symbol: 거래쌍 (선택사항, 없으면 전체 조회)

    Returns:
        포지션 리스트
    """
    from ..utils.cache_manager import cache_manager, make_cache_key

    # 캐시 키 생성 (심볼이 있으면 포함)
    cache_suffix = f"positions:{symbol}" if symbol else "positions"
    cache_key = make_cache_key(cache_suffix, user_id)

    # 캐시 확인 (3초 TTL - 포지션은 빠르게 변할 수 있음)
    cached_data = await cache_manager.get(cache_key)
    if cached_data is not None:
        return cached_data

    try:
        client = await get_user_bitget_client(user_id, session)
        positions = await client.get_positions(symbol=symbol)
        response = {"positions": positions}

        # 캐시 저장
        await cache_manager.set(cache_key, response, ttl=3)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get positions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get positions: {str(e)}"
        ) from e


@router.get("/account")
async def get_account(
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    계좌 정보 조회

    Returns:
        계좌 잔고 및 마진 정보 (USDT 선물 계좌)
    """
    from ..utils.cache_manager import cache_manager, make_cache_key

    # 캐시 확인 (5초 TTL)
    cache_key = make_cache_key("bitget_account", user_id)
    cached_data = await cache_manager.get(cache_key)
    if cached_data is not None:
        return cached_data

    try:
        client = await get_user_bitget_client(user_id, session)
        account_data = await client.get_account_info()

        # Bitget API returns a list of accounts (one per margin coin)
        # Extract the USDT account for futures trading
        response_data = None
        if isinstance(account_data, list):
            usdt_account = None
            for account in account_data:
                if account.get("marginCoin", "").upper() == "USDT":
                    usdt_account = account
                    break

            if not usdt_account and len(account_data) > 0:
                # Fallback to first account if no USDT found
                usdt_account = account_data[0]

            if usdt_account:
                response_data = {
                    "marginCoin": usdt_account.get("marginCoin", "USDT"),
                    "available": usdt_account.get("available", "0"),
                    "frozen": usdt_account.get("frozen", "0"),
                    "locked": usdt_account.get("locked", "0"),
                    "equity": usdt_account.get("equity", "0"),
                    "usdtEquity": usdt_account.get("usdtEquity", "0"),
                    "unrealizedPL": usdt_account.get("unrealizedPL", "0"),
                    "bonus": usdt_account.get("bonus", "0"),
                    "crossedUnrealizedPL": usdt_account.get("crossedUnrealizedPL", "0"),
                    "isolatedUnrealizedPL": usdt_account.get(
                        "isolatedUnrealizedPL", "0"
                    ),
                }
            else:
                raise HTTPException(status_code=404, detail="No account data found")
        else:
            # If it's already a dict (unlikely but handle it)
            response_data = account_data

        # 캐시 저장
        if response_data:
            await cache_manager.set(cache_key, response_data, ttl=5)

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get account: {str(e)}") from e


@router.get("/orders/open")
async def get_open_orders(
    symbol: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    미체결 주문 조회

    Args:
        symbol: 거래쌍 (선택사항)

    Returns:
        미체결 주문 리스트
    """
    try:
        client = await get_user_bitget_client(user_id, session)
        orders = await client.get_open_orders(symbol=symbol)
        return {"orders": orders}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get open orders: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get open orders: {str(e)}"
        ) from e


@router.post("/orders/market")
async def place_market_order(
    payload: MarketOrderRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    시장가 주문 실행

    Args:
        payload: 시장가 주문 요청 (symbol, side, size, reduce_only)

    Returns:
        주문 응답
    """
    try:
        from ..services.bitget_rest import OrderSide

        client = await get_user_bitget_client(user_id, session)

        order_side = OrderSide.BUY if payload.side.lower() == "buy" else OrderSide.SELL

        structured_logger.info(
            "market_order_requested",
            f"Market order requested: {payload.symbol} {payload.side} {payload.size}",
            user_id=user_id,
            symbol=payload.symbol,
            side=payload.side,
            size=payload.size,
            reduce_only=payload.reduce_only,
        )

        result = await client.place_market_order(
            symbol=payload.symbol,
            side=order_side,
            size=payload.size,
            reduce_only=payload.reduce_only,
        )

        structured_logger.info(
            "market_order_placed",
            f"Market order placed successfully: {payload.symbol} {payload.side} {payload.size}",
            user_id=user_id,
            symbol=payload.symbol,
            side=payload.side,
            size=payload.size,
            order_id=result.get("orderId") if isinstance(result, dict) else None,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic validation error
        structured_logger.warning(
            "market_order_validation_error",
            "Market order validation failed",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        structured_logger.error(
            "market_order_failed",
            "Failed to place market order",
            user_id=user_id,
            symbol=payload.symbol,
            side=payload.side,
            size=payload.size,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}") from e


@router.post("/orders/limit")
async def place_limit_order(
    payload: LimitOrderRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    지정가 주문 실행

    Args:
        payload: 지정가 주문 요청 (symbol, side, size, price, reduce_only)

    Returns:
        주문 응답
    """
    try:
        from ..services.bitget_rest import OrderSide

        client = await get_user_bitget_client(user_id, session)

        order_side = OrderSide.BUY if payload.side.lower() == "buy" else OrderSide.SELL

        structured_logger.info(
            "limit_order_requested",
            f"Limit order requested: {payload.symbol} {payload.side} {payload.size} @ {payload.price}",
            user_id=user_id,
            symbol=payload.symbol,
            side=payload.side,
            size=payload.size,
            price=payload.price,
            reduce_only=payload.reduce_only,
        )

        result = await client.place_limit_order(
            symbol=payload.symbol,
            side=order_side,
            size=payload.size,
            price=payload.price,
            reduce_only=payload.reduce_only,
        )

        structured_logger.info(
            "limit_order_placed",
            f"Limit order placed successfully: {payload.symbol} {payload.side} {payload.size} @ {payload.price}",
            user_id=user_id,
            symbol=payload.symbol,
            side=payload.side,
            size=payload.size,
            price=payload.price,
            order_id=result.get("orderId") if isinstance(result, dict) else None,
        )

        return result

    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic validation error
        structured_logger.warning(
            "limit_order_validation_error",
            "Limit order validation failed",
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        structured_logger.error(
            "limit_order_failed",
            "Failed to place limit order",
            user_id=user_id,
            symbol=payload.symbol,
            side=payload.side,
            size=payload.size,
            price=payload.price,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}") from e


@router.post("/orders/cancel")
async def cancel_order(
    payload: CancelOrderRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    주문 취소

    Args:
        payload: 취소 요청 (order_id, symbol)

    Returns:
        취소 응답
    """
    try:
        client = await get_user_bitget_client(user_id, session)
        result = await client.cancel_order(payload.symbol, payload.order_id)

        logger.info(f"Order cancelled: {payload.order_id}")
        return result

    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic validation error
        logger.error(f"Validation error in cancel order: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to cancel order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}") from e


@router.post("/positions/close")
async def close_position(
    payload: ClosePositionRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    포지션 청산

    Args:
        payload: 청산 요청 (symbol, side, size)

    Returns:
        청산 응답
    """
    try:
        from ..services.bitget_rest import PositionSide

        client = await get_user_bitget_client(user_id, session)

        position_side = (
            PositionSide.LONG if payload.side.lower() == "long" else PositionSide.SHORT
        )

        result = await client.close_position(
            payload.symbol, position_side, payload.size
        )

        logger.info(f"Position closed: {payload.symbol} {payload.side}")
        return result

    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic validation error
        logger.error(f"Validation error in close position: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to close position: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to close position: {str(e)}"
        ) from e


@router.post("/leverage")
async def set_leverage(
    payload: SetLeverageRequest,
    user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    레버리지 설정

    Args:
        payload: 레버리지 설정 요청 (symbol, leverage)

    Returns:
        설정 응답
    """
    try:
        client = await get_user_bitget_client(user_id, session)
        result = await client.set_leverage(payload.symbol, payload.leverage)

        logger.info(f"Leverage set: {payload.symbol} {payload.leverage}x")
        return result

    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic validation error
        logger.error(f"Validation error in set leverage: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Failed to set leverage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set leverage: {str(e)}") from e
