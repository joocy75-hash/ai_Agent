# 🔧 환경 변수 설정 가이드

**프로젝트**: Auto Dashboard - Backend
**최종 업데이트**: 2025년 12월 2일

---

## 📋 목차

1. [필수 환경 변수](#필수-환경-변수)
2. [선택적 환경 변수](#선택적-환경-변수)
3. [설정 예시](#설정-예시)
4. [보안 주의사항](#보안-주의사항)

---

## 필수 환경 변수

### 1. 데이터베이스 설정

#### `DATABASE_URL`
**설명**: 데이터베이스 연결 URL

**형식**:
- SQLite (개발): `sqlite+aiosqlite:///./trading.db`
- PostgreSQL (프로덕션): `postgresql+asyncpg://user:password@localhost:5432/dbname`

**예시**:
```bash
# 개발 환경 (SQLite)
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"

# 프로덕션 (PostgreSQL)
export DATABASE_URL="postgresql+asyncpg://trader:secretpass@localhost:5432/trading"
```

**기본값**: `postgresql+asyncpg://user:password@localhost:5432/lbank`

**주의**:
- `asyncpg`와 `psycopg2`를 혼동하지 마세요
- Alembic은 자동으로 `asyncpg` → `psycopg2`로 변환합니다

---

### 2. 보안 설정

#### `JWT_SECRET`
**설명**: JWT 토큰 서명에 사용되는 비밀 키

**요구사항**:
- 최소 32자 이상의 무작위 문자열
- 절대 Git에 커밋하지 마세요!

**생성 방법**:
```bash
# Python으로 생성
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL로 생성
openssl rand -base64 32
```

**예시**:
```bash
export JWT_SECRET="your-super-secret-jwt-key-min-32-chars"
```

**기본값**: `change_me` ⚠️ (프로덕션에서는 반드시 변경)

---

#### `ENCRYPTION_KEY`
**설명**: API 키 암호화에 사용되는 Fernet 키

**요구사항**:
- Fernet 형식의 키 (Base64 인코딩된 32바이트)
- 절대 Git에 커밋하지 마세요!

**생성 방법**:
```bash
# Python Cryptography 라이브러리로 생성
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**예시**:
```bash
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
```

**주의**:
- 키를 잃어버리면 기존 암호화된 API 키를 복호화할 수 없습니다
- 백업 필수!

---

### 3. 거래소 API 키 (선택적)

#### `LBANK_API_KEY`
**설명**: LBank 거래소 API 키

**예시**:
```bash
export LBANK_API_KEY="34e50e3f-b2ea-480d-9a95-6b6161678fae"
```

**주의**: 사용자가 개별적으로 API 키를 저장하는 경우 불필요

---

#### `LBANK_SECRET_KEY`
**설명**: LBank 거래소 Secret Key

**예시**:
```bash
export LBANK_SECRET_KEY="6A9CB2B7FC7EF0B21DDFF7BB88EC0FEF"
```

---

### 4. AI 설정 (선택적)

#### `DEEPSEEK_API_KEY`
**설명**: DeepSeek AI API 키 (AI 전략 생성용)

**예시**:
```bash
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxx"
```

**기능**: `/ai_strategy/generate` 엔드포인트에서 사용

---

## 선택적 환경 변수

### 1. 서버 설정

#### `HOST`
**설명**: 서버 바인딩 호스트

**기본값**: `0.0.0.0`

**예시**:
```bash
export HOST="127.0.0.1"  # 로컬 전용
export HOST="0.0.0.0"    # 모든 인터페이스
```

---

#### `PORT`
**설명**: 서버 포트 번호

**기본값**: `8000`

**예시**:
```bash
export PORT="8080"
```

---

#### `DEBUG`
**설명**: 디버그 모드 활성화 여부

**기본값**: `false`

**허용값**: `true`, `false`

**예시**:
```bash
export DEBUG="true"   # 개발 환경
export DEBUG="false"  # 프로덕션 환경
```

**효과**:
- `true`: 상세한 에러 메시지, 자동 리로드
- `false`: 최소한의 에러 메시지, 성능 최적화

---

### 2. CORS 설정

#### `CORS_ORIGINS`
**설명**: CORS 허용 도메인 목록 (쉼표로 구분)

**기본값**: (없음)

**예시**:
```bash
export CORS_ORIGINS="https://example.com,https://app.example.com,https://admin.example.com"
```

**기본 허용 도메인** (코드에 하드코딩):
- `http://localhost:3000`
- `http://localhost:5173`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

---

## 설정 예시

### 개발 환경 (.env.development)

```bash
# 데이터베이스
DATABASE_URL="sqlite+aiosqlite:///./trading.db"

# 보안
JWT_SECRET="dev-jwt-secret-change-in-production"
ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="

# 서버
HOST="0.0.0.0"
PORT="8000"
DEBUG="true"

# 거래소 API (선택)
LBANK_API_KEY=""
LBANK_SECRET_KEY=""

# AI (선택)
DEEPSEEK_API_KEY=""

# CORS
CORS_ORIGINS=""
```

---

### 프로덕션 환경 (.env.production)

```bash
# 데이터베이스
DATABASE_URL="postgresql+asyncpg://trader:STRONG_PASSWORD@db.example.com:5432/trading_prod"

# 보안 (반드시 변경!)
JWT_SECRET="$(openssl rand -base64 32)"
ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"

# 서버
HOST="0.0.0.0"
PORT="8000"
DEBUG="false"

# 거래소 API (사용자가 개별 설정하면 불필요)
LBANK_API_KEY=""
LBANK_SECRET_KEY=""

# AI
DEEPSEEK_API_KEY="sk-prod-xxxxxxxxxxxxx"

# CORS (프론트엔드 도메인만 허용)
CORS_ORIGINS="https://trade.example.com,https://admin.example.com"
```

---

## 보안 주의사항

### ⚠️ 절대 하지 말아야 할 것

1. **Git에 환경 변수 파일 커밋**
   ```bash
   # .gitignore에 추가
   .env
   .env.local
   .env.development
   .env.production
   ```

2. **프로덕션에서 기본값 사용**
   - `JWT_SECRET="change_me"` ❌
   - `DEBUG="true"` ❌

3. **API 키를 코드에 하드코딩**
   ```python
   # ❌ 절대 안됨
   api_key = "34e50e3f-b2ea-480d-9a95-6b6161678fae"

   # ✅ 환경 변수 사용
   api_key = os.getenv("LBANK_API_KEY")
   ```

---

### ✅ 권장 사항

1. **환경별로 .env 파일 분리**
   ```
   .env.development
   .env.staging
   .env.production
   ```

2. **환경 변수 검증**
   ```python
   if settings.jwt_secret == "change_me":
       raise ValueError("JWT_SECRET must be changed in production!")
   ```

3. **보안 키 백업**
   - `ENCRYPTION_KEY`를 분실하면 암호화된 데이터를 복구할 수 없습니다
   - 안전한 장소에 백업 보관 (Vault, 1Password 등)

4. **최소 권한 원칙**
   - 데이터베이스 사용자에게 필요한 권한만 부여
   - API 키는 읽기 전용 권한만 부여 (가능한 경우)

---

## 환경 변수 로드 방법

### 1. Shell에서 직접 export
```bash
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export JWT_SECRET="your-secret-key"
```

### 2. .env 파일 사용 (python-dotenv)
```bash
# backend/.env 파일 생성
DATABASE_URL="sqlite+aiosqlite:///./trading.db"
JWT_SECRET="your-secret-key"
```

```python
# Python 코드에서 로드
from dotenv import load_dotenv
load_dotenv()
```

### 3. Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    env_file:
      - .env.production
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
```

### 4. Systemd 서비스
```ini
# /etc/systemd/system/trading-backend.service
[Service]
Environment="DATABASE_URL=sqlite+aiosqlite:///./trading.db"
Environment="JWT_SECRET=your-secret-key"
```

---

## 트러블슈팅

### 문제: "JWT_SECRET not found"
**해결**:
```bash
export JWT_SECRET="your-secret-key"
# 또는 .env 파일에 추가
```

### 문제: "Invalid ENCRYPTION_KEY"
**해결**:
```bash
# 새 키 생성
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 환경 변수 설정
export ENCRYPTION_KEY="생성된_키"
```

### 문제: "Database connection failed"
**해결**:
1. `DATABASE_URL` 형식 확인
2. 데이터베이스 서버 실행 확인
3. 사용자명/비밀번호 확인
4. 방화벽 설정 확인

---

## 참고 자료

- [FastAPI 환경 변수](https://fastapi.tiangolo.com/advanced/settings/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [12 Factor App - Config](https://12factor.net/config)
- [Python Cryptography](https://cryptography.io/en/latest/)
