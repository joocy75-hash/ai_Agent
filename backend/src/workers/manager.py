import asyncio
from sqlalchemy import select

from ..database.models import BotStatus
from ..services.bot_runner import BotRunner


class BotManager:
    def __init__(self, market_queue: asyncio.Queue, session_factory):
        self.market_queue = market_queue
        self.runner = BotRunner(market_queue)
        self.session_factory = session_factory

    async def bootstrap(self):
        async with self.session_factory() as session:
            result = await session.execute(select(BotStatus).where(BotStatus.is_running.is_(True)))
            for status in result.scalars():
                await self.runner.start(self.session_factory, status.user_id)

    async def start_bot(self, user_id: int):
        await self.runner.start(self.session_factory, user_id)

    async def stop_bot(self, user_id: int):
        self.runner.stop(user_id)
