"""
멀티봇 매니저 서비스

여러 봇 인스턴스의 생성, 관리, 모니터링을 담당
- TrendBotTemplate에서 봇 생성
- 최대 5개 봇 제한
- 동일 심볼 중복 방지
"""
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import BotInstance, BotType, TrendBotTemplate

logger = logging.getLogger(__name__)


class MultiBotManager:
    MAX_BOTS_PER_USER = 5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_templates(self) -> List[TrendBotTemplate]:
        """활성화된 전략 템플릿 목록"""
        result = await self.db.execute(
            select(TrendBotTemplate)
            .where(TrendBotTemplate.is_active is True)
            .order_by(TrendBotTemplate.is_featured.desc(), TrendBotTemplate.sort_order)
        )
        return result.scalars().all()

    async def get_template(self, template_id: int) -> Optional[TrendBotTemplate]:
        """전략 템플릿 상세"""
        return await self.db.get(TrendBotTemplate, template_id)

    async def start_bot(self, user_id: int, template_id: int, amount: float, name: str = None) -> BotInstance:
        """새 봇 시작"""
        # 1. 템플릿 확인
        template = await self.db.get(TrendBotTemplate, template_id)
        if not template or not template.is_active:
            raise ValueError("유효하지 않은 전략입니다")

        # 2. 금액 범위 확인
        if amount < float(template.min_investment):
            raise ValueError(f"최소 투자금은 ${template.min_investment}입니다")

        # 3. 최대 봇 개수 확인
        running_bots = await self.get_user_bots(user_id, running_only=True)
        if len(running_bots) >= self.MAX_BOTS_PER_USER:
            raise ValueError(f"최대 {self.MAX_BOTS_PER_USER}개의 봇만 운용할 수 있습니다")

        # 4. 동일 심볼 봇 중복 확인
        existing = await self._get_running_bot_by_symbol(user_id, template.symbol)
        if existing:
            raise ValueError(f"{template.symbol} 봇이 이미 실행 중입니다")

        # 5. 봇 인스턴스 생성
        bot_name = name or f"{template.name} Bot"
        bot_instance = BotInstance(
            user_id=user_id,
            trend_template_id=template_id,
            name=bot_name,
            bot_type=BotType.AI_TREND,
            symbol=template.symbol,
            allocated_amount=amount,
            max_leverage=template.leverage,
            stop_loss_percent=template.stop_loss_percent,
            take_profit_percent=template.take_profit_percent,
            is_running=True,
            is_active=True,
            last_started_at=datetime.utcnow(),
        )

        self.db.add(bot_instance)

        # 6. 템플릿 사용자 수 증가
        template.active_users = (template.active_users or 0) + 1
        template.total_users = (template.total_users or 0) + 1

        await self.db.commit()
        await self.db.refresh(bot_instance)

        logger.info(f"Bot started: user={user_id}, template={template.strategy_type}, amount=${amount}")

        return bot_instance

    async def stop_bot(self, user_id: int, bot_id: int) -> bool:
        """봇 중지"""
        result = await self.db.execute(
            select(BotInstance).where(
                and_(
                    BotInstance.id == bot_id,
                    BotInstance.user_id == user_id,
                    BotInstance.is_running is True
                )
            )
        )
        bot = result.scalar_one_or_none()

        if not bot:
            return False

        bot.is_running = False
        bot.last_stopped_at = datetime.utcnow()

        # 템플릿 활성 사용자 수 감소
        if bot.trend_template_id:
            template = await self.db.get(TrendBotTemplate, bot.trend_template_id)
            if template and template.active_users > 0:
                template.active_users -= 1

        await self.db.commit()

        logger.info(f"Bot stopped: user={user_id}, bot_id={bot_id}")
        return True

    async def get_user_bots(self, user_id: int, running_only: bool = False) -> List[BotInstance]:
        """사용자 봇 목록"""
        query = select(BotInstance).where(
            and_(
                BotInstance.user_id == user_id,
                BotInstance.is_active is True
            )
        )

        if running_only:
            query = query.where(BotInstance.is_running is True)

        query = query.order_by(BotInstance.created_at.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_bot_by_id(self, user_id: int, bot_id: int) -> Optional[BotInstance]:
        """봇 ID로 조회"""
        result = await self.db.execute(
            select(BotInstance).where(
                and_(
                    BotInstance.id == bot_id,
                    BotInstance.user_id == user_id,
                    BotInstance.is_active is True
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_running_bot_by_symbol(self, user_id: int, symbol: str) -> Optional[BotInstance]:
        """심볼로 실행 중인 봇 조회"""
        result = await self.db.execute(
            select(BotInstance).where(
                and_(
                    BotInstance.user_id == user_id,
                    BotInstance.symbol == symbol,
                    BotInstance.is_running is True
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_total_allocated(self, user_id: int) -> float:
        """사용자의 총 할당 금액 조회"""
        bots = await self.get_user_bots(user_id, running_only=True)
        return sum(float(b.allocated_amount or 0) for b in bots)
