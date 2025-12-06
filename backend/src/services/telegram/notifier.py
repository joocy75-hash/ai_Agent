"""
텔레그램 알림 서비스
실제 텔레그램 API와 통신하는 메인 서비스
"""

import asyncio
import logging
import os
from typing import Optional, List, Callable, Dict

import httpx

from .messages import TelegramMessages
from .types import (
    TradeInfo,
    TradeResult,
    BotConfig,
    SessionSummary,
    PositionInfo,
    WarningInfo,
    ErrorInfo,
    BalanceInfo,
    DailyStats,
    PerformanceStats,
)

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """텔레그램 알림 서비스"""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        notify_trades: bool = True,
        notify_system: bool = True,
        notify_errors: bool = True,
    ):
        """
        텔레그램 알림 서비스 초기화

        Args:
            bot_token: 텔레그램 봇 토큰 (BotFather에서 발급)
            chat_id: 알림 받을 채팅 ID
            notify_trades: 거래 알림 활성화 여부
            notify_system: 시스템 알림 활성화 여부
            notify_errors: 에러 알림 활성화 여부
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

        self.notify_trades = notify_trades
        self.notify_system = notify_system
        self.notify_errors = notify_errors

        self.enabled = bool(self.bot_token and self.chat_id)
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        # 명령어 핸들러 (봇이 명령어를 받을 때 사용)
        self._command_handlers: Dict[str, Callable] = {}

        # 메시지 큐 (rate limit 방지)
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._queue_task: Optional[asyncio.Task] = None

        if self.enabled:
            logger.info("✅ 텔레그램 알림 서비스 활성화됨")
        else:
            logger.warning("⚠️ 텔레그램 알림 서비스 비활성화 (토큰 또는 채팅 ID 없음)")

    async def _send_request(self, method: str, data: dict) -> Optional[dict]:
        """텔레그램 API 요청 전송"""
        if not self.enabled:
            logger.warning(
                f"[Telegram] Request skipped - notifier disabled. bot_token set: {bool(self.bot_token)}, chat_id set: {bool(self.chat_id)}"
            )
            return None

        try:
            url = f"{self.base_url}/{method}"
            logger.debug(f"[Telegram] Sending request to: {method}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=data)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"텔레그램 API 에러: {response.status_code} - {response.text}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("텔레그램 API 타임아웃")
            return None
        except Exception as e:
            logger.error(f"텔레그램 API 요청 실패: {e}")
            return None

    async def send_message(
        self,
        message: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
        reply_markup: Optional[dict] = None,
    ) -> bool:
        """
        텔레그램 메시지 전송

        Args:
            message: 전송할 메시지 (HTML 포맷 지원)
            chat_id: 채팅 ID (None이면 기본값 사용)
            parse_mode: 파싱 모드 (HTML, Markdown, MarkdownV2)
            disable_notification: 무음 알림 여부
            reply_markup: 인라인 키보드 등 마크업

        Returns:
            전송 성공 여부
        """
        if not self.enabled:
            logger.debug("텔레그램 비활성화 - 메시지 전송 스킵")
            return False

        data = {
            "chat_id": chat_id or self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }

        if reply_markup:
            data["reply_markup"] = reply_markup

        result = await self._send_request("sendMessage", data)

        if result and result.get("ok"):
            logger.debug("텔레그램 메시지 전송 성공")
            return True
        else:
            logger.error("텔레그램 메시지 전송 실패")
            return False

    async def send_message_with_keyboard(
        self,
        message: str,
        buttons: List[List[str]],
        chat_id: Optional[str] = None,
    ) -> bool:
        """
        키보드 버튼과 함께 메시지 전송

        Args:
            message: 전송할 메시지
            buttons: 버튼 배열 (예: [["/status", "/balance"], ["/start", "/stop"]])
            chat_id: 채팅 ID
        """
        keyboard = {
            "keyboard": [[{"text": btn} for btn in row] for row in buttons],
            "resize_keyboard": True,
            "one_time_keyboard": False,
        }

        return await self.send_message(
            message=message, chat_id=chat_id, reply_markup=keyboard
        )

    def get_default_keyboard(self) -> List[List[str]]:
        """기본 키보드 레이아웃 (한국어)"""
        return [
            ["📊 오늘 현황", "💰 수익", "💵 잔고"],
            ["📈 상태", "📋 상태표", "📉 성과"],
            ["🔢 거래횟수", "▶️ 시작", "⏹️ 정지", "❓ 도움말"],
        ]

    # ==================== 거래 알림 메서드 ====================

    async def notify_new_trade(self, trade: TradeInfo) -> bool:
        """신규 거래 알림"""
        if not self.notify_trades:
            return False

        message = TelegramMessages.new_trade(trade)
        return await self.send_message(message)

    async def notify_close_trade(self, trade: TradeResult) -> bool:
        """포지션 종료 알림"""
        if not self.notify_trades:
            return False

        message = TelegramMessages.close_trade(trade)
        return await self.send_message(message)

    # ==================== 시스템 알림 메서드 ====================

    async def notify_bot_start(self, config: BotConfig) -> bool:
        """봇 시작 알림"""
        if not self.notify_system:
            return False

        message = TelegramMessages.bot_start(config)
        return await self.send_message_with_keyboard(
            message=message, buttons=self.get_default_keyboard()
        )

    async def notify_bot_stop(
        self, summary: Optional[SessionSummary] = None, reason: str = "정상 종료"
    ) -> bool:
        """봇 종료 알림"""
        if not self.notify_system:
            return False

        message = TelegramMessages.bot_stop(summary, reason)
        return await self.send_message(message)

    async def notify_open_positions_warning(
        self, positions: List[PositionInfo]
    ) -> bool:
        """미청산 포지션 경고"""
        if not self.notify_system:
            return False

        message = TelegramMessages.open_positions_warning(positions)
        return await self.send_message(message)

    async def notify_warning(self, warning: WarningInfo) -> bool:
        """일반 경고 알림"""
        if not self.notify_system:
            return False

        message = TelegramMessages.warning(warning)
        return await self.send_message(message)

    # ==================== 에러 알림 메서드 ====================

    async def notify_error(self, error: ErrorInfo) -> bool:
        """에러 알림"""
        if not self.notify_errors:
            return False

        message = TelegramMessages.error(error)
        return await self.send_message(message)

    # ==================== 조회 메서드 ====================

    async def send_balance(self, balance: BalanceInfo) -> bool:
        """잔고 정보 전송"""
        message = TelegramMessages.balance(balance)
        return await self.send_message(message)

    async def send_daily_stats(self, stats: DailyStats) -> bool:
        """일일 통계 전송"""
        message = TelegramMessages.daily_stats(stats)
        return await self.send_message(message)

    async def send_performance(self, stats: PerformanceStats) -> bool:
        """성과 통계 전송"""
        message = TelegramMessages.performance(stats)
        return await self.send_message(message)

    async def send_status(
        self,
        is_running: bool,
        config: Optional[BotConfig] = None,
        positions: Optional[List[PositionInfo]] = None,
    ) -> bool:
        """봇 상태 전송"""
        message = TelegramMessages.status(is_running, config, positions)
        return await self.send_message(message)

    async def send_help(self) -> bool:
        """도움말 전송"""
        message = TelegramMessages.help_message()
        return await self.send_message_with_keyboard(
            message=message, buttons=self.get_default_keyboard()
        )

    async def send_trade_count(self, total: int, today: int, week: int) -> bool:
        """거래 횟수 전송"""
        message = TelegramMessages.count_trades(total, today, week)
        return await self.send_message(message)

    async def send_profit_summary(
        self, today_pnl: float, week_pnl: float, month_pnl: float, total_pnl: float
    ) -> bool:
        """수익 요약 전송"""
        message = TelegramMessages.profit_summary(
            today_pnl, week_pnl, month_pnl, total_pnl
        )
        return await self.send_message(message)

    # ==================== 유틸리티 메서드 ====================

    async def test_connection(self) -> bool:
        """연결 테스트"""
        if not self.enabled:
            return False

        result = await self._send_request("getMe", {})
        if result and result.get("ok"):
            bot_info = result.get("result", {})
            logger.info(
                f"✅ 텔레그램 봇 연결 성공: @{bot_info.get('username', 'unknown')}"
            )
            return True
        return False

    async def send_test_message(self) -> bool:
        """테스트 메시지 전송"""
        message = """🧪 <b>테스트 메시지</b>

✅ 텔레그램 알림 봇이 정상 작동합니다!

이 메시지는 연결 테스트용입니다."""

        return await self.send_message_with_keyboard(
            message=message, buttons=self.get_default_keyboard()
        )

    def is_enabled(self) -> bool:
        """활성화 상태 확인"""
        return self.enabled

    def get_config(self) -> dict:
        """현재 설정 반환"""
        return {
            "enabled": self.enabled,
            "notify_trades": self.notify_trades,
            "notify_system": self.notify_system,
            "notify_errors": self.notify_errors,
            "chat_id_configured": bool(self.chat_id),
            "bot_token_configured": bool(self.bot_token),
        }


# 싱글톤 인스턴스
_notifier_instance: Optional[TelegramNotifier] = None


def get_telegram_notifier() -> TelegramNotifier:
    """텔레그램 알림 서비스 싱글톤 인스턴스 반환"""
    global _notifier_instance

    if _notifier_instance is None:
        _notifier_instance = TelegramNotifier()

    return _notifier_instance


def init_telegram_notifier(
    bot_token: Optional[str] = None, chat_id: Optional[str] = None, **kwargs
) -> TelegramNotifier:
    """텔레그램 알림 서비스 초기화"""
    global _notifier_instance

    _notifier_instance = TelegramNotifier(
        bot_token=bot_token, chat_id=chat_id, **kwargs
    )

    return _notifier_instance
