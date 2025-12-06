"""
Admin Monitoring API

관리자용 모니터링 엔드포인트.
시스템 상태, 사용자 활동, 백테스트 통계 조회.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database.session import get_session
from ..database.models import BacktestResult, User
from ..utils.monitoring import monitor
from ..utils.auth_dependencies import require_admin

router = APIRouter(prefix="/admin/monitoring", tags=["admin", "monitoring"])


@router.get("/stats")
async def get_monitoring_stats(admin_id: int = Depends(require_admin)):
    """
    실시간 모니터링 통계.

    Returns:
    - 시스템 리소스 (CPU, 메모리, 디스크)
    - API 요청 통계
    - 활성 사용자 수
    - 백테스트 통계
    """
    return monitor.get_stats()


@router.get("/backtest/summary")
async def get_backtest_summary(
    session: Session = Depends(get_session),
    admin_id: int = Depends(require_admin)
):
    """
    백테스트 요약 통계 (DB 기반).

    Returns:
    - 총 백테스트 수
    - 상태별 개수 (queued, completed, failed)
    - 최근 10개 백테스트
    """
    # 전체 개수
    total_count = session.query(func.count(BacktestResult.id)).scalar()

    # 상태별 개수
    status_counts = {}
    for status in ["queued", "running", "completed", "failed"]:
        count = session.query(func.count(BacktestResult.id))\
            .filter(BacktestResult.status == status)\
            .scalar()
        status_counts[status] = count or 0

    # 최근 10개
    recent_backtests = session.query(BacktestResult)\
        .order_by(BacktestResult.created_at.desc())\
        .limit(10)\
        .all()

    recent_list = [{
        "id": bt.id,
        "pair": bt.pair,
        "status": bt.status,
        "initial_balance": float(bt.initial_balance),
        "final_balance": float(bt.final_balance) if bt.final_balance else 0.0,
        "created_at": bt.created_at.isoformat() if bt.created_at else None,
    } for bt in recent_backtests]

    return {
        "total_backtests": total_count,
        "status_counts": status_counts,
        "recent_backtests": recent_list,
    }


@router.get("/health")
async def health_check(admin_id: int = Depends(require_admin)):
    """
    간단한 헬스 체크.

    Returns:
    - status: "ok" if healthy
    - timestamp
    """
    stats = monitor.get_stats()

    # CPU/메모리가 80% 이상이면 경고
    system = stats.get("system", {})
    cpu_percent = system.get("cpu_percent", 0)
    memory_percent = system.get("memory_percent", 0)

    status = "ok"
    warnings = []

    if cpu_percent > 80:
        status = "warning"
        warnings.append(f"High CPU usage: {cpu_percent}%")

    if memory_percent > 80:
        status = "warning"
        warnings.append(f"High memory usage: {memory_percent}%")

    return {
        "status": status,
        "warnings": warnings,
        "timestamp": stats["timestamp"],
        "system": system,
    }


@router.post("/reset-stats")
async def reset_monitoring_stats(admin_id: int = Depends(require_admin)):
    """
    모니터링 통계 초기화.
    (일일 리셋용)
    """
    monitor.reset_stats()
    return {"message": "Monitoring stats reset successfully"}
