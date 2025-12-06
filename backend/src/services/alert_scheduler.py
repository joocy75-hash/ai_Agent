import asyncio
import logging
from typing import Set
from sqlalchemy import select
from ..database.models import User, BotStatus
from ..database.db import AsyncSessionLocal
from .alert_monitor import alert_monitor

logger = logging.getLogger(__name__)


class AlertScheduler:
    """알림 모니터링 스케줄러"""

    def __init__(self):
        self.running = False
        self.active_users: Set[int] = set()
        self.check_interval = 60  # 60초마다 체크

    async def get_active_users(self) -> Set[int]:
        """활성 사용자 목록 조회 (봇이 실행 중인 사용자)"""
        try:
            async with AsyncSessionLocal() as session:
                # 봇이 실행 중인 사용자 조회
                result = await session.execute(
                    select(BotStatus.user_id).where(BotStatus.is_running == True)
                )
                user_ids = set(result.scalars().all())

                logger.debug(f"Active users: {user_ids}")
                return user_ids

        except Exception as e:
            logger.error(f"Failed to get active users: {e}")
            return set()

    async def check_user_alerts(self, user_id: int):
        """특정 사용자의 알림 체크"""
        try:
            await alert_monitor.run_all_checks(user_id)
        except Exception as e:
            logger.error(f"Failed to check alerts for user {user_id}: {e}")

    async def run(self):
        """스케줄러 실행"""
        self.running = True
        logger.info("Alert scheduler started")

        while self.running:
            try:
                # 활성 사용자 조회
                self.active_users = await self.get_active_users()

                # 각 사용자에 대해 알림 체크
                if self.active_users:
                    tasks = [
                        self.check_user_alerts(user_id) for user_id in self.active_users
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    logger.info(
                        f"Alert checks completed for {len(self.active_users)} users"
                    )

                # 다음 체크까지 대기
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in alert scheduler: {e}")
                await asyncio.sleep(self.check_interval)

    async def start(self):
        """스케줄러 시작"""
        if not self.running:
            asyncio.create_task(self.run())

    async def stop(self):
        """스케줄러 중지"""
        self.running = False
        logger.info("Alert scheduler stopped")


# 싱글톤 인스턴스
alert_scheduler = AlertScheduler()
