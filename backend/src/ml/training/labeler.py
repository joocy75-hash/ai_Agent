"""
Labeler - 학습용 라벨 생성

5개 모델을 위한 라벨:
1. Direction: 방향 (0=하락, 1=횡보, 2=상승)
2. Volatility: 변동성 레벨 (0=low, 1=normal, 2=high, 3=extreme)
3. Timing: 진입 타이밍 (0=bad, 1=ok, 2=good)
4. StopLoss: 최적 SL 비율 (regression)
5. PositionSize: 최적 사이즈 비율 (regression)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class Labeler:
    """
    학습용 라벨 생성기

    Usage:
    ```python
    labeler = Labeler()
    df_labeled = labeler.generate_all_labels(df_features)
    ```
    """

    def __init__(
        self,
        direction_threshold: float = 0.005,  # 0.5% 이상 변화 = 방향 있음
        volatility_percentiles: Tuple[float, ...] = (25, 75, 95),
        lookahead_candles: int = 6,  # 30분 (5분봉 기준)
    ):
        self.direction_threshold = direction_threshold
        self.volatility_percentiles = volatility_percentiles
        self.lookahead_candles = lookahead_candles

        logger.info(f"Labeler initialized (lookahead: {lookahead_candles} candles)")

    def generate_all_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        모든 라벨 생성

        Args:
            df: 피처가 포함된 DataFrame (close, high, low, atr_14 필요)

        Returns:
            라벨이 추가된 DataFrame
        """
        result = df.copy()

        # 1. Direction 라벨
        result = self._label_direction(result)

        # 2. Volatility 라벨
        result = self._label_volatility(result)

        # 3. Timing 라벨
        result = self._label_timing(result)

        # 4. StopLoss 라벨 (regression)
        result = self._label_stop_loss(result)

        # 5. PositionSize 라벨 (regression)
        result = self._label_position_size(result)

        # 라벨 없는 행 제거 (lookahead 때문에 마지막 N개)
        result = result.dropna(subset=['label_direction'])

        logger.info(f"Generated labels for {len(result)} samples")

        return result

    def _label_direction(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Direction 라벨 생성

        미래 N캔들 후 가격 변화율 기준:
        - 0 (down): < -threshold
        - 1 (neutral): -threshold ~ +threshold
        - 2 (up): > +threshold
        """
        close = df['close']

        # 미래 가격
        future_close = close.shift(-self.lookahead_candles)

        # 변화율
        pct_change = (future_close - close) / close

        # 라벨링
        df['label_direction'] = np.where(
            pct_change > self.direction_threshold, 2,  # up
            np.where(pct_change < -self.direction_threshold, 0, 1)  # down or neutral
        )

        # 실제 변화율도 저장 (분석용)
        df['future_return'] = pct_change

        return df

    def _label_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Volatility 라벨 생성

        ATR 기반 변동성 분류:
        - 0 (low): < 25th percentile
        - 1 (normal): 25th ~ 75th percentile
        - 2 (high): 75th ~ 95th percentile
        - 3 (extreme): > 95th percentile
        """
        if 'atr_14' not in df.columns:
            # ATR이 없으면 직접 계산
            tr = pd.concat([
                df['high'] - df['low'],
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
        else:
            atr = df['atr_14']

        # ATR을 가격으로 정규화
        atr_pct = atr / df['close'] * 100

        # 백분위 계산
        p25, p75, p95 = np.nanpercentile(atr_pct, self.volatility_percentiles)

        # 라벨링
        df['label_volatility'] = np.where(
            atr_pct > p95, 3,  # extreme
            np.where(
                atr_pct > p75, 2,  # high
                np.where(atr_pct > p25, 1, 0)  # normal or low
            )
        )

        df['atr_pct'] = atr_pct

        return df

    def _label_timing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Timing 라벨 생성

        미래 움직임의 효율성 기준:
        - 0 (bad): 반대로 움직이거나 손실
        - 1 (ok): 방향은 맞지만 비효율적
        - 2 (good): 방향 맞고 효율적
        """
        close = df['close']
        high = df['high']
        low = df['low']

        # 미래 N캔들 동안의 최고/최저
        future_high = high.shift(-1).rolling(self.lookahead_candles).max().shift(-self.lookahead_candles + 1)
        future_low = low.shift(-1).rolling(self.lookahead_candles).min().shift(-self.lookahead_candles + 1)

        # 상승/하락 가능성
        up_potential = (future_high - close) / close
        down_potential = (close - future_low) / close

        # 최종 방향
        future_close = close.shift(-self.lookahead_candles)
        final_direction = np.sign(future_close - close)

        # 효율성 (최대 가능 이익 대비 실현 비율)
        max_potential = np.maximum(up_potential, down_potential)
        actual_move = abs(future_close - close) / close
        efficiency = actual_move / (max_potential + 1e-10)

        # 라벨링
        # Good: 방향 맞고, 효율성 > 0.5
        # OK: 방향 맞지만 효율성 < 0.5
        # Bad: 방향 틀림
        is_direction_correct = (
            ((final_direction > 0) & (up_potential > down_potential)) |
            ((final_direction < 0) & (down_potential > up_potential))
        )

        df['label_timing'] = np.where(
            is_direction_correct & (efficiency > 0.5), 2,  # good
            np.where(is_direction_correct, 1, 0)  # ok or bad
        )

        df['timing_efficiency'] = efficiency

        return df

    def _label_stop_loss(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        StopLoss 라벨 생성 (Regression)

        미래 N캔들 동안 반대 방향 최대 움직임 기준
        """
        close = df['close']
        high = df['high']
        low = df['low']

        # 미래 최대 역방향 움직임
        future_high = high.shift(-1).rolling(self.lookahead_candles).max().shift(-self.lookahead_candles + 1)
        future_low = low.shift(-1).rolling(self.lookahead_candles).min().shift(-self.lookahead_candles + 1)

        # 최종 방향 결정
        future_close = close.shift(-self.lookahead_candles)
        is_up = future_close > close

        # SL 비율 계산
        # Long인 경우: 현재가 - 미래 최저가
        # Short인 경우: 미래 최고가 - 현재가
        sl_long = (close - future_low) / close * 100
        sl_short = (future_high - close) / close * 100

        df['label_stop_loss'] = np.where(is_up, sl_long, sl_short)

        # 합리적 범위로 클리핑 (0.5% ~ 5%)
        df['label_stop_loss'] = df['label_stop_loss'].clip(0.5, 5.0)

        return df

    def _label_position_size(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        PositionSize 라벨 생성 (Regression)

        변동성과 신호 강도 기반 최적 사이즈:
        - 변동성 낮음 + 신호 강함 → 큰 사이즈
        - 변동성 높음 + 신호 약함 → 작은 사이즈
        """
        # 변동성 역수 (정규화)
        if 'atr_pct' in df.columns:
            vol_score = 1 / (df['atr_pct'] + 0.1)
        elif 'atr_14' in df.columns:
            vol_score = 1 / (df['atr_14'] / df['close'] * 100 + 0.1)
        else:
            vol_score = 1.0

        vol_score_norm = (vol_score - vol_score.min()) / (vol_score.max() - vol_score.min() + 1e-10)

        # 신호 강도 (미래 수익률 기반)
        if 'future_return' in df.columns:
            signal_strength = abs(df['future_return'])
            signal_norm = (signal_strength - signal_strength.min()) / (signal_strength.max() - signal_strength.min() + 1e-10)
        else:
            signal_norm = 0.5

        # 최적 사이즈 (5% ~ 40% 범위)
        optimal_size = 5 + 35 * (0.5 * vol_score_norm + 0.5 * signal_norm)

        df['label_position_size'] = optimal_size.clip(5, 40)

        return df

    def get_label_stats(self, df: pd.DataFrame) -> Dict:
        """라벨 통계 반환"""
        stats = {}

        # Direction 분포
        if 'label_direction' in df.columns:
            direction_counts = df['label_direction'].value_counts().to_dict()
            stats['direction'] = {
                'down': direction_counts.get(0, 0),
                'neutral': direction_counts.get(1, 0),
                'up': direction_counts.get(2, 0),
            }

        # Volatility 분포
        if 'label_volatility' in df.columns:
            vol_counts = df['label_volatility'].value_counts().to_dict()
            stats['volatility'] = {
                'low': vol_counts.get(0, 0),
                'normal': vol_counts.get(1, 0),
                'high': vol_counts.get(2, 0),
                'extreme': vol_counts.get(3, 0),
            }

        # Timing 분포
        if 'label_timing' in df.columns:
            timing_counts = df['label_timing'].value_counts().to_dict()
            stats['timing'] = {
                'bad': timing_counts.get(0, 0),
                'ok': timing_counts.get(1, 0),
                'good': timing_counts.get(2, 0),
            }

        # StopLoss 통계
        if 'label_stop_loss' in df.columns:
            stats['stop_loss'] = {
                'mean': df['label_stop_loss'].mean(),
                'std': df['label_stop_loss'].std(),
                'min': df['label_stop_loss'].min(),
                'max': df['label_stop_loss'].max(),
            }

        # PositionSize 통계
        if 'label_position_size' in df.columns:
            stats['position_size'] = {
                'mean': df['label_position_size'].mean(),
                'std': df['label_position_size'].std(),
                'min': df['label_position_size'].min(),
                'max': df['label_position_size'].max(),
            }

        return stats
