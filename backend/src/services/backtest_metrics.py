import math


class BacktestMetricsCalculator:
    """
    백테스트 메트릭 계산기 (확장 버전)

    계산 항목:
    - total_return: 총 수익률 (%)
    - max_drawdown: 최대 손실 (%)
    - win_rate: 승률 (%)
    - total_trades: 총 거래 수
    - profit_factor: 수익 비율 (총 이익 / 총 손실)
    - sharpe_ratio: 샤프 비율 (위험 조정 수익률)
    - avg_win: 평균 수익
    - avg_loss: 평균 손실
    """

    def __init__(self):
        self._metrics = {}

    def compute(self, trades, equity_curve, initial_balance: float):
        """메트릭 계산"""

        # === 1. 총 수익률 ===
        if equity_curve and len(equity_curve) > 0:
            final_equity = equity_curve[-1]
            total_return = ((final_equity - initial_balance) / initial_balance) * 100
        else:
            total_return = 0.0

        # === 2. 최대 손실 (MDD) ===
        max_equity = initial_balance
        max_drawdown = 0.0
        for value in equity_curve:
            if value > max_equity:
                max_equity = value
            if max_equity > 0:
                drawdown = ((max_equity - value) / max_equity) * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        # === 3. 승률 및 거래 통계 ===
        wins = 0
        losses = 0
        total_profit = 0.0
        total_loss = 0.0
        pnl_list = []

        for trade in trades:
            pnl = trade.get("pnl", 0.0)
            pnl_list.append(pnl)

            if pnl > 0:
                wins += 1
                total_profit += pnl
            elif pnl < 0:
                losses += 1
                total_loss += abs(pnl)

        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

        # === 4. Profit Factor (수익 비율) ===
        if total_loss > 0:
            profit_factor = total_profit / total_loss
        else:
            profit_factor = total_profit if total_profit > 0 else 0.0

        # === 5. 평균 수익/손실 ===
        avg_win = (total_profit / wins) if wins > 0 else 0.0
        avg_loss = (total_loss / losses) if losses > 0 else 0.0

        # === 6. 샤프 비율 (연간화) ===
        sharpe_ratio = 0.0
        if len(pnl_list) > 1:
            mean_pnl = sum(pnl_list) / len(pnl_list)
            variance = sum((x - mean_pnl) ** 2 for x in pnl_list) / len(pnl_list)
            std_pnl = (
                math.sqrt(variance) if variance > 0 else 0.001
            )  # 0으로 나누기 방지

            # 연간화 (거래 횟수 기준)
            if std_pnl > 0:
                sharpe_ratio = (mean_pnl / std_pnl) * math.sqrt(len(pnl_list))

        # === 결과 저장 ===
        self._metrics = {
            # 필수 메트릭
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "win_rate": round(win_rate, 2),
            "total_trades": total_trades,  # 키 이름 수정!
            "number_of_trades": total_trades,  # 호환성 유지
            # 확장 메트릭
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "total_profit": round(total_profit, 2),
            "total_loss": round(total_loss, 2),
            "wins": wins,
            "losses": losses,
        }

    def summary(self):
        """메트릭 요약 반환"""
        return self._metrics
