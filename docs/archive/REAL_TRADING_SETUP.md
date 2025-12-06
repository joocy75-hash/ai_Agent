# 실제 매매 환경 설정 완료

## 변경 사항 요약

Mock 데이터를 완전히 제거하고 실제 거래소 API와 연동하도록 백엔드를 설정했습니다.

### 1. Mock Price Generator 비활성화
- **파일**: [backend/src/database/db.py](backend/src/database/db.py)
- **변경**: Mock price generator를 비활성화하고 Bitget WebSocket collector 활성화
- **결과**: 실제 Bitget 거래소로부터 실시간 시장 데이터 수신

```python
# 변경 전
asyncio.create_task(mock_price_generator(market_queue))

# 변경 후
asyncio.create_task(bitget_ws_collector(market_queue))
```

### 2. Chart API Mock 데이터 제거
- **파일**: [backend/src/api/chart.py](backend/src/api/chart.py)
- **변경**: Mock 캔들 데이터 생성 로직 제거
- **결과**: 캔들 데이터가 없을 경우 503 에러 반환 (실제 데이터만 제공)

```python
# 변경 후
if not candles:
    raise HTTPException(
        status_code=503,
        detail="No market data available. Please ensure market data service is running."
    )
```

### 3. Account API Mock 데이터 제거
- **파일**: [backend/src/api/account.py](backend/src/api/account.py)
- **변경**: 포지션 조회 실패 시 mock 데이터 반환 제거
- **결과**: API 에러 발생 시 명확한 에러 메시지 반환

```python
# 변경 후
except Exception as e:
    raise HTTPException(
        status_code=500,
        detail=f"Failed to fetch positions from exchange: {str(e)}"
    )
```

### 4. Config Mock 설정 제거
- **파일**: [backend/src/config.py](backend/src/config.py)
- **변경**: ExchangeConfig에서 Mock 잔고 설정 제거
- **결과**: Mock 잔고 상수 삭제

### 5. Mock Price Generator 파일 삭제
- **파일**: `backend/src/services/mock_price_generator.py` (삭제됨)
- **결과**: Mock 데이터 생성 코드 완전히 제거

## 실제 매매 테스트를 위한 설정

### 필수 사항

1. **API 키 설정**
   - 거래소 API 키가 필수입니다
   - Settings 페이지에서 API 키를 입력하거나
   - 다음 curl 명령어로 직접 설정:

```bash
TOKEN="YOUR_JWT_TOKEN"

curl -X POST http://localhost:8000/account/save_keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "api_key": "YOUR_BITGET_API_KEY",
    "secret_key": "YOUR_BITGET_SECRET_KEY",
    "passphrase": "YOUR_BITGET_PASSPHRASE"
  }'
```

2. **환경 변수 설정**
```bash
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
```

3. **백엔드 시작**
```bash
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 백엔드 시작 확인

백엔드 로그에서 다음 메시지를 확인:

```
✅ Bitget WebSocket collector started (production mode)
✅ Chart data service started
✅ Bot manager bootstrapped
✅ Alert scheduler started
🎉 Application startup complete!
```

### 실제 데이터 흐름

1. **시장 데이터**: Bitget WebSocket → Market Queue → Candle Generator → Chart API
2. **잔고 조회**: Frontend → Backend API → Bitget REST API → 실제 잔고
3. **포지션 조회**: Frontend → Backend API → Bitget REST API → 실제 포지션
4. **주문 실행**: Frontend → Backend API → Bitget REST API → 실제 거래소 주문

## API 키 없이 사용 가능한 기능

- 백테스트 (과거 데이터 기반 시뮬레이션)
- AI 전략 생성
- 전략 업로드 및 관리
- 차트 데이터 조회 (Bitget 퍼블릭 API 사용)

## API 키가 필요한 기능

- 실제 잔고 조회
- 실제 포지션 조회
- 실제 주문 실행 (라이브 트레이딩)
- 봇 자동 매매

## 주의 사항

⚠️ **실제 자금을 사용하는 환경입니다!**

1. 처음에는 테스트넷이나 소액으로 테스트하세요
2. API 키는 반드시 안전하게 보관하세요
3. 봇 실행 전 전략을 충분히 백테스트하세요
4. Stop Loss 설정을 확인하세요
5. 리스크 관리 설정을 적절히 조정하세요

## 백테스트로 먼저 테스트

실제 매매 전 반드시 백테스트로 전략을 검증하세요:

```bash
# 백테스트 실행
curl -X POST http://localhost:8000/backtest/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "strategy_id": 1,
    "symbol": "BTCUSDT",
    "start_date": "2025-01-01",
    "end_date": "2025-12-01",
    "initial_balance": 1000,
    "fee_rate": 0.001
  }'
```

## 문제 해결

### WebSocket 연결 실패
- 로그에서 "구독 실패" 메시지가 보이면 재연결 시도 중입니다
- 5초마다 자동으로 재연결됩니다
- 인터넷 연결을 확인하세요

### API 키 인증 실패
- API 키가 올바르게 설정되었는지 확인
- Bitget에서 API 키의 권한을 확인
- API 키의 IP 화이트리스트를 확인

### 차트 데이터 없음 (503 에러)
- Bitget WebSocket이 정상 작동하는지 확인
- 백엔드 로그에서 WebSocket 연결 상태 확인
- 잠시 후 다시 시도 (데이터 수집 중)

## 다음 단계

1. API 키를 설정하세요
2. 프론트엔드를 시작하세요: `cd frontend && npm run dev`
3. 브라우저에서 http://localhost:5173 접속
4. 로그인 후 Settings에서 API 키 입력
5. Dashboard에서 실제 잔고와 포지션 확인
6. 백테스트로 전략 검증
7. 소액으로 라이브 트레이딩 테스트

## 참고 문서

- [WORK_LOG.md](WORK_LOG.md) - 전체 작업 로그
- [CURRENT_STATUS_SUMMARY.md](CURRENT_STATUS_SUMMARY.md) - 현재 상태 요약
- [AGGRESSIVE_TEST_GUIDE.md](AGGRESSIVE_TEST_GUIDE.md) - 공격적 테스트 가이드
