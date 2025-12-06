from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from ..utils.validators import (
    validate_file_path,
    validate_positive_number,
    validate_strategy_name,
    ValidationRules,
    sanitize_html
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
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Expected YYYY-MM-DD")
