"""
Health Check 엔드포인트

시스템 상태 모니터링 및 헬스 체크를 위한 API
- 기본 헬스 체크
- 데이터베이스 연결 상태
- 시스템 정보
"""
import time
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..config import settings

router = APIRouter(prefix="/health", tags=["health"])

# 서버 시작 시간
SERVER_START_TIME = time.time()


@router.get("")
async def health_check():
    """
    기본 헬스 체크

    시스템이 정상적으로 동작하는지 확인합니다.
    로드 밸런서, 모니터링 도구에서 사용됩니다.

    Returns:
        - status: "healthy"
        - timestamp: 현재 시간
        - uptime: 서버 가동 시간 (초)
        - version: API 버전
    """
    current_time = time.time()
    uptime_seconds = int(current_time - SERVER_START_TIME)

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_seconds,
        "uptime_human": format_uptime(uptime_seconds),
        "version": "1.0.0",
        "environment": "production" if not settings.debug else "development"
    }


@router.get("/db")
async def health_check_db(session: AsyncSession = Depends(get_session)):
    """
    데이터베이스 헬스 체크

    데이터베이스 연결 상태를 확인합니다.

    Returns:
        - status: "healthy" 또는 "unhealthy"
        - database: 연결 상태
        - response_time_ms: DB 응답 시간 (밀리초)
    """
    try:
        start_time = time.time()

        # 간단한 쿼리로 DB 연결 테스트
        result = await session.execute(text("SELECT 1"))
        result.scalar()

        response_time = (time.time() - start_time) * 1000  # ms

        return {
            "status": "healthy",
            "database": "connected",
            "response_time_ms": round(response_time, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/ready")
async def readiness_check(session: AsyncSession = Depends(get_session)):
    """
    Readiness 체크 (Kubernetes 준비 상태 확인)

    서비스가 트래픽을 받을 준비가 되었는지 확인합니다.
    - 데이터베이스 연결 확인

    Returns:
        - ready: True/False
        - checks: 각 컴포넌트 상태
    """
    checks = {
        "database": False
    }

    # 데이터베이스 연결 확인
    try:
        result = await session.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = True
    except Exception:
        pass

    all_ready = all(checks.values())

    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness 체크 (Kubernetes 생존 확인)

    애플리케이션이 살아있는지 확인합니다.
    데드락이나 무한 루프에 빠지지 않았는지 확인합니다.

    Returns:
        - alive: True
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }


def format_uptime(seconds: int) -> str:
    """
    초를 사람이 읽기 쉬운 형식으로 변환

    Args:
        seconds: 초 단위 시간

    Returns:
        "1d 2h 3m 4s" 형식의 문자열
    """
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)
