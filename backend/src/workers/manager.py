"""
봇 관리자 (Bot Manager)

다중 봇 시스템 지원 버전
- 기존: user_id 기반 (하위 호환성 유지)
- 신규: bot_instance_id 기반 (다중 봇)

관련 문서: docs/MULTI_BOT_03_IMPLEMENTATION.md
"""

import asyncio
import logging
from typing import List, Set

from sqlalchemy import and_, select

from ..database.models import BotInstance, BotStatus
from ..services.bot_runner import BotRunner

logger = logging.getLogger(__name__)


class BotManager:
    """
    봇 생명주기 관리자

    역할:
    1. 서버 시작 시 실행 중이던 봇 복구 (bootstrap)
    2. 봇 시작/정지 API 처리
    3. 다중 봇 인스턴스 관리 (NEW)
    """

    def __init__(self, market_queue: asyncio.Queue, session_factory):
        self.market_queue = market_queue
        self.runner = BotRunner(market_queue)
        self.session_factory = session_factory

    async def bootstrap(self):
        """
        서버 시작 시 DB에서 is_running=True인 봇들을 복구합니다.
        - 기존 BotStatus 테이블 (하위 호환성)
        - 신규 BotInstance 테이블 (다중 봇)
        """
        # 1. 기존 시스템 복구 (BotStatus)
        await self._bootstrap_legacy_bots()

        # 2. 다중 봇 시스템 복구 (BotInstance)
        await self._bootstrap_bot_instances()

    async def _bootstrap_legacy_bots(self):
        """기존 BotStatus 테이블 기반 봇 복구 (하위 호환성)"""
        started_count = 0
        failed_count = 0

        async with self.session_factory() as session:
            result = await session.execute(
                select(BotStatus).where(BotStatus.is_running.is_(True))
            )
            bot_statuses = list(result.scalars())

            if not bot_statuses:
                logger.info("No legacy bots to restore")
                return

            logger.info(f"Found {len(bot_statuses)} legacy bot(s) to restore")

            for status in bot_statuses:
                try:
                    from ..utils.log_broadcaster import attach_log_handler
                    attach_log_handler(status.user_id)

                    await self.runner.start(self.session_factory, status.user_id)
                    started_count += 1
                    logger.info(f"✅ Legacy bot restored for user {status.user_id}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Failed to restore legacy bot for user {status.user_id}: {e}")

            logger.info(
                f"Legacy bot bootstrap: {started_count} started, {failed_count} failed"
            )

    async def _bootstrap_bot_instances(self):
        """다중 봇 시스템 BotInstance 테이블 기반 봇 복구"""
        started_count = 0
        failed_count = 0

        async with self.session_factory() as session:
            result = await session.execute(
                select(BotInstance).where(
                    and_(
                        BotInstance.is_running.is_(True),
                        BotInstance.is_active.is_(True)
                    )
                )
            )
            bot_instances = list(result.scalars())

            if not bot_instances:
                logger.info("No bot instances to restore")
                return

            logger.info(f"Found {len(bot_instances)} bot instance(s) to restore")

            for instance in bot_instances:
                try:
                    from ..utils.log_broadcaster import attach_log_handler
                    attach_log_handler(instance.user_id)

                    await self.runner.start_instance(
                        self.session_factory,
                        instance.id,
                        instance.user_id
                    )
                    started_count += 1
                    logger.info(
                        f"✅ Bot instance '{instance.name}' (ID: {instance.id}) "
                        f"restored for user {instance.user_id}"
                    )
                except Exception as e:
                    failed_count += 1
                    logger.error(
                        f"❌ Failed to restore bot instance {instance.id}: {e}"
                    )

            logger.info(
                f"Bot instance bootstrap: {started_count} started, {failed_count} failed"
            )

    # ============================================================
    # 기존 API (하위 호환성)
    # ============================================================

    async def start_bot(self, user_id: int):
        """기존 시스템: 사용자별 단일 봇 시작"""
        from ..utils.log_broadcaster import attach_log_handler
        attach_log_handler(user_id)

        await self.runner.start(self.session_factory, user_id)

    async def stop_bot(self, user_id: int):
        """기존 시스템: 사용자별 단일 봇 정지"""
        from ..utils.log_broadcaster import detach_log_handler
        detach_log_handler(user_id)

        self.runner.stop(user_id)

    def is_bot_running(self, user_id: int) -> bool:
        """기존 시스템: 봇 실행 상태 확인"""
        return self.runner.is_running(user_id)

    # ============================================================
    # 다중 봇 시스템 API (NEW)
    # ============================================================

    async def start_bot_instance(self, bot_instance_id: int, user_id: int):
        """
        봇 인스턴스 시작 (다중 봇)

        Args:
            bot_instance_id: 봇 인스턴스 ID
            user_id: 사용자 ID
        """
        from ..utils.log_broadcaster import attach_log_handler
        attach_log_handler(user_id)

        await self.runner.start_instance(
            self.session_factory,
            bot_instance_id,
            user_id
        )
        logger.info(f"Bot instance {bot_instance_id} started for user {user_id}")

    async def stop_bot_instance(self, bot_instance_id: int, user_id: int):
        """
        봇 인스턴스 정지 (다중 봇)

        Args:
            bot_instance_id: 봇 인스턴스 ID
            user_id: 사용자 ID
        """
        self.runner.stop_instance(bot_instance_id, user_id)
        logger.info(f"Bot instance {bot_instance_id} stopped for user {user_id}")

        # 사용자의 모든 봇이 정지되면 로그 핸들러 제거
        if self.runner.get_running_instance_count(user_id) == 0:
            from ..utils.log_broadcaster import detach_log_handler
            detach_log_handler(user_id)

    def is_instance_running(self, bot_instance_id: int) -> bool:
        """봇 인스턴스 실행 상태 확인"""
        return self.runner.is_instance_running(bot_instance_id)

    def get_user_running_instances(self, user_id: int) -> Set[int]:
        """사용자의 실행 중인 봇 인스턴스 ID 목록"""
        return self.runner.get_user_running_bots(user_id)

    def get_running_instance_count(self, user_id: int) -> int:
        """사용자의 실행 중인 봇 인스턴스 수"""
        return self.runner.get_running_instance_count(user_id)

    async def stop_all_user_instances(self, user_id: int):
        """사용자의 모든 봇 인스턴스 정지"""
        await self.runner.stop_all_user_instances(user_id)

        from ..utils.log_broadcaster import detach_log_handler
        detach_log_handler(user_id)

        logger.info(f"All bot instances stopped for user {user_id}")

    async def start_multiple_instances(
        self,
        bot_instance_ids: List[int],
        user_id: int
    ):
        """여러 봇 인스턴스 동시 시작"""
        from ..utils.log_broadcaster import attach_log_handler
        attach_log_handler(user_id)

        started = 0
        failed = 0

        for bot_id in bot_instance_ids:
            try:
                await self.runner.start_instance(
                    self.session_factory,
                    bot_id,
                    user_id
                )
                started += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to start bot instance {bot_id}: {e}")

        logger.info(
            f"Started {started}/{len(bot_instance_ids)} bot instances "
            f"for user {user_id} ({failed} failed)"
        )
        return started, failed
