"""
API 연결 상태 확인
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import requests
from typing import Optional

from ..database.db import get_session
from ..config import settings
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
    """DeepSeek AI API 상태 확인"""
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
                "model": "deepseek-chat",
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
    """Bitget API 상태 확인"""
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
