"""
Bitget WebSocket 데이터 수집기

실시간 시세 데이터를 수집하여 candle_generator와 market_queue에 전달
"""

import asyncio
import json
import logging
from typing import Optional

import websockets

logger = logging.getLogger(__name__)


class BitgetWebSocketCollector:
    """Bitget WebSocket 실시간 데이터 수집"""

    def __init__(self, market_queue: asyncio.Queue):
        self.market_queue = market_queue
        self.ws_url = "wss://ws.bitget.com/mix/v1/stream"
        self.symbols = ["BTCUSDT", "ETHUSDT"]  # 기본 구독 심볼
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False

    async def connect(self):
        """WebSocket 연결"""
        try:
            import ssl

            # SSL 인증서 검증 활성화 (보안 강화)
            ssl_context = ssl.create_default_context()

            self.websocket = await websockets.connect(self.ws_url, ssl=ssl_context)
            logger.info(f"✅ Bitget WebSocket 연결 성공: {self.ws_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Bitget WebSocket 연결 실패: {e}")
            return False

    async def subscribe_symbols(self):
        """심볼 구독"""
        if not self.websocket:
            logger.error("WebSocket이 연결되지 않음")
            return

        for symbol in self.symbols:
            # Bitget swap 형식: BTCUSDT_UMCBL
            bitget_symbol = f"{symbol}_UMCBL"

            # Ticker 구독
            subscribe_msg = {
                "op": "subscribe",
                "args": [
                    {
                        "instType": "mc",  # Mixed Contract (USDT-M)
                        "channel": "ticker",
                        "instId": bitget_symbol
                    }
                ]
            }

            try:
                await self.websocket.send(json.dumps(subscribe_msg))
                logger.info(f"📡 {symbol} ticker 구독 요청")
            except Exception as e:
                logger.error(f"❌ {symbol} 구독 실패: {e}")

    async def process_message(self, message: dict):
        """WebSocket 메시지 처리"""
        try:
            # Ticker 데이터 처리
            if message.get("action") == "snapshot" or message.get("action") == "update":
                data = message.get("data", [])
                if data:
                    ticker_data = data[0]
                    inst_id = ticker_data.get("instId", "")

                    # BTCUSDT_UMCBL -> BTCUSDT 변환
                    symbol = inst_id.replace("_UMCBL", "")

                    # Market data 생성
                    market_data = {
                        "symbol": symbol,
                        "price": float(ticker_data.get("last", 0)),
                        "volume": float(ticker_data.get("baseVolume", 0)),
                        "timestamp": int(ticker_data.get("ts", 0)) / 1000,  # ms to seconds
                        "high": float(ticker_data.get("high24h", 0)),
                        "low": float(ticker_data.get("low24h", 0)),
                        "open": float(ticker_data.get("open24h", 0)),
                    }

                    # Market queue에 전달
                    try:
                        self.market_queue.put_nowait(market_data)
                        logger.debug(f"✅ Market data queued: {symbol} @ ${market_data['price']}")
                    except asyncio.QueueFull:
                        logger.warning("⚠️ Market queue full, removing old data")
                        try:
                            self.market_queue.get_nowait()
                            self.market_queue.put_nowait(market_data)
                            logger.debug(f"✅ Market data queued after cleanup: {symbol}")
                        except Exception:
                            pass

        except Exception as e:
            logger.error(f"메시지 처리 에러: {e}")

    async def listen(self):
        """WebSocket 메시지 수신"""
        if not self.websocket:
            logger.error("WebSocket이 연결되지 않음")
            return

        self.is_running = True

        try:
            async for message in self.websocket:
                if not self.is_running:
                    break

                try:
                    data = json.loads(message)

                    # Pong 응답
                    if data.get("event") == "ping":
                        await self.websocket.send(json.dumps({"event": "pong"}))
                        continue

                    # 구독 확인
                    if data.get("event") == "subscribe":
                        logger.info(f"✅ 구독 확인: {data}")
                        continue

                    # 데이터 처리
                    await self.process_message(data)

                except json.JSONDecodeError:
                    logger.warning(f"JSON 파싱 실패: {message}")
                except Exception as e:
                    logger.error(f"메시지 처리 에러: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ WebSocket 연결 종료")
        except Exception as e:
            logger.error(f"❌ WebSocket listen 에러: {e}")
        finally:
            self.is_running = False

    async def start(self):
        """WebSocket 시작"""
        while True:
            try:
                logger.info("🚀 Bitget WebSocket 시작...")

                # 연결
                if not await self.connect():
                    await asyncio.sleep(5)
                    continue

                # 구독
                await self.subscribe_symbols()

                # 수신 시작
                await self.listen()

            except Exception as e:
                logger.error(f"❌ WebSocket 에러: {e}")

            finally:
                # 재연결 대기
                logger.info("⏳ 5초 후 재연결...")
                await asyncio.sleep(5)

    async def stop(self):
        """WebSocket 중지"""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
            logger.info("✅ Bitget WebSocket 종료")


async def bitget_ws_collector(market_queue: asyncio.Queue):
    """
    Bitget WebSocket 데이터 수집기 시작

    Args:
        market_queue: 시세 데이터를 전달할 큐
    """
    collector = BitgetWebSocketCollector(market_queue)
    await collector.start()
