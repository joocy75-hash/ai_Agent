"""
Backtester - ML 예측 기반 백테스트

ML 모델의 실제 거래 성능을 시뮬레이션하여 검증
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """거래 기록"""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    side: str = "long"  # long or short
    entry_price: float = 0.0
    exit_price: float = 0.0
    size: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    exit_reason: str = ""  # tp, sl, signal, timeout
    ml_confidence: float = 0.0


@dataclass
class BacktestResult:
    """백테스트 결과"""
    # 기본 정보
    symbol: str = ""
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 10000.0
    final_capital: float = 10000.0

    # 성과 지표
    total_return: float = 0.0  # %
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0  # %
    win_rate: float = 0.0  # %
    profit_factor: float = 0.0

    # 거래 통계
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0  # %
    avg_loss: float = 0.0  # %
    avg_trade_duration: float = 0.0  # minutes

    # ML 관련
    avg_confidence: float = 0.0
    confidence_correlation: float = 0.0  # 신뢰도-수익률 상관관계

    # 상세 데이터
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'period': f"{self.start_date} ~ {self.end_date}",
            'initial_capital': self.initial_capital,
            'final_capital': round(self.final_capital, 2),
            'total_return': round(self.total_return, 2),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'win_rate': round(self.win_rate, 2),
            'profit_factor': round(self.profit_factor, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'avg_win': round(self.avg_win, 2),
            'avg_loss': round(self.avg_loss, 2),
            'avg_confidence': round(self.avg_confidence, 2),
            'confidence_correlation': round(self.confidence_correlation, 2),
        }


class Backtester:
    """
    ML 예측 기반 백테스터

    Usage:
    ```python
    backtester = Backtester(initial_capital=10000)
    result = backtester.run(
        candles=df_candles,
        predictions=predictions,  # ML 예측 결과 리스트
    )
    ```
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        max_position_size: float = 0.4,  # 40% max
        commission: float = 0.0006,  # 0.06%
        slippage: float = 0.0002,  # 0.02%
    ):
        self.initial_capital = initial_capital
        self.max_position_size = max_position_size
        self.commission = commission
        self.slippage = slippage

        logger.info(f"Backtester initialized (capital: ${initial_capital})")

    def run(
        self,
        candles: pd.DataFrame,
        predictions: List[Dict[str, Any]],
        symbol: str = "ETHUSDT",
    ) -> BacktestResult:
        """
        백테스트 실행

        Args:
            candles: OHLCV DataFrame (index=timestamp)
            predictions: ML 예측 결과 리스트
            symbol: 심볼

        Returns:
            BacktestResult
        """
        result = BacktestResult(
            symbol=symbol,
            initial_capital=self.initial_capital,
        )

        if len(candles) == 0 or len(predictions) == 0:
            logger.warning("Empty data, returning default result")
            return result

        # 예측을 시간별로 매핑
        pred_by_time = self._map_predictions(predictions)

        # 시뮬레이션 변수
        capital = self.initial_capital
        position: Optional[Trade] = None
        equity_curve = [capital]
        trades: List[Trade] = []

        result.start_date = str(candles.index[0])
        result.end_date = str(candles.index[-1])

        # 캔들 순회
        for _i, (timestamp, candle) in enumerate(candles.iterrows()):
            current_price = float(candle['close'])
            high = float(candle['high'])
            low = float(candle['low'])

            # 포지션이 있으면 SL/TP 체크
            if position:
                closed, exit_reason = self._check_exit(
                    position, current_price, high, low
                )

                if closed:
                    # 포지션 청산
                    position.exit_time = timestamp
                    position.exit_price = current_price
                    position.exit_reason = exit_reason
                    position.pnl = self._calculate_pnl(position)
                    position.pnl_percent = position.pnl / (position.entry_price * position.size) * 100

                    capital += position.pnl
                    trades.append(position)
                    position = None

            # 예측 확인 및 신규 진입
            if position is None and timestamp in pred_by_time:
                pred = pred_by_time[timestamp]

                if self._should_enter(pred):
                    position = self._open_position(
                        timestamp, current_price, capital, pred
                    )

            equity_curve.append(capital)

        # 열린 포지션 강제 청산
        if position:
            position.exit_time = candles.index[-1]
            position.exit_price = float(candles.iloc[-1]['close'])
            position.exit_reason = "end"
            position.pnl = self._calculate_pnl(position)
            trades.append(position)
            capital += position.pnl

        # 결과 계산
        result.final_capital = capital
        result.trades = trades
        result.equity_curve = equity_curve
        result = self._calculate_metrics(result)

        logger.info(
            f"Backtest complete: {len(trades)} trades, "
            f"Return: {result.total_return:.2f}%, "
            f"Win rate: {result.win_rate:.2f}%"
        )

        return result

    def _map_predictions(self, predictions: List[Dict]) -> Dict[Any, Dict]:
        """예측을 timestamp로 매핑"""
        result = {}
        for pred in predictions:
            ts = pred.get('timestamp')
            if ts:
                if isinstance(ts, str):
                    ts = pd.to_datetime(ts)
                result[ts] = pred
        return result

    def _should_enter(self, pred: Dict) -> bool:
        """진입 조건 확인"""
        action = pred.get('recommended_action', 'hold')
        confidence = pred.get('confidence', {}).get('overall', 0)
        timing = pred.get('timing', 'ok')

        return (
            action in ['buy', 'sell'] and
            confidence >= 0.6 and
            timing != 'bad'
        )

    def _open_position(
        self,
        timestamp: Any,
        price: float,
        capital: float,
        pred: Dict
    ) -> Trade:
        """포지션 오픈"""
        action = pred.get('recommended_action', 'buy')
        size_pct = min(
            pred.get('position_size_percent', 10) / 100,
            self.max_position_size
        )
        sl_pct = pred.get('stop_loss_percent', 2.0)

        size = (capital * size_pct) / price

        # 슬리피지 적용
        entry_price = price * (1 + self.slippage if action == 'buy' else 1 - self.slippage)

        # SL/TP 계산
        if action == 'buy':
            stop_loss = entry_price * (1 - sl_pct / 100)
            take_profit = entry_price * (1 + sl_pct * 2 / 100)  # 1:2 R:R
        else:
            stop_loss = entry_price * (1 + sl_pct / 100)
            take_profit = entry_price * (1 - sl_pct * 2 / 100)

        return Trade(
            entry_time=timestamp,
            side='long' if action == 'buy' else 'short',
            entry_price=entry_price,
            size=size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            ml_confidence=pred.get('confidence', {}).get('overall', 0),
        )

    def _check_exit(
        self,
        position: Trade,
        current_price: float,
        high: float,
        low: float
    ) -> tuple:
        """청산 조건 확인"""
        if position.side == 'long':
            # SL 체크
            if low <= position.stop_loss:
                return True, "sl"
            # TP 체크
            if high >= position.take_profit:
                return True, "tp"
        else:
            # Short
            if high >= position.stop_loss:
                return True, "sl"
            if low <= position.take_profit:
                return True, "tp"

        return False, ""

    def _calculate_pnl(self, position: Trade) -> float:
        """PnL 계산"""
        if position.side == 'long':
            gross_pnl = (position.exit_price - position.entry_price) * position.size
        else:
            gross_pnl = (position.entry_price - position.exit_price) * position.size

        # 커미션 차감
        commission = position.entry_price * position.size * self.commission * 2
        return gross_pnl - commission

    def _calculate_metrics(self, result: BacktestResult) -> BacktestResult:
        """성과 지표 계산"""
        trades = result.trades

        if not trades:
            return result

        # 기본 통계
        result.total_trades = len(trades)
        result.total_return = (result.final_capital - result.initial_capital) / result.initial_capital * 100

        # 승/패 통계
        pnls = [t.pnl for t in trades]
        winning = [p for p in pnls if p > 0]
        losing = [p for p in pnls if p < 0]

        result.winning_trades = len(winning)
        result.losing_trades = len(losing)
        result.win_rate = len(winning) / len(trades) * 100 if trades else 0

        result.avg_win = np.mean(winning) if winning else 0
        result.avg_loss = np.mean(losing) if losing else 0

        # Profit Factor
        total_win = sum(winning) if winning else 0
        total_loss = abs(sum(losing)) if losing else 1
        result.profit_factor = total_win / total_loss if total_loss > 0 else 0

        # Max Drawdown
        equity = result.equity_curve
        peak = equity[0]
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak * 100
            max_dd = max(max_dd, dd)
        result.max_drawdown = max_dd

        # Sharpe Ratio (연환산)
        if len(equity) > 1:
            returns = np.diff(equity) / equity[:-1]
            if np.std(returns) > 0:
                result.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252 * 24 * 12)  # 5분봉 기준
            result.daily_returns = returns.tolist()

        # ML 신뢰도 분석
        confidences = [t.ml_confidence for t in trades]
        result.avg_confidence = np.mean(confidences) if confidences else 0

        # 신뢰도-수익률 상관관계
        if len(trades) > 5:
            pnl_pcts = [t.pnl_percent for t in trades]
            corr = np.corrcoef(confidences, pnl_pcts)[0, 1]
            result.confidence_correlation = corr if not np.isnan(corr) else 0

        return result
