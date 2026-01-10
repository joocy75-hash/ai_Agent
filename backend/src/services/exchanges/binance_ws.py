"""
Binance WebSocket 클라이언트

실시간 시장 데이터 수신 (Ticker, Candle, Order Book)
Binance USDT-M Futures WebSocket API
"""

import asyncio
import json
import websockets
import hmac
import hashlib
import time
from typing import Dict, Callable, Optional, Any, List
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class BinanceWebSocket:
    """Binance USDT-M 선물 WebSocket 클라이언트"""

    def __init__(self, api_key: str = None, secret_key: str = None):
        """
        WebSocket 클라이언트 초기화

        Args:
            api_key: API 키 (Private 스트림용, 선택)
            secret_key: Secret 키 (Private 스트림용, 선택)
        """
        self.api_key = api_key
        self.secret_key = secret_key

        # Binance USDT-M 선물 WebSocket URL
        self.ws_base_url = "wss://fstream.binance.com"
        self.ws_stream_url = f"{self.ws_base_url}/ws"
        self.ws_combined_url = f"{self.ws_base_url}/stream"

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.callbacks: Dict[str, Callable] = {}
        self.subscriptions: List[str] = []
        self.running = False
        self.ping_task: Optional[asyncio.Task] = None
        self.listen_key: Optional[str] = None

    def _generate_signature(self, params: dict) -> str:
        """HMAC SHA256 서명 생성"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _normalize_symbol(self, symbol: str) -> str:
        """심볼을 Binance WebSocket 형식으로 변환 (소문자)"""
        # ETH/USDT -> ethusdt, ETHUSDT -> ethusdt
        return symbol.replace('/', '').lower()

    async def connect(self, authenticate: bool = False) -> bool:
        """
        WebSocket 연결

        Args:
            authenticate: Private 스트림 사용 여부 (미구현, 향후 확장)
        """
        try:
            # Combined stream URL 사용 (여러 스트림 구독용)
            self.ws = await websockets.connect(
                self.ws_combined_url,
                ping_interval=20,
                ping_timeout=10
            )
            self.running = True
            logger.info(f"Connected to Binance WebSocket: {self.ws_combined_url}")

            # Ping 루프 시작 (Binance는 자체 ping/pong 처리하지만 안전을 위해)
            self.ping_task = asyncio.create_task(self._ping_loop())

            return True
        except Exception as e:
            logger.error(f"Binance WebSocket connection error: {e}")
            return False

    async def _ping_loop(self):
        """주기적 연결 상태 확인"""
        while self.running:
            try:
                await asyncio.sleep(30)  # 30초마다
                if self.ws and not self.ws.closed:
                    # Binance는 ping frame을 자동 처리
                    logger.debug("Binance WebSocket connection alive")
            except Exception as e:
                logger.error(f"Binance ping loop error: {e}")

    async def _subscribe(self, streams: List[str]):
        """스트림 구독"""
        if not self.ws or self.ws.closed:
            logger.error("WebSocket not connected")
            return

        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000)
        }

        await self.ws.send(json.dumps(subscribe_message))
        self.subscriptions.extend(streams)
        logger.info(f"Subscribed to Binance streams: {streams}")

    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """
        Ticker 구독 (24hr Mini Ticker)

        Args:
            symbol: 심볼 (예: "ETHUSDT" 또는 "ETH/USDT")
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        stream = f"{normalized}@miniTicker"
        self.callbacks[stream] = callback

        await self._subscribe([stream])
        logger.info(f"Subscribed to Binance ticker: {symbol}")

    async def subscribe_ticker_full(self, symbol: str, callback: Callable):
        """
        Ticker 구독 (Full 24hr Ticker - 더 많은 정보)

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        stream = f"{normalized}@ticker"
        self.callbacks[stream] = callback

        await self._subscribe([stream])
        logger.info(f"Subscribed to Binance full ticker: {symbol}")

    async def subscribe_candle(self, symbol: str, timeframe: str, callback: Callable):
        """
        Candle(Kline) 구독

        Args:
            symbol: 심볼
            timeframe: 시간봉 (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        stream = f"{normalized}@kline_{timeframe}"
        self.callbacks[stream] = callback

        await self._subscribe([stream])
        logger.info(f"Subscribed to Binance candle: {symbol} {timeframe}")

    async def subscribe_trades(self, symbol: str, callback: Callable):
        """
        실시간 거래 내역 구독 (Aggregate Trade)

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        stream = f"{normalized}@aggTrade"
        self.callbacks[stream] = callback

        await self._subscribe([stream])
        logger.info(f"Subscribed to Binance trades: {symbol}")

    async def subscribe_orderbook(self, symbol: str, depth: str, callback: Callable):
        """
        호가창 구독

        Args:
            symbol: 심볼
            depth: 깊이 (5, 10, 20) 또는 업데이트 속도 (@100ms, @500ms)
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        # 예: ethusdt@depth5@100ms 또는 ethusdt@depth20
        if depth.isdigit():
            stream = f"{normalized}@depth{depth}"
        else:
            stream = f"{normalized}@depth{depth}"
        self.callbacks[stream] = callback

        await self._subscribe([stream])
        logger.info(f"Subscribed to Binance orderbook: {symbol} depth={depth}")

    async def subscribe_mark_price(self, symbol: str, callback: Callable):
        """
        마크 가격 구독 (1초 업데이트)

        Args:
            symbol: 심볼
            callback: 데이터 수신 콜백 함수
        """
        normalized = self._normalize_symbol(symbol)
        stream = f"{normalized}@markPrice@1s"
        self.callbacks[stream] = callback

        await self._subscribe([stream])
        logger.info(f"Subscribed to Binance mark price: {symbol}")

    async def _handle_message(self, message: str):
        """메시지 처리"""
        try:
            data = json.loads(message)

            # 구독 응답
            if 'result' in data and data.get('result') is None:
                logger.debug(f"Binance subscription confirmed: id={data.get('id')}")
                return

            # 에러 응답
            if 'error' in data:
                logger.error(f"Binance WebSocket error: {data['error']}")
                return

            # Combined stream 형식: {"stream": "ethusdt@ticker", "data": {...}}
            if 'stream' in data and 'data' in data:
                stream = data['stream']
                payload = data['data']

                if stream in self.callbacks:
                    # 데이터 정규화
                    normalized_data = self._normalize_data(stream, payload)
                    await self.callbacks[stream](normalized_data)
                else:
                    logger.debug(f"No callback for stream: {stream}")

        except json.JSONDecodeError as e:
            logger.error(f"Binance message decode error: {e}, message: {message}")
        except Exception as e:
            logger.error(f"Binance message handling error: {e}")

    def _normalize_data(self, stream: str, data: dict) -> dict:
        """데이터를 공통 형식으로 정규화"""
        # Mini Ticker
        if '@miniTicker' in stream:
            return {
                'type': 'ticker',
                'symbol': data.get('s'),
                'last': float(data.get('c', 0)),
                'open': float(data.get('o', 0)),
                'high': float(data.get('h', 0)),
                'low': float(data.get('l', 0)),
                'volume': float(data.get('v', 0)),
                'quote_volume': float(data.get('q', 0)),
                'timestamp': data.get('E', 0)
            }

        # Full Ticker
        if '@ticker' in stream and '@miniTicker' not in stream:
            return {
                'type': 'ticker_full',
                'symbol': data.get('s'),
                'last': float(data.get('c', 0)),
                'bid': float(data.get('b', 0)),
                'ask': float(data.get('a', 0)),
                'high': float(data.get('h', 0)),
                'low': float(data.get('l', 0)),
                'volume': float(data.get('v', 0)),
                'price_change': float(data.get('p', 0)),
                'price_change_percent': float(data.get('P', 0)),
                'timestamp': data.get('E', 0)
            }

        # Kline/Candle
        if '@kline_' in stream:
            k = data.get('k', {})
            return {
                'type': 'candle',
                'symbol': k.get('s'),
                'timeframe': k.get('i'),
                'timestamp': k.get('t'),
                'open': float(k.get('o', 0)),
                'high': float(k.get('h', 0)),
                'low': float(k.get('l', 0)),
                'close': float(k.get('c', 0)),
                'volume': float(k.get('v', 0)),
                'is_closed': k.get('x', False)
            }

        # Aggregate Trade
        if '@aggTrade' in stream:
            return {
                'type': 'trade',
                'symbol': data.get('s'),
                'price': float(data.get('p', 0)),
                'quantity': float(data.get('q', 0)),
                'side': 'sell' if data.get('m') else 'buy',  # m=True means buyer is maker
                'timestamp': data.get('T', 0)
            }

        # Mark Price
        if '@markPrice' in stream:
            return {
                'type': 'mark_price',
                'symbol': data.get('s'),
                'mark_price': float(data.get('p', 0)),
                'index_price': float(data.get('i', 0)),
                'funding_rate': float(data.get('r', 0)),
                'next_funding_time': data.get('T', 0),
                'timestamp': data.get('E', 0)
            }

        # Orderbook depth
        if '@depth' in stream:
            return {
                'type': 'orderbook',
                'symbol': data.get('s'),
                'bids': [[float(p), float(q)] for p, q in data.get('b', [])],
                'asks': [[float(p), float(q)] for p, q in data.get('a', [])],
                'timestamp': data.get('E', 0)
            }

        # 기본 반환
        return data

    async def listen(self):
        """메시지 수신 루프"""
        try:
            while self.running:
                if self.ws and not self.ws.closed:
                    message = await self.ws.recv()
                    await self._handle_message(message)
                else:
                    logger.warning("Binance WebSocket closed, attempting reconnect...")
                    await self._reconnect()
                    await asyncio.sleep(5)
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Binance WebSocket connection closed: {e}")
            if self.running:
                await self._reconnect()
        except Exception as e:
            logger.error(f"Binance listen error: {e}")
            self.running = False

    async def _reconnect(self):
        """재연결 로직"""
        max_retries = 5
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                logger.info(f"Binance WebSocket reconnection attempt {attempt + 1}/{max_retries}")
                await self.connect()

                # 기존 구독 복원
                if self.subscriptions:
                    await self._subscribe(self.subscriptions.copy())

                logger.info("Binance WebSocket reconnected successfully")
                return
            except Exception as e:
                logger.error(f"Reconnection failed: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 60)  # 최대 60초

        logger.error("Max reconnection attempts reached")
        self.running = False

    async def unsubscribe(self, streams: List[str]):
        """스트림 구독 해제"""
        if not self.ws or self.ws.closed:
            return

        unsubscribe_message = {
            "method": "UNSUBSCRIBE",
            "params": streams,
            "id": int(time.time() * 1000)
        }

        await self.ws.send(json.dumps(unsubscribe_message))

        for stream in streams:
            if stream in self.subscriptions:
                self.subscriptions.remove(stream)
            if stream in self.callbacks:
                del self.callbacks[stream]

        logger.info(f"Unsubscribed from Binance streams: {streams}")

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
            logger.info("Binance WebSocket closed")


# 전역 WebSocket 데이터 수집기 함수
async def binance_ws_collector(market_queue: asyncio.Queue, symbols: List[str] = None):
    """
    Binance WebSocket 데이터 수집기

    Args:
        market_queue: 시장 데이터를 전달할 큐
        symbols: 구독할 심볼 리스트 (기본: ["BTCUSDT", "ETHUSDT"])
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT"]

    ws_client = BinanceWebSocket()

    async def ticker_callback(data):
        """Ticker 데이터 처리"""
        await market_queue.put({
            'type': 'ticker',
            'exchange': 'binance',
            'symbol': data.get('symbol'),
            'data': data
        })

    async def candle_callback(data):
        """Candle 데이터 처리"""
        await market_queue.put({
            'type': 'candle',
            'exchange': 'binance',
            'symbol': data.get('symbol'),
            'data': data
        })

    try:
        connected = await ws_client.connect()
        if not connected:
            logger.error("Failed to connect to Binance WebSocket")
            return

        # 각 심볼에 대해 Ticker와 1분봉 구독
        for symbol in symbols:
            await ws_client.subscribe_ticker(symbol, ticker_callback)
            await ws_client.subscribe_candle(symbol, "1m", candle_callback)
            await asyncio.sleep(0.1)  # Rate limit 방지

        # 메시지 수신 시작
        await ws_client.listen()

    except Exception as e:
        logger.error(f"Binance WebSocket collector error: {e}")
    finally:
        await ws_client.close()
