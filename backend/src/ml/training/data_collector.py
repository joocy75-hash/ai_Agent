"""
Data Collector - 학습용 캔들 데이터 수집

Bitget API를 통해 과거 캔들 데이터를 수집하고 저장
"""

import logging
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class DataCollector:
    """
    캔들 데이터 수집기

    Usage:
    ```python
    collector = DataCollector()
    await collector.collect_historical(
        symbol="ETHUSDT",
        timeframe="5m",
        days=30
    )
    ```
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        bitget_client: Optional[Any] = None
    ):
        self.data_dir = data_dir or Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.bitget_client = bitget_client

        logger.info(f"DataCollector initialized, data_dir: {self.data_dir}")

    def set_client(self, client: Any):
        """Bitget 클라이언트 설정"""
        self.bitget_client = client

    async def collect_historical(
        self,
        symbol: str = "ETHUSDT",
        timeframe: str = "5m",
        days: int = 30,
        save: bool = True
    ) -> pd.DataFrame:
        """
        과거 캔들 데이터 수집

        Args:
            symbol: 심볼 (예: ETHUSDT)
            timeframe: 타임프레임 (5m, 15m, 1h, 4h)
            days: 수집할 일수
            save: 파일로 저장 여부

        Returns:
            캔들 데이터 DataFrame
        """
        if self.bitget_client is None:
            logger.warning("Bitget client not set, returning empty DataFrame")
            return pd.DataFrame()

        try:
            all_candles = []
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)

            # 타임프레임별 캔들 개수 계산
            candles_per_request = 200
            minutes_per_candle = self._timeframe_to_minutes(timeframe)
            total_candles = (days * 24 * 60) // minutes_per_candle

            logger.info(f"Collecting {total_candles} candles for {symbol} ({timeframe})")

            current_end = end_time
            collected = 0

            while collected < total_candles:
                # API 호출
                candles = await self._fetch_candles(
                    symbol=symbol,
                    timeframe=timeframe,
                    end_time=current_end,
                    limit=candles_per_request
                )

                if not candles:
                    break

                all_candles.extend(candles)
                collected += len(candles)

                # 다음 요청 시간 설정
                oldest_ts = min(c.get('timestamp', 0) for c in candles)
                current_end = datetime.fromtimestamp(oldest_ts / 1000) - timedelta(seconds=1)

                # Rate limit
                await asyncio.sleep(0.2)

                if collected >= total_candles:
                    break

            # DataFrame 변환
            df = self._to_dataframe(all_candles)

            # 시간순 정렬
            if not df.empty:
                df = df.sort_index()

            logger.info(f"Collected {len(df)} candles")

            # 저장
            if save and not df.empty:
                self._save_data(df, symbol, timeframe)

            return df

        except Exception as e:
            logger.error(f"Data collection failed: {e}", exc_info=True)
            return pd.DataFrame()

    async def _fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        end_time: datetime,
        limit: int = 200
    ) -> List[Dict]:
        """API로 캔들 가져오기"""
        try:
            # Bitget API 호출 (클라이언트 메서드에 맞게 조정 필요)
            if hasattr(self.bitget_client, 'get_candles'):
                return await self.bitget_client.get_candles(
                    symbol=symbol,
                    granularity=timeframe,
                    end_time=int(end_time.timestamp() * 1000),
                    limit=limit
                )
            elif hasattr(self.bitget_client, 'fetch_ohlcv'):
                # CCXT 스타일
                since = int((end_time - timedelta(minutes=limit * self._timeframe_to_minutes(timeframe))).timestamp() * 1000)
                ohlcv = await self.bitget_client.fetch_ohlcv(symbol, timeframe, since, limit)
                return [
                    {
                        'timestamp': c[0],
                        'open': c[1],
                        'high': c[2],
                        'low': c[3],
                        'close': c[4],
                        'volume': c[5]
                    }
                    for c in ohlcv
                ]
            else:
                logger.warning("Unknown client type")
                return []
        except Exception as e:
            logger.error(f"Fetch candles error: {e}")
            return []

    def _to_dataframe(self, candles: List[Dict]) -> pd.DataFrame:
        """캔들 리스트 → DataFrame"""
        if not candles:
            return pd.DataFrame()

        df = pd.DataFrame(candles)

        # 컬럼 정규화
        column_mapping = {
            'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume',
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
        }
        df = df.rename(columns=column_mapping)

        # 숫자 변환
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # timestamp 인덱스
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
            df = df.set_index('timestamp')

        return df

    def _save_data(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """데이터 저장"""
        filename = f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d')}.parquet"
        filepath = self.data_dir / filename

        df.to_parquet(filepath)
        logger.info(f"Data saved to {filepath}")

    def load_data(self, symbol: str, timeframe: str, date: str = None) -> pd.DataFrame:
        """저장된 데이터 로드"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        filepath = self.data_dir / f"{symbol}_{timeframe}_{date}.parquet"

        if filepath.exists():
            return pd.read_parquet(filepath)
        else:
            logger.warning(f"Data file not found: {filepath}")
            return pd.DataFrame()

    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """타임프레임 → 분 변환"""
        mapping = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        return mapping.get(timeframe, 5)

    def get_available_data(self) -> List[str]:
        """사용 가능한 데이터 파일 목록"""
        return [f.name for f in self.data_dir.glob("*.parquet")]

    async def fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict]:
        """
        Fetch candles from exchange API

        Args:
            symbol: Trading pair (e.g., ETHUSDT)
            timeframe: Candle timeframe (5m, 1h, etc.)
            start_time: Start datetime
            end_time: End datetime

        Returns:
            List of candle dictionaries
        """
        try:
            # Try to use aiohttp if no client set
            if self.bitget_client is None:
                return await self._fetch_from_public_api(symbol, timeframe, start_time, end_time)

            # Use client if available
            all_candles = []
            current_end = end_time
            minutes_per_candle = self._timeframe_to_minutes(timeframe)
            total_candles = int((end_time - start_time).total_seconds() / 60 / minutes_per_candle)
            collected = 0
            candles_per_request = 200

            while collected < total_candles:
                candles = await self._fetch_candles(
                    symbol=symbol,
                    timeframe=timeframe,
                    end_time=current_end,
                    limit=candles_per_request
                )

                if not candles:
                    break

                all_candles.extend(candles)
                collected += len(candles)

                oldest_ts = min(c.get('timestamp', 0) for c in candles)
                current_end = datetime.fromtimestamp(oldest_ts / 1000) - timedelta(seconds=1)

                await asyncio.sleep(0.2)

            return all_candles

        except Exception as e:
            logger.error(f"fetch_candles failed: {e}", exc_info=True)
            return []

    async def _fetch_from_public_api(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict]:
        """Fetch from Bitget public API using aiohttp"""
        try:
            import aiohttp

            all_candles = []
            minutes_per_candle = self._timeframe_to_minutes(timeframe)
            granularity_map = {'5m': '5m', '15m': '15m', '1h': '1H', '4h': '4H', '1d': '1D'}
            granularity = granularity_map.get(timeframe, '5m')

            current_end = int(end_time.timestamp() * 1000)
            start_ms = int(start_time.timestamp() * 1000)

            async with aiohttp.ClientSession() as session:
                while current_end > start_ms:
                    url = f"https://api.bitget.com/api/v2/mix/market/candles"
                    params = {
                        'symbol': symbol,
                        'productType': 'USDT-FUTURES',
                        'granularity': granularity,
                        'endTime': str(current_end),
                        'limit': '200'
                    }

                    async with session.get(url, params=params) as resp:
                        if resp.status != 200:
                            logger.warning(f"API error: {resp.status}")
                            break

                        data = await resp.json()
                        candles_data = data.get('data', [])

                        if not candles_data:
                            break

                        for c in candles_data:
                            all_candles.append({
                                'timestamp': int(c[0]),
                                'open': float(c[1]),
                                'high': float(c[2]),
                                'low': float(c[3]),
                                'close': float(c[4]),
                                'volume': float(c[5])
                            })

                        current_end = int(candles_data[-1][0]) - 1

                    await asyncio.sleep(0.3)

            logger.info(f"Fetched {len(all_candles)} candles from public API")
            return all_candles

        except ImportError:
            logger.error("aiohttp not installed. Run: pip install aiohttp")
            return []
        except Exception as e:
            logger.error(f"Public API fetch failed: {e}", exc_info=True)
            return []
