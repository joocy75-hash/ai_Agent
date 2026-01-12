"""
Authentication and Authorization Dependencies

FastAPI dependencies for checking user authentication and authorization.
"""

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import User
from .exceptions import AdminRequiredError, UserNotFoundError
from .jwt_auth import get_current_user_id


async def require_admin(
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> int:
    """
    관리자 권한 필수 Dependency

    JWT 토큰을 검증하고, 사용자가 관리자인지 확인합니다.

    Args:
        current_user_id: JWT에서 추출한 사용자 ID
        session: DB 세션

    Returns:
        관리자 사용자 ID

    Raises:
        UserNotFoundError: 사용자를 찾을 수 없는 경우
        AdminRequiredError: 관리자가 아닌 경우
    """
    # 사용자 조회
    result = await session.execute(
        select(User).where(User.id == current_user_id)
    )
    user = result.scalars().first()

    # 사용자가 없거나 관리자가 아닌 경우
    if not user:
        raise UserNotFoundError(current_user_id)

    if user.role != "admin":
        raise AdminRequiredError()

    return current_user_id
