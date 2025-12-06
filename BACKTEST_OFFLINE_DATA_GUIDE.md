# 📊 백테스트 오프라인 데이터 관리 가이드

> **작성일**: 2025-12-05  
> **목적**: 백테스트를 다운로드된 캔들 데이터로만 운영하기 위한 시스템 구성 및 데이터 관리 가이드

---

## 📋 목차

1. [현재 시스템 구조](#1-현재-시스템-구조)
2. [오프라인 전용 모드 설정](#2-오프라인-전용-모드-설정)
3. [데이터 다운로드 스크립트](#3-데이터-다운로드-스크립트)
4. [데이터 관리 계획](#4-데이터-관리-계획)
5. [구현 작업 목록](#5-구현-작업-목록)

---

## 1. 현재 시스템 구조

### 1.1 캐시 시스템 현황

| 컴포넌트 | 경로 | 설명 |
|---------|------|------|
| **캐시 매니저** | `backend/src/services/candle_cache.py` | 캔들 데이터 캐싱 클래스 |
| **캐시 디렉토리** | `backend/candle_cache/` | CSV 파일 저장 위치 |
| **메타데이터** | `backend/candle_cache/cache_metadata.json` | 캐시 정보 |

### 1.2 현재 캐시된 데이터

```
backend/candle_cache/
├── BTCUSDT_1h.csv   (약 58KB)
├── BTCUSDT_4h.csv   (약 67KB)
├── BTCUSDT_1d.csv   (약 84KB)
├── ETHUSDT_1h.csv   (약 55KB)
├── ETHUSDT_4h.csv   (약 62KB)
├── ETHUSDT_1d.csv   (약 82KB)
├── SOLUSDT_*.csv    (1h, 4h, 1d)
├── XRPUSDT_*.csv    (1h, 4h, 1d)
├── DOGEUSDT_*.csv   (1h, 4h, 1d)
├── ADAUSDT_*.csv    (1h, 4h, 1d)
├── AVAXUSDT_*.csv   (1h, 4h, 1d)
├── LINKUSDT_*.csv   (1h, 4h, 1d)
├── DOTUSDT_*.csv    (1h, 4h, 1d)
└── cache_metadata.json
```

### 1.3 현재 동작 모드

```python
# backend/src/api/backtest.py:133
candles = await cache_manager.get_candles(
    symbol=pair,
    timeframe=timeframe,
    start_date=start_date,
    end_date=end_date,
    cache_only=True,  # ⚠️ 현재 이미 API 호출 방지 모드
)
```

**현재 설정**: `cache_only=True`로 API 호출 없이 캐시 데이터만 사용

---

## 2. 오프라인 전용 모드 설정

### 2.1 환경변수 추가

`.env` 파일에 추가:

```bash
# 백테스트 데이터 모드
# "offline" = 다운로드된 데이터만 사용 (기본값, 권장)
# "online"  = API 호출 허용 (Rate Limit 주의)
BACKTEST_DATA_MODE=offline

# 캐시 디렉토리 (기본: backend/candle_cache)
CANDLE_CACHE_DIR=./candle_cache
```

### 2.2 config.py 수정

```python
# backend/src/config.py 에 추가

class BacktestConfig:
    """백테스트 설정"""
    
    # 데이터 모드
    DATA_MODE = os.getenv("BACKTEST_DATA_MODE", "offline")  # "offline" 또는 "online"
    CACHE_DIR = os.getenv("CANDLE_CACHE_DIR", "./candle_cache")
    
    # 오프라인 전용 모드
    CACHE_ONLY = DATA_MODE == "offline"
    
    # 기본값
    DEFAULT_INITIAL_BALANCE = 10000.0
    DEFAULT_FEE_RATE = 0.001  # 0.1%
    DEFAULT_SLIPPAGE = 0.0005  # 0.05%
```

### 2.3 backtest.py 수정

```python
# backend/src/api/backtest.py

from ..config import BacktestConfig

# ... 

candles = await cache_manager.get_candles(
    symbol=pair,
    timeframe=timeframe,
    start_date=start_date,
    end_date=end_date,
    cache_only=BacktestConfig.CACHE_ONLY,  # 환경변수로 제어
)

# 오프라인 모드에서 데이터 없으면 에러
if BacktestConfig.CACHE_ONLY and not candles:
    raise HTTPException(
        status_code=400,
        detail=f"해당 기간의 데이터가 없습니다. 현재 오프라인 모드입니다. "
               f"사용 가능한 데이터 범위를 확인하세요. "
               f"({pair} {timeframe})"
    )
```

---

## 3. 데이터 다운로드 스크립트

### 3.1 새 스크립트 생성: `backend/scripts/download_candle_data.py`

```python
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
import os
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.candle_cache import CandleCacheManager
from src.services.bitget_rest import BitgetRestClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 지원하는 심볼 및 타임프레임
ALL_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "MATICUSDT"
]

ALL_TIMEFRAMES = ["1h", "4h", "1d"]

# 확장 타임프레임 (필요시)
EXTENDED_TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h", "1d"]


async def download_symbol_data(
    cache_manager: CandleCacheManager,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    delay: float = 2.0
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
            cache_only=False  # API 호출 허용
        )
        
        if candles:
            logger.info(f"   ✅ Downloaded {len(candles)} candles")
            await asyncio.sleep(delay)  # Rate Limit 방지
            return True
        else:
            logger.warning(f"   ⚠️ No data returned")
            return False
            
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        await asyncio.sleep(delay * 2)  # 에러 시 더 길게 대기
        return False


async def download_all_data(
    symbols: list,
    timeframes: list,
    years: int = 3,
    delay: float = 2.0
):
    """
    모든 심볼/타임프레임 데이터 다운로드
    
    Args:
        symbols: 심볼 리스트
        timeframes: 타임프레임 리스트
        years: 다운로드할 과거 연도 수
        delay: API 호출 간 대기 시간 (초)
    """
    cache_manager = CandleCacheManager()
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    
    total = len(symbols) * len(timeframes)
    completed = 0
    failed = []
    
    logger.info(f"🚀 Starting download: {len(symbols)} symbols × {len(timeframes)} timeframes")
    logger.info(f"📅 Date range: {start_date} ~ {end_date} ({years} years)")
    logger.info(f"⏱️ Estimated time: ~{total * delay / 60:.1f} minutes")
    logger.info("-" * 50)
    
    for symbol in symbols:
        for timeframe in timeframes:
            success = await download_symbol_data(
                cache_manager, symbol, timeframe,
                start_date, end_date, delay
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
    logger.info(f"\n📊 Cache Summary:")
    logger.info(f"   Total files: {info['total_files']}")
    for name, meta in info['caches'].items():
        logger.info(f"   - {name}: {meta.get('size_mb', 'N/A')} MB, {meta.get('count', 'N/A')} candles")


def main():
    parser = argparse.ArgumentParser(description="캔들 데이터 다운로드")
    parser.add_argument("--symbols", type=str, default=None,
                        help="심볼 리스트 (쉼표 구분, 예: BTCUSDT,ETHUSDT)")
    parser.add_argument("--timeframes", type=str, default=None,
                        help="타임프레임 리스트 (쉼표 구분, 예: 1h,4h,1d)")
    parser.add_argument("--years", type=int, default=3,
                        help="다운로드할 과거 연도 수 (기본: 3)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="API 호출 간 대기 시간 초 (기본: 2.0)")
    parser.add_argument("--all", action="store_true",
                        help="모든 심볼 및 타임프레임 다운로드")
    parser.add_argument("--extended", action="store_true",
                        help="확장 타임프레임 포함 (5m, 15m, 30m 포함)")
    
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
    asyncio.run(download_all_data(
        symbols=symbols,
        timeframes=timeframes,
        years=args.years,
        delay=args.delay
    ))


if __name__ == "__main__":
    main()
```

### 3.2 사용 방법

```bash
# 가상환경 활성화
cd backend
source venv/bin/activate

# 1. 기본 다운로드 (BTC, ETH / 1h, 4h, 1d / 3년)
python scripts/download_candle_data.py

# 2. 전체 심볼 다운로드 (10개 심볼 × 3개 타임프레임 × 3년)
python scripts/download_candle_data.py --all --years 3

# 3. 특정 심볼만
python scripts/download_candle_data.py --symbols BTCUSDT,ETHUSDT,SOLUSDT --years 3

# 4. 확장 타임프레임 포함 (5m, 15m도 다운로드)
python scripts/download_candle_data.py --all --extended --years 3

# 5. Rate Limit 안전하게 (10초 간격)
python scripts/download_candle_data.py --all --delay 10
```

---

## 4. 데이터 관리 계획

### 4.1 데이터 범위

| 구분 | 값 |
|------|-----|
| **시작일** | 2021-12-05 (3년 전) |
| **종료일** | 2024-12-05 (현재) |
| **업데이트 주기** | 15일 또는 1개월 |

### 4.2 심볼 목록 (10개)

| 심볼 | 설명 | 우선순위 |
|------|------|----------|
| BTCUSDT | 비트코인 | ⭐⭐⭐ |
| ETHUSDT | 이더리움 | ⭐⭐⭐ |
| SOLUSDT | 솔라나 | ⭐⭐⭐ |
| XRPUSDT | 리플 | ⭐⭐ |
| DOGEUSDT | 도지코인 | ⭐⭐ |
| ADAUSDT | 에이다 | ⭐⭐ |
| AVAXUSDT | 아발란체 | ⭐⭐ |
| LINKUSDT | 체인링크 | ⭐ |
| DOTUSDT | 폴카닷 | ⭐ |
| MATICUSDT | 폴리곤 | ⭐ |

### 4.3 타임프레임 (3개 기본 + 3개 확장)

| 타임프레임 | 3년치 예상 캔들 수 | 파일 크기 예상 |
|-----------|-------------------|----------------|
| **1h** (기본) | 26,280 | ~1.5MB |
| **4h** (기본) | 6,570 | ~400KB |
| **1d** (기본) | 1,095 | ~70KB |
| 5m (확장) | 315,360 | ~18MB |
| 15m (확장) | 105,120 | ~6MB |
| 30m (확장) | 52,560 | ~3MB |

### 4.4 전체 용량 예상

```
기본 (10심볼 × 3타임프레임 × 3년):
  - 총 파일: 30개
  - 총 용량: ~60MB

확장 포함 (10심볼 × 6타임프레임 × 3년):
  - 총 파일: 60개
  - 총 용량: ~300MB
```

### 4.5 데이터 업데이트 일정

```
# crontab 설정 예시

# 매월 1일 새벽 2시에 전체 업데이트
0 2 1 * * cd /path/to/backend && /path/to/venv/bin/python scripts/download_candle_data.py --all --years 3 >> /var/log/candle_update.log 2>&1

# 또는 15일마다 (1일, 15일)
0 2 1,15 * * cd /path/to/backend && /path/to/venv/bin/python scripts/download_candle_data.py --all --years 3 >> /var/log/candle_update.log 2>&1
```

---

## 5. 구현 작업 목록

### 5.1 백엔드 수정

| # | 작업 | 파일 | 상태 | 예상 시간 |
|---|------|------|------|----------|
| 1 | 환경변수 추가 | `backend/src/config.py` | ✅ 완료 | 10분 |
| 2 | 다운로드 스크립트 생성 | `backend/scripts/download_candle_data.py` | ✅ 완료 | 30분 |
| 3 | backtest.py 오프라인 에러 처리 | `backend/src/api/backtest.py` | ✅ 완료 | 15분 |
| 4 | 캐시 정보 API 추가 | `backend/src/api/backtest.py` | ✅ 완료 | 20분 |

### 5.2 프론트엔드 수정

| # | 작업 | 파일 | 상태 | 예상 시간 |
|---|------|------|------|----------|
| 5 | 사용 가능한 데이터 범위 표시 | `BacktestingPage.jsx` | ✅ 완료 | 30분 |
| 6 | 데이터 없음 에러 안내 개선 | `BacktestingPage.jsx` | ✅ 완료 | 15분 |

### 5.3 관리자 기능

| # | 작업 | 파일 | 상태 | 예상 시간 |
|---|------|------|------|----------|
| 7 | 캐시 현황 조회 페이지 | `admin-frontend/AdminDashboard.jsx` | ✅ 완료 | 1시간 |
| 8 | 수동 다운로드 트리거 | `admin-frontend/AdminDashboard.jsx` | ✅ 완료 (안내 표시) | 30분 |

### 5.4 데이터 다운로드 실행

| # | 작업 | 명령어 | 예상 시간 |
|---|------|--------|----------|
| 9 | 초기 3년치 데이터 다운로드 | `python scripts/download_candle_data.py --all --years 3` | ~1시간 |
| 10 | crontab 설정 | 월 1회 또는 15일 1회 | 5분 |

---

## 6. API 엔드포인트 추가

### 6.1 캐시 정보 조회 API

```python
# backend/src/api/backtest.py 에 추가

@router.get("/cache/info")
async def get_cache_info():
    """
    백테스트 캐시 정보 조회
    
    사용 가능한 심볼, 타임프레임, 데이터 범위 반환
    """
    from ..services.candle_cache import get_candle_cache
    
    cache_manager = get_candle_cache()
    info = cache_manager.get_cache_info()
    
    # 프론트엔드용 형식으로 변환
    available_data = []
    for cache_key, meta in info.get("caches", {}).items():
        if isinstance(meta, dict) and "start" in meta:
            available_data.append({
                "symbol": meta.get("symbol"),
                "timeframe": meta.get("timeframe"),
                "candle_count": meta.get("count"),
                "start_date": datetime.fromtimestamp(meta["start"] / 1000).strftime("%Y-%m-%d"),
                "end_date": datetime.fromtimestamp(meta["end"] / 1000).strftime("%Y-%m-%d"),
                "size_mb": meta.get("size_mb", 0),
                "updated_at": meta.get("updated_at"),
            })
    
    return {
        "mode": "offline",  # 현재 모드
        "cache_dir": info.get("cache_dir"),
        "total_files": info.get("total_files"),
        "available_data": sorted(available_data, key=lambda x: (x["symbol"], x["timeframe"])),
    }
```

### 6.2 프론트엔드에서 사용

```jsx
// BacktestingPage.jsx 에서 사용 가능한 데이터 범위 표시

const [availableData, setAvailableData] = useState([]);

useEffect(() => {
    const fetchCacheInfo = async () => {
        try {
            const response = await backtestAPI.getCacheInfo();
            setAvailableData(response.available_data || []);
        } catch (error) {
            console.error('Failed to fetch cache info:', error);
        }
    };
    fetchCacheInfo();
}, []);

// 선택한 심볼/타임프레임의 데이터 범위 표시
const selectedData = availableData.find(
    d => d.symbol === selectedSymbol && d.timeframe === selectedTimeframe
);

{selectedData && (
    <Alert
        message={`사용 가능한 데이터: ${selectedData.start_date} ~ ${selectedData.end_date}`}
        type="info"
        showIcon
    />
)}
```

---

## 📅 실행 일정 권장

| 단계 | 작업 | 예상 일정 |
|------|------|----------|
| **Day 1** | 환경변수 수정, 다운로드 스크립트 생성 | 1시간 |
| **Day 1** | 초기 데이터 다운로드 (3년치) | 1-2시간 |
| **Day 2** | 프론트엔드 데이터 범위 표시 | 1시간 |
| **Day 2** | 테스트 및 검증 | 1시간 |
| **Day 3** | crontab 설정 (자동 업데이트) | 30분 |
| **Day 3** | 관리자 캐시 현황 페이지 (선택) | 2시간 |

---

## ⚠️ 주의사항

1. **API Rate Limit**: Bitget API는 분당 요청 제한이 있으므로 다운로드 시 충분한 딜레이 필요
2. **디스크 용량**: 확장 타임프레임(5m, 15m) 포함 시 약 300MB 필요
3. **백업**: 다운로드된 데이터는 주기적으로 백업 권장
4. **사용자 안내**: 사용 불가능한 기간 선택 시 명확한 에러 메시지 표시

---

이 가이드를 따라 구현하면 API 호출 없이 안정적인 백테스트 서비스가 가능합니다.
