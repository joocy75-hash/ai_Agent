"""
OKX WebSocket 클라이언트

실시간 시장 데이터 수신 (Ticker, Candle, Order Book)
OKX WebSocket API V5
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Callable, Dict, List, Optional

import websockets

logger = logging.getLogger(__name__)


class OKXWebSocket:
    """OKX WebSocket 클라이언트"""

    def __init__(self, api_key: str = None, secret_key: str = None, passphrase: str = None):
        """
        WebSocket 클라이언트 초기화

        Args:
            api_key: API 키 (Private 채널용, 선택)
            secret_key: Secret 키 (Private 채널용, 선택)
            passphrase: Passphrase (Private 채널용, 선택)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

        # OKX WebSocket URL
        self.ws_public_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.ws_private_url = "wss://ws.okx.com:8443/ws/v5/private"

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.callbacks: Dict[str, Callable] = {}
        self.subscriptions: List[dict] = []
        self.running = False
        self.ping_task: Optional[asyncio.Task] = None
        self.is_private = False

    def _generate_signature(self, timestamp: str, method: str, request_path: str) -> str:
        """HMAC SHA256 서명 생성"""
        message = timestamp + method + request_path
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(signature.digest()).decode('utf-8')

    def _normalize_symbol(self, symbol: str) -> str:
        """심볼을 OKX 형식으로 변환"""
        # ETH/USDT -> ETH-USDT-SWAP, ETHUSDT -> ETH-USDT-SWAP
        symbol = symbol.replace('/', '-').upper()
        if 'USDT' in symbol and '-SWAP' not in symbol:
            symbol = symbol.replace('USDT', '-USDT')
            if not symbol.endswith('-SWAP'):
                symbol += '-SWAP'
        return symbol

    async def connect(self, authenticate: bool = False) -> bool:
        """
        WebSocket 연결

        Args:
            authenticate: Private 채널 인증 여부
        """
        try:
            url = self.ws_private_url if authenticate else self.ws_public_url
            self.is_private = authenticate

            self.ws = await websockets.connect(url)
            self.running = True
            logger.info(f"Connected to OKX WebSocket: {url}")

            if authenticate and self.api_key:
                await self._authenticate()

            # Ping 루프 시작
            self.ping_task = asyncio.create_task(self._ping_loop())

            return True
        except Exception as e:
            logger.error(f"OKX WebSocket connection error: {e}")
            return False

    async def _authenticate(self):
        """Private 채널 인증"""
        timestamp = str(int(time.time()))
        sign = self._generate_signature(timestamp, 'GET', '/users/self/verify')

        login_message = {
            "op": "login",
            "args": [{
                "apiKey": self.api_key,
                "passphrase": self.passphrase,
                "timestamp": timestamp,
                "sign": sign
            }]
        }

        await self.ws.send(json.dumps(login_message))
        logger.info("OKX WebSocket authentication sent")

    async def _ping_loop(self):
        """주기적 Ping 전송 (연결 유지)"""
        while self.running:
            try:
                await asyncio.sleep(25)  # 25초마다 (OKX 30초 타임아웃)
                if self.ws and not self.ws.closed:
                    await self.ws.send("ping")
                    logger.debug("Sent ping to OKX")
            except Exception as e:
                logger.error(f"OKX ping error: {e}")

    async def _subscribe(self, args: List[dict]):
        """채널 구독"""
        if not self.ws or self.ws.closed:
            logger.error("WebSocket not connected")
            return

        subscribe_message = {
            "op": "subscribe",
            "args": args
        }

        await self.ws.send(json.dumps(subscribe_message))
        self.subscriptions.extend(args)
        logger.info(f"Subscribed to OKX channels: {args}")

    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        Ticker 구독

        Args:
            symbol: 심볼 (예: "ETH-USDT-SWAP" 또는 "ETHUSDT")
            callback: 데이터 수신 콜백 함수
        """
        inst_id = self._normalize_symbol(symbol)
        channel_key = f"tickers:{inst_id}"
        self.callbacks[channel_key] = callback

        await self._subscribe([{
            "channel": "tickers",
            "instId": inst_id
        }])
        logger.info(f"Subscribed to OKX ticker: {inst_id}")

    async def subscribe_candle(self, symbol: str, timeframe: str, callback: Callable):
        """
        Candle 구독

        Args:
            symbol: 심볼
            timeframe: 시간봉 (1m, 3m, 5m, 15m, 30m, 1H, 2H, 4H, 6H, 12H, 1D, 1W, 1M)
            callback: 데이터 수신 콜백 함수
        """
        inst_id = self._normalize_symbol(symbol)
        # OKX candle 채널: candle1m, candle5m, candle1H 등
        channel = f"candle{timeframe}"
        channel_key = f"{channel}:{inst_id}"
        self.callbacks[channel_key] = callback

        await self._subscribe([{
            "channel": channel,
            "instId": inst_id
        }])
        logger.info(f"Subscribed to OKX candle: {inst_id} {timeframe}")

    async def subscribe_trades(self, symbol: str, callback: Callable):
        """
        실시간 거래 내역 구독

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        inst_id = self._normalize_symbol(symbol)
        channel_key = f"trades:{inst_id}"
        self.callbacks[channel_key] = callback

        await self._subscribe([{
            "channel": "trades",
            "instId": inst_id
        }])
        logger.info(f"Subscribed to OKX trades: {inst_id}")

    async def subscribe_orderbook(self, symbol: str, depth: str, callback: Callable):
        """
        호가창 구독

        Args:
            symbol: 심볼
            depth: 깊이 (books5, books, books50-l2-tbt)
            callback: 데이터 수신 콜백 함수
        """
        inst_id = self._normalize_symbol(symbol)
        channel_key = f"{depth}:{inst_id}"
        self.callbacks[channel_key] = callback

        await self._subscribe([{
            "channel": depth,
            "instId": inst_id
        }])
        logger.info(f"Subscribed to OKX orderbook: {inst_id} {depth}")

    async def subscribe_mark_price(self, symbol: str, callback: Callable):
        """
        마크 가격 구독

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        inst_id = self._normalize_symbol(symbol)
        channel_key = f"mark-price:{inst_id}"
        self.callbacks[channel_key] = callback

        await self._subscribe([{
            "channel": "mark-price",
            "instId": inst_id
        }])
        logger.info(f"Subscribed to OKX mark price: {inst_id}")

    async def _handle_message(self, message: str):
        """메시지 처리"""
        try:
            # Pong 응답
            if message == "pong":
                logger.debug("Received pong from OKX")
                return

            data = json.loads(message)

            # 이벤트 응답 (login, subscribe, error)
            if 'event' in data:
                event = data['event']
                if event == 'login':
                    if data.get('code') == '0':
                        logger.info("OKX WebSocket authenticated successfully")
                    else:
                        logger.error(f"OKX authentication failed: {data}")
                elif event == 'subscribe':
                    logger.info(f"OKX subscription confirmed: {data.get('arg')}")
                elif event == 'error':
                    logger.error(f"OKX WebSocket error: {data}")
                return

            # 데이터 메시지
            if 'data' in data and 'arg' in data:
                arg = data['arg']
                channel = arg.get('channel')
                inst_id = arg.get('instId')
                channel_key = f"{channel}:{inst_id}"

                if channel_key in self.callbacks:
                    normalized_data = self._normalize_data(channel, data['data'])
                    await self.callbacks[channel_key](normalized_data)
                else:
                    logger.debug(f"No callback for channel: {channel_key}")

        except json.JSONDecodeError as e:
            logger.error(f"OKX message decode error: {e}, message: {message}")
        except Exception as e:
            logger.error(f"OKX message handling error: {e}")

    def _normalize_data(self, channel: str, data: list) -> dict:
        """데이터를 공통 형식으로 정규화"""
        if not data:
            return {}

        item = data[0] if isinstance(data, list) else data

        # Ticker
        if channel == 'tickers':
            return {
                'type': 'ticker',
                'symbol': item.get('instId'),
                'last': float(item.get('last', 0)),
                'bid': float(item.get('bidPx', 0)),
                'ask': float(item.get('askPx', 0)),
                'high': float(item.get('high24h', 0)),
                'low': float(item.get('low24h', 0)),
                'volume': float(item.get('vol24h', 0)),
                'timestamp': int(item.get('ts', 0))
            }

        # Candle
        if channel.startswith('candle'):
            return {
                'type': 'candle',
                'symbol': item.get('instId'),
                'timeframe': channel.replace('candle', ''),
                'timestamp': int(item[0]) if isinstance(item, list) else int(item.get('ts', 0)),
                'open': float(item[1]) if isinstance(item, list) else float(item.get('o', 0)),
                'high': float(item[2]) if isinstance(item, list) else float(item.get('h', 0)),
                'low': float(item[3]) if isinstance(item, list) else float(item.get('l', 0)),
                'close': float(item[4]) if isinstance(item, list) else float(item.get('c', 0)),
                'volume': float(item[5]) if isinstance(item, list) else float(item.get('vol', 0)),
                'is_closed': item[8] == '1' if isinstance(item, list) and len(item) > 8 else True
            }

        # Trades
        if channel == 'trades':
            return {
                'type': 'trade',
                'symbol': item.get('instId'),
                'price': float(item.get('px', 0)),
                'quantity': float(item.get('sz', 0)),
                'side': item.get('side', 'buy'),
                'timestamp': int(item.get('ts', 0))
            }

        # Mark Price
        if channel == 'mark-price':
            return {
                'type': 'mark_price',
                'symbol': item.get('instId'),
                'mark_price': float(item.get('markPx', 0)),
                'timestamp': int(item.get('ts', 0))
            }

        # Orderbook
        if channel.startswith('books'):
            return {
                'type': 'orderbook',
                'symbol': item.get('instId'),
                'bids': [[float(p), float(q)] for p, q, _, _ in item.get('bids', [])],
                'asks': [[float(p), float(q)] for p, q, _, _ in item.get('asks', [])],
                'timestamp': int(item.get('ts', 0))
            }

        return item

    async def listen(self):
        """메시지 수신 루프"""
        try:
            while self.running:
                if self.ws and not self.ws.closed:
                    message = await self.ws.recv()
                    await self._handle_message(message)
                else:
                    logger.warning("OKX WebSocket closed, attempting reconnect...")
                    await self._reconnect()
                    await asyncio.sleep(5)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"OKX WebSocket connection closed: {e}")
            if self.running:
                await self._reconnect()
        except Exception as e:
            logger.error(f"OKX listen error: {e}")
            self.running = False

    async def _reconnect(self):
        """재연결 로직"""
        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                logger.info(f"OKX WebSocket reconnection attempt {attempt + 1}/{max_retries}")
                await self.connect(authenticate=self.is_private)

                # 기존 구독 복원
                if self.subscriptions:
                    await self._subscribe(self.subscriptions.copy())

                logger.info("OKX WebSocket reconnected successfully")
                return
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)

        logger.error("Max reconnection attempts reached")
        self.running = False

    async def unsubscribe(self, args: List[dict]):
        """채널 구독 해제"""
        if not self.ws or self.ws.closed:
            return

        unsubscribe_message = {
            "op": "unsubscribe",
            "args": args
        }

        await self.ws.send(json.dumps(unsubscribe_message))
        logger.info(f"Unsubscribed from OKX channels: {args}")

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
            logger.info("OKX WebSocket closed")


async def okx_ws_collector(market_queue: asyncio.Queue, symbols: List[str] = None):
    """
    OKX WebSocket 데이터 수집기

    Args:
        market_queue: 시장 데이터를 전달할 큐
        symbols: 구독할 심볼 리스트
    """
    if symbols is None:
        symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]

    ws_client = OKXWebSocket()

    async def ticker_callback(data):
        await market_queue.put({
            'type': 'ticker',
            'exchange': 'okx',
            'symbol': data.get('symbol'),
            'data': data
        })

    try:
        connected = await ws_client.connect()
        if not connected:
            logger.error("Failed to connect to OKX WebSocket")
            return

        for symbol in symbols:
            await ws_client.subscribe_ticker(symbol, ticker_callback)
            await asyncio.sleep(0.1)

        await ws_client.listen()

    except Exception as e:
        logger.error(f"OKX WebSocket collector error: {e}")
    finally:
        await ws_client.close()
