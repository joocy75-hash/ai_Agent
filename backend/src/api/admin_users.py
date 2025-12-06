from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ..database.db import get_session
from ..database.models import User, ApiKey, BotStatus, Trade
from ..schemas.admin_schema import ApiKeyCreate, ApiKeyUpdate, UserCreate
from ..utils.auth_dependencies import require_admin
from ..utils.crypto_secrets import encrypt_secret, decrypt_secret
from ..utils.structured_logging import get_logger
import logging

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def mask_api_key(key: str) -> str:
    """API 키 마스킹: 앞 4자리와 뒤 4자리만 보여주기"""
    if not key or len(key) <= 8:
        return "***"
    return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"


@router.post("")
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 새 사용자 생성

    필수 필드:
    - email: 이메일 주소
    - password: 비밀번호 (최소 8자)
    - role: 역할 ("user" 또는 "admin", 기본값: "user")

    반환:
    - 생성된 사용자 정보 (비밀번호 제외)
    """
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    try:
        # 이메일 중복 확인
        existing = await session.execute(
            select(User).where(User.email == payload.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다")

        # 사용자 생성
        new_user = User(
            email=payload.email,
            password_hash=pwd_context.hash(payload.password),
            role=payload.role,
            is_active=True,
        )

        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        structured_logger.info(
            "admin_user_created",
            f"Admin {admin_id} created new user",
            admin_id=admin_id,
            new_user_id=new_user.id,
            new_user_email=new_user.email,
            new_user_role=new_user.role,
        )

        return {
            "success": True,
            "message": "사용자가 생성되었습니다",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "role": new_user.role,
                "is_active": new_user.is_active,
                "created_at": new_user.created_at.isoformat()
                if new_user.created_at
                else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        structured_logger.error(
            "admin_user_create_error",
            "Failed to create user",
            admin_id=admin_id,
            email=payload.email,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"사용자 생성 실패: {str(e)}")


@router.get("")
async def get_users(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 모든 회원 목록 조회 (통계 포함)

    각 회원의 기본 정보와 함께 간단한 통계를 제공:
    - 총 거래 수
    - 총 손익 (P&L)
    - 활성 봇 수
    """
    result = await session.execute(select(User))
    users = result.scalars().all()

    users_with_stats = []
    for user in users:
        # 거래 통계
        trades_result = await session.execute(
            select(func.count(Trade.id), func.sum(Trade.pnl)).where(
                Trade.user_id == user.id
            )
        )
        trade_count, total_pnl = trades_result.first()

        # 활성 봇 수
        active_bots_result = await session.execute(
            select(func.count(BotStatus.user_id)).where(
                and_(BotStatus.user_id == user.id, BotStatus.is_running == True)
            )
        )
        active_bots_count = active_bots_result.scalar()

        users_with_stats.append(
            {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active if hasattr(user, "is_active") else True,
                "suspended_at": user.suspended_at.isoformat()
                if hasattr(user, "suspended_at") and user.suspended_at
                else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                # 통계
                "total_trades": trade_count or 0,
                "total_pnl": round(float(total_pnl), 2) if total_pnl else 0.0,
                "active_bots_count": active_bots_count or 0,
            }
        )

    return {"users": users_with_stats}


@router.get("/{user_id}")
async def get_user_detail(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 특정 회원 기본 정보 조회
    """
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active if hasattr(user, "is_active") else True,
        "suspended_at": user.suspended_at.isoformat()
        if hasattr(user, "suspended_at") and user.suspended_at
        else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/{user_id}/detail")
async def get_user_comprehensive_detail(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 특정 회원 종합 상세 정보 조회

    포함 정보:
    - 기본 회원 정보
    - 거래 통계 (총 거래 수, 승률, 손익)
    - 봇 현황
    - 최근 거래 내역
    - API 키 정보
    """
    # 사용자 기본 정보
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 거래 통계
    trades_result = await session.execute(select(Trade).where(Trade.user_id == user_id))
    trades = trades_result.scalars().all()

    total_trades = len(trades)
    total_pnl = sum(trade.pnl for trade in trades if trade.pnl is not None)
    winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
    losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0

    # 봇 현황
    bots_result = await session.execute(
        select(BotStatus).where(BotStatus.user_id == user_id)
    )
    bots = bots_result.scalars().all()

    active_bots_count = len([b for b in bots if b.is_running])

    # 최근 거래 내역 (최대 20개)
    recent_trades_result = await session.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.created_at.desc())
        .limit(20)
    )
    recent_trades = recent_trades_result.scalars().all()

    # API 키 정보
    api_key_result = await session.execute(
        select(ApiKey).where(ApiKey.user_id == user_id)
    )
    api_key = api_key_result.scalars().first()

    return {
        # 기본 정보
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active if hasattr(user, "is_active") else True,
        "suspended_at": user.suspended_at.isoformat()
        if hasattr(user, "suspended_at") and user.suspended_at
        else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        # 거래 통계
        "total_trades": total_trades,
        "total_pnl": round(total_pnl, 2),
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 1),
        "avg_pnl": round(avg_pnl, 2),
        "total_balance": 0.0,  # TODO: 실제 잔고 조회 구현
        # 봇 정보
        "active_bots_count": active_bots_count,
        "bots": [
            {
                "id": bot.user_id,
                "strategy_name": "N/A",  # BotStatus에는 strategy_name이 없음
                "symbol": "N/A",  # BotStatus에는 symbol이 없음
                "status": "running" if bot.is_running else "stopped",
                "started_at": bot.updated_at.isoformat() if bot.updated_at else None,
                "pnl": 0.0,  # BotStatus에는 pnl 정보 없음
            }
            for bot in bots
        ],
        # 최근 거래
        "recent_trades": [
            {
                "symbol": trade.symbol,
                "side": trade.side,
                "entry_price": float(trade.entry_price) if trade.entry_price else 0.0,
                "exit_price": float(trade.exit_price) if trade.exit_price else 0.0,
                "qty": float(trade.qty) if trade.qty else 0.0,
                "pnl": round(float(trade.pnl), 2) if trade.pnl else 0.0,
                "created_at": trade.created_at.isoformat()
                if trade.created_at
                else None,
            }
            for trade in recent_trades
        ],
        # API 키 정보
        "has_api_keys": api_key is not None,
        "api_key_created_at": api_key.created_at.isoformat()
        if api_key and hasattr(api_key, "created_at") and api_key.created_at
        else None,
        "api_key_last_used": None,  # TODO: 마지막 사용 시각 추적 구현 시 추가
    }


@router.get("/{user_id}/api-keys")
async def get_user_api_keys(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 특정 회원의 거래소 API 키 목록 조회
    """
    result = await session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
    api_keys = result.scalars().all()

    return {
        "api_keys": [
            {
                "id": key.id,
                "user_id": key.user_id,
                "exchange": "BITGET",  # 현재는 BITGET 지원
                "api_key": mask_api_key(decrypt_secret(key.encrypted_api_key)),
                "secret_key": mask_api_key(
                    decrypt_secret(key.encrypted_secret_key)
                    if key.encrypted_secret_key
                    else ""
                ),
                "passphrase": mask_api_key(
                    decrypt_secret(key.encrypted_passphrase)
                    if key.encrypted_passphrase
                    else ""
                ),
                "has_secret": bool(key.encrypted_secret_key),
                "has_passphrase": bool(key.encrypted_passphrase),
            }
            for key in api_keys
        ]
    }


@router.post("/{user_id}/api-keys")
async def create_user_api_key(
    user_id: int,
    payload: ApiKeyCreate,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 특정 회원의 거래소 API 키 등록
    """
    # 사용자 존재 확인
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # API 키 암호화 및 저장
    api_key = ApiKey(
        user_id=user_id,
        encrypted_api_key=encrypt_secret(payload.api_key),
        encrypted_secret_key=encrypt_secret(payload.secret_key),
        encrypted_passphrase=encrypt_secret(payload.passphrase)
        if payload.passphrase
        else None,
    )

    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    return {
        "id": api_key.id,
        "user_id": api_key.user_id,
        "exchange": "BITGET",
        "message": "API key created successfully",
    }


@router.put("/{user_id}/api-keys/{api_key_id}")
async def update_user_api_key(
    user_id: int,
    api_key_id: int,
    payload: ApiKeyUpdate,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 특정 회원의 거래소 API 키 수정
    """
    result = await session.execute(
        select(ApiKey).where(ApiKey.id == api_key_id).where(ApiKey.user_id == user_id)
    )
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # 필드 업데이트
    if payload.api_key:
        api_key.encrypted_api_key = encrypt_secret(payload.api_key)
    if payload.secret_key:
        api_key.encrypted_secret_key = encrypt_secret(payload.secret_key)
    if payload.passphrase:
        api_key.encrypted_passphrase = encrypt_secret(payload.passphrase)

    await session.commit()
    await session.refresh(api_key)

    return {
        "id": api_key.id,
        "user_id": api_key.user_id,
        "exchange": "BITGET",
        "message": "API key updated successfully",
    }


@router.delete("/{user_id}/api-keys/{api_key_id}")
async def delete_user_api_key(
    user_id: int,
    api_key_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 특정 회원의 거래소 API 키 삭제
    """
    result = await session.execute(
        select(ApiKey).where(ApiKey.id == api_key_id).where(ApiKey.user_id == user_id)
    )
    api_key = result.scalars().first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    await session.delete(api_key)
    await session.commit()

    return {"message": "API key deleted successfully"}


@router.post("/{user_id}/suspend")
async def suspend_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 사용자 계정 정지

    계정 정지 시:
    - is_active = False로 설정
    - suspended_at 시각 기록
    - 해당 사용자의 봇 자동 정지

    Args:
        user_id: 정지할 사용자 ID

    Returns:
        계정 정지 결과
    """
    try:
        # 사용자 확인
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 이미 정지된 경우
        if not user.is_active:
            return {
                "success": True,
                "message": f"User {user_id} ({user.email}) is already suspended",
                "was_active": False,
            }

        # 계정 정지
        user.is_active = False
        user.suspended_at = datetime.utcnow()

        # 사용자의 봇도 정지
        bot_result = await session.execute(
            select(BotStatus).where(BotStatus.user_id == user_id)
        )
        bot_status = bot_result.scalar_one_or_none()

        bot_was_running = False
        if bot_status and bot_status.is_running:
            bot_status.is_running = False
            bot_was_running = True

        await session.commit()

        structured_logger.warning(
            "admin_user_suspended",
            f"Admin {admin_id} suspended user {user_id}",
            admin_id=admin_id,
            target_user_id=user_id,
            target_user_email=user.email,
            bot_was_running=bot_was_running,
            suspended_at=user.suspended_at.isoformat(),
        )

        return {
            "success": True,
            "message": f"User {user_id} ({user.email}) has been suspended",
            "was_active": True,
            "bot_stopped": bot_was_running,
            "suspended_at": user.suspended_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        structured_logger.error(
            "admin_user_suspend_error",
            "Failed to suspend user",
            admin_id=admin_id,
            target_user_id=user_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to suspend user: {str(e)}")


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 사용자 계정 활성화

    계정 활성화 시:
    - is_active = True로 설정
    - suspended_at 시각 제거
    - 봇은 자동으로 재시작하지 않음 (사용자가 수동으로 시작해야 함)

    Args:
        user_id: 활성화할 사용자 ID

    Returns:
        계정 활성화 결과
    """
    try:
        # 사용자 확인
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 이미 활성화된 경우
        if user.is_active:
            return {
                "success": True,
                "message": f"User {user_id} ({user.email}) is already active",
                "was_suspended": False,
            }

        # 계정 활성화
        user.is_active = True
        user.suspended_at = None

        await session.commit()

        structured_logger.info(
            "admin_user_activated",
            f"Admin {admin_id} activated user {user_id}",
            admin_id=admin_id,
            target_user_id=user_id,
            target_user_email=user.email,
        )

        return {
            "success": True,
            "message": f"User {user_id} ({user.email}) has been activated",
            "was_suspended": True,
            "note": "Bot will NOT auto-restart. User must manually start their bot.",
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        structured_logger.error(
            "admin_user_activate_error",
            "Failed to activate user",
            admin_id=admin_id,
            target_user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to activate user: {str(e)}"
        )


@router.post("/{user_id}/force-logout")
async def force_logout_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 사용자 강제 로그아웃

    강제 로그아웃 시:
    - 현재는 JWT 토큰 기반이므로 토큰을 무효화할 수 없음
    - 대신 계정을 일시적으로 비활성화했다가 다시 활성화
    - 또는 사용자에게 재로그인 요구 (프론트엔드 처리)

    TODO: 향후 Redis 기반 토큰 블랙리스트 구현 시 개선

    Args:
        user_id: 강제 로그아웃할 사용자 ID

    Returns:
        강제 로그아웃 결과
    """
    try:
        # 사용자 확인
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 사용자의 봇 정지
        bot_result = await session.execute(
            select(BotStatus).where(BotStatus.user_id == user_id)
        )
        bot_status = bot_result.scalar_one_or_none()

        bot_was_running = False
        if bot_status and bot_status.is_running:
            bot_status.is_running = False
            bot_was_running = True

        await session.commit()

        structured_logger.warning(
            "admin_user_forced_logout",
            f"Admin {admin_id} forced logout for user {user_id}",
            admin_id=admin_id,
            target_user_id=user_id,
            target_user_email=user.email,
            bot_stopped=bot_was_running,
        )

        return {
            "success": True,
            "message": f"User {user_id} ({user.email}) has been forced to logout",
            "bot_stopped": bot_was_running,
            "note": "User's bot has been stopped. User will need to re-login to continue.",
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        structured_logger.error(
            "admin_user_force_logout_error",
            "Failed to force logout user",
            admin_id=admin_id,
            target_user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to force logout user: {str(e)}"
        )


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 사용자 비밀번호 초기화

    비밀번호를 랜덤 문자열로 초기화하고 반환합니다.
    사용자에게 새 비밀번호를 안내해야 합니다.
    """
    import secrets
    import string
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    try:
        # 사용자 확인
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 관리자 본인 비밀번호는 초기화 불가
        if user_id == admin_id:
            raise HTTPException(
                status_code=400, detail="Cannot reset your own password via admin API"
            )

        # 랜덤 비밀번호 생성 (12자리: 대문자, 소문자, 숫자, 특수문자 포함)
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        new_password = "".join(secrets.choice(alphabet) for _ in range(12))

        # 비밀번호 해시화 저장
        user.password_hash = pwd_context.hash(new_password)
        await session.commit()

        structured_logger.warning(
            "admin_password_reset",
            f"Admin {admin_id} reset password for user {user_id}",
            admin_id=admin_id,
            target_user_id=user_id,
            target_user_email=user.email,
        )

        return {
            "success": True,
            "message": f"비밀번호가 초기화되었습니다.",
            "user_id": user_id,
            "email": user.email,
            "new_password": new_password,  # 주의: 이 비밀번호를 사용자에게 안전하게 전달해야 함
            "notice": "사용자에게 새 비밀번호를 안전하게 전달하세요. 이 비밀번호는 다시 조회할 수 없습니다.",
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        structured_logger.error(
            "admin_password_reset_error",
            "Failed to reset password",
            admin_id=admin_id,
            target_user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to reset password: {str(e)}"
        )


@router.put("/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: str,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 사용자 역할 변경

    role: 'user' 또는 'admin'
    """
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

    try:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 자기 자신의 역할은 변경 불가 (실수 방지)
        if user_id == admin_id:
            raise HTTPException(status_code=400, detail="Cannot change your own role")

        old_role = user.role
        user.role = role
        await session.commit()

        structured_logger.warning(
            "admin_role_changed",
            f"Admin {admin_id} changed role for user {user_id}",
            admin_id=admin_id,
            target_user_id=user_id,
            old_role=old_role,
            new_role=role,
        )

        return {
            "success": True,
            "message": f"역할이 변경되었습니다: {old_role} → {role}",
            "user_id": user_id,
            "old_role": old_role,
            "new_role": role,
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to change role: {str(e)}")


@router.get("/{user_id}/profit-stats")
async def get_user_profit_stats(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 사용자 상세 수익 통계

    일별, 주별, 월별 수익 통계 및 상세 지표 제공
    """
    from datetime import timedelta

    try:
        # 사용자 확인
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        # 전체 거래 조회
        trades_result = await session.execute(
            select(Trade).where(Trade.user_id == user_id)
        )
        all_trades = trades_result.scalars().all()

        # 오늘 거래 필터
        today_trades = [
            t for t in all_trades if t.created_at and t.created_at >= today_start
        ]
        week_trades = [
            t for t in all_trades if t.created_at and t.created_at >= week_start
        ]
        month_trades = [
            t for t in all_trades if t.created_at and t.created_at >= month_start
        ]

        def calc_stats(trades):
            if not trades:
                return {
                    "total_trades": 0,
                    "total_pnl": 0.0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "avg_pnl": 0.0,
                    "max_profit": 0.0,
                    "max_loss": 0.0,
                    "profit_factor": 0.0,
                }

            total = len(trades)
            pnl_values = [t.pnl for t in trades if t.pnl is not None]
            total_pnl = sum(pnl_values) if pnl_values else 0
            wins = [p for p in pnl_values if p > 0]
            losses = [p for p in pnl_values if p < 0]

            total_wins = sum(wins) if wins else 0
            total_losses = abs(sum(losses)) if losses else 0
            profit_factor = (total_wins / total_losses) if total_losses > 0 else 0

            return {
                "total_trades": total,
                "total_pnl": round(total_pnl, 2),
                "winning_trades": len(wins),
                "losing_trades": len(losses),
                "win_rate": round(len(wins) / total * 100, 1) if total > 0 else 0.0,
                "avg_pnl": round(total_pnl / total, 2) if total > 0 else 0.0,
                "max_profit": round(max(pnl_values), 2) if pnl_values else 0.0,
                "max_loss": round(min(pnl_values), 2) if pnl_values else 0.0,
                "profit_factor": round(profit_factor, 2),
            }

        # 일별 수익 (최근 7일)
        daily_pnl = []
        for i in range(7):
            day = today_start - timedelta(days=i)
            day_end = day + timedelta(days=1)
            day_trades = [
                t for t in all_trades if t.created_at and day <= t.created_at < day_end
            ]
            day_pnl = sum(t.pnl for t in day_trades if t.pnl is not None)
            daily_pnl.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "pnl": round(day_pnl, 2),
                    "trades": len(day_trades),
                }
            )

        return {
            "user_id": user_id,
            "email": user.email,
            "today": calc_stats(today_trades),
            "week": calc_stats(week_trades),
            "month": calc_stats(month_trades),
            "all_time": calc_stats(all_trades),
            "daily_pnl": daily_pnl[::-1],  # 오래된 순서로 정렬
            "generated_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get profit stats: {str(e)}"
        )


@router.delete("/{user_id}/api-keys/all")
async def delete_all_user_api_keys(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),
):
    """
    관리자 전용: 사용자의 모든 API 키 삭제

    보안 위협 시 긴급하게 API 키를 무효화할 때 사용
    """
    try:
        # 사용자 확인
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # API 키 조회
        keys_result = await session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id)
        )
        api_keys = keys_result.scalars().all()

        deleted_count = len(api_keys)

        # 모든 키 삭제
        for key in api_keys:
            await session.delete(key)

        # 봇도 정지
        bot_result = await session.execute(
            select(BotStatus).where(BotStatus.user_id == user_id)
        )
        bot_status = bot_result.scalar_one_or_none()

        bot_was_running = False
        if bot_status and bot_status.is_running:
            bot_status.is_running = False
            bot_was_running = True

        await session.commit()

        structured_logger.warning(
            "admin_api_keys_deleted",
            f"Admin {admin_id} deleted all API keys for user {user_id}",
            admin_id=admin_id,
            target_user_id=user_id,
            deleted_count=deleted_count,
            bot_stopped=bot_was_running,
        )

        return {
            "success": True,
            "message": f"{deleted_count}개의 API 키가 삭제되었습니다.",
            "user_id": user_id,
            "deleted_count": deleted_count,
            "bot_stopped": bot_was_running,
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete API keys: {str(e)}"
        )
