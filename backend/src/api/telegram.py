"""
텔레그램 알림 설정 API
사용자별 텔레그램 설정을 데이터베이스에 영구 저장
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.db import get_session
from ..database.models import UserSettings
from ..utils.jwt_auth import get_current_user, TokenData
from ..services.telegram import init_telegram_notifier
from ..services.telegram.types import BotConfig, TradeInfo
from ..utils.crypto_secrets import encrypt_secret, decrypt_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramSettingsResponse(BaseModel):
    """텔레그램 설정 응답"""

    enabled: bool
    notify_trades: bool
    notify_system: bool
    notify_errors: bool
    chat_id_configured: bool
    bot_token_configured: bool
    # 마스킹된 설정 정보 (UI 표시용)
    masked_bot_token: Optional[str] = None
    masked_chat_id: Optional[str] = None


class TelegramSettingsRequest(BaseModel):
    """텔레그램 설정 저장 요청"""

    bot_token: str
    chat_id: str
    notify_trades: bool = True
    notify_system: bool = True
    notify_errors: bool = True


class TestMessageRequest(BaseModel):
    """테스트 메시지 요청"""

    message: Optional[str] = None


class TestMessageResponse(BaseModel):
    """테스트 메시지 응답"""

    success: bool
    message: str


def mask_token(token: str) -> str:
    """토큰을 마스킹 (앞 8자, 뒤 4자만 표시)"""
    if not token or len(token) < 12:
        return "***"
    return token[:8] + "..." + token[-4:]


def mask_chat_id(chat_id: str) -> str:
    """Chat ID를 마스킹 (앞 4자만 표시)"""
    if not chat_id or len(chat_id) < 5:
        return "***"
    return chat_id[:4] + "..." + chat_id[-2:]


@router.post("/settings")
async def save_telegram_settings(
    request: TelegramSettingsRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    텔레그램 설정 저장
    데이터베이스에 암호화하여 영구 저장
    """
    try:
        user_id = current_user.user_id

        if not request.bot_token or not request.chat_id:
            raise HTTPException(
                status_code=400,
                detail="Bot Token과 Chat ID를 모두 입력해주세요.",
            )

        # 먼저 연결 테스트
        # 보안: Bot Token과 Chat ID는 민감 정보이므로 로깅하지 않음
        logger.info(f"[Telegram] Testing connection for user {user_id}")

        test_notifier = init_telegram_notifier(
            bot_token=request.bot_token,
            chat_id=request.chat_id,
        )

        logger.info(f"[Telegram] Notifier enabled: {test_notifier.enabled}")

        connection_ok = await test_notifier.test_connection()
        logger.info(f"[Telegram] Connection test result: {connection_ok}")

        if not connection_ok:
            error_msg = "텔레그램 봇 연결에 실패했습니다. Bot Token과 Chat ID를 다시 확인해주세요."
            logger.warning(
                f"[Telegram] Connection failed for user {user_id}: {error_msg}"
            )
            return {
                "success": False,
                "message": error_msg,
                "enabled": False,
            }

        # 암호화
        logger.info(f"[Telegram] Encrypting secrets...")
        encrypted_bot_token = encrypt_secret(request.bot_token)
        encrypted_chat_id = encrypt_secret(request.chat_id)
        logger.info(f"[Telegram] Encryption successful")

        logger.info(f"[Telegram] Saving settings for user {user_id}")

        # 기존 설정 조회 또는 새로 생성
        result = await session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = result.scalars().first()

        if user_settings:
            # 기존 설정 업데이트
            user_settings.encrypted_telegram_bot_token = encrypted_bot_token
            user_settings.encrypted_telegram_chat_id = encrypted_chat_id
            user_settings.telegram_notify_trades = request.notify_trades
            user_settings.telegram_notify_system = request.notify_system
            user_settings.telegram_notify_errors = request.notify_errors
            logger.info(f"[Telegram] Updated existing settings for user {user_id}")
        else:
            # 새 설정 생성
            user_settings = UserSettings(
                user_id=user_id,
                encrypted_telegram_bot_token=encrypted_bot_token,
                encrypted_telegram_chat_id=encrypted_chat_id,
                telegram_notify_trades=request.notify_trades,
                telegram_notify_system=request.notify_system,
                telegram_notify_errors=request.notify_errors,
            )
            session.add(user_settings)
            logger.info(f"[Telegram] Created new settings for user {user_id}")

        await session.commit()
        logger.info(f"[Telegram] Settings saved successfully for user {user_id}")

        return {
            "success": True,
            "message": "텔레그램 설정이 저장되었습니다.",
            "enabled": True,
            "masked_bot_token": mask_token(request.bot_token),
            "masked_chat_id": mask_chat_id(request.chat_id),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[Telegram] Error saving settings: {type(e).__name__}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"텔레그램 설정 저장 중 오류 발생: {str(e)}"
        )


@router.get("/settings", response_model=TelegramSettingsResponse)
async def get_telegram_settings(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    텔레그램 알림 설정 조회
    데이터베이스에서 사용자별 설정 조회
    """
    user_id = current_user.user_id

    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalars().first()

    if not user_settings or not user_settings.encrypted_telegram_bot_token:
        # 설정이 없음
        return TelegramSettingsResponse(
            enabled=False,
            notify_trades=True,
            notify_system=True,
            notify_errors=True,
            chat_id_configured=False,
            bot_token_configured=False,
            masked_bot_token=None,
            masked_chat_id=None,
        )

    # 복호화하여 마스킹
    try:
        bot_token = decrypt_secret(user_settings.encrypted_telegram_bot_token)
        chat_id = decrypt_secret(user_settings.encrypted_telegram_chat_id)

        return TelegramSettingsResponse(
            enabled=bool(bot_token and chat_id),
            notify_trades=user_settings.telegram_notify_trades,
            notify_system=user_settings.telegram_notify_system,
            notify_errors=user_settings.telegram_notify_errors,
            chat_id_configured=bool(chat_id),
            bot_token_configured=bool(bot_token),
            masked_bot_token=mask_token(bot_token) if bot_token else None,
            masked_chat_id=mask_chat_id(chat_id) if chat_id else None,
        )
    except Exception as e:
        logger.error(f"[Telegram] Failed to decrypt settings for user {user_id}: {e}")
        return TelegramSettingsResponse(
            enabled=False,
            notify_trades=True,
            notify_system=True,
            notify_errors=True,
            chat_id_configured=False,
            bot_token_configured=False,
            masked_bot_token=None,
            masked_chat_id=None,
        )


@router.delete("/settings")
async def delete_telegram_settings(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    텔레그램 설정 삭제
    """
    user_id = current_user.user_id

    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalars().first()

    if user_settings:
        # 텔레그램 관련 필드만 초기화
        user_settings.encrypted_telegram_bot_token = None
        user_settings.encrypted_telegram_chat_id = None
        await session.commit()
        logger.info(f"[Telegram] Deleted settings for user {user_id}")
        return {"success": True, "message": "텔레그램 설정이 삭제되었습니다."}

    return {"success": True, "message": "삭제할 텔레그램 설정이 없습니다."}


@router.post("/test", response_model=TestMessageResponse)
async def send_test_message(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    테스트 메시지 전송
    """
    user_id = current_user.user_id

    # DB에서 설정 조회
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalars().first()

    if not user_settings or not user_settings.encrypted_telegram_bot_token:
        raise HTTPException(
            status_code=400,
            detail="텔레그램 설정이 없습니다. 먼저 설정을 저장해주세요.",
        )

    try:
        bot_token = decrypt_secret(user_settings.encrypted_telegram_bot_token)
        chat_id = decrypt_secret(user_settings.encrypted_telegram_chat_id)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="텔레그램 설정 복호화에 실패했습니다. 설정을 다시 저장해주세요.",
        )

    if not bot_token or not chat_id:
        raise HTTPException(
            status_code=400,
            detail="텔레그램 설정이 유효하지 않습니다.",
        )

    # 임시 notifier 생성하여 테스트 메시지 전송
    notifier = init_telegram_notifier(bot_token=bot_token, chat_id=chat_id)

    # 연결 테스트
    connection_ok = await notifier.test_connection()
    if not connection_ok:
        raise HTTPException(
            status_code=500, detail="텔레그램 봇 연결 실패. 토큰을 확인하세요."
        )

    # 테스트 메시지 전송
    success = await notifier.send_test_message()

    if success:
        return TestMessageResponse(
            success=True, message="테스트 메시지가 성공적으로 전송되었습니다."
        )
    else:
        raise HTTPException(status_code=500, detail="테스트 메시지 전송 실패")


@router.get("/status")
async def get_telegram_status(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    텔레그램 봇 상태 확인
    """
    user_id = current_user.user_id

    # DB에서 설정 조회
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalars().first()

    if not user_settings or not user_settings.encrypted_telegram_bot_token:
        return {
            "enabled": False,
            "connection_ok": False,
            "config": {
                "bot_token_set": False,
                "chat_id_set": False,
                "notify_trades": True,
                "notify_system": True,
                "notify_errors": True,
            },
            "masked_bot_token": None,
            "masked_chat_id": None,
        }

    try:
        bot_token = decrypt_secret(user_settings.encrypted_telegram_bot_token)
        chat_id = decrypt_secret(user_settings.encrypted_telegram_chat_id)
    except Exception:
        return {
            "enabled": False,
            "connection_ok": False,
            "config": {
                "bot_token_set": False,
                "chat_id_set": False,
                "notify_trades": user_settings.telegram_notify_trades,
                "notify_system": user_settings.telegram_notify_system,
                "notify_errors": user_settings.telegram_notify_errors,
            },
            "masked_bot_token": None,
            "masked_chat_id": None,
        }

    enabled = bool(bot_token and chat_id)
    connection_ok = False

    if enabled:
        # 연결 테스트
        notifier = init_telegram_notifier(bot_token=bot_token, chat_id=chat_id)
        connection_ok = await notifier.test_connection()

    return {
        "enabled": enabled,
        "connection_ok": connection_ok,
        "config": {
            "bot_token_set": bool(bot_token),
            "chat_id_set": bool(chat_id),
            "notify_trades": user_settings.telegram_notify_trades,
            "notify_system": user_settings.telegram_notify_system,
            "notify_errors": user_settings.telegram_notify_errors,
        },
        "masked_bot_token": mask_token(bot_token) if bot_token else None,
        "masked_chat_id": mask_chat_id(chat_id) if chat_id else None,
    }


# ==================== 알림 트리거 API (내부용) ====================


class NotifyTradeRequest(BaseModel):
    """거래 알림 요청"""

    symbol: str
    direction: str  # "Long" or "Short"
    entry_price: float
    quantity: float
    total_value: float
    leverage: int = 1


class NotifyBotStartRequest(BaseModel):
    """봇 시작 알림 요청"""

    exchange: str = "BITGET"
    trade_amount: float
    stop_loss_percent: float
    timeframe: str
    strategy: str
    leverage: int = 1
    margin_mode: str = "isolated"


@router.post("/notify/trade/open")
async def notify_trade_open(
    request: NotifyTradeRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    신규 거래 알림 전송 (내부 API)
    """
    user_id = current_user.user_id

    # DB에서 설정 조회
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalars().first()

    if not user_settings or not user_settings.encrypted_telegram_bot_token:
        return {"success": False, "message": "텔레그램 설정이 없습니다."}

    try:
        bot_token = decrypt_secret(user_settings.encrypted_telegram_bot_token)
        chat_id = decrypt_secret(user_settings.encrypted_telegram_chat_id)
    except Exception:
        return {"success": False, "message": "텔레그램 설정 복호화 실패"}

    notifier = init_telegram_notifier(bot_token=bot_token, chat_id=chat_id)

    trade = TradeInfo(
        symbol=request.symbol,
        direction=request.direction,
        entry_price=request.entry_price,
        quantity=request.quantity,
        total_value=request.total_value,
        leverage=request.leverage,
    )

    success = await notifier.notify_new_trade(trade)
    return {"success": success}


@router.post("/notify/bot/start")
async def notify_bot_start(
    request: NotifyBotStartRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    봇 시작 알림 전송 (내부 API)
    """
    user_id = current_user.user_id

    # DB에서 설정 조회
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalars().first()

    if not user_settings or not user_settings.encrypted_telegram_bot_token:
        return {"success": False, "message": "텔레그램 설정이 없습니다."}

    try:
        bot_token = decrypt_secret(user_settings.encrypted_telegram_bot_token)
        chat_id = decrypt_secret(user_settings.encrypted_telegram_chat_id)
    except Exception:
        return {"success": False, "message": "텔레그램 설정 복호화 실패"}

    notifier = init_telegram_notifier(bot_token=bot_token, chat_id=chat_id)

    config = BotConfig(
        exchange=request.exchange,
        trade_amount=request.trade_amount,
        stop_loss_percent=request.stop_loss_percent,
        timeframe=request.timeframe,
        strategy=request.strategy,
        leverage=request.leverage,
        margin_mode=request.margin_mode,
    )

    success = await notifier.notify_bot_start(config)
    return {"success": success}


@router.post("/notify/bot/stop")
async def notify_bot_stop(
    reason: str = "정상 종료",
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    봇 종료 알림 전송 (내부 API)
    """
    user_id = current_user.user_id

    # DB에서 설정 조회
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    user_settings = result.scalars().first()

    if not user_settings or not user_settings.encrypted_telegram_bot_token:
        return {"success": False, "message": "텔레그램 설정이 없습니다."}

    try:
        bot_token = decrypt_secret(user_settings.encrypted_telegram_bot_token)
        chat_id = decrypt_secret(user_settings.encrypted_telegram_chat_id)
    except Exception:
        return {"success": False, "message": "텔레그램 설정 복호화 실패"}

    notifier = init_telegram_notifier(bot_token=bot_token, chat_id=chat_id)
    success = await notifier.notify_bot_stop(reason=reason)
    return {"success": success}
