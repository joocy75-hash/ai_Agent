# 주문 미실행 문제 진단 및 해결방안

**진단 일시**: 2025-12-03 16:40 KST
**문제**: 봇이 시작되지만 실제 주문이 실행되지 않음

---

## 🔍 문제 진단

### 1. ✅ 정상 작동하는 부분

#### API 연결
- **Bitget API 인증**: ✅ 정상
- **잔고 조회**: ✅ 85.38 USDT 확인
- **포지션 조회**: ✅ 정상
- **봇 시작/중지 API**: ✅ 정상

#### 전략 설정
- **전략 로드**: ✅ 3개 전략 확인 (RSI, MA Cross, Ultra Aggressive)
- **전략 코드**: ✅ 공격적인 전략 파일 존재
- **봇 매니저**: ✅ Bootstrap 완료

#### 데이터베이스
- **API 키 저장**: ✅ 암호화되어 안전하게 저장
- **사용자 정보**: ✅ 정상
- **전략 정보**: ✅ 정상

### 2. ❌ 문제가 있는 부분

#### A. Bitget WebSocket 연결 실패 ⚠️ **핵심 문제**

**증상**:
```
ERROR - ❌ BTCUSDT 구독 실패: no close frame received or sent
ERROR - ❌ ETHUSDT 구독 실패: no close frame received or sent
WARNING - ⚠️ WebSocket 연결 종료
INFO - ⏳ 5초 후 재연결...
```

**원인**:
1. Bitget WebSocket API 프로토콜이 변경되었을 가능성
2. SSL 인증서 문제
3. 구독 메시지 형식이 잘못됨

**영향**:
- `market_queue`에 실시간 가격 데이터가 들어오지 않음
- 봇이 market data를 받지 못해서 전략을 실행할 수 없음
- 따라서 주문이 생성되지 않음

#### B. 시장 데이터 부족

**bot_runner.py의 실행 흐름**:
```python
while True:
    # 1. market_queue에서 데이터 수신 (60초 타임아웃)
    market = await asyncio.wait_for(self.market_queue.get(), timeout=60.0)

    # 2. 데이터가 없으면 계속 대기
    # 3. 데이터가 있어야만 전략 실행
    signal = generate_signal_with_strategy(...)

    # 4. 시그널에 따라 주문 실행
```

**WebSocket이 작동하지 않으면**:
- market_queue가 비어있음
- 60초 타임아웃 발생
- "NO_MARKET_DATA" 경고만 발생
- 전략이 실행되지 않음
- 주문이 생성되지 않음

---

## 🔧 해결방안

### 즉시 해결 가능한 방법

#### 방법 1: Bitget WebSocket API 버전 확인 및 수정

**현재 코드** ([backend/src/services/bitget_ws_collector.py](backend/src/services/bitget_ws_collector.py:22)):
```python
self.ws_url = "wss://ws.bitget.com/mix/v1/stream"
```

**시도할 수정사항**:
1. API v2로 변경
   ```python
   self.ws_url = "wss://ws.bitget.com/v2/ws/public"
   ```

2. 구독 메시지 형식 확인
   - Bitget 공식 문서에서 최신 WebSocket API 프로토콜 확인
   - 현재 사용 중인 ticker 구독 형식이 맞는지 확인

3. WebSocket 라이브러리 버전 확인
   ```bash
   pip list | grep websockets
   ```

#### 방법 2: REST API Fallback 활성화 (임시 해결책)

WebSocket이 작동하지 않을 때 REST API로 주기적으로 가격을 가져오는 방식:

**새로운 파일 생성**: `backend/src/services/rest_price_collector.py`
```python
import asyncio
import logging
from services.bitget_rest import get_bitget_rest

logger = logging.getLogger(__name__)

async def rest_price_collector(market_queue: asyncio.Queue, api_key: str, api_secret: str, passphrase: str):
    """
    REST API를 사용한 가격 수집기 (WebSocket 대체)
    """
    client = get_bitget_rest(api_key, api_secret, passphrase)
    symbols = ["BTCUSDT", "ETHUSDT"]

    logger.info("🔄 REST price collector started")

    while True:
        try:
            for symbol in symbols:
                # 현재 가격 조회
                ticker = await client.get_ticker(symbol=symbol)

                market_data = {
                    "symbol": symbol,
                    "price": float(ticker.get("lastPr", 0)),
                    "volume": float(ticker.get("baseVolume", 0)),
                    "timestamp": ticker.get("ts", 0) / 1000,
                    "high": float(ticker.get("high24h", 0)),
                    "low": float(ticker.get("low24h", 0)),
                    "open": float(ticker.get("open24h", 0)),
                }

                try:
                    market_queue.put_nowait(market_data)
                    logger.debug(f"✅ REST price: {symbol} @ ${market_data['price']}")
                except asyncio.QueueFull:
                    # 큐가 가득 차면 오래된 데이터 제거
                    try:
                        market_queue.get_nowait()
                        market_queue.put_nowait(market_data)
                    except:
                        pass

            # 10초마다 업데이트 (봇이 작동할 수 있을 정도로 충분)
            await asyncio.sleep(10)

        except Exception as e:
            logger.error(f"REST price collector error: {e}")
            await asyncio.sleep(5)
```

**db.py 수정**:
```python
# WebSocket 대신 REST collector 사용
from ..services.rest_price_collector import rest_price_collector
from ..database.models import ApiKey

# Admin 계정의 API 키로 REST collector 시작
# (또는 별도의 퍼블릭 API 계정 생성)
async with engine.begin() as conn:
    result = await conn.execute(select(ApiKey).where(ApiKey.user_id == 6))
    admin_api = result.scalar_one_or_none()

    if admin_api:
        api_key = decrypt_secret(admin_api.encrypted_api_key)
        api_secret = decrypt_secret(admin_api.encrypted_secret_key)
        passphrase = decrypt_secret(admin_api.encrypted_passphrase)

        asyncio.create_task(rest_price_collector(market_queue, api_key, api_secret, passphrase))
        logger.info("✅ REST price collector started")
```

#### 방법 3: CCXT 라이브러리 사용 (가장 간단)

CCXT는 이미 설치되어 있고, 안정적인 WebSocket 지원을 제공합니다:

**새로운 파일**: `backend/src/services/ccxt_price_collector.py`
```python
import asyncio
import logging
import ccxt.pro as ccxtpro

logger = logging.getLogger(__name__)

async def ccxt_price_collector(market_queue: asyncio.Queue):
    """
    CCXT Pro를 사용한 실시간 가격 수집
    """
    exchange = ccxtpro.bitget({
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })

    symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT']

    logger.info("🚀 CCXT price collector started")

    try:
        while True:
            for symbol in symbols:
                try:
                    ticker = await exchange.watch_ticker(symbol)

                    # 심볼 변환: BTC/USDT:USDT -> BTCUSDT
                    simple_symbol = symbol.split('/')[0] + 'USDT'

                    market_data = {
                        "symbol": simple_symbol,
                        "price": float(ticker.get('last', 0)),
                        "volume": float(ticker.get('baseVolume', 0)),
                        "timestamp": ticker.get('timestamp', 0) / 1000,
                        "high": float(ticker.get('high', 0)),
                        "low": float(ticker.get('low', 0)),
                        "open": float(ticker.get('open', 0)),
                    }

                    try:
                        market_queue.put_nowait(market_data)
                    except asyncio.QueueFull:
                        try:
                            market_queue.get_nowait()
                            market_queue.put_nowait(market_data)
                        except:
                            pass

                except Exception as e:
                    logger.error(f"Error watching {symbol}: {e}")
                    await asyncio.sleep(1)

    finally:
        await exchange.close()
```

---

## 🎯 권장 해결 순서

### 단계 1: CCXT 방식으로 전환 (가장 빠른 해결)

1. `backend/src/services/ccxt_price_collector.py` 생성
2. `backend/src/database/db.py` 수정:
   ```python
   # 기존 코드 주석처리
   # asyncio.create_task(bitget_ws_collector(market_queue))

   # 새로운 코드 추가
   from ..services.ccxt_price_collector import ccxt_price_collector
   asyncio.create_task(ccxt_price_collector(market_queue))
   ```
3. 백엔드 재시작
4. 봇 시작하여 테스트

**예상 결과**:
- 실시간 가격 데이터 정상 수신
- 봇이 전략을 실행하기 시작
- Ultra Aggressive 전략으로 빠르게 주문 생성

### 단계 2: 봇 로그 모니터링

봇이 시작된 후 로그를 실시간으로 확인:
```bash
# 새 터미널에서
tail -f /Users/mr.joo/Desktop/auto-dashboard/backend/*.log

# 또는 systemd/journalctl 사용
```

**확인할 로그**:
```
✅ Loaded N historical candles
✅ Market data queued: BTCUSDT @ $95000
✅ Strategy signal: buy (confidence: 0.8, reason: ...)
✅ Order placed: BTCUSDT long 0.001
```

### 단계 3: 거래 확인

```bash
# 거래 내역 조회
curl -s http://localhost:8000/trades/recent-trades?limit=10 \
  -H "Authorization: Bearer $TOKEN" | jq

# 실제 거래소에서 확인
curl -s http://localhost:8000/account/positions \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 🚨 주의사항

### 실전 매매 전 확인사항

1. **최소 수량 확인**
   - Bitget BTCUSDT 최소 주문: 0.001 BTC
   - Ultra Aggressive 전략 기본 수량: 0.01 BTC (~$950)
   - 잔고 85.38 USDT로는 0.001 BTC밖에 못 거래합니다!

2. **레버리지 설정**
   - 현재 레버리지 설정을 확인하세요
   - 레버리지 1x: 안전하지만 수익률 낮음
   - 레버리지 10x: 위험하지만 작은 잔고로도 가능

3. **수량 조정**
   전략 파라미터를 수정하여 더 작은 수량으로 테스트:
   ```sql
   UPDATE strategies
   SET params = '{"symbol": "ETH/USDT", "timeframe": "1m", "ma_fast": 3, "ma_slow": 7, "max_position_size": 0.001, "stop_loss_pct": 1.5, "take_profit_pct": 2.0, "cooldown_candles": 0, "min_confidence": 0.2}'
   WHERE id = 7;
   ```

---

## 📋 체크리스트

실제 주문이 들어가기 위해 필요한 조건:

- [x] API 키 설정 완료
- [x] 잔고 확인 (85.38 USDT)
- [x] 봇 시작 가능
- [ ] **시장 데이터 수신 중** ⚠️ **핵심 문제**
- [ ] 전략 시그널 생성 확인
- [ ] 주문 실행 확인
- [ ] 거래 내역 기록 확인

---

## 🔗 관련 파일

- [bitget_ws_collector.py](backend/src/services/bitget_ws_collector.py) - 현재 WebSocket 수집기 (문제 있음)
- [bot_runner.py](backend/src/services/bot_runner.py) - 봇 실행 로직
- [ultra_aggressive_strategy.py](backend/src/strategies/ultra_aggressive_strategy.py) - 공격적 전략
- [db.py](backend/src/database/db.py) - 애플리케이션 시작 로직

---

## 💡 다음 단계

1. **즉시**: CCXT 방식으로 전환하여 시장 데이터 수신 문제 해결
2. **봇 재시작**: Ultra Aggressive 전략으로 봇 시작
3. **모니터링**: 10분간 로그 확인하여 시그널 생성 확인
4. **검증**: 실제 주문 실행 및 거래소 확인

문제의 핵심은 **WebSocket 연결 실패로 인한 시장 데이터 부재**입니다. 이를 해결하면 주문이 정상적으로 실행될 것입니다.
