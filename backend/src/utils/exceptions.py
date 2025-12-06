"""
커스텀 예외 클래스

프로젝트 전체에서 사용할 표준화된 예외 클래스들.
각 예외는 HTTP 상태 코드와 명확한 에러 메시지를 포함합니다.
"""
from typing import Any, Dict, Optional


class AppException(Exception):
    """
    애플리케이션 기본 예외 클래스

    모든 커스텀 예외의 부모 클래스입니다.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 인증 관련 예외 (4xx)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AuthenticationError(AppException):
    """인증 실패 (401)"""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class InvalidTokenError(AuthenticationError):
    """잘못된 토큰 (401)"""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, {"hint": "Please login again"})


class PermissionDeniedError(AppException):
    """권한 없음 (403)"""

    def __init__(self, message: str = "Permission denied", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="PERMISSION_DENIED",
            details=details,
        )


class AdminRequiredError(PermissionDeniedError):
    """관리자 권한 필요 (403)"""

    def __init__(self):
        super().__init__(
            message="Admin access required",
            details={"required_role": "admin"},
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 리소스 관련 예외 (4xx)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ResourceNotFoundError(AppException):
    """리소스를 찾을 수 없음 (404)"""

    def __init__(
        self, resource: str, resource_id: Optional[Any] = None, details: Optional[Dict] = None
    ):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"

        super().__init__(
            message=message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details=details or {},
        )


class UserNotFoundError(ResourceNotFoundError):
    """사용자를 찾을 수 없음 (404)"""

    def __init__(self, user_id: Optional[int] = None):
        super().__init__("User", user_id)


class StrategyNotFoundError(ResourceNotFoundError):
    """전략을 찾을 수 없음 (404)"""

    def __init__(self, strategy_id: Optional[int] = None):
        super().__init__("Strategy", strategy_id)


class ApiKeyNotFoundError(ResourceNotFoundError):
    """API 키를 찾을 수 없음 (404)"""

    def __init__(self):
        super().__init__(
            "API key",
            details={"hint": "Please save your API keys first"},
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 검증 관련 예외 (4xx)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ValidationError(AppException):
    """입력 검증 실패 (400)"""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=error_details,
        )


class InvalidParameterError(ValidationError):
    """잘못된 파라미터 (400)"""

    def __init__(self, parameter: str, reason: str):
        super().__init__(
            message=f"Invalid parameter: {parameter}",
            field=parameter,
            details={"reason": reason},
        )


class DuplicateResourceError(AppException):
    """중복된 리소스 (409)"""

    def __init__(self, resource: str, field: str, value: Any):
        super().__init__(
            message=f"{resource} already exists",
            status_code=409,
            error_code="DUPLICATE_RESOURCE",
            details={"field": field, "value": str(value)},
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Rate Limiting 관련 예외 (4xx)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class RateLimitExceededError(AppException):
    """Rate Limit 초과 (429)"""

    def __init__(
        self,
        message: str = "Too many requests",
        limit: Optional[int] = None,
        window: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        # details 파라미터가 제공되면 사용, 아니면 limit/window로 생성
        if details is None:
            details = {}
            if limit:
                details["limit"] = limit
            if window:
                details["window"] = window

        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class ResourceLimitExceededError(AppException):
    """리소스 제한 초과 (429)"""

    def __init__(self, resource: str, limit: int, current: int):
        super().__init__(
            message=f"{resource} limit exceeded",
            status_code=429,
            error_code="RESOURCE_LIMIT_EXCEEDED",
            details={
                "resource": resource,
                "limit": limit,
                "current": current,
            },
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 비즈니스 로직 관련 예외 (4xx, 5xx)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class BotNotRunningError(AppException):
    """봇이 실행 중이 아님 (400)"""

    def __init__(self):
        super().__init__(
            message="Bot is not running",
            status_code=400,
            error_code="BOT_NOT_RUNNING",
            details={"hint": "Start the bot first"},
        )


class BotAlreadyRunningError(AppException):
    """봇이 이미 실행 중 (400)"""

    def __init__(self):
        super().__init__(
            message="Bot is already running",
            status_code=400,
            error_code="BOT_ALREADY_RUNNING",
            details={"hint": "Stop the bot first"},
        )


class ExchangeAPIError(AppException):
    """거래소 API 에러 (502)"""

    def __init__(self, exchange: str, original_error: str):
        super().__init__(
            message=f"{exchange} API error",
            status_code=502,
            error_code="EXCHANGE_API_ERROR",
            details={
                "exchange": exchange,
                "original_error": original_error,
            },
        )


class EncryptionError(AppException):
    """암호화/복호화 에러 (500)"""

    def __init__(self, message: str = "Encryption/Decryption failed"):
        super().__init__(
            message=message,
            status_code=500,
            error_code="ENCRYPTION_ERROR",
        )


class DatabaseError(AppException):
    """데이터베이스 에러 (500)"""

    def __init__(self, message: str = "Database operation failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details or {},
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 보안 관련 예외 (4xx)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SecurityError(AppException):
    """보안 위반 (403)"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="SECURITY_ERROR",
            details=details or {},
        )


class PathTraversalError(SecurityError):
    """Path Traversal 시도 (403)"""

    def __init__(self, path: str):
        super().__init__(
            message="Access denied: Invalid file path",
            details={"attempted_path": path},
        )
