# 🚀 배포 전 점검 체크리스트

> 최종 점검일: 2025-12-05

## 📋 목차

1. [긴급 필수 작업](#-긴급-필수-작업)
2. [보안 점검](#-보안-점검)
3. [환경 설정](#️-환경-설정)
4. [코드 품질](#-코드-품질)
5. [프로덕션 빌드](#️-프로덕션-빌드)
6. [인프라 및 배포](#-인프라-및-배포)
7. [테스트](#-테스트)
8. [권장 개선사항](#-권장-개선사항)

---

## 🔴 긴급 필수 작업

### 1. 환경 변수 설정 필수

```bash
# 반드시 변경해야 할 환경 변수들
POSTGRES_PASSWORD=강력한-비밀번호-32자-이상
REDIS_PASSWORD=강력한-비밀번호-32자-이상
JWT_SECRET=최소-64자-랜덤-문자열
ENCRYPTION_KEY=Fernet-키-python으로-생성
```

**JWT_SECRET 생성:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

**ENCRYPTION_KEY 생성:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. 기본값 비밀번호 변경

| 파일 | 위치 | 현재 값 | 상태 |
|------|------|---------|------|
| `docker-compose.yml` | Line 11 | `change-this-password` | ⚠️ 변경 필요 |
| `docker-compose.yml` | Line 30 | `change-this-redis-password` | ⚠️ 변경 필요 |
| `docker-compose.yml` | Line 56 | `your-super-secret-jwt-key-change-this` | ⚠️ 변경 필요 |
| `config.py` | Line 99 | `jwt_secret: "change_me"` | ⚠️ 변경 필요 |

### 3. 도메인 설정 변경

```nginx
# nginx/nginx.conf - Line 52, 66, 102
server_name yourdomain.com www.yourdomain.com api.yourdomain.com;

# Line 161
add_header Access-Control-Allow-Origin "https://yourdomain.com" always;
```

---

## 🔒 보안 점검

### ✅ 완료된 보안 기능

| 항목 | 상태 | 비고 |
|------|------|------|
| JWT 인증 | ✅ | `jwt_auth.py` |
| 비밀번호 해싱 (bcrypt) | ✅ | `passlib.hash.bcrypt` |
| API 키 암호화 | ✅ | Fernet 암호화 |
| 2FA (TOTP) | ✅ | Google Authenticator 호환 |
| Rate Limiting | ✅ | IP 및 사용자 기반 |
| CORS 설정 | ✅ | 환경변수로 구성 가능 |
| Admin IP 화이트리스트 | ✅ | 프로덕션에서만 활성화 |
| HTTPS 강제 | ✅ | nginx 설정 |
| 보안 헤더 | ✅ | HSTS, X-Frame-Options 등 |
| Non-root 사용자 | ✅ | Docker에서 실행 |

### ⚠️ 추가 권장 보안 작업

#### 1. 관리자 IP 화이트리스트 설정

```python
# backend/src/middleware/admin_ip_whitelist.py
# ADMIN_ALLOWED_IPS 환경변수 설정
ADMIN_ALLOWED_IPS=1.2.3.4,5.6.7.8
```

#### 2. 로그인 실패 제한 강화

```python
# 현재: Rate limit만 적용
# 권장: 계정 잠금 기능 추가 (5회 실패 시 15분 잠금)
```

#### 3. API 키 마스킹 확인

- API 키 조회 시 부분 마스킹 적용됨 ✅
- 단, 복호화 횟수 제한 (시간당 3회) 확인 ✅

#### 4. SQL Injection 방지

- SQLAlchemy ORM 사용으로 기본 방지 ✅
- 사용자 입력 검증 추가 권장

---

## ⚙️ 환경 설정

### 프로덕션 환경변수 체크리스트

```bash
# .env.production 예시

# === 데이터베이스 ===
DATABASE_URL=postgresql+asyncpg://trading_user:강력한비밀번호@postgres:5432/trading_prod
POSTGRES_PASSWORD=강력한비밀번호

# === 보안 ===
JWT_SECRET=매우긴랜덤문자열최소64자이상필수
ENCRYPTION_KEY=Fernet생성키

# === Redis ===
REDIS_PASSWORD=레디스비밀번호

# === 환경 ===
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING

# === CORS ===
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# === 텔레그램 (선택) ===
TELEGRAM_BOT_TOKEN=봇토큰
TELEGRAM_CHAT_ID=채팅ID

# === DeepSeek AI (선택) ===
DEEPSEEK_API_KEY=API키

# === 프론트엔드 ===
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
```

### 프론트엔드 환경변수

```bash
# frontend/.env.production
VITE_API_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com
```

---

## 🧹 코드 품질

### 1. console.log 제거 필요 (48개 발견)

| 파일 | 개수 | 우선순위 |
|------|------|----------|
| `Trading.jsx` | 5 | 높음 |
| `TradingChart.jsx` | 7 | 높음 |
| `Settings.jsx` | 10 | 중간 |
| `WebSocketContext.jsx` | 12 | 낮음 (디버깅용) |
| `Dashboard.jsx` | 1 | 낮음 |
| 기타 | 13 | 낮음 |

**권장 조치:**

```javascript
// vite.config.js에 추가
export default defineConfig({
  esbuild: {
    drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : [],
  },
});
```

### 2. 에러 핸들링 확인

- ✅ 전역 에러 핸들러 등록됨 (`error_handler.py`)
- ✅ API 에러 응답 형식 통일됨
- ⚠️ 프론트엔드 에러 바운더리 권장

### 3. 타입 체크

- 백엔드: Pydantic 모델로 타입 검증 ✅
- 프론트엔드: TypeScript 미사용 (권장)

---

## 🏗️ 프로덕션 빌드

### 백엔드 체크리스트

- [x] Dockerfile 최적화 (multi-stage build)
- [x] non-root 사용자 실행
- [x] Health check 설정
- [x] Uvicorn workers 설정 (4개)
- [ ] Gunicorn + Uvicorn 권장 (고성능)

### 프론트엔드 체크리스트

- [x] Dockerfile 최적화 (multi-stage build)
- [x] non-root 사용자 실행
- [x] Health check 설정
- [x] Vite 프로덕션 빌드 설정
- [ ] `standalone` 출력 모드 확인 필요

**프론트엔드 vite.config.js 확인:**

```javascript
// vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'antd'],
          charts: ['lightweight-charts', 'recharts'],
        },
      },
    },
  },
});
```

---

## 🌐 인프라 및 배포

### SSL/TLS 인증서

```bash
# Let's Encrypt 인증서 발급
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# 인증서 복사
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./nginx/ssl/
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./nginx/ssl/
```

### 배포 명령어

```bash
# 1. 환경변수 파일 생성
cp .env.example .env
# .env 파일 수정

# 2. 백엔드 마이그레이션
docker-compose run --rm backend alembic upgrade head

# 3. 서비스 시작
docker-compose --profile production up -d

# 4. 로그 확인
docker-compose logs -f
```

### 모니터링 권장 사항

- [ ] Prometheus + Grafana 설정 (`docker-compose.monitoring.yml`)
- [ ] 로그 수집 (ELK 스택 또는 Loki)
- [ ] 알림 설정 (Slack, 이메일)
- [ ] 업타임 모니터링 (UptimeRobot 등)

---

## 🧪 테스트

### 배포 전 수동 테스트 체크리스트

#### 인증

- [ ] 회원가입 테스트
- [ ] 로그인 테스트
- [ ] 2FA 설정 및 로그인
- [ ] 비밀번호 변경
- [ ] 로그아웃

#### 트레이딩

- [ ] 차트 시간대 변경 (1분 → 1일)
- [ ] 코인 변경 (BTC → ETH)
- [ ] API 키 저장
- [ ] 봇 시작/중지

#### 백테스트

- [ ] 단일 백테스트 실행
- [ ] 결과 확인

#### 관리자

- [ ] 관리자 로그인
- [ ] 사용자 목록 조회
- [ ] 봇 상태 모니터링

---

## 💡 권장 개선사항

### 높은 우선순위

| 항목 | 설명 | 예상 시간 |
|------|------|-----------|
| console.log 제거 | 프로덕션 빌드 시 자동 제거 설정 | 30분 |
| 에러 바운더리 | React 에러 경계 컴포넌트 추가 | 1시간 |
| 환경변수 검증 | 필수 환경변수 누락 시 시작 실패 | 1시간 |

### 중간 우선순위

| 항목 | 설명 | 예상 시간 |
|------|------|-----------|
| TypeScript 마이그레이션 | 점진적 타입 추가 | 1주 |
| 단위 테스트 추가 | pytest, jest 설정 | 1주 |
| API 문서 업데이트 | OpenAPI 스펙 보완 | 2시간 |

### 낮은 우선순위

| 항목 | 설명 | 예상 시간 |
|------|------|-----------|
| PWA 지원 | 오프라인 지원, 앱 설치 | 1일 |
| 다국어 지원 | i18n 라이브러리 적용 | 3일 |
| 다크모드 | 시스템 테마 감지 | 1일 |

---

## 📝 배포 전 최종 체크리스트

```
□ 1. 환경변수 모두 설정 완료
□ 2. 기본 비밀번호 모두 변경
□ 3. SSL 인증서 설치
□ 4. 도메인 DNS 설정
□ 5. nginx.conf 도메인 수정
□ 6. CORS 설정 확인
□ 7. 데이터베이스 마이그레이션
□ 8. 프론트엔드 빌드 테스트
□ 9. 백엔드 health check 확인
□ 10. 로그 수집 설정
□ 11. 백업 스크립트 설정
□ 12. 모니터링 알림 설정
```

---

## 📞 문의

문제 발생 시 `DEVELOPMENT_GUIDE.md` 및 `ADMIN_COMPLETION_GUIDE.md` 참조

---

## 🔄 진행 중인 작업 (2025-12-06)

### ✅ 완료된 작업

#### 회원가입 기능 구현

- [x] 백엔드: User 모델에 `name`, `phone` 필드 추가
- [x] 백엔드: RegisterRequest 스키마 업데이트 (이름, 전화번호, 비밀번호 확인)
- [x] 프론트엔드: Login 페이지에 로그인/회원가입 탭 UI 추가
- [x] 프론트엔드: 회원가입 폼 구현 (이메일, 이름, 전화번호, 비밀번호)

#### 소셜 로그인 (OAuth) 기능 구현

- [x] 백엔드: User 모델에 `oauth_provider`, `oauth_id`, `profile_image` 필드 추가
- [x] 백엔드: Google OAuth 2.0 엔드포인트 구현 (`/auth/google/login`, `/auth/google/callback`)
- [x] 백엔드: Kakao OAuth 엔드포인트 구현 (`/auth/kakao/login`, `/auth/kakao/callback`)
- [x] 프론트엔드: Google/Kakao 로그인 버튼 추가
- [x] 프론트엔드: OAuth 콜백 페이지 구현 (`/oauth/callback`)
- [x] DB 마이그레이션 파일 생성

### ⏳ 예정된 작업 (OAuth 자격 증명)

#### Google OAuth 설정 (미완료)

- [ ] Google Cloud Console에서 OAuth 클라이언트 생성
- [ ] 환경변수 설정: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- [ ] 리다이렉트 URI 등록: `http://localhost:8000/auth/google/callback`

#### Kakao OAuth 설정 (미완료)

- [ ] Kakao Developers에서 애플리케이션 생성
- [ ] 환경변수 설정: `KAKAO_CLIENT_ID`
- [ ] 카카오 로그인 활성화 및 Redirect URI 등록

> 📖 상세 설정 가이드: `OAUTH_SETUP_GUIDE.md` 참조

### 📋 DB 마이그레이션 필요

```bash
cd backend
alembic upgrade head
```

---
