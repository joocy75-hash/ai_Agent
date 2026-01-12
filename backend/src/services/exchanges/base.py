"""
거래소 추상화 기본 클래스

이 모듈은 모든 거래소가 구현해야 하는 공통 인터페이스를 정의합니다.
새로운 거래소를 추가할 때는 이 BaseExchange를 상속받아 구현하면 됩니다.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Dict, List, Optional


class BaseExchange(ABC):
    """거래소 기본 추상 클래스"""

    def __init__(self, api_key: str, secret_key: str, passphrase: Optional[str] = None):
        """
        거래소 클라이언트 초기화

        Args:
            api_key: API 키
            secret_key: Secret 키
            passphrase: Passphrase (OKX 등에서 사용)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.exchange_name = self.__class__.__name__.replace("Exchange", "").lower()

    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """
        계정 잔고 조회

        Returns:
            {
                "total": Decimal,  # 총 자산 (USDT)
                "free": Decimal,   # 사용 가능 자산
                "used": Decimal,   # 사용 중 자산
                "assets": [
                    {
                        "currency": "USDT",
                        "total": Decimal,
                        "free": Decimal,
                        "used": Decimal
                    }
                ]
            }
        """
        pass

    @abstractmethod
    async def get_futures_balance(self) -> Dict[str, Any]:
        """
        선물 계정 잔고 조회

        Returns:
            {
                "total": Decimal,  # 총 자산 (USDT)
                "free": Decimal,   # 사용 가능 자산
                "used": Decimal,   # 사용 중 자산 (마진)
                "unrealized_pnl": Decimal,  # 미실현 손익
                "assets": [...]
            }
        """
        pass

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        price: Optional[Decimal] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        주문 생성

        Args:
            symbol: 심볼 (예: "BTC/USDT")
            side: "buy" 또는 "sell"
            order_type: "market", "limit" 등
            amount: 수량
            price: 가격 (limit 주문시 필수)
            params: 추가 파라미터 (레버리지, 포지션 모드 등)

        Returns:
            {
                "id": str,  # 주문 ID
                "symbol": str,
                "side": str,
                "type": str,
                "amount": Decimal,
                "price": Decimal,
                "status": str,  # "open", "closed", "canceled"
                "timestamp": int
            }
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        주문 취소

        Args:
            order_id: 주문 ID
            symbol: 심볼

        Returns:
            취소된 주문 정보
        """
        pass

    @abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        주문 조회

        Args:
            order_id: 주문 ID
            symbol: 심볼

        Returns:
            주문 정보
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        열린 주문 목록 조회

        Args:
            symbol: 심볼 (None이면 모든 심볼)

        Returns:
            주문 목록
        """
        pass

    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        포지션 조회

        Args:
            symbol: 심볼 (None이면 모든 심볼)

        Returns:
            [
                {
                    "symbol": str,
                    "side": str,  # "long" or "short"
                    "amount": Decimal,
                    "entry_price": Decimal,
                    "mark_price": Decimal,
                    "liquidation_price": Decimal,
                    "unrealized_pnl": Decimal,
                    "leverage": int
                }
            ]
        """
        pass

    @abstractmethod
    async def close_position(self, symbol: str, side: Optional[str] = None) -> Dict[str, Any]:
        """
        포지션 청산

        Args:
            symbol: 심볼
            side: "long" or "short" (None이면 모든 포지션)

        Returns:
            청산 결과
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        현재 시세 조회

        Args:
            symbol: 심볼

        Returns:
            {
                "symbol": str,
                "last": Decimal,  # 최종 거래가
                "bid": Decimal,   # 매수호가
                "ask": Decimal,   # 매도호가
                "high": Decimal,  # 24h 고가
                "low": Decimal,   # 24h 저가
                "volume": Decimal,  # 24h 거래량
                "timestamp": int
            }
        """
        pass

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 100,
        since: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        캔들 데이터 조회

        Args:
            symbol: 심볼
            timeframe: 시간봉 ("1m", "5m", "15m", "1h", "4h", "1d")
            limit: 개수
            since: 시작 시간 (timestamp)

        Returns:
            [
                {
                    "timestamp": int,
                    "open": Decimal,
                    "high": Decimal,
                    "low": Decimal,
                    "close": Decimal,
                    "volume": Decimal
                }
            ]
        """
        pass

    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        레버리지 설정

        Args:
            symbol: 심볼
            leverage: 레버리지 배수

        Returns:
            설정 결과
        """
        pass

    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        펀딩 비율 조회

        Args:
            symbol: 심볼

        Returns:
            {
                "symbol": str,
                "funding_rate": Decimal,
                "next_funding_time": int,
                "timestamp": int
            }
        """
        pass

    def get_exchange_name(self) -> str:
        """거래소 이름 반환"""
        return self.exchange_name

    async def health_check(self) -> bool:
        """
        거래소 API 연결 상태 확인

        Returns:
            True if healthy, False otherwise
        """
        try:
            await self.get_ticker("BTC/USDT")
            return True
        except Exception:
            return False
