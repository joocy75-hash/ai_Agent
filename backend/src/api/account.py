import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import ApiKey, RiskSettings, User
from ..middleware.rate_limit_improved import api_key_reveal_limiter
from ..schemas.account_schema import (
    ApiKeyPayload,
    RiskSettingsRequest,
    RiskSettingsResponse,
)
from ..services.exchange_service import ExchangeService
from ..utils.crypto_secrets import decrypt_secret, encrypt_secret
from ..utils.jwt_auth import get_current_user_id
from ..utils.structured_logging import get_logger

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/balance")
async def balance(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """계정 잔고 조회 (JWT 인증 필요)"""
    from ..utils.cache_manager import cache_manager, make_cache_key

    # API 키 확인
    if not await ExchangeService.has_api_key(session, user_id):
        raise HTTPException(
            status_code=400,
            detail="API keys not configured. Please add your exchange API keys in Settings."
        )

    # 캐시 확인 (10초 TTL - 잔고는 자주 변경될 수 있음)
    cache_key = make_cache_key("balance", user_id)
    cached_balance = await cache_manager.get(cache_key)
    if cached_balance is not None:
        logger.debug(f"Cache hit for balance user {user_id}")
        return cached_balance

    try:
        # 거래소 클라이언트 가져오기 (서비스 레이어 사용)
        client, exchange_name = await ExchangeService.get_user_exchange_client(
            session, user_id
        )

        # 선물 잔고 조회
        balance_data = await client.get_futures_balance()

        total = float(balance_data.get("total", 0))
        free = float(balance_data.get("free", 0))
        used = float(balance_data.get("used", 0))
        unrealized_pnl = float(balance_data.get("unrealized_pnl", 0))

        logger.info(
            f"선물 잔고 - Total: {total}, Free: {free}, Used: {used}, PNL: {unrealized_pnl}"
        )

        response = {
            "result": "true",
            "info": {
                "freeze": [{"asset": "usdt", "amount": str(used), "type": "freeze"}],
                "free": [{"asset": "usdt", "amount": str(free), "type": "free"}],
                "asset": [{"asset": "usdt", "amount": str(total), "type": "total"}],
            },
            "futures": {
                "total": str(total),
                "free": str(free),
                "used": str(used),
                "unrealized_pnl": str(unrealized_pnl),
            },
            "exchange": exchange_name,
        }

        # 캐시에 저장 (10초 TTL)
        await cache_manager.set(cache_key, response, ttl=10)
        logger.debug(f"Cached balance for user {user_id}")

        return response
    except HTTPException:
        # ExchangeService에서 발생한 HTTPException은 그대로 전달
        raise
    except Exception as e:
        logger.error(f"Error fetching balance: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch balance from exchange: {str(e)}"
        ) from e


@router.get("/positions")
async def positions(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """포지션 조회 (JWT 인증 필요)"""
    from ..utils.cache_manager import cache_manager, make_cache_key

    # API 키 확인
    if not await ExchangeService.has_api_key(session, user_id):
        raise HTTPException(
            status_code=400,
            detail="API keys not configured. Please add your exchange API keys in Settings."
        )

    # 캐시 확인 (5초 TTL - 포지션은 자주 변경될 수 있음)
    cache_key = make_cache_key("positions", user_id)
    cached_positions = await cache_manager.get(cache_key)
    if cached_positions is not None:
        logger.debug(f"Cache hit for positions user {user_id}")
        return cached_positions

    try:
        # 거래소 클라이언트 가져오기 (서비스 레이어 사용)
        client, exchange_name = await ExchangeService.get_user_exchange_client(
            session, user_id
        )

        positions_data = await client.get_positions()

        logger.info(f"포지션 조회 성공: {len(positions_data)}개")

        response = {"result": "true", "data": positions_data, "exchange": exchange_name}

        # 캐시에 저장 (5초 TTL)
        await cache_manager.set(cache_key, response, ttl=5)
        logger.debug(f"Cached positions for user {user_id}")

        return response
    except HTTPException:
        # ExchangeService에서 발생한 HTTPException은 그대로 전달
        raise
    except Exception as e:
        logger.error(f"Error fetching positions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch positions from exchange: {str(e)}"
        ) from e


@router.post("/save_keys")
async def save_keys(
    payload: ApiKeyPayload,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """API 키 저장 (JWT 인증 필요, 자신의 키만 저장 가능)"""
    try:
        structured_logger.info(
            "api_keys_save_requested",
            "API keys save requested",
            user_id=user_id,
            exchange=payload.exchange
        )

        # Passphrase 검증 (Bitget, OKX는 필수)
        if payload.exchange in ApiKeyPayload.PASSPHRASE_REQUIRED:
            if not payload.passphrase:
                raise ValueError(f"{payload.exchange.upper()} requires a passphrase")

        # API 키 암호화
        encrypted_api = encrypt_secret(payload.api_key)
        encrypted_secret = encrypt_secret(payload.secret_key)
        encrypted_passphrase = encrypt_secret(payload.passphrase or "")

        logger.debug(f"[save_keys] API keys encrypted successfully for {payload.exchange}")

        # User.exchange 필드 업데이트
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalars().first()
        if user:
            user.exchange = payload.exchange
            logger.info(f"[save_keys] Updated user exchange to {payload.exchange}")

        # DB 저장 또는 업데이트
        result = await session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
        key = result.scalars().first()

        if not key:
            logger.info(f"[save_keys] Creating new API key for user {user_id} ({payload.exchange})")
            key = ApiKey(
                user_id=user_id,
                encrypted_api_key=encrypted_api,
                encrypted_secret_key=encrypted_secret,
                encrypted_passphrase=encrypted_passphrase,
            )
            session.add(key)
        else:
            logger.info(f"[save_keys] Updating existing API key for user {user_id} ({payload.exchange})")
            key.encrypted_api_key = encrypted_api
            key.encrypted_secret_key = encrypted_secret
            key.encrypted_passphrase = encrypted_passphrase

        await session.commit()

        structured_logger.info(
            "api_keys_saved",
            "API keys saved successfully",
            user_id=user_id
        )

        # 캐시 무효화 (API 키가 변경되어 잔고/포지션 정보가 달라질 수 있음)
        from ..utils.cache_manager import cache_manager, make_cache_key
        await cache_manager.delete(make_cache_key("balance", user_id))
        await cache_manager.delete(make_cache_key("positions", user_id))
        await cache_manager.delete(make_cache_key("bot_status", user_id))
        logger.debug(f"Invalidated caches for user {user_id} after API key save")

        return {"ok": True, "message": "API keys saved successfully"}

    except ValueError as e:
        # Validation error
        structured_logger.warning(
            "api_keys_save_validation_error",
            "API keys save validation error",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # Unexpected error
        structured_logger.error(
            "api_keys_save_failed",
            "Failed to save API keys",
            user_id=user_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500, detail="Failed to save API keys. Please try again."
        ) from e


@router.get("/my_keys")
async def get_my_keys(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    자신의 API 키 조회 (JWT 인증 필요, 복호화하여 반환)

    **Rate Limit**: 시간당 3회 제한 (보안상의 이유)
    """
    # Rate Limit 체크 (시간당 3회)
    api_key_reveal_limiter.check(user_id)

    result = await session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
    key = result.scalars().first()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    # 사용자의 거래소 정보 조회
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    exchange = user.exchange if user else "bitget"

    # 보안 로그 (CRITICAL: 보안 감사를 위한 로깅)
    structured_logger.warning(
        "api_keys_revealed",
        "API keys revealed - security audit event",
        user_id=user_id,
        endpoint="/account/my_keys",
        exchange=exchange
    )

    return {
        "api_key": decrypt_secret(key.encrypted_api_key),
        "secret_key": decrypt_secret(key.encrypted_secret_key),
        "passphrase": decrypt_secret(key.encrypted_passphrase)
        if key.encrypted_passphrase
        else "",
        "exchange": exchange,
        "warning": "이 정보는 안전한 곳에 저장하세요. API 키 조회는 시간당 3회로 제한됩니다.",
    }


@router.get("/risk-settings", response_model=RiskSettingsResponse)
async def get_risk_settings(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
) -> RiskSettingsResponse:
    """
    사용자 리스크 설정 조회

    Returns:
        RiskSettingsResponse: 리스크 설정 정보
    """
    from ..utils.cache_manager import cache_manager, make_cache_key

    # 캐시 확인 (60초 TTL - 리스크 설정은 자주 변경되지 않음)
    cache_key = make_cache_key("risk_settings", user_id)
    cached_settings = await cache_manager.get(cache_key)
    if cached_settings is not None:
        logger.debug(f"Cache hit for risk_settings user {user_id}")
        return RiskSettingsResponse(**cached_settings)

    try:
        result = await session.execute(
            select(RiskSettings).where(RiskSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            # 기본 설정 반환
            logger.info(f"[get_risk_settings] Returning default settings for user {user_id}")
            response_data = {
                "daily_loss_limit": 500.0,
                "max_leverage": 10,
                "max_positions": 5,
                "is_default": True,
                "updated_at": None,
            }
        else:
            logger.info(f"[get_risk_settings] Retrieved settings for user {user_id}")
            response_data = {
                "daily_loss_limit": settings.daily_loss_limit,
                "max_leverage": settings.max_leverage,
                "max_positions": settings.max_positions,
                "is_default": False,
                "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
            }

        # 캐시에 저장 (60초 TTL)
        await cache_manager.set(cache_key, response_data, ttl=60)
        logger.debug(f"Cached risk_settings for user {user_id}")

        return RiskSettingsResponse(**response_data)

    except Exception as e:
        logger.error(f"[get_risk_settings] Error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="리스크 설정 조회에 실패했습니다."
        ) from e


@router.post("/risk-settings")
async def save_risk_settings(
    payload: RiskSettingsRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    리스크 설정 저장/업데이트

    Args:
        payload: 리스크 설정 요청 (daily_loss_limit, max_leverage, max_positions)

    Returns:
        저장된 설정 정보
    """
    try:
        logger.info(
            f"[save_risk_settings] Saving for user {user_id}: "
            f"loss_limit={payload.daily_loss_limit}, leverage={payload.max_leverage}, positions={payload.max_positions}"
        )

        # 기존 설정 조회
        result = await session.execute(
            select(RiskSettings).where(RiskSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if settings:
            # 업데이트
            logger.info(f"[save_risk_settings] Updating existing settings for user {user_id}")
            settings.daily_loss_limit = payload.daily_loss_limit
            settings.max_leverage = payload.max_leverage
            settings.max_positions = payload.max_positions
            settings.updated_at = datetime.utcnow()
        else:
            # 신규 생성
            logger.info(f"[save_risk_settings] Creating new settings for user {user_id}")
            settings = RiskSettings(
                user_id=user_id,
                daily_loss_limit=payload.daily_loss_limit,
                max_leverage=payload.max_leverage,
                max_positions=payload.max_positions,
            )
            session.add(settings)

        await session.commit()
        await session.refresh(settings)

        logger.info(f"[save_risk_settings] Successfully saved settings for user {user_id}")

        # 캐시 무효화 (리스크 설정이 변경됨)
        from ..utils.cache_manager import cache_manager, make_cache_key
        cache_key = make_cache_key("risk_settings", user_id)
        await cache_manager.delete(cache_key)
        logger.debug(f"Invalidated risk_settings cache for user {user_id}")

        return {
            "message": "리스크 한도 설정이 저장되었습니다",
            "daily_loss_limit": settings.daily_loss_limit,
            "max_leverage": settings.max_leverage,
            "max_positions": settings.max_positions,
            "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
        }

    except ValueError as e:
        # Pydantic validation error
        logger.error(f"[save_risk_settings] Validation error for user {user_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        await session.rollback()
        logger.error(f"[save_risk_settings] Error for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="리스크 설정 저장에 실패했습니다."
        ) from e
