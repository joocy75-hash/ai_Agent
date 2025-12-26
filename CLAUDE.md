# Auto Trading Dashboard - AI Development Guide (통합 문서)

> **IMPORTANT**: 이 문서는 AI가 코드 수정 및 배포 시 반드시 읽어야 하는 **유일한 필수 가이드**입니다.
> 다른 MD 파일들은 참고용입니다. 핵심 정보는 모두 이 문서에 있습니다.

---

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [서버 정보 및 접속](#서버-정보-및-접속)
3. [🚨 절대 하면 안 되는 것들](#-절대-하면-안-되는-것들)
4. [AI 에이전트 아키텍처](#ai-에이전트-아키텍처)
5. [핵심 데이터 구조](#핵심-데이터-구조)
6. [배포 프로세스](#배포-프로세스)
7. [파일별 수정 규칙](#파일별-수정-규칙)
8. [문제 해결 가이드](#문제-해결-가이드)

---

## 시스템 개요

### 기술 스택

| 컴포넌트 | 기술 | 포트 | 컨테이너명 |
|---------|------|------|-----------|
| Frontend | React + Vite | 3000 | trading-frontend |
| Admin Frontend | React + Vite | 4000 | trading-admin-frontend |
| Backend | FastAPI + Python 3.11 | 8000 | trading-backend |
| Database | PostgreSQL 15 | 5432 | trading-postgres |
| Cache | Redis 7 | 6379 | trading-redis |

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

---

## 서버 정보 및 접속

```
Production Server: 158.247.245.197
SSH: root / Vc8,xn7j_fjdnNGy
Project Path: /root/auto-dashboard

도메인:
- 사용자: https://ai-deepsignal.com
- 관리자: https://admin.ai-deepsignal.com
- API: https://api.ai-deepsignal.com
```

### 빠른 접속 명령어

```bash
# SSH 접속
sshpass -p 'Vc8,xn7j_fjdnNGy' ssh -o StrictHostKeyChecking=no root@158.247.245.197

# 컨테이너 상태 확인
ssh root@158.247.245.197 "docker ps"

# 백엔드 로그 확인
ssh root@158.247.245.197 "docker logs trading-backend --tail 100"
```

---

## 🚨 절대 하면 안 되는 것들

### ❌ 1. docker cp로 파일 복사 후 "배포 완료" 선언

```bash
# ❌ 잘못된 예 - 컨테이너 재시작 시 파일 사라짐!
docker cp my_file.py trading-backend:/app/src/

# ✅ 올바른 방법 - 서버에 먼저 동기화 후 rebuild
rsync -avz file.py root@158.247.245.197:/root/auto-dashboard/backend/src/
ssh root@158.247.245.197 "cd /root/auto-dashboard && docker compose build backend"
```

### ❌ 2. 서버 동기화 없이 docker compose build

```bash
# ❌ 잘못된 예 - 오래된 서버 코드로 빌드됨
ssh server "docker compose build backend"

# ✅ 올바른 방법 - 먼저 rsync로 동기화
rsync -avz ./ root@158.247.245.197:/root/auto-dashboard/
ssh server "docker compose build backend"
```

### ❌ 3. --no-cache 없이 프론트엔드 빌드

```bash
# ❌ 잘못된 예 - VITE_API_URL이 캐시된 값으로 빌드될 수 있음
docker compose build frontend

# ✅ 올바른 방법
docker compose build --no-cache frontend
```

### ❌ 4. 40% 마진 한도 변경

```python
# ❌ 절대 변경 금지 - MarginCapEnforcer40Pct
MAX_MARGIN_PERCENT = 40.0  # 이 값 변경 금지!
```

### ❌ 5. current_position 데이터 구조 변경

```python
# ❌ 이 구조는 여러 파일에서 사용됨 - 변경 시 전체 시스템 영향
current_position = {
    "side": "long" | "short",
    "entry_price": float,
    "size": float,
    "pnl": float,
    "pnl_percent": float,
    "leverage": int,
    "margin": float,
    "liquidation_price": float,
    "holding_minutes": int,
}
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
│  │ Agent (AI=True) │  │ Agent (AI=True) │                   │
│  │ - 시장환경분석  │  │ - 신호검증      │                   │
│  │ - 추세/횡보감지 │  │ - 중복진입방지  │                   │
│  └─────────────────┘  └─────────────────┘                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Risk Monitor    │  │ Portfolio       │                   │
│  │ Agent           │  │ Optimizer Agent │                   │
│  │ - 리스크감시   │  │ (AI=True)       │                   │
│  │ - 청산가경고   │  │ - 5-40% 범위    │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### AI Service (DeepSeek)

```
Provider: DeepSeek (deepseek-chat)
API: https://api.deepseek.com/v1/chat/completions
Cost: ~$0.0002/call (~400 tokens)
Usage: Market regime analysis
```

### 🔴 절대 수정 금지 컴포넌트

| Component | Location | Reason |
|-----------|----------|--------|
| `MarginCapEnforcer40Pct` | `eth_ai_autonomous_40pct_strategy.py` | 40% 마진 한도 |
| `_check_exit_conditions()` | 동일 파일 | 익절/손절 로직 |
| 포지션 동기화 | `bot_runner.py:627-670` | 봇 시작 시 동기화 |
| AI Agent 초기화 | `strategy_loader.py` | 4개 에이전트 생성 |

### 핵심 데이터 흐름

```
1. 봇 시작 시:
   bot_runner.py → get_positions() → current_position 동기화
   ⚠️ 이 동기화 없으면 기존 포지션 익절/손절 안 됨!

2. 시장 분석:
   Market data → MarketRegimeAgent → DeepSeek AI → regime_type

3. 거래 결정:
   Strategy → analyze_and_decide() → check_exit_conditions() → signal

4. 포지션 관리:
   signal → bot_runner → place_order → update current_position
```

---

## 핵심 데이터 구조

### Position 구조 (MUST MAINTAIN)

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

### Signal 구조 (MUST MAINTAIN)

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

### 환경변수 (MUST SET)

| Variable | Required | Production Value |
|----------|----------|------------------|
| `VITE_API_URL` | **YES** | `https://api.ai-deepsignal.com` |
| `CORS_ORIGINS` | **YES** | `https://ai-deepsignal.com,https://admin.ai-deepsignal.com` |
| `JWT_SECRET` | **YES** | 32+ characters |
| `ENCRYPTION_KEY` | **YES** | Fernet key (base64) |
| `DEEPSEEK_API_KEY` | **YES** | DeepSeek API key |

---

## 배포 프로세스

### 방법 1: 스크립트 사용 (권장)

```bash
# 환경변수 검증 후 전체 배포
./scripts/validate-env.sh && ./scripts/deploy-production.sh
```

### 방법 2: 백엔드만 빠르게 수정 (테스트용)

```bash
# 1. 문법 검증
cd backend && python3 -m py_compile src/services/bot_runner.py

# 2. 서버에 파일 전송
rsync -avz backend/src/services/bot_runner.py root@158.247.245.197:/tmp/ \
  -e "sshpass -p 'Vc8,xn7j_fjdnNGy' ssh -o StrictHostKeyChecking=no"

# 3. 컨테이너에 복사 및 재시작
sshpass -p 'Vc8,xn7j_fjdnNGy' ssh -o StrictHostKeyChecking=no root@158.247.245.197 \
  "docker cp /tmp/bot_runner.py trading-backend:/app/src/services/ && docker restart trading-backend"

# 4. 로그 확인
sshpass -p 'Vc8,xn7j_fjdnNGy' ssh -o StrictHostKeyChecking=no root@158.247.245.197 \
  "docker logs trading-backend --tail 50"
```

### 방법 3: 전체 재빌드 (영구 배포)

```bash
# 1. 로컬 코드를 서버로 동기화
rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '__pycache__' \
  --exclude '*.pyc' --exclude 'dist' --exclude 'build' --exclude '.env' \
  --exclude 'trading.db' \
  -e "sshpass -p 'Vc8,xn7j_fjdnNGy' ssh -o StrictHostKeyChecking=no" \
  ./ root@158.247.245.197:/root/auto-dashboard/

# 2. 서버에서 Docker 이미지 재빌드
sshpass -p 'Vc8,xn7j_fjdnNGy' ssh -o StrictHostKeyChecking=no root@158.247.245.197 \
  "cd /root/auto-dashboard && docker compose build --no-cache backend && docker compose up -d backend"
```

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
- [ ] `current_position` 동기화 로직 (Line 627-670) 유지했는가?
- [ ] AI 에이전트 초기화 순서 유지했는가?
- [ ] 포지션 데이터 구조 유지했는가?

### strategy_loader.py (전략 로더)

```
위치: backend/src/services/strategy_loader.py
```

**수정 시 체크리스트:**
- [ ] `generate_signal_with_strategy()` 인터페이스 유지했는가?
- [ ] `current_position` 파라미터 전달했는가?
- [ ] `PositionInfo` 변환 로직 유지했는가?

### eth_ai_autonomous_40pct_strategy.py (ETH 전략)

```
위치: backend/src/strategies/eth_ai_autonomous_40pct_strategy.py
```

**수정 시 체크리스트:**
- [ ] 40% 마진 한도 (`MAX_MARGIN_PERCENT = 40.0`) 유지했는가?
- [ ] `_check_exit_conditions()` 로직 유지했는가?
- [ ] ATR 기반 SL/TP 계산 유지했는가?
- [ ] 4개 AI 에이전트 초기화 유지했는가?

### Frontend 파일들

```
Trading.jsx - 거래 페이지
Dashboard.jsx - 대시보드
Strategy.jsx - 전략 관리
Login.jsx - 로그인
```

**수정 시 체크리스트:**
- [ ] API 엔드포인트 경로 `/api/v1/` 유지했는가?
- [ ] JWT 토큰 헤더 `Authorization: Bearer` 유지했는가?
- [ ] WebSocket 연결 경로 유지했는가?

---

## 문제 해결 가이드

### 🔴 배포 후 API 호출 실패

```bash
# 프론트엔드 번들에서 API URL 확인
ssh root@158.247.245.197 "docker exec trading-frontend grep -o 'api.ai-deepsignal\|localhost:8000' /usr/share/nginx/html/assets/*.js"

# localhost:8000이 보이면 → --no-cache 재빌드 필요
ssh root@158.247.245.197 "cd /root/auto-dashboard && docker compose build --no-cache frontend && docker compose up -d frontend"
```

### 🔴 코드 변경이 적용 안 될 때

```bash
# 로컬, 서버, 컨테이너 파일 해시 비교
md5 -q backend/src/services/bot_runner.py
ssh root@158.247.245.197 "md5sum /root/auto-dashboard/backend/src/services/bot_runner.py"
ssh root@158.247.245.197 "docker exec trading-backend md5sum /app/src/services/bot_runner.py"

# 세 값이 다르면 동기화 문제 → 방법 3 (전체 재빌드) 실행
```

### 🔴 포지션 익절/손절 안 될 때

```bash
# 포지션 동기화 로그 확인
ssh root@158.247.245.197 "docker logs trading-backend --tail 100 2>&1 | grep -E 'Synced existing|current_position'"

# "Synced existing position" 로그가 없으면:
# bot_runner.py의 포지션 동기화 코드 (Line 627-670) 확인
```

### 🔴 AI 에이전트 작동 확인

```bash
# AI 호출 로그 확인
ssh root@158.247.245.197 "docker logs trading-backend --tail 100 2>&1 | grep -E 'AI call|Market regime|agents initialized'"

# 정상 로그 예시:
# ✅ AI call for market_regime: $0.000185, 416 tokens
# ✅ Market regime: ETHUSDT -> low_volume (confidence: 0.80)
# ✅ All 4 AI agents initialized for ETH autonomous trading
```

### 🔴 거래 결정 로그 확인

```bash
ssh root@158.247.245.197 "docker logs trading-backend --tail 100 2>&1 | grep -E 'Decision|Signal check|Take Profit|Stop Loss'"

# 정상 로그 예시:
# [Decision] hold | Confidence: 50.0% | Size: 0.0%
# Strategy signal: close (reason: ✅ Take Profit: 25.89% > 2.93%)
```

### 🔴 컨테이너 unhealthy

```bash
# 로그 확인
ssh root@158.247.245.197 "docker logs trading-backend --tail 100"

# Health check 직접 테스트
curl http://158.247.245.197:8000/health
```

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

## API Endpoints

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

---

## 보안 Notes

1. **Never commit `.env` files** - 항상 `.gitignore`에 포함
2. **JWT tokens expire** - Access: 1시간, Refresh: 7일
3. **Password requirements** - 최소 8자, 대/소문자, 숫자, 특수문자
4. **HTTPS required** - 프로덕션에서 HTTP 사용 금지

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2025-12-18 | 포지션 동기화 버그 수정 (봇 시작 시 기존 포지션 인식) |
| 2025-12-18 | MarketRegimeAgent 캔들 데이터 전달 문제 해결 |
| 2025-12-18 | 통합 문서로 재작성 |

---

**⚠️ 이 문서를 수정할 때는 실제 코드와 일치하는지 확인하세요.**
