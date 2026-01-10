"""
안전한 JSON 파싱 유틸리티

ReDoS(Regular Expression Denial of Service) 취약점을 방지하기 위한
안전한 JSON 추출 함수를 제공합니다.
"""
import json
from typing import Optional, Dict, Any


def extract_json_from_text(text: str, max_length: int = 5000) -> Optional[Dict[str, Any]]:
    """
    텍스트에서 JSON 객체를 안전하게 추출합니다.

    정규식 대신 순차적 괄호 매칭을 사용하여 ReDoS 공격을 방지합니다.

    Args:
        text: JSON을 포함할 수 있는 텍스트
        max_length: 검색할 최대 문자열 길이 (기본: 5000자)

    Returns:
        파싱된 JSON 딕셔너리 또는 None

    Examples:
        >>> extract_json_from_text('Result: {"status": "ok", "value": 42}')
        {'status': 'ok', 'value': 42}

        >>> extract_json_from_text('No JSON here')
        None
    """
    if not text:
        return None

    # 길이 제한 (DoS 방지)
    text = text[:max_length]

    # JSON 시작점 찾기
    start_idx = text.find('{')
    if start_idx == -1:
        return None

    # 순차적 괄호 매칭 (O(n) 연산, ReDoS 안전)
    depth = 0
    end_idx = -1
    in_string = False
    escape_next = False

    for i in range(start_idx, len(text)):
        char = text[i]

        # 문자열 내부 처리 (JSON 문자열 안의 중괄호 무시)
        if escape_next:
            escape_next = False
            continue

        if char == '\\' and in_string:
            escape_next = True
            continue

        if char == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        # 괄호 카운팅
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                end_idx = i
                break

    if end_idx == -1:
        return None

    # JSON 파싱 시도
    try:
        json_str = text[start_idx:end_idx + 1]
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None


def extract_json_safe(text: str) -> Optional[Dict[str, Any]]:
    """
    extract_json_from_text의 별칭 (하위 호환성)
    """
    return extract_json_from_text(text)
