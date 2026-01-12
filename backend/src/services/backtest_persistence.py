import json
from datetime import datetime

from sqlalchemy.orm import Session

from ..database.models import BacktestResult, BacktestTrade


class BacktestPersistenceService:
    """
    Handles saving backtest results (summary, trades, equity) into DB.
    """

    @staticmethod
    def save_result(session: Session, run_output: dict, request_params: dict, result_id: int = None) -> int:
        """
        Persist BacktestEngine.run() output into DB.

        Args:
            session: SQLAlchemy Session
            run_output: dict returned by BacktestEngine.run()
            request_params: request body from /backtest/start
            result_id: Optional existing result ID to update (if None, creates new)
        Returns:
            result_id: int
        """

        # 1) Summary 저장 or 업데이트
        if result_id:
            # Update existing result
            result = session.query(BacktestResult).filter(BacktestResult.id == result_id).first()
            if not result:
                raise ValueError(f"BacktestResult with id={result_id} not found")
        else:
            # Create new result
            result = BacktestResult(
                user_id=request_params.get("user_id"),  # user_id 필수
                pair=request_params.get("pair"),
                timeframe=request_params.get("timeframe"),
                initial_balance=request_params.get("initial_balance", 1000.0),
                final_balance=run_output.get("final_balance"),
                metrics=json.dumps(run_output.get("metrics", {})),
                equity_curve=json.dumps(run_output.get("equity_curve", [])),
                params=json.dumps(request_params),
                created_at=datetime.utcnow(),
            )
            session.add(result)
            session.flush()   # result.id 확보
            result_id = result.id

        # 2) Trade 저장
        trades = run_output.get("trades", [])
        for t in trades:
            trade = BacktestTrade(
                result_id=result_id,
                timestamp=t.get("timestamp"),
                side=t.get("side"),
                direction=t.get("direction"),
                entry_price=t.get("entry_price"),
                exit_price=t.get("exit_price"),
                qty=t.get("qty"),
                fee=t.get("fee"),
                pnl=t.get("pnl"),
            )
            session.add(trade)

        return result_id
