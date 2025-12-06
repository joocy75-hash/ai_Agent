"""
Admin Bot Control API

관리자 전용 봇 제어 엔드포인트.
봇 강제 정지, 재시작, 전체 봇 긴급 정지 등의 기능 제공.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from ..database.db import get_session
from ..database.models import BotStatus, User, Strategy
from ..utils.auth_dependencies import require_admin
from ..utils.structured_logging import get_logger

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

router = APIRouter(prefix="/admin/bots", tags=["admin-bots"])


@router.get("/active")
async def get_active_bots(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 활성 봇 목록 조회

    Returns:
        활성 상태인 모든 봇 정보 (user_id, strategy_id, status, uptime 등)
    """
    try:
        # BotStatus에서 is_running=True인 봇들 조회
        result = await session.execute(
            select(BotStatus, User, Strategy)
            .join(User, BotStatus.user_id == User.id)
            .outerjoin(Strategy, BotStatus.strategy_id == Strategy.id)
            .where(BotStatus.is_running == True)
        )

        bots_data = result.all()

        active_bots = []
        for bot_status, user, strategy in bots_data:
            active_bots.append({
                "user_id": user.id,
                "user_email": user.email,
                "strategy_id": bot_status.strategy_id,
                "strategy_name": strategy.name if strategy else "Unknown",
                "is_running": bot_status.is_running,
                "updated_at": bot_status.updated_at.isoformat() if hasattr(bot_status, 'updated_at') and bot_status.updated_at else None,
            })

        structured_logger.info(
            "admin_active_bots_fetched",
            f"Admin {admin_id} fetched {len(active_bots)} active bots",
            admin_id=admin_id,
            active_bot_count=len(active_bots)
        )

        return {
            "active_bots": active_bots,
            "total_count": len(active_bots),
        }

    except Exception as e:
        structured_logger.error(
            "admin_active_bots_error",
            "Failed to fetch active bots",
            admin_id=admin_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch active bots: {str(e)}")


@router.post("/{user_id}/pause")
async def pause_user_bot(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 특정 사용자 봇 강제 정지

    Args:
        user_id: 봇을 정지할 사용자 ID

    Returns:
        봇 정지 결과
    """
    try:
        # 사용자 확인
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # BotStatus 조회
        bot_result = await session.execute(
            select(BotStatus).where(BotStatus.user_id == user_id)
        )
        bot_status = bot_result.scalar_one_or_none()

        if not bot_status:
            raise HTTPException(status_code=404, detail="Bot status not found")

        # 이미 정지된 경우
        if not bot_status.is_running:
            return {
                "success": True,
                "message": f"Bot for user {user_id} is already paused",
                "was_running": False,
            }

        # 봇 정지
        bot_status.is_running = False
        await session.commit()

        structured_logger.warning(
            "admin_bot_paused",
            f"Admin {admin_id} paused bot for user {user_id}",
            admin_id=admin_id,
            target_user_id=user_id,
            target_user_email=user.email
        )

        return {
            "success": True,
            "message": f"Bot for user {user_id} ({user.email}) has been paused",
            "was_running": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        structured_logger.error(
            "admin_bot_pause_error",
            "Failed to pause bot",
            admin_id=admin_id,
            target_user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to pause bot: {str(e)}")


@router.post("/{user_id}/restart")
async def restart_user_bot(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 특정 사용자 봇 재시작

    Args:
        user_id: 봇을 재시작할 사용자 ID

    Returns:
        봇 재시작 결과
    """
    try:
        # 사용자 확인
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # BotStatus 조회
        bot_result = await session.execute(
            select(BotStatus).where(BotStatus.user_id == user_id)
        )
        bot_status = bot_result.scalar_one_or_none()

        if not bot_status:
            raise HTTPException(status_code=404, detail="Bot status not found")

        # 이미 실행 중인 경우
        if bot_status.is_running:
            return {
                "success": True,
                "message": f"Bot for user {user_id} is already running",
                "was_paused": False,
            }

        # 봇 재시작
        bot_status.is_running = True
        await session.commit()

        structured_logger.warning(
            "admin_bot_restarted",
            f"Admin {admin_id} restarted bot for user {user_id}",
            admin_id=admin_id,
            target_user_id=user_id,
            target_user_email=user.email
        )

        return {
            "success": True,
            "message": f"Bot for user {user_id} ({user.email}) has been restarted",
            "was_paused": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        structured_logger.error(
            "admin_bot_restart_error",
            "Failed to restart bot",
            admin_id=admin_id,
            target_user_id=user_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to restart bot: {str(e)}")


@router.post("/pause-all")
async def pause_all_bots(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 전체 봇 긴급 정지 (Emergency Stop)

    ⚠️ 주의: 이 기능은 시스템 전체의 모든 봇을 정지시킵니다.
    긴급 상황에서만 사용해야 합니다.

    Returns:
        정지된 봇 개수 및 결과
    """
    try:
        # 현재 실행 중인 모든 봇 조회
        result = await session.execute(
            select(BotStatus).where(BotStatus.is_running == True)
        )
        active_bots = result.scalars().all()

        paused_count = 0

        # 모든 봇 정지
        for bot in active_bots:
            bot.is_running = False
            paused_count += 1

        await session.commit()

        # CRITICAL 로그 기록 (전체 봇 정지는 중요한 이벤트)
        structured_logger.critical(
            "admin_all_bots_paused",
            f"🚨 EMERGENCY: Admin {admin_id} paused ALL bots ({paused_count} bots stopped)",
            admin_id=admin_id,
            paused_count=paused_count
        )

        return {
            "success": True,
            "message": f"🚨 Emergency stop: {paused_count} bots have been paused",
            "paused_count": paused_count,
            "warning": "All trading bots have been stopped. This is an emergency action.",
        }

    except Exception as e:
        await session.rollback()
        structured_logger.error(
            "admin_pause_all_error",
            "Failed to pause all bots",
            admin_id=admin_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to pause all bots: {str(e)}")


@router.get("/statistics")
async def get_bot_statistics(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 봇 통계 조회

    Returns:
        전체 봇 통계 (총 봇 수, 실행 중, 정지 중, 전략별 분포 등)
    """
    try:
        # 전체 봇 수 (user_id가 primary key)
        total_result = await session.execute(select(func.count(BotStatus.user_id)))
        total_bots = total_result.scalar() or 0

        # 실행 중인 봇 수
        running_result = await session.execute(
            select(func.count(BotStatus.user_id)).where(BotStatus.is_running == True)
        )
        running_bots = running_result.scalar() or 0

        # 정지 중인 봇 수
        paused_bots = total_bots - running_bots

        # 전략별 봇 분포
        strategy_result = await session.execute(
            select(Strategy.name, func.count(BotStatus.user_id))
            .join(BotStatus, Strategy.id == BotStatus.strategy_id)
            .group_by(Strategy.name)
        )
        strategy_distribution = {name: count for name, count in strategy_result.all()}

        return {
            "total_bots": total_bots,
            "running_bots": running_bots,
            "paused_bots": paused_bots,
            "strategy_distribution": strategy_distribution,
        }

    except Exception as e:
        structured_logger.error(
            "admin_bot_statistics_error",
            "Failed to fetch bot statistics",
            admin_id=admin_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch bot statistics: {str(e)}")
