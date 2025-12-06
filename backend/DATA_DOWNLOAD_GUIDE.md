# 📊 백테스트 데이터 다운로드 가이드

백테스트를 위한 과거 캔들 데이터를 다운로드하고 관리하는 방법입니다.

---

## 📁 데이터 저장 위치

```
backend/candle_cache/
├── BTCUSDT_1h.csv
├── BTCUSDT_4h.csv
├── BTCUSDT_1d.csv
├── ETHUSDT_1h.csv
├── ...
└── cache_metadata.json  # 캐시 정보
```

---

## 🚀 다운로드 방법

### 방법 1: 전체 다운로드 스크립트 (권장)

#### BTC, ETH, XRP, SOL 다운로드

```bash
cd backend
python3 download_btc_eth.py
```

#### 추가 코인 다운로드 (DOGE, ADA, AVAX 등)

```bash
cd backend
python3 download_more_coins.py
```

#### 모든 메이저 코인 한번에 다운로드

```bash
cd backend
python3 download_historical_data.py
```

---

### 방법 2: 특정 코인만 다운로드

Python 코드로 원하는 코인만 다운로드:

```python
import asyncio
from src.services.candle_cache import CandleCacheManager

async def download_specific():
    cache = CandleCacheManager()
    
    # 원하는 설정
    symbol = "BNBUSDT"        # 거래쌍
    timeframe = "1h"          # 1m, 5m, 15m, 1h, 4h, 1d
    start_date = "2024-01-01" # 시작일
    end_date = "2024-12-04"   # 종료일
    
    candles = await cache.get_candles(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"✅ Downloaded {len(candles)} candles for {symbol} {timeframe}")

asyncio.run(download_specific())
```

저장: `backend/download_custom.py`로 저장 후 실행

---

### 방법 3: API로 프리로드

백엔드 서버가 실행 중일 때:

```bash
# JWT 토큰 필요
curl -X POST "http://localhost:8000/backtest/cache/preload" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 📋 지원하는 심볼

| 티커 | 심볼 | 상장일 (Bitget) |
|------|------|----------------|
| 비트코인 | BTCUSDT | 2020-07-01 |
| 이더리움 | ETHUSDT | 2020-07-01 |
| 리플 | XRPUSDT | 2020-12-01 |
| 솔라나 | SOLUSDT | 2021-06-01 |
| 도지코인 | DOGEUSDT | 2021-02-01 |
| 카르다노 | ADAUSDT | 2021-03-01 |
| 아발란체 | AVAXUSDT | 2021-09-01 |
| 체인링크 | LINKUSDT | 2021-01-01 |
| 폴카닷 | DOTUSDT | 2021-01-01 |
| 폴리곤 | MATICUSDT | 2021-05-01 |

---

## ⏱️ 타임프레임별 데이터 제한

| 타임프레임 | API 최대 반환 | 대략적 기간 |
|-----------|--------------|------------|
| 1m | 1,000개 | 약 16시간 |
| 5m | 1,000개 | 약 3.5일 |
| 15m | 1,000개 | 약 10일 |
| 1h | 1,000개 | 약 42일 |
| 4h | 1,000개 | 약 6개월 |
| 1d | 1,000개 | 약 3년 |

> ⚠️ Bitget API는 한 번의 요청에 최대 1,000개 캔들만 반환합니다.
> 더 많은 데이터가 필요하면 여러 번 요청해야 합니다.

---

## 🔄 정기 업데이트 (권장)

### 매주 한 번 데이터 업데이트

```bash
cd backend
python3 download_btc_eth.py
```

### 자동화 (cron job 예시)

```bash
# 매주 일요일 새벽 3시에 실행
0 3 * * 0 cd /path/to/auto-dashboard/backend && python3 download_btc_eth.py >> /var/log/data_download.log 2>&1
```

---

## ⚠️ 주의사항

### 429 Too Many Requests 오류

**원인**: Bitget API Rate Limit 초과

**해결 방법**:

1. 1-2분 대기 후 재시도
2. 스크립트의 `asyncio.sleep()` 간격 증가 (3초 → 5초)
3. 한 번에 너무 많은 심볼 요청하지 않기

### 데이터 누락

**원인**: 해당 기간에 거래소에 데이터가 없음 (상장 전)

**해결**: 코인별 상장일 이후부터 다운로드

---

## 📊 캐시 확인

### 현재 캐시 상태 확인

```bash
cat backend/candle_cache/cache_metadata.json | python3 -m json.tool
```

### 캐시 파일 목록

```bash
ls -la backend/candle_cache/
```

### 특정 파일 데이터 개수 확인

```bash
wc -l backend/candle_cache/BTCUSDT_1d.csv
```

---

## 🗑️ 캐시 초기화

캐시를 완전히 삭제하고 다시 다운로드:

```bash
rm -rf backend/candle_cache/*.csv
rm -f backend/candle_cache/cache_metadata.json
```

---

## 📝 커스텀 다운로드 스크립트 템플릿

새로운 코인을 추가하려면:

```python
#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.services.candle_cache import CandleCacheManager

# 다운로드할 코인 설정
COINS = [
    ("PEPEUSDT", "2023-05-01"),   # 페페
    ("SHIBUSDT", "2021-05-01"),   # 시바이누
    # 추가하려는 코인...
]

TIMEFRAMES = ["1h", "4h", "1d"]

async def main():
    cache = CandleCacheManager()
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    for symbol, start_date in COINS:
        print(f"\n🚀 {symbol} 다운로드 중...")
        
        for tf in TIMEFRAMES:
            try:
                candles = await cache.get_candles(symbol, tf, start_date, end_date)
                print(f"   ✅ {tf}: {len(candles)}개")
            except Exception as e:
                print(f"   ❌ {tf}: {e}")
            
            await asyncio.sleep(3)  # Rate Limit 방지
        
        await asyncio.sleep(5)

asyncio.run(main())
```

---

## 💡 팁

1. **백테스트 전 데이터 확인**: 원하는 기간의 데이터가 있는지 먼저 확인
2. **정기적 업데이트**: 최신 데이터로 백테스트하려면 주기적으로 다운로드
3. **디스크 용량**: 1분봉은 파일이 클 수 있으므로 필요한 타임프레임만 다운로드
4. **백업**: 중요한 데이터는 별도로 백업해두기

---

*마지막 업데이트: 2025-12-04*
