"""
Bybit WebSocket 클라이언트

실시간 시장 데이터 수신 (Ticker, Candle, Order Book)
Bybit WebSocket API V5
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


class BybitWebSocket:
    """Bybit WebSocket 클라이언트"""

    def __init__(self, api_key: str = None, secret_key: str = None):
        """
        WebSocket 클라이언트 초기화

        Args:
            api_key: API 키 (Private 채널용, 선택)
            secret_key: Secret 키 (Private 채널용, 선택)
        """
        self.api_key = api_key
        self.secret_key = secret_key

        # Bybit V5 WebSocket URL (Linear Perpetual)
        self.ws_public_url = "wss://stream.bybit.com/v5/public/linear"
        self.ws_private_url = "wss://stream.bybit.com/v5/private"

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.callbacks: Dict[str, Callable] = {}
        self.subscriptions: List[str] = []
        self.running = False
        self.ping_task: Optional[asyncio.Task] = None
        self.is_private = False

    def _generate_signature(self, expires: int) -> str:
        """HMAC SHA256 서명 생성"""
        param_str = f"GET/realtime{expires}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _normalize_symbol(self, symbol: str) -> str:
        """심볼을 Bybit 형식으로 변환"""
        # ETH/USDT -> ETHUSDT, ETH-USDT -> ETHUSDT
        return symbol.replace('/', '').replace('-', '').upper()

    async def connect(self, authenticate: bool = False) -> bool:
        """
        WebSocket 연결

        Args:
            authenticate: Private 채널 인증 여부
        """
        try:
            url = self.ws_private_url if authenticate else self.ws_public_url
            self.is_private = authenticate

            self.ws = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10
            )
            self.running = True
            logger.info(f"Connected to Bybit WebSocket: {url}")

            if authenticate and self.api_key:
                await self._authenticate()

            # Ping 루프 시작
            self.ping_task = asyncio.create_task(self._ping_loop())

            return True
        except Exception as e:
            logger.error(f"Bybit WebSocket connection error: {e}")
            return False

    async def _authenticate(self):
        """Private 채널 인증"""
        expires = int((time.time() + 10) * 1000)  # 10초 후 만료
        signature = self._generate_signature(expires)

        auth_message = {
            "op": "auth",
            "args": [self.api_key, expires, signature]
        }

        await self.ws.send(json.dumps(auth_message))
        logger.info("Bybit WebSocket authentication sent")

    async def _ping_loop(self):
        """주기적 Ping 전송 (연결 유지)"""
        while self.running:
            try:
                await asyncio.sleep(20)  # 20초마다
                if self.ws and not self.ws.closed:
                    ping_message = {"op": "ping"}
                    await self.ws.send(json.dumps(ping_message))
                    logger.debug("Sent ping to Bybit")
            except Exception as e:
                logger.error(f"Bybit ping error: {e}")

    async def _subscribe(self, topics: List[str]):
        """토픽 구독"""
        if not self.ws or self.ws.closed:
            logger.error("WebSocket not connected")
            return

        subscribe_message = {
            "op": "subscribe",
            "args": topics
        }

        await self.ws.send(json.dumps(subscribe_message))
        self.subscriptions.extend(topics)
        logger.info(f"Subscribed to Bybit topics: {topics}")

    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        Ticker 구독

        Args:
            symbol: 심볼 (예: "ETHUSDT" 또는 "ETH/USDT")
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        topic = f"tickers.{normalized}"
        self.callbacks[topic] = callback

        await self._subscribe([topic])
        logger.info(f"Subscribed to Bybit ticker: {normalized}")

    async def subscribe_candle(self, symbol: str, timeframe: str, callback: Callable):
        """
        Candle(Kline) 구독

        Args:
            symbol: 심볼
            timeframe: 시간봉 (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M)
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        # Bybit 타임프레임 변환: 1m -> 1, 1h -> 60, 1d -> D
        tf_map = {
            '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
            '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
            '1d': 'D', '1w': 'W', '1M': 'M'
        }
        bybit_tf = tf_map.get(timeframe, timeframe)
        topic = f"kline.{bybit_tf}.{normalized}"
        self.callbacks[topic] = callback

        await self._subscribe([topic])
        logger.info(f"Subscribed to Bybit candle: {normalized} {timeframe}")

    async def subscribe_trades(self, symbol: str, callback: Callable):
        """
        실시간 거래 내역 구독

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        topic = f"publicTrade.{normalized}"
        self.callbacks[topic] = callback

        await self._subscribe([topic])
        logger.info(f"Subscribed to Bybit trades: {normalized}")

    async def subscribe_orderbook(self, symbol: str, depth: str, callback: Callable):
        """
        호가창 구독

        Args:
            symbol: 심볼
            depth: 깊이 (1, 25, 50, 200, 500)
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        topic = f"orderbook.{depth}.{normalized}"
        self.callbacks[topic] = callback

        await self._subscribe([topic])
        logger.info(f"Subscribed to Bybit orderbook: {normalized} depth={depth}")

    async def subscribe_liquidation(self, symbol: str, callback: Callable):
        """
        청산 데이터 구독

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        topic = f"liquidation.{normalized}"
        self.callbacks[topic] = callback

        await self._subscribe([topic])
        logger.info(f"Subscribed to Bybit liquidation: {normalized}")

    async def _handle_message(self, message: str):
        """메시지 처리"""
        try:
            data = json.loads(message)

            # Pong 응답
            if data.get('op') == 'pong':
                logger.debug("Received pong from Bybit")
                return

            # 인증 응답
            if data.get('op') == 'auth':
                if data.get('success'):
                    logger.info("Bybit WebSocket authenticated successfully")
                else:
                    logger.error(f"Bybit authentication failed: {data}")
                return

            # 구독 응답
            if data.get('op') == 'subscribe':
                if data.get('success'):
                    logger.info(f"Bybit subscription confirmed: {data.get('req_id')}")
                else:
                    logger.error(f"Bybit subscription failed: {data}")
                return

            # 데이터 메시지
            if 'topic' in data and 'data' in data:
                topic = data['topic']

                if topic in self.callbacks:
                    normalized_data = self._normalize_data(topic, data['data'])
                    await self.callbacks[topic](normalized_data)
                else:
                    logger.debug(f"No callback for topic: {topic}")

        except json.JSONDecodeError as e:
            logger.error(f"Bybit message decode error: {e}, message: {message}")
        except Exception as e:
            logger.error(f"Bybit message handling error: {e}")

    def _normalize_data(self, topic: str, data: any) -> dict:
        """데이터를 공통 형식으로 정규화"""
        # Ticker
        if topic.startswith('tickers.'):
            return {
                'type': 'ticker',
                'symbol': data.get('symbol'),
                'last': float(data.get('lastPrice', 0)),
                'bid': float(data.get('bid1Price', 0)),
                'ask': float(data.get('ask1Price', 0)),
                'high': float(data.get('highPrice24h', 0)),
                'low': float(data.get('lowPrice24h', 0)),
                'volume': float(data.get('volume24h', 0)),
                'price_change_percent': float(data.get('price24hPcnt', 0)) * 100,
                'timestamp': int(data.get('ts', 0))
            }

        # Kline/Candle
        if topic.startswith('kline.'):
            item = data[0] if isinstance(data, list) else data
            return {
                'type': 'candle',
                'symbol': item.get('symbol'),
                'timeframe': topic.split('.')[1],
                'timestamp': int(item.get('start', 0)),
                'open': float(item.get('open', 0)),
                'high': float(item.get('high', 0)),
                'low': float(item.get('low', 0)),
                'close': float(item.get('close', 0)),
                'volume': float(item.get('volume', 0)),
                'is_closed': item.get('confirm', False)
            }

        # Trades
        if topic.startswith('publicTrade.'):
            trades = data if isinstance(data, list) else [data]
            if trades:
                item = trades[0]
                return {
                    'type': 'trade',
                    'symbol': item.get('s'),
                    'price': float(item.get('p', 0)),
                    'quantity': float(item.get('v', 0)),
                    'side': item.get('S', 'Buy').lower(),
                    'timestamp': int(item.get('T', 0))
                }
            return {}

        # Orderbook
        if topic.startswith('orderbook.'):
            return {
                'type': 'orderbook',
                'symbol': data.get('s'),
                'bids': [[float(p), float(q)] for p, q in data.get('b', [])],
                'asks': [[float(p), float(q)] for p, q in data.get('a', [])],
                'timestamp': int(data.get('ts', 0))
            }

        # Liquidation
        if topic.startswith('liquidation.'):
            return {
                'type': 'liquidation',
                'symbol': data.get('symbol'),
                'side': data.get('side'),
                'price': float(data.get('price', 0)),
                'quantity': float(data.get('size', 0)),
                'timestamp': int(data.get('updatedTime', 0))
            }

        return data

    async def listen(self):
        """메시지 수신 루프"""
        try:
            while self.running:
                if self.ws and not self.ws.closed:
                    message = await self.ws.recv()
                    await self._handle_message(message)
                else:
                    logger.warning("Bybit WebSocket closed, attempting reconnect...")
                    await self._reconnect()
                    await asyncio.sleep(5)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Bybit WebSocket connection closed: {e}")
            if self.running:
                await self._reconnect()
        except Exception as e:
            logger.error(f"Bybit listen error: {e}")
            self.running = False

    async def _reconnect(self):
        """재연결 로직"""
        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                logger.info(f"Bybit WebSocket reconnection attempt {attempt + 1}/{max_retries}")
                await self.connect(authenticate=self.is_private)

                if self.subscriptions:
                    await self._subscribe(self.subscriptions.copy())

                logger.info("Bybit WebSocket reconnected successfully")
                return
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

        logger.error("Max reconnection attempts reached")
        self.running = False

    async def unsubscribe(self, topics: List[str]):
        """토픽 구독 해제"""
        if not self.ws or self.ws.closed:
            return

        unsubscribe_message = {
            "op": "unsubscribe",
            "args": topics
        }

        await self.ws.send(json.dumps(unsubscribe_message))

        for topic in topics:
            if topic in self.subscriptions:
                self.subscriptions.remove(topic)
            if topic in self.callbacks:
                del self.callbacks[topic]

        logger.info(f"Unsubscribed from Bybit topics: {topics}")

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
            logger.info("Bybit WebSocket closed")


async def bybit_ws_collector(market_queue: asyncio.Queue, symbols: List[str] = None):
    """
    Bybit WebSocket 데이터 수집기

    Args:
        market_queue: 시장 데이터를 전달할 큐
        symbols: 구독할 심볼 리스트
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT"]

    ws_client = BybitWebSocket()

    async def ticker_callback(data):
        await market_queue.put({
            'type': 'ticker',
            'exchange': 'bybit',
            'symbol': data.get('symbol'),
            'data': data
        })

    try:
        connected = await ws_client.connect()
        if not connected:
            logger.error("Failed to connect to Bybit WebSocket")
            return

        for symbol in symbols:
            await ws_client.subscribe_ticker(symbol, ticker_callback)
            await asyncio.sleep(0.1)

        await ws_client.listen()

    except Exception as e:
        logger.error(f"Bybit WebSocket collector error: {e}")
    finally:
        await ws_client.close()
