from datetime import datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import BotLog

LogEvent = Literal[
    "strategy_signal",
    "order_execution",
    "risk_action",
    "ws_disconnection",
    "bot_restart",
    "pnl_update",
]


async def persist_log(session: AsyncSession, user_id: int, event_type: LogEvent, message: str):
    log = BotLog(user_id=user_id, event_type=event_type, message=message, created_at=datetime.utcnow())
    session.add(log)
    await session.commit()


def console_log(event_type: LogEvent, message: str):
    timestamp = datetime.utcnow().isoformat()
    print(f"[{timestamp}] [{event_type}] {message}")
