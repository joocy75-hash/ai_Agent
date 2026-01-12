"""
Portfolio Optimization Agent 데이터 모델
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """리스크 수준"""
    CONSERVATIVE = "conservative"  # 최소 분산 포트폴리오
    MODERATE = "moderate"  # 샤프 비율 최대화
    AGGRESSIVE = "aggressive"  # 기대 수익 최대화


class BotPerformanceMetrics(BaseModel):
    """봇 성과 메트릭"""

    bot_instance_id: int
    bot_name: str
    symbol: str

    # 수익 메트릭
    roi: float = Field(description="ROI (%)")
    total_pnl: float = Field(description="총 손익")
    win_rate: float = Field(description="승률 (%)")

    # 리스크 메트릭
    sharpe_ratio: float = Field(description="샤프 비율")
    max_drawdown: float = Field(description="최대 낙폭 (%)")
    volatility: float = Field(description="변동성 (표준편차)")

    # 거래 통계
    total_trades: int = 0
    winning_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0

    # 현재 할당
    current_allocation_percent: float = Field(description="현재 할당 비율 (%)")
    current_allocation_amount: float = Field(description="현재 할당 금액 (USDT)")

    class Config:
        json_schema_extra = {
            "example": {
                "bot_instance_id": 1,
                "bot_name": "BTC 트렌드 봇",
                "symbol": "BTCUSDT",
                "roi": 15.5,
                "total_pnl": 1550.0,
                "win_rate": 65.0,
                "sharpe_ratio": 1.8,
                "max_drawdown": -8.5,
                "volatility": 12.3,
                "total_trades": 120,
                "winning_trades": 78,
                "current_allocation_percent": 20.0,
                "current_allocation_amount": 2000.0,
            }
        }


class CorrelationMatrix(BaseModel):
    """상관관계 매트릭스"""

    bot_ids: List[int] = Field(description="봇 ID 목록")
    matrix: List[List[float]] = Field(description="상관관계 행렬 (NxN)")

    class Config:
        json_schema_extra = {
            "example": {
                "bot_ids": [1, 2, 3],
                "matrix": [
                    [1.0, 0.65, 0.32],
                    [0.65, 1.0, 0.45],
                    [0.32, 0.45, 1.0],
                ],
            }
        }


class RiskContribution(BaseModel):
    """리스크 기여도"""

    bot_instance_id: int
    bot_name: str

    # 리스크 기여도
    marginal_var: float = Field(description="한계 VaR")
    component_var: float = Field(description="구성 VaR")
    contribution_percent: float = Field(description="전체 리스크 기여 비율 (%)")


class PortfolioAnalysis(BaseModel):
    """포트폴리오 분석 결과"""

    user_id: int
    total_bots: int
    total_equity: float = Field(description="총 에퀴티 (USDT)")

    # 개별 봇 성과
    bot_performance: List[BotPerformanceMetrics] = Field(default_factory=list)

    # 상관관계 분석
    correlation_matrix: Optional[CorrelationMatrix] = None

    # 리스크 기여도
    risk_contributions: List[RiskContribution] = Field(default_factory=list)

    # 포트폴리오 전체 메트릭
    portfolio_roi: float = 0.0
    portfolio_sharpe: float = 0.0
    portfolio_volatility: float = 0.0
    portfolio_max_drawdown: float = 0.0

    # 분산 효과
    diversification_ratio: float = Field(
        1.0, description="분산 비율 (1.0 = 분산 없음, >1.0 = 분산 효과)"
    )

    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class AllocationSuggestion(BaseModel):
    """할당 제안"""

    bot_instance_id: int
    bot_name: str

    # 현재 vs 제안
    current_allocation_percent: float
    suggested_allocation_percent: float
    change_percent: float = Field(description="변경량 (%)")

    # 이유
    reason: str = Field(description="할당 변경 이유")
    expected_contribution: Dict[str, float] = Field(
        default_factory=dict, description="예상 기여도 (roi, risk 등)"
    )


class RebalancingSuggestion(BaseModel):
    """리밸런싱 제안"""

    user_id: int
    risk_level: RiskLevel

    # 제안 목록
    suggestions: List[AllocationSuggestion] = Field(default_factory=list)

    # 예상 개선 효과
    current_portfolio_sharpe: float
    expected_portfolio_sharpe: float
    sharpe_improvement_percent: float

    current_portfolio_return: float
    expected_portfolio_return: float
    return_improvement_percent: float

    current_portfolio_risk: float
    expected_portfolio_risk: float
    risk_reduction_percent: float

    # 메타데이터
    optimization_method: str = "markowitz"  # "markowitz", "risk_parity", "equal_weight"
    constraints: Dict[str, Any] = Field(
        default_factory=dict, description="최적화 제약 조건"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "risk_level": "moderate",
                "suggestions": [
                    {
                        "bot_instance_id": 1,
                        "bot_name": "BTC 트렌드",
                        "current_allocation_percent": 20.0,
                        "suggested_allocation_percent": 25.0,
                        "change_percent": 5.0,
                        "reason": "높은 샤프 비율 (1.8) 및 낮은 상관관계",
                    }
                ],
                "current_portfolio_sharpe": 1.2,
                "expected_portfolio_sharpe": 1.5,
                "sharpe_improvement_percent": 25.0,
            }
        }


class RebalancingHistory(BaseModel):
    """리밸런싱 이력"""

    rebalancing_id: str
    user_id: int
    executed_at: datetime

    suggestions_applied: List[AllocationSuggestion]

    # 결과 추적
    before_snapshot: Dict[str, Any] = Field(default_factory=dict)
    after_snapshot: Dict[str, Any] = Field(default_factory=dict)
    actual_improvement: Optional[Dict[str, float]] = None


from typing import Any
