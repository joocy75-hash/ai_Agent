"""
텔레그램 봇 명령어 핸들러
사용자의 버튼 클릭/명령어에 응답합니다.
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, Dict, Optional

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

    async def _get_db_session(self):
        """비동기 DB 세션 생성"""
        from ...database.db import AsyncSessionLocal

        return AsyncSessionLocal()

    async def _get_user_trades_today(self, session) -> dict:
        """오늘 거래 데이터 조회"""
        from datetime import date

        from sqlalchemy import func, select

        from ...database.models import Trade

        today = date.today()

        # 오늘 거래 조회
        result = await session.execute(
            select(Trade).where(func.date(Trade.created_at) == today)
        )
        trades = result.scalars().all()

        if not trades:
            return {"count": 0, "wins": 0, "losses": 0, "pnl": 0.0}

        wins = sum(1 for t in trades if float(t.pnl or 0) > 0)
        losses = sum(1 for t in trades if float(t.pnl or 0) < 0)
        total_pnl = sum(float(t.pnl or 0) for t in trades)

        return {"count": len(trades), "wins": wins, "losses": losses, "pnl": total_pnl}

    async def _get_profit_summary(self, session) -> dict:
        """수익 요약 조회"""
        from datetime import date, timedelta

        from sqlalchemy import func, select

        from ...database.models import Trade

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # 기간별 수익 계산
        async def get_pnl_sum(start_date):
            result = await session.execute(
                select(func.sum(Trade.pnl)).where(
                    func.date(Trade.created_at) >= start_date
                )
            )
            return float(result.scalar() or 0)

        return {
            "today": await get_pnl_sum(today),
            "week": await get_pnl_sum(week_start),
            "month": await get_pnl_sum(month_start),
            "total": (await session.execute(select(func.sum(Trade.pnl)))).scalar() or 0,
        }

    async def _get_trade_counts(self, session) -> dict:
        """거래 횟수 조회"""
        from datetime import date, timedelta

        from sqlalchemy import func, select

        from ...database.models import Trade

        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        today_count = (
            await session.execute(
                select(func.count())
                .select_from(Trade)
                .where(func.date(Trade.created_at) == today)
            )
        ).scalar() or 0

        week_count = (
            await session.execute(
                select(func.count())
                .select_from(Trade)
                .where(func.date(Trade.created_at) >= week_start)
            )
        ).scalar() or 0

        total_count = (
            await session.execute(select(func.count()).select_from(Trade))
        ).scalar() or 0

        return {"today": today_count, "week": week_count, "total": total_count}

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
        """오늘 거래 현황 (실제 DB 연동)"""
        try:
            async with await self._get_db_session() as session:
                data = await self._get_user_trades_today(session)

                today = datetime.now().strftime("%Y-%m-%d")
                count = data["count"]
                wins = data["wins"]
                losses = data["losses"]
                pnl = data["pnl"]
                win_rate = f"{(wins / count * 100):.1f}" if count > 0 else "--"
                pnl_emoji = "📈" if pnl >= 0 else "📉"

                msg = f"""📊 <b>일일 거래 현황</b>

📅 {today}
━━━━━━━━━━━━━━━━━━━━━
• 총 거래: {count}회
• 승/패: {wins}승 {losses}패
• 승률: {win_rate}%
• 손익: {pnl_emoji} {pnl:+.2f} USDT

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        except Exception as e:
            logger.error(f"오늘 현황 조회 실패: {e}")
            msg = f"""📊 <b>일일 거래 현황</b>

⚠️ 데이터 조회 중 오류가 발생했습니다.

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        await self._send_message(chat_id, msg)

    async def handle_profit(self, chat_id: int):
        """수익 현황 (실제 DB 연동)"""
        try:
            async with await self._get_db_session() as session:
                data = await self._get_profit_summary(session)

                def fmt(val):
                    emoji = "📈" if val >= 0 else "📉"
                    return f"{emoji} {val:+.2f} USDT"

                msg = f"""💰 <b>수익 현황</b>

━━━━━━━━━━━━━━━━━━━━━
• 오늘: {fmt(data["today"])}
• 이번 주: {fmt(data["week"])}
• 이번 달: {fmt(data["month"])}
• 전체: {fmt(float(data["total"]))}

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        except Exception as e:
            logger.error(f"수익 조회 실패: {e}")
            msg = f"""💰 <b>수익 현황</b>

⚠️ 데이터 조회 중 오류가 발생했습니다.

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        await self._send_message(chat_id, msg)

    async def _get_user_by_chat_id(self, session, chat_id: int):
        """텔레그램 chat_id로 사용자 찾기"""
        from sqlalchemy import select

        from ...database.models import UserSettings
        from ...utils.crypto_secrets import decrypt_secret

        # 모든 UserSettings 조회하여 chat_id 매칭
        result = await session.execute(
            select(UserSettings).where(
                UserSettings.encrypted_telegram_chat_id.isnot(None)
            )
        )
        all_settings = result.scalars().all()

        for settings in all_settings:
            try:
                decrypted_chat_id = decrypt_secret(settings.encrypted_telegram_chat_id)
                if decrypted_chat_id and str(chat_id) == decrypted_chat_id:
                    return settings.user_id
            except Exception:
                continue

        return None

    async def handle_balance(self, chat_id: int):
        """잔고 조회 (실제 거래소 API 연동)"""
        try:
            from sqlalchemy import select

            from ...database.models import ApiKey
            from ...services.bitget_rest import BitgetRestClient
            from ...utils.crypto_secrets import decrypt_secret

            async with await self._get_db_session() as session:
                # 1. chat_id로 user_id 찾기
                user_id = await self._get_user_by_chat_id(session, chat_id)

                if not user_id:
                    msg = """💵 <b>잔고 현황</b>

━━━━━━━━━━━━━━━━━━━━━
⚠️ 텔레그램 계정이 연동되지 않았습니다.

대시보드에서 Telegram 설정을 완료해주세요:
💡 대시보드 → 설정 → Telegram 연동

⏰ """ + datetime.now().strftime("%H:%M:%S")
                    await self._send_message(chat_id, msg)
                    return

                # 2. user_id로 API 키 조회
                result = await session.execute(
                    select(ApiKey).where(ApiKey.user_id == user_id)
                )
                api_key_obj = result.scalars().first()

                if not api_key_obj:
                    msg = """💵 <b>잔고 현황</b>

━━━━━━━━━━━━━━━━━━━━━
⚠️ 거래소 API 키가 설정되지 않았습니다.

대시보드에서 API 키를 등록해주세요:
💡 대시보드 → 설정 → API 키 등록

⏰ """ + datetime.now().strftime("%H:%M:%S")
                    await self._send_message(chat_id, msg)
                    return

                # 3. 거래소 API로 잔고 조회
                api_key = decrypt_secret(api_key_obj.encrypted_api_key)
                api_secret = decrypt_secret(api_key_obj.encrypted_secret_key)
                passphrase = (
                    decrypt_secret(api_key_obj.encrypted_passphrase)
                    if api_key_obj.encrypted_passphrase
                    else ""
                )

                client = BitgetRestClient(
                    api_key=api_key,
                    api_secret=api_secret,
                    passphrase=passphrase,
                )

                try:
                    # 선물 계좌 정보 조회
                    account_info = await client.get_account_info(product_type="USDT-FUTURES")

                    # API 응답이 직접 배열이거나 data 키 안에 배열일 수 있음
                    accounts = (
                        account_info
                        if isinstance(account_info, list)
                        else account_info.get("data", []) if isinstance(account_info, dict) else []
                    )

                    if accounts and len(accounts) > 0:
                        acc = accounts[0]
                        # Bitget API 필드명
                        equity = float(acc.get("accountEquity", 0) or acc.get("equity", 0))
                        available = float(acc.get("available", 0) or acc.get("crossedMaxAvailable", 0))
                        used = float(acc.get("locked", 0) or acc.get("crossedMargin", 0))
                        unrealized_pnl = float(acc.get("unrealizedPL", 0) or acc.get("crossedUnrealizedPL", 0))

                        pnl_emoji = "📈" if unrealized_pnl >= 0 else "📉"

                        msg = f"""💵 <b>잔고 현황</b>

━━━━━━━━━━━━━━━━━━━━━
• 총 자산: {equity:,.2f} USDT
• 가용 잔고: {available:,.2f} USDT
• 사용 중: {used:,.2f} USDT
• 미실현 손익: {pnl_emoji} {unrealized_pnl:+,.2f} USDT

💡 Bitget USDT-Futures
⏰ {datetime.now().strftime("%H:%M:%S")}"""
                    else:
                        msg = """💵 <b>잔고 현황</b>

━━━━━━━━━━━━━━━━━━━━━
⚠️ 잔고 정보를 가져올 수 없습니다.
거래소 API 키를 확인해주세요.

⏰ """ + datetime.now().strftime("%H:%M:%S")

                finally:
                    await client.close()

        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}", exc_info=True)
            msg = f"""💵 <b>잔고 현황</b>

━━━━━━━━━━━━━━━━━━━━━
⚠️ 잔고 조회 중 오류가 발생했습니다.

{str(e)[:50]}...

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        await self._send_message(chat_id, msg)

    async def handle_status(self, chat_id: int):
        """봇 상태 (실제 DB 연동)"""
        try:
            from sqlalchemy import select

            from ...database.models import BotInstance

            async with await self._get_db_session() as session:
                # 실행 중인 봇 조회
                result = await session.execute(
                    select(BotInstance).where(BotInstance.is_running is True)
                )
                running_bots = result.scalars().all()

                if running_bots:
                    bot = running_bots[0]
                    status_emoji = "🟢"
                    status_text = "실행 중"
                    bot_info = f"""• 봇 이름: {bot.name}
• 심볼: {bot.symbol or "--"}"""
                else:
                    status_emoji = "🔴"
                    status_text = "정지됨"
                    bot_info = "• 실행 중인 봇 없음"

                total_bots = (
                    (
                        await session.execute(
                            select(BotInstance).where(BotInstance.is_active is True)
                        )
                    )
                    .scalars()
                    .all()
                )

                msg = f"""📈 <b>봇 상태</b>

{status_emoji} 상태: {status_text}

━━━━━━━━━━━━━━━━━━━━━
{bot_info}
• 등록된 봇: {len(total_bots)}개
• 실행 중: {len(running_bots)}개

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        except Exception as e:
            logger.error(f"상태 조회 실패: {e}")
            msg = f"""📈 <b>봇 상태</b>

⚠️ 상태 조회 중 오류가 발생했습니다.

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        await self._send_message(chat_id, msg)

    async def handle_status_table(self, chat_id: int):
        """상태 테이블 (사용자별 + 거래소 실시간 포지션)"""
        try:
            from sqlalchemy import select

            from ...database.models import ApiKey
            from ...services.bitget_rest import BitgetRestClient
            from ...utils.crypto_secrets import decrypt_secret

            async with await self._get_db_session() as session:
                # 1. chat_id로 user_id 찾기
                user_id = await self._get_user_by_chat_id(session, chat_id)

                if not user_id:
                    msg = """📋 <b>포지션 상태표</b>

━━━━━━━━━━━━━━━━━━━━━
⚠️ 텔레그램 계정이 연동되지 않았습니다.

💡 대시보드 → 설정 → Telegram 연동

⏰ """ + datetime.now().strftime("%H:%M:%S")
                    await self._send_message(chat_id, msg)
                    return

                # 2. user_id로 API 키 조회
                result = await session.execute(
                    select(ApiKey).where(ApiKey.user_id == user_id)
                )
                api_key_obj = result.scalars().first()

                if not api_key_obj:
                    msg = """📋 <b>포지션 상태표</b>

━━━━━━━━━━━━━━━━━━━━━
⚠️ 거래소 API 키가 설정되지 않았습니다.

💡 대시보드 → 설정 → API 키 등록

⏰ """ + datetime.now().strftime("%H:%M:%S")
                    await self._send_message(chat_id, msg)
                    return

                # 3. 거래소에서 실시간 포지션 조회
                api_key = decrypt_secret(api_key_obj.encrypted_api_key)
                api_secret = decrypt_secret(api_key_obj.encrypted_secret_key)
                passphrase = (
                    decrypt_secret(api_key_obj.encrypted_passphrase)
                    if api_key_obj.encrypted_passphrase
                    else ""
                )

                client = BitgetRestClient(
                    api_key=api_key,
                    api_secret=api_secret,
                    passphrase=passphrase,
                )

                try:
                    positions = await client.get_positions(product_type="USDT-FUTURES")

                    # 실제 포지션만 필터링 (size > 0)
                    active_positions = [
                        p for p in positions
                        if float(p.get("total", 0) or p.get("available", 0)) > 0
                    ]

                    if active_positions:
                        pos_lines = []
                        for p in active_positions[:5]:
                            symbol = p.get("symbol", "").replace("USDT", "")
                            side = p.get("holdSide", "").upper()
                            size = float(p.get("total", 0) or p.get("available", 0))
                            entry = float(p.get("openPriceAvg", 0) or p.get("averageOpenPrice", 0))
                            pnl = float(p.get("unrealizedPL", 0) or 0)
                            leverage = p.get("leverage", 1)

                            emoji = "📈" if pnl >= 0 else "📉"
                            side_emoji = "🟢" if side == "LONG" else "🔴"

                            pos_lines.append(
                                f"{side_emoji} {symbol} {side}\n"
                                f"   수량: {size:.4f} | {leverage}x\n"
                                f"   진입가: ${entry:,.2f}\n"
                                f"   {emoji} PnL: {pnl:+,.2f} USDT"
                            )

                        pos_text = "\n\n".join(pos_lines)
                        if len(active_positions) > 5:
                            pos_text += f"\n\n... 외 {len(active_positions) - 5}개"
                    else:
                        pos_text = "현재 열린 포지션이 없습니다."

                    msg = f"""📋 <b>포지션 상태표</b>

━━━━━━━━━━━━━━━━━━━━━
{pos_text}

💡 Bitget USDT-Futures (실시간)
⏰ {datetime.now().strftime("%H:%M:%S")}"""

                finally:
                    await client.close()

        except Exception as e:
            logger.error(f"포지션 조회 실패: {e}", exc_info=True)
            msg = f"""📋 <b>포지션 상태표</b>

━━━━━━━━━━━━━━━━━━━━━
⚠️ 조회 중 오류가 발생했습니다.

{str(e)[:50]}...

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        await self._send_message(chat_id, msg)

    async def handle_performance(self, chat_id: int):
        """성과 분석 (실제 DB 연동)"""
        try:
            from datetime import timedelta

            from sqlalchemy import select

            from ...database.models import Trade

            async with await self._get_db_session() as session:
                # 최근 30일 거래
                start_date = datetime.now() - timedelta(days=30)
                result = await session.execute(
                    select(Trade).where(Trade.created_at >= start_date)
                )
                trades = result.scalars().all()

                count = len(trades)
                if count > 0:
                    pnl_list = [float(t.pnl or 0) for t in trades]
                    wins = sum(1 for p in pnl_list if p > 0)
                    total_pnl = sum(pnl_list)
                    max_profit = max(pnl_list) if pnl_list else 0
                    max_loss = min(pnl_list) if pnl_list else 0
                    win_rate = f"{(wins / count * 100):.1f}"
                else:
                    total_pnl = 0
                    max_profit = 0
                    max_loss = 0
                    win_rate = "--"

                pnl_emoji = "📈" if total_pnl >= 0 else "📉"

                msg = f"""📉 <b>성과 분석</b>

📊 최근 30일
━━━━━━━━━━━━━━━━━━━━━
• 총 거래: {count}회
• 승률: {win_rate}%
• 총 손익: {pnl_emoji} {total_pnl:+.2f} USDT
• 최대 이익: +{max_profit:.2f} USDT
• 최대 손실: {max_loss:.2f} USDT

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        except Exception as e:
            logger.error(f"성과 분석 실패: {e}")
            msg = f"""📉 <b>성과 분석</b>

⚠️ 데이터 조회 중 오류가 발생했습니다.

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        await self._send_message(chat_id, msg)

    async def handle_count(self, chat_id: int):
        """거래 횟수 (실제 DB 연동)"""
        try:
            async with await self._get_db_session() as session:
                data = await self._get_trade_counts(session)

                msg = f"""🔢 <b>거래 횟수</b>

━━━━━━━━━━━━━━━━━━━━━
• 오늘: {data["today"]}회
• 이번 주: {data["week"]}회
• 전체: {data["total"]}회

⏰ {datetime.now().strftime("%H:%M:%S")}"""

        except Exception as e:
            logger.error(f"거래 횟수 조회 실패: {e}")
            msg = f"""🔢 <b>거래 횟수</b>

⚠️ 데이터 조회 중 오류가 발생했습니다.

⏰ {datetime.now().strftime("%H:%M:%S")}"""

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
    from sqlalchemy import select

    from ...database.db import AsyncSessionLocal
    from ...database.models import UserSettings
    from ...utils.crypto_secrets import decrypt_secret

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
        logger.info("[Telegram] Bot handler initialized with DB settings")
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
