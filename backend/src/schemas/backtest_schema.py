from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from ..database.models import GridMode, PositionDirection
from ..utils.validators import (
    ValidationRules,
    validate_file_path,
    validate_positive_number,
)


class BacktestStartRequest(BaseModel):
    """
    /backtest/start 요청 바디 스키마.

    - strategy_id: 데이터베이스의 전략 ID
    - initial_balance: 시작 잔고
    - start_date: 백테스트 시작 날짜 (YYYY-MM-DD)
    - end_date: 백테스트 종료 날짜 (YYYY-MM-DD)
    - csv_path: (옵션) CSV 파일 경로 (지정하지 않으면 Bitget API에서 자동 다운로드)
    """
    strategy_id: int
    initial_balance: float = 10000.0
    start_date: str
    end_date: str
    csv_path: Optional[str] = None

    @field_validator('csv_path')
    @classmethod
    def validate_csv_path(cls, v: Optional[str]) -> Optional[str]:
        """CSV 파일 경로 검증 (Path Traversal 방지)"""
        if v is None:
            return None
        path = validate_file_path(v, ValidationRules.ALLOWED_CSV_EXTENSIONS)
        return str(path)

    @field_validator('initial_balance')
    @classmethod
    def validate_balance(cls, v: float) -> float:
        """초기 잔고 범위 검증"""
        return validate_positive_number(
            v,
            min_value=ValidationRules.BALANCE_MIN,
            max_value=ValidationRules.BALANCE_MAX,
            field_name="initial_balance"
        )

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """날짜 형식 검증 (YYYY-MM-DD)"""
        from datetime import datetime
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError as e:
            raise ValueError(f"Invalid date format: {v}. Expected YYYY-MM-DD") from e


# ===== Grid Bot Backtest Schemas =====

class GridBacktestRequest(BaseModel):
    """그리드봇 백테스트 요청 (관리자용 직접 테스트)"""
    symbol: str = Field(..., min_length=3, max_length=20)
    direction: PositionDirection
    lower_price: Decimal = Field(..., gt=0)
    upper_price: Decimal = Field(..., gt=0)
    grid_count: int = Field(..., ge=2, le=200)
    grid_mode: GridMode = GridMode.ARITHMETIC
    leverage: int = Field(default=5, ge=1, le=125)
    investment: Decimal = Field(default=Decimal('1000'), gt=0)
    days: int = Field(default=30, ge=7, le=90)
    granularity: str = Field(default="5m")

    model_config = {"from_attributes": True}


class GridBacktestResponse(BaseModel):
    """그리드봇 백테스트 응답"""
    success: bool = True

    # 주요 지표
    roi_30d: float              # 30일 ROI (%)
    max_drawdown: float         # 최대 낙폭 (%)
    total_trades: int           # 총 거래 수
    win_rate: float             # 승률 (%)

    # 수익 정보
    total_profit: float         # 총 수익 (USDT)
    avg_profit_per_trade: float  # 거래당 평균 수익

    # 차트 데이터
    daily_roi: List[float]      # 일별 누적 ROI (30개)

    # 메타 정보
    backtest_days: int
    total_candles: int
    grid_cycles_completed: int

    model_config = {"from_attributes": True}


class GridBacktestSummary(BaseModel):
    """간단한 백테스트 결과 요약"""
    roi_30d: float
    max_drawdown: float
    win_rate: float
    total_trades: int

    model_config = {"from_attributes": True}
