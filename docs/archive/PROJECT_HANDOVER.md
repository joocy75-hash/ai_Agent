# 🤖 자동매매 플랫폼 프로젝트 인수인계 문서

> **작성일**: 2025-12-04
> **프로젝트명**: Auto Trading Dashboard
> **기술 스택**: React + Vite (Frontend), FastAPI (Backend), SQLite (Database)

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [현재까지 완료된 작업](#현재까지-완료된-작업)
3. [시스템 아키텍처](#시스템-아키텍처)
4. [보완해야 할 점](#보완해야-할-점)
5. [앞으로 해야 할 작업](#앞으로-해야-할-작업)
6. [배포 및 운영 가이드](#배포-및-운영-가이드)
7. [문제 해결 가이드](#문제-해결-가이드)

---

## 프로젝트 개요

### 프로젝트 목적
암호화폐 자동매매를 위한 웹 기반 대시보드 시스템으로, Bitget 거래소와 연동하여 실시간 거래 모니터링, 전략 관리, 백테스팅, 성과 분석 기능을 제공합니다.

### 기술 스택

**Frontend**
- React 18.3.1
- Vite 6.0.11 (개발 서버)
- Ant Design 5.x (UI 컴포넌트)
- Recharts 2.x (차트 라이브러리)
- React Router 7.1.0 (라우팅)
- Axios (HTTP 클라이언트)
- Day.js (날짜 처리)

**Backend**
- FastAPI (Python 웹 프레임워크)
- SQLAlchemy (ORM)
- SQLite + aiosqlite (비동기 데이터베이스)
- Passlib + bcrypt (비밀번호 해싱)
- PyJWT (JWT 인증)
- WebSocket (실시간 통신)
- Bitget API (거래소 연동)

**인프라**
- Docker (컨테이너화)
- Nginx (리버스 프록시)
- Prometheus + Grafana (모니터링)

---

## 현재까지 완료된 작업

### ✅ Phase 1: 핵심 대시보드 (완료)

#### 1. Dashboard 페이지
- **파일**: `/frontend/src/pages/Dashboard.jsx`
- **기능**:
  - 봇 상태 모니터링 (실행중/정지/오류)
  - 봇 시작/정지 제어
  - 실시간 암호화폐 가격 표시 (BTC, ETH, SOL)
  - WebSocket 연동으로 실시간 데이터 업데이트
  - 잔고 카드 (BalanceCard 컴포넌트)
  - 포지션 목록 (PositionList 컴포넌트)
  - 주문/알림 활동 로그 (OrderActivityLog 컴포넌트)

#### 2. Settings 페이지
- **파일**: `/frontend/src/pages/Settings.jsx`
- **기능**:
  - 3개 탭 구조 (API 키, 비밀번호, 도움말)
  - Bitget API 키 등록 및 관리
  - API 연결 테스트 기능
  - 등록된 키 조회 (시간당 3회 제한)
  - 키 표시/숨김 토글
  - 보안 가이드 및 FAQ

#### 3. OrderActivityLog 컴포넌트
- **파일**: `/frontend/src/components/OrderActivityLog.jsx`
- **기능**:
  - 주문 이력 + 시스템 알림 통합 표시
  - 실시간 WebSocket 업데이트
  - 타입별 아이콘 및 색상 코딩
  - 필터링 (전체/주문/알림)
  - 자동 스크롤 토글
  - 상대 시간 표시
  - 하단 통계 (총 활동, 주문, 에러, 경고)

### ✅ Phase 2: 성과 분석 (완료)

#### 4. Performance Analytics 페이지
- **파일**: `/frontend/src/pages/Performance.jsx`
- **기능**:
  - **EquityCurve 컴포넌트**: 자산 변화 곡선 차트
  - **PerformanceMetrics**: 월별 수익률, 승/패 분포, 심볼별 수익
  - **TradeHistory**: 거래 이력 테이블
  - **PerformanceReport**: 기간별 보고서 (일/주/월/분기/연)
  - 실제 API 연동 완료
  - Sharpe Ratio, Profit Factor, MDD 계산

### ✅ Phase 3: 알림 센터 (완료)

#### 5. Notification Center
- **파일**:
  - `/frontend/src/pages/Notifications.jsx` (알림 페이지)
  - `/frontend/src/components/NotificationBell.jsx` (헤더 벨)
- **기능**:
  - 실시간 알림 배지 (읽지 않은 개수)
  - 드롭다운 알림 목록 (최근 10개)
  - 전체 알림 페이지 (필터링, 페이지네이션)
  - 알림 읽음 처리
  - 모든 알림 읽음/삭제 기능
  - WebSocket 실시간 업데이트
  - 통계 카드 (총 알림, 읽지 않음, 에러, 경고)

### ✅ Phase 4: 백테스트 비교 (완료)

#### 6. BacktestComparison 페이지
- **파일**: `/frontend/src/pages/BacktestComparison.jsx`
- **기능**:
  - 여러 백테스트 결과 다중 선택
  - 최우수 전략 자동 표시 (Sharpe Ratio 기준)
  - 수익 곡선 비교 차트 (Equity Curve Overlay)
  - 총 수익률 비교 막대 차트
  - 상세 지표 비교 테이블 (10개 지표)
  - 결과 비교 페이지 라우팅 (`/backtest-comparison`)

### ✅ Phase 5: 전략 관리 개선 (완료)

#### 7. Strategy Management Enhancement
- **파일**:
  - `/frontend/src/pages/Strategy.jsx`
  - `/frontend/src/components/strategy/BacktestHistory.jsx`
- **기능**:
  - 4개 탭 구조 (전략 목록, 전략 편집, 백테스트, 백테스트 이력)
  - 백테스트 이력 테이블 (12개 칼럼)
  - 상세 결과 모달 (9개 핵심 지표)
  - 결과 비교 페이지 연동
  - 백테스트 실행 폼 (BacktestRunner)
  - 실시간 진행률 표시

### ✅ Phase 6: 거래 내역 개선 (완료)

#### 8. TradingHistory Enhancement
- **파일**: `/frontend/src/pages/TradingHistory.jsx`
- **기능**:
  - 통계 카드 (총 거래, 매수, 매도, 순손익)
  - 고급 필터링 (텍스트 검색, 방향, 상태, 날짜 범위)
  - Ant Design Table 스타일
  - 9개 칼럼 상세 표시
  - CSV 내보내기 (UTF-8 BOM)
  - 페이지네이션 (10/20/50/100)

---

## 시스템 아키텍처

### 디렉토리 구조

```
auto-dashboard/
├── backend/                    # FastAPI 백엔드
│   ├── src/
│   │   ├── api/               # API 엔드포인트
│   │   │   ├── auth.py        # 인증 (로그인/회원가입)
│   │   │   ├── account.py     # 계정 관리 (API 키)
│   │   │   ├── bot.py         # 봇 제어
│   │   │   ├── bitget.py      # Bitget API 연동
│   │   │   ├── order.py       # 주문 이력
│   │   │   ├── analytics.py   # 성과 분석
│   │   │   ├── alerts.py      # 알림 관리
│   │   │   └── backtest.py    # 백테스팅
│   │   ├── models/            # SQLAlchemy 모델
│   │   ├── schemas/           # Pydantic 스키마
│   │   ├── services/          # 비즈니스 로직
│   │   └── main.py            # FastAPI 앱
│   ├── alembic/               # 데이터베이스 마이그레이션
│   └── trading.db             # SQLite 데이터베이스
│
├── frontend/                   # React 프론트엔드
│   ├── src/
│   │   ├── pages/             # 페이지 컴포넌트
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Performance.jsx
│   │   │   ├── Strategy.jsx
│   │   │   ├── TradingHistory.jsx
│   │   │   ├── BacktestComparison.jsx
│   │   │   ├── Notifications.jsx
│   │   │   ├── Settings.jsx
│   │   │   └── Login.jsx
│   │   ├── components/        # 재사용 컴포넌트
│   │   │   ├── layout/
│   │   │   ├── charts/
│   │   │   ├── strategy/
│   │   │   ├── performance/
│   │   │   └── ...
│   │   ├── api/               # API 클라이언트
│   │   │   ├── client.js      # Axios 설정
│   │   │   ├── auth.js
│   │   │   ├── bot.js
│   │   │   ├── order.js
│   │   │   ├── analytics.js
│   │   │   ├── backtest.js
│   │   │   └── ...
│   │   ├── context/           # React Context
│   │   │   ├── AuthContext.jsx
│   │   │   ├── ThemeContext.jsx
│   │   │   └── WebSocketContext.jsx
│   │   └── App.jsx
│   └── package.json
│
├── nginx/                      # Nginx 설정
├── monitoring/                 # Prometheus + Grafana
├── docker-compose.yml
└── README.md
```

### API 엔드포인트 목록

#### 인증 (Auth)
- `POST /auth/register` - 회원가입
- `POST /auth/login` - 로그인
- `GET /auth/me` - 현재 사용자 정보

#### 계정 관리 (Account)
- `POST /account/save_keys` - API 키 저장
- `GET /account/get_keys` - API 키 조회 (시간당 3회 제한)
- `POST /account/test_connection` - API 연결 테스트

#### 봇 제어 (Bot)
- `GET /bot/status` - 봇 상태 조회
- `POST /bot/start` - 봇 시작
- `POST /bot/stop` - 봇 정지

#### Bitget API
- `GET /bitget/account` - 계정 잔고
- `GET /bitget/positions` - 포지션 목록
- `POST /bitget/positions/close` - 포지션 청산
- `GET /bitget/ticker/{symbol}` - 현재가 조회

#### 주문 (Order)
- `GET /order/history` - 주문 이력
- `GET /order/recent` - 최근 주문

#### 성과 분석 (Analytics)
- `GET /analytics/equity-curve` - 자산 곡선
- `GET /analytics/performance` - 성과 지표
- `GET /analytics/risk-metrics` - 리스크 지표

#### 알림 (Alerts)
- `GET /alerts/all` - 전체 알림
- `GET /alerts/urgent` - 긴급 알림
- `GET /alerts/statistics` - 알림 통계
- `POST /alerts/resolve/{id}` - 알림 읽음 처리
- `POST /alerts/resolve-all` - 모든 알림 읽음
- `DELETE /alerts/clear-resolved` - 읽은 알림 삭제

#### 백테스트 (Backtest)
- `POST /backtest/start` - 백테스트 시작
- `GET /backtest/result/{id}` - 백테스트 결과
- `GET /backtest/all` - 모든 백테스트
- `GET /backtest_result/result/{id}` - 백테스트 상세

### 데이터베이스 스키마

**주요 테이블**:
1. `users` - 사용자 정보
2. `api_keys` - Bitget API 키 (암호화 저장)
3. `orders` - 주문 이력
4. `positions` - 포지션 정보
5. `alerts` - 시스템 알림
6. `backtests` - 백테스트 설정
7. `backtest_results` - 백테스트 결과
8. `strategies` - 전략 설정
9. `bot_status` - 봇 상태

### 환경 변수

**Backend** (`/backend/.env`):
```bash
DATABASE_URL=sqlite+aiosqlite:///./trading.db
ENCRYPTION_KEY=Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

**Frontend**:
- 환경 변수 불필요 (API URL은 하드코딩: `http://localhost:8000`)

---

## 보완해야 할 점

### 🔴 높은 우선순위

#### 1. 보안 강화
- **문제**: JWT Secret Key가 하드코딩되어 있음
- **해결**: 환경 변수로 관리하고 복잡한 키 생성
- **파일**: `/backend/src/api/auth.py`

```python
# 현재 (취약)
JWT_SECRET_KEY = "your-super-secret-key-change-this-in-production"

# 개선 필요
import os
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY must be set")
```

#### 2. API 키 암호화 개선
- **문제**: 암호화 키가 코드에 하드코딩
- **해결**: 환경 변수로 관리 + Key Rotation 구현
- **파일**: `/backend/src/services/encryption.py`

#### 3. 에러 처리 강화
- **문제**: 일부 API에서 에러 메시지가 사용자에게 직접 노출
- **해결**: 에러 로깅 + 사용자 친화적 메시지 분리
- **파일**: 모든 `/backend/src/api/*.py` 파일

#### 4. CORS 설정 개선
- **문제**: 개발 환경 URL이 하드코딩됨
- **해결**: 환경 변수로 관리
- **파일**: `/backend/src/main.py`

```python
# 현재
allowed_origins = [
    "http://localhost:3003",
    # ...
]

# 개선 필요
allowed_origins = os.getenv("CORS_ORIGINS", "").split(",")
```

#### 5. 비밀번호 정책
- **문제**: 비밀번호 복잡도 검증 없음
- **해결**: 최소 길이, 특수문자 포함 등 정책 추가
- **파일**: `/backend/src/api/auth.py`

### 🟡 중간 우선순위

#### 6. Rate Limiting
- **문제**: API 호출 제한이 없음 (DoS 취약)
- **해결**: FastAPI Rate Limiter 미들웨어 추가
- **참고**: `slowapi` 라이브러리 사용

#### 7. 로깅 시스템
- **문제**: 콘솔 로그만 사용 중
- **해결**: 파일 로그 + 로그 레벨 관리
- **추천**: Python `logging` 모듈 + `loguru`

#### 8. 데이터베이스 백업
- **문제**: SQLite 백업 자동화 없음
- **해결**: Cron 작업으로 매일 백업 + S3 저장

#### 9. WebSocket 재연결 로직
- **문제**: 연결 끊김 시 자동 재연결이 불안정할 수 있음
- **해결**: 지수 백오프 + 최대 재시도 횟수 설정
- **파일**: `/frontend/src/context/WebSocketContext.jsx`

#### 10. 테스트 코드
- **문제**: 단위 테스트 없음
- **해결**:
  - Backend: `pytest` + `pytest-asyncio`
  - Frontend: `vitest` + `@testing-library/react`

### 🟢 낮은 우선순위

#### 11. 성능 최적화
- **문제**: 큰 데이터셋 로딩 시 느릴 수 있음
- **해결**:
  - 백엔드: 쿼리 최적화, 페이지네이션 개선
  - 프론트엔드: React.memo, useMemo, useCallback 활용

#### 12. UI/UX 개선
- **문제**: 일부 페이지의 모바일 반응형 개선 필요
- **해결**: Ant Design Grid 시스템 활용

#### 13. 국제화 (i18n)
- **문제**: 한국어만 지원
- **해결**: `react-i18next` 라이브러리 도입

#### 14. 다크 모드
- **문제**: 라이트 모드만 지원
- **해결**: ThemeContext에 다크 모드 추가

---

## 앞으로 해야 할 작업

### 📌 Phase 7: LiveTrading 페이지 개선 (추천)

**목표**: 실시간 거래 모니터링 강화

**작업 내역**:
1. 실시간 포지션 테이블 업그레이드
   - 청산가 표시 (Bitget API 지원 시)
   - 미실현 손익 실시간 업데이트
   - Panic Close 버튼 (긴급 청산)

2. 주문 북 (Order Book) 표시
   - 호가창 실시간 업데이트
   - 매수/매도 호가 비율 시각화

3. 실시간 차트 개선
   - TradingView 라이브러리 통합 검토
   - 기술적 지표 추가 (MA, RSI, MACD 등)

**예상 소요 시간**: 4-6시간

### 📌 Phase 8: BotControl 페이지 개선

**목표**: 봇 제어 및 모니터링 기능 강화

**작업 내역**:
1. 봇 설정 관리
   - 레버리지 설정
   - 포지션 크기 제한
   - Stop Loss / Take Profit 자동 설정

2. 봇 실행 로그
   - 실시간 로그 스트리밍
   - 로그 레벨 필터링
   - 로그 검색 기능

3. 봇 성능 모니터링
   - CPU / 메모리 사용량
   - API 호출 횟수
   - 에러율 모니터링

**예상 소요 시간**: 4-6시간

### 📌 Phase 9: 리스크 관리 기능

**목표**: 계정 보호 및 리스크 통제

**작업 내역**:
1. 리스크 한도 설정
   - 일일 손실 한도
   - 최대 포지션 개수
   - 최대 레버리지 제한

2. 자동 손실 차단
   - 일일 손실 한도 도달 시 자동 봇 정지
   - 알림 발송

3. 리스크 대시보드
   - 현재 리스크 레벨 시각화
   - 경고 알림
   - 리스크 히스토리

**예상 소요 시간**: 6-8시간

### 📌 Phase 10: 다중 거래소 지원

**목표**: Bitget 외 다른 거래소 연동

**작업 내역**:
1. 거래소 추상화 레이어
   - 공통 인터페이스 정의
   - 어댑터 패턴 적용

2. Binance, Bybit 연동
   - API 클라이언트 구현
   - 주문 형식 통일

3. 거래소 선택 UI
   - Settings에서 거래소 선택
   - 거래소별 API 키 관리

**예상 소요 시간**: 10-15시간

### 📌 Phase 11: 고급 백테스팅

**목표**: 백테스팅 기능 고도화

**작업 내역**:
1. 파라미터 최적화
   - 그리드 서치
   - 유전 알고리즘

2. Walk-Forward 분석
   - 시계열 교차 검증
   - 오버피팅 방지

3. 멀티 전략 백테스팅
   - 포트폴리오 백테스팅
   - 전략 간 상관관계 분석

**예상 소요 시간**: 15-20시간

### 📌 Phase 12: 소셜 기능

**목표**: 커뮤니티 및 공유 기능

**작업 내역**:
1. 전략 공유
   - 전략 퍼블리싱
   - 전략 마켓플레이스

2. 리더보드
   - 사용자별 수익률 순위
   - 전략별 순위

3. 소셜 알림
   - 텔레그램 봇 연동
   - 디스코드 웹훅

**예상 소요 시간**: 12-18시간

---

## 배포 및 운영 가이드

### 개발 환경 실행

#### Backend 실행
```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend

# 가상환경 활성화
source venv/bin/activate  # Mac/Linux
# 또는
venv\Scripts\activate  # Windows

# 환경 변수 설정
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="

# 서버 실행
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend 실행
```bash
cd /Users/mr.joo/Desktop/auto-dashboard/frontend

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행
npm run dev

# 접속: http://localhost:3003
```

#### 테스트 계정
- **아이디**: `admin@admin.com`
- **비밀번호**: `admin123`

### 프로덕션 배포

#### Docker Compose 사용
```bash
cd /Users/mr.joo/Desktop/auto-dashboard

# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

#### 환경 변수 설정 (프로덕션)
`.env.production` 파일 생성:
```bash
# Backend
DATABASE_URL=postgresql://user:password@db:5432/trading  # SQLite 대신 PostgreSQL 권장
ENCRYPTION_KEY=<강력한-암호화-키-생성>
JWT_SECRET_KEY=<강력한-JWT-시크릿-생성>

# Frontend
VITE_API_URL=https://api.yourdomain.com

# Bitget API (선택)
BITGET_API_KEY=<your-api-key>
BITGET_SECRET_KEY=<your-secret-key>
BITGET_PASSPHRASE=<your-passphrase>
```

### 데이터베이스 마이그레이션

```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend

# 마이그레이션 생성
alembic revision --autogenerate -m "description"

# 마이그레이션 실행
alembic upgrade head

# 롤백
alembic downgrade -1
```

### 모니터링 설정

#### Prometheus + Grafana
```bash
cd /Users/mr.joo/Desktop/auto-dashboard

# 모니터링 스택 실행
docker-compose -f docker-compose.monitoring.yml up -d

# Grafana 접속: http://localhost:3000
# 기본 계정: admin / admin
```

---

## 문제 해결 가이드

### 🐛 일반적인 문제

#### 1. 로그인 실패
**증상**: "로그인 실패" 메시지
**원인**:
- 백엔드 서버가 실행되지 않음
- CORS 설정 문제
- 데이터베이스 연결 실패

**해결**:
```bash
# 백엔드 상태 확인
curl http://localhost:8000/health

# 백엔드 로그 확인
cd backend
tail -f logs/app.log

# 데이터베이스 확인
sqlite3 trading.db "SELECT * FROM users;"
```

#### 2. API 키 저장 실패
**증상**: "API 키 저장에 실패했습니다"
**원인**: 암호화 키 문제

**해결**:
```bash
# 환경 변수 확인
echo $ENCRYPTION_KEY

# 재설정
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
```

#### 3. WebSocket 연결 끊김
**증상**: 실시간 데이터 업데이트 안 됨
**원인**: WebSocket 서버 연결 실패

**해결**:
- 백엔드 재시작
- 프론트엔드 페이지 새로고침
- 브라우저 콘솔에서 WebSocket 상태 확인

#### 4. 백테스트 시간 초과
**증상**: "백테스트가 시간 초과되었습니다"
**원인**:
- 데이터 양이 너무 많음
- Bitget API 응답 느림

**해결**:
- 백테스트 기간 단축
- 타임아웃 설정 증가 (`BacktestRunner.jsx:54`)

#### 5. 포트 충돌
**증상**: "Port already in use"
**원인**: 다른 프로세스가 포트 사용 중

**해결**:
```bash
# 프로세스 찾기
lsof -i :8000  # 백엔드
lsof -i :3003  # 프론트엔드

# 프로세스 종료
kill -9 <PID>
```

### 🔍 디버깅 팁

#### Backend 로깅 활성화
```python
# /backend/src/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Frontend 디버깅
```javascript
// 브라우저 콘솔에서 API 응답 확인
localStorage.getItem('token')  // JWT 토큰 확인
```

#### 데이터베이스 직접 확인
```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend

sqlite3 trading.db
> .tables
> SELECT * FROM users;
> SELECT * FROM orders LIMIT 10;
```

---

## 📚 참고 문서

### 내부 문서
- `README.md` - 프로젝트 소개
- `FRONTEND_IMPLEMENTATION_PLAN.md` - 프론트엔드 구현 계획
- `Frontend_Structure_Outline.md` - 프론트엔드 구조 설계
- `QUICK_START_GUIDE.md` - 빠른 시작 가이드

### 외부 문서
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [React 공식 문서](https://react.dev/)
- [Ant Design 문서](https://ant.design/)
- [Bitget API 문서](https://bitgetlimited.github.io/apidoc/en/mix/)

---

## 👥 연락처 및 지원

**프로젝트 이슈**:
GitHub Issues: `/Users/mr.joo/Desktop/auto-dashboard/.github/issues` (설정 필요)

**긴급 문제**:
1. 백엔드 서버가 다운된 경우: 즉시 재시작
2. 데이터베이스 손상: 백업에서 복원
3. 보안 이슈 발견: 즉시 서버 중지 + 로그 분석

---

## ✅ 인수인계 체크리스트

- [ ] 프로젝트 코드 저장소 접근 권한 확인
- [ ] 개발 환경 설정 완료 (Backend + Frontend)
- [ ] 테스트 계정으로 로그인 성공
- [ ] 모든 페이지 접근 및 기능 테스트
- [ ] 데이터베이스 백업 방법 숙지
- [ ] 배포 프로세스 이해
- [ ] 환경 변수 설정 이해
- [ ] 로그 확인 방법 숙지
- [ ] 일반적인 문제 해결 방법 숙지
- [ ] 향후 개발 계획 검토

---

**작성자**: Claude (AI Assistant)
**최종 검토**: 2025-12-04
**버전**: 1.0

---

## 🎯 핵심 요약

### 현재 상태
✅ **완료**: 6개 Phase (Dashboard, Performance, Notifications, Backtest Comparison, Strategy, Trading History)
✅ **기능**: 실시간 거래 모니터링, 백테스팅, 성과 분석, 알림 시스템
✅ **기술**: React + FastAPI + SQLite + WebSocket

### 보완 필요
🔴 **보안**: JWT Secret, API 키 암호화, CORS 설정
🟡 **안정성**: Rate Limiting, 로깅, 백업, 테스트
🟢 **최적화**: 성능, UI/UX, i18n, 다크모드

### 다음 단계
📌 **Phase 7-12**: LiveTrading 개선, BotControl, 리스크 관리, 다중 거래소, 고급 백테스팅, 소셜 기능

### 긴급 연락
⚠️ **서버 다운**: 재시작 (`docker-compose restart`)
⚠️ **DB 손상**: 백업 복원
⚠️ **보안 이슈**: 서버 중지 + 로그 분석

---

**행운을 빕니다! 🚀**
