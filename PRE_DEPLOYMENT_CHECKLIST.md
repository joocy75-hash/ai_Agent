# 🚀 배포 전 최종 점검 가이드

> 작성일: 2025-12-06
> 프로젝트: Auto Dashboard (암호화폐 AI 자동매매 플랫폼)

---

## 📋 목차

1. [프로젝트 구조 요약](#프로젝트-구조-요약)
2. [보안 체크리스트](#보안-체크리스트)
3. [환경 설정 필수 사항](#환경-설정-필수-사항)
4. [백엔드 점검 사항](#백엔드-점검-사항)
5. [프론트엔드 점검 사항](#프론트엔드-점검-사항)
6. [관리자 페이지 점검 사항](#관리자-페이지-점검-사항)
7. [배포 전 필수 작업](#배포-전-필수-작업)
8. [남은 개발 작업 (Optional)](#남은-개발-작업-optional)
9. [배포 절차](#배포-절차)
10. [배포 후 모니터링](#배포-후-모니터링)

---

## 🏗️ 프로젝트 구조 요약

```
auto-dashboard/
├── backend/                 # FastAPI 백엔드
│   └── src/
│       ├── api/             # 28개 API 라우터
│       ├── database/        # SQLAlchemy 모델
│       ├── middleware/      # Rate Limit, IP Whitelist 등
│       ├── services/        # 비즈니스 로직
│       ├── utils/           # 유틸리티 (JWT, 암호화 등)
│       └── workers/         # 봇 매니저
├── frontend/                # React + Vite 사용자 프론트엔드
│   └── src/
│       ├── pages/           # 13개 페이지
│       ├── components/      # UI 컴포넌트
│       ├── api/             # API 클라이언트
│       └── context/         # Auth, WebSocket 컨텍스트
├── admin-frontend/          # React 관리자 대시보드
│   └── src/
│       ├── pages/           # 로그인, 대시보드
│       └── api/             # API 클라이언트
├── nginx/                   # Nginx 설정
└── docker-compose.yml       # Docker 배포 설정
```

---

## 🔒 보안 체크리스트

### ✅ 완료된 보안 기능

| 항목 | 상태 | 설명 |
|------|------|------|
| JWT 인증 | ✅ | `HS256` 알고리즘, 24시간 만료 |
| 비밀번호 해싱 | ✅ | `bcrypt` 사용 |
| API 키 암호화 | ✅ | `Fernet` 대칭 암호화 (AES-128) |
| Rate Limiting | ✅ | IP/사용자별 요청 제한 |
| CORS 설정 | ✅ | 허용된 도메인만 접근 |
| RBAC | ✅ | `user`/`admin` 역할 분리 |
| 관리자 IP 화이트리스트 | ✅ | 프로덕션에서만 활성화 |
| 2단계 인증 (2FA) | ✅ | TOTP 기반 |
| XSS 방지 헤더 | ✅ | Nginx 설정에 포함 |

### ⚠️ 배포 전 반드시 확인/조치할 사항

| 항목 | 우선순위 | 조치 사항 |
|------|----------|----------|
| JWT_SECRET 변경 | 🔴 **긴급** | 기본값 `change_me` → 32자 이상 랜덤 문자열 |
| ENCRYPTION_KEY 설정 | 🔴 **긴급** | 환경변수로 설정 (Fernet.generate_key() 사용) |
| DATABASE_URL 변경 | 🔴 **긴급** | PostgreSQL 프로덕션 DB 연결 |
| POSTGRES_PASSWORD 변경 | 🔴 **긴급** | 강력한 비밀번호로 변경 |
| REDIS_PASSWORD 변경 | 🟡 높음 | 강력한 비밀번호로 변경 |
| ADMIN_IP_WHITELIST 설정 | 🟡 높음 | 관리자 IP 주소 등록 |
| CORS_ORIGINS 설정 | 🟡 높음 | 실제 도메인으로 변경 |
| HTTPS 인증서 | 🟡 높음 | Let's Encrypt SSL 발급 |
| 디버그 모드 비활성화 | 🟡 높음 | `DEBUG=false` 확인 |
| Google/Kakao OAuth 설정 | 🟢 보통 | 실제 클라이언트 ID/시크릿 등록 |

### 🔑 필수 환경 변수 목록

```bash
# [필수] 보안
JWT_SECRET=your-super-secret-jwt-key-minimum-32-characters
ENCRYPTION_KEY=<Fernet.generate_key() 결과>

# [필수] 데이터베이스
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/trading
POSTGRES_PASSWORD=<strong-password>

# [필수] Redis
REDIS_URL=redis://default:<password>@redis:6379
REDIS_PASSWORD=<strong-password>

# [권장] 관리자 보안
ADMIN_IP_WHITELIST=123.45.67.89,111.222.333.444
ENVIRONMENT=production

# [권장] CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
FRONTEND_URL=https://yourdomain.com

# [선택] OAuth
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
KAKAO_CLIENT_ID=<your-kakao-client-id>

# [선택] 텔레그램
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_CHAT_ID=<chat-id>

# [선택] AI 전략
DEEPSEEK_API_KEY=<your-api-key>
```

---

## ⚙️ 백엔드 점검 사항

### ✅ API 엔드포인트 현황 (28개 라우터)

| 카테고리 | 엔드포인트 | 상태 | 비고 |
|----------|-----------|------|------|
| 인증 | `/auth/*` | ✅ | 로그인, 회원가입, 비밀번호 변경 |
| OAuth | `/auth/google/*`, `/auth/kakao/*` | ✅ | 소셜 로그인 |
| 2FA | `/2fa/*` | ✅ | TOTP 기반 2단계 인증 |
| 계정 | `/account/*` | ✅ | API 키, 잔고, 리스크 설정 |
| 봇 | `/bot/*` | ✅ | 봇 시작/정지/상태 |
| 전략 | `/strategy/*` | ✅ | 전략 CRUD |
| AI 전략 | `/ai-strategy/*` | ✅ | DeepSeek 기반 전략 생성 |
| 차트 | `/chart/*` | ✅ | 캔들, 시장 데이터 |
| 백테스트 | `/backtest/*` | ✅ | 백테스트 실행/결과 |
| 거래 | `/trades/*` | ✅ | 거래 내역 |
| 분석 | `/analytics/*` | ✅ | 성과 분석 |
| 포지션 | `/positions/*` | ✅ | 포지션 조회 |
| 알림 | `/alerts/*` | ✅ | 알림 관리 |
| 텔레그램 | `/telegram/*` | ✅ | 텔레그램 봇 설정 |
| 관리자 | `/admin/*` | ✅ | 사용자/봇/분석/로그 관리 |
| 헬스 | `/health` | ✅ | 서버 상태 체크 |
| WebSocket | `/ws/*` | ✅ | 실시간 통신 |

### ⚠️ 백엔드 잠재적 이슈

| 이슈 | 심각도 | 설명 | 해결 방법 |
|------|--------|------|----------|
| JWT 토큰 블랙리스트 미구현 | 🟡 | 강제 로그아웃 시 토큰 즉시 무효화 불가 | Redis 토큰 블랙리스트 구현 |
| 사용자별 잔고 조회 미구현 | 🟢 | `total_balance` 항상 0.0 반환 | 거래소 API 연동 |
| 봇 핸들러 멀티유저 | 🟢 | 현재 첫 번째 사용자 설정만 로드 | 사용자별 봇 핸들러 분리 |

---

## 🎨 프론트엔드 점검 사항

### ✅ 페이지 현황 (13개)

| 페이지 | 파일 | 상태 | 비고 |
|--------|------|------|------|
| 로그인/랜딩 | `Login.jsx` | ✅ | 새 디자인 적용 |
| 대시보드 | `Dashboard.jsx` | ✅ | 포트폴리오, 차트, 알림 |
| 트레이딩 | `Trading.jsx` | ✅ | 차트 + 봇 컨트롤 통합 |
| 백테스팅 | `BacktestingPage.jsx` | ✅ | 백테스트 실행/결과 |
| 백테스트 비교 | `BacktestComparison.jsx` | ✅ | 결과 비교 |
| 백테스트 히스토리 | `BacktestHistoryPage.jsx` | ✅ | 기록 조회 |
| 설정 | `Settings.jsx` | ✅ | API 키, 텔레그램, 2FA 등 |
| 전략 | `Strategy.jsx` | ✅ | 전략 관리 |
| 거래 내역 | `TradingHistory.jsx` | ✅ | 거래 기록 |
| 알림 | `Notifications.jsx` | ✅ | 알림 목록 |
| OAuth 콜백 | `OAuthCallback.jsx` | ✅ | 소셜 로그인 처리 |

### ⚠️ 프론트엔드 점검 필요 사항

| 항목 | 우선순위 | 조치 사항 |
|------|----------|----------|
| API URL 환경변수 | 🔴 **긴급** | `VITE_API_URL` 프로덕션 주소로 설정 |
| WebSocket URL | 🔴 **긴급** | `VITE_WS_URL` 프로덕션 주소로 설정 |
| 에러 바운더리 | 🟡 높음 | 전역 에러 핸들링 컴포넌트 추가 권장 |
| 로딩 스켈레톤 | 🟢 보통 | UX 개선을 위한 스켈레톤 UI |

---

## 👨‍💼 관리자 페이지 점검 사항

### ✅ 기능 현황

| 기능 | 상태 | 설명 |
|------|------|------|
| 관리자 로그인 | ✅ | JWT 기반, role 검증 |
| 사용자 목록 | ✅ | 통계 포함 |
| 사용자 상세 | ✅ | 거래 통계, 봇 현황 |
| 사용자 생성 | ✅ | 관리자가 직접 생성 |
| 계정 활성화/정지 | ✅ | 봇 자동 정지 포함 |
| 비밀번호 초기화 | ✅ | 랜덤 비밀번호 생성 |
| 역할 변경 | ✅ | user ↔ admin |
| 강제 로그아웃 | ✅ | 봇 정지 포함 |
| 봇 모니터링 | ✅ | 전체 봇 상태 조회 |
| 시스템 로그 | ✅ | 로그 조회/다운로드 |
| 분석 대시보드 | ✅ | 시스템 통계 |

### ⚠️ 관리자 페이지 보안 주의사항

1. **IP 화이트리스트 필수 설정**
   - `ADMIN_IP_WHITELIST` 환경변수 설정
   - 프로덕션에서만 활성화됨 (개발 환경에서는 비활성화)

2. **관리자 계정 보안**
   - 기본 `admin@admin.com` / `admin123` 비밀번호 **반드시 변경**
   - 2FA 활성화 권장

---

## 🔧 배포 전 필수 작업

### 1단계: 환경 설정

```bash
# .env 파일 생성 (프로덕션용)
cp .env.example .env.production

# 필수 환경변수 설정
nano .env.production
```

### 2단계: 암호화 키 생성

```python
# Python에서 ENCRYPTION_KEY 생성
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### 3단계: 데이터베이스 마이그레이션

```bash
# 테이블 생성 (서버 시작 시 자동)
# 또는 Alembic 사용 시:
alembic upgrade head
```

### 4단계: SSL 인증서 발급

```bash
# Let's Encrypt 인증서 발급
certbot certonly --webroot -w /var/www/certbot \
  -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com
```

### 5단계: nginx.conf 수정

```nginx
# nginx/nginx.conf에서 도메인 변경
server_name yourdomain.com www.yourdomain.com api.yourdomain.com;

# CORS 헤더도 수정
add_header Access-Control-Allow-Origin "https://yourdomain.com";
```

### 6단계: Docker 빌드 및 배포

```bash
# 이미지 빌드
docker-compose build

# 서비스 시작
docker-compose --profile production up -d

# 로그 확인
docker-compose logs -f backend
```

---

## 📝 남은 개발 작업 (Optional)

### 🟡 권장 개선 사항

| 작업 | 설명 | 예상 시간 |
|------|------|----------|
| Redis 토큰 블랙리스트 | JWT 즉시 무효화 기능 | 2-3시간 |
| 이메일 알림 | 회원가입/비밀번호 초기화 알림 | 4-6시간 |
| 로그 집계 | ELK Stack 또는 CloudWatch 연동 | 4-8시간 |
| 사용자별 봇 핸들러 | 멀티유저 텔레그램 봇 지원 | 3-4시간 |

### 🟢 향후 개선 사항

| 작업 | 설명 |
|------|------|
| 다크 모드 테마 전환 | 사용자 토글 기능 |
| PWA 지원 | 모바일 앱처럼 설치 가능 |
| 푸시 알림 | 브라우저 푸시 알림 |
| 다중 거래소 지원 | Binance, OKX 추가 |

---

## 🚢 배포 절차

### 체크리스트

```markdown
배포 전:
- [ ] .env.production 파일 생성 및 모든 환경변수 설정
- [ ] JWT_SECRET 변경 (32자 이상)
- [ ] ENCRYPTION_KEY 새로 생성
- [ ] 데이터베이스 비밀번호 변경
- [ ] 관리자 기본 비밀번호 변경
- [ ] ADMIN_IP_WHITELIST 설정
- [ ] CORS_ORIGINS 도메인 설정
- [ ] SSL 인증서 설치
- [ ] nginx.conf 도메인 수정

배포:
- [ ] docker-compose build
- [ ] docker-compose up -d
- [ ] /health 엔드포인트 확인
- [ ] 로그인 테스트
- [ ] 관리자 페이지 접근 테스트

배포 후:
- [ ] 기본 관리자 비밀번호 변경
- [ ] 2FA 활성화
- [ ] 모니터링 대시보드 설정
```

---

## 📊 배포 후 모니터링

### 헬스 체크 엔드포인트

```bash
# 서버 상태 확인
curl https://api.yourdomain.com/health

# 예상 응답
{
  "status": "healthy",
  "timestamp": "2025-12-06T14:50:00Z",
  "version": "1.0.0"
}
```

### 모니터링 항목

| 항목 | 설명 | 도구 |
|------|------|------|
| 서버 리소스 | CPU, 메모리, 디스크 | Prometheus + Grafana |
| API 응답 시간 | 엔드포인트별 레이턴시 | Prometheus |
| 에러율 | 5xx 에러 비율 | Sentry |
| 봇 상태 | 활성 봇 수, 에러 | 관리자 대시보드 |
| DB 커넥션 | 커넥션 풀 사용량 | PostgreSQL |

### 알림 설정 권장

- API 응답시간 > 1초
- 5xx 에러율 > 1%
- CPU > 80%
- 디스크 > 90%
- 봇 크래시

---

## ✅ 최종 결론

### 현재 상태: **배포 준비 완료 (환경 설정 필요)**

프로젝트는 기능적으로 완성되어 있으며, **환경 변수 설정과 보안 조치**만 완료하면 바로 배포할 수 있습니다.

### 핵심 조치 사항 (배포 전 필수)

1. ✏️ **JWT_SECRET** 변경
2. ✏️ **ENCRYPTION_KEY** 생성 및 설정
3. ✏️ **DATABASE_URL** 프로덕션 DB로 변경
4. ✏️ **ADMIN_IP_WHITELIST** 설정
5. ✏️ **SSL 인증서** 설치
6. ✏️ **기본 관리자 비밀번호** 변경

---

> 📌 이 문서는 배포 시점에 업데이트되어야 합니다.
>
> 문의: 개발팀
