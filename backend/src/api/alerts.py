import logging
from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..database.db import get_session
from ..database.models import SystemAlert
from ..utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertInfo(BaseModel):
    id: int
    level: str  # ERROR, WARNING, INFO
    message: str
    timestamp: datetime
    is_resolved: bool


class AlertsResponse(BaseModel):
    alerts: List[AlertInfo]


@router.get("/urgent", response_model=AlertsResponse)
async def get_urgent_alerts(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """긴급 알림 조회 (최근 3개, ERROR/WARNING만, JWT 인증 필요)"""
    try:
        # 미해결된 ERROR, WARNING 알림만 조회
        result = await session.execute(
            select(SystemAlert)
            .where(
                and_(
                    SystemAlert.user_id == user_id,
                    SystemAlert.is_resolved == False,
                    SystemAlert.level.in_(["ERROR", "WARNING"]),
                )
            )
            .order_by(SystemAlert.created_at.desc())
            .limit(3)
        )

        alerts_data = result.scalars().all()

        alerts = [
            AlertInfo(
                id=alert.id,
                level=alert.level,
                message=alert.message,
                timestamp=alert.created_at,
                is_resolved=alert.is_resolved,
            )
            for alert in alerts_data
        ]

        return AlertsResponse(alerts=alerts)

    except Exception as e:
        logger.error(f"[get_urgent_alerts] Error: {e}", exc_info=True)
        return AlertsResponse(alerts=[])


@router.get("/all", response_model=AlertsResponse)
async def get_all_alerts(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
    limit: int = 50,
):
    """모든 알림 조회 (JWT 인증 필요)"""
    try:
        result = await session.execute(
            select(SystemAlert)
            .where(SystemAlert.user_id == user_id)
            .order_by(SystemAlert.created_at.desc())
            .limit(limit)
        )

        alerts_data = result.scalars().all()

        alerts = [
            AlertInfo(
                id=alert.id,
                level=alert.level,
                message=alert.message,
                timestamp=alert.created_at,
                is_resolved=alert.is_resolved,
            )
            for alert in alerts_data
        ]

        return AlertsResponse(alerts=alerts)

    except Exception as e:
        logger.error(f"[get_all_alerts] Error: {e}", exc_info=True)
        return AlertsResponse(alerts=[])


@router.post("/resolve/{alert_id}")
async def resolve_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """알림 해결 처리 (JWT 인증 필요)"""
    try:
        result = await session.execute(
            select(SystemAlert).where(
                and_(SystemAlert.id == alert_id, SystemAlert.user_id == user_id)
            )
        )

        alert = result.scalars().first()
        if not alert:
            return {"success": False, "message": "Alert not found"}

        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        await session.commit()

        return {"success": True, "message": "Alert resolved"}

    except Exception as e:
        logger.error(f"[resolve_alert] Error: {e}", exc_info=True)
        return {"success": False, "message": str(e)}


@router.post("/resolve-all")
async def resolve_all_alerts(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """모든 알림 해결 처리 (JWT 인증 필요)"""
    try:
        result = await session.execute(
            select(SystemAlert).where(
                and_(SystemAlert.user_id == user_id, SystemAlert.is_resolved == False)
            )
        )

        alerts = result.scalars().all()
        count = 0

        for alert in alerts:
            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()
            count += 1

        await session.commit()

        return {"success": True, "message": f"{count} alerts resolved"}

    except Exception as e:
        logger.error(f"[resolve_all_alerts] Error: {e}", exc_info=True)
        return {"success": False, "message": str(e)}


@router.get("/statistics")
async def get_alert_statistics(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """알림 통계 조회 (JWT 인증 필요)"""
    try:
        # 전체 알림 조회
        result = await session.execute(
            select(SystemAlert).where(SystemAlert.user_id == user_id)
        )
        all_alerts = result.scalars().all()

        # 통계 계산
        total = len(all_alerts)
        unresolved = sum(1 for a in all_alerts if not a.is_resolved)
        resolved = total - unresolved

        by_level = {
            "ERROR": sum(1 for a in all_alerts if a.level == "ERROR"),
            "WARNING": sum(1 for a in all_alerts if a.level == "WARNING"),
            "INFO": sum(1 for a in all_alerts if a.level == "INFO"),
        }

        # 최근 24시간 알림
        recent_time = datetime.utcnow() - timedelta(hours=24)
        recent = sum(1 for a in all_alerts if a.created_at >= recent_time)

        return {
            "total": total,
            "unresolved": unresolved,
            "resolved": resolved,
            "by_level": by_level,
            "recent_24h": recent,
        }

    except Exception as e:
        logger.error(f"[get_alert_statistics] Error: {e}", exc_info=True)
        return {
            "total": 0,
            "unresolved": 0,
            "resolved": 0,
            "by_level": {"ERROR": 0, "WARNING": 0, "INFO": 0},
            "recent_24h": 0,
        }


@router.delete("/clear-resolved")
async def clear_resolved_alerts(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """해결된 알림 삭제 (JWT 인증 필요)"""
    try:
        result = await session.execute(
            select(SystemAlert).where(
                and_(SystemAlert.user_id == user_id, SystemAlert.is_resolved == True)
            )
        )

        alerts = result.scalars().all()
        count = len(alerts)

        for alert in alerts:
            await session.delete(alert)

        await session.commit()

        return {"success": True, "message": f"{count} resolved alerts deleted"}

    except Exception as e:
        logger.error(f"[clear_resolved_alerts] Error: {e}", exc_info=True)
        return {"success": False, "message": str(e)}
