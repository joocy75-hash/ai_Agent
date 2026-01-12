"""
캐시 기반 백테스트 서비스

일반 회원들이 API Rate Limit 걱정 없이
무제한으로 백테스트를 실행할 수 있도록 설계됨.

특징:
1. 저장된 CSV 캐시 데이터만 사용 (API 호출 없음)
2. Rate Limit 없음 - 무제한 실행 가능
3. 빠른 속도 - 로컬 파일 읽기
4. 동시성 안전 - 여러 사용자 동시 사용 가능

작성일: 2025-12-13
"""

import csv
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..database.models import GridMode, PositionDirection

logger = logging.getLogger(__name__)


@dataclass
class CachedCandle:
    """캐시된 캔들 데이터"""

    timestamp: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)


class CacheBacktestService:
    """
    캐시 기반 백테스트 서비스

    API 호출 없이 로컬 CSV 파일만 사용하여
    백테스트를 무제한으로 실행할 수 있습니다.

    사용 예시:
        service = CacheBacktestService()

        # 사용 가능한 데이터 확인
        available = service.get_available_data()

        # 백테스트 실행
        result = await service.run_grid_backtest(
            symbol="BTCUSDT",
            timeframe="1h",
            days=30,
            direction=PositionDirection.LONG,
            lower_price=90000,
            upper_price=100000,
            grid_count=10,
            investment=1000,
            leverage=5,
        )
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        서비스 초기화

        Args:
            cache_dir: 캐시 디렉토리 경로 (None이면 기본 경로 사용)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / "candle_cache"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📦 CacheBacktestService initialized: {self.cache_dir}")

    def get_available_data(self) -> Dict[str, Any]:
        """
        사용 가능한 캐시 데이터 목록 조회

        Returns:
            사용 가능한 심볼, 타임프레임, 캔들 수 정보
        """
        available = {
            "symbols": set(),
            "timeframes": set(),
            "data": [],
        }

        for csv_file in self.cache_dir.glob("*.csv"):
            parts = csv_file.stem.split("_")
            if len(parts) >= 2:
                symbol = parts[0]
                timeframe = parts[1]

                available["symbols"].add(symbol)
                available["timeframes"].add(timeframe)

                # 캔들 수 계산 (헤더 제외)
                try:
                    with open(csv_file, "r") as f:
                        candle_count = sum(1 for _ in f) - 1
                except Exception:
                    candle_count = 0

                available["data"].append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "candle_count": candle_count,
                        "file": csv_file.name,
                    }
                )

        available["symbols"] = sorted(available["symbols"])
        available["timeframes"] = sorted(
            available["timeframes"],
            key=lambda x: (
                0 if x.endswith("m") else 1 if x.endswith("h") else 2,
                int(x.replace("m", "").replace("h", "").replace("d", ""))
                if x[:-1].isdigit()
                else 0,
            ),
        )

        return available

    def load_candles(
        self,
        symbol: str,
        timeframe: str,
        days: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[CachedCandle]:
        """
        캐시에서 캔들 데이터 로드

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
            timeframe: 타임프레임 (예: 1h)
            days: 최근 N일 데이터 (start_date보다 우선)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            캔들 데이터 리스트

        Raises:
            FileNotFoundError: 캐시 파일이 없는 경우
            ValueError: 데이터가 없는 경우
        """
        symbol = symbol.upper().replace("/", "")
        cache_file = self.cache_dir / f"{symbol}_{timeframe}.csv"

        if not cache_file.exists():
            raise FileNotFoundError(
                f"캐시 데이터 없음: {symbol} {timeframe}\n"
                f"사용 가능한 데이터: {self.get_available_data()['data']}"
            )

        candles = []
        with open(cache_file, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                candles.append(
                    CachedCandle(
                        timestamp=int(row["timestamp"]),
                        open=Decimal(row["open"]),
                        high=Decimal(row["high"]),
                        low=Decimal(row["low"]),
                        close=Decimal(row["close"]),
                        volume=Decimal(row["volume"]),
                    )
                )

        if not candles:
            raise ValueError(f"캐시 파일이 비어있음: {cache_file}")

        # 기간 필터링
        if days:
            # 최근 N일
            now_ts = datetime.now().timestamp() * 1000
            start_ts = now_ts - (days * 24 * 60 * 60 * 1000)
            candles = [c for c in candles if c.timestamp >= start_ts]
        elif start_date or end_date:
            if start_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                start_ts = int(start_dt.timestamp() * 1000)
                candles = [c for c in candles if c.timestamp >= start_ts]

            if end_date:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                )
                end_ts = int(end_dt.timestamp() * 1000)
                candles = [c for c in candles if c.timestamp <= end_ts]

        if not candles:
            raise ValueError(
                f"지정된 기간에 데이터 없음: {symbol} {timeframe}\n"
                f"요청 기간: days={days}, start={start_date}, end={end_date}"
            )

        logger.info(
            f"📊 Loaded {len(candles)} candles from cache: {symbol} {timeframe}"
        )
        return candles

    async def run_grid_backtest(
        self,
        symbol: str,
        timeframe: str,
        direction: PositionDirection,
        lower_price: float,
        upper_price: float,
        grid_count: int,
        investment: float,
        leverage: int = 5,
        grid_mode: GridMode = GridMode.ARITHMETIC,
        days: int = 30,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        그리드 백테스트 실행 (캐시 데이터 사용)

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
            timeframe: 타임프레임 (1m, 5m, 15m, 1h, 4h 등)
            direction: 포지션 방향 (LONG/SHORT)
            lower_price: 하단 가격
            upper_price: 상단 가격
            grid_count: 그리드 개수
            investment: 투자금액 (USDT)
            leverage: 레버리지 (기본: 5)
            grid_mode: 그리드 모드 (ARITHMETIC/GEOMETRIC)
            days: 백테스트 기간 (일)
            start_date: 시작일 (YYYY-MM-DD, days보다 우선)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            백테스트 결과 딕셔너리

        예시:
            result = await service.run_grid_backtest(
                symbol="BTCUSDT",
                timeframe="1h",
                direction=PositionDirection.LONG,
                lower_price=90000,
                upper_price=100000,
                grid_count=10,
                investment=1000,
                leverage=5,
                days=30,
            )
        """
        # 1. 캐시에서 캔들 로드
        candles = self.load_candles(
            symbol=symbol,
            timeframe=timeframe,
            days=days if not start_date else None,
            start_date=start_date,
            end_date=end_date,
        )

        # 2. Decimal 변환
        lower_price = Decimal(str(lower_price))
        upper_price = Decimal(str(upper_price))
        investment = Decimal(str(investment))

        # 3. 그리드 가격 계산
        grid_prices = self._calculate_grid_prices(
            lower_price, upper_price, grid_count, grid_mode
        )

        # 4. 그리드당 투자금액
        per_grid_amount = (investment * leverage) / grid_count

        # 5. 시뮬레이션 실행
        result = self._run_simulation(
            candles=candles,
            grid_prices=grid_prices,
            direction=direction,
            per_grid_amount=per_grid_amount,
            investment=investment,
        )

        # 6. 메타 정보 추가
        result.update(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": direction.value,
                "lower_price": float(lower_price),
                "upper_price": float(upper_price),
                "grid_count": grid_count,
                "grid_mode": grid_mode.value,
                "leverage": leverage,
                "investment": float(investment),
                "total_candles": len(candles),
                "backtest_days": days,
                "data_source": "cache",  # API 호출 없음
            }
        )

        logger.info(
            f"✅ Grid backtest complete: {symbol} {timeframe} | "
            f"ROI: {result['roi_30d']}% | Trades: {result['total_trades']}"
        )

        return result

    def _run_simulation(
        self,
        candles: List[CachedCandle],
        grid_prices: List[Decimal],
        direction: PositionDirection,
        per_grid_amount: Decimal,
        investment: Decimal,
    ) -> Dict[str, Any]:
        """그리드 트레이딩 시뮬레이션"""

        # 수수료율
        TAKER_FEE = Decimal("0.0006")  # 0.06%

        # 그리드 상태 초기화
        grids = [
            {"price": p, "filled": False, "fill_price": None, "fill_time": None}
            for p in grid_prices
        ]

        trades = []
        equity = investment
        peak_equity = investment
        max_drawdown = Decimal("0")
        daily_equity = {}

        # 첫 캔들 가격
        initial_price = candles[0].close

        # 초기 그리드 설정
        for grid in grids:
            if direction == PositionDirection.LONG:
                if grid["price"] < initial_price:
                    grid["filled"] = True
                    grid["fill_price"] = grid["price"]
                    grid["fill_time"] = candles[0].datetime
            else:
                if grid["price"] > initial_price:
                    grid["filled"] = True
                    grid["fill_price"] = grid["price"]
                    grid["fill_time"] = candles[0].datetime

        # 캔들 순회
        current_date = None
        for candle in candles:
            # 일별 자산 기록
            date_str = candle.datetime.strftime("%Y-%m-%d")
            if date_str != current_date:
                current_date = date_str
                daily_equity[date_str] = equity

            price_high = candle.high
            price_low = candle.low

            # 그리드 처리
            for i, grid in enumerate(grids):
                if direction == PositionDirection.LONG:
                    # 매수
                    if not grid["filled"] and price_low <= grid["price"]:
                        grid["filled"] = True
                        grid["fill_price"] = grid["price"]
                        grid["fill_time"] = candle.datetime

                    # 매도
                    if grid["filled"] and i < len(grids) - 1:
                        next_grid = grids[i + 1]
                        if price_high >= next_grid["price"]:
                            quantity = per_grid_amount / grid["fill_price"]
                            sell_price = next_grid["price"]
                            fee = (
                                (grid["fill_price"] + sell_price) * quantity * TAKER_FEE
                            )
                            profit = (sell_price - grid["fill_price"]) * quantity - fee

                            trades.append(
                                {
                                    "buy": float(grid["fill_price"]),
                                    "sell": float(sell_price),
                                    "profit": float(profit),
                                    "time": candle.datetime.isoformat(),
                                }
                            )
                            equity += profit

                            grid["filled"] = False
                            grid["fill_price"] = None
                            grid["fill_time"] = None
                else:
                    # 숏: 매도 진입
                    if not grid["filled"] and price_high >= grid["price"]:
                        grid["filled"] = True
                        grid["fill_price"] = grid["price"]
                        grid["fill_time"] = candle.datetime

                    # 숏: 매수 청산
                    if grid["filled"] and i > 0:
                        prev_grid = grids[i - 1]
                        if price_low <= prev_grid["price"]:
                            quantity = per_grid_amount / grid["fill_price"]
                            buy_price = prev_grid["price"]
                            fee = (
                                (grid["fill_price"] + buy_price) * quantity * TAKER_FEE
                            )
                            profit = (grid["fill_price"] - buy_price) * quantity - fee

                            trades.append(
                                {
                                    "sell": float(grid["fill_price"]),
                                    "buy": float(buy_price),
                                    "profit": float(profit),
                                    "time": candle.datetime.isoformat(),
                                }
                            )
                            equity += profit

                            grid["filled"] = False
                            grid["fill_price"] = None
                            grid["fill_time"] = None

            # 낙폭 계산
            if equity > peak_equity:
                peak_equity = equity
            if peak_equity > 0:
                drawdown = (peak_equity - equity) / peak_equity * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        # 결과 계산
        total_profit = sum(t["profit"] for t in trades) if trades else 0
        total_roi = (
            (Decimal(str(total_profit)) / investment * 100)
            if investment > 0
            else Decimal("0")
        )

        winning = [t for t in trades if t["profit"] > 0]
        losing = [t for t in trades if t["profit"] <= 0]
        win_rate = (len(winning) / len(trades) * 100) if trades else 0

        # 일별 ROI
        daily_roi = []
        prev_eq = float(investment)
        for d in sorted(daily_equity.keys()):
            eq = float(daily_equity[d])
            day_roi = ((eq - prev_eq) / prev_eq * 100) if prev_eq > 0 else 0
            daily_roi.append(round(day_roi, 2))
            prev_eq = eq

        # 누적 ROI
        cumulative_roi = []
        cum = 0
        for roi in daily_roi:
            cum += roi
            cumulative_roi.append(round(cum, 2))

        return {
            "total_roi": round(float(total_roi), 2),
            "roi_30d": round(float(total_roi), 2),
            "max_drawdown": round(float(max_drawdown), 2),
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(win_rate, 2),
            "total_profit": round(total_profit, 2),
            "avg_profit_per_trade": round(total_profit / len(trades), 2)
            if trades
            else 0,
            "daily_roi": cumulative_roi,
            "equity_curve": [
                float(daily_equity.get(d, investment))
                for d in sorted(daily_equity.keys())
            ],
            "trades": trades[-50:],  # 최근 50개만
        }

    def _calculate_grid_prices(
        self,
        lower_price: Decimal,
        upper_price: Decimal,
        grid_count: int,
        grid_mode: GridMode,
    ) -> List[Decimal]:
        """그리드 가격 배열 계산"""
        import math
        from decimal import ROUND_DOWN

        prices = []

        if grid_mode == GridMode.ARITHMETIC:
            step = (upper_price - lower_price) / (grid_count - 1)
            for i in range(grid_count):
                price = lower_price + (step * i)
                prices.append(
                    price.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
                )
        else:
            ratio = math.pow(float(upper_price / lower_price), 1 / (grid_count - 1))
            for i in range(grid_count):
                price = lower_price * Decimal(str(pow(ratio, i)))
                prices.append(
                    price.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
                )

        return prices


# 싱글톤
_cache_backtest_service: Optional[CacheBacktestService] = None


def get_cache_backtest_service() -> CacheBacktestService:
    """캐시 백테스트 서비스 인스턴스 반환"""
    global _cache_backtest_service
    if _cache_backtest_service is None:
        _cache_backtest_service = CacheBacktestService()
    return _cache_backtest_service
