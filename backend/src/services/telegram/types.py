"""
텔레그램 알림용 데이터 타입 정의
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel


class TradeInfo(BaseModel):
    """신규 거래 정보"""

    symbol: str  # 예: "SOL/USDT"
    direction: Literal["Long", "Short"]
    entry_price: float
    quantity: float
    total_value: float  # USDT 기준 총액
    leverage: Optional[int] = 1
    timestamp: datetime = datetime.now()


class TradeResult(BaseModel):
    """포지션 종료 결과"""

    symbol: str
    direction: Literal["Long", "Short"]
    entry_price: float
    exit_price: float
    quantity: float
    pnl_percent: float  # 손익률 (%)
    pnl_usdt: float  # 손익 (USDT)
    exit_reason: str  # 예: "take_profit", "stop_loss", "exit_signal"
    duration_minutes: float  # 보유 시간 (분)
    timestamp: datetime = datetime.now()


class BotConfig(BaseModel):
    """봇 설정 정보"""

    exchange: str = "BITGET"
    trade_amount: float  # 거래당 금액 (USDT)
    stop_loss_percent: float  # 손절가 (%)
    timeframe: str  # 예: "5m", "1h"
    strategy: str  # 전략 이름
    leverage: int = 1
    margin_mode: str = "isolated"


class SessionSummary(BaseModel):
    """세션 요약 정보"""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float  # 승률 (%)
    total_pnl_usdt: float  # 총 손익 (USDT)
    total_pnl_percent: float  # 총 손익률 (%)
    duration_hours: float  # 운영 시간


class PositionInfo(BaseModel):
    """포지션 정보"""

    symbol: str
    direction: Literal["Long", "Short"]
    pnl_percent: float
    entry_price: float
    current_price: Optional[float] = None
    quantity: float
    unrealized_pnl: Optional[float] = None


class WarningInfo(BaseModel):
    """경고 정보"""

    warning_type: str  # 예: "open_positions", "low_balance", "high_drawdown"
    message: str
    positions: Optional[List[PositionInfo]] = None
    timestamp: datetime = datetime.now()


class ErrorInfo(BaseModel):
    """에러 정보"""

    error_type: str  # 예: "api_error", "connection_error", "rate_limit"
    message: str
    details: Optional[str] = None
    will_retry: bool = False
    retry_after_seconds: Optional[int] = None
    timestamp: datetime = datetime.now()


class BalanceInfo(BaseModel):
    """잔고 정보"""

    total_balance: float
    available_balance: float
    used_margin: float
    unrealized_pnl: float
    currency: str = "USDT"


class DailyStats(BaseModel):
    """일일 통계"""

    date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    pnl_usdt: float
    pnl_percent: float


class PerformanceStats(BaseModel):
    """성과 통계"""

    period: str  # 예: "7d", "30d", "all"
    total_trades: int
    win_rate: float
    total_pnl_usdt: float
    total_pnl_percent: float
    best_trade_pnl: float
    worst_trade_pnl: float
    avg_trade_duration_minutes: float
    max_drawdown_percent: float
