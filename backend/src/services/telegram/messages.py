"""
텔레그램 메시지 포맷터
모든 알림 메시지의 포맷을 정의합니다.
"""

from datetime import datetime
from typing import List, Optional
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


class TelegramMessages:
    """텔레그램 메시지 포맷터"""

    @staticmethod
    def _format_timestamp(dt: Optional[datetime] = None) -> str:
        """타임스탬프 포맷"""
        if dt is None:
            dt = datetime.now()
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _format_duration(minutes: float) -> str:
        """시간 포맷 (분 -> 시:분:초)"""
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        secs = int((minutes % 1) * 60)

        if hours > 0:
            return f"{hours}시간 {mins}분"
        elif mins > 0:
            return f"{mins}분 {secs}초"
        else:
            return f"{secs}초"

    @staticmethod
    def _get_exit_reason_text(reason: str) -> str:
        """종료 사유 텍스트"""
        reasons = {
            "take_profit": "🎯 익절",
            "stop_loss": "🛑 손절",
            "exit_signal": "📊 시그널 종료",
            "trailing_stop": "📈 트레일링 스탑",
            "force_exit": "⚡ 강제 종료",
            "manual": "✋ 수동 종료",
        }
        return reasons.get(reason, f"🔄 {reason}")

    @classmethod
    def new_trade(cls, trade: TradeInfo) -> str:
        """신규 거래 알림 메시지"""
        direction_emoji = "📈" if trade.direction == "Long" else "📉"

        msg = f"""🟢 <b>Bitget: 신규 거래</b>

• 코인: {trade.symbol}
• 방향: {trade.direction} {direction_emoji}
• 진입가: {trade.entry_price:,.4f} USDT
• 수량: {trade.quantity}
• 총액: {trade.total_value:,.2f} USDT"""

        if trade.leverage and trade.leverage > 1:
            msg += f"\n• 레버리지: {trade.leverage}x"

        msg += f"\n\n⏰ {cls._format_timestamp(trade.timestamp)}"
        return msg

    @classmethod
    def close_trade(cls, trade: TradeResult) -> str:
        """포지션 종료 알림 메시지"""
        pnl_emoji = "📈" if trade.pnl_percent > 0 else "📉"
        pnl_sign = "+" if trade.pnl_percent > 0 else ""
        pnl_usdt_sign = "+" if trade.pnl_usdt > 0 else ""

        exit_reason_text = cls._get_exit_reason_text(trade.exit_reason)
        duration_text = cls._format_duration(trade.duration_minutes)

        msg = f"""🔴 <b>Bitget: 포지션 종료</b>

{pnl_emoji} <b>손익: {pnl_sign}{trade.pnl_percent:.2f}% ({pnl_usdt_sign}{trade.pnl_usdt:.3f} USDT)</b>
━━━━━━━━━━━━━━━━━━━━━
• 코인: {trade.symbol}
• 방향: {trade.direction}
• 진입가: {trade.entry_price:,.4f} USDT
• 종료가: {trade.exit_price:,.4f} USDT
• 수량: {trade.quantity}
• 종료 사유: {exit_reason_text}
• 보유 기간: {duration_text}

⏰ {cls._format_timestamp(trade.timestamp)}"""
        return msg

    @classmethod
    def bot_start(cls, config: BotConfig) -> str:
        """봇 시작 알림 메시지"""
        msg = f"""🚀 <b>AI 자동매매 시작</b>

✅ AI봇이 성공적으로 연결되었습니다!
📝 거래 알림을 실시간으로 받으실 수 있습니다.

<b>현재 설정:</b>
━━━━━━━━━━━━━━━━━━━━━
• 거래소: {config.exchange}
• 거래당 금액: {config.trade_amount} USDT
• 손절가: -{config.stop_loss_percent}%
• 타임프레임: {config.timeframe}
• 전략: {config.strategy}
• 레버리지: {config.leverage}x
• 마진 모드: {config.margin_mode}

⏰ {cls._format_timestamp()}"""
        return msg

    @classmethod
    def bot_stop(
        cls, summary: Optional[SessionSummary] = None, reason: str = "정상 종료"
    ) -> str:
        """봇 종료 알림 메시지"""
        msg = f"""⏹️ <b>AI 자동매매 종료</b>

상태: {reason}"""

        if summary:
            pnl_emoji = "📈" if summary.total_pnl_usdt > 0 else "📉"
            pnl_sign = "+" if summary.total_pnl_usdt > 0 else ""

            msg += f"""

<b>📊 세션 요약:</b>
━━━━━━━━━━━━━━━━━━━━━
• 총 거래 수: {summary.total_trades}
• 승률: {summary.win_rate:.1f}% ({summary.winning_trades}승 {summary.losing_trades}패)
• 총 손익: {pnl_emoji} {pnl_sign}{summary.total_pnl_usdt:.2f} USDT ({pnl_sign}{summary.total_pnl_percent:.2f}%)
• 운영 시간: {summary.duration_hours:.1f}시간"""

        msg += f"\n\n⏰ {cls._format_timestamp()}"
        return msg

    @classmethod
    def open_positions_warning(cls, positions: List[PositionInfo]) -> str:
        """미청산 포지션 경고 메시지"""
        msg = f"""⚠️ <b>미청산 포지션 경고</b>

⚠️ {len(positions)}개 미청산 포지션이 남아 있습니다.

<b>현재 포지션:</b>
━━━━━━━━━━━━━━━━━━━━━"""

        for i, pos in enumerate(positions, 1):
            pnl_emoji = "📈" if pos.pnl_percent > 0 else "📉"
            pnl_sign = "+" if pos.pnl_percent > 0 else ""
            msg += f"\n{i}. {pos.symbol} {pos.direction} {pnl_emoji} ({pnl_sign}{pos.pnl_percent:.2f}%)"

        msg += f"""

💡 Bitget에서 직접 처리하거나,
'/start'로 봇을 다시 켠 후 
'/stopentry'로 신규 진입을 막고 정리해 주세요.

⏰ {cls._format_timestamp()}"""
        return msg

    @classmethod
    def warning(cls, warning: WarningInfo) -> str:
        """일반 경고 메시지"""
        msg = f"""⚠️ <b>경고</b>

{warning.message}

⏰ {cls._format_timestamp(warning.timestamp)}"""
        return msg

    @classmethod
    def error(cls, error: ErrorInfo) -> str:
        """에러 알림 메시지"""
        msg = f"""🚨 <b>시스템 에러</b>

❌ {error.error_type}

<b>에러 내용:</b>
━━━━━━━━━━━━━━━━━━━━━
{error.message}"""

        if error.details:
            msg += f"\n\n상세: {error.details}"

        if error.will_retry and error.retry_after_seconds:
            msg += f"\n\n💡 {error.retry_after_seconds}초 후 자동 재시도됩니다."
        else:
            msg += "\n\n💡 수동 확인이 필요할 수 있습니다."

        msg += f"\n\n⏰ {cls._format_timestamp(error.timestamp)}"
        return msg

    @classmethod
    def balance(cls, balance: BalanceInfo) -> str:
        """잔고 조회 메시지"""
        pnl_emoji = "📈" if balance.unrealized_pnl >= 0 else "📉"
        pnl_sign = "+" if balance.unrealized_pnl >= 0 else ""

        msg = f"""💰 <b>잔고 현황</b>

━━━━━━━━━━━━━━━━━━━━━
• 총 잔고: {balance.total_balance:,.2f} {balance.currency}
• 가용 잔고: {balance.available_balance:,.2f} {balance.currency}
• 사용 중 마진: {balance.used_margin:,.2f} {balance.currency}
• 미실현 손익: {pnl_emoji} {pnl_sign}{balance.unrealized_pnl:,.2f} {balance.currency}

⏰ {cls._format_timestamp()}"""
        return msg

    @classmethod
    def daily_stats(cls, stats: DailyStats) -> str:
        """일일 통계 메시지"""
        pnl_emoji = "📈" if stats.pnl_usdt >= 0 else "📉"
        pnl_sign = "+" if stats.pnl_usdt >= 0 else ""
        win_rate = (
            (stats.winning_trades / stats.total_trades * 100)
            if stats.total_trades > 0
            else 0
        )

        msg = f"""📊 <b>일일 거래 현황</b>

📅 {stats.date}
━━━━━━━━━━━━━━━━━━━━━
• 총 거래: {stats.total_trades}회
• 승/패: {stats.winning_trades}승 {stats.losing_trades}패
• 승률: {win_rate:.1f}%
• 손익: {pnl_emoji} {pnl_sign}{stats.pnl_usdt:,.2f} USDT ({pnl_sign}{stats.pnl_percent:.2f}%)

⏰ {cls._format_timestamp()}"""
        return msg

    @classmethod
    def performance(cls, stats: PerformanceStats) -> str:
        """성과 통계 메시지"""
        pnl_emoji = "📈" if stats.total_pnl_usdt >= 0 else "📉"
        pnl_sign = "+" if stats.total_pnl_usdt >= 0 else ""

        period_text = {
            "7d": "최근 7일",
            "30d": "최근 30일",
            "all": "전체 기간",
        }.get(stats.period, stats.period)

        msg = f"""📈 <b>성과 분석</b>

📊 {period_text}
━━━━━━━━━━━━━━━━━━━━━
• 총 거래: {stats.total_trades}회
• 승률: {stats.win_rate:.1f}%
• 총 손익: {pnl_emoji} {pnl_sign}{stats.total_pnl_usdt:,.2f} USDT ({pnl_sign}{stats.total_pnl_percent:.2f}%)
• 최대 이익: +{stats.best_trade_pnl:.2f}%
• 최대 손실: {stats.worst_trade_pnl:.2f}%
• 평균 보유시간: {cls._format_duration(stats.avg_trade_duration_minutes)}
• 최대 낙폭: -{stats.max_drawdown_percent:.2f}%

⏰ {cls._format_timestamp()}"""
        return msg

    @classmethod
    def status(
        cls,
        is_running: bool,
        config: Optional[BotConfig] = None,
        positions: Optional[List[PositionInfo]] = None,
    ) -> str:
        """봇 상태 메시지"""
        status_emoji = "🟢" if is_running else "🔴"
        status_text = "실행 중" if is_running else "정지됨"

        msg = f"""📊 <b>봇 상태</b>

{status_emoji} 상태: {status_text}"""

        if config and is_running:
            msg += f"""

<b>현재 설정:</b>
━━━━━━━━━━━━━━━━━━━━━
• 전략: {config.strategy}
• 타임프레임: {config.timeframe}
• 거래 금액: {config.trade_amount} USDT
• 레버리지: {config.leverage}x"""

        if positions and len(positions) > 0:
            msg += f"""

<b>현재 포지션 ({len(positions)}개):</b>
━━━━━━━━━━━━━━━━━━━━━"""
            for pos in positions:
                pnl_emoji = "📈" if pos.pnl_percent > 0 else "📉"
                pnl_sign = "+" if pos.pnl_percent > 0 else ""
                msg += f"\n• {pos.symbol} {pos.direction}: {pnl_emoji} {pnl_sign}{pos.pnl_percent:.2f}%"
        elif is_running:
            msg += "\n\n📭 현재 열린 포지션 없음"

        msg += f"\n\n⏰ {cls._format_timestamp()}"
        return msg

    @classmethod
    def help_message(cls) -> str:
        """도움말 메시지"""
        msg = """📚 <b>명령어 도움말</b>

<b>📊 조회 명령어</b>
━━━━━━━━━━━━━━━━━━━━━
/status - 봇 상태 확인
/balance - 잔고 조회
/daily - 오늘 거래 현황
/profit - 수익 현황
/performance - 성과 분석

<b>🤖 제어 명령어</b>
━━━━━━━━━━━━━━━━━━━━━
/start - 봇 시작
/stop - 봇 정지
/stopentry - 신규 진입 중지

<b>ℹ️ 기타</b>
━━━━━━━━━━━━━━━━━━━━━
/help - 도움말 표시
/count - 거래 횟수 조회

💡 버튼을 클릭하거나 명령어를 입력하세요."""
        return msg

    @classmethod
    def count_trades(cls, total: int, today: int, week: int) -> str:
        """거래 횟수 메시지"""
        msg = f"""📊 <b>거래 횟수</b>

━━━━━━━━━━━━━━━━━━━━━
• 오늘: {today}회
• 이번 주: {week}회
• 전체: {total}회

⏰ {cls._format_timestamp()}"""
        return msg

    @classmethod
    def profit_summary(
        cls, today_pnl: float, week_pnl: float, month_pnl: float, total_pnl: float
    ) -> str:
        """수익 요약 메시지"""

        def format_pnl(pnl: float) -> str:
            emoji = "📈" if pnl >= 0 else "📉"
            sign = "+" if pnl >= 0 else ""
            return f"{emoji} {sign}{pnl:,.2f} USDT"

        msg = f"""💰 <b>수익 현황</b>

━━━━━━━━━━━━━━━━━━━━━
• 오늘: {format_pnl(today_pnl)}
• 이번 주: {format_pnl(week_pnl)}
• 이번 달: {format_pnl(month_pnl)}
• 전체: {format_pnl(total_pnl)}

⏰ {cls._format_timestamp()}"""
        return msg
