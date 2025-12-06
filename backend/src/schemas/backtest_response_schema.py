from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime


class BacktestResponse(BaseModel):
    """
    (이전 버전 호환용)
    현재는 사용하지 않더라도 남겨둠.
    """
    status: str
    final_balance: float
    metrics: dict


class BacktestStartResponse(BaseModel):
    """
    /backtest/start 전용 응답 스키마.
    - DB에 저장된 result_id를 함께 내려주는 확장 버전
    """
    status: str
    result_id: int
    final_balance: float
    metrics: Dict[str, float]


class BacktestTradeSchema(BaseModel):
    """
    /backtest/result/{id} 에서 반환되는 개별 트레이드 정보
    """
    timestamp: Any
    side: str
    direction: str
    entry_price: float | None
    exit_price: float | None
    qty: float | None
    fee: float | None
    pnl: float | None
    cumulative_pnl: float


class BacktestResultResponse(BaseModel):
    """
    /backtest/result/{id} 응답 스키마
    """
    id: int
    pair: str | None
    timeframe: str | None
    initial_balance: float
    final_balance: float
    status: str | None  # Added: backtest status (queued/running/completed/failed)
    error_message: str | None  # Added: error message if failed
    metrics: Dict[str, float]
    equity_curve: List[float]
    params: Dict[str, Any]
    created_at: datetime
    trades: List[BacktestTradeSchema]
