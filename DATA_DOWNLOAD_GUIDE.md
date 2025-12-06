# 📥 캔들 데이터 다운로드 완벽 가이드

> **작성일**: 2025-12-05  
> **대상**: 다음 작업자  
> **목적**: 백테스트용 OHLCV 캔들 데이터 다운로드 및 캐시 구축

---

## 📋 목차

1. [개요](#1-개요)
2. [사전 준비](#2-사전-준비)
3. [다운로드 실행](#3-다운로드-실행)
4. [다운로드 옵션 상세](#4-다운로드-옵션-상세)
5. [오류 해결 가이드](#5-오류-해결-가이드)
6. [확인 및 검증](#6-확인-및-검증)
7. [유지보수](#7-유지보수)
8. [FAQ](#8-faq)

---

## 1. 개요

### 목적

백테스트가 외부 API 호출 없이 **오프라인 캐시 데이터만** 사용하도록 구성합니다.

### 다운로드 대상

| 항목 | 설명 |
|------|------|
| **데이터 유형** | OHLCV (시가, 고가, 저가, 종가, 거래량) |
| **거래소** | Bitget (CCXT 라이브러리 사용) |
| **기간** | 최대 3년 (권장) |
| **심볼** | BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT 등 8개 |
| **타임프레임** | 1m, 5m, 15m, 1h, 4h, 1d |

### 저장 위치

```
backend/cache/candles/
├── BTCUSDT_1h.csv
├── BTCUSDT_4h.csv
├── ETHUSDT_1h.csv
└── ...
```

### CSV 파일 형식

```csv
timestamp,open,high,low,close,volume
1762268400000,104460.3,104799.9,103144.0,103159.9,4170.8809
```

---

## 2. 사전 준비

### 2.1 필수 환경

```bash
# Python 버전 확인 (3.9 이상 필요)
python3 --version
# 예: Python 3.11.x

# pip 버전 확인
pip3 --version
```

### 2.2 필수 패키지 설치

```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend

# 가상환경 활성화 (있는 경우)
source venv/bin/activate

# 필수 패키지 설치
pip install ccxt aiofiles

# 설치 확인
python3 -c "import ccxt; print('ccxt 버전:', ccxt.__version__)"
```

### 2.3 네트워크 확인

```bash
# Bitget API 접속 테스트
curl -s "https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES" | head -100

# 성공 시 JSON 데이터가 출력됨
```

### 2.4 디스크 공간 확인

```bash
# 예상 용량: 약 500MB~1GB (3년치 전체 데이터)
df -h .
```

---

## 3. 다운로드 실행

### 3.1 기본 실행 (권장)

```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend

# 전체 심볼 3년치 다운로드
python scripts/download_candle_data.py --all --years 3 --delay 0.3
```

**예상 소요 시간**: 1~2시간

### 3.2 빠른 테스트용 (주요 심볼만)

```bash
# BTC, ETH만 1년치 다운로드 (약 15분)
python scripts/download_candle_data.py \
    --symbols BTCUSDT ETHUSDT \
    --timeframes 1h 4h 1d \
    --years 1 \
    --delay 0.2
```

### 3.3 단일 심볼 다운로드

```bash
# 특정 심볼만 다운로드
python scripts/download_candle_data.py \
    --symbols BTCUSDT \
    --timeframes 1h \
    --years 1
```

### 3.4 백그라운드 실행 (터미널 종료해도 계속)

```bash
# nohup으로 백그라운드 실행
nohup python scripts/download_candle_data.py --all --years 3 --delay 0.3 > download.log 2>&1 &

# 진행 상황 확인
tail -f download.log

# 프로세스 확인
ps aux | grep download_candle
```

---

## 4. 다운로드 옵션 상세

### 4.1 명령어 옵션

| 옵션 | 설명 | 기본값 | 예시 |
|------|------|--------|------|
| `--symbols` | 다운로드할 심볼 | - | `--symbols BTCUSDT ETHUSDT` |
| `--timeframes` | 타임프레임 | - | `--timeframes 1h 4h 1d` |
| `--years` | 다운로드 기간 (년) | 3 | `--years 2` |
| `--delay` | API 호출 간 딜레이 (초) | 0.2 | `--delay 0.5` |
| `--all` | 모든 심볼 다운로드 | False | `--all` |
| `--extended` | 확장 타임프레임 포함 | False | `--extended` |

### 4.2 지원 심볼

```python
DEFAULT_SYMBOLS = [
    "BTCUSDT",   # 비트코인
    "ETHUSDT",   # 이더리움
    "SOLUSDT",   # 솔라나
    "XRPUSDT",   # 리플
    "DOGEUSDT",  # 도지코인
    "ADAUSDT",   # 카르다노
    "AVAXUSDT",  # 아발란체
    "DOTUSDT",   # 폴카닷
]
```

### 4.3 지원 타임프레임

```python
# 기본 타임프레임
DEFAULT_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

# 확장 타임프레임 (--extended 옵션)
EXTENDED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"]
```

---

## 5. 오류 해결 가이드

### 5.1 Rate Limit 오류 (429)

**증상**:

```
Error: 429 Too Many Requests
ccxt.base.errors.RateLimitExceeded
```

**원인**: API 호출이 너무 빠름

**해결 방법**:

```bash
# 딜레이 증가
python scripts/download_candle_data.py --all --years 3 --delay 0.5

# 또는 더 느리게
python scripts/download_candle_data.py --all --years 3 --delay 1.0
```

**스크립트 자동 대응**:

- 429 오류 시 자동으로 30초 대기 후 재시도
- 3회 실패 시 해당 심볼 건너뛰고 계속 진행

---

### 5.2 네트워크 오류

**증상**:

```
ConnectionError: HTTPSConnectionPool
TimeoutError: The read operation timed out
```

**해결 방법**:

```bash
# 1. 인터넷 연결 확인
ping api.bitget.com

# 2. DNS 확인
nslookup api.bitget.com

# 3. VPN 사용 중이면 끄기

# 4. 다시 시도
python scripts/download_candle_data.py --all --years 3 --delay 0.5
```

---

### 5.3 디스크 공간 부족

**증상**:

```
OSError: [Errno 28] No space left on device
```

**해결 방법**:

```bash
# 1. 디스크 공간 확인
df -h .

# 2. 불필요한 파일 삭제
rm -rf backend/backtest_data/*.csv

# 3. 최소 1GB 공간 확보 후 다시 시도
```

---

### 5.4 Python 모듈 오류

**증상**:

```
ModuleNotFoundError: No module named 'ccxt'
```

**해결 방법**:

```bash
# 1. 가상환경 확인
which python3

# 2. 패키지 설치
pip install ccxt aiofiles

# 3. 설치 확인
pip list | grep ccxt
```

---

### 5.5 권한 오류

**증상**:

```
PermissionError: [Errno 13] Permission denied
```

**해결 방법**:

```bash
# 캐시 디렉토리 권한 설정
chmod -R 755 backend/cache/
mkdir -p backend/cache/candles
chmod 755 backend/cache/candles
```

---

### 5.6 심볼 없음 오류

**증상**:

```
BadSymbol: bitget does not have market symbol XXXUSDT
```

**해결 방법**:

```bash
# 해당 심볼 제외하고 다운로드
python scripts/download_candle_data.py \
    --symbols BTCUSDT ETHUSDT SOLUSDT \
    --years 3
```

---

### 5.7 중간에 중단된 경우

**증상**: 다운로드 중 터미널 종료 등으로 중단

**해결 방법**:

```bash
# 이미 다운로드된 파일 확인
ls -la backend/cache/candles/

# 없는 심볼만 다시 다운로드
python scripts/download_candle_data.py \
    --symbols SOLUSDT XRPUSDT \
    --years 3
```

**참고**: 스크립트는 기존 파일을 덮어쓰므로, 처음부터 다시 실행해도 됩니다.

---

## 6. 확인 및 검증

### 6.1 다운로드 결과 확인

```bash
# 캐시 폴더 확인
ls -la backend/cache/candles/

# 예상 출력:
# -rw-r--r--  1 user  staff  15234567 Dec  5 15:00 BTCUSDT_1h.csv
# -rw-r--r--  1 user  staff  23456789 Dec  5 15:00 BTCUSDT_4h.csv
# ...
```

### 6.2 파일 크기 확인

```bash
# 전체 크기
du -sh backend/cache/candles/

# 파일별 크기
du -h backend/cache/candles/*.csv | sort -h
```

### 6.3 데이터 무결성 확인

```bash
# CSV 파일 구조 확인
head -5 backend/cache/candles/BTCUSDT_1h.csv

# 예상 출력:
# timestamp,open,high,low,close,volume
# 1609459200000,29000.5,29100.0,28900.0,29050.0,1234.56
```

### 6.4 캔들 수 확인

```bash
# 각 파일의 캔들 수 확인
for f in backend/cache/candles/*.csv; do
    count=$(wc -l < "$f")
    echo "$(basename $f): $((count - 1)) 캔들"
done
```

**예상 캔들 수 (3년 기준)**:

| 타임프레임 | 예상 캔들 수 |
|------------|-------------|
| 1m | ~1,576,800 |
| 5m | ~315,360 |
| 15m | ~105,120 |
| 1h | ~26,280 |
| 4h | ~6,570 |
| 1d | ~1,095 |

### 6.5 날짜 범위 확인

```bash
python3 << 'EOF'
import csv
from datetime import datetime

file_path = "backend/cache/candles/BTCUSDT_1h.csv"
with open(file_path, 'r') as f:
    reader = csv.reader(f)
    next(reader)  # 헤더 스킵
    rows = list(reader)
    
    first = datetime.fromtimestamp(int(rows[0][0]) / 1000)
    last = datetime.fromtimestamp(int(rows[-1][0]) / 1000)
    
    print(f"시작: {first}")
    print(f"종료: {last}")
    print(f"기간: {(last - first).days}일")
    print(f"캔들 수: {len(rows)}")
EOF
```

---

## 7. 유지보수

### 7.1 정기 업데이트 (권장: 월 1회)

```bash
# 매월 1일에 실행
cd /Users/mr.joo/Desktop/auto-dashboard/backend
python scripts/download_candle_data.py --all --years 3 --delay 0.3
```

### 7.2 crontab 자동화 (선택)

```bash
# crontab 편집
crontab -e

# 매월 1일 새벽 3시 실행
0 3 1 * * cd /Users/mr.joo/Desktop/auto-dashboard/backend && python scripts/download_candle_data.py --all --years 3 >> /tmp/candle_download.log 2>&1
```

### 7.3 오래된 데이터 정리 (필요 시)

```bash
# 캐시 폴더 전체 삭제 후 새로 다운로드
rm -rf backend/cache/candles/*
python scripts/download_candle_data.py --all --years 3
```

---

## 8. FAQ

### Q1. 다운로드 시간이 너무 오래 걸려요

**A**: 정상입니다. 3년치 전체 데이터는 1~2시간 소요됩니다.

- 빠른 테스트: `--years 1`로 1년치만 다운로드
- 주요 심볼만: `--symbols BTCUSDT ETHUSDT`

### Q2. 어떤 타임프레임을 다운로드해야 하나요?

**A**: 백테스트에서 가장 많이 사용하는 타임프레임:

- **필수**: 1h, 4h, 1d
- **권장**: 5m, 15m 추가
- **고급**: 1m (파일 크기 매우 큼)

### Q3. 다운로드 중간에 끊겼어요

**A**: 다시 실행하면 됩니다. 스크립트는 처음부터 다시 다운로드합니다.

### Q4. 특정 심볼만 업데이트하고 싶어요

**A**: `--symbols` 옵션 사용

```bash
python scripts/download_candle_data.py --symbols BTCUSDT --timeframes 1h 4h --years 3
```

### Q5. 백테스트에서 데이터가 없다고 나와요

**A**: 캐시 폴더 경로 확인

```bash
# 올바른 경로
ls backend/cache/candles/

# 환경변수 확인
echo $CANDLE_CACHE_DIR
```

### Q6. API 키가 필요한가요?

**A**: **아니오!** 공개 API를 사용하므로 API 키가 필요하지 않습니다.

### Q7. 다른 거래소 데이터도 받을 수 있나요?

**A**: 현재 스크립트는 Bitget 전용입니다. 다른 거래소는 코드 수정 필요.

---

## 📞 문제 발생 시

1. **로그 확인**: 스크립트 실행 시 출력되는 로그 확인
2. **에러 메시지**: 정확한 에러 메시지 기록
3. **환경 정보**: Python 버전, OS, 패키지 버전 확인
4. **재시도**: 대부분의 문제는 재시도로 해결

---

## ✅ 체크리스트

### 다운로드 전

- [ ] Python 3.9+ 설치 확인
- [ ] ccxt, aiofiles 패키지 설치
- [ ] 디스크 공간 1GB 이상 확보
- [ ] 인터넷 연결 확인

### 다운로드 중

- [ ] 터미널 열어두기 (또는 nohup 사용)
- [ ] 진행 상황 모니터링 (1~2시간 소요)

### 다운로드 후

- [ ] 캐시 폴더 파일 확인
- [ ] 파일 크기 확인
- [ ] 데이터 무결성 확인 (head 명령어)
- [ ] 백테스트 테스트 실행

---

## 📁 관련 파일

| 파일 | 설명 |
|------|------|
| `backend/scripts/download_candle_data.py` | 다운로드 스크립트 |
| `backend/cache/candles/` | 캐시 저장 폴더 |
| `backend/src/config.py` | BacktestConfig 설정 |
| `BACKTEST_OFFLINE_DATA_GUIDE.md` | 오프라인 모드 가이드 |

---

*마지막 업데이트: 2025-12-05 15:15*
