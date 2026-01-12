"""
일반 회원용 그리드 백테스트 API

특징:
1. 캐시 데이터만 사용 (API 호출 없음)
2. Rate Limit 없음 - 무제한 실행 가능
3. 빠른 응답 - 로컬 파일 사용
4. 간단한 인터페이스 - 회원 친화적

작성일: 2025-12-13
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..database.models import GridMode, PositionDirection
from ..services.cache_backtest_service import get_cache_backtest_service
from ..utils.jwt_auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user/backtest", tags=["user-backtest"])


# =====================================================
# Request/Response 스키마
# =====================================================


class GridBacktestRequest(BaseModel):
    """그리드 백테스트 요청"""

    symbol: str = Field(..., description="거래쌍 (예: BTCUSDT)", example="BTCUSDT")
    timeframe: str = Field(default="1h", description="타임프레임", example="1h")
    direction: str = Field(
        default="long", description="방향 (long/short)", example="long"
    )
    lower_price: float = Field(..., gt=0, description="하단 가격", example=90000)
    upper_price: float = Field(..., gt=0, description="상단 가격", example=100000)
    grid_count: int = Field(
        default=10, ge=2, le=200, description="그리드 개수", example=10
    )
    grid_mode: str = Field(
        default="arithmetic", description="그리드 모드 (arithmetic/geometric)"
    )
    investment: float = Field(
        default=1000, gt=0, description="투자금액 (USDT)", example=1000
    )
    leverage: int = Field(default=5, ge=1, le=125, description="레버리지", example=5)
    days: int = Field(
        default=30, ge=1, le=365, description="백테스트 기간 (일)", example=30
    )


class GridBacktestResponse(BaseModel):
    """그리드 백테스트 응답"""

    success: bool = True

    # 주요 지표
    roi_30d: float = Field(..., description="30일 ROI (%)")
    max_drawdown: float = Field(..., description="최대 낙폭 (%)")
    total_trades: int = Field(..., description="총 거래 수")
    win_rate: float = Field(..., description="승률 (%)")

    # 수익 정보
    total_profit: float = Field(..., description="총 수익 (USDT)")
    avg_profit_per_trade: float = Field(..., description="거래당 평균 수익")

    # 차트 데이터
    daily_roi: List[float] = Field(default=[], description="일별 누적 ROI")

    # 메타 정보
    symbol: str
    timeframe: str
    total_candles: int
    data_source: str = "cache"


class AvailableDataResponse(BaseModel):
    """사용 가능한 데이터 응답"""

    symbols: List[str]
    timeframes: List[str]
    data: List[dict]


# =====================================================
# API 엔드포인트
# =====================================================


@router.get("/available-data", response_model=AvailableDataResponse)
async def get_available_data():
    """
    백테스트에 사용 가능한 데이터 목록 조회

    캐시에 저장된 심볼, 타임프레임, 캔들 개수를 반환합니다.

    Returns:
        사용 가능한 심볼 및 타임프레임 목록
    """
    service = get_cache_backtest_service()
    data = service.get_available_data()

    return {
        "symbols": data["symbols"],
        "timeframes": data["timeframes"],
        "data": data["data"],
    }


@router.post("/grid", response_model=GridBacktestResponse)
async def run_grid_backtest(
    request: GridBacktestRequest,
    user_id: int = Depends(get_current_user_id),
):
    """
    그리드 백테스트 실행

    저장된 캐시 데이터만 사용하여 백테스트를 실행합니다.
    API 호출이 없으므로 Rate Limit 걱정 없이 무제한 실행 가능합니다.

    Parameters:
        - symbol: 거래쌍 (예: BTCUSDT)
        - timeframe: 타임프레임 (1m, 5m, 15m, 1h, 4h)
        - direction: 포지션 방향 (long/short)
        - lower_price: 그리드 하단 가격
        - upper_price: 그리드 상단 가격
        - grid_count: 그리드 개수 (2-200)
        - investment: 투자금액 (USDT)
        - leverage: 레버리지 (1-125)
        - days: 백테스트 기간 (일)

    Returns:
        백테스트 결과 (ROI, 낙폭, 거래 수, 승률 등)
    """
    logger.info(
        f"User {user_id} running grid backtest: {request.symbol} {request.timeframe}"
    )

    # 파라미터 변환
    try:
        direction = (
            PositionDirection.LONG
            if request.direction.lower() == "long"
            else PositionDirection.SHORT
        )
        grid_mode = (
            GridMode.ARITHMETIC
            if request.grid_mode.lower() == "arithmetic"
            else GridMode.GEOMETRIC
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"잘못된 파라미터: {e}") from e

    # 가격 검증
    if request.lower_price >= request.upper_price:
        raise HTTPException(
            status_code=400, detail="lower_price는 upper_price보다 작아야 합니다"
        )

    # 백테스트 실행
    service = get_cache_backtest_service()

    try:
        result = await service.run_grid_backtest(
            symbol=request.symbol,
            timeframe=request.timeframe,
            direction=direction,
            lower_price=request.lower_price,
            upper_price=request.upper_price,
            grid_count=request.grid_count,
            grid_mode=grid_mode,
            investment=request.investment,
            leverage=request.leverage,
            days=request.days,
        )

        return GridBacktestResponse(
            success=True,
            roi_30d=result["roi_30d"],
            max_drawdown=result["max_drawdown"],
            total_trades=result["total_trades"],
            win_rate=result["win_rate"],
            total_profit=result["total_profit"],
            avg_profit_per_trade=result["avg_profit_per_trade"],
            daily_roi=result["daily_roi"],
            symbol=result["symbol"],
            timeframe=result["timeframe"],
            total_candles=result["total_candles"],
            data_source=result["data_source"],
        )

    except FileNotFoundError as e:
        logger.warning(f"Cache not found for {request.symbol} {request.timeframe}")
        raise HTTPException(
            status_code=404,
            detail=f"데이터 없음: {request.symbol} {request.timeframe}. "
            f"사용 가능한 데이터는 /available-data에서 확인하세요.",
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"백테스트 실행 중 오류: {str(e)}") from e


@router.get("/quick")
async def quick_backtest(
    symbol: str = Query("BTCUSDT", description="거래쌍"),
    timeframe: str = Query("1h", description="타임프레임"),
    direction: str = Query("long", description="방향 (long/short)"),
    lower_price: float = Query(..., description="하단 가격"),
    upper_price: float = Query(..., description="상단 가격"),
    grid_count: int = Query(10, ge=2, le=100, description="그리드 개수"),
    investment: float = Query(1000, gt=0, description="투자금액"),
    leverage: int = Query(5, ge=1, le=50, description="레버리지"),
    days: int = Query(30, ge=1, le=90, description="기간 (일)"),
    user_id: int = Depends(get_current_user_id),
):
    """
    빠른 그리드 백테스트 (GET 방식)

    URL 파라미터로 간편하게 백테스트를 실행합니다.

    예시:
        /quick?symbol=BTCUSDT&lower_price=90000&upper_price=100000
    """
    request = GridBacktestRequest(
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        lower_price=lower_price,
        upper_price=upper_price,
        grid_count=grid_count,
        investment=investment,
        leverage=leverage,
        days=days,
    )

    return await run_grid_backtest(request, user_id)


@router.get("/recommended-settings")
async def get_recommended_settings(
    symbol: str = Query("BTCUSDT", description="거래쌍"),
):
    """
    추천 그리드 설정 조회

    현재 시장 상황을 기반으로 추천 설정을 반환합니다.
    """
    service = get_cache_backtest_service()

    try:
        # 최근 데이터 로드
        candles = service.load_candles(symbol, "1h", days=7)

        if not candles:
            raise HTTPException(status_code=404, detail="데이터 없음")

        # 최근 7일 고가/저가 계산
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]

        high_7d = max(highs)
        low_7d = min(lows)
        current_price = float(candles[-1].close)

        # 가격 범위 계산 (±5% 여유)
        price_range = high_7d - low_7d
        recommended_lower = low_7d - (price_range * 0.05)
        recommended_upper = high_7d + (price_range * 0.05)

        # 변동성에 따른 그리드 개수 추천
        volatility = (high_7d - low_7d) / current_price * 100
        if volatility > 20:
            recommended_grids = 20
        elif volatility > 10:
            recommended_grids = 15
        else:
            recommended_grids = 10

        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "high_7d": round(high_7d, 2),
            "low_7d": round(low_7d, 2),
            "volatility_7d": round(volatility, 2),
            "recommended": {
                "lower_price": round(recommended_lower, 2),
                "upper_price": round(recommended_upper, 2),
                "grid_count": recommended_grids,
                "direction": "long"
                if current_price < (high_7d + low_7d) / 2
                else "neutral",
                "leverage": 3 if volatility > 15 else 5,
            },
            "note": "이 추천은 최근 7일 데이터를 기반으로 합니다. 시장 상황에 따라 조정이 필요할 수 있습니다.",
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"데이터 없음: {symbol}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
