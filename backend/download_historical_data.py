#!/usr/bin/env python3
"""
메이저 코인 과거 캔들 데이터 다운로드 스크립트 (안정화 버전)

각 코인별 실제 상장일을 고려하여 다운로드합니다.
"""

import asyncio
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.services.candle_cache import CandleCacheManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("data_download.log")],
)
logger = logging.getLogger(__name__)


# 코인별 Bitget 상장일 (실제 데이터 시작일)
# 정확한 날짜가 아닐 수 있으니 여유있게 설정
COIN_START_DATES = {
    "BTCUSDT": "2020-07-01",  # BTC - 비트겟 초기
    "ETHUSDT": "2020-07-01",  # ETH - 비트겟 초기
    "SOLUSDT": "2021-06-01",  # SOL - 2021년 상장
    "XRPUSDT": "2020-12-01",  # XRP - 2020년 말
    "DOGEUSDT": "2021-02-01",  # DOGE - 2021년 초
    "ADAUSDT": "2021-03-01",  # ADA - 2021년
    "AVAXUSDT": "2021-09-01",  # AVAX - 2021년
    "LINKUSDT": "2021-01-01",  # LINK - 2021년 초
    "DOTUSDT": "2021-01-01",  # DOT - 2021년 초
    "MATICUSDT": "2021-05-01",  # MATIC - 2021년
}

# 주요 코인 목록 (안정적인 데이터 확인된 것)
STABLE_COINS = [
    "BTCUSDT",
    "ETHUSDT",
]

# 추가 코인 (최근 데이터만)
RECENT_COINS = [
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "DOTUSDT",
    "MATICUSDT",
]


def get_start_date(symbol: str, timeframe: str) -> str:
    """심볼과 타임프레임에 따른 시작 날짜"""
    coin_start = COIN_START_DATES.get(symbol, "2021-01-01")

    # 1분봉은 최근 7일만
    if timeframe == "1m":
        return (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    # 5분봉은 최근 30일
    elif timeframe == "5m":
        return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    # 15분봉은 최근 90일
    elif timeframe == "15m":
        return (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    else:
        # 1h, 4h는 상장일부터
        return coin_start


async def download_btc_eth_full():
    """BTC, ETH만 전체 기간 다운로드 (가장 안정적)"""

    cache = CandleCacheManager()

    coins = ["BTCUSDT", "ETHUSDT"]
    timeframes = ["1h", "4h"]
    total = len(coins) * len(timeframes)
    completed = 0
    success_data = []
    failed = []

    end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info("=" * 70)
    logger.info("🚀 BTC, ETH 전체 기간 데이터 다운로드")
    logger.info("=" * 70)
    logger.info(f"💰 코인: {', '.join(coins)}")
    logger.info(f"⏱️ 타임프레임: {', '.join(timeframes)}")
    logger.info(f"📅 기간: 2020-07-01 ~ {end_date}")
    logger.info("=" * 70)
    logger.info("")

    start_time = datetime.now()

    for symbol in coins:
        start_date = COIN_START_DATES[symbol]

        for timeframe in timeframes:
            completed += 1
            progress = f"[{completed}/{total}]"

            logger.info(f"{progress} 📥 {symbol} {timeframe} 다운로드 중...")

            try:
                candles = await cache.get_candles(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                )

                count = len(candles)
                logger.info(f"{progress} ✅ {symbol} {timeframe}: {count:,}개 캔들")
                success_data.append((symbol, timeframe, count))

            except Exception as e:
                logger.error(f"{progress} ❌ {symbol} {timeframe} 실패: {e}")
                failed.append((symbol, timeframe, str(e)))

            await asyncio.sleep(2)

        logger.info("")
        await asyncio.sleep(3)

    # 완료 리포트
    elapsed = datetime.now() - start_time

    logger.info("")
    logger.info("=" * 70)
    logger.info("📊 다운로드 완료")
    logger.info("=" * 70)
    logger.info(f"✅ 성공: {len(success_data)}/{total}")
    logger.info(f"⏱️ 소요 시간: {elapsed}")

    total_candles = sum(c for _, _, c in success_data)
    logger.info(f"📊 총 캔들: {total_candles:,}개")

    # 캐시 정보
    cache_info = cache.get_cache_info()
    logger.info(f"💾 캐시 디렉토리: {cache_info['cache_dir']}")
    logger.info("=" * 70)

    return len(failed) == 0


async def download_all_coins():
    """모든 코인 다운로드 (각 코인 상장일 고려)"""

    cache = CandleCacheManager()

    all_coins = list(COIN_START_DATES.keys())
    timeframes = ["1h", "4h"]
    total = len(all_coins) * len(timeframes)
    completed = 0
    success_data = []
    failed = []

    end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info("=" * 70)
    logger.info("🚀 메이저 코인 10개 데이터 다운로드")
    logger.info("=" * 70)
    logger.info(f"💰 코인: {', '.join(all_coins)}")
    logger.info(f"⏱️ 타임프레임: {', '.join(timeframes)}")
    logger.info("")
    logger.info("📅 코인별 시작일:")
    for coin, start in COIN_START_DATES.items():
        logger.info(f"   {coin}: {start}부터")
    logger.info("=" * 70)
    logger.info("")

    start_time = datetime.now()

    for symbol in all_coins:
        start_date = COIN_START_DATES[symbol]

        for timeframe in timeframes:
            completed += 1
            progress = f"[{completed}/{total}]"

            logger.info(
                f"{progress} 📥 {symbol} {timeframe} ({start_date} ~ {end_date})"
            )

            try:
                candles = await cache.get_candles(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                )

                count = len(candles)
                logger.info(f"{progress} ✅ {symbol} {timeframe}: {count:,}개 캔들")
                success_data.append((symbol, timeframe, count))

            except Exception as e:
                logger.error(f"{progress} ❌ {symbol} {timeframe} 실패: {e}")
                failed.append((symbol, timeframe, str(e)))

            await asyncio.sleep(2)

        logger.info("")
        await asyncio.sleep(3)

    # 완료 리포트
    elapsed = datetime.now() - start_time

    logger.info("")
    logger.info("=" * 70)
    logger.info("📊 다운로드 완료 리포트")
    logger.info("=" * 70)
    logger.info(f"✅ 성공: {len(success_data)}/{total}")
    logger.info(f"❌ 실패: {len(failed)}/{total}")
    logger.info(f"⏱️ 소요 시간: {elapsed}")

    if success_data:
        total_candles = sum(c for _, _, c in success_data)
        logger.info(f"📊 총 캔들: {total_candles:,}개")

    if failed:
        logger.info("")
        logger.info("❌ 실패 목록:")
        for symbol, timeframe, error in failed:
            logger.info(f"   - {symbol} {timeframe}: {error[:50]}...")

    # 캐시 정보
    cache_info = cache.get_cache_info()
    logger.info("")
    logger.info(f"💾 캐시 디렉토리: {cache_info['cache_dir']}")
    logger.info(f"💾 캐시 파일: {cache_info['total_files']}개")
    logger.info("=" * 70)

    return len(failed) == 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="메이저 코인 과거 데이터 다운로드")
    parser.add_argument(
        "--btc-eth", action="store_true", help="BTC, ETH만 다운로드 (가장 안정적)"
    )
    parser.add_argument("--all", action="store_true", help="모든 메이저 코인 다운로드")

    args = parser.parse_args()

    if args.btc_eth:
        success = asyncio.run(download_btc_eth_full())
        sys.exit(0 if success else 1)
    elif args.all:
        success = asyncio.run(download_all_coins())
        sys.exit(0 if success else 1)
    else:
        print("사용법:")
        print("  python3 download_historical_data.py --btc-eth   # BTC, ETH만 (권장)")
        print("  python3 download_historical_data.py --all       # 모든 메이저 코인")
        sys.exit(0)
