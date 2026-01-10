"""
Sentiment Analyzer - Data Sources (CryptoPanic, Reddit)

뉴스 데이터 수집을 위한 클라이언트 구현
"""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import NewsItem

logger = logging.getLogger(__name__)


class NewsDataSource(ABC):
    """뉴스 데이터 소스 기본 클래스"""

    @abstractmethod
    async def fetch_news(
        self,
        symbols: List[str],
        hours: int = 24
    ) -> List[NewsItem]:
        """뉴스 가져오기"""
        pass


class CryptoPanicSource(NewsDataSource):
    """
    CryptoPanic API 클라이언트

    무료 플랜: 100 requests/day
    API 문서: https://cryptopanic.com/developers/api/
    """

    BASE_URL = "https://cryptopanic.com/api/v1/posts/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CRYPTOPANIC_API_KEY", "")
        if not self.api_key:
            logger.warning("⚠️  CryptoPanic API 키가 설정되지 않음")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def fetch_news(
        self,
        symbols: List[str],
        hours: int = 24
    ) -> List[NewsItem]:
        """
        CryptoPanic에서 뉴스 가져오기

        Args:
            symbols: 심볼 리스트 (예: ["ETH", "BTC"])
            hours: 최근 N시간 이내 뉴스

        Returns:
            뉴스 아이템 리스트
        """
        if not self.api_key:
            logger.warning("CryptoPanic API 키 없음 - 빈 리스트 반환")
            return []

        try:
            # API 요청 파라미터
            params = {
                "auth_token": self.api_key,
                "currencies": ",".join(symbols),
                "filter": "hot",  # 인기 뉴스
                "kind": "news",   # 뉴스만 (소셜 제외)
                "regions": "en",  # 영어만
            }

            logger.info(f"CryptoPanic API 요청: symbols={symbols}, hours={hours}")

            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # NewsItem으로 변환
            news_items = []
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            for item in results:
                try:
                    # 시간 파싱
                    created_at_str = item.get("created_at", "")
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )

                    # 시간 필터
                    if created_at < cutoff_time:
                        continue

                    # 통화 리스트
                    currencies = [
                        c["code"] for c in item.get("currencies", [])
                    ]

                    news_item = NewsItem(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        source="cryptopanic",
                        published_at=created_at,
                        currencies=currencies,
                    )
                    news_items.append(news_item)

                except Exception as e:
                    logger.error(f"뉴스 파싱 에러: {e}")
                    continue

            logger.info(f"✅ CryptoPanic 뉴스 {len(news_items)}개 수집")
            return news_items

        except requests.exceptions.HTTPError as e:
            logger.error(f"CryptoPanic API HTTP 에러: {e}")
            return []
        except Exception as e:
            logger.error(f"CryptoPanic API 에러: {e}")
            return []


class RedditSource(NewsDataSource):
    """
    Reddit API 클라이언트 (백업 소스)

    r/CryptoCurrency, r/ethereum 서브레딧 모니터링
    TODO: Phase 4에서 구현
    """

    def __init__(self):
        pass

    async def fetch_news(
        self,
        symbols: List[str],
        hours: int = 24
    ) -> List[NewsItem]:
        """Reddit에서 게시물 가져오기 (향후 구현)"""
        logger.info("Reddit 소스는 아직 구현되지 않음")
        return []
