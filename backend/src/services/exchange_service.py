"""
거래소 클라이언트 관리 서비스

사용자별 거래소 클라이언트 초기화 로직을 중앙화하여
코드 중복을 제거하고 유지보수성을 향상시킵니다.
"""
import logging
from typing import Tuple

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import ExchangeConfig
from ..database.models import ApiKey, User
from ..services.exchanges import BaseExchange, exchange_manager
from ..utils.crypto_secrets import decrypt_secret

logger = logging.getLogger(__name__)


class ExchangeService:
    """거래소 클라이언트 관리 서비스"""

    @staticmethod
    async def get_user_exchange_client(
        session: AsyncSession,
        user_id: int
    ) -> Tuple[BaseExchange, str]:
        """
        사용자의 거래소 클라이언트 가져오기

        Args:
            session: DB 세션
            user_id: 사용자 ID

        Returns:
            (거래소 클라이언트, 거래소 이름) 튜플

        Raises:
            HTTPException: API 키가 없는 경우 (400)

        Example:
            >>> client, exchange_name = await ExchangeService.get_user_exchange_client(session, user_id)
            >>> balance = await client.get_futures_balance()
        """
        # 사용자 정보 조회
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalars().first()

        # API 키 조회
        api_key_result = await session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id)
        )
        api_key = api_key_result.scalars().first()

        if not api_key:
            logger.warning(f"User {user_id} has no API keys configured")
            raise HTTPException(
                status_code=400,
                detail="API keys not configured. Please add your exchange API keys first."
            )

        # 거래소 이름 결정 (설정에서 기본값 가져오기)
        exchange_name = (
            user.exchange if user and user.exchange
            else ExchangeConfig.DEFAULT_EXCHANGE
        )

        try:
            # 클라이언트 생성
            client = exchange_manager.get_client(
                user_id=user_id,
                exchange_name=exchange_name,
                api_key=decrypt_secret(api_key.encrypted_api_key),
                secret_key=decrypt_secret(api_key.encrypted_secret_key),
                passphrase=decrypt_secret(api_key.encrypted_passphrase)
                    if api_key.encrypted_passphrase else None
            )

            logger.info(f"Created {exchange_name} client for user {user_id}")
            return client, exchange_name

        except Exception as e:
            logger.error(f"Failed to create exchange client for user {user_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect to exchange: {str(e)}"
            ) from e

    @staticmethod
    async def has_api_key(session: AsyncSession, user_id: int) -> bool:
        """
        사용자가 API 키를 설정했는지 확인

        Args:
            session: DB 세션
            user_id: 사용자 ID

        Returns:
            API 키가 있으면 True, 없으면 False
        """
        api_key_result = await session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id)
        )
        api_key = api_key_result.scalars().first()
        return api_key is not None
