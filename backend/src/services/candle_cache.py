"""
캔들 데이터 캐싱 시스템

다중 사용자 백테스트를 위한 공용 캔들 데이터 캐시.
Bitget API Rate Limit 문제를 해결하고 성능을 최적화합니다.

기능:
1. 공용 캐시: 모든 사용자가 동일한 캔들 데이터 공유
2. 스마트 갱신: 없는 데이터만 API로 가져옴
3. Rate Limit 큐: 동시 요청 순차 처리
4. 파일 기반 영구 저장: 서버 재시작 후에도 유지
"""

import csv
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import json
import time

logger = logging.getLogger(__name__)


class CandleCacheManager:
    """
    공용 캔들 데이터 캐시 매니저

    모든 사용자의 백테스트 요청을 위한 중앙 캐시 관리.
    """

    # 지원하는 심볼과 타임프레임
    SUPPORTED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1D"]

    # 타임프레임별 캔들 간격 (밀리초)
    TIMEFRAME_MS = {
        "1m": 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "30m": 30 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "1D": 24 * 60 * 60 * 1000,
    }

    def __init__(self, cache_dir: Optional[str] = None):
        """
        캐시 매니저 초기화

        Args:
            cache_dir: 캐시 디렉토리 경로 (없으면 기본 경로 사용)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # 기본: backend/candle_cache/
            self.cache_dir = Path(__file__).parent.parent.parent / "candle_cache"

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 메모리 캐시 (자주 사용되는 데이터)
        self._memory_cache: Dict[str, List[Dict]] = {}
        self._memory_cache_timestamps: Dict[str, float] = {}
        self._memory_cache_max_age = 300  # 5분

        # Rate Limit 관리
        self._api_queue = asyncio.Queue()
        self._rate_limit_lock = asyncio.Lock()
        self._last_api_call = 0
        self._min_api_interval = 2.0  # 2초 간격 (Rate Limit 안전)

        # 캐시 메타데이터
        self._metadata_file = self.cache_dir / "cache_metadata.json"
        self._metadata = self._load_metadata()

        logger.info(f"📦 CandleCacheManager initialized: {self.cache_dir}")

    def _load_metadata(self) -> Dict:
        """캐시 메타데이터 로드"""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
        return {"caches": {}, "last_update": None}

    def _save_metadata(self):
        """캐시 메타데이터 저장"""
        try:
            self._metadata["last_update"] = datetime.now().isoformat()
            with open(self._metadata_file, "w") as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache metadata: {e}")

    def _get_cache_key(self, symbol: str, timeframe: str) -> str:
        """캐시 키 생성"""
        return f"{symbol}_{timeframe}"

    def _get_cache_file(self, symbol: str, timeframe: str) -> Path:
        """캐시 파일 경로"""
        return self.cache_dir / f"{symbol}_{timeframe}.csv"

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        cache_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        캔들 데이터 조회 (캐시 우선)

        1. 캐시 확인 → 있으면 반환
        2. 캐시 없거나 부족 → cache_only=True면 캐시만 반환, 아니면 API 호출

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
            timeframe: 타임프레임 (예: 1h)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            cache_only: True면 API 호출 없이 캐시 데이터만 반환 (Rate Limit 방지)

        Returns:
            캔들 데이터 리스트
        """
        symbol = symbol.upper().replace("/", "")
        cache_key = self._get_cache_key(symbol, timeframe)

        logger.info(
            f"📊 Requesting candles: {symbol} {timeframe} ({start_date} ~ {end_date})"
        )

        # 1. 메모리 캐시 확인
        memory_candles = self._get_from_memory_cache(cache_key, start_date, end_date)
        if memory_candles:
            logger.info(f"   ✅ Memory cache hit: {len(memory_candles)} candles")
            return memory_candles

        # 2. 파일 캐시 확인
        file_candles = self._get_from_file_cache(
            symbol, timeframe, start_date, end_date
        )

        # 3. 필요한 기간 계산
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )

        if file_candles:
            # 캐시에 있는 기간 확인
            cached_start = min(c["timestamp"] for c in file_candles)
            cached_end = max(c["timestamp"] for c in file_candles)

            start_ts = int(start_dt.timestamp() * 1000)
            end_ts = int(end_dt.timestamp() * 1000)

            # 필요한 기간이 캐시 범위 내에 있는지 확인
            if cached_start <= start_ts and cached_end >= end_ts:
                # 캐시 범위 내 → 필터링 후 반환
                result = [
                    c for c in file_candles if start_ts <= c["timestamp"] <= end_ts
                ]
                logger.info(f"   ✅ File cache hit: {len(result)} candles")
                self._update_memory_cache(cache_key, result)
                return result

            # 부분 캐시 → 캐시 전용 모드면 캐시만 반환
            if cache_only:
                result = [
                    c for c in file_candles if start_ts <= c["timestamp"] <= end_ts
                ]
                if result:
                    logger.info(
                        f"   ✅ Cache only mode: {len(result)} candles (may be partial)"
                    )
                    self._update_memory_cache(cache_key, result)
                    return result
                else:
                    logger.warning(f"   ⚠️ Cache only mode: no data in requested range")
                    return file_candles  # 전체 캐시 반환

            # 부분 캐시 → 부족한 부분만 API 호출
            missing_ranges = self._calculate_missing_ranges(
                file_candles, start_ts, end_ts, timeframe
            )

            if missing_ranges:
                logger.info(
                    f"   ⚠️ Partial cache, fetching {len(missing_ranges)} missing ranges"
                )
                new_candles = await self._fetch_missing_ranges(
                    symbol, timeframe, missing_ranges
                )
                # 기존 캐시와 합치기
                all_candles = file_candles + new_candles
                all_candles = self._deduplicate_candles(all_candles)
                self._save_to_file_cache(symbol, timeframe, all_candles)

                result = [
                    c for c in all_candles if start_ts <= c["timestamp"] <= end_ts
                ]
                self._update_memory_cache(cache_key, result)
                return result

        # 4. 캐시 없음
        if cache_only:
            logger.warning(
                f"   ⚠️ Cache only mode: no cache available for {symbol} {timeframe}"
            )
            return []

        logger.info(f"   🌐 No cache, fetching from Bitget API...")
        candles = await self._fetch_from_api(symbol, timeframe, start_date, end_date)

        if candles:
            # 파일 캐시에 저장
            self._save_to_file_cache(symbol, timeframe, candles)
            self._update_memory_cache(cache_key, candles)

        return candles

    def _get_from_memory_cache(
        self, cache_key: str, start_date: str, end_date: str
    ) -> Optional[List[Dict]]:
        """메모리 캐시에서 조회"""
        if cache_key not in self._memory_cache:
            return None

        # 캐시 만료 확인
        cache_time = self._memory_cache_timestamps.get(cache_key, 0)
        if time.time() - cache_time > self._memory_cache_max_age:
            del self._memory_cache[cache_key]
            del self._memory_cache_timestamps[cache_key]
            return None

        candles = self._memory_cache[cache_key]

        # 요청 기간 필터링
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
        start_ts = int(start_dt.timestamp() * 1000)
        end_ts = int(end_dt.timestamp() * 1000)

        return [c for c in candles if start_ts <= c["timestamp"] <= end_ts]

    def _update_memory_cache(self, cache_key: str, candles: List[Dict]):
        """메모리 캐시 업데이트"""
        self._memory_cache[cache_key] = candles
        self._memory_cache_timestamps[cache_key] = time.time()

    def _get_from_file_cache(
        self, symbol: str, timeframe: str, start_date: str, end_date: str
    ) -> List[Dict]:
        """파일 캐시에서 조회"""
        cache_file = self._get_cache_file(symbol, timeframe)

        if not cache_file.exists():
            return []

        try:
            candles = []
            with open(cache_file, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    candles.append(
                        {
                            "timestamp": int(row["timestamp"]),
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "volume": float(row["volume"]),
                        }
                    )

            logger.debug("Loaded %d candles from %s", len(candles), cache_file)
            return candles

        except Exception as e:
            logger.error(f"Failed to read cache file {cache_file}: {e}")
            return []

    def _save_to_file_cache(self, symbol: str, timeframe: str, candles: List[Dict]):
        """파일 캐시에 저장"""
        if not candles:
            return

        cache_file = self._get_cache_file(symbol, timeframe)

        try:
            # 정렬 (오래된 것부터)
            candles = sorted(candles, key=lambda x: x["timestamp"])

            with open(cache_file, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
                )
                writer.writeheader()
                writer.writerows(candles)

            # 메타데이터 업데이트
            cache_key = self._get_cache_key(symbol, timeframe)
            self._metadata["caches"][cache_key] = {
                "symbol": symbol,
                "timeframe": timeframe,
                "count": len(candles),
                "start": min(c["timestamp"] for c in candles),
                "end": max(c["timestamp"] for c in candles),
                "updated_at": datetime.now().isoformat(),
            }
            self._save_metadata()

            logger.info(f"   💾 Saved {len(candles)} candles to {cache_file.name}")

        except Exception as e:
            logger.error(f"Failed to save cache file {cache_file}: {e}")

    def _calculate_missing_ranges(
        self,
        cached_candles: List[Dict],
        start_ts: int,
        end_ts: int,
        timeframe: str,
    ) -> List[Tuple[int, int]]:
        """캐시에서 누락된 기간 계산"""
        if not cached_candles:
            return [(start_ts, end_ts)]

        cached_start = min(c["timestamp"] for c in cached_candles)
        cached_end = max(c["timestamp"] for c in cached_candles)

        missing = []

        # 시작 전 누락
        if start_ts < cached_start:
            missing.append((start_ts, cached_start - 1))

        # 끝 후 누락
        if end_ts > cached_end:
            missing.append((cached_end + 1, end_ts))

        return missing

    async def _fetch_missing_ranges(
        self,
        symbol: str,
        timeframe: str,
        missing_ranges: List[Tuple[int, int]],
    ) -> List[Dict]:
        """누락된 기간의 데이터를 API에서 가져옴"""
        all_candles = []

        for start_ts, end_ts in missing_ranges:
            start_date = datetime.fromtimestamp(start_ts / 1000).strftime("%Y-%m-%d")
            end_date = datetime.fromtimestamp(end_ts / 1000).strftime("%Y-%m-%d")

            candles = await self._fetch_from_api(
                symbol, timeframe, start_date, end_date
            )
            all_candles.extend(candles)

        return all_candles

    def _deduplicate_candles(self, candles: List[Dict]) -> List[Dict]:
        """중복 캔들 제거"""
        seen = set()
        unique = []
        for c in candles:
            if c["timestamp"] not in seen:
                seen.add(c["timestamp"])
                unique.append(c)
        return sorted(unique, key=lambda x: x["timestamp"])

    async def _fetch_from_api(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
    ) -> List[Dict]:
        """
        Bitget API에서 캔들 데이터 가져오기 (Rate Limit 관리)
        """
        from .bitget_rest import BitgetRestClient

        async with self._rate_limit_lock:
            # Rate Limit 대기
            elapsed = time.time() - self._last_api_call
            if elapsed < self._min_api_interval:
                await asyncio.sleep(self._min_api_interval - elapsed)

            try:
                client = BitgetRestClient()
                candles = await client.get_all_historical_candles(
                    symbol=symbol,
                    interval=timeframe,
                    start_time=start_date,
                    end_time=end_date,
                )
                self._last_api_call = time.time()

                logger.info(f"   🌐 Fetched {len(candles)} candles from Bitget API")
                return candles

            except Exception as e:
                logger.error(f"Failed to fetch from Bitget API: {e}")
                raise

    def get_cache_info(self) -> Dict[str, Any]:
        """캐시 정보 조회"""
        cache_files = list(self.cache_dir.glob("*.csv"))

        info = {
            "cache_dir": str(self.cache_dir),
            "total_files": len(cache_files),
            "caches": {},
        }

        for cache_file in cache_files:
            name = cache_file.stem
            stat = cache_file.stat()
            info["caches"][name] = {
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }

        # 메타데이터 추가
        for key, meta in self._metadata.get("caches", {}).items():
            if key in info["caches"]:
                info["caches"][key].update(meta)

        return info

    async def preload_popular_symbols(self):
        """
        인기 심볼의 최근 데이터 미리 로드

        서버 시작 시 호출하여 자주 사용되는 데이터를 캐싱
        """
        logger.info("🔄 Preloading popular symbol data...")

        # 최근 1년 데이터 프리로드
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # 가장 인기 있는 심볼과 타임프레임
        popular = [
            ("BTCUSDT", "1h"),
            ("ETHUSDT", "1h"),
            ("BTCUSDT", "4h"),
            ("ETHUSDT", "4h"),
        ]

        for symbol, timeframe in popular:
            try:
                await self.get_candles(symbol, timeframe, start_date, end_date)
                logger.info(f"   ✅ Preloaded {symbol} {timeframe}")
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to preload {symbol} {timeframe}: {e}")

            # Rate Limit 방지
            await asyncio.sleep(1)

        logger.info("✅ Preloading complete")

    def clear_cache(
        self, symbol: Optional[str] = None, timeframe: Optional[str] = None
    ):
        """
        캐시 삭제

        Args:
            symbol: 심볼 (None이면 전체)
            timeframe: 타임프레임 (None이면 전체)
        """
        if symbol and timeframe:
            # 특정 캐시만 삭제
            cache_file = self._get_cache_file(symbol, timeframe)
            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"🗑️ Deleted cache: {cache_file.name}")

            cache_key = self._get_cache_key(symbol, timeframe)
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            if cache_key in self._metadata["caches"]:
                del self._metadata["caches"][cache_key]
                self._save_metadata()
        else:
            # 전체 캐시 삭제
            for cache_file in self.cache_dir.glob("*.csv"):
                cache_file.unlink()

            self._memory_cache.clear()
            self._memory_cache_timestamps.clear()
            self._metadata["caches"] = {}
            self._save_metadata()

            logger.info("🗑️ Cleared all cache")


# 싱글톤 인스턴스
_cache_manager: Optional[CandleCacheManager] = None


def get_candle_cache() -> CandleCacheManager:
    """캔들 캐시 매니저 인스턴스 반환"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CandleCacheManager()
    return _cache_manager
