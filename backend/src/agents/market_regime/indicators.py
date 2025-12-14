"""
Market Regime Indicators (시장 환경 지표 계산)

시장 환경을 판단하는 기술적 지표 계산
"""

import logging
from typing import List, Dict, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


class RegimeIndicators:
    """
    시장 환경 지표 계산기

    주요 지표:
    - ATR (Average True Range): 변동성 측정
    - ADX (Average Directional Index): 추세 강도 측정
    - Bollinger Bands: 변동성 및 지지/저항 레벨
    - EMA (Exponential Moving Average): 추세 방향
    """

    @staticmethod
    def calculate_atr(candles: List[dict], period: int = 14) -> float:
        """
        ATR (Average True Range) 계산

        Args:
            candles: 캔들 데이터 리스트
            period: ATR 기간

        Returns:
            ATR 값
        """
        if len(candles) < period + 1:
            return 0.0

        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)

        # 최근 period개의 TR 평균
        atr = np.mean(true_ranges[-period:])
        return float(atr)

    @staticmethod
    def calculate_adx(candles: List[dict], period: int = 14) -> float:
        """
        ADX (Average Directional Index) 계산

        Args:
            candles: 캔들 데이터 리스트
            period: ADX 기간

        Returns:
            ADX 값 (0~100, 25 이상이면 강한 추세)
        """
        if len(candles) < period + 1:
            return 0.0

        # +DM, -DM 계산
        plus_dm = []
        minus_dm = []

        for i in range(1, len(candles)):
            high_diff = candles[i]["high"] - candles[i - 1]["high"]
            low_diff = candles[i - 1]["low"] - candles[i]["low"]

            plus_dm.append(high_diff if high_diff > low_diff and high_diff > 0 else 0)
            minus_dm.append(low_diff if low_diff > high_diff and low_diff > 0 else 0)

        # ATR 계산
        atr_values = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            atr_values.append(tr)

        # +DI, -DI 계산 (smoothed)
        if len(atr_values) < period:
            return 0.0

        smoothed_plus_dm = np.mean(plus_dm[-period:])
        smoothed_minus_dm = np.mean(minus_dm[-period:])
        smoothed_atr = np.mean(atr_values[-period:])

        if smoothed_atr == 0:
            return 0.0

        plus_di = (smoothed_plus_dm / smoothed_atr) * 100
        minus_di = (smoothed_minus_dm / smoothed_atr) * 100

        # DX 계산
        if plus_di + minus_di == 0:
            return 0.0

        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100

        # ADX는 DX의 이동평균 (간단화: 여기서는 DX 값 사용)
        return float(dx)

    @staticmethod
    def calculate_bollinger_bands(
        candles: List[dict],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """
        Bollinger Bands 계산

        Args:
            candles: 캔들 데이터 리스트
            period: 이동평균 기간
            std_dev: 표준편차 배수

        Returns:
            (upper_band, middle_band, lower_band)
        """
        if len(candles) < period:
            last_close = candles[-1]["close"] if candles else 0
            return last_close, last_close, last_close

        closes = [c["close"] for c in candles[-period:]]
        middle = np.mean(closes)
        std = np.std(closes)

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return float(upper), float(middle), float(lower)

    @staticmethod
    def calculate_ema(candles: List[dict], period: int = 20) -> float:
        """
        EMA (Exponential Moving Average) 계산

        Args:
            candles: 캔들 데이터 리스트
            period: EMA 기간

        Returns:
            EMA 값
        """
        if len(candles) < period:
            return candles[-1]["close"] if candles else 0.0

        closes = [c["close"] for c in candles[-period:]]
        multiplier = 2 / (period + 1)

        ema = closes[0]
        for close in closes[1:]:
            ema = (close * multiplier) + (ema * (1 - multiplier))

        return float(ema)

    @staticmethod
    def detect_support_resistance(
        candles: List[dict],
        lookback: int = 50
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        지지선/저항선 탐지

        Args:
            candles: 캔들 데이터 리스트
            lookback: 탐지 기간

        Returns:
            (support_level, resistance_level)
        """
        if len(candles) < lookback:
            return None, None

        recent_candles = candles[-lookback:]

        # 최근 저점들
        lows = [c["low"] for c in recent_candles]
        # 최근 고점들
        highs = [c["high"] for c in recent_candles]

        # 지지선: 최근 저점들의 평균 (간단화)
        support = np.percentile(lows, 25)

        # 저항선: 최근 고점들의 평균 (간단화)
        resistance = np.percentile(highs, 75)

        return float(support), float(resistance)

    @staticmethod
    def calculate_average_volume(candles: List[dict], period: int = 20) -> float:
        """
        평균 거래량 계산

        Args:
            candles: 캔들 데이터 리스트
            period: 평균 기간

        Returns:
            평균 거래량
        """
        if len(candles) < period:
            return 0.0

        volumes = [c["volume"] for c in candles[-period:]]
        return float(np.mean(volumes))

    @staticmethod
    def calculate_bollinger_width(
        candles: List[dict],
        period: int = 20,
        std_dev: float = 2.0
    ) -> float:
        """
        볼린저밴드 폭 계산 (변동성 측정)

        Args:
            candles: 캔들 데이터 리스트
            period: 이동평균 기간
            std_dev: 표준편차 배수

        Returns:
            볼린저밴드 폭 (%)
        """
        if len(candles) < period:
            return 0.0

        upper, middle, lower = RegimeIndicators.calculate_bollinger_bands(
            candles, period, std_dev
        )

        # 볼린저밴드 폭 = (upper - lower) / middle * 100
        if middle == 0:
            return 0.0

        width_percent = (upper - lower) / middle * 100
        return float(width_percent)
