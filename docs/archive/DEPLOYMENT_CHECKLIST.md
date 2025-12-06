# 🚀 배포 전 체크리스트

**작성일**: 2025-12-03
**현재 상태**: 실전 매매 테스트 성공 ✅

---

## ✅ 완료된 작업

1. **Mock 데이터 제거** ✅
   - mock_price_generator.py 삭제
   - Mock 잔고/포지션 fallback 제거
   - Mock 캔들 생성 제거

2. **실전 API 연동** ✅
   - Bitget API 키 암호화 저장
   - CCXT 라이브러리로 안정적인 시장 데이터 수집
   - REST API로 주문 실행 성공

3. **실제 거래 검증** ✅
   - ETH/USDT 0.02 SHORT 포지션 체결 확인
   - Order ID: 1380021839811223553
   - Entry: $3,056.37

---

## ⚠️ 배포 전 필수 수정사항

### 1. **차트 서비스 복구** (HIGH PRIORITY)

**현재 문제**:
- 차트 서비스가 market_queue를 소비해서 봇이 데이터를 받지 못함
- 임시로 차트 서비스를 완전히 비활성화한 상태

**해결 방법**:
```python
# backend/src/database/db.py 수정

# 현재 (임시):
asyncio.create_task(ccxt_price_collector(market_queue))
# chart_service 비활성화됨

# 수정해야 할 내용:
chart_queue = asyncio.Queue(maxsize=1000)
asyncio.create_task(ccxt_price_collector(market_queue, chart_queue))
chart_service = await get_chart_service(chart_queue)
```

**수정 파일**:
- `backend/src/database/db.py`: 차트 큐 추가
- `backend/src/services/ccxt_price_collector.py`: 두 큐에 동시 전송

**테스트**:
```bash
# 백엔드 재시작 후
curl http://localhost:8000/health
# 프론트엔드에서 차트가 업데이트되는지 확인
```

---

### 2. **환경 변수 설정**

**필수 환경 변수**:
```bash
# .env 파일 생성
DATABASE_URL=sqlite+aiosqlite:///./trading.db
ENCRYPTION_KEY=<32바이트 Base64 인코딩 키>
JWT_SECRET=<강력한 시크릿 키>
```

**Encryption Key 생성**:
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # 이 값을 ENCRYPTION_KEY로 사용
```

**배포 환경별 설정**:
- **개발**: `trading.db` (SQLite)
- **운영**: PostgreSQL 권장 (`postgresql+asyncpg://...`)

---

### 3. **프로덕션 설정**

#### 백엔드 (FastAPI)

**config.py 수정**:
```python
# 현재는 개발 모드
DEBUG = os.getenv("DEBUG", "True") == "True"

# 운영 환경에서는:
DEBUG = False
ALLOWED_HOSTS = ["yourdomain.com", "api.yourdomain.com"]
```

**CORS 설정**:
```python
# backend/src/main.py
origins = [
    "https://yourdomain.com",  # 실제 도메인으로 변경
]
```

**Uvicorn 실행**:
```bash
# 개발:
uvicorn src.main:app --reload

# 운영:
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 프론트엔드

**환경 변수** (`frontend/.env.production`):
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com
```

**빌드**:
```bash
cd frontend
npm run build
npm start
```

---

### 4. **데이터베이스 마이그레이션**

**SQLite → PostgreSQL 전환** (운영 환경 권장):

```bash
# PostgreSQL 설치 및 설정
createdb trading_prod

# 환경 변수 변경
DATABASE_URL=postgresql+asyncpg://user:password@localhost/trading_prod

# 마이그레이션
alembic upgrade head
```

**이유**:
- SQLite는 동시 쓰기 성능이 낮음
- 운영 환경에서는 PostgreSQL이 안정적

---

### 5. **보안 강화**

#### API 키 보호
```python
# 현재: 암호화되어 DB 저장 ✅
# 추가 권장사항:
- API 키 입력 시 HTTPS 필수
- Redis/Memcached로 세션 관리
```

#### Rate Limiting
```python
# backend/src/main.py에 추가
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/bot/start")
@limiter.limit("5/minute")  # 1분에 5회 제한
async def start_bot(...):
    ...
```

#### HTTPS 강제
```python
# Nginx 리버스 프록시 설정:
server {
    listen 443 ssl;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
    }
}
```

---

### 6. **로깅 및 모니터링**

#### 로그 파일 로테이션
```python
# backend/src/config.py
import logging.handlers

handler = logging.handlers.RotatingFileHandler(
    "/var/log/trading_bot.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

#### 에러 알림
```python
# Sentry, Datadog, 또는 CloudWatch 연동
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=1.0,
)
```

---

### 7. **성능 최적화**

#### Redis 캐싱
```python
# 잔고, 포지션 등 자주 조회되는 데이터 캐싱
import aioredis

redis = await aioredis.create_redis_pool('redis://localhost')
```

#### Connection Pooling
```python
# CCXT exchange 객체 재사용
# 현재는 매번 새로 생성하지만, 풀링하면 성능 향상
```

---

### 8. **테스트 코드 작성**

```bash
# 필수 테스트 항목:
- API 인증 테스트
- 주문 실행 시뮬레이션
- 전략 시그널 검증
- WebSocket 연결 테스트
```

```python
# backend/tests/test_bot_runner.py
async def test_bot_executes_order():
    # Mock Bitget API
    # 전략 시그널 생성
    # 주문 실행 검증
    pass
```

---

## 🔧 배포 스크립트

### Docker Compose (권장)

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:password@postgres/trading
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=trading
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 배포 명령어

```bash
# 1. 이미지 빌드
docker-compose build

# 2. 서비스 시작
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f backend

# 4. 헬스 체크
curl http://localhost:8000/health
```

---

## 📋 배포 후 확인사항

### 1. 헬스 체크
```bash
curl https://api.yourdomain.com/health
# Expected: {"status":"ok"}
```

### 2. 봇 상태 확인
```bash
# 로그인
TOKEN=$(curl -s -X POST https://api.yourdomain.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"admin123"}' | jq -r '.access_token')

# 봇 상태
curl -s https://api.yourdomain.com/bot/status \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### 3. 실시간 데이터 수신
```bash
# WebSocket 연결 테스트
wscat -c wss://api.yourdomain.com/ws/user/6?token=$TOKEN
```

### 4. 거래 내역 확인
```bash
curl -s https://api.yourdomain.com/trades/recent-trades?limit=10 \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## ⚡ 긴급 대응

### 봇 긴급 정지
```bash
curl -X POST https://api.yourdomain.com/bot/stop \
  -H "Authorization: Bearer $TOKEN"
```

### 모든 포지션 강제 청산
```python
# backend/scripts/emergency_close_all.py
async def close_all_positions():
    # 모든 사용자의 열린 포지션 조회
    # Bitget API로 시장가 청산
    pass
```

---

## 📊 모니터링 대시보드

### Grafana + Prometheus
```yaml
# docker-compose.yml에 추가
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

**모니터링 지표**:
- 봇 실행 상태
- 주문 성공/실패율
- API 응답 시간
- WebSocket 연결 수
- 데이터베이스 쿼리 성능

---

## 🚨 알려진 이슈 및 해결책

### 1. 차트 서비스 비활성화
**증상**: 프론트엔드 차트가 업데이트되지 않음
**원인**: market_queue 경쟁 이슈
**해결**: 위의 "차트 서비스 복구" 참조

### 2. WebSocket ping 경고
**증상**: `Invalid JSON: ping`
**영향**: 없음 (정상 동작)
**해결**: WebSocket 핸들러에서 ping 메시지 무시하도록 수정

### 3. 전략 시그니처 불일치
**증상**: `unexpected keyword argument 'current_price'`
**해결**: ✅ `strategy_loader.py`에서 전략별로 다른 시그니처 사용하도록 수정됨

---

## 📝 체크리스트 요약

- [ ] 차트 서비스 복구 (두 개의 큐 사용)
- [ ] 환경 변수 설정 (.env 파일)
- [ ] CORS 도메인 설정
- [ ] PostgreSQL 마이그레이션 (운영 환경)
- [ ] HTTPS 인증서 설정
- [ ] Rate Limiting 추가
- [ ] 로그 로테이션 설정
- [ ] Docker Compose 파일 작성
- [ ] 모니터링 대시보드 구축
- [ ] 긴급 대응 스크립트 준비
- [ ] 백업 전략 수립

---

**참고 문서**:
- [REAL_TRADING_SETUP.md](REAL_TRADING_SETUP.md)
- [ORDER_EXECUTION_DIAGNOSIS.md](ORDER_EXECUTION_DIAGNOSIS.md)
- Bitget API Docs: https://bitgetlimited.github.io/apidoc/en/mix/

**마지막 테스트**:
- 실전 거래 성공 ✅
- ETH SHORT 0.02 @ $3,056.37
- Order ID: 1380021839811223553
