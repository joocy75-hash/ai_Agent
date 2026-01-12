"""
거래소 팩토리 및 매니저

여러 거래소를 통합 관리하는 모듈
"""

import logging
from typing import Dict, Optional, Type

from .base import BaseExchange
from .binance import BinanceExchange
from .bitget import BitgetExchange
from .bybit import BybitExchange
from .gateio import GateioExchange
from .okx import OKXExchange

logger = logging.getLogger(__name__)


class ExchangeFactory:
    """거래소 팩토리 클래스"""

    # 지원 거래소 등록
    _exchanges: Dict[str, Type[BaseExchange]] = {
        'bitget': BitgetExchange,
        'binance': BinanceExchange,
        'okx': OKXExchange,
        'bybit': BybitExchange,
        'gateio': GateioExchange,
    }

    # Passphrase가 필요한 거래소
    PASSPHRASE_REQUIRED = ['bitget', 'okx']

    @classmethod
    def create(
        cls,
        exchange_name: str,
        api_key: str,
        secret_key: str,
        passphrase: Optional[str] = None
    ) -> BaseExchange:
        """
        거래소 클라이언트 생성

        Args:
            exchange_name: 거래소 이름 ('bitget', 'binance', 'okx')
            api_key: API 키
            secret_key: Secret 키
            passphrase: Passphrase (필요한 거래소만)

        Returns:
            거래소 클라이언트 인스턴스

        Raises:
            ValueError: 지원하지 않는 거래소
        """
        exchange_name = exchange_name.lower()

        if exchange_name not in cls._exchanges:
            raise ValueError(
                f"Unsupported exchange: {exchange_name}. "
                f"Supported exchanges: {list(cls._exchanges.keys())}"
            )

        exchange_class = cls._exchanges[exchange_name]

        # Passphrase 필요 여부 확인
        if exchange_name in cls.PASSPHRASE_REQUIRED:
            if not passphrase:
                raise ValueError(f"{exchange_name} requires passphrase")
            return exchange_class(api_key, secret_key, passphrase)
        else:
            return exchange_class(api_key, secret_key)

    @classmethod
    def register_exchange(cls, name: str, exchange_class: Type[BaseExchange]):
        """
        새로운 거래소 등록

        Args:
            name: 거래소 이름
            exchange_class: 거래소 클래스
        """
        cls._exchanges[name.lower()] = exchange_class
        logger.info(f"Registered exchange: {name}")

    @classmethod
    def get_supported_exchanges(cls) -> list:
        """지원 거래소 목록 반환"""
        return list(cls._exchanges.keys())


class ExchangeManager:
    """
    거래소 관리자

    사용자별 거래소 클라이언트를 관리하고 캐싱
    """

    def __init__(self):
        self._clients: Dict[str, BaseExchange] = {}

    def get_client(
        self,
        user_id: int,
        exchange_name: str,
        api_key: str,
        secret_key: str,
        passphrase: Optional[str] = None,
        force_new: bool = False
    ) -> BaseExchange:
        """
        거래소 클라이언트 가져오기 (캐싱)

        Args:
            user_id: 사용자 ID
            exchange_name: 거래소 이름
            api_key: API 키
            secret_key: Secret 키
            passphrase: Passphrase
            force_new: 강제로 새 인스턴스 생성

        Returns:
            거래소 클라이언트
        """
        cache_key = f"{user_id}:{exchange_name}"

        if not force_new and cache_key in self._clients:
            return self._clients[cache_key]

        client = ExchangeFactory.create(
            exchange_name=exchange_name,
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase
        )

        self._clients[cache_key] = client
        logger.info(f"Created {exchange_name} client for user {user_id}")

        return client

    async def close_client(self, user_id: int, exchange_name: str):
        """
        거래소 클라이언트 종료

        Args:
            user_id: 사용자 ID
            exchange_name: 거래소 이름
        """
        cache_key = f"{user_id}:{exchange_name}"

        if cache_key in self._clients:
            client = self._clients[cache_key]
            if hasattr(client, 'close'):
                await client.close()
            del self._clients[cache_key]
            logger.info(f"Closed {exchange_name} client for user {user_id}")

    async def close_all(self):
        """모든 거래소 클라이언트 종료"""
        for _cache_key, client in self._clients.items():
            if hasattr(client, 'close'):
                await client.close()
        self._clients.clear()
        logger.info("Closed all exchange clients")

    def get_active_exchanges(self) -> Dict[str, int]:
        """
        활성 거래소별 연결 수 반환

        Returns:
            {'bitget': 2, 'binance': 1, ...}
        """
        result = {}
        for cache_key in self._clients:
            exchange_name = cache_key.split(':')[1]
            result[exchange_name] = result.get(exchange_name, 0) + 1
        return result


# 전역 거래소 매니저 인스턴스
exchange_manager = ExchangeManager()
