"""
Bitget WebSocket Client
실시간 가격, 포지션, 잔고 데이터 수신
"""
import asyncio
import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Callable, Dict, Optional

import websockets

logger = logging.getLogger(__name__)


class BitgetWebSocket:
    """Bitget WebSocket 클라이언트"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase

        # WebSocket URLs
        self.public_url = "wss://ws.bitget.com/v2/ws/public"
        self.private_url = "wss://ws.bitget.com/v2/ws/private"

        # WebSocket 연결
        self.public_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.private_ws: Optional[websockets.WebSocketClientProtocol] = None

        # 콜백 함수들
        self.ticker_callback: Optional[Callable] = None
        self.position_callback: Optional[Callable] = None
        self.balance_callback: Optional[Callable] = None
        self.order_callback: Optional[Callable] = None

        # 상태 관리
        self.is_running = False
        self.is_public_connected = False
        self.is_private_connected = False
        self.last_message_time = None
        self.message_count = 0
        self.error_count = 0

        # 백그라운드 작업 추적 (리소스 관리)
        self.background_tasks: list[asyncio.Task] = []

        # 구독 채널
        self.subscribed_symbols = set()

    def _generate_signature(self, timestamp: str, method: str = "GET", request_path: str = "/user/verify") -> str:
        """인증 서명 생성"""
        message = timestamp + method + request_path
        mac = hmac.new(
            bytes(self.api_secret, encoding="utf8"),
            bytes(message, encoding="utf-8"),
            digestmod=hashlib.sha256,
        )
        return base64.b64encode(mac.digest()).decode()

    async def _login(self, ws: websockets.WebSocketClientProtocol):
        """Private WebSocket 로그인"""
        if not all([self.api_key, self.api_secret, self.passphrase]):
            logger.warning("API credentials not provided, skipping private login")
            return

        timestamp = str(int(time.time()))
        sign = self._generate_signature(timestamp)

        login_msg = {
            "op": "login",
            "args": [
                {
                    "apiKey": self.api_key,
                    "passphrase": self.passphrase,
                    "timestamp": timestamp,
                    "sign": sign,
                }
            ],
        }

        await ws.send(json.dumps(login_msg))
        logger.info("Private WebSocket login request sent")

    async def connect_public(self):
        """Public WebSocket 연결"""
        try:
            self.public_ws = await websockets.connect(self.public_url)
            self.is_public_connected = True
            logger.info(f"✅ Public WebSocket connected: {self.public_url}")

            # Ping-Pong 설정 (태스크 추적)
            ping_task = asyncio.create_task(self._ping_loop(self.public_ws, "public"))
            self.background_tasks.append(ping_task)

        except Exception as e:
            logger.error(f"❌ Public WebSocket connection failed: {e}")
            self.is_public_connected = False
            raise

    async def connect_private(self):
        """Private WebSocket 연결 (인증 필요)"""
        try:
            self.private_ws = await websockets.connect(self.private_url)
            self.is_private_connected = True
            logger.info(f"✅ Private WebSocket connected: {self.private_url}")

            # 로그인
            await self._login(self.private_ws)

            # Ping-Pong 설정 (태스크 추적)
            ping_task = asyncio.create_task(self._ping_loop(self.private_ws, "private"))
            self.background_tasks.append(ping_task)

        except Exception as e:
            logger.error(f"❌ Private WebSocket connection failed: {e}")
            self.is_private_connected = False
            raise

    async def _ping_loop(self, ws: websockets.WebSocketClientProtocol, ws_type: str):
        """Ping 메시지 전송 (30초마다)"""
        while self.is_running:
            try:
                await asyncio.sleep(30)
                if ws and not ws.closed:
                    await ws.send("ping")
                    logger.debug(f"📡 Sent ping to {ws_type} WebSocket")
            except Exception as e:
                logger.error(f"Ping failed for {ws_type}: {e}")
                break

    async def subscribe_ticker(self, symbol: str):
        """
        실시간 가격 구독 (Ticker)

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
        """
        if not self.public_ws or self.public_ws.closed:
            logger.error("Public WebSocket not connected")
            return

        subscribe_msg = {
            "op": "subscribe",
            "args": [{"instType": "USDT-FUTURES", "channel": "ticker", "instId": symbol}],
        }

        await self.public_ws.send(json.dumps(subscribe_msg))
        self.subscribed_symbols.add(symbol)
        logger.info(f"📊 Subscribed to ticker: {symbol}")

    async def subscribe_positions(self, inst_type: str = "USDT-FUTURES"):
        """
        실시간 포지션 구독

        Args:
            inst_type: 상품 타입 (USDT-FUTURES, COIN-FUTURES 등)
        """
        if not self.private_ws or self.private_ws.closed:
            logger.error("Private WebSocket not connected")
            return

        subscribe_msg = {
            "op": "subscribe",
            "args": [{"instType": inst_type, "channel": "positions", "instId": "default"}],
        }

        await self.private_ws.send(json.dumps(subscribe_msg))
        logger.info(f"📈 Subscribed to positions: {inst_type}")

    async def subscribe_balance(self):
        """실시간 잔고 구독"""
        if not self.private_ws or self.private_ws.closed:
            logger.error("Private WebSocket not connected")
            return

        subscribe_msg = {
            "op": "subscribe",
            "args": [{"instType": "USDT-FUTURES", "channel": "account", "instId": "default"}],
        }

        await self.private_ws.send(json.dumps(subscribe_msg))
        logger.info("💰 Subscribed to balance updates")

    async def subscribe_orders(self, inst_type: str = "USDT-FUTURES"):
        """실시간 주문 업데이트 구독"""
        if not self.private_ws or self.private_ws.closed:
            logger.error("Private WebSocket not connected")
            return

        subscribe_msg = {
            "op": "subscribe",
            "args": [{"instType": inst_type, "channel": "orders", "instId": "default"}],
        }

        await self.private_ws.send(json.dumps(subscribe_msg))
        logger.info("📋 Subscribed to order updates")

    def _handle_ticker_message(self, data: Dict[str, Any]):
        """Ticker 메시지 처리"""
        try:
            if "data" in data and len(data["data"]) > 0:
                ticker = data["data"][0]

                parsed = {
                    "symbol": ticker.get("instId"),
                    "last_price": float(ticker.get("last", 0)),
                    "bid_price": float(ticker.get("bidPr", 0)),
                    "ask_price": float(ticker.get("askPr", 0)),
                    "high_24h": float(ticker.get("high24h", 0)),
                    "low_24h": float(ticker.get("low24h", 0)),
                    "volume_24h": float(ticker.get("baseVolume", 0)),
                    "change_24h": float(ticker.get("change24h", 0)),
                    "timestamp": ticker.get("ts"),
                }

                if self.ticker_callback:
                    self.ticker_callback(parsed)

        except Exception as e:
            logger.error(f"Ticker message parsing error: {e}")
            self.error_count += 1

    def _handle_position_message(self, data: Dict[str, Any]):
        """포지션 메시지 처리"""
        try:
            if "data" in data and len(data["data"]) > 0:
                positions = data["data"]

                parsed_positions = []
                for pos in positions:
                    parsed_positions.append({
                        "symbol": pos.get("instId"),
                        "side": pos.get("posSide"),  # long / short
                        "size": float(pos.get("total", 0)),
                        "available": float(pos.get("available", 0)),
                        "avg_price": float(pos.get("averageOpenPrice", 0)),
                        "unrealized_pnl": float(pos.get("unrealizedPL", 0)),
                        "leverage": float(pos.get("leverage", 0)),
                        "margin": float(pos.get("margin", 0)),
                        "liquidation_price": float(pos.get("liqPr", 0)),
                        "timestamp": pos.get("cTime"),
                    })

                if self.position_callback:
                    self.position_callback(parsed_positions)

        except Exception as e:
            logger.error(f"Position message parsing error: {e}")
            self.error_count += 1

    def _handle_balance_message(self, data: Dict[str, Any]):
        """잔고 메시지 처리"""
        try:
            if "data" in data and len(data["data"]) > 0:
                account = data["data"][0]

                parsed = {
                    "total_equity": float(account.get("equity", 0)),
                    "available_balance": float(account.get("available", 0)),
                    "unrealized_pnl": float(account.get("unrealizedPL", 0)),
                    "margin_used": float(account.get("locked", 0)),
                    "margin_ratio": float(account.get("marginRatio", 0)),
                    "timestamp": account.get("uTime"),
                }

                if self.balance_callback:
                    self.balance_callback(parsed)

        except Exception as e:
            logger.error(f"Balance message parsing error: {e}")
            self.error_count += 1

    def _handle_order_message(self, data: Dict[str, Any]):
        """주문 메시지 처리"""
        try:
            if "data" in data and len(data["data"]) > 0:
                orders = data["data"]

                parsed_orders = []
                for order in orders:
                    parsed_orders.append({
                        "order_id": order.get("ordId"),
                        "client_order_id": order.get("clOrdId"),
                        "symbol": order.get("instId"),
                        "side": order.get("side"),  # buy / sell
                        "order_type": order.get("ordType"),  # limit / market
                        "price": float(order.get("px", 0)),
                        "size": float(order.get("sz", 0)),
                        "filled_size": float(order.get("accFillSz", 0)),
                        "status": order.get("status"),  # new / partial-fill / full-fill / canceled
                        "timestamp": order.get("cTime"),
                    })

                if self.order_callback:
                    self.order_callback(parsed_orders)

        except Exception as e:
            logger.error(f"Order message parsing error: {e}")
            self.error_count += 1

    async def _process_public_messages(self):
        """Public WebSocket 메시지 처리"""
        try:
            async for message in self.public_ws:
                if message == "pong":
                    logger.debug("Received pong from public WebSocket")
                    continue

                try:
                    data = json.loads(message)
                    self.last_message_time = time.time()
                    self.message_count += 1

                    # 이벤트 타입별 처리
                    event = data.get("event")
                    if event == "subscribe":
                        logger.info(f"Subscription confirmed: {data.get('arg')}")
                    elif event == "error":
                        logger.error(f"WebSocket error: {data}")
                        self.error_count += 1
                    elif "arg" in data and "channel" in data["arg"]:
                        channel = data["arg"]["channel"]

                        if channel == "ticker":
                            self._handle_ticker_message(data)

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {message}")
                    self.error_count += 1

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Public WebSocket connection closed")
            self.is_public_connected = False
        except Exception as e:
            logger.error(f"Public WebSocket error: {e}")
            self.is_public_connected = False
            self.error_count += 1

    async def _process_private_messages(self):
        """Private WebSocket 메시지 처리"""
        try:
            async for message in self.private_ws:
                if message == "pong":
                    logger.debug("Received pong from private WebSocket")
                    continue

                try:
                    data = json.loads(message)
                    self.last_message_time = time.time()
                    self.message_count += 1

                    # 로그인 응답
                    if data.get("event") == "login":
                        if data.get("code") == "0":
                            logger.info("✅ Private WebSocket login successful")
                        else:
                            logger.error(f"❌ Private WebSocket login failed: {data}")
                            self.error_count += 1
                        continue

                    # 구독 확인
                    if data.get("event") == "subscribe":
                        logger.info(f"Private subscription confirmed: {data.get('arg')}")
                        continue

                    # 에러 처리
                    if data.get("event") == "error":
                        logger.error(f"Private WebSocket error: {data}")
                        self.error_count += 1
                        continue

                    # 데이터 처리
                    if "arg" in data and "channel" in data["arg"]:
                        channel = data["arg"]["channel"]

                        if channel == "positions":
                            self._handle_position_message(data)
                        elif channel == "account":
                            self._handle_balance_message(data)
                        elif channel == "orders":
                            self._handle_order_message(data)

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {message}")
                    self.error_count += 1

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Private WebSocket connection closed")
            self.is_private_connected = False
        except Exception as e:
            logger.error(f"Private WebSocket error: {e}")
            self.is_private_connected = False
            self.error_count += 1

    async def start(self):
        """WebSocket 시작"""
        self.is_running = True
        logger.info("🚀 Starting Bitget WebSocket client...")

        try:
            # Public WebSocket 연결
            await self.connect_public()

            # Private WebSocket 연결 (API 키가 있는 경우)
            if all([self.api_key, self.api_secret, self.passphrase]):
                await self.connect_private()

            # 메시지 처리 시작
            tasks = [self._process_public_messages()]

            if self.private_ws:
                tasks.append(self._process_private_messages())

            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"WebSocket start error: {e}")
            self.is_running = False
            raise

    async def stop(self):
        """WebSocket 중지 및 리소스 정리"""
        logger.info("🛑 Stopping Bitget WebSocket client...")
        self.is_running = False

        # 1. 모든 백그라운드 태스크 취소 (즉시 정리)
        logger.info(f"Cancelling {len(self.background_tasks)} background tasks...")
        for task in self.background_tasks:
            if not task.done():
                task.cancel()

        # 2. 태스크 취소 대기 (예외 무시)
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            logger.info("All background tasks cancelled")

        # 3. WebSocket 연결 종료
        if self.public_ws and not self.public_ws.closed:
            await self.public_ws.close()
            logger.info("Public WebSocket closed")

        if self.private_ws and not self.private_ws.closed:
            await self.private_ws.close()
            logger.info("Private WebSocket closed")

        # 4. 태스크 목록 초기화
        self.background_tasks.clear()

    def get_status(self) -> Dict[str, Any]:
        """WebSocket 상태 조회"""
        return {
            "is_running": self.is_running,
            "is_public_connected": self.is_public_connected,
            "is_private_connected": self.is_private_connected,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "last_message_time": self.last_message_time,
            "last_message_ago": time.time() - self.last_message_time if self.last_message_time else None,
            "subscribed_symbols": list(self.subscribed_symbols),
        }


# 싱글톤 인스턴스
_ws_client: Optional[BitgetWebSocket] = None


def get_bitget_ws(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    passphrase: Optional[str] = None,
) -> BitgetWebSocket:
    """Bitget WebSocket 클라이언트 인스턴스 반환"""
    global _ws_client

    if _ws_client is None:
        _ws_client = BitgetWebSocket(api_key, api_secret, passphrase)

    return _ws_client
