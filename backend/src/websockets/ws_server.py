import asyncio
import logging
from typing import Dict, List, Set, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..utils.jwt_auth import JWTAuth
from ..database.db import AsyncSessionLocal
from ..services.exchange_service import ExchangeService

logger = logging.getLogger(__name__)

router = APIRouter()


@dataclass
class ConnectionState:
    """WebSocket 연결 상태 추적"""
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: Optional[datetime] = None
    last_pong: Optional[datetime] = None
    message_count: int = 0
    error_count: int = 0
    is_alive: bool = True


# 연결된 WebSocket 관리 (개선됨)
connections: Dict[int, List[ConnectionState]] = {}
send_lock = asyncio.Lock()

# 구독 관리
subscriptions: Dict[int, Set[str]] = {}  # user_id -> {channels}

# 연결 상태 모니터링 설정
HEARTBEAT_INTERVAL = 30  # 30초마다 ping 전송
HEARTBEAT_TIMEOUT = 60  # 60초 동안 응답 없으면 연결 종료
MAX_ERROR_COUNT = 5  # 최대 에러 횟수


# 모듈 레벨 함수 (하위 호환성)
async def broadcast_to_user(user_id: int, data: dict):
    """특정 사용자에게 메시지 전송 (모듈 레벨 함수)"""
    return await WebSocketManager.broadcast_to_user(user_id, data)


async def broadcast_to_all(data: dict):
    """모든 사용자에게 메시지 전송 (모듈 레벨 함수)"""
    return await WebSocketManager.broadcast_to_all(data)


async def connection_health_monitor():
    """
    주기적으로 연결 상태를 체크하고 죽은 연결을 제거
    애플리케이션 시작 시 백그라운드로 실행
    """
    while True:
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            current_time = datetime.utcnow()
            dead_connections = []

            async with send_lock:
                for user_id, conn_states in list(connections.items()):
                    for conn_state in conn_states[:]:  # 복사본으로 순회
                        # Heartbeat 타임아웃 체크
                        if conn_state.last_ping:
                            time_since_ping = (current_time - conn_state.last_ping).total_seconds()
                            if time_since_ping > HEARTBEAT_TIMEOUT:
                                logger.warning(
                                    f"Connection timeout for user {user_id} "
                                    f"(last ping: {time_since_ping:.1f}s ago)"
                                )
                                conn_state.is_alive = False
                                dead_connections.append((user_id, conn_state))

                        # 에러 횟수 체크
                        if conn_state.error_count >= MAX_ERROR_COUNT:
                            logger.warning(
                                f"Too many errors for user {user_id} connection "
                                f"(error count: {conn_state.error_count})"
                            )
                            conn_state.is_alive = False
                            dead_connections.append((user_id, conn_state))

            # 죽은 연결 제거
            for user_id, conn_state in dead_connections:
                try:
                    await conn_state.websocket.close(
                        code=status.WS_1001_GOING_AWAY,
                        reason="Connection timeout or too many errors"
                    )
                    if conn_state in connections.get(user_id, []):
                        connections[user_id].remove(conn_state)
                        if not connections[user_id]:
                            connections.pop(user_id, None)
                            subscriptions.pop(user_id, None)
                except Exception as e:
                    logger.error(f"Error closing dead connection for user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Error in connection health monitor: {e}")


class WebSocketManager:
    """WebSocket 연결 및 메시지 브로드캐스트 관리 (개선됨)"""

    @staticmethod
    async def broadcast_to_user(user_id: int, data: dict):
        """특정 사용자에게 메시지 전송 (에러 처리 강화)"""
        async with send_lock:
            conn_states = connections.get(user_id, [])
            for conn_state in conn_states[:]:  # 복사본으로 순회
                if not conn_state.is_alive:
                    continue

                try:
                    await conn_state.websocket.send_json(data)
                    conn_state.message_count += 1
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected while sending to user {user_id}")
                    conn_state.is_alive = False
                    conn_states.remove(conn_state)
                except Exception as e:
                    logger.error(f"Failed to send to user {user_id}: {e}")
                    conn_state.error_count += 1
                    if conn_state.error_count >= MAX_ERROR_COUNT:
                        conn_state.is_alive = False
                        conn_states.remove(conn_state)

    @staticmethod
    async def broadcast_to_all(data: dict):
        """모든 연결된 사용자에게 메시지 전송 (에러 처리 강화)"""
        async with send_lock:
            for user_id, conn_states in list(connections.items()):
                for conn_state in conn_states[:]:  # 복사본으로 순회
                    if not conn_state.is_alive:
                        continue

                    try:
                        await conn_state.websocket.send_json(data)
                        conn_state.message_count += 1
                    except WebSocketDisconnect:
                        logger.info(f"WebSocket disconnected while broadcasting to user {user_id}")
                        conn_state.is_alive = False
                        conn_states.remove(conn_state)
                    except Exception as e:
                        logger.error(f"Failed to broadcast to user {user_id}: {e}")
                        conn_state.error_count += 1

    @staticmethod
    async def send_price_update(
        user_id: int, symbol: str, price: float, timestamp: str
    ):
        """가격 업데이트 전송"""
        if "price" in subscriptions.get(user_id, set()):
            await WebSocketManager.broadcast_to_user(
                user_id,
                {
                    "type": "price_update",
                    "symbol": symbol,
                    "price": price,
                    "timestamp": timestamp,
                },
            )

    @staticmethod
    async def send_position_update(user_id: int, position_data: dict):
        """포지션 변경 알림"""
        if "position" in subscriptions.get(user_id, set()):
            await WebSocketManager.broadcast_to_user(
                user_id,
                {
                    "type": "position_update",
                    "data": position_data,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )

    @staticmethod
    async def send_order_update(user_id: int, order_data: dict):
        """주문 상태 업데이트"""
        if "order" in subscriptions.get(user_id, set()):
            await WebSocketManager.broadcast_to_user(
                user_id,
                {
                    "type": "order_update",
                    "data": order_data,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )

    @staticmethod
    async def send_balance_update(user_id: int, balance_data: dict):
        """잔고 업데이트"""
        if "balance" in subscriptions.get(user_id, set()):
            await WebSocketManager.broadcast_to_user(
                user_id,
                {
                    "type": "balance_update",
                    "data": balance_data,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )

    @staticmethod
    async def send_alert(user_id: int, level: str, message: str):
        """시스템 알림 전송"""
        await WebSocketManager.broadcast_to_user(
            user_id,
            {
                "type": "alert",
                "level": level,
                "message": message,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        )

    @staticmethod
    async def send_grid_order_update(user_id: int, order_data: dict):
        """그리드 주문 상태 업데이트 (NEW - Grid Bot)"""
        if "grid_order" in subscriptions.get(user_id, set()):
            await WebSocketManager.broadcast_to_user(
                user_id,
                {
                    "type": "grid_order_update",
                    "data": order_data,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )

    @staticmethod
    async def send_grid_cycle_complete(user_id: int, cycle_data: dict):
        """그리드 사이클 완료 알림 (매도 체결 시) (NEW - Grid Bot)"""
        if "grid_order" in subscriptions.get(user_id, set()):
            await WebSocketManager.broadcast_to_user(
                user_id,
                {
                    "type": "grid_cycle_complete",
                    "data": cycle_data,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )


async def heartbeat_sender(user_id: int, conn_state: ConnectionState):
    """
    자동 heartbeat 전송 (서버 -> 클라이언트 ping)
    클라이언트가 pong으로 응답하지 않으면 연결 종료
    """
    try:
        while user_id in connections and conn_state.is_alive:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            try:
                # Ping 전송
                await conn_state.websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
                conn_state.last_ping = datetime.utcnow()
                logger.debug(f"Sent ping to user {user_id}")

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected during heartbeat for user {user_id}")
                conn_state.is_alive = False
                break
            except Exception as e:
                logger.error(f"Heartbeat error for user {user_id}: {e}")
                conn_state.error_count += 1
                if conn_state.error_count >= MAX_ERROR_COUNT:
                    conn_state.is_alive = False
                    break

    except Exception as e:
        logger.error(f"Failed heartbeat sender for user {user_id}: {e}")


async def start_price_stream(user_id: int, symbols: List[str]):
    """실시간 가격 데이터 스트리밍 (백그라운드 태스크, 에러 복구 개선)"""
    error_count = 0
    max_retries = 3

    try:
        async with AsyncSessionLocal() as session:
            client, exchange_name = await ExchangeService.get_user_exchange_client(
                session, user_id
            )

            while user_id in connections and "price" in subscriptions.get(user_id, set()):
                try:
                    for symbol in symbols:
                        # Bitget API에서 현재 가격 조회
                        ticker = await client.fetch_ticker(symbol)
                        price = ticker.get("last", 0)

                        await WebSocketManager.send_price_update(
                            user_id, symbol, price, datetime.utcnow().isoformat() + "Z"
                        )

                    await asyncio.sleep(1)  # 1초마다 업데이트
                    error_count = 0  # 성공 시 에러 카운트 리셋

                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"Price stream error for user {user_id} (attempt {error_count}/{max_retries}): {e}"
                    )

                    if error_count >= max_retries:
                        logger.error(f"Price stream failed after {max_retries} retries for user {user_id}")
                        await WebSocketManager.send_alert(
                            user_id,
                            "ERROR",
                            "가격 스트리밍 연결이 실패했습니다. 잠시 후 다시 시도합니다."
                        )
                        await asyncio.sleep(30)  # 30초 대기 후 재시도
                        error_count = 0
                    else:
                        await asyncio.sleep(5)  # 에러 시 5초 대기

    except Exception as e:
        logger.error(f"Failed to start price stream for user {user_id}: {e}")
        await WebSocketManager.send_alert(
            user_id,
            "ERROR",
            "가격 스트리밍을 시작할 수 없습니다."
        )


async def start_position_monitor(user_id: int):
    """포지션 변경 모니터링 (백그라운드 태스크)"""
    try:
        async with AsyncSessionLocal() as session:
            client, exchange_name = await ExchangeService.get_user_exchange_client(
                session, user_id
            )
            previous_positions = {}

            while user_id in connections and "position" in subscriptions.get(
                user_id, set()
            ):
                try:
                    # 현재 포지션 조회
                    positions = await client.fetch_positions()

                    # 변경 감지
                    for pos in positions:
                        symbol = pos.get("symbol", "")
                        contracts = pos.get("contracts", 0)

                        if contracts == 0:
                            continue

                        # 새로운 포지션 또는 변경된 포지션
                        pos_key = f"{symbol}_{pos.get('side', '')}"
                        if (
                            pos_key not in previous_positions
                            or previous_positions[pos_key] != contracts
                        ):
                            await WebSocketManager.send_position_update(
                                user_id,
                                {
                                    "symbol": symbol,
                                    "side": pos.get("side", ""),
                                    "contracts": contracts,
                                    "entryPrice": pos.get("entryPrice", 0),
                                    "unrealizedPnl": pos.get("unrealizedPnl", 0),
                                },
                            )
                            previous_positions[pos_key] = contracts

                    await asyncio.sleep(2)  # 2초마다 체크

                except Exception as e:
                    logger.error(f"Position monitor error for user {user_id}: {e}")
                    await asyncio.sleep(5)

    except Exception as e:
        logger.error(f"Failed to start position monitor for user {user_id}: {e}")


async def start_balance_monitor(user_id: int):
    """잔고 변경 모니터링 (백그라운드 태스크)"""
    try:
        async with AsyncSessionLocal() as session:
            client, exchange_name = await ExchangeService.get_user_exchange_client(
                session, user_id
            )
            previous_balance = None

            while user_id in connections and "balance" in subscriptions.get(
                user_id, set()
            ):
                try:
                    # 잔고 조회
                    balance = await client.fetch_balance()
                    usdt_balance = balance.get("USDT", {})
                    current_total = float(usdt_balance.get("total", 0))

                    # 변경 감지 (0.01 USDT 이상 차이)
                    if (
                        previous_balance is None
                        or abs(current_total - previous_balance) > 0.01
                    ):
                        await WebSocketManager.send_balance_update(
                            user_id,
                            {
                                "total": current_total,
                                "free": float(usdt_balance.get("free", 0)),
                                "used": float(usdt_balance.get("used", 0)),
                            },
                        )
                        previous_balance = current_total

                    await asyncio.sleep(5)  # 5초마다 체크

                except Exception as e:
                    logger.error(f"Balance monitor error for user {user_id}: {e}")
                    await asyncio.sleep(10)

    except Exception as e:
        logger.error(f"Failed to start balance monitor for user {user_id}: {e}")


@router.websocket("/ws/user/{user_id}")
async def user_socket(websocket: WebSocket, user_id: int, token: str = Query(...)):
    """
    WebSocket 연결 엔드포인트 (JWT 인증 필요)

    클라이언트 메시지 형식:
    - {"action": "subscribe", "channels": ["price", "position", "order", "balance"]}
    - {"action": "unsubscribe", "channels": ["price"]}
    - {"action": "ping"}

    서버 메시지 형식:
    - {"type": "price_update", "symbol": "BTC/USDT", "price": 50000, "timestamp": "..."}
    - {"type": "position_update", "data": {...}, "timestamp": "..."}
    - {"type": "order_update", "data": {...}, "timestamp": "..."}
    - {"type": "balance_update", "data": {...}, "timestamp": "..."}
    - {"type": "alert", "level": "ERROR", "message": "...", "timestamp": "..."}
    """
    # JWT 토큰 검증
    try:
        payload = JWTAuth.decode_token(token)
        token_user_id = payload.get("user_id")

        if token_user_id != user_id:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="User ID mismatch"
            )
            return
    except Exception as e:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token"
        )
        return

    # WebSocket 연결 수락
    await websocket.accept()

    # ConnectionState 생성 및 등록
    conn_state = ConnectionState(websocket=websocket)
    connections.setdefault(user_id, []).append(conn_state)
    subscriptions.setdefault(user_id, set())

    # 백그라운드 태스크
    background_tasks = []

    # Heartbeat 태스크 시작
    heartbeat_task = asyncio.create_task(heartbeat_sender(user_id, conn_state))
    heartbeat_task.set_name(f"heartbeat_{user_id}")
    background_tasks.append(heartbeat_task)

    try:
        # 환영 메시지
        await websocket.send_json(
            {
                "type": "connected",
                "message": "WebSocket connected successfully",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )
        logger.info(f"WebSocket connected for user {user_id}")

        while True:
            try:
                # Receive and parse message
                message = await websocket.receive_text()

                # Skip empty messages
                if not message or message.strip() == "":
                    continue

                # Handle ping/pong keepalive (plain text)
                if message.strip().lower() == "ping":
                    await websocket.send_text("pong")
                    continue

                # Parse JSON
                import json
                try:
                    data = json.loads(message)
                except json.JSONDecodeError as e:
                    # Only log non-ping messages as warnings
                    if message.strip().lower() not in ["ping", "pong"]:
                        logger.warning(f"Invalid JSON from user {user_id}: {e}, message: {message[:100]}")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        })
                    continue

            except WebSocketDisconnect:
                # Client disconnected, break the loop
                break
            except Exception as e:
                logger.error(f"Error receiving WebSocket message for user {user_id}: {e}")
                # If it's a disconnect-related error, break the loop
                if "disconnect" in str(e).lower() or "cannot call" in str(e).lower():
                    break
                continue

            action = data.get("action", "")

            if action == "subscribe":
                channels = data.get("channels", [])
                subscriptions[user_id].update(channels)

                # 구독에 따라 백그라운드 태스크 시작
                if "price" in channels and not any(
                    t.get_name() == f"price_{user_id}" for t in background_tasks
                ):
                    symbols = data.get("symbols", ["BTC/USDT", "ETH/USDT"])
                    task = asyncio.create_task(start_price_stream(user_id, symbols))
                    task.set_name(f"price_{user_id}")
                    background_tasks.append(task)

                if "position" in channels and not any(
                    t.get_name() == f"position_{user_id}" for t in background_tasks
                ):
                    task = asyncio.create_task(start_position_monitor(user_id))
                    task.set_name(f"position_{user_id}")
                    background_tasks.append(task)

                if "balance" in channels and not any(
                    t.get_name() == f"balance_{user_id}" for t in background_tasks
                ):
                    task = asyncio.create_task(start_balance_monitor(user_id))
                    task.set_name(f"balance_{user_id}")
                    background_tasks.append(task)

                await websocket.send_json(
                    {
                        "type": "subscribed",
                        "channels": list(subscriptions[user_id]),
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                )

            elif action == "unsubscribe":
                channels = data.get("channels", [])
                subscriptions[user_id].difference_update(channels)

                await websocket.send_json(
                    {
                        "type": "unsubscribed",
                        "channels": channels,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                )

            elif action == "ping":
                await websocket.send_json(
                    {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                )

            elif action == "pong":
                # 클라이언트의 pong 응답 기록
                conn_state.last_pong = datetime.utcnow()
                logger.debug(f"Received pong from user {user_id}")

            elif action == "get_recent_logs":
                # 최근 로그 요청
                from ..utils.log_broadcaster import get_recent_logs
                limit = data.get("limit", 100)
                logs = get_recent_logs(user_id, limit)
                await websocket.send_json(
                    {
                        "type": "recent_logs",
                        "logs": logs,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # 정리
        conn_state.is_alive = False

        # ConnectionState 제거
        if user_id in connections and conn_state in connections[user_id]:
            connections[user_id].remove(conn_state)

        if not connections.get(user_id):
            connections.pop(user_id, None)
            subscriptions.pop(user_id, None)
            logger.info(f"All connections closed for user {user_id}")

        # 백그라운드 태스크 취소
        for task in background_tasks:
            try:
                task.cancel()
                await asyncio.sleep(0.1)  # 태스크 취소 완료 대기
            except Exception as e:
                logger.error(f"Error cancelling task {task.get_name()}: {e}")

        # 최종 통계 로그
        duration = (datetime.utcnow() - conn_state.connected_at).total_seconds()
        logger.info(
            f"Connection closed for user {user_id} - "
            f"Duration: {duration:.1f}s, Messages: {conn_state.message_count}, "
            f"Errors: {conn_state.error_count}"
        )


# 외부에서 사용할 수 있도록 export
ws_manager = WebSocketManager()
