"""
텔레그램 알림 봇 서비스
"""

from .messages import TelegramMessages
from .notifier import TelegramNotifier, get_telegram_notifier, init_telegram_notifier
from .types import (
    BotConfig,
    ErrorInfo,
    OrderFilledInfo,
    # 상세 알림 타입
    OrderInfo,
    PartialCloseInfo,
    PositionInfo,
    RiskAlertInfo,
    SessionSummary,
    SignalInfo,
    StopLossInfo,
    TakeProfitInfo,
    TradeInfo,
    TradeResult,
    WarningInfo,
)

__all__ = [
    "TelegramNotifier",
    "TelegramMessages",
    "get_telegram_notifier",
    "init_telegram_notifier",
    "TradeInfo",
    "TradeResult",
    "BotConfig",
    "SessionSummary",
    "PositionInfo",
    "WarningInfo",
    "ErrorInfo",
    # 상세 알림 타입
    "OrderInfo",
    "OrderFilledInfo",
    "StopLossInfo",
    "TakeProfitInfo",
    "PartialCloseInfo",
    "RiskAlertInfo",
    "SignalInfo",
]
