"""
전역 에러 핸들러

모든 예외를 catch하여 일관된 형식으로 응답합니다.
"""
import logging
import traceback
from datetime import datetime
from typing import Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..utils.exceptions import AppException

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int,
    message: str,
    error_code: str = "ERROR",
    details: dict = None,
    request_id: str = None,
) -> JSONResponse:
    """
    표준화된 에러 응답 생성

    Response Format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {...},
            "timestamp": "2025-12-02T10:00:00",
            "request_id": "abc123"
        }
    }
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
            },
        },
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    커스텀 AppException 핸들러

    우리가 정의한 모든 커스텀 예외를 처리합니다.
    """
    logger.warning(
        f"AppException: {exc.error_code}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "error_message": exc.message,  # Changed from 'message' to avoid logging conflict
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
        request_id=getattr(request.state, "request_id", None),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    FastAPI HTTPException 핸들러

    FastAPI의 기본 HTTPException을 처리합니다.
    """
    logger.warning(
        f"HTTPException: {exc.status_code}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return create_error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        error_code="HTTP_ERROR",
        request_id=getattr(request.state, "request_id", None),
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """
    Pydantic 검증 에러 핸들러

    요청 데이터 검증 실패 시 처리합니다.
    """
    # Pydantic 에러를 읽기 쉬운 형태로 변환
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(
            {
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            }
        )

    logger.warning(
        "Validation error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors,
        },
    )

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation failed",
        error_code="VALIDATION_ERROR",
        details={"errors": errors},
        request_id=getattr(request.state, "request_id", None),
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    SQLAlchemy 에러 핸들러

    데이터베이스 관련 에러를 처리합니다.
    """
    logger.error(
        "Database error",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
        },
        exc_info=True,
    )

    # 프로덕션에서는 상세 에러 숨김
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Database operation failed",
        error_code="DATABASE_ERROR",
        details={},  # 보안상 상세 정보 제외
        request_id=getattr(request.state, "request_id", None),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    처리되지 않은 예외 핸들러

    모든 예상치 못한 에러를 catch합니다.
    """
    # 전체 스택 트레이스 로깅
    logger.critical(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )

    # 프로덕션에서는 일반적인 메시지만 반환
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error",
        error_code="INTERNAL_SERVER_ERROR",
        details={},  # 보안상 상세 정보 제외
        request_id=getattr(request.state, "request_id", None),
    )


def register_exception_handlers(app):
    """
    FastAPI 앱에 모든 예외 핸들러 등록

    Usage:
        from src.middleware.error_handler import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """
    # 우선순위 순서 (높은 순서대로)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    logger.info("Exception handlers registered successfully")
