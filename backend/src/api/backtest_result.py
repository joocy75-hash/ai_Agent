import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.models import BacktestResult, BacktestTrade
from ..database.session import get_session
from ..schemas.backtest_response_schema import BacktestResultResponse
from ..utils.jwt_auth import get_current_user_id

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.get("/result/{result_id}", response_model=BacktestResultResponse)
async def get_backtest_result(
    result_id: int,
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    백테스트 결과 조회 (JWT 인증 필요).

    사용자는 자신의 백테스트 결과만 조회 가능.

    Returns:
    - summary metrics
    - equity curve
    - parameters
    - all trades with cumulative PnL
    """

    result = (
        session.query(BacktestResult)
        .filter(BacktestResult.id == result_id)
        .filter(BacktestResult.user_id == user_id)  # 사용자별 격리
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Backtest result not found or access denied"
        )

    trades = (
        session.query(BacktestTrade)
        .filter(BacktestTrade.result_id == result_id)
        .order_by(BacktestTrade.id.asc())
        .all()
    )

    trades_list = []
    cumulative_pnl = 0.0

    for t in trades:
        pnl = t.pnl if t.pnl is not None else 0.0
        cumulative_pnl += pnl

        trades_list.append({
            "timestamp": t.timestamp,
            "side": t.side,
            "direction": t.direction,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "qty": t.qty,
            "fee": t.fee,
            "pnl": t.pnl,
            "cumulative_pnl": cumulative_pnl,
        })

    try:
        metrics = json.loads(result.metrics or "{}")
    except Exception:
        metrics = {}

    try:
        equity_curve = json.loads(result.equity_curve or "[]")
    except Exception:
        equity_curve = []

    try:
        params = json.loads(result.params or "{}")
    except Exception:
        params = {}

    response = {
        "id": result.id,
        "pair": result.pair,
        "timeframe": result.timeframe,
        "initial_balance": float(result.initial_balance),
        "final_balance": float(result.final_balance),
        "status": result.status,  # Added status field
        "error_message": result.error_message,  # Added error_message field
        "metrics": metrics,
        "equity_curve": equity_curve,
        "params": params,
        "created_at": result.created_at,
        "trades": trades_list,
    }

    return response
