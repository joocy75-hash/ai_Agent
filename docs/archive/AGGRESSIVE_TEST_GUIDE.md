# 🚀 공격적 테스트 전략 실전 매매 가이드

## 📋 목차
1. [전략 개요](#전략-개요)
2. [테스트 준비](#테스트-준비)
3. [봇 시작](#봇-시작)
4. [모니터링](#모니터링)
5. [예상 동작](#예상-동작)
6. [문제 해결](#문제-해결)

---

## 전략 개요

### Aggressive Test Strategy

실전 매매 시스템을 빠르게 검증하기 위한 공격적 테스트 전략입니다.

#### 핵심 특징

| 항목 | 값 | 설명 |
|------|-----|------|
| 진입 신뢰도 | 30% | 매우 낮음 - 빠른 진입 |
| EMA | 5/10 | 빠른 반응 |
| RSI | 40/60 | 쉬운 진입 조건 |
| 손절 | -1% | 빠른 손절 |
| 익절 | +2% | 빠른 익절 |
| 포지션 크기 | 0.001 BTC | 최소 수량 (~$100) |
| 쿨다운 | 2 캔들 (10분) | 짧은 대기 시간 |
| 타임프레임 | 5분 | 빠른 거래 빈도 |

#### 진입 조건

**롱 포지션 (매수)**:
- EMA(5) > EMA(10) **OR**
- RSI < 40

**숏 포지션 (매도)**:
- EMA(5) < EMA(10) **OR**
- RSI > 60

#### 청산 조건

자동으로 다음 조건에서 청산됩니다:
- **익절**: +2% 수익
- **손절**: -1% 손실

---

## 테스트 준비

### 1. Bitget API 키 설정

#### API 키 발급
1. Bitget 계정 로그인
2. API 관리 페이지로 이동
3. 새 API 키 생성:
   - **권한**: Read + Trade만 활성화
   - **출금 권한**: 반드시 비활성화
   - **IP 화이트리스트**: 현재 IP 추가 권장

#### API 키 등록 (프론트엔드)
1. http://localhost:3001 접속
2. Settings 페이지로 이동
3. API 키 정보 입력:
   - API Key
   - Secret Key
   - Passphrase
4. "Save" 클릭

#### API 키 등록 (CLI)
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

### 2. 잔고 확인

최소 잔고: **$150 USDT** 권장
- 포지션: $100
- 수수료: ~$0.1
- 여유 자금: $50

### 3. 전략 확인

```bash
sqlite3 trading.db "SELECT id, name, is_active FROM strategies WHERE name = 'Aggressive Test Strategy';"
```

출력 예:
```
6|Aggressive Test Strategy|0
```

---

## 봇 시작

### 방법 1: 프론트엔드에서 시작

1. **로그인**: http://localhost:3001
   - Email: admin@admin.com
   - Password: Admin1234!

2. **전략 활성화**:
   - 전략 관리 페이지로 이동
   - "Aggressive Test Strategy" 찾기
   - Switch를 ON으로 전환
   - 페이지 새로고침해도 ON 상태 유지 확인

3. **봇 시작**:
   - Dashboard로 이동
   - 전략 선택: "Aggressive Test Strategy"
   - "Start Bot" 버튼 클릭

### 방법 2: API로 시작

```bash
# 1. 로그인
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin1234!"}' \
  > /tmp/login.json

TOKEN=$(cat /tmp/login.json | jq -r '.token')

# 2. 봇 시작
curl -X POST "http://localhost:8000/bot/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": 6}'

# 3. 상태 확인
curl -X GET "http://localhost:8000/bot/status" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 모니터링

### 1. 백엔드 로그 확인

```bash
tail -f /tmp/backend_new.log
```

**주요 로그 메시지**:
```
[INFO] Starting bot loop for user 6
[INFO] Loaded strategy 'Aggressive Test Strategy' for user 6
[INFO] Bitget API client initialized for user 6
[INFO] Strategy signal for user 6: buy (confidence: 0.60, reason: Trend: bullish | RSI: neutral)
[INFO] Executing buy order for user 6 at 50000.0 (size: 0.001, confidence: 0.60)
[INFO] Bitget order executed successfully for user 6
```

### 2. 프론트엔드 모니터링

#### Dashboard
- 봇 상태: 실행 중 / 중지
- 현재 잔고 실시간 업데이트
- 최근 거래 내역

#### Positions 페이지
- 열린 포지션 확인
- 미실현 손익
- 진입 가격 / 현재 가격

#### Trades 페이지
- 거래 기록
- 각 거래의 손익
- 진입/청산 사유

### 3. WebSocket 이벤트

브라우저 콘솔 (F12):
```javascript
// 거래 체결 이벤트
{
  "event": "trade_filled",
  "symbol": "BTCUSDT",
  "side": "buy",
  "price": 50000.0,
  "size": 0.001,
  "confidence": 0.6,
  "reason": "Trend: bullish | RSI: neutral"
}

// 포지션 청산 이벤트
{
  "event": "position_closed",
  "symbol": "BTCUSDT",
  "reason": "Quick TP: 2.01%"
}
```

### 4. 데이터베이스 확인

```bash
# 최근 거래 내역
sqlite3 trading.db "SELECT * FROM trades ORDER BY created_at DESC LIMIT 5;"

# 현재 포지션
sqlite3 trading.db "SELECT * FROM positions WHERE user_id = 6;"

# 봇 상태
sqlite3 trading.db "SELECT * FROM bot_status WHERE user_id = 6;"
```

---

## 예상 동작

### 시나리오 1: 롱 포지션 진입 → 익절

```
1. [00:00] 시그널 감지: EMA 상승 추세, RSI 45
   → 신뢰도 60%, 매수 시그널

2. [00:00] 롱 포지션 진입
   - 진입 가격: $50,000
   - 수량: 0.001 BTC
   - 손절가: $49,500 (-1%)
   - 익절가: $51,000 (+2%)

3. [00:15] 가격 상승: $51,020
   → 익절 조건 충족 (>+2%)

4. [00:15] 포지션 자동 청산
   - 청산 가격: $51,020
   - 손익: +$10.20 (+2.04%)
   - 사유: "Quick TP: 2.04%"

5. [00:25] 쿨다운 종료 (2 캔들 = 10분)
   → 다음 거래 가능
```

### 시나리오 2: 숏 포지션 진입 → 손절

```
1. [00:00] 시그널 감지: EMA 하락 추세, RSI 62
   → 신뢰도 70%, 매도 시그널

2. [00:00] 숏 포지션 진입
   - 진입 가격: $50,000
   - 수량: 0.001 BTC
   - 손절가: $50,500 (+1%)
   - 익절가: $49,000 (-2%)

3. [00:10] 가격 상승: $50,520
   → 손절 조건 충족 (>+1%)

4. [00:10] 포지션 자동 청산
   - 청산 가격: $50,520
   - 손익: -$5.20 (-1.04%)
   - 사유: "Quick SL (Short): 1.04%"

5. [00:20] 쿨다운 종료
   → 다음 거래 가능
```

### 예상 거래 빈도

**정상적인 경우**:
- 시간당 1-3회 거래
- 하루 10-20회 거래

**활발한 시장**:
- 시간당 5-10회 거래
- 하루 30-50회 거래

⚠️ **주의**: 거래 빈도가 매우 높으면 수수료 부담이 큽니다!

---

## 문제 해결

### 문제 1: 봇이 시작되지 않음

**증상**: "Start Bot" 클릭 시 에러 발생

**해결**:
```bash
# 1. 백엔드 로그 확인
tail -50 /tmp/backend_new.log

# 2. API 키 확인
curl -X GET "http://localhost:8000/account/keys" \
  -H "Authorization: Bearer $TOKEN"

# 3. 전략 확인
sqlite3 trading.db "SELECT * FROM strategies WHERE id = 6;"
```

### 문제 2: 거래가 실행되지 않음

**증상**: 봇은 실행 중이지만 거래가 없음

**원인**:
- 시장 조건이 진입 조건 불충족
- WebSocket 데이터 수신 안됨
- API 키 권한 부족

**확인**:
```bash
# 백엔드 로그에서 시그널 확인
tail -f /tmp/backend_new.log | grep "Strategy signal"

# 예상 출력:
# [INFO] Strategy signal for user 6: hold (confidence: 0.20, reason: Trend: neutral | Momentum: neutral)
```

### 문제 3: 손실이 계속됨

**증상**: 5회 이상 연속 손실 또는 누적 손실 -5% 초과

**즉시 조치**:
1. **봇 중지**:
   ```bash
   curl -X POST "http://localhost:8000/bot/stop" \
     -H "Authorization: Bearer $TOKEN"
   ```

2. **포지션 확인 및 수동 청산**:
   - Positions 페이지에서 열린 포지션 확인
   - "Close Position" 클릭하여 수동 청산

3. **로그 분석**:
   ```bash
   # 최근 50개 거래 확인
   sqlite3 trading.db "SELECT * FROM trades WHERE user_id = 6 ORDER BY created_at DESC LIMIT 50;"
   ```

4. **시장 조건 확인**:
   - 현재 시장이 공격적 전략에 적합한지 확인
   - 변동성이 너무 높거나 낮으면 부적합

### 문제 4: API 에러 발생

**증상**: "Invalid API key" 또는 "Insufficient permissions"

**해결**:
1. Bitget API 키 권한 확인
   - Read 권한: ✅ 활성화
   - Trade 권한: ✅ 활성화
   - Withdraw 권한: ❌ 비활성화

2. API 키 재등록
   - Settings 페이지에서 삭제 후 재등록

3. IP 화이트리스트 확인
   - 현재 IP가 허용 목록에 있는지 확인

### 문제 5: WebSocket 연결 끊김

**증상**: 실시간 데이터 업데이트 중단

**해결**:
1. 브라우저 새로고침 (Ctrl + F5)

2. 백엔드 재시작:
   ```bash
   lsof -ti:8000 | xargs kill -9
   export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
   export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend_new.log 2>&1 &
   ```

3. 네트워크 확인:
   ```bash
   ping localhost
   curl http://localhost:8000/docs
   ```

---

## 비상 중단 절차

### 즉시 봇 중지

**프론트엔드**:
- Dashboard → "Stop Bot" 버튼 클릭

**CLI**:
```bash
curl -X POST "http://localhost:8000/bot/stop" \
  -H "Authorization: Bearer $TOKEN"
```

### 모든 포지션 청산

**프론트엔드**:
1. Positions 페이지로 이동
2. 각 포지션의 "Close" 버튼 클릭

**CLI**:
```bash
# BTCUSDT 포지션 청산
curl -X POST "http://localhost:8000/bitget/positions/close" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT"}'
```

### 로그 저장

```bash
# 백엔드 로그 저장
cp /tmp/backend_new.log ~/aggressive_test_$(date +%Y%m%d_%H%M%S).log

# 거래 내역 저장
curl -X GET "http://localhost:8000/trades?limit=100" \
  -H "Authorization: Bearer $TOKEN" \
  > ~/trades_backup_$(date +%Y%m%d_%H%M%S).json
```

---

## 성공 기준

### 시스템 작동 확인
- ✅ 봇이 정상적으로 시작됨
- ✅ 시그널 감지 및 로깅됨
- ✅ 주문이 실제로 실행됨
- ✅ 포지션이 자동으로 청산됨
- ✅ 거래 기록이 DB에 저장됨
- ✅ WebSocket 알림이 프론트엔드에 도착함

### 전략 성능 (참고용)
- 승률: 40% 이상이면 양호 (공격적 전략 특성상 낮을 수 있음)
- Profit Factor: 1.0 이상 (수익 = 손실)
- 최대 손실: -10% 이내
- 거래 빈도: 시간당 1-10회

⚠️ **중요**: 이 전략은 **시스템 테스트용**이지 실전 수익 목적이 아닙니다!

---

## 체크리스트

### 테스트 시작 전
- [ ] Bitget API 키 등록 완료
- [ ] 잔고 최소 $150 확보
- [ ] 전략 "Aggressive Test Strategy" 활성화
- [ ] 백엔드 실행 중 확인 (http://localhost:8000/docs)
- [ ] 프론트엔드 실행 중 확인 (http://localhost:3001)
- [ ] 백엔드 로그 모니터링 준비 (`tail -f /tmp/backend_new.log`)

### 테스트 중
- [ ] 봇 상태 "실행 중" 확인
- [ ] 로그에서 시그널 감지 확인
- [ ] 거래 실행 확인 (Trades 페이지)
- [ ] 포지션 변화 확인 (Positions 페이지)
- [ ] WebSocket 연결 상태 확인
- [ ] 손익 추적 (누적 손실 -5% 초과 시 중단)

### 테스트 완료 후
- [ ] 봇 중지
- [ ] 모든 포지션 청산
- [ ] 로그 저장
- [ ] 거래 내역 분석
- [ ] 시스템 작동 여부 평가
- [ ] 개선사항 기록

---

## 다음 단계

테스트 완료 후:

1. **보수적 전략 테스트**:
   - "SafeTest AI Strategy" 활성화
   - 더 안전한 진입 조건으로 재테스트

2. **파라미터 조정**:
   - 손익 비율 변경 (예: 1.5% 손절, 3% 익절)
   - 신뢰도 기준 상향 (예: 50%)
   - 쿨다운 시간 증가 (예: 5 캔들)

3. **프로덕션 배포**:
   - 안정성 확인 후 장기 운영
   - 리스크 관리 시스템 추가
   - 모니터링 알림 설정

---

**문의 및 지원**: GitHub Issues에 문제 보고

**면책 조항**:
- 암호화폐 거래는 높은 위험을 수반합니다
- 모든 투자 손실은 사용자 책임입니다
- 이 전략은 테스트 목적으로만 제공됩니다
- 실전 사용 시 충분한 검증이 필요합니다
