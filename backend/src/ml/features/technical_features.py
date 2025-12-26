"""
Technical Features - 50개 기술적 지표

EMA, RSI, MACD, Bollinger Bands, ATR, ADX, Stochastic, CCI,
Williams %R, Volume 지표, Price Pattern 등
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Optional

logger = logging.getLogger(__name__)


class TechnicalFeatures:
    """
    기술적 피처 계산 클래스

    50개 기술적 지표:
    - EMA: 6개 (5, 10, 20, 50, 100, 200)
    - RSI: 3개 (7, 14, 21)
    - MACD: 3개 (macd, signal, histogram)
    - Bollinger: 4개 (upper, middle, lower, width)
    - ATR: 2개 (14, 21)
    - ADX: 3개 (adx, +di, -di)
    - Stochastic: 2개 (%K, %D)
    - CCI: 2개 (14, 20)
    - Williams %R: 1개
    - Volume: 5개 (OBV, VWAP, volume_ma_ratio, volume_delta, volume_trend)
    - Price Pattern: 10개+ (higher_high, lower_low 등)
    - 기타: 9개+
    """

    def __init__(
        self,
        ema_periods: List[int] = None,
        rsi_periods: List[int] = None,
        atr_period: int = 14,
        adx_period: int = 14,
    ):
        self.ema_periods = ema_periods or [5, 10, 20, 50, 100, 200]
        self.rsi_periods = rsi_periods or [7, 14, 21]
        self.atr_period = atr_period
        self.adx_period = adx_period

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """모든 기술적 피처 계산"""
        result = df.copy()

        # 필수 컬럼 확인
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in result.columns:
                raise ValueError(f"Missing required column: {col}")

        # EMA (6개)
        for period in self.ema_periods:
            result[f'ema_{period}'] = self._ema(result['close'], period)

        # RSI (3개)
        for period in self.rsi_periods:
            result[f'rsi_{period}'] = self._rsi(result['close'], period)

        # MACD (3개)
        macd, signal, hist = self._macd(result['close'])
        result['macd'] = macd
        result['macd_signal'] = signal
        result['macd_histogram'] = hist

        # Bollinger Bands (4개)
        upper, middle, lower = self._bollinger_bands(result['close'])
        result['bb_upper'] = upper
        result['bb_middle'] = middle
        result['bb_lower'] = lower
        result['bb_width'] = (upper - lower) / middle

        # ATR (2개)
        result['atr_14'] = self._atr(result, 14)
        result['atr_21'] = self._atr(result, 21)

        # ADX (3개)
        adx, plus_di, minus_di = self._adx(result, self.adx_period)
        result['adx'] = adx
        result['plus_di'] = plus_di
        result['minus_di'] = minus_di

        # Stochastic (2개)
        k, d = self._stochastic(result)
        result['stoch_k'] = k
        result['stoch_d'] = d

        # CCI (2개)
        result['cci_14'] = self._cci(result, 14)
        result['cci_20'] = self._cci(result, 20)

        # Williams %R (1개)
        result['williams_r'] = self._williams_r(result)

        # Volume 지표 (5개)
        result['obv'] = self._obv(result)
        result['vwap'] = self._vwap(result)
        result['volume_ma_ratio'] = result['volume'] / result['volume'].rolling(20).mean()
        result['volume_delta'] = result['volume'].diff()
        result['volume_trend'] = result['volume'].rolling(5).mean() / result['volume'].rolling(20).mean()

        # Price Pattern (10개)
        result = self._add_price_patterns(result)

        # 추가 피처 (9개)
        result = self._add_additional_features(result)

        return result

    def _ema(self, series: pd.Series, period: int) -> pd.Series:
        """지수이동평균"""
        return series.ewm(span=period, adjust=False).mean()

    def _rsi(self, series: pd.Series, period: int) -> pd.Series:
        """상대강도지수"""
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    def _macd(
        self,
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple:
        """MACD"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram

    def _bollinger_bands(
        self,
        series: pd.Series,
        period: int = 20,
        std: float = 2.0
    ) -> tuple:
        """볼린저 밴드"""
        middle = series.rolling(window=period).mean()
        std_dev = series.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower

    def _atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR (Average True Range)"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def _adx(self, df: pd.DataFrame, period: int = 14) -> tuple:
        """ADX (Average Directional Index)"""
        high = df['high']
        low = df['low']
        close = df['close']

        # +DM, -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        # ATR
        tr = self._atr(df, period)

        # +DI, -DI
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / tr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / tr)

        # DX, ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(span=period, adjust=False).mean()

        return adx, plus_di, minus_di

    def _stochastic(
        self,
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> tuple:
        """Stochastic Oscillator"""
        lowest_low = df['low'].rolling(window=k_period).min()
        highest_high = df['high'].rolling(window=k_period).max()

        k = 100 * (df['close'] - lowest_low) / (highest_high - lowest_low + 1e-10)
        d = k.rolling(window=d_period).mean()

        return k, d

    def _cci(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Commodity Channel Index"""
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
        return (tp - sma) / (0.015 * mad + 1e-10)

    def _williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Williams %R"""
        highest_high = df['high'].rolling(window=period).max()
        lowest_low = df['low'].rolling(window=period).min()
        return -100 * (highest_high - df['close']) / (highest_high - lowest_low + 1e-10)

    def _obv(self, df: pd.DataFrame) -> pd.Series:
        """On Balance Volume"""
        obv = np.where(
            df['close'] > df['close'].shift(1),
            df['volume'],
            np.where(df['close'] < df['close'].shift(1), -df['volume'], 0)
        )
        return pd.Series(obv, index=df.index).cumsum()

    def _vwap(self, df: pd.DataFrame) -> pd.Series:
        """Volume Weighted Average Price (일일 리셋 없는 버전)"""
        tp = (df['high'] + df['low'] + df['close']) / 3
        return (tp * df['volume']).cumsum() / df['volume'].cumsum()

    def _add_price_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Price Pattern 피처 추가 (10개)"""
        close = df['close']
        high = df['high']
        low = df['low']

        # Higher High, Lower Low (최근 5개 캔들 기준)
        df['higher_high'] = (high > high.shift(1)).astype(int).rolling(5).sum()
        df['lower_low'] = (low < low.shift(1)).astype(int).rolling(5).sum()

        # 연속 상승/하락
        df['consecutive_up'] = (close > close.shift(1)).astype(int).rolling(5).sum()
        df['consecutive_down'] = (close < close.shift(1)).astype(int).rolling(5).sum()

        # 가격 변동률
        df['pct_change_1'] = close.pct_change(1)
        df['pct_change_5'] = close.pct_change(5)
        df['pct_change_10'] = close.pct_change(10)

        # 캔들 바디/위꼬리/아래꼬리
        body = abs(close - df['open'])
        upper_wick = high - df[['close', 'open']].max(axis=1)
        lower_wick = df[['close', 'open']].min(axis=1) - low

        df['body_ratio'] = body / (high - low + 1e-10)
        df['upper_wick_ratio'] = upper_wick / (high - low + 1e-10)
        df['lower_wick_ratio'] = lower_wick / (high - low + 1e-10)

        return df

    def _add_additional_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """추가 피처 (9개)"""
        close = df['close']

        # EMA 크로스
        df['ema_cross_5_20'] = (df['ema_5'] > df['ema_20']).astype(int)
        df['ema_cross_10_50'] = (df['ema_10'] > df['ema_50']).astype(int)

        # 가격 위치 (EMA 대비)
        df['price_vs_ema_20'] = (close - df['ema_20']) / df['ema_20'] * 100
        df['price_vs_ema_50'] = (close - df['ema_50']) / df['ema_50'] * 100

        # 볼린저 밴드 위치 (0~1)
        df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10)

        # ATR 비율 (현재 vs 평균)
        df['atr_ratio'] = df['atr_14'] / df['atr_14'].rolling(20).mean()

        # 모멘텀
        df['momentum_10'] = close / close.shift(10) - 1

        # 추세 강도 (ADX 기반)
        df['trend_strength'] = df['adx'] / 100

        # 변동성 정규화
        df['volatility_norm'] = df['atr_14'] / close * 100

        return df
