"""
Bitget WebSocket 클라이언트

실시간 시장 데이터 수신 (Ticker, Candle, Order Book)
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Callable, Dict, Optional

import websockets

logger = logging.getLogger(__name__)


class BitgetWebSocket:
    """Bitget WebSocket 클라이언트"""

    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        passphrase: str = None
    ):
        """
        WebSocket 클라이언트 초기화

        Args:
            api_key: API 키 (Private 스트림용, 선택)
            secret_key: Secret 키 (Private 스트림용, 선택)
            passphrase: API Passphrase (Private 스트림용, 선택)

        Note:
            Public 스트림(Ticker, Candle 등)은 API 키 없이 사용 가능
            Private 스트림(주문, 포지션)은 API 키 필수
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

        # Bitget USDT-M 선물 WebSocket URL
        self.ws_url = "wss://ws.bitget.com/mix/v1/stream"

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.callbacks: Dict[str, Callable] = {}
        self.running = False
        self.ping_task: Optional[asyncio.Task] = None

    def _generate_signature(self, timestamp: str, method: str, request_path: str) -> str:
        """인증 서명 생성"""
        message = timestamp + method + request_path
        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode('utf-8')

    async def _authenticate(self):
        """WebSocket 인증 (Private 스트림용)"""
        if not self.api_key or not self.secret_key or not self.passphrase:
            logger.warning("API credentials not provided, skipping authentication")
            return False

        timestamp = str(int(time.time()))
        sign = self._generate_signature(timestamp, 'GET', '/user/verify')

        auth_message = {
            "op": "login",
            "args": [{
                "apiKey": self.api_key,
                "passphrase": self.passphrase,
                "timestamp": timestamp,
                "sign": sign
            }]
        }

        await self.ws.send(json.dumps(auth_message))
        logger.info("Bitget WebSocket authentication sent")
        return True

    async def _ping_loop(self):
        """주기적 Ping 전송 (연결 유지)"""
        while self.running:
            try:
                await asyncio.sleep(15)  # 15초마다
                if self.ws and not self.ws.closed:
                    await self.ws.send("ping")
                    logger.debug("Sent ping to Bitget")
            except Exception as e:
                logger.error(f"Bitget ping error: {e}")

    async def connect(self, authenticate: bool = False):
        """WebSocket 연결"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.running = True
            logger.info(f"Connected to Bitget WebSocket: {self.ws_url}")

            if authenticate:
                await self._authenticate()

            # Ping 루프 시작
            self.ping_task = asyncio.create_task(self._ping_loop())

            return True
        except Exception as e:
            logger.error(f"Bitget WebSocket connection error: {e}")
            return False

    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        Ticker 구독

        Args:
            symbol: 심볼 (예: "BTCUSDT_UMCBL")
            callback: 데이터 수신 콜백 함수
        """
        channel = f"ticker:{symbol}"
        self.callbacks[channel] = callback

        subscribe_message = {
            "op": "subscribe",
            "args": [{
                "instType": "mc",  # Mixed Contract (USDT-M)
                "channel": "ticker",
                "instId": symbol
            }]
        }

        await self.ws.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to Bitget ticker: {symbol}")

    async def subscribe_candle(self, symbol: str, timeframe: str, callback: Callable):
        """
        Candle 구독

        Args:
            symbol: 심볼
            timeframe: 시간봉 (1m, 5m, 15m, 30m, 1H, 4H, 1D)
            callback: 데이터 수신 콜백 함수
        """
        channel = f"candle{timeframe}:{symbol}"
        self.callbacks[channel] = callback

        subscribe_message = {
            "op": "subscribe",
            "args": [{
                "instType": "mc",
                "channel": f"candle{timeframe}",
                "instId": symbol
            }]
        }

        await self.ws.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to Bitget candle: {symbol} {timeframe}")

    async def subscribe_trades(self, symbol: str, callback: Callable):
        """
        실시간 거래 내역 구독

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        channel = f"trade:{symbol}"
        self.callbacks[channel] = callback

        subscribe_message = {
            "op": "subscribe",
            "args": [{
                "instType": "mc",
                "channel": "trade",
                "instId": symbol
            }]
        }

        await self.ws.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to Bitget trades: {symbol}")

    async def subscribe_orderbook(self, symbol: str, depth: str, callback: Callable):
        """
        호가창 구독

        Args:
            symbol: 심볼
            depth: 깊이 (books5, books15, books)
            callback: 데이터 수신 콜백 함수
        """
        channel = f"{depth}:{symbol}"
        self.callbacks[channel] = callback

        subscribe_message = {
            "op": "subscribe",
            "args": [{
                "instType": "mc",
                "channel": depth,
                "instId": symbol
            }]
        }

        await self.ws.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to Bitget orderbook: {symbol} {depth}")

    async def _handle_message(self, message: str):
        """메시지 처리"""
        try:
            if message == "pong":
                logger.debug("Received pong from Bitget")
                return

            data = json.loads(message)

            # 인증 응답
            if data.get('event') == 'login':
                if data.get('code') == '0':
                    logger.info("Bitget WebSocket authenticated successfully")
                else:
                    logger.error(f"Bitget authentication failed: {data}")
                return

            # 구독 응답
            if data.get('event') == 'subscribe':
                logger.info(f"Bitget subscription confirmed: {data}")
                return

            # 데이터 메시지
            if 'data' in data and 'arg' in data:
                channel = data['arg'].get('channel')
                inst_id = data['arg'].get('instId')
                channel_key = f"{channel}:{inst_id}"

                if channel_key in self.callbacks:
                    await self.callbacks[channel_key](data['data'])
                else:
                    logger.debug(f"No callback for channel: {channel_key}")

        except json.JSONDecodeError as e:
            logger.error(f"Bitget message decode error: {e}, message: {message}")
        except Exception as e:
            logger.error(f"Bitget message handling error: {e}")

    async def listen(self):
        """메시지 수신 루프"""
        try:
            while self.running:
                if self.ws and not self.ws.closed:
                    message = await self.ws.recv()
                    await self._handle_message(message)
                else:
                    logger.warning("Bitget WebSocket closed, attempting reconnect...")
                    await self.connect()
                    await asyncio.sleep(5)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Bitget WebSocket connection closed")
            self.running = False
        except Exception as e:
            logger.error(f"Bitget listen error: {e}")
            self.running = False

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
            logger.info("Bitget WebSocket closed")


# 전역 WebSocket 데이터 수집기 함수
async def bitget_ws_collector(
    market_queue: asyncio.Queue,
    symbols: list = None,
    api_key: str = None,
    secret_key: str = None,
    passphrase: str = None
):
    """
    Bitget WebSocket 데이터 수집기

    Public 스트림(Ticker, Candle)은 API 키 없이 사용 가능.
    Private 스트림(주문, 포지션)은 API 키 필요.

    Args:
        market_queue: 시장 데이터를 전달할 큐
        symbols: 구독할 심볼 리스트 (기본: ["BTCUSDT_UMCBL", "ETHUSDT_UMCBL"])
        api_key: API 키 (Private 스트림용, 선택)
        secret_key: Secret 키 (Private 스트림용, 선택)
        passphrase: Passphrase (Private 스트림용, 선택)
    """
    if symbols is None:
        symbols = ["BTCUSDT_UMCBL", "ETHUSDT_UMCBL"]

    # API 키가 없어도 Public 스트림 사용 가능
    ws_client = BitgetWebSocket(api_key, secret_key, passphrase)

    async def ticker_callback(data):
        """Ticker 데이터 처리"""
        for ticker in data:
            await market_queue.put({
                'type': 'ticker',
                'exchange': 'bitget',
                'symbol': ticker.get('instId'),
                'data': {
                    'last': float(ticker.get('last', 0)),
                    'bid': float(ticker.get('bidPr', 0)),
                    'ask': float(ticker.get('askPr', 0)),
                    'high24h': float(ticker.get('high24h', 0)),
                    'low24h': float(ticker.get('low24h', 0)),
                    'volume24h': float(ticker.get('baseVolume', 0)),
                    'timestamp': int(ticker.get('ts', 0))
                }
            })

    async def candle_callback(data):
        """Candle 데이터 처리"""
        for candle in data:
            await market_queue.put({
                'type': 'candle',
                'exchange': 'bitget',
                'symbol': candle.get('instId'),
                'data': {
                    'timestamp': int(candle[0]) if isinstance(candle, list) else 0,
                    'open': float(candle[1]) if isinstance(candle, list) else 0,
                    'high': float(candle[2]) if isinstance(candle, list) else 0,
                    'low': float(candle[3]) if isinstance(candle, list) else 0,
                    'close': float(candle[4]) if isinstance(candle, list) else 0,
                    'volume': float(candle[5]) if isinstance(candle, list) else 0
                }
            })

    try:
        connected = await ws_client.connect()
        if not connected:
            logger.error("Failed to connect to Bitget WebSocket")
            return

        # 각 심볼에 대해 Ticker와 1분봉 구독
        for symbol in symbols:
            await ws_client.subscribe_ticker(symbol, ticker_callback)
            await ws_client.subscribe_candle(symbol, "1m", candle_callback)
            await asyncio.sleep(0.1)  # Rate limit 방지

        logger.info(f"Bitget WebSocket collector started for symbols: {symbols}")

        # 메시지 수신 시작
        await ws_client.listen()

    except Exception as e:
        logger.error(f"Bitget WebSocket collector error: {e}")
    finally:
        await ws_client.close()
