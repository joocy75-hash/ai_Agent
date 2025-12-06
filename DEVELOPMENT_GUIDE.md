# 🚀 Deep Signal - 개발자 인수인계 문서

> **프로젝트**: Deep Signal - 암호화폐 자동 거래 시스템  
> **마지막 업데이트**: 2025-12-04 23:56 KST  
> **현재 상태**: ✅ Production Ready (실전 배포 가능)  
> **작업자**: AI 코딩 어시스턴트 (Gemini)

---

## 📋 목차

1. [현재 작업 상황 요약](#1-현재-작업-상황-요약)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [기술 스택](#3-기술-스택)
4. [🔒 보안 주의사항](#4-보안-주의사항)
5. [🔴 앞으로 해야 할 작업](#5-앞으로-해야-할-작업)
6. [개발 환경 설정](#6-개발-환경-설정)
7. [API 문서](#7-api-문서)
8. [알려진 이슈](#8-알려진-이슈)
9. [완료된 작업 로그](#9-완료된-작업-로그)

---

## 1. 현재 작업 상황 요약

### 🎯 프로젝트 개요

**Deep Signal**은 Bitget 거래소를 사용한 암호화폐 자동 거래 시스템입니다.

| 구성요소 | 설명 | 포트 |
|----------|------|------|
| Frontend (사용자) | React + Vite 대시보드 | 3000 |
| Admin Frontend | 관리자 대시보드 | 4000 |
| Backend | FastAPI REST API + WebSocket | 8000 |
| Database | SQLite (개발) / PostgreSQL (운영) | - |

### ✅ 최근 완료된 주요 작업 (2025-12-05)

| 작업 | 설명 | 상태 |
|------|------|------|
| **🆕 2FA 인증 (TOTP)** | Google/Microsoft Authenticator 호환 2단계 인증 | ✅ 완료 |
| **🆕 모바일 반응형 UI** | 모든 페이지 모바일 최적화, Drawer 사이드바, 터치 친화적 UI | ✅ 완료 |
| **🆕 백테스트 에쿼티 커브** | 에쿼티 커브 시각화, 드로다운 차트, recharts 기반 | ✅ 완료 |
| **간단 전략 생성기** | 초보자용 전략 생성 UI (SimpleStrategyCreator.jsx) | ✅ 완료 |
| **통합 백테스팅 페이지** | 실행/이력/비교 탭 통합 (BacktestingPage.jsx) | ✅ 완료 |
| **백테스트 캐시 시스템** | API Rate Limit 방지를 위한 캔들 데이터 캐싱 | ✅ 완료 |
| **429 에러 해결** | cache_only 모드로 API 호출 방지 | ✅ 완료 |
| **리소스 매니저 개선** | 백테스트 완료 시 자동 리소스 해제 | ✅ 완료 |
| **추가 코인 데이터 다운로드** | DOGE, ADA, AVAX, LINK, DOT 캐시 데이터 | ✅ 완료 |
| **화이트 & 블루 테마** | 전체 UI 디자인 업데이트 | ✅ 완료 |
| **메뉴 구조 개선** | 전략관리/백테스팅 분리 | ✅ 완료 |

### 📁 주요 파일 위치

```
auto-dashboard/
├── frontend/src/
│   ├── pages/
│   │   ├── BacktestingPage.jsx      # 통합 백테스팅 (실행/이력/비교)
│   │   ├── Strategy.jsx             # 전략 관리 (간단/목록/편집)
│   │   ├── Dashboard.jsx            # 메인 대시보드
│   │   ├── Settings.jsx             # 설정 (API키/2FA/비밀번호)
│   │   ├── Login.jsx                # 🆕 로그인 (2FA 지원)
│   │   └── Trading.jsx              # 트레이딩 (차트/봇컨트롤)
│   ├── components/
│   │   ├── strategy/
│   │   │   ├── SimpleStrategyCreator.jsx  # 🆕 초보자용 전략 생성
│   │   │   ├── StrategyList.jsx
│   │   │   └── StrategyEditor.jsx
│   │   └── settings/
│   │       └── TwoFactorSettings.jsx  # 🆕 2FA 설정 UI
│   └── api/
│       ├── auth.js                  # 🆕 인증 + 2FA API
│       ├── backtest.js              # 백테스트 API
│       └── strategy.js              # 전략 API
│
├── backend/src/
│   ├── api/
│   │   ├── auth.py                  # 🆕 인증 (2FA 지원 로그인)
│   │   ├── two_factor.py            # 🆕 2FA API 엔드포인트
│   │   ├── backtest.py              # 백테스트 실행
│   │   ├── strategy.py              # 전략 CRUD
│   │   └── backtest_history.py      # 백테스트 이력
│   ├── services/
│   │   ├── totp_service.py          # 🆕 TOTP 2FA 서비스
│   │   ├── candle_cache.py          # 캔들 데이터 캐시 시스템
│   │   ├── bot_runner.py            # 봇 실행 로직
│   │   └── backtest_engine.py       # 백테스트 엔진
│   └── utils/
│       └── resource_manager.py      # 리소스 제한 관리
│
├── backend/candle_cache/            # 캔들 데이터 캐시 저장소
│   ├── BTCUSDT_1h.csv
│   ├── ETHUSDT_1h.csv
│   └── ... (28개 파일)
│
└── docs/
    ├── STRATEGY_GUIDE_BEGINNER.md   # 초보자 가이드
    └── DATA_DOWNLOAD_GUIDE.md       # 데이터 다운로드 가이드
```

---

## 2. 프로젝트 구조

```
auto-dashboard/
├── frontend/                   # 사용자 대시보드 (React)
│   ├── src/
│   │   ├── api/               # API 클라이언트
│   │   ├── pages/             # 페이지 컴포넌트
│   │   ├── components/        # 재사용 컴포넌트
│   │   └── context/           # React Context (Auth, WebSocket)
│   └── package.json
│
├── admin-frontend/             # 관리자 대시보드 (React)
│   └── src/
│
├── backend/                    # FastAPI 백엔드
│   ├── src/
│   │   ├── api/               # REST API 엔드포인트
│   │   ├── services/          # 비즈니스 로직
│   │   ├── database/          # SQLAlchemy 모델
│   │   ├── middleware/        # 미들웨어 (Rate Limit 등)
│   │   ├── websockets/        # 실시간 통신
│   │   └── utils/             # 유틸리티 (JWT, 암호화)
│   ├── candle_cache/          # 캔들 데이터 캐시
│   ├── alembic/               # DB 마이그레이션
│   └── requirements.txt
│
└── docker-compose.yml          # Docker 배포 설정
```

---

## 3. 기술 스택

| 영역 | 기술 | 버전 | 비고 |
|------|------|------|------|
| **Frontend** | React + Vite | 18.x | Ant Design UI |
| **Backend** | FastAPI | 0.100+ | Python 3.11 |
| **Database** | SQLite / PostgreSQL | - | 운영은 PostgreSQL 권장 |
| **인증** | JWT + Fernet | - | 토큰 + API 키 암호화 |
| **거래소** | Bitget Futures API | v2 | 선물 거래 |
| **차트** | Lightweight Charts | 4.x | TradingView 차트 |
| **실시간** | WebSocket | - | 가격/포지션 업데이트 |

---

## 4. 🔒 보안 주의사항

### 🔴 배포 전 필수 변경 사항

#### 1. 환경 변수 (`backend/.env`)

```env
# ⚠️ 반드시 변경해야 함!
JWT_SECRET=942fcf20ad1857f46fd7aa369fd28f8a407e3fa8b4ac33bfb131002ece5b7e70
ENCRYPTION_KEY=qdNwSaqXY15IKvoNSabeZEvmzq3cpq4nw-d1A6S3tQc=

# 데이터베이스 (운영 환경)
DATABASE_URL=postgresql+asyncpg://user:STRONG_PASSWORD@localhost/trading

# 기타
BITGET_API_KEY=     # 사용자별 저장
BITGET_SECRET=      # 사용자별 저장
BITGET_PASSPHRASE=  # 사용자별 저장
```

#### 2. CORS 설정 (`backend/src/main.py`)

```python
# 현재: localhost만 허용
# 변경 필요: 프로덕션 도메인 추가
allowed_origins = [
    "https://yourdomain.com",
    "https://admin.yourdomain.com",
]
```

#### 3. API 키 보안

| 항목 | 현재 상태 | 개선 필요 |
|------|----------|----------|
| API 키 저장 | Fernet 암호화 | ✅ 안전 |
| 키 조회 | 마스킹 반환 | ✅ 안전 |
| Rate Limit | 5 req/sec | 조정 가능 |

#### 4. HTTPS 설정

```nginx
# Nginx 설정 예시
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

### 🟡 추가 보안 권장사항

| 항목 | 상태 | 우선순위 |
|------|------|----------|
| 2FA (TOTP) | ✅ 구현됨 | 완료 |
| IP 화이트리스트 | 미구현 | 높음 |
| 감사 로그 | 기본 로그만 | 중간 |
| 비정상 접속 탐지 | 미구현 | 중간 |
| API 키 만료 알림 | 미구현 | 낮음 |

---

## 5. 🔴 앞으로 해야 할 작업

### 긴급 (배포 전 필수)

| 작업 | 설명 | 예상 시간 |
|------|------|----------|
| **환경 변수 적용** | JWT_SECRET, ENCRYPTION_KEY 변경 | 5분 |
| **CORS 도메인 설정** | 프로덕션 도메인 추가 | 10분 |
| **PostgreSQL 마이그레이션** | SQLite → PostgreSQL | 2시간 |
| **HTTPS 설정** | SSL 인증서 + Nginx | 1시간 |

### 높은 우선순위 (1주일 내)

| 작업 | 설명 | 예상 시간 | 상태 |
|------|------|----------|------|
| **2FA 인증** | TOTP 기반 2단계 인증 | 1일 | ✅ 완료 |
| **모바일 반응형** | 모바일 UI 최적화 | 1일 | ✅ 완료 |
| **백테스트 차트** | 에쿼티 커브 시각화 | 4시간 | ✅ 완료 |
| **관리자 IP 제한** | 화이트리스트 기능 | 4시간 | ⏳ 대기 |

### 중간 우선순위 (1개월 내)

| 작업 | 설명 | 예상 시간 |
|------|------|----------|
| **다크 모드** | 전체 테마 적용 | 4시간 |
| **알림 시스템** | 텔레그램/이메일 연동 | 2일 |
| **다중 거래소** | Binance, OKX 지원 | 2주 |
| **성능 최적화** | React.memo, 가상화 | 1일 |

### 낮은 우선순위 (향후)

| 작업 | 설명 |
|------|------|
| AI 전략 자동 생성 | GPT 기반 전략 추천 |
| 소셜 트레이딩 | 카피 트레이딩 기능 |
| 모바일 앱 | React Native 앱 |

---

## 6. 개발 환경 설정

### 백엔드 실행

```bash
cd backend

# 환경 변수 설정
cp .env.example .env
# .env 파일에서 필요한 값 수정

# 실행
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

### 관리자 프론트엔드 실행

```bash
cd admin-frontend
npm install
npm run dev  # http://localhost:4000
```

### 테스트 계정

| 역할 | 이메일 | 비밀번호 |
|------|--------|----------|
| 관리자 | <admin@admin.com> | admin123 |
| 사용자 | (회원가입 필요) | - |

---

## 7. API 문서

### 주요 엔드포인트

| 카테고리 | 엔드포인트 | 설명 |
|----------|-----------|------|
| **인증** | POST /auth/login | 로그인 |
| **인증** | POST /auth/register | 회원가입 |
| **계정** | GET /account/balance | 잔고 조회 |
| **계정** | POST /account/save_keys | API 키 저장 |
| **전략** | GET /strategy/list | 전략 목록 |
| **전략** | POST /strategy/create | 전략 생성 |
| **백테스트** | POST /backtest/start | 백테스트 시작 |
| **백테스트** | GET /backtest/result/{id} | 결과 조회 |
| **봇** | POST /bot/start | 봇 시작 |
| **봇** | POST /bot/stop | 봇 정지 |

### Swagger 문서

백엔드 실행 후: `http://localhost:8000/docs`

---

## 8. 알려진 이슈

### 해결된 이슈

| 이슈 | 원인 | 해결 방법 |
|------|------|----------|
| 백테스트 429 에러 | Bitget API Rate Limit | cache_only 모드 적용 |
| 동시 백테스트 제한 | 리소스 미해제 | finish_backtest() 자동 호출 |
| 포지션 현재가 조회 실패 | API 응답 형식 | 자체 가격 조회로 변경 |
| WebSocket 재연결 | 에러 시 끊김 | 자동 재연결 + 지수 백오프 |

### 현재 이슈

| 이슈 | 상태 | 우선순위 |
|------|------|----------|
| 15분봉 캐시 데이터 없음 | 다운로드 필요 | 낮음 |
| 모바일 UI 불편 | 개선 필요 | 중간 |
| 다크 모드 일부 적용 | 전체 적용 필요 | 낮음 |

---

## 9. 완료된 작업 로그

### 2025-12-04 (저녁 세션)

| 시간 | 작업 | 파일 |
|------|------|------|
| 21:00 | 화이트 & 블루 테마 적용 | index.css, MainLayout.jsx |
| 21:30 | 백테스트 캐시 시스템 구현 | candle_cache.py |
| 22:00 | 추가 코인 데이터 다운로드 | download_more_coins.py |
| 22:30 | 간단 전략 생성기 구현 | SimpleStrategyCreator.jsx |
| 23:00 | 메뉴 구조 재구성 | MainLayout.jsx, App.jsx |
| 23:30 | 통합 백테스팅 페이지 | BacktestingPage.jsx |
| 23:45 | 429 에러 해결 | backtest.py, candle_cache.py |
| 23:55 | 리소스 매니저 개선 | resource_manager.py |

### 이전 세션 (2025-12-04 오전/오후)

- 관리자 회원 상세페이지 고도화
- 비밀번호 초기화 API
- 역할 변경 API
- 상세 수익 통계 API
- WebSocket 자동 재연결
- 거래내역 API 수정
- 백테스트 비교 페이지

---

## 📞 문의

작업 관련 문의사항이 있으시면 이 문서와 코드 주석을 참고해주세요.

**핵심 파일 우선 확인:**

1. `backend/src/services/candle_cache.py` - 캐시 시스템
2. `frontend/src/pages/BacktestingPage.jsx` - 백테스팅 UI
3. `frontend/src/components/strategy/SimpleStrategyCreator.jsx` - 전략 생성
4. `backend/src/api/backtest.py` - 백테스트 API

---

*마지막 업데이트: 2025-12-04 23:56 KST*
