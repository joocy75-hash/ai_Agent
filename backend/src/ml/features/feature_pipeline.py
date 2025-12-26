"""
Feature Pipeline - 통합 피처 파이프라인

70개 피처 (50 기술적 + 10 구조 + 10 MTF) 추출
"""

import logging
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime

from .technical_features import TechnicalFeatures
from .structure_features import StructureFeatures
from .mtf_features import MTFFeatures

logger = logging.getLogger(__name__)


class FeaturePipeline:
    """
    통합 피처 파이프라인

    OHLCV 캔들 데이터 → 70개 피처 DataFrame

    사용법:
    ```python
    pipeline = FeaturePipeline()
    features_df = pipeline.extract_features(candles_5m, candles_1h)
    ```
    """

    def __init__(self):
        self.technical = TechnicalFeatures()
        self.structure = StructureFeatures()
        self.mtf = MTFFeatures()

        # 피처 캐시 (심볼별)
        self._cache: Dict[str, tuple] = {}  # {symbol: (features, timestamp)}
        self._cache_ttl = 5.0  # 초

        logger.info("FeaturePipeline initialized")

    def extract_features(
        self,
        candles_5m: List[dict],
        candles_1h: Optional[List[dict]] = None,
        symbol: str = "ETHUSDT"
    ) -> pd.DataFrame:
        """
        피처 추출

        Args:
            candles_5m: 5분봉 캔들 데이터 (최소 100개 권장)
            candles_1h: 1시간봉 캔들 데이터 (optional)
            symbol: 심볼 (캐시 키)

        Returns:
            70개 피처가 포함된 DataFrame
        """
        # 캐시 확인
        cached = self._get_cached(symbol)
        if cached is not None:
            logger.debug(f"Using cached features for {symbol}")
            return cached

        try:
            # 1. DataFrame 변환
            df_5m = self._to_dataframe(candles_5m)

            if df_5m is None or len(df_5m) < 50:
                logger.warning(f"Insufficient data: {len(candles_5m) if candles_5m else 0} candles")
                return self._empty_features()

            df_1h = self._to_dataframe(candles_1h) if candles_1h else None

            # 2. 기술적 피처 (50개)
            df_5m = self.technical.calculate_all(df_5m)

            # 3. 구조 피처 (10개)
            df_5m = self.structure.calculate_all(df_5m)

            # 4. MTF 피처 (10개)
            df_5m = self.mtf.calculate_all(df_5m, df_1h)

            # 5. NaN 처리
            df_5m = self._handle_nan(df_5m)

            # 6. 캐시 저장
            self._set_cache(symbol, df_5m)

            logger.info(f"Extracted {len(df_5m.columns)} features for {symbol}")
            return df_5m

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}", exc_info=True)
            return self._empty_features()

    def extract_latest_features(
        self,
        candles_5m: List[dict],
        candles_1h: Optional[List[dict]] = None,
        symbol: str = "ETHUSDT"
    ) -> Dict[str, float]:
        """
        최신 캔들의 피처만 추출 (예측용)

        Returns:
            {feature_name: value} 딕셔너리
        """
        df = self.extract_features(candles_5m, candles_1h, symbol)

        if df.empty:
            return {}

        # 마지막 행 (최신)
        latest = df.iloc[-1]
        return latest.to_dict()

    def get_feature_names(self) -> List[str]:
        """피처 이름 목록 반환"""
        # 모든 피처 이름
        return [
            # EMA (6)
            'ema_5', 'ema_10', 'ema_20', 'ema_50', 'ema_100', 'ema_200',
            # RSI (3)
            'rsi_7', 'rsi_14', 'rsi_21',
            # MACD (3)
            'macd', 'macd_signal', 'macd_histogram',
            # Bollinger (4)
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
            # ATR (2)
            'atr_14', 'atr_21',
            # ADX (3)
            'adx', 'plus_di', 'minus_di',
            # Stochastic (2)
            'stoch_k', 'stoch_d',
            # CCI (2)
            'cci_14', 'cci_20',
            # Williams %R (1)
            'williams_r',
            # Volume (5)
            'obv', 'vwap', 'volume_ma_ratio', 'volume_delta', 'volume_trend',
            # Price Pattern (10)
            'higher_high', 'lower_low', 'consecutive_up', 'consecutive_down',
            'pct_change_1', 'pct_change_5', 'pct_change_10',
            'body_ratio', 'upper_wick_ratio', 'lower_wick_ratio',
            # Additional (9)
            'ema_cross_5_20', 'ema_cross_10_50',
            'price_vs_ema_20', 'price_vs_ema_50',
            'bb_position', 'atr_ratio', 'momentum_10',
            'trend_strength', 'volatility_norm',
            # Structure (10)
            'dist_to_support', 'dist_to_resistance',
            'swing_high_count', 'swing_low_count',
            'price_position_ema', 'trend_quality',
            'structural_bias', 'near_key_level',
            'breakout_probability', 'consolidation',
            # MTF (10)
            'mtf_trend_aligned', 'htf_ema_trend',
            'mtf_rsi_diff', 'mtf_momentum_agreement',
            'htf_adx', 'htf_bb_position',
            'htf_macd_direction', 'htf_volume_trend',
            'mtf_volatility_ratio', 'mtf_score',
        ]

    def _to_dataframe(self, candles: Optional[List[dict]]) -> Optional[pd.DataFrame]:
        """캔들 리스트 → DataFrame 변환"""
        if not candles or len(candles) == 0:
            return None

        df = pd.DataFrame(candles)

        # 컬럼 정규화
        column_mapping = {
            'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume',
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
        }

        df = df.rename(columns=column_mapping)

        # 필수 컬럼 확인
        required = ['open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                logger.warning(f"Missing column: {col}")
                return None

        # 숫자 변환
        for col in required:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # timestamp 처리
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
            df = df.set_index('timestamp')

        return df

    def _handle_nan(self, df: pd.DataFrame) -> pd.DataFrame:
        """NaN 값 처리"""
        # Forward fill → Backward fill → 0
        df = df.ffill().bfill().fillna(0)

        # 무한대 → 0
        df = df.replace([np.inf, -np.inf], 0)

        return df

    def _empty_features(self) -> pd.DataFrame:
        """빈 피처 DataFrame 반환"""
        return pd.DataFrame()

    def _get_cached(self, symbol: str) -> Optional[pd.DataFrame]:
        """캐시에서 피처 조회"""
        if symbol in self._cache:
            features, timestamp = self._cache[symbol]
            age = (datetime.utcnow() - timestamp).total_seconds()
            if age < self._cache_ttl:
                return features
            else:
                del self._cache[symbol]
        return None

    def _set_cache(self, symbol: str, features: pd.DataFrame):
        """캐시에 피처 저장"""
        self._cache[symbol] = (features, datetime.utcnow())

        # 캐시 크기 제한
        if len(self._cache) > 10:
            oldest = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest]

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        logger.info("Feature cache cleared")
