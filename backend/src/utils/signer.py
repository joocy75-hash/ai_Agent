import hashlib
import hmac
import secrets
from urllib.parse import urlencode


def sign_request(params: dict, secret_key: str) -> str:
    """
    LBank API 서명 생성 (공식 문서 기준)

    LBank API 문서에 따른 서명 방식:
    1. 파라미터에 signature_method, timestamp, echostr 추가
    2. 파라미터를 알파벳 순으로 정렬하여 쿼리 스트링 생성
    3. MD5 다이제스트 생성 (대문자)
    4. HmacSHA256으로 MD5 다이제스트 서명 (hex)
    """
    # echostr이 없으면 추가 (30-40자 랜덤 문자열)
    if "echostr" not in params:
        # 30-40자 길이의 숫자와 문자로 구성
        params["echostr"] = secrets.token_hex(15)  # 30자 hex 문자열

    # signature_method 추가
    if "signature_method" not in params:
        params["signature_method"] = "HmacSHA256"

    # 파라미터를 알파벳 순으로 정렬하여 쿼리 스트링 생성
    sorted_params = sorted(params.items())
    query_string = urlencode(sorted_params)

    # MD5 다이제스트 생성 (대문자)
    md5_digest = hashlib.md5(query_string.encode("utf-8")).hexdigest().upper()

    # HmacSHA256으로 MD5 다이제스트 서명
    signature = hmac.new(
        secret_key.encode("utf-8"), md5_digest.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return signature
