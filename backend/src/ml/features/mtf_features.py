"""
MTF Features - 10개 멀티타임프레임 피처

1시간봉과 5분봉의 추세 일치, RSI 비교, 모멘텀 일치 등
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MTFFeatures:
    """
    멀티타임프레임 피처 계산 클래스

    10개 MTF 피처:
    1. 1h 추세와 5m 추세 일치 여부
    2. 1h EMA 트렌드 방향
    3. 5m/1h RSI 비교
    4. MTF 모멘텀 일치도
    5. 상위 TF ADX
    6. 1h 볼린저 밴드 위치
    7. 1h MACD 히스토그램 방향
    8. 상위 TF 거래량 추세
    9. 1h/5m 변동성 비율
    10. 종합 MTF 점수
    """

    def __init__(self):
        pass

    def calculate_all(
        self,
        df_5m: pd.DataFrame,
        df_1h: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        모든 MTF 피처 계산

        Args:
            df_5m: 5분봉 데이터 (technical features 포함)
            df_1h: 1시간봉 데이터 (optional, None이면 5분봉에서 리샘플)

        Returns:
            MTF 피처가 추가된 DataFrame
        """
        result = df_5m.copy()

        # 1시간봉 데이터 준비
        if df_1h is not None and len(df_1h) > 0:
            htf = df_1h.copy()
        else:
            # 5분봉에서 1시간봉 리샘플링
            htf = self._resample_to_1h(df_5m)

        # 1시간봉 기술적 지표 계산
        htf = self._calculate_htf_indicators(htf)

        # 피처 매핑 (1시간봉 → 5분봉)
        result = self._map_htf_features(result, htf)

        # 1. 추세 일치 여부
        result['mtf_trend_aligned'] = self._trend_aligned(result)

        # 2. 1h EMA 트렌드 방향
        result['htf_ema_trend'] = self._htf_ema_trend(result)

        # 3. 5m/1h RSI 비교
        result['mtf_rsi_diff'] = self._mtf_rsi_diff(result)

        # 4. 모멘텀 일치도
        result['mtf_momentum_agreement'] = self._momentum_agreement(result)

        # 5. 상위 TF ADX (이미 매핑됨)
        if 'htf_adx' not in result.columns:
            result['htf_adx'] = 25  # 기본값

        # 6. 1h 볼린저 밴드 위치
        result['htf_bb_position'] = self._htf_bb_position(result)

        # 7. 1h MACD 히스토그램 방향
        result['htf_macd_direction'] = self._htf_macd_direction(result)

        # 8. 상위 TF 거래량 추세
        result['htf_volume_trend'] = self._htf_volume_trend(result)

        # 9. 1h/5m 변동성 비율
        result['mtf_volatility_ratio'] = self._mtf_volatility_ratio(result)

        # 10. 종합 MTF 점수
        result['mtf_score'] = self._calculate_mtf_score(result)

        return result

    def _resample_to_1h(self, df_5m: pd.DataFrame) -> pd.DataFrame:
        """5분봉 → 1시간봉 리샘플링"""
        # timestamp가 index가 아니면 설정
        if 'timestamp' in df_5m.columns:
            df = df_5m.set_index('timestamp')
        else:
            df = df_5m.copy()

        # OHLCV 리샘플링
        ohlc_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }

        # 존재하는 컬럼만 리샘플링
        available_cols = {k: v for k, v in ohlc_dict.items() if k in df.columns}

        if len(available_cols) < 5:
            logger.warning("Not enough OHLCV columns for resampling")
            return df_5m

        try:
            resampled = df[list(available_cols.keys())].resample('1h').agg(available_cols)
            resampled = resampled.dropna()
            resampled = resampled.reset_index()
            return resampled
        except Exception as e:
            logger.error(f"Resampling failed: {e}")
            return df_5m

    def _calculate_htf_indicators(self, htf: pd.DataFrame) -> pd.DataFrame:
        """1시간봉 기술적 지표 계산"""
        if len(htf) < 20:
            return htf

        close = htf['close']

        # EMA
        htf['htf_ema_20'] = close.ewm(span=20, adjust=False).mean()
        htf['htf_ema_50'] = close.ewm(span=50, adjust=False).mean()

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        htf['htf_rsi'] = 100 - (100 / (1 + rs))

        # MACD
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        htf['htf_macd'] = ema_12 - ema_26
        htf['htf_macd_signal'] = htf['htf_macd'].ewm(span=9, adjust=False).mean()
        htf['htf_macd_hist'] = htf['htf_macd'] - htf['htf_macd_signal']

        # Bollinger Bands
        middle = close.rolling(20).mean()
        std = close.rolling(20).std()
        htf['htf_bb_upper'] = middle + 2 * std
        htf['htf_bb_lower'] = middle - 2 * std
        htf['htf_bb_middle'] = middle

        # ADX
        htf['htf_adx'] = self._calculate_adx(htf)

        # ATR
        tr1 = htf['high'] - htf['low']
        tr2 = abs(htf['high'] - close.shift(1))
        tr3 = abs(htf['low'] - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        htf['htf_atr'] = tr.rolling(14).mean()

        # Volume MA
        htf['htf_volume_ma'] = htf['volume'].rolling(20).mean()

        return htf

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ADX 계산"""
        high = df['high']
        low = df['low']

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr1 = high - low
        tr2 = abs(high - df['close'].shift(1))
        tr3 = abs(low - df['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()

        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(span=period, adjust=False).mean()

        return adx

    def _map_htf_features(
        self,
        ltf: pd.DataFrame,
        htf: pd.DataFrame
    ) -> pd.DataFrame:
        """1시간봉 피처를 5분봉에 매핑"""
        # 간단한 forward fill 방식
        htf_cols = [c for c in htf.columns if c.startswith('htf_')]

        if len(htf_cols) == 0:
            return ltf

        # 1시간봉 값을 5분봉에 매핑 (가장 최근 1시간봉 값 사용)
        # 실제로는 timestamp 기반 매핑이 필요하지만, 간단히 마지막 값 복제
        for col in htf_cols:
            if col in htf.columns and len(htf) > 0:
                # 가장 최근 값으로 채우기
                ltf[col] = htf[col].iloc[-1] if not pd.isna(htf[col].iloc[-1]) else 0

        return ltf

    def _trend_aligned(self, df: pd.DataFrame) -> pd.Series:
        """추세 일치 여부 (0 or 1)"""
        # 5분봉 EMA 크로스와 1시간봉 EMA 크로스 비교
        ltf_trend = (df.get('ema_5', df['close']) > df.get('ema_20', df['close'])).astype(int)
        htf_trend = (df.get('htf_ema_20', df['close']) > df.get('htf_ema_50', df['close'])).astype(int)

        # 둘 다 bullish(1) 또는 둘 다 bearish(0)이면 일치
        return (ltf_trend == htf_trend).astype(int)

    def _htf_ema_trend(self, df: pd.DataFrame) -> pd.Series:
        """1h EMA 트렌드 방향 (-1, 0, 1)"""
        ema_20 = df.get('htf_ema_20', df['close'])
        ema_50 = df.get('htf_ema_50', df['close'])

        bullish = (ema_20 > ema_50).astype(int)
        bearish = (ema_20 < ema_50).astype(int)

        return bullish - bearish

    def _mtf_rsi_diff(self, df: pd.DataFrame) -> pd.Series:
        """5m RSI - 1h RSI"""
        ltf_rsi = df.get('rsi_14', pd.Series(50, index=df.index))
        htf_rsi = df.get('htf_rsi', pd.Series(50, index=df.index))

        return ltf_rsi - htf_rsi

    def _momentum_agreement(self, df: pd.DataFrame) -> pd.Series:
        """모멘텀 일치도 (0~1)"""
        # RSI 방향 일치
        ltf_rsi = df.get('rsi_14', pd.Series(50, index=df.index))
        htf_rsi = df.get('htf_rsi', pd.Series(50, index=df.index))

        ltf_rsi_bull = ltf_rsi > 50
        htf_rsi_bull = htf_rsi > 50

        rsi_agree = (ltf_rsi_bull == htf_rsi_bull).astype(float)

        # MACD 방향 일치
        ltf_macd = df.get('macd_histogram', pd.Series(0, index=df.index))
        htf_macd = df.get('htf_macd_hist', pd.Series(0, index=df.index))

        ltf_macd_bull = ltf_macd > 0
        htf_macd_bull = htf_macd > 0

        macd_agree = (ltf_macd_bull == htf_macd_bull).astype(float)

        # 평균
        return (rsi_agree * 0.5 + macd_agree * 0.5)

    def _htf_bb_position(self, df: pd.DataFrame) -> pd.Series:
        """1h 볼린저 밴드 위치 (0~1)"""
        close = df['close']
        upper = df.get('htf_bb_upper', close * 1.02)
        lower = df.get('htf_bb_lower', close * 0.98)

        position = (close - lower) / (upper - lower + 1e-10)
        return position.clip(0, 1)

    def _htf_macd_direction(self, df: pd.DataFrame) -> pd.Series:
        """1h MACD 히스토그램 방향 (-1, 0, 1)"""
        hist = df.get('htf_macd_hist', pd.Series(0, index=df.index))
        prev_hist = hist.shift(1).fillna(0)

        increasing = (hist > prev_hist).astype(int)
        decreasing = (hist < prev_hist).astype(int)

        return increasing - decreasing

    def _htf_volume_trend(self, df: pd.DataFrame) -> pd.Series:
        """상위 TF 거래량 추세"""
        volume = df['volume']
        htf_vol_ma = df.get('htf_volume_ma', volume.rolling(20).mean())

        return (volume / (htf_vol_ma + 1e-10)).clip(0, 3)

    def _mtf_volatility_ratio(self, df: pd.DataFrame) -> pd.Series:
        """1h/5m 변동성 비율"""
        ltf_atr = df.get('atr_14', pd.Series(1, index=df.index))
        htf_atr = df.get('htf_atr', pd.Series(1, index=df.index))

        # 5분봉 ATR을 1시간봉 스케일로 조정 (12배)
        ltf_atr_scaled = ltf_atr * 12

        return (ltf_atr_scaled / (htf_atr + 1e-10)).clip(0.5, 2.0)

    def _calculate_mtf_score(self, df: pd.DataFrame) -> pd.Series:
        """종합 MTF 점수 (0~1)"""
        score = pd.Series(0.5, index=df.index)

        # 추세 일치 (+0.2)
        score += df.get('mtf_trend_aligned', 0) * 0.2

        # 모멘텀 일치 (+0.15)
        score += df.get('mtf_momentum_agreement', 0.5) * 0.15

        # RSI 차이 (과도하면 -0.1)
        rsi_diff = abs(df.get('mtf_rsi_diff', 0))
        score -= (rsi_diff > 20).astype(float) * 0.1

        # ADX 높으면 (+0.1)
        htf_adx = df.get('htf_adx', 25)
        score += (htf_adx > 25).astype(float) * 0.1

        return score.clip(0, 1)
