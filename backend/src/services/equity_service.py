from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Equity


async def record_equity(session: AsyncSession, user_id: int, value: float):
    equity = Equity(user_id=user_id, value=Decimal(str(value)), timestamp=datetime.utcnow())
    session.add(equity)
    await session.commit()
    return equity
