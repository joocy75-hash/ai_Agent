# 🚀 Auto Dashboard - Backend

**암호화폐 자동 거래 시스템** 백엔드 API 서버

FastAPI 기반의 고성능 비동기 API 서버로, JWT 인증, 백테스트, AI 전략 생성 등의 기능을 제공합니다.

---

## 📋 목차

1. [주요 기능](#주요-기능)
2. [기술 스택](#기술-스택)
3. [시작하기](#시작하기)
4. [API 문서](#api-문서)
5. [프로젝트 구조](#프로젝트-구조)
6. [환경 설정](#환경-설정)
7. [개발 가이드](#개발-가이드)

---

## 주요 기능

### 🔐 인증 및 보안
- **JWT 기반 인증**: 안전한 토큰 기반 인증 시스템
- **RBAC (역할 기반 접근 제어)**: Admin/User 권한 분리
- **API 키 암호화**: Fernet을 사용한 거래소 API 키 안전 보관
- **Rate Limiting**: IP 및 사용자별 요청 제한
- **CORS 설정**: 안전한 크로스 오리진 리소스 공유

### 📊 거래 기능
- **실시간 잔고 조회**: 거래소 계정 잔고 및 포지션 확인
- **주문 관리**: 거래 내역 조회 및 관리 (페이지네이션 지원)
- **자동 거래 봇**: 전략 기반 자동 거래 실행
- **다중 거래소 지원**: Bitget, Binance, OKX (확장 가능)

### 🤖 전략 및 백테스트
- **백테스트 엔진**: 과거 데이터로 전략 성능 검증
  - 비동기 CSV 파일 로드 (대용량 파일 지원)
  - 슬리피지 및 수수료 고려
  - 상세한 성과 지표 (Sharpe Ratio, Max Drawdown 등)
- **AI 전략 생성**: DeepSeek API를 활용한 전략 자동 생성
- **전략 관리**: 사용자별 전략 저장 및 관리

### 📈 데이터 및 차트
- **실시간 시장 데이터**: WebSocket을 통한 실시간 데이터 수신
- **차트 데이터**: OHLCV 캔들 데이터 제공
- **거래 기록**: 모든 거래 내역 저장 및 조회

### 🔍 모니터링
- **Health Check**: 시스템 상태 확인 (`/health`)
- **Database Check**: DB 연결 상태 확인 (`/health/db`)
- **Readiness/Liveness**: Kubernetes 준비 상태 확인
- **관리자 대시보드**: 시스템 진단 및 사용자 관리

---

## 기술 스택

### 핵심 프레임워크
- **[FastAPI](https://fastapi.tiangolo.com/)** 0.100+: 고성능 비동기 웹 프레임워크
- **[SQLAlchemy](https://www.sqlalchemy.org/) 2.0**: ORM 및 비동기 데이터베이스
- **[Pydantic](https://docs.pydantic.dev/)**: 데이터 검증 및 설정 관리

### 데이터베이스
- **SQLite** (개발): 로컬 개발용
- **PostgreSQL** (프로덕션): 프로덕션 환경 권장

### 인증 및 보안
- **PyJWT**: JWT 토큰 생성 및 검증
- **Passlib + Bcrypt**: 비밀번호 해싱
- **Cryptography (Fernet)**: API 키 암호화

### 비동기 I/O
- **aiofiles**: 비동기 파일 처리
- **asyncpg**: PostgreSQL 비동기 드라이버
- **aiosqlite**: SQLite 비동기 드라이버

### 데이터 처리
- **Pandas**: 백테스트 데이터 분석
- **TA-Lib**: 기술적 지표 계산

### 거래소 연동
- **CCXT**: 다중 거래소 통합 라이브러리
- **WebSocket**: 실시간 시장 데이터 수신

---

## 시작하기

### 1. 요구사항

- **Python 3.11** 이상
- **pip** (Python 패키지 관리자)
- **PostgreSQL** (프로덕션) 또는 **SQLite** (개발)

### 2. 설치

```bash
# 1. 저장소 클론
cd auto-dashboard/backend

# 2. 가상 환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# 필수 환경 변수 설정
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export JWT_SECRET="your-super-secret-key-change-in-production"
export ENCRYPTION_KEY="$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

**상세 가이드**: [ENV_SETUP.md](./ENV_SETUP.md) 참조

### 4. 데이터베이스 마이그레이션

```bash
# Alembic 마이그레이션 실행
alembic upgrade head
```

### 5. 서버 실행

```bash
# 개발 서버 실행 (자동 리로드)
python -m src.main

# 또는 uvicorn 직접 실행
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

서버가 실행되면 다음 주소에서 확인 가능:
- API 서버: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## API 문서

### Swagger UI
자동 생성된 대화형 API 문서: **http://localhost:8000/docs**

![Swagger UI](https://fastapi.tiangolo.com/img/index/index-01-swagger-ui-simple.png)

### ReDoc
깔끔한 API 문서: **http://localhost:8000/redoc**

### 주요 엔드포인트

#### 인증
- `POST /auth/register` - 회원가입
- `POST /auth/login` - 로그인 (JWT 발급)

#### 계정
- `GET /account/balance` - 잔고 조회
- `GET /account/positions` - 포지션 조회
- `POST /account/save_keys` - API 키 저장

#### 거래
- `GET /order/history` - 거래 내역 (페이지네이션)
- `POST /order/submit` - 주문 제출

#### 백테스트
- `POST /backtest/start` - 백테스트 시작
- `GET /backtest/result/{id}` - 결과 조회
- `GET /backtest/history` - 백테스트 목록

#### AI 전략
- `POST /ai_strategy/generate` - AI 전략 생성

#### 모니터링
- `GET /health` - 기본 헬스 체크
- `GET /health/db` - 데이터베이스 상태
- `GET /health/ready` - Readiness Probe
- `GET /health/live` - Liveness Probe

---

## 프로젝트 구조

```
backend/
├── src/
│   ├── api/                    # API 엔드포인트
│   │   ├── auth.py            # 인증 (회원가입, 로그인)
│   │   ├── account.py         # 계정 (잔고, API 키)
│   │   ├── order.py           # 주문 및 거래 내역
│   │   ├── backtest.py        # 백테스트 실행
│   │   ├── ai_strategy.py     # AI 전략 생성
│   │   ├── health.py          # 헬스 체크
│   │   └── admin_*.py         # 관리자 전용 API
│   │
│   ├── services/              # 비즈니스 로직
│   │   ├── exchange_service.py       # 거래소 클라이언트 관리
│   │   ├── backtest_engine.py        # 백테스트 엔진
│   │   ├── exchanges/                # 거래소 연동
│   │   └── strategies/               # 트레이딩 전략
│   │
│   ├── database/              # 데이터베이스
│   │   ├── models.py          # SQLAlchemy 모델
│   │   ├── db.py              # DB 연결 관리
│   │   └── session.py         # 세션 관리
│   │
│   ├── schemas/               # Pydantic 스키마 (검증)
│   ├── utils/                 # 유틸리티 함수
│   │   ├── jwt_auth.py        # JWT 인증
│   │   ├── crypto_secrets.py  # 암호화/복호화
│   │   └── validators.py      # 입력 검증
│   │
│   ├── middleware/            # 미들웨어
│   │   ├── rate_limit_improved.py  # Rate Limiting
│   │   └── error_handler.py        # 전역 에러 핸들러
│   │
│   ├── config.py              # 설정 (환경 변수)
│   └── main.py                # 애플리케이션 진입점
│
├── alembic/                   # 데이터베이스 마이그레이션
│   └── versions/              # 마이그레이션 파일
│
├── tests/                     # 테스트 코드
├── requirements.txt           # Python 의존성
├── alembic.ini                # Alembic 설정
├── .env.example               # 환경 변수 예시
├── ENV_SETUP.md              # 환경 설정 가이드
└── README.md                  # 이 파일
```

---

## 환경 설정

### 주요 환경 변수

| 변수명 | 설명 | 기본값 | 필수 |
|--------|------|--------|------|
| `DATABASE_URL` | 데이터베이스 연결 URL | `sqlite+aiosqlite:///./trading.db` | ✅ |
| `JWT_SECRET` | JWT 서명 키 | `change_me` | ✅ |
| `ENCRYPTION_KEY` | API 키 암호화 키 | - | ✅ |
| `DEBUG` | 디버그 모드 | `false` | ❌ |
| `HOST` | 서버 호스트 | `0.0.0.0` | ❌ |
| `PORT` | 서버 포트 | `8000` | ❌ |
| `CORS_ORIGINS` | 허용 도메인 (쉼표 구분) | - | ❌ |
| `DEEPSEEK_API_KEY` | AI API 키 | - | ❌ |

**상세 가이드**: [ENV_SETUP.md](./ENV_SETUP.md)

---

## 개발 가이드

### 코드 스타일
- **PEP 8** 준수
- **Type Hints** 적극 활용
- **Docstrings** 작성 (함수 설명)

### 새로운 API 추가

1. **모델 정의** (`src/database/models.py`)
2. **스키마 정의** (`src/schemas/*.py`)
3. **비즈니스 로직** (`src/services/*.py`)
4. **API 엔드포인트** (`src/api/*.py`)
5. **마이그레이션** (`alembic revision -m "설명"`)

### 데이터베이스 마이그레이션

```bash
# 1. 모델 변경 후 마이그레이션 생성
alembic revision -m "add_new_field"

# 2. alembic/versions/xxx_add_new_field.py 수정

# 3. 마이그레이션 적용
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
alembic upgrade head

# 4. 롤백 (필요시)
alembic downgrade -1
```

### 테스트

```bash
# 테스트 실행
pytest

# 커버리지 확인
pytest --cov=src tests/
```

---

## 성능 최적화

이 프로젝트는 다음과 같은 성능 최적화가 적용되어 있습니다:

### ✅ 데이터베이스 최적화
- **인덱스 10개 추가**: 거래 내역 조회 10배 속도 향상
- **페이지네이션**: 메모리 사용량 90% 감소
- **복합 인덱스**: `user_id + created_at` 등

### ✅ 비동기 I/O
- **aiofiles**: 백테스트 CSV 파일 비동기 로드
- **asyncpg**: PostgreSQL 비동기 드라이버
- **비동기 엔드포인트**: 모든 API 비동기 처리

### ✅ 코드 품질
- **서비스 레이어 패턴**: 비즈니스 로직 분리
- **설정 중앙화**: 5개 설정 클래스
- **Magic Numbers 제거**: 모든 상수 설정화

---

## 보안

### 구현된 보안 기능

- ✅ **RBAC (역할 기반 접근 제어)**: Admin/User 권한 분리
- ✅ **JWT 인증**: 안전한 토큰 기반 인증
- ✅ **API 키 암호화**: Fernet 암호화 (AES-128)
- ✅ **Rate Limiting**: DoS 공격 방지
- ✅ **입력 검증**: XSS, SQL Injection 방지
- ✅ **Path Traversal 방지**: 파일 경로 검증
- ✅ **CORS 제한**: 허용된 도메인만 접근

### 보안 체크리스트

프로덕션 배포 전 확인사항:

- [ ] `JWT_SECRET` 변경 (32자 이상)
- [ ] `ENCRYPTION_KEY` 생성 및 백업
- [ ] `DEBUG=false` 설정
- [ ] CORS 도메인 제한 (`CORS_ORIGINS`)
- [ ] HTTPS 사용
- [ ] 데이터베이스 접근 제한 (방화벽)
- [ ] 로그 모니터링 설정

---

## 문제 해결

### 문제: "Database connection failed"
**원인**: DATABASE_URL 설정 오류

**해결**:
```bash
# SQLite 사용 시
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"

# PostgreSQL 사용 시
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/dbname"
```

### 문제: "JWT decode error"
**원인**: JWT_SECRET 미설정 또는 변경됨

**해결**:
```bash
export JWT_SECRET="your-consistent-secret-key"
```

### 문제: "Invalid ENCRYPTION_KEY"
**원인**: Fernet 키 형식 오류

**해결**:
```bash
# 새 키 생성
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
export ENCRYPTION_KEY="생성된_키"
```

---

## 참고 자료

- **작업 이력**: [WORK_LOG.md](../WORK_LOG.md)
- **환경 설정**: [ENV_SETUP.md](./ENV_SETUP.md)
- **개선 가이드**: [BACKEND_IMPROVEMENT_GUIDE.md](../BACKEND_IMPROVEMENT_GUIDE.md)

### 외부 문서
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 문서](https://docs.sqlalchemy.org/en/20/)
- [Alembic 문서](https://alembic.sqlalchemy.org/)
- [Pydantic 문서](https://docs.pydantic.dev/)

---

## 라이선스

MIT License

---

## 기여

버그 리포트 및 기능 제안은 GitHub Issues에 올려주세요.

---

**개발**: Auto Dashboard Team
**최종 업데이트**: 2025년 12월 2일
