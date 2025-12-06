#!/usr/bin/env python3
"""
BTC, ETH 순차 다운로드 (최대 기간)
- 429 오류 방지를 위해 요청 간격 유지
- BTC 완료 후 ETH 다운로드
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.services.candle_cache import CandleCacheManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 다운로드할 코인 (순서대로)
COINS = [
    ("BTCUSDT", "2020-07-01"),  # BTC - Bitget 초기부터
    ("ETHUSDT", "2020-07-01"),  # ETH
    ("XRPUSDT", "2020-12-01"),  # XRP
    ("SOLUSDT", "2021-06-01"),  # SOL
]

# 타임프레임 (순서대로)
TIMEFRAMES = ["1h", "4h", "1d"]


async def download_coin(cache: CandleCacheManager, symbol: str, start_date: str):
    """단일 코인 다운로드"""
    end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info("=" * 60)
    logger.info(f"🚀 {symbol} 다운로드 시작")
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
            logger.info(f"   ✅ {symbol} {timeframe}: {count:,}개 캔들 완료")
            results.append((timeframe, count, None))

        except Exception as e:
            logger.error(f"   ❌ {symbol} {timeframe} 실패: {e}")
            results.append((timeframe, 0, str(e)))

        # Rate Limit 방지 (3초 대기)
        logger.info("   ⏳ 3초 대기 (Rate Limit 방지)...")
        await asyncio.sleep(3)

    return results


async def main():
    logger.info("\n" + "=" * 60)
    logger.info("🚀 BTC → ETH → XRP → SOL 순차 다운로드")
    logger.info("=" * 60)

    cache = CandleCacheManager()

    all_results = {}

    for symbol, start_date in COINS:
        results = await download_coin(cache, symbol, start_date)
        all_results[symbol] = results

        # 코인 간 대기 (5초)
        if symbol != COINS[-1][0]:
            logger.info(f"\n⏳ 다음 코인 대기 중 (5초)...")
            await asyncio.sleep(5)

    # 최종 리포트
    logger.info("\n" + "=" * 60)
    logger.info("📊 다운로드 완료 리포트")
    logger.info("=" * 60)

    for symbol, results in all_results.items():
        logger.info(f"\n{symbol}:")
        for timeframe, count, error in results:
            if error:
                logger.info(f"   ❌ {timeframe}: 실패 - {error}")
            else:
                logger.info(f"   ✅ {timeframe}: {count:,}개")

    # 캐시 정보
    cache_info = cache.get_cache_info()
    logger.info(f"\n💾 캐시 디렉토리: {cache_info['cache_dir']}")
    logger.info(f"💾 총 캐시 파일: {cache_info['total_files']}개")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
