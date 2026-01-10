"""
Sentiment Analyzer Agent

FinBERT를 사용한 금융 뉴스 감성 분석 에이전트
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from ..base import BaseAgent, AgentTask
from .models import (
    MarketSentiment,
    NewsItem,
    SentimentLabel,
    SentimentSignal,
    SentimentStrength,
)
from .data_sources import CryptoPanicSource, RedditSource

logger = logging.getLogger(__name__)


class SentimentAnalyzerAgent(BaseAgent):
    """
    감성 분석 에이전트

    주요 기능:
    1. FinBERT 모델을 사용한 뉴스 감성 분석
    2. 여러 데이터 소스 통합 (CryptoPanic, Reddit)
    3. 심볼별 전체 시장 감성 계산
    4. 거래 시그널 생성 (진입 허용/차단)
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        config: dict = None,
        redis_client=None,
    ):
        super().__init__(agent_id, name, config)
        self.redis_client = redis_client

        cfg = config or {}

        # FinBERT 모델 설정
        self.model_name = cfg.get("model_name", "ProsusAI/finbert")
        self.model = None
        self.tokenizer = None
        self._load_model()

        # 데이터 소스
        self.cryptopanic = CryptoPanicSource()
        self.reddit = RedditSource()

        # 임계값 설정
        self.extreme_positive_threshold = cfg.get("extreme_positive", 0.5)
        self.extreme_negative_threshold = cfg.get("extreme_negative", -0.5)
        self.block_entry_threshold = cfg.get("block_entry", -0.7)

        # 캐시 설정
        self._cache: Dict[str, MarketSentiment] = {}
        self._cache_ttl = timedelta(minutes=cfg.get("cache_ttl_minutes", 30))

    def _load_model(self):
        """FinBERT 모델 로드"""
        try:
            logger.info(f"FinBERT 모델 로드 중: {self.model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name
            )
            self.model.eval()

            logger.info("✅ FinBERT 모델 로드 완료")

        except Exception as e:
            logger.error(f"❌ FinBERT 모델 로드 실패: {e}")
            self.model = None
            self.tokenizer = None

    def _analyze_text_sentiment(self, text: str) -> tuple:
        """텍스트 감성 분석"""
        if not self.model or not self.tokenizer:
            return 0.0, SentimentLabel.NEUTRAL, 0.0

        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )

            with torch.no_grad():
                outputs = self.model(**inputs)

            logits = outputs.logits
            probs = torch.softmax(logits, dim=1)[0]

            pos_prob = probs[0].item()
            neg_prob = probs[1].item()
            neu_prob = probs[2].item()

            score = pos_prob - neg_prob

            if pos_prob > neg_prob and pos_prob > neu_prob:
                label = SentimentLabel.POSITIVE
                confidence = pos_prob
            elif neg_prob > pos_prob and neg_prob > neu_prob:
                label = SentimentLabel.NEGATIVE
                confidence = neg_prob
            else:
                label = SentimentLabel.NEUTRAL
                confidence = neu_prob

            return score, label, confidence

        except Exception as e:
            logger.error(f"감성 분석 에러: {e}")
            return 0.0, SentimentLabel.NEUTRAL, 0.0

    def _calculate_strength(self, score: float) -> SentimentStrength:
        """감성 점수 to 강도 변환"""
        if score >= 0.8:
            return SentimentStrength.EXTREME_POSITIVE
        elif score >= 0.6:
            return SentimentStrength.STRONG_POSITIVE
        elif score >= 0.4:
            return SentimentStrength.MODERATE_POSITIVE
        elif score <= -0.8:
            return SentimentStrength.EXTREME_NEGATIVE
        elif score <= -0.6:
            return SentimentStrength.STRONG_NEGATIVE
        elif score <= -0.4:
            return SentimentStrength.MODERATE_NEGATIVE
        else:
            return SentimentStrength.NEUTRAL

    async def _fetch_all_news(
        self,
        symbols: List[str],
        hours: int = 24
    ) -> List[NewsItem]:
        """모든 데이터 소스에서 뉴스 수집"""
        all_news = []
        cryptopanic_news = await self.cryptopanic.fetch_news(symbols, hours)
        all_news.extend(cryptopanic_news)
        return all_news

    async def analyze_market_sentiment(
        self,
        symbol: str,
        hours: int = 24,
        use_cache: bool = True
    ) -> MarketSentiment:
        """시장 감성 분석"""
        cache_key = f"sentiment:{symbol}:{hours}"
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            age = datetime.utcnow() - cached.timestamp
            if age < self._cache_ttl:
                logger.info(f"캐시된 감성 데이터 사용: {symbol}")
                return cached

        logger.info(f"시장 감성 분석 시작: symbol={symbol}, hours={hours}")

        news_items = await self._fetch_all_news([symbol], hours)

        if not news_items:
            logger.warning(f"뉴스 없음: {symbol}")
            return MarketSentiment(
                symbol=symbol,
                score=0.0,
                strength=SentimentStrength.NEUTRAL,
                confidence=0.0,
                news_count=0,
                positive_count=0,
                negative_count=0,
                neutral_count=0,
                news_items=[],
            )

        total_score = 0.0
        total_confidence = 0.0
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for news in news_items:
            score, label, confidence = self._analyze_text_sentiment(news.title)
            news.sentiment_score = score
            news.sentiment_label = label
            news.confidence = confidence
            total_score += score
            total_confidence += confidence

            if label == SentimentLabel.POSITIVE:
                positive_count += 1
            elif label == SentimentLabel.NEGATIVE:
                negative_count += 1
            else:
                neutral_count += 1

        avg_score = total_score / len(news_items)
        avg_confidence = total_confidence / len(news_items)
        strength = self._calculate_strength(avg_score)

        sentiment = MarketSentiment(
            symbol=symbol,
            score=avg_score,
            strength=strength,
            confidence=avg_confidence,
            news_count=len(news_items),
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            news_items=news_items,
        )

        self._cache[cache_key] = sentiment

        logger.info(
            f"✅ 감성 분석 완료: {symbol} | "
            f"Score={avg_score:.3f} | "
            f"Strength={strength.value} | "
            f"News={len(news_items)}"
        )

        return sentiment

    def generate_sentiment_signal(
        self,
        sentiment: MarketSentiment
    ) -> SentimentSignal:
        """감성 기반 시그널 생성"""
        score = sentiment.score
        confidence = sentiment.confidence

        if score <= self.block_entry_threshold and confidence > 0.7:
            return SentimentSignal(
                action="block_entry",
                reason=f"Extreme negative sentiment (score={score:.2f})",
                sentiment=sentiment,
                should_block=True,
                confidence_multiplier=0.5,
            )

        if score <= self.extreme_negative_threshold:
            multiplier = 0.7 if confidence > 0.6 else 0.85
            return SentimentSignal(
                action="reduce_confidence",
                reason=f"Strong negative sentiment (score={score:.2f})",
                sentiment=sentiment,
                should_block=False,
                confidence_multiplier=multiplier,
            )

        if score >= self.extreme_positive_threshold:
            multiplier = 1.2 if confidence > 0.7 else 1.1
            return SentimentSignal(
                action="boost_confidence",
                reason=f"Strong positive sentiment (score={score:.2f})",
                sentiment=sentiment,
                should_block=False,
                confidence_multiplier=multiplier,
            )

        return SentimentSignal(
            action="neutral",
            reason=f"Neutral sentiment (score={score:.2f})",
            sentiment=sentiment,
            should_block=False,
            confidence_multiplier=1.0,
        )

    async def process(self, task: AgentTask) -> dict:
        """에이전트 작업 처리"""
        task_type = task.task_type
        params = task.params or {}

        if task_type == "analyze_market_sentiment":
            symbol = params.get("symbol", "ETH")
            hours = params.get("hours", 24)
            sentiment = await self.analyze_market_sentiment(symbol, hours)
            return sentiment.to_dict()

        elif task_type == "get_sentiment_signal":
            symbol = params.get("symbol", "ETH")
            hours = params.get("hours", 24)
            sentiment = await self.analyze_market_sentiment(symbol, hours)
            signal = self.generate_sentiment_signal(sentiment)
            return {
                "action": signal.action,
                "reason": signal.reason,
                "should_block": signal.should_block,
                "confidence_multiplier": signal.confidence_multiplier,
                "sentiment": sentiment.to_dict(),
            }

        else:
            return {"error": f"Unknown task type: {task_type}"}
