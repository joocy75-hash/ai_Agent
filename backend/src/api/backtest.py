import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..schemas.backtest_schema import BacktestStartRequest
from ..schemas.backtest_response_schema import BacktestStartResponse
from ..services.backtest_engine import BacktestEngine
from ..services.backtest_persistence import BacktestPersistenceService
from ..services.strategies.registry import get_strategy
from ..database.session import get_session
from ..database.models import BacktestResult
from ..utils.jwt_auth import get_current_user_id
from ..utils.resource_manager import resource_manager
from ..config import BacktestConfig

router = APIRouter(prefix="/backtest", tags=["backtest"])


def validate_csv_path(csv_path: str) -> None:
    """
    CSV 파일 경로 검증 (Path Traversal 방지)

    Args:
        csv_path: 검증할 CSV 파일 경로

    Raises:
        HTTPException: 경로가 유효하지 않거나 안전하지 않은 경우

    Security:
        - 절대 경로로 변환하여 ".." 등의 상대 경로 공격 방지
        - 허용된 디렉토리 내에 있는지 확인
        - 파일 존재 여부 확인
    """
    try:
        # 절대 경로로 변환
        abs_path = Path(csv_path).resolve()

        # 허용된 디렉토리 목록 (프로젝트 루트 기준)
        # 실제 환경에 맞게 수정 필요
        project_root = Path(__file__).parent.parent.parent
        allowed_dirs = [
            project_root / "data",
            project_root / "backtest_data",
            project_root / "uploads",
        ]

        # 파일이 허용된 디렉토리 내에 있는지 확인
        is_allowed = any(
            abs_path.is_relative_to(allowed_dir) for allowed_dir in allowed_dirs
        )

        if not is_allowed:
            raise HTTPException(
                status_code=403,
                detail="Access denied: CSV file must be in an allowed directory",
            )

        # 파일 존재 여부 확인
        if not abs_path.exists():
            raise HTTPException(
                status_code=400, detail=f"CSV file not found: {csv_path}"
            )

        # CSV 파일인지 확인
        if abs_path.suffix.lower() != ".csv":
            raise HTTPException(status_code=400, detail="File must have .csv extension")

    except ValueError as e:
        # Path.is_relative_to() 에러 (Python 3.9+)
        raise HTTPException(status_code=403, detail="Invalid file path")


def _run_backtest_background(result_id: int, request_dict: dict, user_id: int):
    """
    백그라운드에서 실행되는 백테스트 작업.
    별도 DB 세션을 사용하여 실행.
    """
    import logging
    import asyncio
    from datetime import datetime
    from ..utils.resource_manager import resource_manager

    logger = logging.getLogger(__name__)
    logger.info(f"Starting background backtest for result_id={result_id}")

    from ..database.session import _get_sync_engine

    SessionLocal = _get_sync_engine()
    session = SessionLocal()

    try:
        logger.info(f"Running backtest with params: {request_dict}")

        # CSV 경로가 없으면 캐시 시스템에서 과거 데이터 가져오기
        csv_path = request_dict.get("csv_path")

        if not csv_path:
            logger.info(
                "CSV path not provided, fetching historical data from cache/API"
            )

            # 캔들 데이터 가져오기 (캐시 우선, 없으면 API 호출)
            symbol = request_dict.get("symbol", "BTCUSDT")
            # Symbol 형식 변환: "BTC/USDT" -> "BTCUSDT"
            symbol = symbol.replace("/", "")
            timeframe = request_dict.get("timeframe", "1h")
            start_date = request_dict.get("start_date")
            end_date = request_dict.get("end_date")

            # 기본값 설정 (없으면 최근 1년)
            from datetime import datetime, timedelta

            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

            # 캐시 시스템 사용 (Rate Limit 문제 해결!)
            from ..services.candle_cache import get_candle_cache

            async def fetch_historical_data():
                cache_manager = get_candle_cache()
                # 환경변수로 제어 (기본: 오프라인 모드)
                # Rate Limit (429) 에러 방지
                candles = await cache_manager.get_candles(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    cache_only=BacktestConfig.CACHE_ONLY,  # 환경변수로 제어
                )
                return candles

            historical_data = asyncio.run(fetch_historical_data())

            if not historical_data:
                # 오프라인 모드에서 더 명확한 에러 메시지
                mode_info = (
                    "오프라인 모드" if BacktestConfig.CACHE_ONLY else "온라인 모드"
                )
                raise Exception(
                    f"📊 {mode_info}: 해당 기간의 캔들 데이터가 없습니다.\n\n"
                    f"• 심볼: {symbol}\n"
                    f"• 타임프레임: {timeframe}\n"
                    f"• 기간: {start_date} ~ {end_date}\n\n"
                    f"💡 해결 방법:\n"
                    f"1. 다른 날짜 범위를 선택하세요\n"
                    f"2. 관리자에게 데이터 다운로드를 요청하세요\n"
                    f"   (python scripts/download_candle_data.py --symbols {symbol})"
                )

            # CSV 파일로 저장
            import csv
            import tempfile
            from pathlib import Path

            # backtest_data 디렉토리에 저장
            backtest_data_dir = Path(__file__).parent.parent.parent / "backtest_data"
            backtest_data_dir.mkdir(parents=True, exist_ok=True)

            csv_filename = f"backtest_{result_id}_{symbol}_{timeframe}.csv"
            csv_path = str(backtest_data_dir / csv_filename)

            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

                for candle in historical_data:
                    writer.writerow(
                        [
                            candle["timestamp"],
                            candle["open"],
                            candle["high"],
                            candle["low"],
                            candle["close"],
                            candle["volume"],
                        ]
                    )

            logger.info(
                f"Historical data saved to {csv_path} ({len(historical_data)} candles)"
            )

            # request_dict 업데이트
            request_dict["csv_path"] = csv_path

        # 전략 선택
        strategy_code = request_dict.get("strategy_code", "openclose")
        strategy_params = request_dict.get("strategy_params", {})

        strategy = get_strategy(strategy_code, strategy_params)

        # 엔진 실행 (비동기)
        engine = BacktestEngine(strategy=strategy)
        run_output = asyncio.run(engine.run(request_dict))

        # DB 업데이트 - 성공
        result = (
            session.query(BacktestResult).filter(BacktestResult.id == result_id).first()
        )
        if result:
            result.final_balance = run_output.get("final_balance")
            result.equity_curve = str(run_output.get("equity_curve", []))
            result.status = "completed"

            # 거래 내역 저장 (기존 result 업데이트)
            BacktestPersistenceService.save_result(
                session=session,
                run_output=run_output,
                request_params=request_dict,
                result_id=result_id,
            )

            # 거래가 저장되도록 flush (commit 전에 DB에 반영)
            session.flush()

            # 성능 메트릭 계산 (CRITICAL: 전략 평가를 위한 핵심 지표)
            try:
                import json
                from ..database.models import BacktestTrade

                initial_balance = float(request_dict["initial_balance"])
                final_balance = float(result.final_balance)

                # 총 수익률
                total_return = (
                    (final_balance - initial_balance) / initial_balance
                ) * 100

                # 거래 통계
                all_trades = (
                    session.query(BacktestTrade)
                    .filter(BacktestTrade.result_id == result_id)
                    .all()
                )

                total_trades = len(all_trades)

                if total_trades > 0:
                    # 승/패 거래 구분
                    winning_trades = [t for t in all_trades if t.pnl and t.pnl > 0]
                    losing_trades = [t for t in all_trades if t.pnl and t.pnl < 0]

                    win_count = len(winning_trades)
                    loss_count = len(losing_trades)
                    win_rate = (
                        (win_count / total_trades * 100) if total_trades > 0 else 0
                    )

                    # Profit Factor
                    gross_profit = sum(float(t.pnl) for t in winning_trades)
                    gross_loss = abs(sum(float(t.pnl) for t in losing_trades))
                    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

                    # 평균 승/패
                    avg_win = (gross_profit / win_count) if win_count > 0 else 0
                    avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0
                else:
                    win_rate = 0
                    profit_factor = 0
                    avg_win = 0
                    avg_loss = 0

                # Maximum Drawdown
                equity_curve = (
                    json.loads(result.equity_curve) if result.equity_curve else []
                )
                max_dd = 0
                peak = equity_curve[0] if equity_curve else initial_balance

                for balance in equity_curve:
                    if balance > peak:
                        peak = balance
                    drawdown = ((peak - balance) / peak * 100) if peak > 0 else 0
                    if drawdown > max_dd:
                        max_dd = drawdown

                # Sharpe Ratio (단순화된 버전 - 무위험 수익률 0% 가정)
                if len(equity_curve) > 1:
                    returns = []
                    for i in range(1, len(equity_curve)):
                        ret = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[
                            i - 1
                        ]
                        returns.append(ret)

                    try:
                        import numpy as np

                        mean_return = np.mean(returns)
                        std_return = np.std(returns)
                        sharpe_ratio = (
                            (mean_return / std_return * np.sqrt(252))
                            if std_return > 0
                            else 0
                        )
                    except ImportError:
                        # numpy 없으면 수동 계산
                        mean_return = sum(returns) / len(returns)
                        variance = sum((r - mean_return) ** 2 for r in returns) / len(
                            returns
                        )
                        std_return = variance**0.5
                        sharpe_ratio = (
                            (mean_return / std_return * (252**0.5))
                            if std_return > 0
                            else 0
                        )
                else:
                    sharpe_ratio = 0

                # 메트릭 컴파일
                metrics = {
                    "total_return": round(total_return, 2),
                    "total_trades": total_trades,
                    "win_rate": round(win_rate, 2),
                    "profit_factor": round(profit_factor, 2),
                    "avg_win": round(avg_win, 2),
                    "avg_loss": round(avg_loss, 2),
                    "sharpe_ratio": round(sharpe_ratio, 2),
                    "max_drawdown": round(max_dd, 2),
                }

                # DB에 메트릭 저장
                result.metrics = json.dumps(metrics)
                session.commit()

                logger.info(
                    f"✅ Backtest metrics calculated for result {result_id}: {metrics}"
                )

            except Exception as e:
                logger.error(
                    f"❌ Failed to calculate metrics for result {result_id}: {e}",
                    exc_info=True,
                )
                # 메트릭 계산 실패해도 백테스트 결과는 유효함
                result.metrics = "{}"
                session.commit()

        session.commit()
        logger.info(f"Backtest completed successfully for result_id={result_id}")

    except Exception as exc:
        logger.error(f"Backtest failed for result_id={result_id}: {exc}", exc_info=True)
        # DB 업데이트 - 실패
        try:
            result = (
                session.query(BacktestResult)
                .filter(BacktestResult.id == result_id)
                .first()
            )
            if result:
                result.status = "failed"
                result.error_message = str(exc)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to update error status: {e}")
    finally:
        # 리소스 해제 (Rate Limit 해제)
        resource_manager.finish_backtest(user_id, result_id)
        session.close()


@router.post("/start", response_model=BacktestStartResponse)
async def start_backtest(
    request: BacktestStartRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    백테스트를 백그라운드에서 비동기로 실행하고 즉시 응답.

    JWT 인증 필요.
    사용자별 리소스 제한 적용.

    Parameters:
    - strategy_id: 데이터베이스의 전략 ID
    - initial_balance: 시작 잔고
    - start_date: 백테스트 시작 날짜 (YYYY-MM-DD)
    - end_date: 백테스트 종료 날짜 (YYYY-MM-DD)
    - csv_path: (옵션) CSV 파일 경로

    Returns:
    - result_id: 백테스트 결과 ID
    - status: "queued" (처리 중)

    결과 조회: GET /backtest/result/{result_id}
    """
    from sqlalchemy import select
    from ..database.models import Strategy

    # 0) 리소스 제한 확인
    can_start, error_msg = resource_manager.can_start_backtest(user_id)
    if not can_start:
        raise HTTPException(status_code=429, detail=error_msg)

    # 1) Strategy validation - DB에서 전략 조회 (sync session)
    result = session.execute(select(Strategy).where(Strategy.id == request.strategy_id))
    strategy = result.scalars().first()

    if not strategy:
        raise HTTPException(
            status_code=404, detail=f"Strategy not found: {request.strategy_id}"
        )

    if not strategy.is_active:
        raise HTTPException(status_code=400, detail="Strategy is not active")

    # 2) Initial balance validation
    if request.initial_balance <= 0:
        raise HTTPException(
            status_code=400, detail="initial_balance must be greater than 0"
        )

    # 3) CSV path validation (옵션)
    if request.csv_path:
        validate_csv_path(request.csv_path)

    # 4) 전략 파라미터 추출
    import json

    strategy_params = json.loads(strategy.params) if strategy.params else {}
    strategy_type = strategy_params.get("type", "openclose")
    symbol = strategy_params.get("symbol", "BTCUSDT")
    timeframe = strategy_params.get("timeframe", "1h")

    # 5) DB에 pending 상태로 먼저 저장 (user_id 포함)
    backtest_result = BacktestResult(
        user_id=user_id,
        pair=symbol,
        timeframe=timeframe,
        initial_balance=request.initial_balance,
        final_balance=0.0,
        metrics="{}",
        equity_curve="[]",
        params=str(request.dict()),
        status="queued",
        created_at=datetime.utcnow(),
    )
    session.add(backtest_result)
    session.commit()
    session.refresh(backtest_result)

    result_id = backtest_result.id

    # 6) 리소스 매니저에 백테스트 시작 기록
    resource_manager.start_backtest(user_id, result_id)

    # 7) 백그라운드 태스크용 파라미터 준비
    task_params = {
        "strategy_id": request.strategy_id,
        "strategy_code": strategy_type,  # Use type from params, not DB code
        "strategy_params": strategy_params,
        "initial_balance": request.initial_balance,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "csv_path": request.csv_path,
        "symbol": symbol,
        "timeframe": timeframe,
    }

    # 8) 백그라운드 태스크 추가
    background_tasks.add_task(
        _run_backtest_background,
        result_id=result_id,
        request_dict=task_params,
        user_id=user_id,
    )

    # 4) 즉시 응답
    response = {
        "status": "queued",
        "result_id": result_id,
        "final_balance": 0.0,
        "metrics": {},
    }
    return response


@router.get("/cache/info")
async def get_cache_info():
    """
    백테스트 캐시 정보 조회

    사용 가능한 심볼, 타임프레임, 데이터 범위 반환

    Returns:
        - mode: 현재 데이터 모드 (offline/online)
        - cache_dir: 캐시 디렉토리 경로
        - total_files: 총 캐시 파일 수
        - available_data: 사용 가능한 데이터 목록
    """
    from ..services.candle_cache import get_candle_cache

    cache_manager = get_candle_cache()
    info = cache_manager.get_cache_info()

    # 프론트엔드용 형식으로 변환
    available_data = []

    caches = info.get("caches", {})
    for cache_key, meta in caches.items():
        if isinstance(meta, dict) and "start" in meta:
            try:
                start_ts = meta.get("start", 0)
                end_ts = meta.get("end", 0)

                # 타임스탬프가 밀리초인 경우 초로 변환
                if start_ts > 1e12:
                    start_ts = start_ts / 1000
                if end_ts > 1e12:
                    end_ts = end_ts / 1000

                available_data.append(
                    {
                        "symbol": meta.get("symbol", cache_key.split("_")[0]),
                        "timeframe": meta.get(
                            "timeframe",
                            cache_key.split("_")[1] if "_" in cache_key else "1h",
                        ),
                        "candle_count": meta.get("count", 0),
                        "start_date": datetime.fromtimestamp(start_ts).strftime(
                            "%Y-%m-%d"
                        )
                        if start_ts
                        else None,
                        "end_date": datetime.fromtimestamp(end_ts).strftime("%Y-%m-%d")
                        if end_ts
                        else None,
                        "size_mb": round(meta.get("size_mb", 0), 2),
                        "updated_at": meta.get("updated_at"),
                    }
                )
            except Exception as e:
                # 메타데이터 형식 오류 시 스킵
                continue

    return {
        "mode": BacktestConfig.DATA_MODE,
        "cache_only": BacktestConfig.CACHE_ONLY,
        "cache_dir": str(BacktestConfig.CACHE_DIR),
        "total_files": info.get("total_files", 0),
        "available_data": sorted(
            available_data, key=lambda x: (x["symbol"], x["timeframe"])
        ),
    }


@router.get("/cache/symbols")
async def get_available_symbols():
    """
    사용 가능한 심볼 목록 조회 (간단 버전)

    Returns:
        - symbols: 사용 가능한 심볼 리스트
        - timeframes: 사용 가능한 타임프레임 리스트
    """
    from ..services.candle_cache import get_candle_cache

    cache_manager = get_candle_cache()
    info = cache_manager.get_cache_info()

    symbols = set()
    timeframes = set()

    caches = info.get("caches", {})
    for cache_key in caches.keys():
        parts = cache_key.replace(".csv", "").split("_")
        if len(parts) >= 2:
            symbols.add(parts[0])
            timeframes.add(parts[1])

    return {
        "symbols": sorted(list(symbols)),
        "timeframes": sorted(
            list(timeframes),
            key=lambda x: (
                0 if x.endswith("m") else 1 if x.endswith("h") else 2,
                int(x[:-1]) if x[:-1].isdigit() else 0,
            ),
        ),
    }
