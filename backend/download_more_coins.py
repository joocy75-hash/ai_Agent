#!/usr/bin/env python3
"""
추가 코인 다운로드 (DOGE, ADA, AVAX, LINK, DOT, MATIC)
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.candle_cache import CandleCacheManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 추가 다운로드할 코인
COINS = [
    ("DOGEUSDT", "2021-02-01"),
    ("ADAUSDT", "2021-03-01"),
    ("AVAXUSDT", "2021-09-01"),
    ("LINKUSDT", "2021-01-01"),
    ("DOTUSDT", "2021-01-01"),
    ("MATICUSDT", "2021-05-01"),
]

TIMEFRAMES = ["1h", "4h", "1d"]


async def download_coin(cache: CandleCacheManager, symbol: str, start_date: str):
    end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info("=" * 60)
    logger.info(f"🚀 {symbol} 다운로드")
    logger.info(f"   기간: {start_date} ~ {end_date}")
    logger.info("=" * 60)

    results = []

    for timeframe in TIMEFRAMES:
        logger.info(f"\n📥 [{symbol}] {timeframe} 다운로드 중...")

        try:
            candles = await cache.get_candles(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )

            count = len(candles) if candles else 0
            logger.info(f"   ✅ {symbol} {timeframe}: {count:,}개 완료")
            results.append((timeframe, count, None))

        except Exception as e:
            logger.error(f"   ❌ {symbol} {timeframe} 실패: {e}")
            results.append((timeframe, 0, str(e)))

        await asyncio.sleep(3)

    return results


async def main():
    logger.info("\n" + "=" * 60)
    logger.info("🚀 추가 코인 다운로드 (DOGE, ADA, AVAX, LINK, DOT, MATIC)")
    logger.info("=" * 60)

    cache = CandleCacheManager()
    all_results = {}

    for symbol, start_date in COINS:
        results = await download_coin(cache, symbol, start_date)
        all_results[symbol] = results

        if symbol != COINS[-1][0]:
            logger.info(f"\n⏳ 다음 코인 대기 (5초)...")
            await asyncio.sleep(5)

    # 리포트
    logger.info("\n" + "=" * 60)
    logger.info("📊 다운로드 완료")
    logger.info("=" * 60)

    for symbol, results in all_results.items():
        logger.info(f"\n{symbol}:")
        for timeframe, count, error in results:
            if error:
                logger.info(f"   ❌ {timeframe}: {error}")
            else:
                logger.info(f"   ✅ {timeframe}: {count:,}개")

    cache_info = cache.get_cache_info()
    logger.info(f"\n💾 총 캐시 파일: {cache_info['total_files']}개")


if __name__ == "__main__":
    asyncio.run(main())
