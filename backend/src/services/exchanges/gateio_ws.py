"""
Gate.io WebSocket 클라이언트

실시간 시장 데이터 수신 (Ticker, Candle, Order Book)
Gate.io WebSocket API V4 (USDT Perpetual)
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Callable, Dict, List, Optional

import websockets

logger = logging.getLogger(__name__)


class GateioWebSocket:
    """Gate.io WebSocket 클라이언트"""

    def __init__(self, api_key: str = None, secret_key: str = None):
        """
        WebSocket 클라이언트 초기화

        Args:
            api_key: API 키 (Private 채널용, 선택)
            secret_key: Secret 키 (Private 채널용, 선택)
        """
        self.api_key = api_key
        self.secret_key = secret_key

        # Gate.io USDT Perpetual WebSocket URL
        self.ws_url = "wss://fx-ws.gateio.ws/v4/ws/usdt"

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.callbacks: Dict[str, Callable] = {}
        self.subscriptions: List[dict] = []
        self.running = False
        self.ping_task: Optional[asyncio.Task] = None
        self.request_id = 0

    def _get_request_id(self) -> int:
        """요청 ID 생성"""
        self.request_id += 1
        return self.request_id

    def _generate_signature(self, channel: str, event: str, timestamp: int) -> str:
        """HMAC SHA512 서명 생성"""
        message = f"channel={channel}&event={event}&time={timestamp}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        return signature

    def _normalize_symbol(self, symbol: str) -> str:
        """심볼을 Gate.io 형식으로 변환"""
        # ETH/USDT -> ETH_USDT, ETHUSDT -> ETH_USDT
        symbol = symbol.replace('/', '_').upper()
        if 'USDT' in symbol and '_' not in symbol:
            symbol = symbol.replace('USDT', '_USDT')
        return symbol

    async def connect(self, authenticate: bool = False) -> bool:
        """
        WebSocket 연결

        Args:
            authenticate: Private 채널 인증 여부 (향후 확장)
        """
        try:
            self.ws = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10
            )
            self.running = True
            logger.info(f"Connected to Gate.io WebSocket: {self.ws_url}")

            # Ping 루프 시작
            self.ping_task = asyncio.create_task(self._ping_loop())

            return True
        except Exception as e:
            logger.error(f"Gate.io WebSocket connection error: {e}")
            return False

    async def _ping_loop(self):
        """주기적 Ping 전송 (연결 유지)"""
        while self.running:
            try:
                await asyncio.sleep(15)  # 15초마다
                if self.ws and not self.ws.closed:
                    ping_message = {
                        "time": int(time.time()),
                        "channel": "futures.ping"
                    }
                    await self.ws.send(json.dumps(ping_message))
                    logger.debug("Sent ping to Gate.io")
            except Exception as e:
                logger.error(f"Gate.io ping error: {e}")

    async def _subscribe(self, channel: str, payload: List[str]):
        """채널 구독"""
        if not self.ws or self.ws.closed:
            logger.error("WebSocket not connected")
            return

        timestamp = int(time.time())
        subscribe_message = {
            "time": timestamp,
            "channel": channel,
            "event": "subscribe",
            "payload": payload,
            "id": self._get_request_id()
        }

        # Private 채널이면 서명 추가
        if self.api_key and self.secret_key:
            subscribe_message["auth"] = {
                "method": "api_key",
                "KEY": self.api_key,
                "SIGN": self._generate_signature(channel, "subscribe", timestamp)
            }

        await self.ws.send(json.dumps(subscribe_message))
        self.subscriptions.append({"channel": channel, "payload": payload})
        logger.info(f"Subscribed to Gate.io channel: {channel} {payload}")

    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        Ticker 구독

        Args:
            symbol: 심볼 (예: "ETH_USDT" 또는 "ETHUSDT")
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        channel = "futures.tickers"
        channel_key = f"{channel}:{normalized}"
        self.callbacks[channel_key] = callback

        await self._subscribe(channel, [normalized])
        logger.info(f"Subscribed to Gate.io ticker: {normalized}")

    async def subscribe_candle(self, symbol: str, timeframe: str, callback: Callable):
        """
        Candle 구독

        Args:
            symbol: 심볼
            timeframe: 시간봉 (10s, 1m, 5m, 15m, 30m, 1h, 4h, 8h, 1d, 7d, 30d)
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        channel = "futures.candlesticks"
        channel_key = f"{channel}:{timeframe}_{normalized}"
        self.callbacks[channel_key] = callback

        await self._subscribe(channel, [f"{timeframe}_{normalized}"])
        logger.info(f"Subscribed to Gate.io candle: {normalized} {timeframe}")

    async def subscribe_trades(self, symbol: str, callback: Callable):
        """
        실시간 거래 내역 구독

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        channel = "futures.trades"
        channel_key = f"{channel}:{normalized}"
        self.callbacks[channel_key] = callback

        await self._subscribe(channel, [normalized])
        logger.info(f"Subscribed to Gate.io trades: {normalized}")

    async def subscribe_orderbook(self, symbol: str, depth: str, callback: Callable):
        """
        호가창 구독

        Args:
            symbol: 심볼
            depth: 깊이 (예: "20", "100ms" for update frequency)
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        channel = "futures.order_book"
        channel_key = f"{channel}:{normalized}"
        self.callbacks[channel_key] = callback

        # Gate.io는 심볼, 레벨, 업데이트 주기를 함께 지정
        await self._subscribe(channel, [normalized, depth, "0"])
        logger.info(f"Subscribed to Gate.io orderbook: {normalized} depth={depth}")

    async def subscribe_book_ticker(self, symbol: str, callback: Callable):
        """
        Best Bid/Ask 구독 (빠른 업데이트)

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        channel = "futures.book_ticker"
        channel_key = f"{channel}:{normalized}"
        self.callbacks[channel_key] = callback

        await self._subscribe(channel, [normalized])
        logger.info(f"Subscribed to Gate.io book ticker: {normalized}")

    async def _handle_message(self, message: str):
        """메시지 처리"""
        try:
            data = json.loads(message)

            # Pong 응답
            if data.get('channel') == 'futures.pong':
                logger.debug("Received pong from Gate.io")
                return

            # 구독 응답
            if data.get('event') == 'subscribe':
                if data.get('error') is None:
                    logger.info(f"Gate.io subscription confirmed: {data.get('channel')}")
                else:
                    logger.error(f"Gate.io subscription failed: {data.get('error')}")
                return

            # 데이터 업데이트
            if data.get('event') == 'update' and 'result' in data:
                channel = data.get('channel')
                result = data['result']

                # 콜백 키 결정
                channel_key = self._get_callback_key(channel, result)

                if channel_key and channel_key in self.callbacks:
                    normalized_data = self._normalize_data(channel, result)
                    await self.callbacks[channel_key](normalized_data)
                else:
                    logger.debug(f"No callback for channel: {channel_key}")

        except json.JSONDecodeError as e:
            logger.error(f"Gate.io message decode error: {e}, message: {message}")
        except Exception as e:
            logger.error(f"Gate.io message handling error: {e}")

    def _get_callback_key(self, channel: str, result: any) -> str:
        """콜백 키 결정"""
        if channel == 'futures.tickers':
            if isinstance(result, list) and result:
                return f"{channel}:{result[0].get('contract')}"
            return f"{channel}:{result.get('contract')}"

        if channel == 'futures.candlesticks':
            if isinstance(result, list) and result:
                return f"{channel}:{result[0].get('n')}"
            return f"{channel}:{result.get('n')}"

        if channel == 'futures.trades':
            if isinstance(result, list) and result:
                return f"{channel}:{result[0].get('contract')}"
            return f"{channel}:{result.get('contract')}"

        if channel == 'futures.order_book':
            return f"{channel}:{result.get('contract')}"

        if channel == 'futures.book_ticker':
            return f"{channel}:{result.get('s')}"

        return channel

    def _normalize_data(self, channel: str, result: any) -> dict:
        """데이터를 공통 형식으로 정규화"""
        # Ticker
        if channel == 'futures.tickers':
            item = result[0] if isinstance(result, list) else result
            return {
                'type': 'ticker',
                'symbol': item.get('contract'),
                'last': float(item.get('last', 0)),
                'high': float(item.get('high_24h', 0)),
                'low': float(item.get('low_24h', 0)),
                'volume': float(item.get('volume_24h', 0)),
                'mark_price': float(item.get('mark_price', 0)),
                'index_price': float(item.get('index_price', 0)),
                'funding_rate': float(item.get('funding_rate', 0)),
                'timestamp': int(time.time() * 1000)
            }

        # Candlesticks
        if channel == 'futures.candlesticks':
            item = result[0] if isinstance(result, list) else result
            return {
                'type': 'candle',
                'symbol': item.get('n', '').split('_', 1)[1] if '_' in item.get('n', '') else item.get('n'),
                'timeframe': item.get('n', '').split('_')[0] if '_' in item.get('n', '') else '',
                'timestamp': int(item.get('t', 0)) * 1000,
                'open': float(item.get('o', 0)),
                'high': float(item.get('h', 0)),
                'low': float(item.get('l', 0)),
                'close': float(item.get('c', 0)),
                'volume': float(item.get('v', 0)),
                'is_closed': True
            }

        # Trades
        if channel == 'futures.trades':
            items = result if isinstance(result, list) else [result]
            if items:
                item = items[0]
                return {
                    'type': 'trade',
                    'symbol': item.get('contract'),
                    'price': float(item.get('price', 0)),
                    'quantity': float(item.get('size', 0)),
                    'side': 'buy' if item.get('size', 0) > 0 else 'sell',
                    'timestamp': int(item.get('create_time', 0)) * 1000
                }
            return {}

        # Orderbook
        if channel == 'futures.order_book':
            return {
                'type': 'orderbook',
                'symbol': result.get('contract'),
                'bids': [[float(p), float(s)] for p, s in result.get('bids', [])],
                'asks': [[float(p), float(s)] for p, s in result.get('asks', [])],
                'timestamp': int(result.get('t', 0)) * 1000
            }

        # Book Ticker
        if channel == 'futures.book_ticker':
            return {
                'type': 'book_ticker',
                'symbol': result.get('s'),
                'bid': float(result.get('b', 0)),
                'bid_size': float(result.get('B', 0)),
                'ask': float(result.get('a', 0)),
                'ask_size': float(result.get('A', 0)),
                'timestamp': int(result.get('t', 0)) * 1000
            }

        return result

    async def listen(self):
        """메시지 수신 루프"""
        try:
            while self.running:
                if self.ws and not self.ws.closed:
                    message = await self.ws.recv()
                    await self._handle_message(message)
                else:
                    logger.warning("Gate.io WebSocket closed, attempting reconnect...")
                    await self._reconnect()
                    await asyncio.sleep(5)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Gate.io WebSocket connection closed: {e}")
            if self.running:
                await self._reconnect()
        except Exception as e:
            logger.error(f"Gate.io listen error: {e}")
            self.running = False

    async def _reconnect(self):
        """재연결 로직"""
        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                logger.info(f"Gate.io WebSocket reconnection attempt {attempt + 1}/{max_retries}")
                await self.connect()

                # 기존 구독 복원
                for sub in self.subscriptions:
                    await self._subscribe(sub['channel'], sub['payload'])

                logger.info("Gate.io WebSocket reconnected successfully")
                return
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

        logger.error("Max reconnection attempts reached")
        self.running = False

    async def unsubscribe(self, channel: str, payload: List[str]):
        """채널 구독 해제"""
        if not self.ws or self.ws.closed:
            return

        unsubscribe_message = {
            "time": int(time.time()),
            "channel": channel,
            "event": "unsubscribe",
            "payload": payload
        }

        await self.ws.send(json.dumps(unsubscribe_message))
        logger.info(f"Unsubscribed from Gate.io channel: {channel} {payload}")

    async def close(self):
        """WebSocket 연결 종료"""
        self.running = False

        if self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass

        if self.ws and not self.ws.closed:
            await self.ws.close()
            logger.info("Gate.io WebSocket closed")


async def gateio_ws_collector(market_queue: asyncio.Queue, symbols: List[str] = None):
    """
    Gate.io WebSocket 데이터 수집기

    Args:
        market_queue: 시장 데이터를 전달할 큐
        symbols: 구독할 심볼 리스트
    """
    if symbols is None:
        symbols = ["BTC_USDT", "ETH_USDT"]

    ws_client = GateioWebSocket()

    async def ticker_callback(data):
        await market_queue.put({
            'type': 'ticker',
            'exchange': 'gateio',
            'symbol': data.get('symbol'),
            'data': data
        })

    try:
        connected = await ws_client.connect()
        if not connected:
            logger.error("Failed to connect to Gate.io WebSocket")
            return

        for symbol in symbols:
            await ws_client.subscribe_ticker(symbol, ticker_callback)
            await asyncio.sleep(0.1)

        await ws_client.listen()

    except Exception as e:
        logger.error(f"Gate.io WebSocket collector error: {e}")
    finally:
        await ws_client.close()
