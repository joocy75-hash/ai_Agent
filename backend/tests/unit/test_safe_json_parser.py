"""
safe_json_parser 유닛 테스트

ReDoS 취약점 방지를 위한 안전한 JSON 파싱 유틸리티 테스트.
"""
import pytest
from src.utils.safe_json_parser import extract_json_from_text, extract_json_safe


class TestExtractJsonFromText:
    """extract_json_from_text 함수 테스트"""

    # === 기본 기능 테스트 ===

    def test_simple_json_extraction(self):
        """단순 JSON 추출 테스트"""
        text = 'Result: {"status": "ok", "value": 42}'
        result = extract_json_from_text(text)

        assert result is not None
        assert result["status"] == "ok"
        assert result["value"] == 42

    def test_json_only_text(self):
        """순수 JSON 텍스트 테스트"""
        text = '{"name": "test", "active": true}'
        result = extract_json_from_text(text)

        assert result == {"name": "test", "active": True}

    def test_json_with_prefix_and_suffix(self):
        """앞뒤 텍스트가 있는 JSON 추출"""
        text = 'Here is the result: {"data": [1, 2, 3]} End of response.'
        result = extract_json_from_text(text)

        assert result == {"data": [1, 2, 3]}

    # === 중첩 구조 테스트 ===

    def test_nested_json_objects(self):
        """중첩된 JSON 객체 테스트"""
        text = 'Response: {"outer": {"inner": {"deep": "value"}}}'
        result = extract_json_from_text(text)

        assert result["outer"]["inner"]["deep"] == "value"

    def test_nested_arrays_and_objects(self):
        """배열과 객체가 혼합된 중첩 구조"""
        text = '{"items": [{"id": 1}, {"id": 2}], "meta": {"count": 2}}'
        result = extract_json_from_text(text)

        assert len(result["items"]) == 2
        assert result["items"][0]["id"] == 1
        assert result["meta"]["count"] == 2

    # === 문자열 내부 특수문자 테스트 ===

    def test_braces_in_string(self):
        """문자열 내부의 중괄호 처리"""
        text = '{"message": "Use {name} for placeholder"}'
        result = extract_json_from_text(text)

        assert result["message"] == "Use {name} for placeholder"

    def test_escaped_quotes_in_string(self):
        """이스케이프된 따옴표 처리"""
        text = r'{"text": "He said \"Hello\""}'
        result = extract_json_from_text(text)

        assert result["text"] == 'He said "Hello"'

    def test_escaped_backslash(self):
        """이스케이프된 백슬래시 처리"""
        text = r'{"path": "C:\\Users\\test"}'
        result = extract_json_from_text(text)

        assert result["path"] == "C:\\Users\\test"

    def test_complex_escapes(self):
        """복합 이스케이프 시퀀스"""
        text = r'{"content": "line1\nline2\ttab"}'
        result = extract_json_from_text(text)

        assert result["content"] == "line1\nline2\ttab"

    # === NULL 및 빈 값 테스트 ===

    def test_null_value(self):
        """null 값 처리"""
        text = '{"result": null, "count": 0}'
        result = extract_json_from_text(text)

        assert result["result"] is None
        assert result["count"] == 0

    def test_empty_string_value(self):
        """빈 문자열 값"""
        text = '{"name": "", "active": false}'
        result = extract_json_from_text(text)

        assert result["name"] == ""
        assert result["active"] is False

    def test_empty_object(self):
        """빈 객체"""
        text = 'Empty: {}'
        result = extract_json_from_text(text)

        assert result == {}

    def test_empty_array(self):
        """빈 배열"""
        text = '{"items": []}'
        result = extract_json_from_text(text)

        assert result["items"] == []

    # === 에러 케이스 테스트 ===

    def test_no_json_in_text(self):
        """JSON이 없는 텍스트"""
        text = "This is just plain text without any JSON"
        result = extract_json_from_text(text)

        assert result is None

    def test_empty_input(self):
        """빈 입력"""
        assert extract_json_from_text("") is None
        assert extract_json_from_text(None) is None

    def test_unclosed_brace(self):
        """닫히지 않은 중괄호"""
        text = '{"unclosed": "value"'
        result = extract_json_from_text(text)

        assert result is None

    def test_invalid_json_syntax(self):
        """잘못된 JSON 문법"""
        text = "{invalid json here}"
        result = extract_json_from_text(text)

        assert result is None

    def test_unquoted_key(self):
        """따옴표 없는 키 (잘못된 JSON)"""
        text = "{name: 'test'}"
        result = extract_json_from_text(text)

        assert result is None

    # === DoS 방지 테스트 ===

    def test_max_length_limit(self):
        """최대 길이 제한 테스트"""
        # 기본 max_length=5000 이후에 JSON이 있는 경우
        padding = "x" * 6000
        text = padding + '{"key": "value"}'
        result = extract_json_from_text(text)

        assert result is None  # 길이 제한으로 잘림

    def test_custom_max_length(self):
        """커스텀 최대 길이"""
        padding = "x" * 100
        text = padding + '{"key": "value"}'

        # 짧은 제한으로는 찾지 못함
        result_short = extract_json_from_text(text, max_length=50)
        assert result_short is None

        # 충분한 제한으로는 찾음
        result_long = extract_json_from_text(text, max_length=200)
        assert result_long == {"key": "value"}

    def test_very_deep_nesting(self):
        """깊은 중첩 구조"""
        # 10단계 중첩
        nested = '{"l1": {"l2": {"l3": {"l4": {"l5": {"l6": {"l7": {"l8": {"l9": {"l10": "deep"}}}}}}}}}}'
        result = extract_json_from_text(nested)

        assert result["l1"]["l2"]["l3"]["l4"]["l5"]["l6"]["l7"]["l8"]["l9"]["l10"] == "deep"

    def test_large_but_valid_json(self):
        """큰 크기의 유효한 JSON"""
        items = [{"id": i, "name": f"item_{i}"} for i in range(100)]
        import json
        text = f"Data: {json.dumps({'items': items})}"
        result = extract_json_from_text(text)

        assert len(result["items"]) == 100
        assert result["items"][99]["id"] == 99

    # === AI 응답 시뮬레이션 테스트 ===

    def test_ai_response_with_reasoning(self):
        """AI 응답 형식 (reasoning + JSON)"""
        text = '''
        Based on my analysis, I recommend:

        {"action": "buy", "confidence": 0.85, "reason": "Strong uptrend detected"}

        This is because the market shows bullish signals.
        '''
        result = extract_json_from_text(text)

        assert result["action"] == "buy"
        assert result["confidence"] == 0.85

    def test_ai_response_with_code_block(self):
        """코드 블록 포함 AI 응답"""
        text = '''
        Here's the JSON response:
        ```json
        {"status": "success", "data": {"processed": true}}
        ```
        '''
        result = extract_json_from_text(text)

        assert result["status"] == "success"
        assert result["data"]["processed"] is True

    def test_multiple_json_objects(self):
        """여러 JSON 객체 (첫 번째만 추출)"""
        text = '{"first": 1} and {"second": 2}'
        result = extract_json_from_text(text)

        # 첫 번째 객체만 추출됨
        assert result == {"first": 1}

    # === 특수 데이터 타입 테스트 ===

    def test_numeric_values(self):
        """숫자 값 테스트"""
        text = '{"int": 42, "float": 3.14, "negative": -10, "scientific": 1.5e-3}'
        result = extract_json_from_text(text)

        assert result["int"] == 42
        assert result["float"] == 3.14
        assert result["negative"] == -10
        assert result["scientific"] == 0.0015

    def test_unicode_content(self):
        """유니코드 문자 테스트"""
        text = '{"message": "안녕하세요", "emoji": "👍"}'
        result = extract_json_from_text(text)

        assert result["message"] == "안녕하세요"
        assert result["emoji"] == "👍"


class TestExtractJsonSafe:
    """extract_json_safe 별칭 함수 테스트"""

    def test_alias_works(self):
        """별칭 함수가 동일하게 동작하는지 테스트"""
        text = '{"alias": "test"}'

        result1 = extract_json_from_text(text)
        result2 = extract_json_safe(text)

        assert result1 == result2 == {"alias": "test"}

    def test_alias_returns_none_on_invalid(self):
        """별칭도 잘못된 입력에 None 반환"""
        assert extract_json_safe("no json") is None
        assert extract_json_safe("") is None


class TestReDoSPrevention:
    """ReDoS 공격 방지 테스트"""

    def test_pathological_input_doesnt_hang(self):
        """악의적 패턴 입력에 행이 걸리지 않음"""
        import time

        # ReDoS에 취약한 정규식에서 문제가 될 수 있는 패턴
        pathological = "{" * 100 + "}" * 50 + "invalid"

        start = time.time()
        result = extract_json_from_text(pathological)
        elapsed = time.time() - start

        # 1초 이내 완료되어야 함 (정상적인 O(n) 연산)
        assert elapsed < 1.0
        assert result is None  # 유효한 JSON이 아님

    def test_repeated_escapes_performance(self):
        """반복된 이스케이프 패턴 성능"""
        import time

        # 많은 이스케이프 문자가 포함된 입력
        escapes = '{"data": "' + ('\\\\' * 500) + '"}'

        start = time.time()
        result = extract_json_from_text(escapes)
        elapsed = time.time() - start

        assert elapsed < 1.0
        # 이스케이프된 백슬래시 500개 = 실제 250개
        assert result is not None

    def test_many_nested_braces_in_strings(self):
        """문자열 내 많은 중괄호"""
        import time

        # 문자열 내부에 많은 중괄호
        text = '{"template": "' + '{x}' * 200 + '"}'

        start = time.time()
        result = extract_json_from_text(text)
        elapsed = time.time() - start

        assert elapsed < 1.0
        assert result["template"] == '{x}' * 200
