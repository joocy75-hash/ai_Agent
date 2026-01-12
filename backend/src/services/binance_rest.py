"""
Binance REST API 클라이언트
- 캔들(Kline) 데이터 조회 전용 (인증 불필요)
- Binance Futures API 사용

작성일: 2025-12-13
목적: 백테스트용 과거 캔들 데이터 수집

API 문서:
- https://binance-docs.github.io/apidocs/futures/en/#kline-candlestick-data

Rate Limit:
- 1200 requests/min (IP 기준)
- 권장 딜레이: 50-100ms
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class BinanceRestClient:
    """
    Binance Futures REST API 클라이언트 (캔들 데이터 전용)

    특징:
    - 인증 불필요 (Public API)
    - 요청당 최대 1,500개 캔들
    - Rate Limit: 1200 req/min

    사용 예시:
        client = BinanceRestClient()
        candles = await client.get_klines("BTCUSDT", "1h", limit=100)
        await client.close()
    """

    # Binance Futures API 엔드포인트
    BASE_URL = "https://fapi.binance.com"
    KLINES_ENDPOINT = "/fapi/v1/klines"

    # 바이낸스 선물 런칭일 (2019년 9월)
    BINANCE_FUTURES_LAUNCH = "2019-09-01"

    # 타임프레임 매핑 (통일된 형식 → Binance 형식)
    INTERVAL_MAP = {
        # 분봉
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        # 시간봉
        "1h": "1h",
        "1H": "1h",
        "2h": "2h",
        "4h": "4h",
        "4H": "4h",
        "6h": "6h",
        "8h": "8h",
        "12h": "12h",
        # 일봉 이상
        "1d": "1d",
        "1D": "1d",
        "3d": "3d",
        "1w": "1w",
        "1W": "1w",
        "1M": "1M",
    }

    # 타임프레임별 밀리초 간격 (페이지네이션 계산용)
    INTERVAL_MS = {
        "1m": 60 * 1000,
        "3m": 3 * 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "30m": 30 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "2h": 2 * 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "6h": 6 * 60 * 60 * 1000,
        "8h": 8 * 60 * 60 * 1000,
        "12h": 12 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
        "3d": 3 * 24 * 60 * 60 * 1000,
        "1w": 7 * 24 * 60 * 60 * 1000,
    }

    def __init__(self):
        """클라이언트 초기화"""
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_remaining = 1200
        self._rate_limit_reset = 0

    async def _ensure_session(self):
        """aiohttp 세션 생성 (없으면 생성)"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        """세션 종료 (반드시 호출!)"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    def _normalize_interval(self, interval: str) -> str:
        """타임프레임을 Binance 형식으로 변환"""
        return self.INTERVAL_MAP.get(interval, interval.lower())

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1500,
    ) -> List[Dict[str, Any]]:
        """
        캔들(Kline) 데이터 조회 (단일 요청)

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
            interval: 캔들 간격 (1m, 5m, 15m, 30m, 1h, 4h, 1d 등)
            start_time: 시작 시간 (밀리초, 선택)
            end_time: 종료 시간 (밀리초, 선택)
            limit: 조회 개수 (최대 1500)

        Returns:
            캔들 데이터 리스트. 각 캔들은 다음 형식:
            {
                "timestamp": int,  # 시작 시간 (ms)
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": float,
            }

        Raises:
            Exception: API 에러 또는 Rate Limit 초과 시
        """
        await self._ensure_session()

        # 타임프레임 변환
        binance_interval = self._normalize_interval(interval)

        # 파라미터 구성
        params = {
            "symbol": symbol.upper(),
            "interval": binance_interval,
            "limit": min(limit, 1500),
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        url = f"{self.BASE_URL}{self.KLINES_ENDPOINT}"

        try:
            async with self.session.get(url, params=params) as response:
                # Rate Limit 헤더 파싱
                if "X-MBX-USED-WEIGHT-1M" in response.headers:
                    used = int(response.headers["X-MBX-USED-WEIGHT-1M"])
                    self._rate_limit_remaining = 1200 - used

                # Rate Limit 초과
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    logger.warning(
                        f"🚫 Binance Rate Limit 도달. {retry_after}초 후 재시도 필요"
                    )
                    raise Exception(f"Rate Limit Exceeded. Retry after {retry_after}s")

                # 기타 에러
                if response.status != 200:
                    text = await response.text()
                    logger.error(f"Binance API 에러: {response.status} - {text}")
                    raise Exception(f"API Error: {response.status} - {text}")

                data = await response.json()

                # 캔들 데이터 파싱
                # Binance 응답 형식:
                # [시작시간, 시가, 고가, 저가, 종가, 거래량, 종료시간, ...]
                candles = []
                for kline in data:
                    candles.append(
                        {
                            "timestamp": int(kline[0]),
                            "open": float(kline[1]),
                            "high": float(kline[2]),
                            "low": float(kline[3]),
                            "close": float(kline[4]),
                            "volume": float(kline[5]),
                        }
                    )

                logger.debug(
                    f"Binance: {symbol} {interval} - {len(candles)}개 캔들 조회"
                )
                return candles

        except asyncio.TimeoutError as e:
            logger.error(f"Binance API 타임아웃: {symbol} {interval}")
            raise Exception("API Timeout") from e

        except aiohttp.ClientError as e:
            logger.error(f"Binance 네트워크 에러: {e}")
            raise

    async def get_all_historical_klines(
        self,
        symbol: str,
        interval: str = "1h",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        max_candles: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        전체 과거 캔들 데이터 조회 (페이지네이션)

        여러 번의 API 호출로 전체 기간 데이터를 수집합니다.
        Binance는 startTime 기준 오름차순으로 데이터를 반환합니다.

        Args:
            symbol: 거래쌍 (예: BTCUSDT)
            interval: 캔들 간격 (1h, 4h, 1d 등)
            start_time: 시작 날짜 (YYYY-MM-DD), 없으면 Binance Futures 런칭일
            end_time: 종료 날짜 (YYYY-MM-DD), 없으면 현재
            max_candles: 최대 캔들 수 제한 (None이면 무제한)

        Returns:
            캔들 데이터 리스트 (시간순 정렬, 오래된 것부터)

        예시:
            candles = await client.get_all_historical_klines(
                symbol="BTCUSDT",
                interval="1h",
                start_time="2024-01-01",
                end_time="2024-12-01",
            )
        """
        # 시작/종료 시간 설정
        if not start_time:
            start_time = self.BINANCE_FUTURES_LAUNCH

        if not end_time:
            end_time = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 날짜 문자열 → datetime → timestamp (ms)
        start_dt = datetime.strptime(start_time, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        end_dt = datetime.strptime(end_time, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )

        # 미래 날짜 방지
        now_utc = datetime.now(timezone.utc)
        if end_dt > now_utc:
            end_dt = now_utc

        start_ts = int(start_dt.timestamp() * 1000)
        end_ts = int(end_dt.timestamp() * 1000)

        logger.info(f"📊 Binance에서 {symbol} ({interval}) 캔들 수집 시작")
        logger.info(f"   기간: {start_time} ~ {end_time}")

        all_candles = []
        current_start_ts = start_ts
        batch_count = 0
        rate_limit_delay = 0.1  # 100ms 딜레이 (안전)

        while current_start_ts < end_ts:
            batch_count += 1

            try:
                candles = await self.get_klines(
                    symbol=symbol,
                    interval=interval,
                    start_time=current_start_ts,
                    end_time=end_ts,
                    limit=1500,
                )

                if not candles:
                    logger.info(f"   더 이상 데이터 없음 (배치 {batch_count})")
                    break

                # 중복 제거 후 추가
                existing_ts = {c["timestamp"] for c in all_candles}
                new_candles = [c for c in candles if c["timestamp"] not in existing_ts]
                all_candles.extend(new_candles)

                # 진행률 로깅 (10배치마다)
                if batch_count % 10 == 0:
                    logger.info(
                        f"   배치 {batch_count}: {len(all_candles):,}개 수집 완료..."
                    )

                # 다음 배치 시작점 (마지막 캔들 다음)
                latest_ts = max(c["timestamp"] for c in candles)
                current_start_ts = latest_ts + 1

                # 끝에 도달했는지 확인
                if latest_ts >= end_ts:
                    break

                # 최대 캔들 수 체크
                if max_candles and len(all_candles) >= max_candles:
                    logger.info(f"   최대 캔들 수 도달: {max_candles:,}개")
                    all_candles = all_candles[:max_candles]
                    break

                # Rate Limit 방지 딜레이
                await asyncio.sleep(rate_limit_delay)

            except Exception as e:
                logger.error(f"   배치 {batch_count} 에러: {e}")
                # 이미 수집한 데이터는 반환
                if "Rate Limit" in str(e):
                    logger.warning("   Rate Limit 도달. 수집된 데이터 반환...")
                break

        # 시간순 정렬 (오래된 것부터)
        all_candles.sort(key=lambda x: x["timestamp"])

        # 지정된 기간 외 데이터 필터링
        all_candles = [c for c in all_candles if start_ts <= c["timestamp"] <= end_ts]

        logger.info(
            f"✅ 총 {len(all_candles):,}개 캔들 수집 완료 ({batch_count}회 API 호출)"
        )

        return all_candles

    async def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        거래소 정보 조회 (심볼 목록, 거래 규칙 등)

        Args:
            symbol: 특정 심볼만 조회 (선택)

        Returns:
            거래소 정보 딕셔너리
        """
        await self._ensure_session()

        url = f"{self.BASE_URL}/fapi/v1/exchangeInfo"

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"API Error: {response.status}")

                data = await response.json()

                if symbol:
                    # 특정 심볼 필터링
                    symbols = [
                        s
                        for s in data.get("symbols", [])
                        if s["symbol"] == symbol.upper()
                    ]
                    return {"symbols": symbols}

                return data

        except Exception as e:
            logger.error(f"Exchange info 조회 실패: {e}")
            raise

    async def get_server_time(self) -> int:
        """
        Binance 서버 시간 조회

        Returns:
            서버 시간 (밀리초)
        """
        await self._ensure_session()

        url = f"{self.BASE_URL}/fapi/v1/time"

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"API Error: {response.status}")

                data = await response.json()
                return data.get("serverTime", 0)

        except Exception as e:
            logger.error(f"서버 시간 조회 실패: {e}")
            raise


# =====================================================
# 편의 함수
# =====================================================


async def download_candles(
    symbol: str,
    interval: str,
    start_time: str,
    end_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    캔들 데이터 다운로드 (편의 함수)

    사용 예시:
        candles = await download_candles("BTCUSDT", "1h", "2024-01-01", "2024-12-01")
    """
    client = BinanceRestClient()
    try:
        candles = await client.get_all_historical_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
        )
        return candles
    finally:
        await client.close()


# =====================================================
# 테스트용 코드
# =====================================================

if __name__ == "__main__":

    async def test():
        """간단한 테스트"""
        print("🧪 Binance REST 클라이언트 테스트")
        print("=" * 50)

        client = BinanceRestClient()

        try:
            # 1. 서버 시간 확인
            server_time = await client.get_server_time()
            print(f"✅ 서버 시간: {datetime.fromtimestamp(server_time / 1000)}")

            # 2. 단일 요청 테스트
            candles = await client.get_klines("BTCUSDT", "1h", limit=10)
            print(f"✅ 단일 요청: {len(candles)}개 캔들")
            if candles:
                c = candles[0]
                print(
                    f"   첫 캔들: {datetime.fromtimestamp(c['timestamp'] / 1000)} - O:{c['open']:.2f} H:{c['high']:.2f} L:{c['low']:.2f} C:{c['close']:.2f}"
                )

            # 3. 히스토리 테스트 (최근 7일)
            print("\n📥 최근 7일 데이터 다운로드...")
            from datetime import timedelta

            end = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            history = await client.get_all_historical_klines(
                symbol="BTCUSDT",
                interval="1h",
                start_time=start,
                end_time=end,
            )
            print(f"✅ 히스토리: {len(history)}개 캔들 ({start} ~ {end})")

        finally:
            await client.close()

        print("\n" + "=" * 50)
        print("✅ 모든 테스트 통과!")

    asyncio.run(test())
