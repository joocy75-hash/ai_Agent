from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import ApiKey, User
from ..services.exchanges import exchange_manager
from ..utils.crypto_secrets import CryptoError, decrypt_secret


class InvalidApiKeyError(Exception):
    """Raised when the stored encrypted API key cannot be used."""


async def ensure_client(user_id: int, session: AsyncSession, validate: bool = True):
    """Return a client bound to the decrypted API key for a user."""
    try:
        # 사용자 정보와 API 키 조회
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalars().first()

        api_key_result = await session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
        api_key = api_key_result.scalars().first()

        if not api_key:
            raise ValueError("API key not found")

        # 사용자의 거래소 설정에 따라 클라이언트 생성
        exchange_name = user.exchange if user and user.exchange else "bitget"

        client = exchange_manager.get_client(
            user_id=user_id,
            exchange_name=exchange_name,
            api_key=decrypt_secret(api_key.encrypted_api_key),
            secret_key=decrypt_secret(api_key.encrypted_secret_key),
            passphrase=decrypt_secret(api_key.encrypted_passphrase) if api_key.encrypted_passphrase else None
        )

        if validate:
            # 잔고 조회로 API 키 유효성 검증
            await client.get_futures_balance()

        return client

    except (ValueError, CryptoError) as exc:
        raise InvalidApiKeyError("Unable to load API credentials.") from exc


async def place_market_order(
    client, symbol: str, side: str, qty: float, leverage: int
) -> Any:
    """시장가 주문 실행"""
    # 레버리지 설정
    await client.set_leverage(symbol, leverage)

    # 주문 생성
    order = await client.create_order(
        symbol=symbol,
        side=side,
        order_type='market',
        amount=Decimal(str(qty))
    )

    return order
