# AI Trading Platform - 통합 개발 가이드

> **IMPORTANT**: 이 문서는 AI가 코드 수정 및 배포 시 반드시 읽어야 하는 **유일한 필수 가이드**입니다.
> 모든 핵심 정보가 이 문서에 통합되어 있습니다.

**최종 업데이트**: 2026-01-02

---

## 📋 목차

1. [📁 프로젝트 구조](#-프로젝트-구조) ⭐ NEW
2. [서버 및 인프라 정보](#서버-및-인프라-정보)
3. [시스템 아키텍처](#시스템-아키텍처)
4. [CI/CD 자동 배포](#cicd-자동-배포)
5. [🚀 상세 배포 가이드](#-상세-배포-가이드)
6. [🤖 전략 생성 가이드](#-전략-생성-가이드)
7. [AI 에이전트 아키텍처](#ai-에이전트-아키텍처)
8. [핵심 데이터 구조](#핵심-데이터-구조)
9. [절대 하면 안 되는 것들](#-절대-하면-안-되는-것들)
10. [파일별 수정 규칙](#파일별-수정-규칙)
11. [문제 해결 가이드](#문제-해결-가이드)
12. [API 엔드포인트](#api-엔드포인트)

---

## 📁 프로젝트 구조

```
auto-dashboard/
├── 📁 backend/                          # FastAPI 백엔드 서버
│   ├── src/
│   │   ├── api/                         # API 엔드포인트
│   │   │   ├── auth.py                  # 인증 (로그인, 회원가입, JWT)
│   │   │   ├── bot.py                   # ⭐ 봇 시작/중지 API
│   │   │   ├── bot_instances.py         # 다중 봇 인스턴스 관리
│   │   │   ├── strategy.py              # 전략 CRUD
│   │   │   ├── account.py               # 계정 및 API 키 관리
│   │   │   ├── order.py                 # 주문 및 거래 내역
│   │   │   ├── backtest.py              # 백테스트 실행
│   │   │   ├── health.py                # 헬스 체크
│   │   │   ├── admin_*.py               # 관리자 전용 API
│   │   │   └── ...
│   │   │
│   │   ├── services/                    # 비즈니스 로직 (핵심)
│   │   │   ├── bot_runner.py            # ⭐⭐ 봇 메인 루프 (~2700줄)
│   │   │   ├── strategy_loader.py       # ⭐ 전략 로더 (코드→클래스 매핑)
│   │   │   ├── exchange_service.py      # 거래소 클라이언트 관리
│   │   │   ├── trade_executor.py        # 주문 실행
│   │   │   ├── backtest_engine.py       # 백테스트 엔진
│   │   │   ├── exchanges/               # 거래소 연동
│   │   │   │   ├── bitget.py            # Bitget REST API
│   │   │   │   ├── bitget_ws.py         # Bitget WebSocket
│   │   │   │   └── base.py              # 거래소 기본 클래스
│   │   │   ├── telegram/                # 텔레그램 알림
│   │   │   ├── ai_optimization/         # AI 서비스 최적화
│   │   │   │   ├── integrated_ai_service.py  # 통합 AI 서비스
│   │   │   │   ├── smart_sampling.py    # 스마트 샘플링
│   │   │   │   └── cost_tracker.py      # AI 비용 추적
│   │   │   └── ...
│   │   │
│   │   ├── strategies/                  # 트레이딩 전략 클래스
│   │   │   ├── eth_ai_fusion_strategy.py  # ⭐ 메인 전략 (ETH AI Fusion)
│   │   │   └── __init__.py
│   │   │
│   │   ├── agents/                      # AI 에이전트
│   │   │   ├── market_regime/           # 시장 국면 분석 에이전트
│   │   │   ├── signal_validator/        # 신호 검증 에이전트
│   │   │   ├── risk_monitor/            # 리스크 모니터 에이전트
│   │   │   ├── portfolio_optimizer/     # 포트폴리오 최적화 에이전트
│   │   │   └── ml_predictor/            # ML 예측 에이전트
│   │   │
│   │   ├── ml/                          # 머신러닝 모듈
│   │   │   ├── features/                # 피처 엔지니어링
│   │   │   │   ├── feature_pipeline.py  # 피처 파이프라인
│   │   │   │   ├── technical_features.py
│   │   │   │   └── structure_features.py
│   │   │   ├── models/                  # ML 모델
│   │   │   │   └── ensemble_predictor.py  # 앙상블 예측기
│   │   │   ├── training/                # 학습 스크립트
│   │   │   └── validation/              # 검증 및 백테스트
│   │   │
│   │   ├── database/                    # 데이터베이스
│   │   │   ├── models.py                # SQLAlchemy 모델 정의
│   │   │   ├── db.py                    # DB 연결 관리
│   │   │   └── session.py               # 세션 관리
│   │   │
│   │   ├── schemas/                     # Pydantic 스키마 (요청/응답 검증)
│   │   │   ├── auth_schema.py
│   │   │   ├── bot_schema.py
│   │   │   └── ...
│   │   │
│   │   ├── middleware/                  # 미들웨어
│   │   │   ├── csrf.py                  # CSRF 보호
│   │   │   ├── rate_limit_improved.py   # Rate Limiting
│   │   │   ├── security_headers.py      # 보안 헤더
│   │   │   └── error_handler.py         # 전역 에러 핸들러
│   │   │
│   │   ├── utils/                       # 유틸리티
│   │   │   ├── jwt_auth.py              # JWT 인증
│   │   │   ├── auth_cookies.py          # 쿠키 기반 인증
│   │   │   ├── crypto_secrets.py        # API 키 암호화
│   │   │   └── log_broadcaster.py       # 로그 브로드캐스터
│   │   │
│   │   ├── workers/                     # 백그라운드 워커
│   │   │   └── manager.py               # 봇 매니저 (bootstrap)
│   │   │
│   │   ├── config.py                    # 환경 설정
│   │   └── main.py                      # FastAPI 앱 진입점
│   │
│   ├── alembic/                         # DB 마이그레이션
│   │   ├── versions/                    # 마이그레이션 파일들
│   │   └── env.py
│   │
│   ├── tests/                           # 테스트 코드
│   │   ├── unit/                        # 단위 테스트
│   │   ├── integration/                 # 통합 테스트
│   │   └── ml/                          # ML 테스트
│   │
│   ├── scripts/                         # 유틸리티 스크립트
│   │   ├── train_ml_models.py           # ML 모델 학습
│   │   ├── register_ai_strategy.py      # 전략 등록
│   │   └── emergency_stop_all.py        # 긴급 정지
│   │
│   ├── requirements.txt                 # Python 의존성
│   ├── alembic.ini                      # Alembic 설정
│   ├── Dockerfile                       # Docker 빌드
│   └── README.md
│
├── 📁 frontend/                         # 사용자 대시보드 (React)
│   ├── src/
│   │   ├── api/                         # API 클라이언트
│   │   │   ├── client.js                # Axios 인스턴스 (쿠키 인증)
│   │   │   ├── auth.js                  # 인증 API
│   │   │   ├── bot.js                   # 봇 API
│   │   │   ├── strategy.js              # 전략 API
│   │   │   └── ...
│   │   │
│   │   ├── pages/                       # 페이지 컴포넌트
│   │   │   ├── Dashboard.jsx            # 메인 대시보드
│   │   │   ├── Trading.jsx              # 트레이딩 페이지
│   │   │   ├── Strategy.jsx             # 전략 관리
│   │   │   ├── BotManagement.jsx        # 봇 관리
│   │   │   ├── Settings.jsx             # 설정
│   │   │   ├── Login.jsx                # 로그인
│   │   │   └── admin/                   # 관리자 페이지
│   │   │
│   │   ├── components/                  # 재사용 컴포넌트
│   │   │   ├── dashboard/               # 대시보드 위젯
│   │   │   ├── bot/                     # 봇 관련 컴포넌트
│   │   │   ├── strategy/                # 전략 관련 컴포넌트
│   │   │   ├── grid/                    # 그리드 봇 컴포넌트
│   │   │   └── ...
│   │   │
│   │   ├── context/                     # React Context
│   │   │   ├── AuthContext.jsx          # 인증 상태
│   │   │   ├── WebSocketContext.jsx     # WebSocket 연결
│   │   │   └── ThemeContext.jsx         # 테마 설정
│   │   │
│   │   ├── hooks/                       # Custom Hooks
│   │   ├── App.jsx                      # 메인 App
│   │   └── main.jsx                     # 진입점
│   │
│   ├── vite.config.js                   # Vite 설정
│   ├── tailwind.config.js               # Tailwind CSS 설정
│   ├── package.json                     # NPM 의존성
│   ├── Dockerfile                       # Docker 빌드
│   └── .env                             # 환경 변수 (VITE_API_URL)
│
├── 📁 admin-frontend/                   # 관리자 페이지 (React)
│   ├── src/
│   │   ├── api/                         # 관리자 API 클라이언트
│   │   ├── pages/                       # 관리자 페이지
│   │   │   ├── AdminDashboard.jsx       # 관리자 대시보드
│   │   │   └── Login.jsx                # 관리자 로그인
│   │   └── components/
│   ├── package.json
│   └── Dockerfile
│
├── 📁 tools/                            # 개발 도구 및 에이전트
│   ├── agents/                          # CI/CD 에이전트
│   │   ├── dev_assistant.py             # 개발 어시스턴트
│   │   ├── ci_agent.py                  # CI 에이전트
│   │   └── ops_agent.py                 # 운영 에이전트
│   └── ...
│
├── 📁 monitoring/                       # 모니터링 설정
│   ├── prometheus.yml                   # Prometheus 설정
│   └── grafana/                         # Grafana 대시보드
│
├── 📁 .github/                          # GitHub 설정
│   └── workflows/
│       └── deploy-production.yml        # ⭐ 자동 배포 워크플로우
│
├── 📁 .claude/                          # Claude 설정
│   └── settings.local.json              # 로컬 설정
│
├── docker-compose.yml                   # 로컬 개발용
├── docker-compose.production.yml        # ⭐ 프로덕션 배포용
├── docker-compose.monitoring.yml        # 모니터링 스택
├── CLAUDE.md                            # ⭐⭐ 이 문서 (필독)
└── README.md
```

### 핵심 파일 요약

| 파일 | 역할 | 중요도 |
|------|------|--------|
| `backend/src/services/bot_runner.py` | 봇 메인 루프, 시그널 처리, 주문 실행 | ⭐⭐⭐ |
| `backend/src/services/strategy_loader.py` | 전략 코드 → 클래스 매핑 | ⭐⭐⭐ |
| `backend/src/strategies/eth_ai_fusion_strategy.py` | 메인 트레이딩 전략 | ⭐⭐⭐ |
| `backend/src/api/bot.py` | 봇 시작/중지 API | ⭐⭐ |
| `backend/src/workers/manager.py` | 서버 시작 시 봇 복구 | ⭐⭐ |
| `backend/src/database/models.py` | DB 모델 정의 | ⭐⭐ |
| `docker-compose.production.yml` | 프로덕션 컨테이너 구성 | ⭐⭐ |
| `.github/workflows/deploy-production.yml` | CI/CD 자동 배포 | ⭐⭐ |

---

## 서버 및 인프라 정보

### Production Server (Seoul)

```
서버 IP: 141.164.55.245
서버명: seoul-server
위치: Seoul, Korea
사양: 4 vCPU / 8 GB RAM (예상)
OS: Ubuntu 24.04 LTS

프로젝트 경로: /root/group_c
```

### 접속 URL (Nginx Proxy)

| 서비스 | URL | 내부 포트 | 외부 노출 포트 |
|-------|-----|----------|---------------|
| **Frontend** | <https://deepsignal.shop> | 3000 | 3201 |
| **Admin** | <https://admin.deepsignal.shop> | 4000 | 3202 |
| **API** | <https://api.deepsignal.shop> | 8000 | 3200 |

> **Note**: 모든 트래픽은 Global Proxy(80/443)를 통해 분산됩니다. 직접 접속 시 32xx 포트를 사용하세요.

### SSH 접속

```bash
# SSH 접속
ssh root@141.164.55.245

# 통합 관리 스크립트 사용
/root/deploy.sh status
/root/deploy.sh group_c logs
```

### GitHub 저장소

```
Repository: https://github.com/joocy75-hash/AI-Agent-DeepSignal
Branch: main
Remote name: hetzner
```

---

### 서버 그룹 구조 및 포트 가이드라인

```
┌─────────────────────────────────────────────────────────────┐
│                    Seoul 서버 (8GB RAM)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Group A       │  │   Group B       │  │  Group C    │ │
│  │   Stock Trading │  │   개인 자동화    │  │  AI 트레이딩 │ │
│  │   (3000-3099)   │  │   (3100-3199)   │  │  (3200-3299)│ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│           │                   │                  │          │
│           └───────────┬───────┴──────────────────┘          │
│                       ▼                                     │
│             ┌───────────────────┐                           │
│             │   Global Proxy    │                           │
│             │   (Nginx: 80/443) │                           │
│             └───────────────────┘                           │
│                                                             │
│  * 각 그룹은 독립된 네트워크와 docker-compose를 사용함           │
│  * Nginx와 통신할 때만 proxy-net을 공유함                      │
└─────────────────────────────────────────────────────────────┘
```

### 포트 할당 규칙

- **Global Proxy**: 80, 443
- **Group A**: 3000 ~ 3099 (Stock Trading AI)
- **Group B**: 3100 ~ 3199 (Automation)
- **Group C**: 3200 ~ 3299 (AI Trading Platform)
  - 3200: Backend API
  - 3201: Frontend
  - 3202: Admin Frontend
  - 3203: PostgreSQL (내부 전용)
  - 3204: Redis (내부 전용)

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
| `HETZNER_SERVER_IP` | 서버 IP (141.164.55.245) |
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
ssh -i ~/.ssh/hetzner_deploy_key root@141.164.55.245

# 2. 프로젝트 디렉토리로 이동
cd /root/service_c/ai-trading-platform

# 3. 코드 동기화 (로컬에서)
rsync -avz --exclude 'node_modules' --exclude '.git' \
  -e "ssh -i ~/.ssh/hetzner_deploy_key" \
  ./ root@141.164.55.245:/root/service_c/ai-trading-platform/

# 4. 서비스 재빌드 및 재시작
docker compose -f docker-compose.production.yml build --no-cache
docker compose -f docker-compose.production.yml up -d
```

---

## 🚀 상세 배포 가이드

> 이 섹션은 새로운 개발자가 처음부터 끝까지 배포할 수 있도록 상세하게 작성되었습니다.

### 배포 전 체크리스트

```
□ 1. 로컬에서 코드가 정상 작동하는지 확인
□ 2. Python 구문 오류 없는지 확인: python -m py_compile backend/src/main.py
□ 3. Frontend 빌드 성공하는지 확인: cd frontend && npm run build
□ 4. Git 커밋 메시지 작성
□ 5. 민감한 정보(.env, API 키 등) 커밋에 포함되지 않았는지 확인
```

### Step 1: 로컬 개발 환경 설정

#### Backend 설정

```bash
# 1. 프로젝트 클론 또는 이동
cd /Users/mr.joo/Desktop/auto-dashboard/backend

# 2. 가상환경 생성 및 활성화
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export JWT_SECRET="your-dev-secret-key"
export ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"

# 5. DB 마이그레이션
alembic upgrade head

# 6. 서버 실행
python -m src.main
# 또는
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend 설정

```bash
# 1. Frontend 디렉토리로 이동
cd /Users/mr.joo/Desktop/auto-dashboard/frontend

# 2. 의존성 설치
npm install

# 3. 환경 변수 설정 (.env 파일)
echo "VITE_API_URL=http://localhost:8000" > .env

# 4. 개발 서버 실행
npm run dev
```

### Step 2: 코드 변경 및 테스트

#### Python 구문 검사

```bash
# 전체 백엔드 구문 검사
find backend/src -name "*.py" -exec python -m py_compile {} \;

# 특정 파일 검사
python -m py_compile backend/src/services/strategy_loader.py
```

#### 로컬 테스트

```bash
# Backend 테스트
cd backend
pytest tests/

# Frontend 빌드 테스트
cd frontend
npm run build
```

### Step 3: Git 커밋 및 배포

#### 자동 배포 (권장)

```bash
# 1. 변경 사항 스테이징
git add .

# 2. 커밋 (의미있는 메시지 작성)
git commit -m "feat: 새 전략 추가 - MyNewStrategy"

# 3. GitHub 푸시 → 자동 배포 시작!
git push hetzner main

# 4. 배포 상태 모니터링
gh run list -R joocy75-hash/AI-Agent-DeepSignal --limit 3
gh run watch <RUN_ID> -R joocy75-hash/AI-Agent-DeepSignal
```

#### 배포 진행 상황 확인

```bash
# GitHub Actions 로그 확인
gh run view <RUN_ID> --log -R joocy75-hash/AI-Agent-DeepSignal

# 또는 SSH로 서버 로그 직접 확인
ssh -i ~/.ssh/hetzner_deploy_key root@141.164.55.245 "docker logs groupc-backend --tail 50"
```

### Step 4: 배포 검증

```bash
# 1. API 헬스 체크
curl https://api.deepsignal.shop/health

# 2. 로그인 테스트 (쿠키 기반 인증)
curl -c cookies.txt -X POST "https://api.deepsignal.shop/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'

# 3. 인증이 필요한 API 테스트
# 쿠키에서 CSRF 토큰 추출
CSRF_TOKEN=$(grep csrf cookies.txt | awk '{print $7}')

# 봇 상태 확인
curl -b cookies.txt -X GET "https://api.deepsignal.shop/api/v1/bot/status" \
  -H "X-CSRF-Token: $CSRF_TOKEN"

# 전략 목록 확인
curl -b cookies.txt -X GET "https://api.deepsignal.shop/api/v1/ai/strategies/list" \
  -H "X-CSRF-Token: $CSRF_TOKEN"
```

### Step 5: 롤백 (문제 발생 시)

```bash
# 1. 이전 커밋으로 되돌리기
git revert HEAD
git push hetzner main

# 또는 특정 커밋으로 복원
git reset --hard <commit_hash>
git push hetzner main --force  # 주의: force push

# 2. 서버에서 직접 롤백 (긴급 시)
ssh -i ~/.ssh/hetzner_deploy_key root@141.164.55.245 << 'EOF'
cd /root/service_c/ai-trading-platform
git log --oneline -5  # 최근 커밋 확인
git checkout <이전_commit_hash>
docker compose -f docker-compose.production.yml build --no-cache
docker compose -f docker-compose.production.yml up -d
EOF
```

### 배포 시 자주 발생하는 문제

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| 배포 실패: Python syntax error | 코드 구문 오류 | `python -m py_compile <file>` 로 확인 |
| 배포 실패: npm build error | Frontend 빌드 오류 | `npm run build` 로컬에서 확인 |
| API 500 에러 | 런타임 오류 | `docker logs groupc-backend` 확인 |
| DB 연결 실패 | PostgreSQL 비밀번호 불일치 | 문제 해결 가이드 참조 |
| 전략 로드 실패 | strategy_loader.py 매핑 누락 | 아래 전략 생성 가이드 참조 |

---

## 🤖 전략 생성 가이드

> 새로운 트레이딩 전략을 만들고 시스템에 등록하는 완전한 가이드입니다.

### 전략 시스템 아키텍처 이해

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           전략 시스템 흐름도                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. DB (strategies 테이블)                                               │
│     └─ code: "my_new_strategy" 또는 "my_strategy.MyStrategy"            │
│                    │                                                     │
│                    ▼                                                     │
│  2. strategy_loader.py                                                   │
│     └─ load_strategy_class(strategy_code, params_json, user_id)         │
│     └─ _create_strategy_instance_internal()에서 매핑                     │
│                    │                                                     │
│                    ▼                                                     │
│  3. 전략 클래스 (backend/src/strategies/my_new_strategy.py)              │
│     └─ generate_signal(current_price, candles, current_position)        │
│                    │                                                     │
│                    ▼                                                     │
│  4. bot_runner.py                                                        │
│     └─ 시그널에 따라 주문 실행                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 1: 전략 클래스 파일 생성

**위치**: `backend/src/strategies/my_new_strategy.py`

```python
"""
나의 새로운 전략

전략 설명:
- 진입 조건: ...
- 청산 조건: ...
- 리스크 관리: ...
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class IndicatorSnapshot:
    """지표 스냅샷 - 필요한 지표들을 정의"""
    close: float
    ema_fast: float
    ema_slow: float
    rsi: float
    # 필요한 지표 추가...


class MyNewStrategy:
    """
    나의 새로운 전략 클래스

    ⚠️ 필수 메서드:
    - __init__(self, params, user_id)
    - generate_signal(self, current_price, candles, current_position)

    ⚠️ 필수 반환 구조:
    {
        "action": "buy" | "sell" | "hold" | "close",
        "confidence": 0.0 ~ 1.0,
        "reason": str,
        "stop_loss": float | None,
        "take_profit": float | None,
        "size": float | None,
        "strategy_type": str,
    }
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None):
        """
        전략 초기화

        Args:
            params: 전략 파라미터 (DB의 params JSON에서 로드됨)
            user_id: 사용자 ID (AI 에이전트 캐싱에 사용)
        """
        self.params = params or {}
        self.user_id = user_id

        # 파라미터에서 설정값 로드 (기본값 포함)
        self.symbol = self.params.get("symbol", "ETH/USDT")
        self.timeframe = self.params.get("timeframe", "5m")
        self.leverage = int(self.params.get("leverage", 10))

        # 지표 설정
        self._ema_fast = int(self.params.get("ema_fast", 9))
        self._ema_slow = int(self.params.get("ema_slow", 21))
        self._rsi_length = int(self.params.get("rsi_length", 14))

        # 리스크 관리 설정
        self._stop_loss_percent = float(self.params.get("stop_loss_percent", 1.5))
        self._take_profit_percent = float(self.params.get("take_profit_percent", 3.0))

    def generate_signal(
        self,
        current_price: float,
        candles: list,
        current_position: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        시그널 생성 - 봇 루프에서 주기적으로 호출됨

        Args:
            current_price: 현재 가격
            candles: OHLCV 캔들 데이터 리스트
                [{"open": float, "high": float, "low": float, "close": float, "volume": float}, ...]
            current_position: 현재 포지션 정보 (없으면 None)
                {
                    "side": "long" | "short",
                    "entry_price": float,
                    "size": float,
                    "pnl": float,
                    "pnl_percent": float,
                    "leverage": int,
                }

        Returns:
            시그널 딕셔너리 (구조는 위 docstring 참조)
        """
        # 1. 캔들 데이터 검증
        if not candles or len(candles) < 60:
            return self._hold("insufficient_candles")

        # 2. 지표 계산
        snapshot = self._compute_indicators(candles)

        # 3. 포지션이 있으면 관리, 없으면 진입 평가
        if current_position and current_position.get("size", 0) > 0:
            return self._manage_position(current_price, snapshot, current_position)

        return self._evaluate_entry(snapshot)

    def _evaluate_entry(self, snapshot: IndicatorSnapshot) -> Dict[str, Any]:
        """진입 조건 평가"""
        # 롱 진입 조건
        if snapshot.ema_fast > snapshot.ema_slow and snapshot.rsi < 70:
            return {
                "action": "buy",
                "confidence": 0.7,
                "reason": "EMA 골든크로스 + RSI 과매수 아님",
                "stop_loss": self._stop_loss_percent,
                "take_profit": self._take_profit_percent,
                "size": None,  # bot_runner가 계산
                "strategy_type": "my_new_strategy",
            }

        # 숏 진입 조건
        if snapshot.ema_fast < snapshot.ema_slow and snapshot.rsi > 30:
            return {
                "action": "sell",
                "confidence": 0.7,
                "reason": "EMA 데드크로스 + RSI 과매도 아님",
                "stop_loss": self._stop_loss_percent,
                "take_profit": self._take_profit_percent,
                "size": None,
                "strategy_type": "my_new_strategy",
            }

        return self._hold("no_entry_signal")

    def _manage_position(
        self,
        current_price: float,
        snapshot: IndicatorSnapshot,
        current_position: Dict[str, Any],
    ) -> Dict[str, Any]:
        """포지션 관리 (손절/익절/청산)"""
        side = current_position.get("side", "long")
        pnl_percent = current_position.get("pnl_percent", 0)

        # 손절
        if pnl_percent <= -self._stop_loss_percent:
            return self._close("stop_loss_hit")

        # 익절
        if pnl_percent >= self._take_profit_percent:
            return self._close("take_profit_hit")

        # 추세 반전 시 청산
        if side == "long" and snapshot.ema_fast < snapshot.ema_slow:
            return self._close("trend_reversal")
        if side == "short" and snapshot.ema_fast > snapshot.ema_slow:
            return self._close("trend_reversal")

        return self._hold("position_maintained")

    def _compute_indicators(self, candles: list) -> IndicatorSnapshot:
        """지표 계산"""
        closes = [c.get("close", 0) for c in candles]

        return IndicatorSnapshot(
            close=closes[-1],
            ema_fast=self._ema(closes, self._ema_fast),
            ema_slow=self._ema(closes, self._ema_slow),
            rsi=self._rsi(closes, self._rsi_length),
        )

    def _hold(self, reason: str) -> Dict[str, Any]:
        """HOLD 시그널 반환"""
        return {
            "action": "hold",
            "confidence": 0.0,
            "reason": reason,
            "stop_loss": None,
            "take_profit": None,
            "size": None,
            "strategy_type": "my_new_strategy",
        }

    def _close(self, reason: str) -> Dict[str, Any]:
        """CLOSE 시그널 반환"""
        return {
            "action": "close",
            "confidence": 0.7,
            "reason": reason,
            "stop_loss": None,
            "take_profit": None,
            "size": None,
            "strategy_type": "my_new_strategy",
        }

    # ============================================================
    # 지표 계산 헬퍼 함수들
    # ============================================================

    def _ema(self, values: list, period: int) -> float:
        """EMA 계산"""
        if not values or len(values) < period:
            return values[-1] if values else 0.0
        k = 2 / (period + 1)
        ema = values[0]
        for price in values[1:]:
            ema = price * k + ema * (1 - k)
        return ema

    def _rsi(self, closes: list, period: int) -> float:
        """RSI 계산"""
        if len(closes) <= period:
            return 50.0
        gains = 0.0
        losses = 0.0
        for i in range(-period, 0):
            change = closes[i] - closes[i - 1]
            if change >= 0:
                gains += change
            else:
                losses += abs(change)
        if losses == 0:
            return 100.0
        rs = gains / losses
        return 100 - (100 / (1 + rs))


# 팩토리 함수 (선택사항이지만 권장)
def create_my_new_strategy(
    params: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
) -> MyNewStrategy:
    """전략 인스턴스 생성 팩토리"""
    return MyNewStrategy(params=params, user_id=user_id)
```

### Step 2: strategy_loader.py에 매핑 추가

**위치**: `backend/src/services/strategy_loader.py`

`_create_strategy_instance_internal()` 함수에 새 전략 매핑을 추가합니다:

```python
def _create_strategy_instance_internal(
    strategy_code: str,
    params: dict,
    user_id: Optional[int] = None,
):
    # ... 기존 코드 ...

    try:
        normalized = (strategy_code or "eth_ai_fusion").strip()
        if not normalized:
            normalized = "eth_ai_fusion"

        # Legacy aliases 및 다양한 형태의 전략 코드 처리
        legacy_aliases = {
            "proven_conservative",
            "proven_balanced",
            # ... 기존 aliases ...

            # ⭐ 새 전략 aliases 추가
            "my_new_strategy",
            "my_new_strategy.MyNewStrategy",
            "MyNewStrategy",
        }

        # eth_ai_fusion으로 매핑되는 aliases
        if normalized in legacy_aliases and normalized not in ["my_new_strategy", "my_new_strategy.MyNewStrategy", "MyNewStrategy"]:
            normalized = "eth_ai_fusion"

        # ⭐ 새 전략 로드 블록 추가
        if normalized in ["my_new_strategy", "my_new_strategy.MyNewStrategy", "MyNewStrategy"]:
            from ..strategies.my_new_strategy import MyNewStrategy
            logger.info(f"✅ Loading MyNewStrategy for user {user_id}")
            return MyNewStrategy(params, user_id=user_id)

        if normalized == "eth_ai_fusion":
            from ..strategies.eth_ai_fusion_strategy import ETHAIFusionStrategy
            logger.info(f"✅ Loading ETHAIFusionStrategy for user {user_id}")
            return ETHAIFusionStrategy(params, user_id=user_id)

        # ... 기존 코드 ...
```

### Step 3: 데이터베이스에 전략 등록

```bash
# SSH로 서버 접속
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248

# PostgreSQL에 전략 INSERT
docker exec groupc-postgres psql -U trading_user -d trading_prod -c "
INSERT INTO strategies (user_id, name, description, code, params, is_active) VALUES
(1, '나의 새 전략', 'EMA 크로스오버 기반 전략', 'my_new_strategy', '{\"symbol\": \"ETH/USDT\", \"timeframe\": \"5m\", \"ema_fast\": 9, \"ema_slow\": 21}', true);
"

# 등록 확인
docker exec groupc-postgres psql -U trading_user -d trading_prod -c "SELECT id, name, code, is_active FROM strategies;"
```

### Step 4: 배포 및 테스트

```bash
# 1. 로컬에서 구문 검사
python -m py_compile backend/src/strategies/my_new_strategy.py
python -m py_compile backend/src/services/strategy_loader.py

# 2. Git 커밋 및 배포
git add backend/src/strategies/my_new_strategy.py backend/src/services/strategy_loader.py
git commit -m "feat: 새 전략 추가 - MyNewStrategy"
git push hetzner main

# 3. 배포 완료 후 테스트
# 로그인 및 쿠키 저장
curl -c cookies.txt -X POST "https://api.deepsignal.shop/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'

# CSRF 토큰 추출
CSRF_TOKEN=$(grep csrf cookies.txt | awk '{print $7}')

# 전략 목록에서 새 전략 확인
curl -b cookies.txt -X GET "https://api.deepsignal.shop/api/v1/ai/strategies/list" \
  -H "X-CSRF-Token: $CSRF_TOKEN" | jq .

# 봇 시작 테스트 (새 전략 ID로)
curl -b cookies.txt -X POST "https://api.deepsignal.shop/api/v1/bot/start" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"strategy_id": <새_전략_ID>}'
```

### 전략 개발 체크리스트

```
□ 1. 전략 클래스 파일 생성 (backend/src/strategies/)
□ 2. generate_signal() 메서드 구현 (필수 반환 구조 준수)
□ 3. strategy_loader.py에 매핑 추가
□ 4. 로컬 구문 검사 통과
□ 5. Git 커밋 및 배포
□ 6. DB에 전략 등록
□ 7. 봇 시작 테스트
□ 8. 로그에서 전략 로드 확인: "✅ Loading MyNewStrategy"
```

### 전략 코드 매핑 규칙

| DB의 code 값 | strategy_loader.py 매핑 | 실제 클래스 |
|--------------|------------------------|------------|
| `eth_ai_fusion` | `if normalized == "eth_ai_fusion":` | ETHAIFusionStrategy |
| `eth_ai_fusion_strategy.ETHAIFusionStrategy` | legacy_aliases에서 변환 | ETHAIFusionStrategy |
| `my_new_strategy` | `if normalized in ["my_new_strategy", ...]:` | MyNewStrategy |

### ML/AI 기능 추가 (고급)

ETH AI Fusion 전략처럼 ML 기능을 추가하려면:

```python
# 전략 파일 상단에 ML 모듈 import
try:
    from src.ml.features import FeaturePipeline
    from src.ml.models import EnsemblePredictor
    ML_AVAILABLE = True
except Exception:
    FeaturePipeline = None
    EnsemblePredictor = None
    ML_AVAILABLE = False


class MyMLStrategy:
    def __init__(self, params, user_id=None):
        # ... 기존 초기화 ...

        # ML 초기화
        self.enable_ml = self.params.get("enable_ml", True) and ML_AVAILABLE
        self._feature_pipeline = FeaturePipeline() if self.enable_ml and FeaturePipeline else None
        self._ml_predictor = EnsemblePredictor() if self.enable_ml and EnsemblePredictor else None

    def _get_ml_prediction(self, candles, snapshot):
        """ML 예측 수행"""
        if not self._ml_predictor or not self._feature_pipeline:
            return None

        symbol = self.symbol.replace("/", "").replace(":USDT", "")
        features = self._feature_pipeline.extract_features(candles, symbol=symbol)

        if features.empty:
            return None

        rule_signal = "long" if snapshot.ema_fast > snapshot.ema_slow else "short"
        return self._ml_predictor.predict(features, symbol=symbol, rule_based_signal=rule_signal)
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

### 현재 활성 전략 (2026-01-01 ETH AI Fusion으로 교체)

전략명: ETH AI Fusion Strategy
전략코드: eth_ai_fusion
심볼: ETHUSDT
타임프레임: 5m
최대 마진: 40% (하드코딩)
레버리지: 10-20x (변동성 기반 동적)

**전략 로직 요약:**

- **진입 기준**: EMA(9/21) 방향, RSI(14), MACD 히스토그램, 거래량 비율 점수화. 점수 ≥ 4 및 방향 우세 시 진입
- **ML 게이트**: FeaturePipeline + EnsemblePredictor 사용. `should_skip_entry` 또는 방향 불일치/타이밍 불량 시 진입 차단
- **보수적 손절/익절**: ATR% 기반 SL/TP (SL: 0.6~1.6%, ML 신뢰도 높으면 최대 1.8%), TP: 1.2~4.5%
- **트레일링**: 최대 수익이 TP 도달 시, `max(stop_loss, max_profit*0.5)` 기준으로 이익 보호 청산
- **추매(수익 구간)**: 0.8% 단위 수익 구간 도달 시 최대 3회, 현재 포지션의 35% 규모로 추가 진입
  - RSI 과열/과매도, EMA/MACD 반전, ML 방향 불일치 시 추매 차단

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
| `ETHAIFusionStrategy` | `eth_ai_fusion_strategy.py` | 메인 트레이딩 로직 |
| `_risk_targets()` | 동일 파일 | 익절/손절 로직 |
| 포지션 동기화 | `bot_runner.py:627-670` | 봇 시작 시 동기화 |
| AI Agent 초기화 | `strategy_loader.py` | 에이전트 생성 |

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

### eth_ai_fusion_strategy.py

```
위치: backend/src/strategies/eth_ai_fusion_strategy.py
```

**수정 시 체크리스트:**

- [ ] 40% 마진 한도 유지했는가?
- [ ] `_risk_targets()` 로직 유지했는가?
- [ ] AI 에이전트 및 ML 연동 유지했는가?

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

**현재 등록된 전략 (2025-12-27 복구됨):**

| ID | 이름 | 코드 |
|----|------|------|
| 1 | ETH AI Fusion 전략 | eth_ai_fusion_strategy.ETHAIFusionStrategy |

**전략 복구 명령어** (DB가 비어있을 경우):

```bash
ssh -i ~/.ssh/hetzner_deploy_key root@5.161.112.248 "docker exec groupc-postgres psql -U trading_user -d trading_prod -c \"
TRUNCATE strategies;
INSERT INTO strategies (user_id, name, description, code, params, is_active) VALUES
(1, 'ETH AI Fusion 전략', 'ETH AI/ML 융합 전략', 'eth_ai_fusion_strategy.ETHAIFusionStrategy', '{\\\"symbol\\\": \\\"ETH/USDT\\\", \\\"timeframe\\\": \\\"5m\\\"}', true);
\""
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
| 2026-01-02 | **프로젝트 구조 섹션 추가** - 전체 디렉토리 구조 및 핵심 파일 설명 |
| 2026-01-02 | **상세 배포 가이드 및 전략 생성 가이드 추가** - 새 개발자를 위한 완전한 가이드 |
| 2026-01-02 | **전략 코드 매핑 문제 해결** - strategy_loader.py에서 다양한 형태의 코드 인식 |
| 2026-01-02 | **tradesource enum 수정** - bot_instance 값 추가 |
| 2026-01-01 | **ETH AI Fusion 전략으로 전면 교체** - 기존 전략 제거 및 단일화 |
| 2025-12-27 | **적극적 매매 전략으로 변경** - 레버리지 10-20x, 진입조건 완화, 포지션 크기 상향 |
| 2025-12-27 | **DB 전략 복구** - Production DB strategies 테이블에 5개 전략 재삽입 |
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
