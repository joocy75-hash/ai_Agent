"""
Market Regime Models (시장 환경 데이터 모델)

시장 환경 분석 결과를 저장하는 데이터 모델
"""

from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class RegimeType(str, Enum):
    """시장 환경 타입"""
    TRENDING_UP = "trending_up"  # 상승 추세
    TRENDING_DOWN = "trending_down"  # 하락 추세
    RANGING = "ranging"  # 횡보장
    VOLATILE = "volatile"  # 고변동성
    LOW_VOLUME = "low_volume"  # 저거래량
    HIGH_VOLATILITY = "high_volatility"  # 고변동성 (deprecated, use VOLATILE)
    LOW_VOLATILITY = "low_volatility"  # 저변동성 (deprecated)
    UNKNOWN = "unknown"  # 불명확


@dataclass
class MarketRegime:
    """
    시장 환경 분석 결과

    Attributes:
        symbol: 심볼 (예: BTCUSDT)
        regime_type: 시장 환경 타입
        confidence: 신뢰도 (0.0 ~ 1.0)
        volatility: 변동성 (ATR 기반)
        trend_strength: 추세 강도 (ADX 기반)
        support_level: 지지선
        resistance_level: 저항선
        timestamp: 분석 시각
    """
    symbol: str
    regime_type: RegimeType
    confidence: float
    volatility: float
    trend_strength: float
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "symbol": self.symbol,
            "regime_type": self.regime_type.value,
            "confidence": self.confidence,
            "volatility": self.volatility,
            "trend_strength": self.trend_strength,
            "support_level": self.support_level,
            "resistance_level": self.resistance_level,
            "timestamp": self.timestamp.isoformat(),
        }

    def is_trending(self) -> bool:
        """추세장인지 확인"""
        return self.regime_type in {
            RegimeType.TRENDING_UP,
            RegimeType.TRENDING_DOWN
        }

    def is_ranging(self) -> bool:
        """횡보장인지 확인"""
        return self.regime_type == RegimeType.RANGING
