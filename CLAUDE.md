# AI Trading Platform - 통합 개발 가이드

> **IMPORTANT**: 이 문서는 AI가 코드 수정 및 배포 시 반드시 읽어야 하는 **유일한 필수 가이드**입니다.
> 모든 핵심 정보가 이 문서에 통합되어 있습니다.

**최종 업데이트**: 2025-12-27

---

## 📋 목차

1. [서버 및 인프라 정보](#서버-및-인프라-정보)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [CI/CD 자동 배포](#cicd-자동-배포)
4. [AI 에이전트 아키텍처](#ai-에이전트-아키텍처)
5. [핵심 데이터 구조](#핵심-데이터-구조)
6. [절대 하면 안 되는 것들](#-절대-하면-안-되는-것들)
7. [파일별 수정 규칙](#파일별-수정-규칙)
8. [문제 해결 가이드](#문제-해결-가이드)
9. [API 엔드포인트](#api-엔드포인트)

---

## 서버 및 인프라 정보

### Production Server (Hetzner)

```
서버 IP: 5.161.112.248
서버명: deep-server
위치: Ashburn, VA (USA)
사양: CPX31 (4 vCPU / 8 GB RAM / 160 GB SSD)
OS: Ubuntu 24.04 LTS

프로젝트 경로: /root/service_c/ai-trading-platform
```

### 접속 URL

| 서비스 | URL | 포트 |
|-------|-----|------|
| **Frontend** | http://5.161.112.248:3001 | 3001 |
| **Admin** | http://5.161.112.248:4000 | 4000 |
| **API** | http://5.161.112.248:8000 | 8000 |

> **Note**: 포트 3000은 Freqtrade UI가 사용 중이므로 Frontend는 3001 사용

### SSH 접속

```bash
# SSH 키 기반 접속 (권장)
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248

# 컨테이너 상태 확인
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 "docker ps --filter name=groupc-"

# 백엔드 로그 확인
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 "docker logs groupc-backend --tail 100"
```

### GitHub 저장소

```
Repository: https://github.com/joocy75-hash/AI-Agent-DeepSignal
Branch: main
Remote name: hetzner
```

---

## 시스템 아키텍처

### 서버 그룹 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Hetzner 서버 (8GB RAM)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Group A       │  │   Group B       │  │  Group C    │ │
│  │   Freqtrade     │  │   개인 자동화    │  │  AI 트레이딩 │ │
│  │   (포트 3000)    │  │                 │  │  플랫폼     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
│              각 그룹은 독립된 네트워크로 격리됨                │
└─────────────────────────────────────────────────────────────┘
```

### Group C (AI Trading Platform) 컨테이너 구성

| 컨테이너 | 역할 | 포트 | 메모리 한도 | CPU 한도 |
|---------|------|------|-----------|---------|
| `groupc-backend` | FastAPI + AI 에이전트 | 8000 | 2GB | 2.0 |
| `groupc-frontend` | 사용자 대시보드 | 3001→3000 | 256MB | 0.5 |
| `groupc-admin` | 관리자 페이지 | 4000 | 256MB | 0.5 |
| `groupc-postgres` | PostgreSQL 15 | 5432 | 1GB | 1.0 |
| `groupc-redis` | Redis 7 캐시 | 6379 | 256MB | 0.5 |

### 기술 스택

| 컴포넌트 | 기술 |
|---------|------|
| Frontend | React 18 + Vite |
| Admin | React 18 + Vite |
| Backend | FastAPI + Python 3.11 |
| Database | PostgreSQL 15 Alpine |
| Cache | Redis 7 Alpine |
| AI | Gemini / DeepSeek |
| Container | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## CI/CD 자동 배포

### 자동 배포 흐름

```
git push hetzner main
        │
        ▼
┌─────────────────────────────────────────┐
│           GitHub Actions                 │
├─────────────────────────────────────────┤
│  1. Build & Test (1분)                   │
│     - Python 구문 검사                   │
│     - Frontend 빌드 확인                 │
│                                         │
│  2. Deploy to Production (3분)           │
│     - SSH로 서버 접속                    │
│     - rsync로 코드 동기화                │
│     - Docker 이미지 재빌드              │
│     - 서비스 재시작                      │
│                                         │
│  3. Verify Deployment (1분)              │
│     - API 헬스체크                       │
│     - Frontend 접근 확인                 │
└─────────────────────────────────────────┘
```

### 배포 방법

```bash
# 1. 코드 수정 후 커밋
git add .
git commit -m "변경 내용 설명"

# 2. GitHub에 푸시 → 자동 배포 시작
git push hetzner main

# 3. 배포 상태 확인
gh run list -R joocy75-hash/AI-Agent-DeepSignal --limit 3
gh run watch <RUN_ID> -R joocy75-hash/AI-Agent-DeepSignal
```

### GitHub Secrets (설정 완료됨)

| Secret | 설명 |
|--------|------|
| `HETZNER_SERVER_IP` | 서버 IP (5.161.112.248) |
| `HETZNER_SSH_PRIVATE_KEY` | SSH 배포 키 |
| `POSTGRES_PASSWORD` | DB 비밀번호 |
| `REDIS_PASSWORD` | Redis 비밀번호 |
| `JWT_SECRET` | JWT 시크릿 |
| `ENCRYPTION_KEY` | Fernet 암호화 키 |
| `VITE_API_URL` | API URL |
| `CORS_ORIGINS` | CORS 허용 도메인 |
| `AI_PROVIDER` | AI 제공자 (gemini) |
| `GEMINI_API_KEY` | Gemini API 키 |
| `DEEPSEEK_API_KEY` | DeepSeek API 키 |

### 수동 배포 (긴급 시)

```bash
# 1. SSH 접속
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248

# 2. 프로젝트 디렉토리로 이동
cd /root/service_c/ai-trading-platform

# 3. 코드 동기화 (로컬에서)
rsync -avz --exclude 'node_modules' --exclude '.git' \
  -e "ssh -i ~/.ssh/hetzner_deploy_key" \
  ./ root@5.161.112.248:/root/service_c/ai-trading-platform/

# 4. 서비스 재빌드 및 재시작
docker compose -f docker-compose.production.yml build --no-cache
docker compose -f docker-compose.production.yml up -d
```

---

## AI 에이전트 아키텍처

### 4개 AI 에이전트 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    ETH Autonomous Strategy                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Market Regime   │  │ Signal Validator│                   │
│  │ Agent (AI)      │  │ Agent (AI)      │                   │
│  │ - 시장환경분석  │  │ - 신호검증      │                   │
│  │ - 추세/횡보감지 │  │ - 중복진입방지  │                   │
│  └─────────────────┘  └─────────────────┘                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Risk Monitor    │  │ Portfolio       │                   │
│  │ Agent           │  │ Optimizer Agent │                   │
│  │ - 리스크감시   │  │ (AI)            │                   │
│  │ - 청산가경고   │  │ - 5-40% 범위    │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 현재 활성 전략

```
전략명: ETH AI Autonomous 40% Margin Strategy
전략코드: eth_autonomous_40pct
심볼: ETHUSDT
최대 마진: 40% (하드코딩 - 절대 변경 금지)
레버리지: 8-15x (변동성 기반 동적)
손절: ATR × 1.5~2.5 (~1.5%)
익절: ATR × 3.0~5.0 (~3%, 1:2 R:R)
```

### AI Service 설정

| Provider | Model | 용도 | 비용 |
|----------|-------|------|------|
| Gemini | gemini-pro | Primary | Google Cloud 크레딧 |
| DeepSeek | deepseek-chat | Fallback | ~$0.0002/call |

---

## 핵심 데이터 구조

### Position 구조 (절대 변경 금지)

```python
current_position = {
    "side": "long" | "short",
    "entry_price": float,
    "size": float,
    "pnl": float,              # Unrealized PnL (USDT)
    "pnl_percent": float,      # Unrealized PnL (%)
    "leverage": int,
    "margin": float,
    "liquidation_price": float,
    "holding_minutes": int,
}
```

### Signal 구조 (절대 변경 금지)

```python
signal_result = {
    "action": "buy" | "sell" | "hold" | "close",
    "confidence": float,        # 0.0 - 1.0
    "stop_loss_percent": float,
    "take_profit_percent": float,
    "position_size_percent": float,
    "leverage": int,
    "reasoning": str,
    "market_regime": str,
    "ai_powered": bool,
    "strategy_type": str,
}
```

---

## 🚨 절대 하면 안 되는 것들

### ❌ 1. docker cp로 파일 복사 후 "배포 완료" 선언

```bash
# ❌ 잘못된 예 - 컨테이너 재시작 시 파일 사라짐!
docker cp my_file.py groupc-backend:/app/src/

# ✅ 올바른 방법 - GitHub에 푸시하면 자동 배포됨
git add . && git commit -m "fix" && git push hetzner main
```

### ❌ 2. 40% 마진 한도 변경

```python
# ❌ 절대 변경 금지 - MarginCapEnforcer40Pct
MAX_MARGIN_PERCENT = 40.0  # 이 값 변경 금지!
```

### ❌ 3. current_position 데이터 구조 변경

이 구조는 여러 파일에서 사용됨 - 변경 시 전체 시스템 영향

### ❌ 4. --no-cache 없이 프론트엔드 빌드

```bash
# ❌ VITE_API_URL이 캐시된 값으로 빌드될 수 있음
docker compose build frontend

# ✅ 올바른 방법
docker compose build --no-cache frontend
```

### 🔴 절대 수정 금지 컴포넌트

| Component | Location | Reason |
|-----------|----------|--------|
| `MarginCapEnforcer40Pct` | `eth_ai_autonomous_40pct_strategy.py` | 40% 마진 한도 |
| `_check_exit_conditions()` | 동일 파일 | 익절/손절 로직 |
| 포지션 동기화 | `bot_runner.py:627-670` | 봇 시작 시 동기화 |
| AI Agent 초기화 | `strategy_loader.py` | 4개 에이전트 생성 |

---

## 파일별 수정 규칙

### bot_runner.py (⚠️ 핵심 파일)

```
위치: backend/src/services/bot_runner.py
크기: ~2700 lines
주의: 두 개의 봇 루프 존재!
```

**수정 시 체크리스트:**
- [ ] 두 루프 모두 동일하게 수정했는가? (instance loop + legacy loop)
- [ ] `current_position` 동기화 로직 유지했는가?
- [ ] AI 에이전트 초기화 순서 유지했는가?

### strategy_loader.py

```
위치: backend/src/services/strategy_loader.py
```

**수정 시 체크리스트:**
- [ ] `generate_signal_with_strategy()` 인터페이스 유지했는가?
- [ ] `current_position` 파라미터 전달했는가?

### eth_ai_autonomous_40pct_strategy.py

```
위치: backend/src/strategies/eth_ai_autonomous_40pct_strategy.py
```

**수정 시 체크리스트:**
- [ ] 40% 마진 한도 유지했는가?
- [ ] `_check_exit_conditions()` 로직 유지했는가?
- [ ] 4개 AI 에이전트 초기화 유지했는가?

---

## 문제 해결 가이드

### 🚨 PostgreSQL 비밀번호 인증 실패 (가장 흔한 문제)

**증상**: 백엔드 로그에 `password authentication failed for user "trading_user"` 에러

**원인**: PostgreSQL Docker 볼륨은 **최초 생성 시에만** `POSTGRES_PASSWORD` 환경변수를 사용합니다.
이미 존재하는 볼륨은 새 비밀번호를 무시하므로, .env 파일의 비밀번호와 볼륨 내 비밀번호가 불일치할 수 있습니다.

**해결 방법**:

```bash
# 1. 현재 데이터 백업
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker exec groupc-postgres pg_dump -U trading_user trading_prod > /root/service_c/backup_trading_prod.sql"

# 2. 비밀번호 수동 변경 (데이터 보존)
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker exec groupc-postgres psql -U trading_user -d trading_prod -c \"ALTER USER trading_user WITH PASSWORD 'TradingPostgres2024!';\""

# 3. PostgreSQL 재시작
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker restart groupc-postgres && sleep 5 && docker restart groupc-backend"
```

**또는 볼륨 재생성** (데이터 손실 주의):

```bash
# 1. 백업 먼저!
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker exec groupc-postgres pg_dump -U trading_user trading_prod > /root/service_c/backup.sql"

# 2. 볼륨 삭제 및 재생성
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 << 'EOF'
cd /root/service_c/ai-trading-platform
docker compose -f docker-compose.production.yml down
docker volume rm ai-trading-platform_groupc_postgres_data
docker compose -f docker-compose.production.yml up -d postgres
sleep 10
# 백업 복원
cat /root/service_c/backup.sql | docker exec -i groupc-postgres psql -U trading_user -d trading_prod
docker compose -f docker-compose.production.yml up -d
EOF
```

**예방책**: 이 프로젝트는 PostgreSQL init 스크립트가 설정되어 있어, 컨테이너 시작 시 자동으로 비밀번호를 동기화합니다.

---

### 🚨 Alembic 마이그레이션 실패

**증상**: 백엔드가 시작되지 않고 `Migration attempt X/5...` 반복

**해결 방법**:

```bash
# 1. PostgreSQL 연결 테스트
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker exec groupc-backend python -c \"import psycopg2; conn = psycopg2.connect(host='postgres', port=5432, user='trading_user', password='TradingPostgres2024!', database='trading_prod'); print('OK')\""

# 2. 연결 실패 시 → 위의 PostgreSQL 비밀번호 문제 해결 참조

# 3. 마이그레이션 수동 실행
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker exec groupc-backend alembic upgrade head"
```

---

### 🔴 컨테이너 상태 확인

```bash
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker ps --filter name=groupc- --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```

### 🔴 백엔드 로그 확인

```bash
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker logs groupc-backend --tail 100"
```

### 🔴 AI 에이전트 작동 확인

```bash
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker logs groupc-backend --tail 100 2>&1 | grep -E 'AI call|Market regime|agents initialized'"
```

### 🔴 서비스 재시작

```bash
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "cd /root/service_c/ai-trading-platform && docker compose -f docker-compose.production.yml restart"
```

### 🔴 디스크 용량 확인

```bash
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 "df -h / && docker system df"
```

### 🔴 Docker 캐시 정리 (용량 부족 시)

```bash
# 안전한 정리
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker container prune -f && docker image prune -f"

# 전체 정리 (주의: 미사용 이미지 모두 삭제)
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 \
  "docker system prune -a"
```

---

## API 엔드포인트

### Auth
- `POST /api/v1/auth/login` - 로그인
- `POST /api/v1/auth/register` - 회원가입
- `POST /api/v1/auth/refresh` - 토큰 갱신

### Bot
- `GET /api/v1/bot/status` - 봇 상태
- `POST /api/v1/bot/start` - 봇 시작
- `POST /api/v1/bot/stop` - 봇 중지

### Strategy
- `GET /api/v1/strategy/list` - 전략 목록
- `GET /api/v1/ai/strategies/list` - AI 전략 목록

### Health
- `GET /health` - 서버 헬스체크

---

## Database Schema (핵심 테이블)

### strategies
```sql
id, name, code, type, params, is_active, user_id, created_at
```

### trades
```sql
id, user_id, symbol, side, entry_price, exit_price, size, pnl, status, created_at
```

### bot_instances
```sql
id, user_id, strategy_id, symbol, status, allocation_percent, bot_type
```

---

## 보안 Notes

1. **SSH 키 기반 인증** - 비밀번호 대신 SSH 키 사용
2. **GitHub Secrets** - 민감한 정보는 모두 GitHub Secrets에 저장
3. **JWT tokens expire** - Access: 1시간, Refresh: 7일
4. **리소스 격리** - 각 그룹은 독립된 Docker 네트워크 사용

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2025-12-27 | **PostgreSQL 비밀번호 문제 해결** - 볼륨 재생성 및 문서화 |
| 2025-12-27 | **Dockerfile 개선** - 마이그레이션 실패 시 컨테이너 종료 로직 추가 |
| 2025-12-27 | **PostgreSQL init 스크립트 추가** - 자동 초기화 설정 |
| 2025-12-27 | **문제 해결 가이드 추가** - PostgreSQL/Alembic 에러 해결 방법 |
| 2025-12-27 | Hetzner 신규 서버(5.161.112.248)로 이전 |
| 2025-12-27 | GitHub Actions CI/CD 자동 배포 구축 |
| 2025-12-27 | Group C 전용 docker-compose.production.yml 작성 |
| 2025-12-27 | 리소스 제한 설정 (Backend 2GB, DB 1GB 등) |
| 2025-12-18 | 포지션 동기화 버그 수정 |
| 2025-12-18 | MarketRegimeAgent 캔들 데이터 전달 문제 해결 |

---

**⚠️ 이전 서버(158.247.245.197)는 삭제되었습니다. 위 정보만 참고하세요.**
