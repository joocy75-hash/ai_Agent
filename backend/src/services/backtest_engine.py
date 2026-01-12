import csv
import os
from io import StringIO

import aiofiles

from ..config import BacktestConfig
from .backtest_metrics import BacktestMetricsCalculator
from .backtest_trade_recorder import BacktestTradeRecorder
from .strategies.eth_ai_fusion import EthAIFusionBacktestStrategy


class BacktestEngine:
    """
    BacktestEngine (Phase G – 정확도 강화 버전)

    주요 특징:
    - CSV 캔들 로딩
    - 단일 포지션(long/short) 지원
    - 전략 클래스(StrategyBase)를 이용한 신호 생성
    - 슬리피지/수수료 방향을 일관되게 처리
    - 각 캔들마다 equity(잔고 + 미실현 손익) 기록
    - 마지막에 포지션이 열려 있으면 자동 청산
    - MetricsCalculator로 total_return / max_drawdown / win_rate 계산

    run() 반환값 구조:
    {
        "final_balance": float,
        "trades": List[dict],
        "equity_curve": List[float],
        "metrics": dict,
    }
    """

    def __init__(self, strategy=None):
        self.strategy = strategy or EthAIFusionBacktestStrategy()

    async def load_candles(self, path: str):
        """
        CSV에서 캔들 데이터 비동기 로드

        비동기 파일 I/O를 사용하여 이벤트 루프 블로킹을 방지합니다.
        대용량 CSV 파일 (100MB+)도 효율적으로 처리 가능합니다.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV not found: {path}")

        candles = []

        # 비동기 파일 읽기
        async with aiofiles.open(path, "r") as f:
            content = await f.read()

        # 메모리에서 CSV 파싱 (빠름)
        reader = csv.DictReader(StringIO(content))

        for row in reader:
            try:
                candles.append(
                    {
                        "timestamp": row["timestamp"],
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                    }
                )
            except Exception:
                continue

        return candles

    def _compute_equity(self, balance: float, position: dict | None, price: float) -> float:
        if position is None:
            return float(balance)
        entry_price = position["entry_price"]
        direction = position["direction"]
        if direction == "long":
            unrealized = (price - entry_price) * 1.0
        else:
            unrealized = (entry_price - price) * 1.0
        return float(balance + unrealized)

    async def run(self, params: dict):
        """
        백테스트 실행 (비동기)

        비동기 파일 I/O를 사용하여 CSV 로드 중에도 다른 요청 처리 가능
        """
        csv_path = params.get("csv_path")
        if not csv_path:
            raise ValueError("csv_path is required for backtesting")

        # 비동기 CSV 로드
        candles = await self.load_candles(csv_path)

        recorder = BacktestTradeRecorder()

        # 설정에서 기본값 가져오기
        initial_balance = float(
            params.get("initial_balance", BacktestConfig.DEFAULT_INITIAL_BALANCE)
        )
        balance = initial_balance

        fee_rate = float(params.get("fee_rate", BacktestConfig.DEFAULT_FEE_RATE))
        slippage = float(params.get("slippage", BacktestConfig.DEFAULT_SLIPPAGE))

        position: dict | None = None
        last_price = None

        for candle in candles:
            candle["open"]
            c = candle["close"]
            ts = candle["timestamp"]

            if c <= 0:
                equity = self._compute_equity(balance, position, last_price) if last_price else balance
                recorder.record_equity(equity)
                continue

            last_price = c

            signal = self.strategy.on_candle(candle, position)

            if position is None and signal == "buy":
                entry_price = c * (1 + slippage)
                entry_fee = entry_price * fee_rate
                balance -= entry_fee

                position = {
                    "direction": "long",
                    "entry_price": entry_price,
                    "entry_fee": entry_fee,
                    "opened_at": ts,
                }

            elif position is None and signal == "sell":
                entry_price = c * (1 - slippage)
                entry_fee = entry_price * fee_rate
                balance -= entry_fee

                position = {
                    "direction": "short",
                    "entry_price": entry_price,
                    "entry_fee": entry_fee,
                    "opened_at": ts,
                }

            elif position is not None:
                if position["direction"] == "long" and signal == "sell":
                    exit_price = c * (1 - slippage)
                    pnl = (exit_price - position["entry_price"]) * 1.0
                    exit_fee = exit_price * fee_rate
                    balance += pnl - exit_fee
                    total_fee = position["entry_fee"] + exit_fee

                    recorder.record_trade(
                        side="exit",
                        direction="long",
                        entry=position["entry_price"],
                        exit=exit_price,
                        fee=total_fee,
                        pnl=pnl,
                        timestamp=ts,
                    )
                    position = None

                elif position["direction"] == "short" and signal == "buy":
                    exit_price = c * (1 + slippage)
                    pnl = (position["entry_price"] - exit_price) * 1.0
                    exit_fee = exit_price * fee_rate
                    balance += pnl - exit_fee
                    total_fee = position["entry_fee"] + exit_fee

                    recorder.record_trade(
                        side="exit",
                        direction="short",
                        entry=position["entry_price"],
                        exit=exit_price,
                        fee=total_fee,
                        pnl=pnl,
                        timestamp=ts,
                    )
                    position = None

            equity = self._compute_equity(balance, position, last_price)
            recorder.record_equity(equity)

        if position is not None and last_price is not None:
            ts = candles[-1]["timestamp"] if candles else None
            c = last_price

            if position["direction"] == "long":
                exit_price = c * (1 - slippage)
                pnl = (exit_price - position["entry_price"]) * 1.0
                exit_fee = exit_price * fee_rate
                balance += pnl - exit_fee
                total_fee = position["entry_fee"] + exit_fee

                recorder.record_trade(
                    side="exit",
                    direction="long",
                    entry=position["entry_price"],
                    exit=exit_price,
                    fee=total_fee,
                    pnl=pnl,
                    timestamp=ts,
                )

            elif position["direction"] == "short":
                exit_price = c * (1 + slippage)
                pnl = (position["entry_price"] - exit_price) * 1.0
                exit_fee = exit_price * fee_rate
                balance += pnl - exit_fee
                total_fee = position["entry_fee"] + exit_fee

                recorder.record_trade(
                    side="exit",
                    direction="short",
                    entry=position["entry_price"],
                    exit=exit_price,
                    fee=total_fee,
                    pnl=pnl,
                    timestamp=ts,
                )

            equity = self._compute_equity(balance, None, c)
            recorder.record_equity(equity)

        metrics = BacktestMetricsCalculator()
        metrics.compute(recorder.trades, recorder.equity_curve, initial_balance)
        summary = metrics.summary()

        return {
            "final_balance": float(balance),
            "trades": recorder.trades,
            "equity_curve": recorder.equity_curve,
            "metrics": summary,
        }
