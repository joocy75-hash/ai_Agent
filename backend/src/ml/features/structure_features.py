"""
Structure Features - 10개 시장 구조 피처

지지/저항선, 스윙 고점/저점, 추세 품질 등
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Tuple

logger = logging.getLogger(__name__)


class StructureFeatures:
    """
    시장 구조 피처 계산 클래스

    10개 시장 구조 피처:
    1. 가장 가까운 지지선 거리
    2. 가장 가까운 저항선 거리
    3. 최근 스윙 하이 수
    4. 최근 스윙 로우 수
    5. EMA 대비 가격 위치
    6. 추세 품질 점수
    7. 구조적 편향 (bullish/bearish)
    8. 가격 레벨 (주요 레벨 근처 여부)
    9. 브레이크아웃 확률
    10. 컨솔리데이션 지표
    """

    def __init__(self, lookback_period: int = 50):
        self.lookback_period = lookback_period

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """모든 구조 피처 계산"""
        result = df.copy()

        # 스윙 포인트 감지
        swing_highs, swing_lows = self._detect_swing_points(result)

        # 1-2. 지지/저항선 거리
        result['dist_to_support'] = self._distance_to_support(result, swing_lows)
        result['dist_to_resistance'] = self._distance_to_resistance(result, swing_highs)

        # 3-4. 스윙 포인트 수
        result['swing_high_count'] = swing_highs.rolling(self.lookback_period).sum()
        result['swing_low_count'] = swing_lows.rolling(self.lookback_period).sum()

        # 5. EMA 대비 가격 위치 (이미 technical에서 계산됨)
        if 'ema_50' in result.columns:
            result['price_position_ema'] = (result['close'] - result['ema_50']) / result['ema_50'] * 100
        else:
            ema_50 = result['close'].ewm(span=50, adjust=False).mean()
            result['price_position_ema'] = (result['close'] - ema_50) / ema_50 * 100

        # 6. 추세 품질 점수
        result['trend_quality'] = self._calculate_trend_quality(result)

        # 7. 구조적 편향
        result['structural_bias'] = self._calculate_structural_bias(result, swing_highs, swing_lows)

        # 8. 주요 가격 레벨
        result['near_key_level'] = self._near_key_level(result)

        # 9. 브레이크아웃 확률
        result['breakout_probability'] = self._breakout_probability(result)

        # 10. 컨솔리데이션 지표
        result['consolidation'] = self._consolidation_indicator(result)

        return result

    def _detect_swing_points(
        self,
        df: pd.DataFrame,
        left: int = 3,
        right: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """스윙 고점/저점 감지"""
        highs = df['high'].values
        lows = df['low'].values
        n = len(highs)

        swing_highs = np.zeros(n, dtype=bool)
        swing_lows = np.zeros(n, dtype=bool)

        for i in range(left, n - right):
            # 스윙 하이: 좌우 모두보다 높으면
            if all(highs[i] >= highs[i-left:i]) and all(highs[i] >= highs[i+1:i+right+1]):
                swing_highs[i] = True

            # 스윙 로우: 좌우 모두보다 낮으면
            if all(lows[i] <= lows[i-left:i]) and all(lows[i] <= lows[i+1:i+right+1]):
                swing_lows[i] = True

        return pd.Series(swing_highs, index=df.index), pd.Series(swing_lows, index=df.index)

    def _distance_to_support(
        self,
        df: pd.DataFrame,
        swing_lows: pd.Series
    ) -> pd.Series:
        """가장 가까운 지지선까지 거리 (%)"""
        result = []

        for i in range(len(df)):
            current_price = df['close'].iloc[i]

            # 현재 위치 이전의 스윙 로우 찾기
            past_swing_lows = df['low'].iloc[:i+1][swing_lows.iloc[:i+1]]

            if len(past_swing_lows) == 0:
                result.append(0)
                continue

            # 현재 가격보다 낮은 스윙 로우 중 가장 가까운 것
            below_price = past_swing_lows[past_swing_lows < current_price]

            if len(below_price) > 0:
                nearest_support = below_price.iloc[-1]  # 가장 최근
                distance = (current_price - nearest_support) / current_price * 100
            else:
                distance = 0

            result.append(distance)

        return pd.Series(result, index=df.index)

    def _distance_to_resistance(
        self,
        df: pd.DataFrame,
        swing_highs: pd.Series
    ) -> pd.Series:
        """가장 가까운 저항선까지 거리 (%)"""
        result = []

        for i in range(len(df)):
            current_price = df['close'].iloc[i]

            # 현재 위치 이전의 스윙 하이 찾기
            past_swing_highs = df['high'].iloc[:i+1][swing_highs.iloc[:i+1]]

            if len(past_swing_highs) == 0:
                result.append(0)
                continue

            # 현재 가격보다 높은 스윙 하이 중 가장 가까운 것
            above_price = past_swing_highs[past_swing_highs > current_price]

            if len(above_price) > 0:
                nearest_resistance = above_price.iloc[-1]  # 가장 최근
                distance = (nearest_resistance - current_price) / current_price * 100
            else:
                distance = 0

            result.append(distance)

        return pd.Series(result, index=df.index)

    def _calculate_trend_quality(self, df: pd.DataFrame) -> pd.Series:
        """추세 품질 점수 (0~1)"""
        # R² 기반 추세 품질 (선형 회귀)
        result = []
        window = 20

        for i in range(len(df)):
            if i < window:
                result.append(0.5)
                continue

            y = df['close'].iloc[i-window+1:i+1].values
            x = np.arange(window)

            # 선형 회귀
            slope, intercept = np.polyfit(x, y, 1)
            y_pred = slope * x + intercept

            # R² 계산
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)

            r_squared = 1 - (ss_res / (ss_tot + 1e-10)) if ss_tot > 0 else 0
            result.append(max(0, min(1, r_squared)))

        return pd.Series(result, index=df.index)

    def _calculate_structural_bias(
        self,
        df: pd.DataFrame,
        swing_highs: pd.Series,
        swing_lows: pd.Series
    ) -> pd.Series:
        """구조적 편향 (-1: bearish, 0: neutral, 1: bullish)"""
        result = []
        window = 20

        for i in range(len(df)):
            if i < window:
                result.append(0)
                continue

            # 최근 스윙 포인트들 분석
            recent_sh = swing_highs.iloc[i-window+1:i+1]
            recent_sl = swing_lows.iloc[i-window+1:i+1]

            # Higher highs and higher lows = bullish
            recent_highs = df['high'].iloc[i-window+1:i+1][recent_sh]
            recent_lows = df['low'].iloc[i-window+1:i+1][recent_sl]

            if len(recent_highs) >= 2 and len(recent_lows) >= 2:
                hh = recent_highs.iloc[-1] > recent_highs.iloc[-2] if len(recent_highs) >= 2 else False
                hl = recent_lows.iloc[-1] > recent_lows.iloc[-2] if len(recent_lows) >= 2 else False
                ll = recent_lows.iloc[-1] < recent_lows.iloc[-2] if len(recent_lows) >= 2 else False
                lh = recent_highs.iloc[-1] < recent_highs.iloc[-2] if len(recent_highs) >= 2 else False

                if hh and hl:
                    bias = 1  # Bullish
                elif ll and lh:
                    bias = -1  # Bearish
                else:
                    bias = 0  # Neutral
            else:
                bias = 0

            result.append(bias)

        return pd.Series(result, index=df.index)

    def _near_key_level(self, df: pd.DataFrame, threshold: float = 0.005) -> pd.Series:
        """주요 가격 레벨 근처 여부 (0 or 1)"""
        close = df['close']

        # 라운드 넘버 (100, 1000 단위)
        round_100 = (close / 100).round() * 100
        round_1000 = (close / 1000).round() * 1000

        # 거리 계산
        dist_100 = abs(close - round_100) / close
        dist_1000 = abs(close - round_1000) / close

        # threshold 이내면 1
        near_100 = (dist_100 < threshold).astype(int)
        near_1000 = (dist_1000 < threshold).astype(int)

        return near_100 | near_1000

    def _breakout_probability(self, df: pd.DataFrame) -> pd.Series:
        """브레이크아웃 확률 (0~1)"""
        # 볼린저 밴드 폭 + 거래량 증가 기반
        close = df['close']

        # BB 폭 수축 (좁을수록 브레이크아웃 가능성 높음)
        bb_width = df.get('bb_width', close.rolling(20).std() / close.rolling(20).mean())
        bb_percentile = bb_width.rolling(50).rank(pct=True)

        # 거래량 증가
        vol_ratio = df['volume'] / df['volume'].rolling(20).mean()

        # 조합
        prob = (1 - bb_percentile) * 0.6 + (vol_ratio.clip(0, 2) / 2) * 0.4

        return prob.clip(0, 1)

    def _consolidation_indicator(self, df: pd.DataFrame) -> pd.Series:
        """컨솔리데이션 지표 (0~1, 1이면 강한 횡보)"""
        # ATR 감소 + ADX 낮음
        atr = df.get('atr_14', self._calculate_atr(df, 14))
        atr_ratio = atr / atr.rolling(50).mean()

        adx = df.get('adx', pd.Series(25, index=df.index))

        # ATR 낮고 ADX 낮으면 컨솔리데이션
        consolidation = ((1 - atr_ratio.clip(0, 2) / 2) * 0.5 +
                        (1 - adx.clip(0, 50) / 50) * 0.5)

        return consolidation.clip(0, 1)

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR 계산 (내부용)"""
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift(1))
        tr3 = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
