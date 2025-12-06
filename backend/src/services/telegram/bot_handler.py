"""
텔레그램 봇 명령어 핸들러
사용자의 버튼 클릭/명령어에 응답합니다.
"""

import asyncio
import logging
from typing import Optional, Callable, Dict
from datetime import datetime

import httpx

from .notifier import TelegramNotifier, get_telegram_notifier

logger = logging.getLogger(__name__)


class TelegramBotHandler:
    """텔레그램 봇 명령어 핸들러"""

    def __init__(self, notifier: Optional[TelegramNotifier] = None):
        self.notifier = notifier or get_telegram_notifier()
        self.bot_token = self.notifier.bot_token
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.last_update_id = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # 명령어 핸들러 매핑
        self.commands: Dict[str, Callable] = {
            # 한국어 버튼
            "📊 오늘 현황": self.handle_daily,
            "💰 수익": self.handle_profit,
            "💵 잔고": self.handle_balance,
            "📈 상태": self.handle_status,
            "📋 상태표": self.handle_status_table,
            "📉 성과": self.handle_performance,
            "🔢 거래횟수": self.handle_count,
            "▶️ 시작": self.handle_start_bot,
            "⏹️ 정지": self.handle_stop_bot,
            "❓ 도움말": self.handle_help,
            # 슬래시 명령어
            "/start": self.handle_welcome,
            "/help": self.handle_help,
            "/daily": self.handle_daily,
            "/profit": self.handle_profit,
            "/balance": self.handle_balance,
            "/status": self.handle_status,
            "/performance": self.handle_performance,
            "/count": self.handle_count,
        }

    async def _get_updates(self, offset: int = 0, timeout: int = 30) -> list:
        """텔레그램 업데이트 가져오기 (Long Polling)"""
        try:
            async with httpx.AsyncClient(timeout=timeout + 10) as client:
                response = await client.get(
                    f"{self.base_url}/getUpdates",
                    params={
                        "offset": offset,
                        "timeout": timeout,
                        "allowed_updates": ["message"],
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        return data.get("result", [])
        except Exception as e:
            logger.error(f"텔레그램 업데이트 조회 실패: {e}")
        return []

    async def start_polling(self):
        """Long Polling 시작"""
        if self._running:
            return

        self._running = True
        logger.info("🤖 텔레그램 봇 핸들러 시작됨")

        while self._running:
            try:
                updates = await self._get_updates(offset=self.last_update_id + 1)

                for update in updates:
                    self.last_update_id = update["update_id"]
                    await self._process_update(update)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"봇 핸들러 에러: {e}")
                await asyncio.sleep(5)

        logger.info("🤖 텔레그램 봇 핸들러 종료됨")

    def stop_polling(self):
        """Polling 중지"""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _process_update(self, update: dict):
        """업데이트 처리"""
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")

        if not text or not chat_id:
            return

        logger.info(f"📩 받은 메시지: {text} (chat_id: {chat_id})")

        # 명령어 핸들러 찾기
        handler = self.commands.get(text)
        if handler:
            try:
                await handler(chat_id)
            except Exception as e:
                logger.error(f"명령어 처리 실패: {e}")
                await self._send_error(chat_id, str(e))
        else:
            # 알 수 없는 명령어
            await self._send_unknown_command(chat_id)

    async def _send_message(self, chat_id: int, text: str, keyboard: bool = True):
        """메시지 전송"""
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}

        if keyboard:
            data["reply_markup"] = {
                "keyboard": [
                    [
                        {"text": "📊 오늘 현황"},
                        {"text": "💰 수익"},
                        {"text": "💵 잔고"},
                    ],
                    [{"text": "📈 상태"}, {"text": "📋 상태표"}, {"text": "📉 성과"}],
                    [
                        {"text": "🔢 거래횟수"},
                        {"text": "▶️ 시작"},
                        {"text": "⏹️ 정지"},
                        {"text": "❓ 도움말"},
                    ],
                ],
                "resize_keyboard": True,
            }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.post(f"{self.base_url}/sendMessage", json=data)
        except Exception as e:
            logger.error(f"메시지 전송 실패: {e}")

    # ==================== 명령어 핸들러 ====================

    async def handle_welcome(self, chat_id: int):
        """환영 메시지"""
        msg = """🤖 <b>비트해커 트레이딩 봇</b>

안녕하세요! AI 자동매매 봇입니다.
아래 버튼을 눌러 사용하세요.

━━━━━━━━━━━━━━━━━━━━━
📊 <b>조회</b>: 오늘 현황, 수익, 잔고, 상태
🤖 <b>제어</b>: 시작, 정지
ℹ️ <b>도움</b>: 도움말"""
        await self._send_message(chat_id, msg)

    async def handle_help(self, chat_id: int):
        """도움말"""
        msg = """📚 <b>명령어 도움말</b>

<b>📊 조회 명령어</b>
━━━━━━━━━━━━━━━━━━━━━
📊 오늘 현황 - 오늘 거래 현황
💰 수익 - 수익 요약
💵 잔고 - 잔고 조회
📈 상태 - 봇 상태 확인
📉 성과 - 성과 분석

<b>🤖 제어 명령어</b>
━━━━━━━━━━━━━━━━━━━━━
▶️ 시작 - 봇 시작
⏹️ 정지 - 봇 정지

💡 버튼을 클릭하세요!"""
        await self._send_message(chat_id, msg)

    async def handle_daily(self, chat_id: int):
        """오늘 거래 현황"""
        # TODO: 실제 데이터 연동
        today = datetime.now().strftime("%Y-%m-%d")
        msg = f"""📊 <b>일일 거래 현황</b>

📅 {today}
━━━━━━━━━━━━━━━━━━━━━
• 총 거래: 0회
• 승/패: 0승 0패
• 승률: --%
• 손익: 📈 +0.00 USDT (0.00%)

⏰ {datetime.now().strftime("%H:%M:%S")}"""
        await self._send_message(chat_id, msg)

    async def handle_profit(self, chat_id: int):
        """수익 현황"""
        # TODO: 실제 데이터 연동
        msg = """💰 <b>수익 현황</b>

━━━━━━━━━━━━━━━━━━━━━
• 오늘: 📈 +0.00 USDT
• 이번 주: 📈 +0.00 USDT
• 이번 달: 📈 +0.00 USDT
• 전체: 📈 +0.00 USDT

⏰ """ + datetime.now().strftime("%H:%M:%S")
        await self._send_message(chat_id, msg)

    async def handle_balance(self, chat_id: int):
        """잔고 조회"""
        # TODO: 실제 데이터 연동 (API 호출)
        msg = """💵 <b>잔고 현황</b>

━━━━━━━━━━━━━━━━━━━━━
• 총 잔고: -- USDT
• 가용 잔고: -- USDT
• 사용 중 마진: -- USDT
• 미실현 손익: -- USDT

💡 대시보드에서 API 키를 등록하세요.

⏰ """ + datetime.now().strftime("%H:%M:%S")
        await self._send_message(chat_id, msg)

    async def handle_status(self, chat_id: int):
        """봇 상태"""
        # TODO: 실제 상태 연동
        msg = """📈 <b>봇 상태</b>

🔴 상태: 정지됨

━━━━━━━━━━━━━━━━━━━━━
• 전략: --
• 타임프레임: --
• 거래 금액: -- USDT
• 레버리지: --x

📭 현재 열린 포지션 없음

⏰ """ + datetime.now().strftime("%H:%M:%S")
        await self._send_message(chat_id, msg)

    async def handle_status_table(self, chat_id: int):
        """상태 테이블"""
        msg = """📋 <b>포지션 상태표</b>

━━━━━━━━━━━━━━━━━━━━━
현재 열린 포지션이 없습니다.

💡 봇을 시작하면 포지션이 표시됩니다.

⏰ """ + datetime.now().strftime("%H:%M:%S")
        await self._send_message(chat_id, msg)

    async def handle_performance(self, chat_id: int):
        """성과 분석"""
        msg = """📉 <b>성과 분석</b>

📊 최근 30일
━━━━━━━━━━━━━━━━━━━━━
• 총 거래: 0회
• 승률: --%
• 총 손익: 📈 +0.00 USDT (0.00%)
• 최대 이익: +0.00%
• 최대 손실: 0.00%
• 평균 보유시간: --
• 최대 낙폭: 0.00%

⏰ """ + datetime.now().strftime("%H:%M:%S")
        await self._send_message(chat_id, msg)

    async def handle_count(self, chat_id: int):
        """거래 횟수"""
        msg = """🔢 <b>거래 횟수</b>

━━━━━━━━━━━━━━━━━━━━━
• 오늘: 0회
• 이번 주: 0회
• 전체: 0회

⏰ """ + datetime.now().strftime("%H:%M:%S")
        await self._send_message(chat_id, msg)

    async def handle_start_bot(self, chat_id: int):
        """봇 시작"""
        msg = """▶️ <b>봇 시작 요청</b>

⚠️ 텔레그램에서 직접 봇을 시작할 수 없습니다.

대시보드에서 봇을 시작해주세요:
👉 Trading 페이지 → 봇 시작 버튼

━━━━━━━━━━━━━━━━━━━━━
봇이 시작되면 알림을 받으실 수 있습니다."""
        await self._send_message(chat_id, msg)

    async def handle_stop_bot(self, chat_id: int):
        """봇 정지"""
        msg = """⏹️ <b>봇 정지 요청</b>

⚠️ 텔레그램에서 직접 봇을 정지할 수 없습니다.

대시보드에서 봇을 정지해주세요:
👉 Trading 페이지 → 봇 정지 버튼

━━━━━━━━━━━━━━━━━━━━━
봇이 정지되면 알림을 받으실 수 있습니다."""
        await self._send_message(chat_id, msg)

    async def _send_unknown_command(self, chat_id: int):
        """알 수 없는 명령어"""
        msg = """❓ 알 수 없는 명령어입니다.

아래 버튼을 사용하거나 /help 를 입력하세요."""
        await self._send_message(chat_id, msg)

    async def _send_error(self, chat_id: int, error: str):
        """에러 메시지"""
        msg = f"""🚨 <b>오류 발생</b>

{error}

잠시 후 다시 시도해주세요."""
        await self._send_message(chat_id, msg)


# 싱글톤 인스턴스
_handler_instance: Optional[TelegramBotHandler] = None
_handler_task: Optional[asyncio.Task] = None


def get_bot_handler() -> TelegramBotHandler:
    """봇 핸들러 인스턴스 반환"""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = TelegramBotHandler()
    return _handler_instance


async def load_telegram_settings_from_db():
    """DB에서 활성화된 텔레그램 설정 로드"""
    from ...database.db import AsyncSessionLocal
    from ...database.models import UserSettings
    from ...utils.crypto_secrets import decrypt_secret
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as session:
            # 텔레그램이 설정된 첫 번째 사용자 찾기
            result = await session.execute(
                select(UserSettings)
                .where(UserSettings.encrypted_telegram_bot_token.isnot(None))
                .limit(1)
            )
            user_settings = result.scalars().first()

            if user_settings:
                bot_token = decrypt_secret(user_settings.encrypted_telegram_bot_token)
                chat_id = decrypt_secret(user_settings.encrypted_telegram_chat_id)

                if bot_token and chat_id:
                    logger.info(
                        f"[Telegram] Loaded settings from DB for user {user_settings.user_id}"
                    )
                    return bot_token, chat_id

        logger.info("[Telegram] No telegram settings found in DB")
        return None, None
    except Exception as e:
        logger.error(f"[Telegram] Failed to load settings from DB: {e}")
        return None, None


async def start_telegram_bot():
    """텔레그램 봇 시작 (백그라운드)"""
    global _handler_task, _handler_instance

    # DB에서 텔레그램 설정 로드 시도
    bot_token, chat_id = await load_telegram_settings_from_db()

    if bot_token and chat_id:
        # DB에서 로드한 설정으로 노티파이어 초기화
        from .notifier import init_telegram_notifier

        notifier = init_telegram_notifier(bot_token=bot_token, chat_id=chat_id)
        _handler_instance = TelegramBotHandler(notifier=notifier)
        logger.info(f"[Telegram] Bot handler initialized with DB settings")
    else:
        # 환경변수 기반 (기존 방식)
        handler = get_bot_handler()
        if not handler.notifier.is_enabled():
            logger.warning("텔레그램이 비활성화되어 봇 핸들러를 시작하지 않습니다.")
            return
        _handler_instance = handler

    _handler_task = asyncio.create_task(_handler_instance.start_polling())
    logger.info("🤖 텔레그램 봇 핸들러 태스크 시작됨")


def stop_telegram_bot():
    """텔레그램 봇 중지"""
    global _handler_task, _handler_instance

    if _handler_instance:
        _handler_instance.stop_polling()

    if _handler_task:
        _handler_task.cancel()
