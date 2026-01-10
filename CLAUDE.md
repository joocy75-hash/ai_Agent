# AI Trading Platform - 통합 개발 가이드

> **IMPORTANT**: 이 문서는 AI가 코드 수정 및 배포 시 반드시 읽어야 하는 **유일한 필수 가이드**입니다.

**최종 업데이트**: 2026-01-11

---

## 📋 목차

1. [프로젝트 분리 정책](#프로젝트-분리-정책) ⭐ CRITICAL
2. [핵심 아키텍처](#핵심-아키텍처)
3. [서버 및 배포](#서버-및-배포)
4. [전략 개발](#전략-개발)
5. [데이터 구조](#데이터-구조)
6. [금지 사항](#금지-사항)
7. [문제 해결](#문제-해결)
8. [🔥 주요 배포 문제 및 해결법](#-주요-배포-문제-및-해결법-2026-01-11) ⭐ NEW
9. [진행 중 프로젝트](#진행-중-프로젝트)

---

## 프로젝트 분리 정책

> **⚠️ CRITICAL**: 서버에 여러 프로젝트 공존. **Group C만** 영향받도록 배포/재시작 필수.

### 서버 구조

| 그룹 | 경로 | 프로젝트 | 포트 범위 |
|------|------|---------|---------|
| A | /root/group_a/ | Stock Trading AI | 3000-3099 |
| B | /root/group_b/ | Automation | 3100-3199 |
| **C** | **/root/group_c/** | **AI Trading (이 프로젝트)** | **3200-3299** |
| E | /root/group_e/ | N8N Automation | 3300-3399 |

### 분리 보장 메커니즘

- **컨테이너**: `groupc-` 접두사 (groupc-backend, groupc-frontend 등)
- **네트워크**: `group_c_network` (내부), `proxy-net` (외부 공유)
- **볼륨**: `groupc_` 접두사 (groupc_postgres_data 등)
- **배포**: `deploy.sh group_c deploy` - Group C만 영향

### 안전한 명령어

```bash
# ✅ 안전
./deploy.sh group_c deploy    # Group C만 배포
./deploy.sh group_c restart   # Group C만 재시작
./deploy.sh group_c logs      # Group C 로그
git push hetzner main         # 자동 배포 (Group C만)

# ❌ 위험
docker compose down           # 모든 컨테이너 중지
docker stop groupa-*          # 다른 그룹 조작
docker network rm proxy-net   # 공유 네트워크 삭제
```

---

## 핵심 아키텍처

### 프로젝트 구조 (핵심 파일)

| 경로 | 역할 | 중요도 |
|------|------|--------|
| `backend/src/services/bot_runner.py` | 봇 메인 루프 (~2700줄) | ⭐⭐⭐ |
| `backend/src/services/strategy_loader.py` | 전략 코드→클래스 매핑 | ⭐⭐⭐ |
| `backend/src/strategies/eth_ai_fusion_strategy.py` | 메인 트레이딩 전략 | ⭐⭐⭐ |
| `backend/src/api/bot.py` | 봇 시작/중지 API | ⭐⭐ |
| `backend/src/workers/manager.py` | 서버 시작 시 봇 복구 | ⭐⭐ |
| `backend/src/database/models.py` | DB 모델 정의 | ⭐⭐ |
| `docker-compose.production.yml` | 프로덕션 컨테이너 | ⭐⭐ |
| `.github/workflows/deploy-production.yml` | CI/CD 자동 배포 | ⭐⭐ |

### 디렉토리 구조 (주요)

```
auto-dashboard/
├── backend/src/
│   ├── api/              # REST API 엔드포인트
│   ├── services/         # 비즈니스 로직 (bot_runner, strategy_loader 등)
│   ├── strategies/       # 트레이딩 전략 클래스
│   ├── agents/           # AI 에이전트 (market_regime, signal_validator 등)
│   ├── ml/               # ML 모듈 (features, models)
│   ├── database/         # SQLAlchemy 모델
│   ├── middleware/       # CSRF, Rate Limit, Security
│   └── utils/            # JWT, 암호화, 로그
├── frontend/             # React 사용자 대시보드
├── admin-frontend/       # React 관리자 페이지
└── .github/workflows/    # CI/CD
```

### 컨테이너 리소스

| 컨테이너 | 포트 | 메모리 | CPU |
|---------|------|--------|-----|
| groupc-backend | 8000 | 2GB | 2.0 |
| groupc-frontend | 3000 | 256MB | 0.5 |
| groupc-admin | 4000 | 256MB | 0.5 |
| groupc-postgres | 5432 | 1GB | 1.0 |
| groupc-redis | 6379 | 256MB | 0.5 |

### 기술 스택

- **Frontend**: React 18 + Vite
- **Backend**: FastAPI + Python 3.11
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **AI**: Gemini (Primary), DeepSeek (Fallback)
- **거래소**: Bitget, Binance, OKX, Bybit, Gate.io (CCXT)
- **CI/CD**: GitHub Actions

### 다중 거래소 지원 (2026-01-10 구현 완료)

| 거래소 | REST API | WebSocket | Passphrase |
|--------|----------|-----------|------------|
| Bitget | ✅ | ✅ | 필수 |
| Binance | ✅ | ✅ | 불필요 |
| OKX | ✅ | ✅ | 필수 |
| Bybit | ✅ | ✅ | 불필요 |
| Gate.io | ✅ | ✅ | 불필요 |

**핵심 파일**:
- `backend/src/services/exchanges/base.py` - 추상 인터페이스
- `backend/src/services/exchanges/factory.py` - 팩토리 패턴
- `backend/src/services/exchanges/{거래소}.py` - 각 거래소 구현
- `backend/src/services/exchange_service.py` - 사용자별 클라이언트 관리

**사용 예시**:
```python
from src.services.exchange_service import ExchangeService

# 사용자의 거래소 클라이언트 가져오기
client, exchange_name = await ExchangeService.get_user_exchange_client(session, user_id)

# 잔고 조회
balance = await client.get_futures_balance()

# 포지션 조회
positions = await client.get_positions()
```

---

## 서버 및 배포

### Production Server

```
IP: 141.164.55.245
경로: /root/group_c
OS: Ubuntu 24.04 LTS
사양: 4 vCPU / 8GB RAM

Repository: https://github.com/joocy75-hash/AI-Agent-DeepSignal
Branch: main
Remote: hetzner
```

### 접속 URL

| 서비스 | URL | 포트 |
|-------|-----|------|
| Frontend | https://deepsignal.shop | 3201 |
| Admin | https://admin.deepsignal.shop | 3202 |
| API | https://api.deepsignal.shop | 3200 |

### 배포 프로세스

```bash
# 1. 로컬 테스트
python -m py_compile backend/src/main.py  # 구문 검사
cd frontend && npm run build              # 빌드 테스트

# 2. 자동 배포
git add .
git commit -m "변경 내용"
git push hetzner main  # → GitHub Actions 자동 배포

# 3. 배포 모니터링
gh run watch -R joocy75-hash/AI-Agent-DeepSignal

# 4. 검증
curl https://api.deepsignal.shop/health
```

### GitHub Secrets (설정 완료)

- `HETZNER_SERVER_IP`, `HETZNER_SSH_PRIVATE_KEY`
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`
- `JWT_SECRET`, `ENCRYPTION_KEY`
- `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`
- `VITE_API_URL`, `CORS_ORIGINS`

### 수동 배포 (긴급)

```bash
ssh root@141.164.55.245
cd /root/group_c/ai-trading-platform
git pull
docker compose -f docker-compose.production.yml build --no-cache
docker compose -f docker-compose.production.yml up -d
```

---

## 전략 개발

### 전략 시스템 흐름

```
DB (strategies 테이블)
  └─ code: "my_strategy"
       ↓
strategy_loader.py
  └─ load_strategy_class()
       ↓
MyStrategy 클래스
  └─ generate_signal()
       ↓
bot_runner.py
  └─ 주문 실행
```

### 필수 인터페이스

```python
class MyNewStrategy:
    def __init__(self, params: dict = None, user_id: int = None):
        """
        params: DB의 params JSON
        user_id: 사용자 ID (AI 캐싱용)
        """
        self.params = params or {}
        self.user_id = user_id
        # 설정값 로드...

    def generate_signal(
        self,
        current_price: float,
        candles: list,
        current_position: dict = None
    ) -> dict:
        """
        Returns:
        {
            "action": "buy"|"sell"|"hold"|"close",
            "confidence": 0.0~1.0,
            "reason": str,
            "stop_loss": float|None,
            "take_profit": float|None,
            "size": float|None,
            "strategy_type": str
        }
        """
        # 전략 로직...
```

### 전략 등록 절차

1. **파일 생성**: `backend/src/strategies/my_strategy.py`
2. **매핑 추가**: `strategy_loader.py`의 `_create_strategy_instance_internal()`에 추가
   ```python
   if normalized == "my_strategy":
       from ..strategies.my_strategy import MyStrategy
       return MyStrategy(params, user_id=user_id)
   ```
3. **DB 등록**:
   ```bash
   docker exec groupc-postgres psql -U trading_user -d trading_prod -c "
   INSERT INTO strategies (user_id, name, code, params, is_active) VALUES
   (1, '내 전략', 'my_strategy', '{...}', true);"
   ```
4. **배포 및 테스트**: `git push hetzner main`

### 현재 활성 전략

- **이름**: ETH AI Fusion Strategy
- **코드**: `eth_ai_fusion`
- **심볼**: ETHUSDT
- **타임프레임**: 5m
- **레버리지**: 10-20x (변동성 기반)
- **마진 한도**: 40% (하드코딩) - 멀티봇에는 미적용

**로직 요약**:
- 진입: EMA(9/21), RSI(14), MACD, 거래량 점수화 (≥4점)
- ML 게이트: FeaturePipeline + EnsemblePredictor로 진입 차단
- 손절/익절: ATR 기반 (SL: 0.6~1.8%, TP: 1.2~4.5%)
- 트레일링: TP 도달 시 `max(SL, max_profit*0.5)` 보호
- 추매: 0.8% 단위 수익 구간, 최대 3회, 35% 규모

### AI 에이전트 구조

- **Market Regime Agent**: 시장 국면 분석 (추세/횡보)
- **Signal Validator Agent**: 신호 검증, 중복 진입 방지
- **Risk Monitor Agent**: 리스크 감시, 청산가 경고
- **Portfolio Optimizer Agent**: 포지션 크기 최적화 (5-40%)

---

## 데이터 구조

### Position (절대 변경 금지)

```python
current_position = {
    "side": "long"|"short",
    "entry_price": float,
    "size": float,
    "pnl": float,              # Unrealized PnL (USDT)
    "pnl_percent": float,      # Unrealized PnL (%)
    "leverage": int,
    "margin": float,
    "liquidation_price": float,
    "holding_minutes": int
}
```

### Signal (절대 변경 금지)

```python
signal_result = {
    "action": "buy"|"sell"|"hold"|"close",
    "confidence": 0.0~1.0,
    "stop_loss_percent": float,
    "take_profit_percent": float,
    "position_size_percent": float,
    "leverage": int,
    "reasoning": str,
    "market_regime": str,
    "ai_powered": bool,
    "strategy_type": str
}
```

### Database Schema

**strategies**: `id, name, code, params, is_active, user_id`
**trades**: `id, user_id, symbol, side, entry_price, exit_price, size, pnl, status`
**bot_instances**: `id, user_id, strategy_id, symbol, status, allocation_percent`

---

## 금지 사항

### ❌ 절대 금지

1. **docker cp 배포**
   ```bash
   # ❌ 컨테이너 재시작 시 사라짐
   docker cp file.py groupc-backend:/app/
   # ✅ Git 푸시로 배포
   git push hetzner main
   ```

2. **기존 단일 봇 전략의 40% 마진 한도 변경**
   ```python
   # ETHAIFusionStrategy 등 기존 전략에만 적용
   MAX_MARGIN_PERCENT = 40.0  # 절대 변경 금지
   ```
   > **참고**: 멀티봇 시스템은 잔고 초과만 체크 (40% 한도 미적용)

3. **데이터 구조 변경**
   - `current_position`, `signal_result` 구조 유지 필수

4. **Frontend 빌드 캐시**
   ```bash
   # ❌ 환경변수 캐시될 수 있음
   docker compose build frontend
   # ✅ 항상 --no-cache 사용
   docker compose build --no-cache frontend
   ```

### 🔴 절대 수정 금지

- `ETHAIFusionStrategy` 전략 로직
- `_risk_targets()` 익절/손절 로직
- `bot_runner.py:627-670` 포지션 동기화
- `strategy_loader.py` AI Agent 초기화

### 파일 수정 체크리스트

**bot_runner.py** (~2700줄):
- [ ] 두 루프 모두 수정? (instance + legacy)
- [ ] position 동기화 유지?
- [ ] AI 에이전트 초기화 순서 유지?

**strategy_loader.py**:
- [ ] `generate_signal_with_strategy()` 인터페이스 유지?
- [ ] `current_position` 파라미터 전달?

**eth_ai_fusion_strategy.py**:
- [ ] 40% 마진 한도 유지? (멀티봇은 별도)
- [ ] `_risk_targets()` 로직 유지?
- [ ] ML 연동 유지?

---

## 문제 해결

### PostgreSQL 비밀번호 실패

**증상**: `password authentication failed`

**해결**:
```bash
# 방법 1: 비밀번호 변경 (데이터 보존)
ssh root@141.164.55.245 "docker exec groupc-postgres \
  psql -U trading_user -d trading_prod -c \
  \"ALTER USER trading_user WITH PASSWORD 'TradingPostgres2024!';\""

# 방법 2: 볼륨 재생성 (백업 필수)
ssh root@141.164.55.245 << 'EOF'
docker exec groupc-postgres pg_dump -U trading_user trading_prod > /tmp/backup.sql
cd /root/group_c/ai-trading-platform
docker compose -f docker-compose.production.yml down
docker volume rm ai-trading-platform_groupc_postgres_data
docker compose -f docker-compose.production.yml up -d postgres
sleep 10
cat /tmp/backup.sql | docker exec -i groupc-postgres psql -U trading_user -d trading_prod
docker compose -f docker-compose.production.yml up -d
EOF
```

### Alembic 마이그레이션 실패

```bash
# 연결 테스트
docker exec groupc-backend python -c "import psycopg2; \
  conn = psycopg2.connect(host='postgres', user='trading_user', \
  password='TradingPostgres2024!', database='trading_prod'); print('OK')"

# 수동 마이그레이션
docker exec groupc-backend alembic upgrade head
```

### 유용한 명령어

```bash
# 상태 확인
docker ps --filter name=groupc-
docker logs groupc-backend --tail 100
docker logs groupc-backend | grep -E 'AI call|agents initialized'

# 서비스 재시작
cd /root/group_c/ai-trading-platform
docker compose -f docker-compose.production.yml restart

# 디스크 정리
docker container prune -f
docker image prune -f

# 롤백
git revert HEAD
git push hetzner main
```

### API 테스트

```bash
# 헬스 체크
curl https://api.deepsignal.shop/health

# 로그인 (쿠키 저장)
curl -c cookies.txt -X POST "https://api.deepsignal.shop/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'

# CSRF 토큰 추출
CSRF_TOKEN=$(grep csrf cookies.txt | awk '{print $7}')

# 인증 API
curl -b cookies.txt -X GET "https://api.deepsignal.shop/api/v1/bot/status" \
  -H "X-CSRF-Token: $CSRF_TOKEN"
```

---

## 🔥 주요 배포 문제 및 해결법 (2026-01-11)

> **⚠️ CRITICAL**: 이 섹션은 반복되는 배포 문제를 방지하기 위한 필수 가이드입니다.

### 1. Frontend 변경사항이 반영되지 않는 문제

**증상**:
- 코드 수정 후 `git push` 완료
- GitHub Actions 배포 성공
- 브라우저 캐시 삭제, 시크릿 모드로도 변경사항 미반영

**원인**:
1. **Docker 빌드 캐시**: Vite 빌드가 캐시되어 이전 번들 사용
2. **GitHub Actions rsync 동기화 실패**: 파일이 서버에 제대로 전송되지 않음

**해결법**:
```bash
# 1. 서버에서 직접 캐시 없이 빌드 (필수!)
ssh root@141.164.55.245 "cd /root/group_c && \
  docker compose -f docker-compose.production.yml build --no-cache frontend && \
  docker compose -f docker-compose.production.yml up -d frontend --force-recreate"

# 2. 빌드 검증 - 새 번들 해시 확인
curl -s https://deepsignal.shop/ | grep -o 'index-[^"]*\.js'
# 결과 예: index-ByPJuAUQ.js (해시가 변경되어야 함)

# 3. CSS/JS 내용 검증
ssh root@141.164.55.245 "docker exec groupc-frontend \
  cat /usr/share/nginx/html/assets/index-*.css | grep 'trading-page'"
```

**예방책**:
```bash
# ❌ 절대 금지 - 캐시된 빌드 사용
docker compose build frontend

# ✅ 항상 사용 - 캐시 없는 빌드
docker compose build --no-cache frontend
```

---

### 2. .env 파일 삭제/손상 문제

**증상**:
- `rsync --delete` 실행 후 컨테이너 시작 실패
- Redis: `dependency failed to start: container groupc-redis is unhealthy`
- Backend: `ENCRYPTION_KEY environment variable is required`

**원인**:
수동 rsync에서 `--delete` 옵션이 서버의 `.env` 파일을 삭제함

**⚠️ 위험한 명령어**:
```bash
# ❌ 절대 금지 - .env 파일 삭제됨
rsync -avz --delete /local/path/ root@server:/remote/path/

# ✅ 안전한 rsync - .env 제외
rsync -avz --exclude='.env' --exclude='*.log' /local/path/ root@server:/remote/path/
```

**복구 방법**:
```bash
# 1. .env 파일 복구 (필수 환경변수)
ssh root@141.164.55.245 "cat > /root/group_c/.env << 'EOF'
POSTGRES_PASSWORD=TradingPostgres2024!
REDIS_PASSWORD=TradingRedis2024!
JWT_SECRET=TradingJWTSecret2024!SuperSecretKey123456
ENCRYPTION_KEY=<유효한_Fernet_키>
VITE_API_URL=https://api.deepsignal.shop
CORS_ORIGINS=https://deepsignal.shop,https://admin.deepsignal.shop
AI_PROVIDER=gemini
GEMINI_API_KEY=<실제_키>
DEEPSEEK_API_KEY=<실제_키>
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF"

# 2. 컨테이너 재시작
ssh root@141.164.55.245 "cd /root/group_c && \
  docker compose -f docker-compose.production.yml up -d --force-recreate"
```

---

### 3. ENCRYPTION_KEY 형식 오류

**증상**:
```
src.utils.crypto_secrets.CryptoError: ENCRYPTION_KEY must be a valid URL-safe base64 32-byte key.
```

**원인**:
`ENCRYPTION_KEY`가 유효한 Fernet 키 형식이 아님

**요구사항**:
- URL-safe Base64 인코딩
- 정확히 32바이트 키
- 예: `AkAsKsbo6oHBvuvjpLbnD4UI12ZnaYaGlt3fsfP6wvc=`

**새 키 생성**:
```bash
# Python으로 유효한 Fernet 키 생성
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# 출력 예: AkAsKsbo6oHBvuvjpLbnD4UI12ZnaYaGlt3fsfP6wvc=
```

**⚠️ 주의사항**:
- 키 변경 시 기존 암호화된 데이터(거래소 API 키 등) **복호화 불가**
- 사용자는 거래소 API 키를 **재등록**해야 함
- 가능하면 기존 키 백업 후 사용

---

### 4. Redis 볼륨 손상

**증상**:
```
*** FATAL CONFIG FILE ERROR (Redis 7.4.7) ***
Reading the configuration file, at line 3
>>> 'requirepass "--maxmemory" "200mb"'
wrong number of arguments
```

**원인**:
Redis 볼륨에 잘못된 설정 파일이 저장됨

**해결법**:
```bash
# Redis 볼륨 삭제 후 재생성
ssh root@141.164.55.245 "cd /root/group_c && \
  docker compose -f docker-compose.production.yml stop redis && \
  docker rm groupc-redis && \
  docker volume rm groupc_redis_data 2>/dev/null; \
  docker compose -f docker-compose.production.yml up -d redis"

# 상태 확인 (healthy 될 때까지 대기)
ssh root@141.164.55.245 "docker ps --filter name=groupc-redis"
```

---

### 5. CSRF 토큰 오류 (Cross-Subdomain)

**증상**:
```
403 Forbidden: CSRF token missing or invalid
```

**원인**:
- `api.deepsignal.shop`에서 설정한 쿠키를 `deepsignal.shop`에서 접근 불가
- Cookie Domain 설정 누락

**해결법** (`docker-compose.production.yml`):
```yaml
backend:
  environment:
    # ⚠️ CRITICAL: Cross-subdomain 인증에 필수
    COOKIE_DOMAIN: ".deepsignal.shop"   # 점(.)으로 시작해야 서브도메인 공유
    COOKIE_SAMESITE: "none"              # Cross-origin 요청 허용
    COOKIE_SECURE: "true"                # HTTPS 필수
```

**검증**:
```bash
# 로그인 후 쿠키 확인
curl -c cookies.txt -X POST "https://api.deepsignal.shop/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"password"}'

# csrf_token 쿠키에 Domain=.deepsignal.shop 확인
cat cookies.txt | grep csrf
```

---

### 6. GitHub Actions rsync 동기화 실패

**증상**:
- GitHub Actions 로그: "success"
- 서버 파일: 변경되지 않음

**원인**:
- SSH 키 권한 문제
- rsync 경로 불일치
- 네트워크 일시적 오류

**디버깅**:
```bash
# 1. 서버 파일 타임스탬프 확인
ssh root@141.164.55.245 "ls -la /root/group_c/frontend/src/components/layout/MainLayout.jsx"

# 2. 로컬 파일과 비교
ssh root@141.164.55.245 "md5sum /root/group_c/frontend/src/components/layout/MainLayout.jsx"
md5 frontend/src/components/layout/MainLayout.jsx

# 3. 수동 동기화 (긴급 시)
rsync -avz --exclude='.env' --exclude='node_modules' --exclude='__pycache__' \
  /Users/mr.joo/Desktop/auto-dashboard/ root@141.164.55.245:/root/group_c/
```

**예방책**:
- 배포 후 항상 서버 파일 검증
- `git push` 후 서버에서 `git pull` 확인

---

### 7. 컨테이너 전체 복구 절차

모든 컨테이너가 비정상일 때 전체 복구:

```bash
# 1. 모든 컨테이너 중지
ssh root@141.164.55.245 "cd /root/group_c && \
  docker compose -f docker-compose.production.yml down"

# 2. .env 파일 확인/복구
ssh root@141.164.55.245 "cat /root/group_c/.env"

# 3. 볼륨 상태 확인 (필요시 Redis만 삭제)
ssh root@141.164.55.245 "docker volume ls | grep groupc"

# 4. 이미지 재빌드 (캐시 없이)
ssh root@141.164.55.245 "cd /root/group_c && \
  docker compose -f docker-compose.production.yml build --no-cache"

# 5. 컨테이너 시작
ssh root@141.164.55.245 "cd /root/group_c && \
  docker compose -f docker-compose.production.yml up -d"

# 6. 상태 확인
ssh root@141.164.55.245 "docker ps --filter name=groupc- --format 'table {{.Names}}\t{{.Status}}'"

# 7. 서비스 검증
curl https://api.deepsignal.shop/health
curl -s https://deepsignal.shop/ | head -5
```

---

### 빠른 참조 - 배포 체크리스트

```
□ 코드 수정 완료
□ 로컬 빌드 테스트 (npm run build)
□ git push hetzner main
□ GitHub Actions 완료 확인
□ 서버 파일 동기화 확인 (md5sum 비교)
□ --no-cache로 Docker 빌드
□ 컨테이너 재시작 (--force-recreate)
□ 새 번들 해시 확인 (index-*.js)
□ 브라우저 강력 새로고침 (Ctrl+Shift+R)
□ 기능 테스트
```

---

## API 엔드포인트

**Auth**: `/api/v1/auth/login`, `/api/v1/auth/register`, `/api/v1/auth/refresh`
**Bot**: `/api/v1/bot/status`, `/api/v1/bot/start`, `/api/v1/bot/stop`
**Strategy**: `/api/v1/strategy/list`, `/api/v1/ai/strategies/list`
**Health**: `/health`

---

## 보안

- SSH 키 기반 인증
- GitHub Secrets로 민감 정보 관리
- JWT 토큰 만료 (Access: 1h, Refresh: 7d)
- 그룹별 Docker 네트워크 격리

### 보안 수정 이력 (2026-01-10)

| 취약점 | 파일 | 상태 |
|--------|------|------|
| Rate Limit JWT 미인증 | `middleware/rate_limit.py` | ✅ 수정됨 |
| ReDoS 정규식 취약점 | `utils/validators.py` | ✅ 수정됨 |
| Pydantic ClassVar 오류 | `schemas/account_schema.py` | ✅ 수정됨 |
| 업로드 용량 제한 | `api/upload.py` | ✅ 이미 구현됨 |

---

## 진행 중 프로젝트

### 🚀 멀티봇 트레이딩 시스템 (v2.0)

사용자가 여러 전략 봇을 동시에 운용할 수 있는 시스템 구현 중

**상태**: 계획 수립 완료, 구현 대기

**버전**: v2.0 (2026-01-10 업데이트)

**핵심 문서**:
- [상세 구현 계획서](./docs/MULTI_BOT_IMPLEMENTATION_PLAN.md)
- [진행 상황 추적](./docs/MULTIBOT_PROGRESS.md)
- [구현 스킬](./.claude/skills/multibot-implementation.md)

**v2.0 주요 변경**:
| 항목 | v1 | v2 |
|------|----|----|
| 마진 한도 | 40% 강제 | **잔고 초과만 체크** |
| 최대 봇 | 10개 | **5개** |
| 전략 템플릿 | StrategyTemplate (신규) | **TrendBotTemplate (기존 활용)** |
| 단일 봇 | 레거시 호환 유지 | **폐지** |

**주요 기능**:
- 전략별 카드 UI (금액만 입력하면 즉시 시작)
- 사용자당 최대 5개 봇 동시 운용
- 잔고 초과만 체크 (40% 한도 없음)
- 봇별 독립 수익률 추적

**핵심 로직 변경**:
```python
# v1 (40% 한도)
if new_percent > 40.0:
    return (False, "마진 한도 초과")

# v2 (잔고 초과만 체크)
if used_amount + amount > total_balance:
    return (False, "잔고가 부족합니다")
```

**작업 분배** (여러 AI 협업):
```
Phase 1: DB 스키마        → AI-1
Phase 2: 백엔드 API       → AI-1, AI-2
Phase 3: 봇 러너 수정     → AI-2, AI-3
Phase 4: 프론트엔드       → AI-3, AI-4
Phase 5: 테스트/배포      → AI-4
```

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-01-11 | **배포 문제 해결 가이드 추가** - Frontend 캐시, .env 복구, CSRF 설정, Redis 볼륨 등 7가지 주요 문제 문서화 |
| 2026-01-10 | **멀티봇 시스템 v2.0** - 40% 한도 제거, 최대 봇 5개, TrendBotTemplate 활용 |
| 2026-01-10 | **멀티봇 시스템** - 구현 계획서 및 스킬 파일 작성 |
| 2026-01-10 | **다중 거래소 지원** - Binance, OKX, Bybit, Gate.io 추가 (REST+WS) |
| 2026-01-10 | **보안 수정** - Rate Limit JWT 인증, ReDoS 취약점 수정 |
| 2026-01-10 | **테스트 추가** - ExchangeFactory 24개 유닛 테스트 |
| 2026-01-09 | 서울 서버 IP 및 통합 배포 스크립트 적용 |
| 2026-01-02 | 프로젝트 구조 및 상세 가이드 추가 |
| 2026-01-01 | ETH AI Fusion 전략으로 전면 교체 |
| 2025-12-27 | Hetzner 서버 이전 및 CI/CD 구축 |

---

**⚠️ 이전 서버(158.247.245.197)는 삭제되었습니다.**
