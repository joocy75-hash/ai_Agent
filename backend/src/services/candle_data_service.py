"""
Candle Data Service
- Bitget API에서 과거 캔들 데이터 수집
- 캐싱을 통한 효율적인 데이터 관리
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class Candle:
    """캔들 데이터 구조체"""
    timestamp: int          # Unix timestamp (ms)
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)


class CandleDataService:
    """
    캔들 데이터 수집 서비스

    Bitget API 사용:
    - 선물: https://api.bitget.com/api/v2/mix/market/candles
    - 최대 1000개 캔들/요청
    """

    BITGET_FUTURES_CANDLE_URL = "https://api.bitget.com/api/v2/mix/market/candles"

    # 캔들 간격 (분)
    GRANULARITY_MAP = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1H": "1H",
        "4H": "4H",
        "1D": "1D"
    }

    def __init__(self):
        self._cache: Dict[str, List[Candle]] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(hours=1)  # 캐시 유효시간

    async def get_candles(
        self,
        symbol: str,
        granularity: str = "5m",
        days: int = 30,
        product_type: str = "USDT-FUTURES"
    ) -> List[Candle]:
        """
        과거 캔들 데이터 조회

        Args:
            symbol: 심볼 (예: "SOLUSDT")
            granularity: 캔들 간격 ("1m", "5m", "15m", "30m", "1H", "4H", "1D")
            days: 조회 기간 (일)
            product_type: 상품 유형 ("USDT-FUTURES", "COIN-FUTURES")

        Returns:
            List[Candle]: 캔들 데이터 리스트 (오래된 순)
        """
        cache_key = f"{symbol}_{granularity}_{days}"

        # 캐시 확인
        if self._is_cache_valid(cache_key):
            logger.info(f"Using cached candle data for {cache_key}")
            return self._cache[cache_key]

        # API에서 데이터 수집
        candles = await self._fetch_candles(
            symbol=symbol,
            granularity=granularity,
            days=days,
            product_type=product_type
        )

        # 캐시 저장
        self._cache[cache_key] = candles
        self._cache_expiry[cache_key] = datetime.now() + self._cache_ttl

        return candles

    async def _fetch_candles(
        self,
        symbol: str,
        granularity: str,
        days: int,
        product_type: str
    ) -> List[Candle]:
        """Bitget API에서 캔들 데이터 가져오기"""

        # 시간 계산
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        # 캔들 간격에 따른 예상 개수 계산
        minutes_per_candle = self._get_minutes(granularity)
        total_minutes = days * 24 * 60
        expected_candles = total_minutes // minutes_per_candle

        logger.info(
            f"Fetching {expected_candles} candles for {symbol} "
            f"({granularity}, {days} days)"
        )

        all_candles = []
        current_end = end_time

        async with aiohttp.ClientSession() as session:
            while current_end > start_time:
                params = {
                    "symbol": symbol,
                    "productType": product_type,
                    "granularity": granularity,
                    "endTime": str(current_end),
                    "limit": "1000"  # 최대 1000개
                }

                try:
                    async with session.get(
                        self.BITGET_FUTURES_CANDLE_URL,
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status != 200:
                            logger.error(f"API error: {response.status}")
                            break

                        data = await response.json()

                        if data.get("code") != "00000":
                            logger.error(f"API error: {data.get('msg')}")
                            break

                        candle_data = data.get("data", [])
                        if not candle_data:
                            break

                        # 캔들 파싱
                        for c in candle_data:
                            candle = Candle(
                                timestamp=int(c[0]),
                                open=Decimal(c[1]),
                                high=Decimal(c[2]),
                                low=Decimal(c[3]),
                                close=Decimal(c[4]),
                                volume=Decimal(c[5])
                            )
                            all_candles.append(candle)

                        # 다음 배치를 위한 시간 업데이트
                        oldest_timestamp = min(int(c[0]) for c in candle_data)
                        current_end = oldest_timestamp - 1

                        # API 레이트 리밋 방지
                        await asyncio.sleep(0.1)

                except asyncio.TimeoutError:
                    logger.error("API timeout")
                    break
                except Exception as e:
                    logger.error(f"Error fetching candles: {e}")
                    break

        # 시간순 정렬 (오래된 것이 앞에)
        all_candles.sort(key=lambda c: c.timestamp)

        # start_time 이후의 캔들만 필터링
        filtered = [c for c in all_candles if c.timestamp >= start_time]

        logger.info(f"Fetched {len(filtered)} candles for {symbol}")
        return filtered

    def _get_minutes(self, granularity: str) -> int:
        """캔들 간격을 분으로 변환"""
        mapping = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1H": 60,
            "4H": 240,
            "1D": 1440
        }
        return mapping.get(granularity, 5)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 확인"""
        if cache_key not in self._cache:
            return False
        if cache_key not in self._cache_expiry:
            return False
        return datetime.now() < self._cache_expiry[cache_key]

    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        self._cache_expiry.clear()


# 싱글톤 인스턴스
_candle_service_instance: Optional[CandleDataService] = None


def get_candle_data_service() -> CandleDataService:
    """CandleDataService 싱글톤 인스턴스 반환"""
    global _candle_service_instance
    if _candle_service_instance is None:
        _candle_service_instance = CandleDataService()
    return _candle_service_instance
