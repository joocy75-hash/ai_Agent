# 실전거래 테스트용 AI 전략 가이드

## 📋 목차
1. [전략 개요](#전략-개요)
2. [전략 등록](#전략-등록)
3. [백테스트](#백테스트)
4. [실전 테스트](#실전-테스트)
5. [모니터링](#모니터링)
6. [트러블슈팅](#트러블슈팅)

---

## 전략 개요

### SafeTest AI Strategy

실전거래 테스트를 위해 설계된 보수적 AI 전략입니다.

#### 주요 특징

1. **다중 지표 확인**
   - EMA 크로스오버: 트렌드 방향 확인
   - RSI: 과매수/과매도 확인
   - ATR: 변동성 필터링
   - Volume: 거래량 증가 확인

2. **엄격한 리스크 관리**
   - 손절매: 2% 자동 설정
   - 익절: 3% 자동 설정
   - 최소 거래 수량: 0.001
   - 쿨다운: 거래 후 5 캔들 대기

3. **보수적 진입**
   - 신뢰도 70% 이상에서만 진입
   - 모든 조건 동시 충족 시에만 거래
   - 변동성 과다/과소 시 거래 중단

#### 전략 파라미터

```json
{
  "ema_fast": 9,              // 빠른 EMA 기간
  "ema_slow": 21,             // 느린 EMA 기간
  "rsi_period": 14,           // RSI 계산 기간
  "rsi_oversold": 30,         // RSI 과매도 기준
  "rsi_overbought": 70,       // RSI 과매수 기준
  "atr_period": 14,           // ATR 계산 기간
  "volume_period": 20,        // 볼륨 평균 계산 기간
  "volume_threshold": 1.2,    // 볼륨 최소 비율 (평균 대비 120%)
  "stop_loss_pct": 2.0,       // 손절 비율 (%)
  "take_profit_pct": 3.0,     // 익절 비율 (%)
  "max_position_size": 0.001, // 최대 포지션 크기
  "cooldown_candles": 5       // 거래 후 대기 캔들 수
}
```

---

## 전략 등록

### 1. 데이터베이스에 전략 등록

```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
python3 register_test_strategy.py
```

### 2. 등록 확인

등록이 완료되면 다음과 같은 출력이 표시됩니다:

```
✅ 새로운 전략이 등록되었습니다!
   Strategy ID: 2
   Name: SafeTest AI Strategy
```

### 3. 전략 목록 확인 (API)

```bash
curl -X GET "http://localhost:8000/strategies" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 백테스트

### 1. 샘플 데이터로 백테스트

```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend
python3 test_strategy_backtest.py
```

### 2. 실제 데이터로 백테스트

실제 거래소 데이터를 사용하여 백테스트를 수행하려면:

```python
from src.strategies.test_live_strategy import create_test_strategy
from src.services.bitget_rest import get_bitget_rest

# 1. Bitget 클라이언트 생성
bitget = get_bitget_rest(api_key, api_secret, passphrase)

# 2. 과거 데이터 가져오기
candles = await bitget.get_candles(
    symbol="BTCUSDT",
    timeframe="15m",
    limit=500
)

# 3. 전략 생성
strategy = create_test_strategy()

# 4. 백테스트 실행
for i, candle in enumerate(candles):
    signal = strategy.generate_signal(
        current_price=candle["close"],
        candles=candles[:i+1],
        current_position=None
    )
    # 시그널 처리 로직...
```

### 3. 백테스트 결과 분석

다음 지표를 확인하세요:

- **승률**: 최소 50% 이상
- **Profit Factor**: 최소 1.5 이상
- **최대 손실**: -10% 이내
- **총 거래 횟수**: 최소 20회 이상 (충분한 샘플)

---

## 실전 테스트

### 1. API 키 설정

#### 프론트엔드에서 설정

1. http://localhost:3001 접속
2. Settings 페이지로 이동
3. Bitget API 키 입력:
   - API Key
   - Secret Key
   - Passphrase

#### API로 설정

```bash
TOKEN="YOUR_JWT_TOKEN"

curl -X POST "http://localhost:8000/account/save_keys" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "api_key": "YOUR_BITGET_API_KEY",
    "secret_key": "YOUR_BITGET_SECRET_KEY",
    "passphrase": "YOUR_BITGET_PASSPHRASE"
  }'
```

### 2. 전략 선택 및 봇 시작

#### 프론트엔드에서 시작

1. Dashboard로 이동
2. "SafeTest AI Strategy" 선택
3. "Start Bot" 버튼 클릭

#### API로 시작

```bash
curl -X POST "http://localhost:8000/bot/start" \
  -H "Authorization: Bearer $TOKEN" \
  -d "strategy_id=2"
```

### 3. 초기 체크리스트

실전 거래 시작 전 반드시 확인:

- [ ] 백테스트 완료 (30일 이상 데이터)
- [ ] API 키 권한 확인 (거래 권한 있음)
- [ ] 최소 수량으로 시작 (0.001 BTC)
- [ ] 손절/익절 설정 확인
- [ ] 충분한 잔고 확보
- [ ] 로그 모니터링 준비
- [ ] 비상 중단 계획 수립

---

## 모니터링

### 1. 실시간 로그 확인

#### 백엔드 로그

```bash
# 백엔드 터미널에서 확인
# 봇 실행 중 자동으로 출력됨
```

주요 로그 메시지:
```
[BotRunner] Loaded strategy 'SafeTest AI Strategy'
[BotRunner] Executing buy order at 50000.0
[BotRunner] Order executed successfully: order_id=12345
```

#### 프론트엔드 모니터링

1. **Dashboard**
   - 봇 상태 (실행 중/중지)
   - 현재 잔고
   - 실시간 가격

2. **Positions 페이지**
   - 열린 포지션
   - 미실현 손익
   - 진입 가격/현재 가격

3. **Trades 페이지**
   - 거래 내역
   - 각 거래의 손익
   - 진입/청산 사유

### 2. WebSocket 이벤트 모니터링

프론트엔드 콘솔에서 확인:

```javascript
// Chrome DevTools Console
// WebSocket 메시지가 실시간으로 표시됨

[WebSocket] Connected
[WebSocket] trade_filled: { symbol: "BTCUSDT", side: "buy", price: 50000 }
[WebSocket] position_update: { ... }
[WebSocket] balance_update: { ... }
```

### 3. 주요 모니터링 지표

#### 성과 지표
- **총 거래 횟수**: 과도한 거래 방지
- **승률**: 최소 50% 유지
- **평균 손익**: 양수 유지
- **최대 손실**: -10% 이내

#### 시스템 지표
- **API 응답 시간**: 1초 이내
- **WebSocket 연결 상태**: 연결됨
- **봇 상태**: 실행 중
- **마지막 데이터 수신**: 30초 이내

#### 알림 조건
- 5회 연속 손실
- 일일 손실 -5% 초과
- API 응답 시간 5초 초과
- WebSocket 연결 끊김 1분 이상

---

## 트러블슈팅

### 1. 봇이 시작되지 않음

**증상**: "Start Bot" 클릭 시 에러 발생

**해결 방법**:

1. API 키 확인
```bash
curl -X GET "http://localhost:8000/account/keys" \
  -H "Authorization: Bearer $TOKEN"
```

2. 백엔드 로그 확인
```bash
# 백엔드 터미널에서 에러 메시지 확인
```

3. 데이터베이스 확인
```bash
sqlite3 trading.db "SELECT * FROM api_keys WHERE user_id = YOUR_USER_ID;"
```

### 2. 거래가 실행되지 않음

**증상**: 봇은 실행 중이지만 거래가 발생하지 않음

**원인**:
- 신뢰도가 70% 미만
- 변동성 필터 통과 실패
- 거래량 부족
- 쿨다운 기간 중

**확인 방법**:
```python
# 백테스트 스크립트로 현재 시장 조건 테스트
python3 test_strategy_backtest.py
```

### 3. API 에러 발생

**증상**: "API key invalid" 또는 "Insufficient permissions"

**해결 방법**:

1. Bitget API 키 권한 확인
   - 거래 권한: 활성화
   - 출금 권한: 비활성화 (보안)
   - IP 화이트리스트: 현재 IP 추가

2. API 키 재등록
```bash
# Settings 페이지에서 API 키 삭제 후 재등록
```

### 4. 손실이 계속됨

**증상**: 5회 이상 연속 손실 또는 일일 손실 -5% 초과

**즉시 조치**:

1. **봇 중지**
```bash
curl -X POST "http://localhost:8000/bot/stop" \
  -H "Authorization: Bearer $TOKEN"
```

2. **포지션 수동 청산**
   - Positions 페이지에서 "Close Position" 클릭

3. **로그 분석**
   - 거래 내역 확인
   - 진입/청산 사유 분석
   - 시장 조건 확인

4. **전략 조정**
   - 파라미터 수정 (더 보수적으로)
   - 백테스트 재실행
   - 승률 및 Profit Factor 확인

### 5. WebSocket 연결 끊김

**증상**: 실시간 데이터 업데이트 중단

**해결 방법**:

1. 브라우저 새로고침
2. 백엔드 재시작
```bash
# Ctrl+C로 중지 후 재시작
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

3. 네트워크 확인
```bash
ping localhost
curl http://localhost:8000/api/status
```

---

## 비상 중단 절차

예상치 못한 상황 발생 시:

### 1. 즉시 봇 중지
```bash
curl -X POST "http://localhost:8000/bot/stop" \
  -H "Authorization: Bearer $TOKEN"
```

또는 Dashboard에서 "Stop Bot" 클릭

### 2. 모든 포지션 청산

#### 프론트엔드
- Positions 페이지 → 각 포지션 "Close" 클릭

#### API
```bash
curl -X POST "http://localhost:8000/positions/{symbol}/close" \
  -H "Authorization: Bearer $TOKEN"
```

### 3. 로그 저장

```bash
# 백엔드 로그 저장
# 터미널 출력을 파일로 저장 (Ctrl+C 전)

# 거래 내역 저장
curl -X GET "http://localhost:8000/trades?limit=100" \
  -H "Authorization: Bearer $TOKEN" > trades_backup.json
```

### 4. 상황 분석

- 거래 내역 검토
- 손실 원인 파악
- 시장 조건 확인
- 전략 파라미터 검토

---

## 문의 및 지원

문제가 지속되거나 추가 도움이 필요하면:

1. GitHub Issues: [프로젝트 주소]
2. 로그 파일 첨부
3. 상세한 증상 설명
4. 재현 방법 기술

---

## ⚠️ 면책 조항

1. 이 전략은 **교육 및 테스트 목적**으로만 제공됩니다
2. 실제 자금 투자 시 발생하는 모든 손실은 사용자 책임입니다
3. 암호화폐 거래는 높은 위험을 수반합니다
4. 투자 결정은 신중하게 하시기 바랍니다
5. 손실을 감당할 수 있는 금액으로만 거래하세요

---

## 라이센스

MIT License
