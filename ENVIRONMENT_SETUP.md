# 🔐 환경변수 설정 가이드

> **작성일**: 2025-12-05  
> **목적**: 프로덕션 배포 전 필수 환경변수 설정 가이드

---

## 📋 필수 환경변수 목록

### 🔴 Critical (반드시 변경)

| 변수명 | 기본값 | 프로덕션 값 | 설명 |
|--------|-------|-------------|------|
| `JWT_SECRET` | `change_me` | **반드시 변경** | JWT 토큰 서명용 비밀키 |
| `DATABASE_URL` | `postgresql+asyncpg://user:password@localhost:5432/trading` | 실제 DB 연결 문자열 | 데이터베이스 연결 |
| `ENCRYPTION_KEY` | 없음 | 생성 필요 | API 키 암호화용 |

### 🟠 High (강력 권장)

| 변수명 | 기본값 | 프로덕션 값 | 설명 |
|--------|-------|-------------|------|
| `CORS_ORIGINS` | `` (빈 문자열) | `https://your-domain.com` | 허용할 도메인 목록 |
| `ADMIN_IP_WHITELIST` | `` (빈 문자열) | `123.45.67.89,111.222.333.444` | 관리자 IP 제한 |
| `ENVIRONMENT` | `development` | `production` | 환경 구분 |

### 🟡 Medium (권장)

| 변수명 | 기본값 | 설명 |
|--------|-------|------|
| `DEBUG` | `true` | 프로덕션에서는 `false` |
| `DEEPSEEK_API_KEY` | `` | AI 전략 생성용 |
| `BACKTEST_DATA_MODE` | `offline` | 백테스트 데이터 모드 |

---

## 🔧 환경변수 생성 방법

### 1. JWT_SECRET 생성

```bash
# 방법 1: OpenSSL 사용
openssl rand -hex 32

# 방법 2: Python 사용
python3 -c "import secrets; print(secrets.token_hex(32))"

# 예시 출력: a3f5c8d9e2b1f4a7c6d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h0
```

### 2. ENCRYPTION_KEY 생성

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 예시 출력: YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=
```

### 3. DATABASE_URL 형식

```bash
# PostgreSQL (프로덕션)
DATABASE_URL=postgresql+asyncpg://<username>:<password>@<host>:<port>/<database>

# SQLite (개발용)
DATABASE_URL=sqlite+aiosqlite:///./trading.db
```

---

## 📁 환경변수 설정 파일

### 개발 환경 (.env)

```bash
# backend 디렉토리에서
cat > .env << 'EOF'
# 보안 설정
JWT_SECRET=dev_secret_key_only_for_local_development
ENCRYPTION_KEY=YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=

# 데이터베이스
DATABASE_URL=sqlite+aiosqlite:///./trading.db

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:5174

# 환경
ENVIRONMENT=development
DEBUG=true

# 관리자 IP (개발용 - 비어있으면 모든 IP 허용)
ADMIN_IP_WHITELIST=

# 백테스트
BACKTEST_DATA_MODE=offline
EOF
```

### 프로덕션 환경 (.env.production)

```bash
# 프로덕션 환경 예시
JWT_SECRET=<위에서 생성한 64자 hex 문자열>
ENCRYPTION_KEY=<Fernet 키>
DATABASE_URL=postgresql+asyncpg://trading_user:strong_password@localhost:5432/trading_db
CORS_ORIGINS=https://trading.yourdomain.com,https://admin.yourdomain.com
ADMIN_IP_WHITELIST=123.45.67.89,111.222.333.444
ENVIRONMENT=production
DEBUG=false
BACKTEST_DATA_MODE=offline
```

---

## 🐳 Docker Compose 환경변수

`docker-compose.yml` 또는 `docker-compose.override.yml`에서 설정:

```yaml
services:
  backend:
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - DATABASE_URL=${DATABASE_URL}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
      - ADMIN_IP_WHITELIST=${ADMIN_IP_WHITELIST}
      - ENVIRONMENT=production
      - DEBUG=false
```

---

## ✅ 환경변수 체크리스트

배포 전 아래 항목을 확인하세요:

- [ ] `JWT_SECRET` - 64자 이상의 랜덤 문자열로 변경
- [ ] `DATABASE_URL` - 프로덕션 DB 연결 문자열 설정
- [ ] `ENCRYPTION_KEY` - Fernet 키 생성 및 설정
- [ ] `CORS_ORIGINS` - 프로덕션 도메인만 허용
- [ ] `ADMIN_IP_WHITELIST` - 관리자 IP만 허용
- [ ] `ENVIRONMENT=production` 설정
- [ ] `DEBUG=false` 설정

---

## ⚠️ 보안 주의사항

1. **`.env` 파일은 절대 Git에 커밋하지 마세요** (이미 `.gitignore`에 포함)
2. **프로덕션 비밀키는 안전한 곳에 백업하세요**
3. **환경변수 변경 시 서비스를 재시작해야 합니다**
4. **정기적으로 비밀키를 교체하세요** (3-6개월 권장)
