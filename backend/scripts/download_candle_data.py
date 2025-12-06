#!/usr/bin/env python3
"""
캔들 데이터 대량 다운로드 스크립트

사용법:
    python download_candle_data.py --years 3
    python download_candle_data.py --symbols BTCUSDT,ETHUSDT --timeframes 1h,4h
    python download_candle_data.py --all

주기적 실행 (cron):
    # 매월 1일 00:00에 실행
    0 0 1 * * cd /path/to/backend && python scripts/download_candle_data.py --all
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 지원하는 심볼 및 타임프레임
ALL_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "DOTUSDT",
    "MATICUSDT",
]

ALL_TIMEFRAMES = ["1h", "4h", "1d"]

# 확장 타임프레임 (필요시)
EXTENDED_TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h", "1d"]


async def download_symbol_data(
    cache_manager,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    delay: float = 2.0,
) -> bool:
    """
    단일 심볼/타임프레임 데이터 다운로드

    Args:
        cache_manager: 캐시 매니저 인스턴스
        symbol: 거래쌍 (예: BTCUSDT)
        timeframe: 타임프레임 (예: 1h)
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        delay: API 호출 간 대기 시간 (초)

    Returns:
        성공 여부
    """
    try:
        logger.info(f"📥 Downloading {symbol} {timeframe}: {start_date} ~ {end_date}")

        # cache_only=False로 API 호출 허용
        candles = await cache_manager.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            cache_only=False,  # API 호출 허용
        )

        if candles:
            logger.info(f"   ✅ Downloaded {len(candles)} candles")
            await asyncio.sleep(delay)  # Rate Limit 방지
            return True
        else:
            logger.warning("   ⚠️ No data returned")
            return False

    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        await asyncio.sleep(delay * 2)  # 에러 시 더 길게 대기
        return False


async def download_all_data(
    symbols: list, timeframes: list, years: int = 3, delay: float = 2.0
):
    """
    모든 심볼/타임프레임 데이터 다운로드

    Args:
        symbols: 심볼 리스트
        timeframes: 타임프레임 리스트
        years: 다운로드할 과거 연도 수
        delay: API 호출 간 대기 시간 (초)
    """
    from src.services.candle_cache import get_candle_cache

    cache_manager = get_candle_cache()

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")

    total = len(symbols) * len(timeframes)
    completed = 0
    failed = []

    logger.info(
        f"🚀 Starting download: {len(symbols)} symbols × {len(timeframes)} timeframes"
    )
    logger.info(f"📅 Date range: {start_date} ~ {end_date} ({years} years)")
    logger.info(f"⏱️ Estimated time: ~{total * delay / 60:.1f} minutes")
    logger.info("-" * 50)

    for symbol in symbols:
        for timeframe in timeframes:
            success = await download_symbol_data(
                cache_manager, symbol, timeframe, start_date, end_date, delay
            )

            completed += 1
            progress = completed / total * 100

            if not success:
                failed.append(f"{symbol}_{timeframe}")

            logger.info(f"   Progress: {completed}/{total} ({progress:.1f}%)")

    # 결과 요약
    logger.info("-" * 50)
    logger.info(f"✅ Download complete: {completed - len(failed)}/{total} succeeded")

    if failed:
        logger.warning(f"❌ Failed: {', '.join(failed)}")

    # 캐시 정보 출력
    info = cache_manager.get_cache_info()
    logger.info("\n📊 Cache Summary:")
    logger.info(f"   Total files: {info.get('total_files', 0)}")

    caches = info.get("caches", {})
    for name, meta in caches.items():
        if isinstance(meta, dict):
            size_mb = meta.get("size_mb", "N/A")
            count = meta.get("count", "N/A")
            logger.info(f"   - {name}: {size_mb} MB, {count} candles")


def main():
    parser = argparse.ArgumentParser(description="캔들 데이터 다운로드")
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="심볼 리스트 (쉼표 구분, 예: BTCUSDT,ETHUSDT)",
    )
    parser.add_argument(
        "--timeframes",
        type=str,
        default=None,
        help="타임프레임 리스트 (쉼표 구분, 예: 1h,4h,1d)",
    )
    parser.add_argument(
        "--years", type=int, default=3, help="다운로드할 과거 연도 수 (기본: 3)"
    )
    parser.add_argument(
        "--delay", type=float, default=2.0, help="API 호출 간 대기 시간 초 (기본: 2.0)"
    )
    parser.add_argument(
        "--all", action="store_true", help="모든 심볼 및 타임프레임 다운로드"
    )
    parser.add_argument(
        "--extended",
        action="store_true",
        help="확장 타임프레임 포함 (5m, 15m, 30m 포함)",
    )

    args = parser.parse_args()

    # 심볼 결정
    if args.all:
        symbols = ALL_SYMBOLS
    elif args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        symbols = ["BTCUSDT", "ETHUSDT"]  # 기본

    # 타임프레임 결정
    if args.extended:
        timeframes = EXTENDED_TIMEFRAMES
    elif args.timeframes:
        timeframes = [t.strip() for t in args.timeframes.split(",")]
    else:
        timeframes = ALL_TIMEFRAMES  # 기본: 1h, 4h, 1d

    # 실행
    asyncio.run(
        download_all_data(
            symbols=symbols, timeframes=timeframes, years=args.years, delay=args.delay
        )
    )


if __name__ == "__main__":
    main()
