# AI Trading Platform - 통합 개발 가이드

> **IMPORTANT**: 이 문서는 AI가 코드 수정 및 배포 시 반드시 읽어야 하는 **유일한 필수 가이드**입니다.

**최종 업데이트**: 2026-01-10

---

## 📋 목차

1. [프로젝트 분리 정책](#프로젝트-분리-정책) ⭐ CRITICAL
2. [핵심 아키텍처](#핵심-아키텍처)
3. [서버 및 배포](#서버-및-배포)
4. [전략 개발](#전략-개발)
5. [데이터 구조](#데이터-구조)
6. [금지 사항](#금지-사항)
7. [문제 해결](#문제-해결)

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
- **CI/CD**: GitHub Actions

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
- **마진 한도**: 40% (하드코딩)

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

2. **40% 마진 한도 변경**
   ```python
   MAX_MARGIN_PERCENT = 40.0  # 절대 변경 금지
   ```

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
- [ ] 40% 마진 한도 유지?
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

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-01-10 | **CLAUDE.md 최적화** - 35k chars 이하로 압축 |
| 2026-01-09 | 서울 서버 IP 및 통합 배포 스크립트 적용 |
| 2026-01-02 | 프로젝트 구조 및 상세 가이드 추가 |
| 2026-01-01 | ETH AI Fusion 전략으로 전면 교체 |
| 2025-12-27 | Hetzner 서버 이전 및 CI/CD 구축 |

---

**⚠️ 이전 서버(158.247.245.197)는 삭제되었습니다.**
