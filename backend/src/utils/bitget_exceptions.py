"""
Bitget API 에러 핸들링
"""


class BitgetAPIError(Exception):
    """Bitget API 에러 기본 클래스"""

    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class BitgetRateLimitError(BitgetAPIError):
    """Rate Limit 초과 에러"""

    pass


class BitgetAuthenticationError(BitgetAPIError):
    """인증 실패 에러"""

    pass


class BitgetInsufficientBalanceError(BitgetAPIError):
    """잔고 부족 에러"""

    pass


class BitgetNetworkError(BitgetAPIError):
    """네트워크 에러"""

    pass


class BitgetTimeoutError(BitgetAPIError):
    """Timeout 에러"""

    pass


class BitgetInvalidParameterError(BitgetAPIError):
    """잘못된 파라미터 에러"""

    pass


class BitgetMarketClosedError(BitgetAPIError):
    """시장 마감 에러"""

    pass


def classify_bitget_error(code: str, message: str) -> BitgetAPIError:
    """
    Bitget 에러 코드를 분류하여 적절한 예외 반환

    Args:
        code: Bitget API 에러 코드
        message: 에러 메시지

    Returns:
        분류된 BitgetAPIError 예외
    """
    # Rate Limit 에러
    if code in ["40014", "40015", "40016"]:
        return BitgetRateLimitError(
            message="API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
            code=code,
            details={"original_message": message},
        )

    # 인증 에러
    if code in ["40001", "40002", "40003", "40004", "40005", "40006"]:
        return BitgetAuthenticationError(
            message="API 인증에 실패했습니다. API 키를 확인해주세요.",
            code=code,
            details={"original_message": message},
        )

    # 잔고 부족
    if code in ["43025", "43026"]:
        return BitgetInsufficientBalanceError(
            message="잔고가 부족합니다.",
            code=code,
            details={"original_message": message},
        )

    # 잘못된 파라미터
    if code in ["40007", "40008", "40009", "40010", "40011", "40012", "40013"]:
        return BitgetInvalidParameterError(
            message=f"잘못된 요청 파라미터입니다: {message}",
            code=code,
            details={"original_message": message},
        )

    # 시장 마감
    if code in ["43001", "43002"]:
        return BitgetMarketClosedError(
            message="현재 거래가 불가능한 시간입니다.",
            code=code,
            details={"original_message": message},
        )

    # 기타 에러
    return BitgetAPIError(
        message=f"Bitget API 에러: {message}",
        code=code,
        details={"original_message": message},
    )
