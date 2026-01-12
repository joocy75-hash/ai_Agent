"""
백테스트 내역 및 결과 목록 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import BacktestResult
from ..services.candle_cache import get_candle_cache
from ..utils.jwt_auth import get_current_user_id

router = APIRouter(prefix="/backtest_history", tags=["backtest_history"])


@router.get("/history")
async def get_backtest_history(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """백테스트 내역 조회 (최근 50개)"""
    result = await session.execute(
        select(BacktestResult)
        .where(BacktestResult.user_id == user_id)
        .order_by(desc(BacktestResult.created_at))
        .limit(limit)
    )
    backtests = result.scalars().all()

    return {
        "backtests": [
            {
                "id": bt.id,
                "strategy_id": bt.strategy_id,
                "symbol": bt.symbol,
                "timeframe": bt.timeframe,
                "start_date": bt.start_date.isoformat() if bt.start_date else None,
                "end_date": bt.end_date.isoformat() if bt.end_date else None,
                "initial_balance": float(bt.initial_balance)
                if bt.initial_balance
                else 0,
                "final_balance": float(bt.final_balance) if bt.final_balance else 0,
                "total_return": float(bt.total_return) if bt.total_return else 0,
                "sharpe_ratio": float(bt.sharpe_ratio) if bt.sharpe_ratio else 0,
                "max_drawdown": float(bt.max_drawdown) if bt.max_drawdown else 0,
                "win_rate": float(bt.win_rate) if bt.win_rate else 0,
                "total_trades": bt.total_trades or 0,
                "created_at": bt.created_at.isoformat() if bt.created_at else None,
            }
            for bt in backtests
        ]
    }


@router.get("/results")
async def get_all_backtest_results(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """모든 백테스트 결과 조회"""
    result = await session.execute(
        select(BacktestResult)
        .where(BacktestResult.user_id == user_id)
        .order_by(desc(BacktestResult.created_at))
    )
    backtests = result.scalars().all()

    return {
        "results": [
            {
                "id": bt.id,
                "strategy_id": bt.strategy_id,
                "symbol": bt.symbol,
                "timeframe": bt.timeframe,
                "total_return": float(bt.total_return) if bt.total_return else 0,
                "sharpe_ratio": float(bt.sharpe_ratio) if bt.sharpe_ratio else 0,
                "max_drawdown": float(bt.max_drawdown) if bt.max_drawdown else 0,
                "win_rate": float(bt.win_rate) if bt.win_rate else 0,
                "total_trades": bt.total_trades or 0,
                "created_at": bt.created_at.isoformat() if bt.created_at else None,
            }
            for bt in backtests
        ]
    }


# ==================== 캔들 캐시 관리 API ====================


@router.get("/cache/info")
async def get_cache_info(
    user_id: int = Depends(get_current_user_id),
):
    """
    캔들 데이터 캐시 정보 조회

    Returns:
        캐시 디렉토리 경로, 파일 목록, 각 캐시의 정보
    """
    cache = get_candle_cache()
    return cache.get_cache_info()


@router.post("/cache/preload")
async def preload_cache(
    user_id: int = Depends(get_current_user_id),
):
    """
    인기 심볼 데이터 프리로드

    BTC, ETH 등 인기 심볼의 최근 1년 데이터를 미리 캐싱합니다.
    """
    cache = get_candle_cache()
    await cache.preload_popular_symbols()
    return {"message": "Preload started", "status": "success"}


@router.delete("/cache/clear")
async def clear_cache(
    symbol: str = None,
    timeframe: str = None,
    user_id: int = Depends(get_current_user_id),
):
    """
    캐시 삭제

    Args:
        symbol: 심볼 (없으면 전체)
        timeframe: 타임프레임 (없으면 전체)
    """
    cache = get_candle_cache()
    cache.clear_cache(symbol, timeframe)

    if symbol and timeframe:
        return {"message": f"Cache cleared: {symbol} {timeframe}"}
    else:
        return {"message": "All cache cleared"}
