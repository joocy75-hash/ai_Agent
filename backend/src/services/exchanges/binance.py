"""
Binance 거래소 REST API 클라이언트

CCXT를 사용한 Binance USDT-M 선물 거래 구현
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

import ccxt.async_support as ccxt

from .base import BaseExchange

logger = logging.getLogger(__name__)


class BinanceExchange(BaseExchange):
    """Binance 거래소 클라이언트"""

    def __init__(self, api_key: str, secret_key: str):
        """
        Binance 클라이언트 초기화

        Args:
            api_key: API 키
            secret_key: Secret 키
        """
        super().__init__(api_key, secret_key, None)  # Binance는 passphrase 불필요

        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # USDT-M 선물 (Perpetual)
                'adjustForTimeDifference': True,  # 서버 시간 자동 동기화
            }
        })

    async def get_balance(self) -> Dict[str, Any]:
        """현물 계정 잔고 조회"""
        try:
            balance = await self.exchange.fetch_balance({'type': 'spot'})

            total = Decimal(str(balance.get('USDT', {}).get('total', 0)))
            free = Decimal(str(balance.get('USDT', {}).get('free', 0)))
            used = Decimal(str(balance.get('USDT', {}).get('used', 0)))

            assets = []
            for currency, data in balance.items():
                if currency not in ['info', 'free', 'used', 'total'] and data.get('total', 0) > 0:
                    assets.append({
                        'currency': currency,
                        'total': Decimal(str(data.get('total', 0))),
                        'free': Decimal(str(data.get('free', 0))),
                        'used': Decimal(str(data.get('used', 0)))
                    })

            return {
                'total': total,
                'free': free,
                'used': used,
                'assets': assets
            }
        except Exception as e:
            logger.error(f"Binance get_balance error: {e}")
            raise

    async def get_futures_balance(self) -> Dict[str, Any]:
        """선물 계정 잔고 조회"""
        try:
            balance = await self.exchange.fetch_balance({'type': 'swap'})

            total = Decimal(str(balance.get('USDT', {}).get('total', 0)))
            free = Decimal(str(balance.get('USDT', {}).get('free', 0)))
            used = Decimal(str(balance.get('USDT', {}).get('used', 0)))

            # 미실현 손익 계산
            positions = await self.get_positions()
            unrealized_pnl = sum(Decimal(str(p.get('unrealized_pnl', 0))) for p in positions)

            assets = []
            for currency, data in balance.items():
                if currency not in ['info', 'free', 'used', 'total'] and data.get('total', 0) > 0:
                    assets.append({
                        'currency': currency,
                        'total': Decimal(str(data.get('total', 0))),
                        'free': Decimal(str(data.get('free', 0))),
                        'used': Decimal(str(data.get('used', 0)))
                    })

            return {
                'total': total,
                'free': free,
                'used': used,
                'unrealized_pnl': unrealized_pnl,
                'assets': assets
            }
        except Exception as e:
            logger.error(f"Binance get_futures_balance error: {e}")
            raise

    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        price: Optional[Decimal] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """주문 생성"""
        try:
            params = params or {}

            order = await self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=float(amount),
                price=float(price) if price else None,
                params=params
            )

            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'amount': Decimal(str(order.get('amount', 0))),
                'price': Decimal(str(order.get('price', 0))) if order.get('price') else None,
                'status': order.get('status', 'unknown'),
                'timestamp': order.get('timestamp', 0)
            }
        except Exception as e:
            logger.error(f"Binance create_order error: {e}")
            raise

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """주문 취소"""
        try:
            result = await self.exchange.cancel_order(order_id, symbol)
            return result
        except Exception as e:
            logger.error(f"Binance cancel_order error: {e}")
            raise

    async def get_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """주문 조회"""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            logger.error(f"Binance get_order error: {e}")
            raise

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """열린 주문 목록 조회"""
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            logger.error(f"Binance get_open_orders error: {e}")
            raise

    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """포지션 조회"""
        try:
            positions = await self.exchange.fetch_positions([symbol] if symbol else None)

            result = []
            for pos in positions:
                contracts = float(pos.get('contracts', 0) or 0)
                if contracts == 0:
                    continue  # 빈 포지션 제외

                result.append({
                    'symbol': pos['symbol'],
                    'side': pos['side'],  # 'long' or 'short'
                    'amount': Decimal(str(contracts)),
                    'entry_price': Decimal(str(pos.get('entryPrice', 0) or 0)),
                    'mark_price': Decimal(str(pos.get('markPrice', 0) or 0)),
                    'liquidation_price': Decimal(str(pos.get('liquidationPrice', 0) or 0)),
                    'unrealized_pnl': Decimal(str(pos.get('unrealizedPnl', 0) or 0)),
                    'leverage': int(pos.get('leverage', 1) or 1)
                })

            return result
        except Exception as e:
            logger.error(f"Binance get_positions error: {e}")
            raise

    async def close_position(self, symbol: str, side: Optional[str] = None) -> Dict[str, Any]:
        """포지션 청산"""
        try:
            positions = await self.get_positions(symbol)

            if not positions:
                return {'message': 'No positions to close'}

            results = []
            for pos in positions:
                if side and pos['side'] != side:
                    continue

                # 반대 방향으로 시장가 주문
                close_side = 'sell' if pos['side'] == 'long' else 'buy'
                result = await self.create_order(
                    symbol=symbol,
                    side=close_side,
                    order_type='market',
                    amount=pos['amount'],
                    params={'reduceOnly': True}  # 포지션 감소 전용
                )
                results.append(result)

            return {'closed_positions': results}
        except Exception as e:
            logger.error(f"Binance close_position error: {e}")
            raise

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """현재 시세 조회"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)

            return {
                'symbol': ticker['symbol'],
                'last': Decimal(str(ticker.get('last', 0))),
                'bid': Decimal(str(ticker.get('bid', 0))),
                'ask': Decimal(str(ticker.get('ask', 0))),
                'high': Decimal(str(ticker.get('high', 0))),
                'low': Decimal(str(ticker.get('low', 0))),
                'volume': Decimal(str(ticker.get('volume', 0))),
                'timestamp': ticker.get('timestamp', 0)
            }
        except Exception as e:
            logger.error(f"Binance get_ticker error: {e}")
            raise

    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 100,
        since: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """캔들 데이터 조회"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )

            candles = []
            for candle in ohlcv:
                candles.append({
                    'timestamp': int(candle[0] / 1000),  # ms -> s
                    'open': Decimal(str(candle[1])),
                    'high': Decimal(str(candle[2])),
                    'low': Decimal(str(candle[3])),
                    'close': Decimal(str(candle[4])),
                    'volume': Decimal(str(candle[5]))
                })

            return candles
        except Exception as e:
            logger.error(f"Binance get_candles error: {e}")
            raise

    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """레버리지 설정"""
        try:
            result = await self.exchange.set_leverage(leverage, symbol)
            return result
        except Exception as e:
            logger.error(f"Binance set_leverage error: {e}")
            raise

    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """펀딩 비율 조회"""
        try:
            funding = await self.exchange.fetch_funding_rate(symbol)

            return {
                'symbol': funding['symbol'],
                'funding_rate': Decimal(str(funding.get('fundingRate', 0))),
                'next_funding_time': funding.get('fundingTimestamp', 0),
                'timestamp': funding.get('timestamp', 0)
            }
        except Exception as e:
            logger.error(f"Binance get_funding_rate error: {e}")
            raise

    # Alias 메서드 (다른 코드와의 호환성을 위해)
    async def fetch_balance(self) -> Dict[str, Any]:
        """잔고 조회 (get_futures_balance의 alias)"""
        return await self.get_futures_balance()

    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """포지션 조회 (get_positions의 alias)"""
        return await self.get_positions(symbol)

    async def close(self):
        """CCXT 연결 종료"""
        if self.exchange:
            await self.exchange.close()
