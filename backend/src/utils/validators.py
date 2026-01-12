"""
입력 검증 유틸리티

Pydantic 스키마에서 사용할 수 있는 재사용 가능한 검증기입니다.
XSS 방지, SQL Injection 방지, 파일 경로 검증 등을 제공합니다.
"""

import re
from pathlib import Path
from typing import Optional

import bleach
from pydantic import field_validator


class ValidationRules:
    """검증 규칙 상수"""

    # 비밀번호
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    PASSWORD_PATTERN = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]"
    )

    # 문자열 길이
    SHORT_TEXT_MAX_LENGTH = 100  # 이름, 제목 등
    MEDIUM_TEXT_MAX_LENGTH = 500  # 설명 등
    LONG_TEXT_MAX_LENGTH = 10000  # 코드, 긴 텍스트 등

    # 숫자 범위
    BALANCE_MIN = 0.01
    BALANCE_MAX = 1_000_000_000

    # 파일
    ALLOWED_CSV_EXTENSIONS = {".csv"}
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}
    MAX_FILE_SIZE_MB = 100

    # API Key
    API_KEY_MIN_LENGTH = 8  # 일부 거래소는 짧은 키를 사용
    API_KEY_MAX_LENGTH = 256


def sanitize_html(text: str) -> str:
    """
    HTML/XSS 공격 방지를 위한 텍스트 정제

    모든 HTML 태그와 위험한 문자를 제거합니다.

    Args:
        text: 정제할 텍스트

    Returns:
        정제된 텍스트
    """
    if not text:
        return text

    # bleach를 사용하여 모든 HTML 태그 제거
    cleaned = bleach.clean(text, tags=[], strip=True)

    # 추가 XSS 패턴 제거 (ReDoS 안전한 패턴 사용)
    xss_patterns = [
        r"javascript:",
        r"<script",
        r"</script>",
    ]

    for pattern in xss_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # 이벤트 핸들러 제거 (ReDoS 방지를 위해 고정 패턴 사용)
    event_handlers = [
        "onclick", "ondblclick", "onmousedown", "onmouseup", "onmouseover",
        "onmousemove", "onmouseout", "onkeydown", "onkeypress", "onkeyup",
        "onload", "onunload", "onerror", "onsubmit", "onreset", "onfocus",
        "onblur", "onchange", "onselect", "onabort"
    ]
    for handler in event_handlers:
        # 대소문자 무시하고 handler= 패턴 제거
        cleaned = re.sub(rf"{handler}\s*=", "", cleaned, flags=re.IGNORECASE)

    return cleaned


def validate_no_sql_injection(text: str) -> str:
    """
    SQL Injection 패턴 검증

    Note: SQLAlchemy ORM을 사용하면 기본적으로 SQL Injection이 방지되지만,
    추가적인 검증 레이어로 위험한 패턴을 체크합니다.

    Args:
        text: 검증할 텍스트

    Returns:
        검증된 텍스트

    Raises:
        ValueError: 위험한 SQL 패턴이 발견된 경우
    """
    if not text:
        return text

    # 위험한 SQL 키워드 패턴
    dangerous_patterns = [
        r"\b(DROP|DELETE|TRUNCATE|ALTER|EXEC|EXECUTE)\b",
        r"--",  # SQL 주석
        r"/\*",  # SQL 블록 주석
        r";\s*(DROP|DELETE|INSERT|UPDATE)",  # 세미콜론 후 위험 명령
        r"UNION\s+SELECT",
        r"OR\s+1\s*=\s*1",
        r"OR\s+\'1\'\s*=\s*\'1\'",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError("Potentially dangerous SQL pattern detected")

    return text


def validate_file_path(file_path: str, allowed_extensions: set[str]) -> Path:
    """
    파일 경로 검증 (Path Traversal 방지)

    Args:
        file_path: 검증할 파일 경로
        allowed_extensions: 허용할 파일 확장자 집합

    Returns:
        검증된 Path 객체

    Raises:
        ValueError: 유효하지 않은 경로인 경우
    """
    try:
        path = Path(file_path).resolve()
    except Exception as e:
        raise ValueError("Invalid file path") from e

    # 확장자 검증
    if path.suffix.lower() not in allowed_extensions:
        raise ValueError(
            f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"
        )

    # Path Traversal 방지: 허용된 디렉토리 내에 있는지 확인
    project_root = Path(__file__).parent.parent.parent
    allowed_dirs = [
        project_root / "data",
        project_root / "backtest_data",
        project_root / "uploads",
    ]

    is_allowed = any(path.is_relative_to(allowed_dir) for allowed_dir in allowed_dirs)

    if not is_allowed:
        raise ValueError(
            "File must be in an allowed directory (data/, backtest_data/, uploads/)"
        )

    return path


def validate_password_strength(password: str) -> str:
    """
    비밀번호 강도 검증

    최소 8자, 최대 128자
    최소 하나의 대문자, 소문자, 숫자, 특수문자 포함

    Args:
        password: 검증할 비밀번호

    Returns:
        검증된 비밀번호

    Raises:
        ValueError: 비밀번호가 요구사항을 만족하지 않는 경우
    """
    if len(password) < ValidationRules.PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {ValidationRules.PASSWORD_MIN_LENGTH} characters"
        )

    if len(password) > ValidationRules.PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must not exceed {ValidationRules.PASSWORD_MAX_LENGTH} characters"
        )

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

    if not re.search(r"[@$!%*?&]", password):
        raise ValueError(
            "Password must contain at least one special character (@$!%*?&)"
        )

    return password


def validate_string_length(
    text: str,
    min_length: int = 1,
    max_length: int = ValidationRules.SHORT_TEXT_MAX_LENGTH,
    field_name: str = "field",
) -> str:
    """
    문자열 길이 검증

    Args:
        text: 검증할 문자열
        min_length: 최소 길이
        max_length: 최대 길이
        field_name: 필드 이름 (에러 메시지용)

    Returns:
        검증된 문자열

    Raises:
        ValueError: 길이가 범위를 벗어난 경우
    """
    if not text or len(text.strip()) < min_length:
        raise ValueError(f"{field_name} must be at least {min_length} characters")

    if len(text) > max_length:
        raise ValueError(f"{field_name} must not exceed {max_length} characters")

    return text.strip()


def validate_positive_number(
    value: float,
    min_value: float = 0.01,
    max_value: Optional[float] = None,
    field_name: str = "value",
) -> float:
    """
    양수 범위 검증

    Args:
        value: 검증할 숫자
        min_value: 최소값
        max_value: 최대값 (None이면 무제한)
        field_name: 필드 이름 (에러 메시지용)

    Returns:
        검증된 숫자

    Raises:
        ValueError: 값이 범위를 벗어난 경우
    """
    if value < min_value:
        raise ValueError(f"{field_name} must be at least {min_value}")

    if max_value is not None and value > max_value:
        raise ValueError(f"{field_name} must not exceed {max_value}")

    return value


def validate_api_key_format(api_key: str) -> str:
    """
    API 키 형식 검증

    Args:
        api_key: 검증할 API 키

    Returns:
        검증된 API 키

    Raises:
        ValueError: 형식이 유효하지 않은 경우
    """
    if not api_key or len(api_key.strip()) < ValidationRules.API_KEY_MIN_LENGTH:
        raise ValueError(
            f"API key must be at least {ValidationRules.API_KEY_MIN_LENGTH} characters"
        )

    if len(api_key) > ValidationRules.API_KEY_MAX_LENGTH:
        raise ValueError(
            f"API key must not exceed {ValidationRules.API_KEY_MAX_LENGTH} characters"
        )

    # 기본적인 형식 검증 - 출력 가능한 ASCII 문자만 허용
    # 거래소마다 API 키 형식이 다르므로 매우 관대하게 검증
    if not all(32 <= ord(c) <= 126 for c in api_key):
        raise ValueError(
            "API key contains invalid characters (only printable ASCII allowed)"
        )

    return api_key.strip()


def validate_strategy_name(name: str) -> str:
    """
    전략 이름 검증

    한글, 영문, 숫자, 공백, 언더스코어, 하이픈 허용
    (사용자 친화적인 이름 지원)

    Args:
        name: 검증할 전략 이름

    Returns:
        검증된 전략 이름

    Raises:
        ValueError: 형식이 유효하지 않은 경우
    """
    name = validate_string_length(
        name, min_length=1, max_length=100, field_name="Strategy name"
    )

    # 한글, 영문, 숫자, 공백, 언더스코어, 하이픈, 괄호, 점 허용
    if not re.match(r"^[\w\s가-힣\-\(\)\.\,\!\@\#]+$", name, re.UNICODE):
        raise ValueError(
            "Strategy name can only contain letters, numbers, spaces, Korean characters, and basic punctuation"
        )

    return name


# Pydantic field validator 데코레이터를 위한 헬퍼 함수들
def create_sanitize_validator(field_name: str):
    """XSS 방지 validator 생성"""

    def validator(cls, v):
        if v is None:
            return v
        return sanitize_html(v)

    return field_validator(field_name, mode="after")(validator)


def create_length_validator(field_name: str, min_len: int, max_len: int):
    """문자열 길이 validator 생성"""

    def validator(cls, v):
        if v is None:
            return v
        return validate_string_length(v, min_len, max_len, field_name)

    return field_validator(field_name, mode="after")(validator)
