"""
API 연결 상태 확인
"""


import requests
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database.db import get_session
from ..utils.jwt_auth import get_current_user_id

router = APIRouter(prefix="/api/status", tags=["API Status"])


@router.get("/all")
async def get_all_api_status(
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id),
):
    """모든 API 연결 상태 확인"""

    # 1. DeepSeek AI 상태
    deepseek_status = check_deepseek_api()

    # 2. Bitget 상태
    bitget_status = check_bitget_api()

    # 3. 데이터베이스 상태
    db_status = await check_database(session)

    return {
        "deepseek": deepseek_status,
        "bitget": bitget_status,
        "database": db_status,
        "overall_status": "healthy"
        if all(
            [
                deepseek_status["connected"],
                bitget_status["connected"],
                db_status["connected"],
            ]
        )
        else "degraded",
    }


def check_deepseek_api() -> dict:
    """DeepSeek AI API의 연결 상태를 확인합니다.

    DeepSeek AI 서비스의 가용성을 확인하여 API 상태 정보를 반환합니다.
    실제 API 호출은 비용이 발생할 수 있으므로, API 키 설정 여부만으로
    연결 상태를 판단합니다.

    Returns:
        dict: API 상태 정보를 담은 딕셔너리.
            - name (str): 서비스 이름 ("DeepSeek AI")
            - connected (bool): 연결 가능 여부
            - status (str): 상태 코드 ("connected", "not_configured", "error")
            - message (str): 사용자 친화적 상태 메시지 (한국어)
            - details (dict): 추가 상세 정보
                - api_key_configured (bool): API 키 설정 여부
                - model (str): 사용 중인 모델명 (연결 시)
                - features (list): 지원 기능 목록 (연결 시)

    Note:
        API 키가 설정되어 있으면 연결된 것으로 간주합니다.
        실제 API 호출 테스트는 비용 문제로 수행하지 않습니다.
    """
    try:
        api_key = settings.deepseek_api_key

        if not api_key:
            return {
                "name": "DeepSeek AI",
                "connected": False,
                "status": "not_configured",
                "message": "API 키가 설정되지 않았습니다",
                "details": {"api_key_configured": False},
            }

        # API 키가 있으면 연결됨으로 간주 (실제 API 호출은 비용이 발생할 수 있음)
        return {
            "name": "DeepSeek AI",
            "connected": True,
            "status": "connected",
            "message": "정상 연결됨",
            "details": {
                "api_key_configured": True,
                "model": "deepseek-chat (V3.2)",
                "features": ["전략 생성", "시장 분석"],
            },
        }
    except Exception as e:
        return {
            "name": "DeepSeek AI",
            "connected": False,
            "status": "error",
            "message": f"오류: {str(e)}",
            "details": {},
        }


def check_bitget_api() -> dict:
    """Bitget 거래소 API의 연결 상태를 확인합니다.

    Bitget 거래소의 공개 API 엔드포인트에 요청을 보내 서버 연결 상태와
    응답 시간을 확인합니다. 인증이 필요 없는 서버 시간 조회 API를 사용합니다.

    Returns:
        dict: API 상태 정보를 담은 딕셔너리.
            - name (str): 서비스 이름 ("Bitget Exchange")
            - connected (bool): 연결 성공 여부
            - status (str): 상태 코드 ("connected", "error", "timeout")
            - message (str): 사용자 친화적 상태 메시지 (한국어)
            - details (dict): 추가 상세 정보
                - server_time (str): 거래소 서버 시간 (연결 성공 시)
                - endpoint (str): API 엔드포인트 URL (연결 성공 시)

    Note:
        - 5초 타임아웃으로 요청합니다.
        - 공개 API (/api/v2/public/time)를 사용하므로 인증 불필요.
        - 네트워크 오류, 타임아웃, HTTP 에러 등을 구분하여 처리합니다.
    """
    try:
        # 공개 API로 연결 테스트
        response = requests.get("https://api.bitget.com/api/v2/public/time", timeout=5)

        if response.status_code == 200:
            return {
                "name": "Bitget Exchange",
                "connected": True,
                "status": "connected",
                "message": "정상 연결됨",
                "details": {
                    "server_time": response.json().get("data", {}).get("serverTime"),
                    "endpoint": "https://api.bitget.com",
                },
            }
        else:
            return {
                "name": "Bitget Exchange",
                "connected": False,
                "status": "error",
                "message": f"HTTP {response.status_code}",
                "details": {},
            }

    except requests.exceptions.Timeout:
        return {
            "name": "Bitget Exchange",
            "connected": False,
            "status": "timeout",
            "message": "연결 시간 초과",
            "details": {},
        }
    except Exception as e:
        return {
            "name": "Bitget Exchange",
            "connected": False,
            "status": "error",
            "message": f"오류: {str(e)}",
            "details": {},
        }


async def check_database(session: AsyncSession) -> dict:
    """데이터베이스 상태 확인"""
    try:
        # 간단한 쿼리로 연결 테스트
        from sqlalchemy import text

        result = await session.execute(text("SELECT 1"))
        result.scalar()

        return {
            "name": "Database",
            "connected": True,
            "status": "connected",
            "message": "정상 연결됨",
            "details": {"type": "SQLite", "url": "sqlite:///./trading.db"},
        }
    except Exception as e:
        return {
            "name": "Database",
            "connected": False,
            "status": "error",
            "message": f"오류: {str(e)}",
            "details": {},
        }
