"""
Grid Bot Backtester
- 과거 데이터로 그리드 트레이딩 시뮬레이션
- 수익률, 낙폭, 승률 등 계산
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from typing import Dict, List, Optional

from ..database.models import GridMode, PositionDirection
from .candle_data_service import Candle, CandleDataService, get_candle_data_service

logger = logging.getLogger(__name__)


@dataclass
class GridLevel:
    """그리드 레벨 상태"""
    index: int
    price: Decimal
    is_filled: bool = False
    fill_price: Optional[Decimal] = None
    fill_time: Optional[datetime] = None


@dataclass
class SimulatedTrade:
    """시뮬레이션된 거래"""
    buy_price: Decimal
    sell_price: Decimal
    quantity: Decimal
    profit: Decimal
    profit_pct: Decimal
    buy_time: datetime
    sell_time: datetime
    grid_index: int


@dataclass
class BacktestResult:
    """백테스트 결과"""
    # 수익률
    total_roi: Decimal              # 총 수익률 (%)
    roi_30d: Decimal                # 30일 환산 ROI (%)

    # 위험 지표
    max_drawdown: Decimal           # 최대 낙폭 (%)
    sharpe_ratio: Optional[Decimal] = None  # 샤프 비율

    # 거래 통계
    total_trades: int = 0           # 총 거래 수
    winning_trades: int = 0         # 이긴 거래 수
    losing_trades: int = 0          # 진 거래 수
    win_rate: Decimal = Decimal('0')  # 승률 (%)

    # 수익 통계
    total_profit: Decimal = Decimal('0')        # 총 수익 (USDT)
    avg_profit_per_trade: Decimal = Decimal('0')  # 거래당 평균 수익
    max_profit_trade: Decimal = Decimal('0')    # 최대 수익 거래
    max_loss_trade: Decimal = Decimal('0')      # 최대 손실 거래

    # 시계열 데이터
    daily_roi: List[float] = field(default_factory=list)  # 일별 ROI (차트용)
    equity_curve: List[float] = field(default_factory=list)  # 자산 곡선

    # 메타 정보
    backtest_days: int = 30
    total_candles: int = 0
    grid_cycles_completed: int = 0

    def to_dict(self) -> dict:
        return {
            "total_roi": float(self.total_roi),
            "roi_30d": float(self.roi_30d),
            "max_drawdown": float(self.max_drawdown),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": float(self.win_rate),
            "total_profit": float(self.total_profit),
            "avg_profit_per_trade": float(self.avg_profit_per_trade),
            "daily_roi": self.daily_roi,
            "backtest_days": self.backtest_days,
            "grid_cycles_completed": self.grid_cycles_completed
        }


class GridBacktester:
    """
    그리드봇 백테스터

    시뮬레이션 로직:
    1. 그리드 가격 배열 계산
    2. 각 캔들마다 가격이 그리드를 통과하는지 확인
    3. 통과 시 매수/매도 시뮬레이션
    4. 수수료 차감
    5. 일별 수익률 계산
    """

    # 수수료율 (Bitget 기준)
    MAKER_FEE = Decimal('0.0002')  # 0.02%
    TAKER_FEE = Decimal('0.0006')  # 0.06%

    def __init__(self, candle_service: Optional[CandleDataService] = None):
        self.candle_service = candle_service or get_candle_data_service()

    async def run_backtest(
        self,
        symbol: str,
        direction: PositionDirection,
        lower_price: Decimal,
        upper_price: Decimal,
        grid_count: int,
        grid_mode: GridMode,
        leverage: int,
        investment: Decimal,
        days: int = 30,
        granularity: str = "5m"
    ) -> BacktestResult:
        """
        백테스트 실행

        Args:
            symbol: 심볼 (예: "SOLUSDT")
            direction: 포지션 방향 (LONG/SHORT)
            lower_price: 하단 가격
            upper_price: 상단 가격
            grid_count: 그리드 개수
            grid_mode: 그리드 모드 (ARITHMETIC/GEOMETRIC)
            leverage: 레버리지
            investment: 총 투자금액 (USDT)
            days: 백테스트 기간 (일)
            granularity: 캔들 간격

        Returns:
            BacktestResult: 백테스트 결과
        """
        logger.info(
            f"Starting backtest: {symbol} {direction.value} "
            f"[{lower_price}-{upper_price}] x{leverage} {grid_count} grids"
        )

        # Decimal 변환 (숫자 타입이 아닐 경우 대비)
        lower_price = Decimal(str(lower_price))
        upper_price = Decimal(str(upper_price))
        investment = Decimal(str(investment))

        # 1. 캔들 데이터 수집
        candles = await self.candle_service.get_candles(
            symbol=symbol,
            granularity=granularity,
            days=days
        )

        if not candles:
            raise ValueError(f"No candle data available for {symbol}")

        # 2. 그리드 가격 계산
        grid_prices = self._calculate_grid_prices(
            lower_price, upper_price, grid_count, grid_mode
        )

        # 3. 그리드당 투자금액 계산
        per_grid_amount = (investment * leverage) / grid_count

        # 4. 시뮬레이션 실행
        result = self._simulate(
            candles=candles,
            grid_prices=grid_prices,
            direction=direction,
            per_grid_amount=per_grid_amount,
            leverage=leverage,
            investment=investment
        )

        result.backtest_days = days
        result.total_candles = len(candles)

        logger.info(
            f"Backtest complete: ROI={result.roi_30d}%, "
            f"MDD={result.max_drawdown}%, Trades={result.total_trades}"
        )

        return result

    def _simulate(
        self,
        candles: List[Candle],
        grid_prices: List[Decimal],
        direction: PositionDirection,
        per_grid_amount: Decimal,
        leverage: int,
        investment: Decimal
    ) -> BacktestResult:
        """시뮬레이션 실행"""

        # 상태 초기화
        grids: List[GridLevel] = [
            GridLevel(index=i, price=p)
            for i, p in enumerate(grid_prices)
        ]

        trades: List[SimulatedTrade] = []
        equity = investment  # 현재 자산
        peak_equity = investment  # 최고 자산
        max_drawdown = Decimal('0')

        daily_equity: Dict[str, Decimal] = {}
        current_date = None

        # 첫 캔들 가격 기준으로 초기 그리드 설정
        initial_price = candles[0].close

        # LONG: 현재가 아래 그리드에 매수, SHORT: 현재가 위 그리드에 매도
        for grid in grids:
            if direction == PositionDirection.LONG:
                if grid.price < initial_price:
                    grid.is_filled = True
                    grid.fill_price = grid.price
                    grid.fill_time = candles[0].datetime
            else:  # SHORT
                if grid.price > initial_price:
                    grid.is_filled = True
                    grid.fill_price = grid.price
                    grid.fill_time = candles[0].datetime

        # 각 캔들 순회
        for candle in candles:
            # 일별 자산 기록
            date_str = candle.datetime.strftime("%Y-%m-%d")
            if date_str != current_date:
                current_date = date_str
                daily_equity[date_str] = equity

            # 가격 범위 (고가-저가)
            price_high = candle.high
            price_low = candle.low

            # 그리드 통과 확인 및 거래 실행
            for grid in grids:
                if direction == PositionDirection.LONG:
                    new_trades = self._process_long_grid(
                        grid=grid,
                        grids=grids,
                        price_low=price_low,
                        price_high=price_high,
                        per_grid_amount=per_grid_amount,
                        candle=candle,
                        trades=trades
                    )
                else:
                    new_trades = self._process_short_grid(
                        grid=grid,
                        grids=grids,
                        price_low=price_low,
                        price_high=price_high,
                        per_grid_amount=per_grid_amount,
                        candle=candle,
                        trades=trades
                    )

                # 거래 수익 반영
                for trade in new_trades:
                    equity += trade.profit

            # 최대 낙폭 계산
            if equity > peak_equity:
                peak_equity = equity
            if peak_equity > 0:
                drawdown = (peak_equity - equity) / peak_equity * 100
            else:
                drawdown = Decimal('0')
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 결과 계산
        total_profit = sum(t.profit for t in trades) if trades else Decimal('0')
        total_roi = (total_profit / investment * 100) if investment > 0 else Decimal('0')

        # 일별 ROI 계산
        daily_roi = []
        prev_equity = investment
        for date_str in sorted(daily_equity.keys()):
            day_equity = daily_equity[date_str]
            if prev_equity > 0:
                day_roi = float((day_equity - prev_equity) / prev_equity * 100)
            else:
                day_roi = 0.0
            daily_roi.append(day_roi)
            prev_equity = day_equity

        # 누적 ROI로 변환 (차트용)
        cumulative_roi = []
        cum = 0.0
        for roi in daily_roi:
            cum += roi
            cumulative_roi.append(round(cum, 2))

        winning = [t for t in trades if t.profit > 0]
        losing = [t for t in trades if t.profit <= 0]

        win_rate = Decimal('0')
        if trades:
            win_rate = (Decimal(len(winning)) / len(trades) * 100).quantize(Decimal('0.01'))

        avg_profit = Decimal('0')
        if trades:
            avg_profit = (total_profit / len(trades)).quantize(Decimal('0.01'))

        return BacktestResult(
            total_roi=total_roi.quantize(Decimal('0.01')) if isinstance(total_roi, Decimal) else Decimal(str(round(total_roi, 2))),
            roi_30d=total_roi.quantize(Decimal('0.01')) if isinstance(total_roi, Decimal) else Decimal(str(round(total_roi, 2))),
            max_drawdown=max_drawdown.quantize(Decimal('0.01')) if isinstance(max_drawdown, Decimal) else Decimal(str(round(max_drawdown, 2))),
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            total_profit=total_profit.quantize(Decimal('0.01')) if isinstance(total_profit, Decimal) else Decimal(str(round(total_profit, 2))),
            avg_profit_per_trade=avg_profit,
            max_profit_trade=max((t.profit for t in trades), default=Decimal('0')),
            max_loss_trade=min((t.profit for t in trades), default=Decimal('0')),
            daily_roi=cumulative_roi,
            equity_curve=[float(daily_equity.get(d, investment)) for d in sorted(daily_equity.keys())],
            grid_cycles_completed=len(trades)
        )

    def _process_long_grid(
        self,
        grid: GridLevel,
        grids: List[GridLevel],
        price_low: Decimal,
        price_high: Decimal,
        per_grid_amount: Decimal,
        candle: Candle,
        trades: List[SimulatedTrade]
    ) -> List[SimulatedTrade]:
        """
        LONG 그리드 처리

        - 가격 하락 시 매수 (grid price에서)
        - 가격 상승 시 매도 (다음 grid price에서)
        """
        new_trades = []

        # 매수: 가격이 그리드 아래로 내려갔다가 올라올 때
        if not grid.is_filled and price_low <= grid.price:
            grid.is_filled = True
            grid.fill_price = grid.price
            grid.fill_time = candle.datetime

        # 매도: 채워진 그리드에서 가격이 다음 그리드까지 올라갈 때
        if grid.is_filled and grid.index < len(grids) - 1:
            next_grid = grids[grid.index + 1]
            if price_high >= next_grid.price:
                # 거래 기록
                quantity = per_grid_amount / grid.fill_price
                sell_price = next_grid.price

                # 수수료 계산
                buy_fee = grid.fill_price * quantity * self.TAKER_FEE
                sell_fee = sell_price * quantity * self.TAKER_FEE
                total_fee = buy_fee + sell_fee

                gross_profit = (sell_price - grid.fill_price) * quantity
                net_profit = gross_profit - total_fee

                trade = SimulatedTrade(
                    buy_price=grid.fill_price,
                    sell_price=sell_price,
                    quantity=quantity,
                    profit=net_profit,
                    profit_pct=((sell_price - grid.fill_price) / grid.fill_price * 100),
                    buy_time=grid.fill_time,
                    sell_time=candle.datetime,
                    grid_index=grid.index
                )
                new_trades.append(trade)
                trades.append(trade)

                # 그리드 리셋 (다음 사이클 준비)
                grid.is_filled = False
                grid.fill_price = None
                grid.fill_time = None

        return new_trades

    def _process_short_grid(
        self,
        grid: GridLevel,
        grids: List[GridLevel],
        price_low: Decimal,
        price_high: Decimal,
        per_grid_amount: Decimal,
        candle: Candle,
        trades: List[SimulatedTrade]
    ) -> List[SimulatedTrade]:
        """
        SHORT 그리드 처리

        - 가격 상승 시 매도 (grid price에서)
        - 가격 하락 시 매수 (다음 grid price에서)
        """
        new_trades = []

        # 매도 진입: 가격이 그리드 위로 올라갔을 때
        if not grid.is_filled and price_high >= grid.price:
            grid.is_filled = True
            grid.fill_price = grid.price
            grid.fill_time = candle.datetime

        # 매수 청산: 채워진 그리드에서 가격이 아래 그리드까지 내려갈 때
        if grid.is_filled and grid.index > 0:
            prev_grid = grids[grid.index - 1]
            if price_low <= prev_grid.price:
                # 거래 기록 (숏 포지션)
                quantity = per_grid_amount / grid.fill_price
                buy_price = prev_grid.price  # 청산 가격

                # 수수료 계산
                sell_fee = grid.fill_price * quantity * self.TAKER_FEE
                buy_fee = buy_price * quantity * self.TAKER_FEE
                total_fee = sell_fee + buy_fee

                # 숏이므로 매도가 - 매수가 = 수익
                gross_profit = (grid.fill_price - buy_price) * quantity
                net_profit = gross_profit - total_fee

                trade = SimulatedTrade(
                    buy_price=buy_price,  # 청산가
                    sell_price=grid.fill_price,  # 진입가
                    quantity=quantity,
                    profit=net_profit,
                    profit_pct=((grid.fill_price - buy_price) / grid.fill_price * 100),
                    buy_time=candle.datetime,  # 청산 시간
                    sell_time=grid.fill_time,  # 진입 시간
                    grid_index=grid.index
                )
                new_trades.append(trade)
                trades.append(trade)

                # 그리드 리셋
                grid.is_filled = False
                grid.fill_price = None
                grid.fill_time = None

        return new_trades

    def _calculate_grid_prices(
        self,
        lower_price: Decimal,
        upper_price: Decimal,
        grid_count: int,
        grid_mode: GridMode
    ) -> List[Decimal]:
        """그리드 가격 배열 계산"""
        prices = []

        if grid_mode == GridMode.ARITHMETIC:
            # 등차 방식: 동일 가격 간격
            step = (upper_price - lower_price) / (grid_count - 1)
            for i in range(grid_count):
                price = lower_price + (step * i)
                prices.append(price.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN))
        else:
            # 등비 방식: 동일 퍼센트 간격
            ratio = math.pow(float(upper_price / lower_price), 1 / (grid_count - 1))
            for i in range(grid_count):
                price = lower_price * Decimal(str(pow(ratio, i)))
                prices.append(price.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN))

        return prices


# 싱글톤 인스턴스
_backtester_instance: Optional[GridBacktester] = None


def get_grid_backtester() -> GridBacktester:
    """GridBacktester 싱글톤 인스턴스 반환"""
    global _backtester_instance
    if _backtester_instance is None:
        _backtester_instance = GridBacktester()
    return _backtester_instance
