"""
실시간 로그 브로드캐스터
봇 실행 로그를 WebSocket을 통해 프론트엔드로 전송
"""
import logging
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


class LogBroadcastHandler(logging.Handler):
    """
    로그를 WebSocket으로 브로드캐스트하는 커스텀 로그 핸들러
    사용자별로 로그를 필터링하여 전송
    """

    def __init__(self, user_id: int, max_logs: int = 500):
        super().__init__()
        self.user_id = user_id
        self.log_buffer = deque(maxlen=max_logs)  # 최근 500개 로그만 유지
        self._ws_broadcast = None

    def set_broadcast_function(self, broadcast_fn):
        """WebSocket 브로드캐스트 함수 설정"""
        self._ws_broadcast = broadcast_fn

    def emit(self, record: logging.LogRecord):
        """로그 레코드를 WebSocket으로 전송"""
        try:
            # 로그 포맷팅
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }

            # 버퍼에 저장
            self.log_buffer.append(log_entry)

            # WebSocket으로 실시간 전송
            if self._ws_broadcast:
                import asyncio
                try:
                    # 이벤트 루프가 있는 경우에만 전송
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._send_log(log_entry))
                except RuntimeError:
                    # 이벤트 루프가 없으면 무시 (테스트 환경 등)
                    pass

        except Exception as e:
            # 로그 핸들러 자체 에러는 무시 (무한 루프 방지)
            print(f"LogBroadcastHandler error: {e}")

    async def _send_log(self, log_entry: dict):
        """비동기로 로그 전송"""
        try:
            await self._ws_broadcast(
                self.user_id,
                {
                    "type": "bot_log",
                    "data": log_entry,
                }
            )
        except Exception:
            # Silently ignore errors to prevent infinite loops
            pass

    def get_recent_logs(self, limit: int = 100):
        """최근 로그 가져오기"""
        return list(self.log_buffer)[-limit:]


# 사용자별 로그 핸들러 저장
_user_log_handlers: dict[int, LogBroadcastHandler] = {}


def get_or_create_log_handler(user_id: int) -> LogBroadcastHandler:
    """사용자별 로그 핸들러 가져오기 또는 생성"""
    if user_id not in _user_log_handlers:
        handler = LogBroadcastHandler(user_id)

        # 포맷 설정
        formatter = logging.Formatter(
            fmt="%(message)s",  # 메시지만 (이미 구조화된 로그)
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        # 레벨 설정 (INFO 이상만)
        handler.setLevel(logging.INFO)

        _user_log_handlers[user_id] = handler

    return _user_log_handlers[user_id]


def attach_log_handler(user_id: int, logger_name: str = None):
    """특정 로거에 로그 핸들러 추가"""
    logger.info(f"🎧 Attaching log handler for user {user_id}")
    handler = get_or_create_log_handler(user_id)

    # WebSocket 브로드캐스트 함수 설정
    from ..websockets.ws_server import broadcast_to_user
    handler.set_broadcast_function(broadcast_to_user)
    logger.info(f"📡 Broadcast function set for user {user_id}")

    # 여러 로거에 핸들러 추가
    loggers_to_attach = []

    if logger_name:
        loggers_to_attach.append(logging.getLogger(logger_name))
    else:
        # 봇 관련 모든 로거에 추가
        loggers_to_attach.extend([
            logging.getLogger("src.services.bot_runner"),
            logging.getLogger("src.services.strategy_loader"),
            logging.getLogger("src.strategies.dynamic_strategy_executor"),
            logging.getLogger("src.services.bitget_rest"),
        ])

    # 중복 방지하며 핸들러 추가
    for target_logger in loggers_to_attach:
        if handler not in target_logger.handlers:
            target_logger.addHandler(handler)
            logger.info(f"✅ Added handler to logger: {target_logger.name}")
        else:
            logger.info(f"⚠️  Handler already attached to logger: {target_logger.name}")

    return handler


def detach_log_handler(user_id: int, logger_name: str = None):
    """로그 핸들러 제거"""
    if user_id not in _user_log_handlers:
        return

    handler = _user_log_handlers[user_id]

    # 여러 로거에서 핸들러 제거
    loggers_to_detach = []

    if logger_name:
        loggers_to_detach.append(logging.getLogger(logger_name))
    else:
        loggers_to_detach.extend([
            logging.getLogger("src.services.bot_runner"),
            logging.getLogger("src.services.strategy_loader"),
            logging.getLogger("src.strategies.dynamic_strategy_executor"),
            logging.getLogger("src.services.bitget_rest"),
        ])

    for logger in loggers_to_detach:
        if handler in logger.handlers:
            logger.removeHandler(handler)


def get_recent_logs(user_id: int, limit: int = 100) -> list[dict]:
    """사용자의 최근 로그 가져오기"""
    if user_id not in _user_log_handlers:
        return []

    handler = _user_log_handlers[user_id]
    return handler.get_recent_logs(limit)
