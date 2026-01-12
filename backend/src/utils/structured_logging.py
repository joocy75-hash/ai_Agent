"""
구조화된 로깅 시스템
JSON 형식으로 로그를 출력하여 분석 및 모니터링을 용이하게 함
"""
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

# Request context를 저장하기 위한 ContextVar
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[int]] = ContextVar('user_id', default=None)


class StructuredLogger:
    """JSON 형식의 구조화된 로그를 제공하는 로거"""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name

    def _build_log_data(
        self,
        level: str,
        event: str,
        message: str = "",
        user_id: Optional[int] = None,
        request_id: Optional[str] = None,
        **extra_fields
    ) -> Dict[str, Any]:
        """로그 데이터 구성"""
        # Context에서 request_id와 user_id 가져오기
        ctx_request_id = request_id_var.get()
        ctx_user_id = user_id_var.get()

        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "logger": self.name,
            "event": event,
        }

        # Message 추가
        if message:
            log_data["message"] = message

        # Request ID 추가 (파라미터 우선, 없으면 context에서)
        final_request_id = request_id or ctx_request_id
        if final_request_id:
            log_data["request_id"] = final_request_id

        # User ID 추가 (파라미터 우선, 없으면 context에서)
        final_user_id = user_id or ctx_user_id
        if final_user_id:
            log_data["user_id"] = final_user_id

        # 추가 필드들
        if extra_fields:
            log_data.update(extra_fields)

        return log_data

    def log_event(
        self,
        level: str,
        event: str,
        message: str = "",
        user_id: Optional[int] = None,
        request_id: Optional[str] = None,
        **extra_fields
    ):
        """
        구조화된 이벤트 로깅

        Args:
            level: 로그 레벨 (INFO, WARNING, ERROR, DEBUG)
            event: 이벤트 이름 (예: "order_submitted", "bot_started")
            message: 로그 메시지
            user_id: 사용자 ID (optional)
            request_id: 요청 ID (optional)
            **extra_fields: 추가 필드들

        Example:
            logger.log_event(
                "INFO",
                "order_submitted",
                "Market order submitted successfully",
                user_id=123,
                symbol="BTCUSDT",
                side="buy",
                size=0.001
            )
        """
        log_data = self._build_log_data(
            level, event, message, user_id, request_id, **extra_fields
        )

        # JSON으로 직렬화
        log_message = json.dumps(log_data, ensure_ascii=False)

        # 레벨에 따라 로깅
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(log_message)

    def info(self, event: str, message: str = "", **kwargs):
        """INFO 레벨 로그"""
        self.log_event("INFO", event, message, **kwargs)

    def warning(self, event: str, message: str = "", **kwargs):
        """WARNING 레벨 로그"""
        self.log_event("WARNING", event, message, **kwargs)

    def error(self, event: str, message: str = "", **kwargs):
        """ERROR 레벨 로그"""
        self.log_event("ERROR", event, message, **kwargs)

    def debug(self, event: str, message: str = "", **kwargs):
        """DEBUG 레벨 로그"""
        self.log_event("DEBUG", event, message, **kwargs)

    def critical(self, event: str, message: str = "", **kwargs):
        """CRITICAL 레벨 로그"""
        self.log_event("CRITICAL", event, message, **kwargs)


class JSONFormatter(logging.Formatter):
    """
    JSON 형식으로 로그를 포맷팅하는 Formatter
    기존 logging 모듈과 통합 가능
    """

    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드를 JSON 형식으로 변환"""
        # 이미 JSON 형식인 경우 (StructuredLogger 사용)
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            pass

        # 일반 로그를 JSON으로 변환
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Request ID 추가
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        # User ID 추가
        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id

        # 예외 정보 추가
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 추가 필드들 (record.extra에서)
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False)


def setup_structured_logging(
    level: str = "INFO",
    enable_json: bool = False
):
    """
    구조화된 로깅 설정

    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: JSON 형식으로 로그 출력 (기본: False, 개발 시 가독성 위해)
    """
    # Root logger 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 새 핸들러 추가
    handler = logging.StreamHandler(sys.stdout)

    if enable_json:
        # JSON 포맷터 사용
        handler.setFormatter(JSONFormatter())
    else:
        # 일반 포맷터 사용 (개발 환경)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )

    root_logger.addHandler(handler)


# Context 관리 함수들
def set_request_id(request_id: str):
    """Request ID 설정"""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Request ID 조회"""
    return request_id_var.get()


def set_user_id(user_id: int):
    """User ID 설정"""
    user_id_var.set(user_id)


def get_user_id() -> Optional[int]:
    """User ID 조회"""
    return user_id_var.get()


def clear_context():
    """Context 초기화"""
    request_id_var.set(None)
    user_id_var.set(None)


# 편의 함수: 모듈별로 StructuredLogger 생성
def get_logger(name: str) -> StructuredLogger:
    """구조화된 로거 생성"""
    return StructuredLogger(name)
