"""
Sentiment Analyzer Agent - Data Models

감성 분석 에이전트에서 사용하는 데이터 모델 정의
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class SentimentLabel(str, Enum):
    """감성 라벨"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SentimentStrength(str, Enum):
    """감성 강도"""
    EXTREME_POSITIVE = "extreme_positive"   # 0.8 ~ 1.0
    STRONG_POSITIVE = "strong_positive"     # 0.6 ~ 0.8
    MODERATE_POSITIVE = "moderate_positive" # 0.4 ~ 0.6
    NEUTRAL = "neutral"                     # -0.4 ~ 0.4
    MODERATE_NEGATIVE = "moderate_negative" # -0.6 ~ -0.4
    STRONG_NEGATIVE = "strong_negative"     # -0.8 ~ -0.6
    EXTREME_NEGATIVE = "extreme_negative"   # -1.0 ~ -0.8


@dataclass
class NewsItem:
    """뉴스 아이템"""
    title: str
    url: str
    source: str  # "cryptopanic", "reddit", etc.
    published_at: datetime
    currencies: List[str]  # ["ETH", "BTC"]
    sentiment_score: Optional[float] = None  # -1.0 ~ 1.0
    sentiment_label: Optional[SentimentLabel] = None
    confidence: Optional[float] = None  # 0.0 ~ 1.0


@dataclass
class MarketSentiment:
    """시장 전체 감성"""
    symbol: str  # "ETH", "BTC"
    score: float  # -1.0 (극도 부정) ~ 1.0 (극도 긍정)
    strength: SentimentStrength
    confidence: float  # 0.0 ~ 1.0
    news_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    news_items: List[NewsItem]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "score": round(self.score, 3),
            "strength": self.strength.value,
            "confidence": round(self.confidence, 3),
            "news_count": self.news_count,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SentimentSignal:
    """감성 기반 시그널"""
    action: str  # "allow_entry", "block_entry", "neutral"
    reason: str
    sentiment: MarketSentiment
    should_block: bool
    confidence_multiplier: float  # 0.5 ~ 1.5
