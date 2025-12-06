# 🔒 백엔드 개선 가이드

**프로젝트**: Auto Dashboard - 암호화폐 자동 거래 시스템
**작성일**: 2025년 12월 1일
**분석 범위**: Backend 전체 코드베이스

---

## 📋 목차

1. [개요](#개요)
2. [보안 이슈 (Critical)](#1-보안-이슈-critical)
3. [코드 품질 개선](#2-코드-품질-개선)
4. [성능 최적화](#3-성능-최적화)
5. [아키텍처 개선](#4-아키텍처-개선)
6. [실행 계획](#5-실행-계획)

---

## 개요

### 분석 결과 요약

총 **47개의 개선 사항**을 발견했습니다:

| 심각도 | 개수 | 카테고리 |
|--------|------|----------|
| 🔴 Critical | 7 | 보안 (즉시 수정 필요) |
| 🟠 High | 9 | 보안/성능 (1주 내 수정) |
| 🟡 Medium | 16 | 코드 품질/아키텍처 |
| 🟢 Low | 15 | 모범 사례 |

### 가장 심각한 문제 Top 5

1. **관리자 권한 검증 없음** - 모든 사용자가 관리자 엔드포인트 접근 가능
2. **WebSocket 인증 우회** - 누구나 다른 사용자의 WebSocket 구독 가능
3. **API 키 복호화 노출** - 관리자 엔드포인트에서 평문 API 키 반환
4. **Path Traversal 취약점** - CSV 경로 검증 없음 (시스템 파일 읽기 가능)
5. **CORS 설정 위험** - `allow_origins=["*"]` + `allow_credentials=True`

---

## 1. 보안 이슈 (Critical)

### 🔴 Issue #1: 관리자 역할 기반 접근 제어(RBAC) 없음

**파일**: `backend/src/api/admin_*.py` (모든 관리자 엔드포인트)
**심각도**: **CRITICAL**

#### 문제점

현재 JWT 인증만 있고 역할 검증이 없어, **일반 사용자도 관리자 기능 사용 가능**:

```python
@router.get("")
async def get_users(
    session: AsyncSession = Depends(get_session),
    current_user_id: int = Depends(get_current_user_id),  # ❌ 역할 검증 없음!
):
    """관리자 전용: 모든 회원 목록 조회"""
    result = await session.execute(select(User))
```

#### 영향

- 모든 사용자의 API 키 조회/삭제 가능
- 시스템 진단 정보 접근 가능
- 완전한 권한 상승(Privilege Escalation)

#### 해결 방안

**1단계: User 모델에 role 필드 추가**

```python
# backend/src/database/models.py
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # ✅ 추가
    exchange = Column(String, default="bitget", nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**2단계: Alembic 마이그레이션 생성**

```bash
cd backend
alembic revision -m "add_user_role"
```

```python
# alembic/versions/xxx_add_user_role.py
def upgrade():
    op.add_column('users', sa.Column('role', sa.String(), nullable=True))
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
    op.alter_column('users', 'role', nullable=False)

def downgrade():
    op.drop_column('users', 'role')
```

**3단계: 관리자 검증 Dependency 생성**

```python
# backend/src/utils/auth_dependencies.py
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import User
from .jwt_auth import get_current_user_id

async def require_admin(
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
) -> int:
    """관리자 권한 필수 (Dependency)"""
    result = await session.execute(select(User).where(User.id == current_user_id))
    user = result.scalars().first()

    if not user or user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user_id
```

**4단계: 관리자 엔드포인트에 적용**

```python
# backend/src/api/admin_users.py
@router.get("")
async def get_users(
    session: AsyncSession = Depends(get_session),
    admin_id: int = Depends(require_admin),  # ✅ 수정
):
    """관리자 전용: 모든 회원 목록 조회"""
    result = await session.execute(select(User))
    return result.scalars().all()
```

**5단계: 첫 관리자 계정 생성 스크립트**

```python
# backend/create_admin.py
import asyncio
from sqlalchemy import select
from src.database.db import AsyncSessionLocal
from src.database.models import User
from src.utils.jwt_auth import JWTAuth

async def create_admin_user(email: str, password: str):
    """관리자 계정 생성"""
    async with AsyncSessionLocal() as session:
        # 이미 존재하는지 확인
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalars().first()

        if existing:
            print(f"❌ User {email} already exists")
            return

        # 관리자 생성
        admin = User(
            email=email,
            password_hash=JWTAuth.get_password_hash(password),
            role="admin",  # ✅ 관리자 역할
            exchange="bitget"
        )

        session.add(admin)
        await session.commit()
        print(f"✅ Admin user created: {email}")

if __name__ == "__main__":
    asyncio.run(create_admin_user("admin@admin.com", "your-secure-password"))
```

---

### 🔴 Issue #2: WebSocket 인증 없음

**파일**: `backend/src/websockets/ws_server.py`
**심각도**: **CRITICAL**

#### 문제점

```python
@router.websocket("/ws/user/{user_id}")
async def user_socket(websocket: WebSocket, user_id: int):
    await websocket.accept()  # ❌ JWT 검증 없음!
    connections.setdefault(user_id, []).append(websocket)
```

**공격 시나리오**:
- 사용자 A가 사용자 B의 `user_id`로 WebSocket 연결
- 사용자 B의 실시간 거래 신호 모니터링 가능

#### 해결 방안

```python
# backend/src/websockets/ws_server.py
from fastapi import WebSocket, WebSocketDisconnect, Query
from ..utils.jwt_auth import JWTAuth

@router.websocket("/ws/user/{user_id}")
async def user_socket(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...)  # ✅ 쿼리 파라미터로 토큰 받기
):
    # JWT 검증
    try:
        payload = JWTAuth.decode_token(token)
        token_user_id = payload.get("user_id")

        # 토큰의 user_id와 경로의 user_id가 일치하는지 확인
        if token_user_id != user_id:
            await websocket.close(code=1008, reason="Unauthorized: User ID mismatch")
            return

        await websocket.accept()
        connections.setdefault(user_id, []).append(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                # ... 메시지 처리
        except WebSocketDisconnect:
            connections[user_id].remove(websocket)

    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=1008, reason="Unauthorized")
```

**프론트엔드 연결 예시**:
```javascript
const token = localStorage.getItem('access_token');
const ws = new WebSocket(`ws://localhost:8000/ws/user/${userId}?token=${token}`);
```

---

### 🔴 Issue #3: API 키 평문 노출

**파일**: `backend/src/api/admin_users.py:77`, `backend/src/api/account.py:197`
**심각도**: **CRITICAL**

#### 문제점

관리자 엔드포인트와 사용자 엔드포인트에서 **복호화된 API 키를 그대로 반환**:

```python
@router.get("/{user_id}/api-keys")
async def get_user_api_keys(...):
    return {
        "api_key": decrypt_secret(key.encrypted_api_key),  # ❌ 평문 노출!
        "secret_key": decrypt_secret(key.encrypted_secret_key),
        "passphrase": decrypt_secret(key.encrypted_passphrase),
    }
```

**위험**:
- 로그에 API 키 기록 가능
- 네트워크 스니핑 시 노출
- XSS 공격 시 탈취 가능

#### 해결 방안

**1단계: API 키 마스킹 함수 추가**

```python
# backend/src/utils/crypto_secrets.py

def mask_secret(secret: str, show_chars: int = 4) -> str:
    """
    API 키를 마스킹 (예: "bg-abc...xyz")

    Args:
        secret: 원본 키
        show_chars: 앞뒤로 보여줄 글자 수

    Returns:
        마스킹된 문자열
    """
    if not secret or len(secret) <= show_chars * 2:
        return "***"

    return f"{secret[:show_chars]}...{secret[-show_chars:]}"
```

**2단계: 기본적으로 마스킹된 정보만 반환**

```python
# backend/src/api/account.py
@router.get("/my_keys")
async def get_my_keys(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """자신의 API 키 조회 (마스킹)"""
    result = await session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
    key = result.scalars().first()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    return {
        "api_key_masked": mask_secret(decrypt_secret(key.encrypted_api_key)),
        "has_secret_key": bool(key.encrypted_secret_key),
        "has_passphrase": bool(key.encrypted_passphrase),
        "created_at": key.created_at.isoformat() if key.created_at else None,
    }
```

**3단계: 명시적 요청 시에만 복호화 (Rate Limiting 적용)**

```python
# backend/src/api/account.py
from fastapi import BackgroundTasks
import time

# In-memory cache for reveal requests (실제로는 Redis 사용 권장)
_reveal_attempts = {}

@router.post("/reveal_keys")
async def reveal_my_keys(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    API 키 복호화 (Rate Limited: 시간당 3회)

    보안상의 이유로 제한된 횟수만 조회 가능합니다.
    """
    # Rate limiting 체크
    now = time.time()
    hour_ago = now - 3600

    attempts = _reveal_attempts.get(user_id, [])
    recent_attempts = [t for t in attempts if t > hour_ago]

    if len(recent_attempts) >= 3:
        raise HTTPException(
            status_code=429,
            detail="Too many reveal requests. Limit: 3 per hour"
        )

    # 시도 기록
    recent_attempts.append(now)
    _reveal_attempts[user_id] = recent_attempts

    # API 키 조회
    result = await session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
    key = result.scalars().first()

    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    # 감사 로그 (실제로는 DB에 저장)
    logger.warning(
        f"API keys revealed",
        extra={"user_id": user_id, "timestamp": now}
    )

    return {
        "api_key": decrypt_secret(key.encrypted_api_key),
        "secret_key": decrypt_secret(key.encrypted_secret_key),
        "passphrase": decrypt_secret(key.encrypted_passphrase) if key.encrypted_passphrase else "",
        "warning": "이 정보는 안전한 곳에 저장하세요. 다시 조회 제한: 시간당 3회",
    }
```

---

### 🔴 Issue #4: Path Traversal 취약점

**파일**: `backend/src/api/backtest.py:110-117`
**심각도**: **HIGH**

#### 문제점

```python
if not os.path.exists(request.csv_path):  # ❌ 경로 검증 없음!
    raise HTTPException(...)
```

**공격 시나리오**:
```bash
# 공격자가 전송하는 요청
POST /backtest/start
{
  "csv_path": "../../../../etc/passwd"  # 시스템 파일 접근
}

# 또는
{
  "csv_path": "../../.env"  # 환경 변수 파일 읽기
}
```

#### 해결 방안

```python
# backend/src/utils/file_validator.py
from pathlib import Path
from fastapi import HTTPException
import os

# 허용된 데이터 디렉토리
ALLOWED_DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data")).resolve()

def validate_csv_path(csv_path: str) -> Path:
    """
    CSV 파일 경로 검증

    Args:
        csv_path: 사용자가 제공한 경로

    Returns:
        검증된 Path 객체

    Raises:
        HTTPException: 잘못된 경로인 경우
    """
    try:
        # 절대 경로로 변환
        path = Path(csv_path).resolve()

        # 1. 허용된 디렉토리 내부인지 확인
        if not path.is_relative_to(ALLOWED_DATA_DIR):
            raise ValueError("Path must be within allowed data directory")

        # 2. CSV 파일인지 확인
        if path.suffix.lower() != '.csv':
            raise ValueError("File must be a CSV file")

        # 3. 파일이 존재하는지 확인
        if not path.is_file():
            raise ValueError("File does not exist")

        # 4. 읽기 권한 확인
        if not os.access(path, os.R_OK):
            raise ValueError("File is not readable")

        # 5. 심볼릭 링크가 아닌지 확인 (보안)
        if path.is_symlink():
            raise ValueError("Symbolic links are not allowed")

        return path

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV path: {str(e)}"
        )
```

**적용**:

```python
# backend/src/api/backtest.py
from ..utils.file_validator import validate_csv_path

@router.post("/start")
async def start_backtest(request: BacktestRequest, ...):
    # CSV 경로 검증
    validated_path = validate_csv_path(request.csv_path)  # ✅

    # 검증된 경로 사용
    result_id = await create_backtest_result(...)
    background_tasks.add_task(
        _run_backtest_background,
        result_id=result_id,
        csv_path=str(validated_path)  # ✅ 안전한 경로
    )
```

---

### 🔴 Issue #5: CORS 설정 위험

**파일**: `backend/src/main.py:40-46`
**심각도**: **HIGH**

#### 문제점

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ 모든 도메인 허용!
    allow_credentials=True,  # ❌ 인증 정보 포함!
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**위험**:
- 악성 웹사이트에서 사용자의 JWT 토큰으로 API 호출 가능
- CSRF 공격 가능
- XSS + CORS 조합으로 토큰 탈취 가능

#### 해결 방안

```python
# backend/src/main.py
import os

def create_app() -> FastAPI:
    # 환경 변수에서 허용할 Origin 가져오기
    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173"
    ).split(",")

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # ✅ 명시적 도메인만
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # ✅ 필요한 메소드만
        allow_headers=["Content-Type", "Authorization"],  # ✅ 필요한 헤더만
        max_age=3600,  # Preflight 캐싱
    )
```

**환경 변수 설정**:

```bash
# 개발 환경
export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"

# 프로덕션 환경
export ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
```

---

### 🔴 Issue #6: 예제 암호화 키 사용 가능

**파일**: `backend/.env.example:6`
**심각도**: **HIGH**

#### 문제점

```bash
# .env.example
ENCRYPTION_KEY=5ztmGVttW8FnSiwrmwh4QYbEiS2wWSDB6h-kQsRq4dk=  # ❌ 실제 키!
```

사용자가 `.env.example`을 복사해서 사용할 경우, 모든 API 키가 **공개된 키로 암호화**됨.

#### 해결 방안

**1단계: .env.example 수정**

```bash
# backend/.env.example

# API 키 암호화 키 (32바이트 base64 인코딩)
# ⚠️ 아래 명령어로 새 키를 생성하세요:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=CHANGE_THIS_TO_YOUR_OWN_KEY_GENERATE_WITH_COMMAND_ABOVE
```

**2단계: 시작 시 검증 추가**

```python
# backend/src/utils/crypto_secrets.py

# 예제 키 목록 (절대 사용 금지)
FORBIDDEN_KEYS = [
    "5ztmGVttW8FnSiwrmwh4QYbEiS2wWSDB6h-kQsRq4dk=",
    "CHANGE_THIS_TO_YOUR_OWN_KEY_GENERATE_WITH_COMMAND_ABOVE",
]

def _build_fernet() -> Fernet:
    """Fernet 인스턴스 생성 (검증 포함)"""
    key = getenv("ENCRYPTION_KEY", "")

    # 1. 키가 설정되었는지 확인
    if not key:
        raise CryptoError(
            "ENCRYPTION_KEY environment variable is required. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    # 2. 예제 키 사용 여부 확인
    if key in FORBIDDEN_KEYS:
        raise CryptoError(
            "ENCRYPTION_KEY is using an example/default key. "
            "Generate a new key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    # 3. 키 형식 검증
    try:
        return Fernet(key.encode())
    except Exception as e:
        raise CryptoError(f"Invalid ENCRYPTION_KEY format: {e}")
```

**3단계: JWT Secret도 동일하게 검증**

```python
# backend/src/config.py
import os

FORBIDDEN_JWT_SECRETS = [
    "change_me",
    "change_me_to_random_secret_key",
]

def validate_jwt_secret() -> str:
    """JWT Secret 검증"""
    secret = os.getenv("JWT_SECRET", "")

    if not secret:
        raise ValueError("JWT_SECRET must be set in environment variables")

    if secret in FORBIDDEN_JWT_SECRETS:
        raise ValueError(
            "JWT_SECRET is using a default value. "
            "Generate a secure random string: openssl rand -hex 32"
        )

    if len(secret) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters")

    return secret

class Settings(BaseModel):
    # ... 기존 설정 ...
    jwt_secret: str = Field(default_factory=validate_jwt_secret)
```

---

### 🔴 Issue #7: 입력 검증 부족

**파일**: `backend/src/services/trade_executor.py:50-65`
**심각도**: **HIGH**

#### 문제점

```python
async def place_market_order(
    client, symbol: str, side: str, qty: float, leverage: int
) -> Any:
    # ❌ 검증 없이 바로 사용!
    await client.set_leverage(symbol, leverage)
    order = await client.create_order(
        symbol=symbol,
        side=side,
        order_type='market',
        amount=Decimal(str(qty))
    )
```

**공격 시나리오**:
- `leverage=1000` → 즉시 청산
- `qty=-100` → 음수 수량
- `side="invalid"` → API 에러

#### 해결 방안

```python
# backend/src/utils/validators.py
from decimal import Decimal
from typing import Literal

class OrderValidator:
    """주문 파라미터 검증"""

    # 심볼별 최소/최대 수량 (실제로는 거래소 API에서 가져오기)
    QUANTITY_LIMITS = {
        "BTCUSDT": {"min": Decimal("0.001"), "max": Decimal("10")},
        "ETHUSDT": {"min": Decimal("0.01"), "max": Decimal("100")},
    }

    @staticmethod
    def validate_symbol(symbol: str) -> str:
        """심볼 검증"""
        allowed_symbols = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"}
        symbol = symbol.upper().strip()

        if symbol not in allowed_symbols:
            raise ValueError(f"Invalid symbol: {symbol}. Allowed: {allowed_symbols}")

        return symbol

    @staticmethod
    def validate_side(side: str) -> Literal["buy", "sell"]:
        """주문 방향 검증"""
        side = side.lower().strip()

        if side not in ["buy", "sell"]:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")

        return side

    @staticmethod
    def validate_quantity(symbol: str, qty: float) -> Decimal:
        """수량 검증"""
        qty_decimal = Decimal(str(qty))

        # 1. 양수 확인
        if qty_decimal <= 0:
            raise ValueError(f"Quantity must be positive: {qty}")

        # 2. 심볼별 제한 확인
        limits = OrderValidator.QUANTITY_LIMITS.get(
            symbol,
            {"min": Decimal("0.001"), "max": Decimal("10")}
        )

        if qty_decimal < limits["min"]:
            raise ValueError(f"Quantity too small. Min: {limits['min']}")

        if qty_decimal > limits["max"]:
            raise ValueError(f"Quantity too large. Max: {limits['max']}")

        return qty_decimal

    @staticmethod
    def validate_leverage(leverage: int) -> int:
        """레버리지 검증"""
        if not isinstance(leverage, int):
            raise ValueError(f"Leverage must be integer: {type(leverage)}")

        if leverage < 1 or leverage > 100:
            raise ValueError(f"Leverage must be 1-100: {leverage}")

        return leverage
```

**적용**:

```python
# backend/src/services/trade_executor.py
from ..utils.validators import OrderValidator

async def place_market_order(
    client, symbol: str, side: str, qty: float, leverage: int
) -> Any:
    """시장가 주문 실행 (검증 추가)"""

    # ✅ 파라미터 검증
    try:
        symbol = OrderValidator.validate_symbol(symbol)
        side = OrderValidator.validate_side(side)
        qty_decimal = OrderValidator.validate_quantity(symbol, qty)
        leverage = OrderValidator.validate_leverage(leverage)
    except ValueError as e:
        logger.error(f"Order validation failed: {e}")
        raise

    # 레버리지 설정
    await client.set_leverage(symbol, leverage)

    # 주문 생성
    order = await client.create_order(
        symbol=symbol,
        side=side,
        order_type='market',
        amount=qty_decimal
    )

    return order
```

---

## 2. 코드 품질 개선

### 🟡 Issue #8: 코드 중복 - 거래소 클라이언트 초기화

**파일**: `backend/src/api/account.py:45-54, 120-128`
**심각도**: MEDIUM

#### 문제점

같은 코드가 2번 반복됨:

```python
# balance() 함수에서
client = exchange_manager.get_client(
    user_id=user_id,
    exchange_name=exchange_name,
    api_key=decrypt_secret(api_key.encrypted_api_key),
    secret_key=decrypt_secret(api_key.encrypted_secret_key),
    passphrase=decrypt_secret(api_key.encrypted_passphrase) if api_key.encrypted_passphrase else None
)

# positions() 함수에서도 동일한 코드
```

#### 해결 방안

```python
# backend/src/services/exchange_service.py
from typing import Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from ..database.models import User, ApiKey
from ..services.exchanges import exchange_manager, BaseExchange
from ..utils.crypto_secrets import decrypt_secret

class ExchangeService:
    """거래소 클라이언트 관리 서비스"""

    @staticmethod
    async def get_user_exchange_client(
        session: AsyncSession,
        user_id: int
    ) -> Tuple[BaseExchange, str]:
        """
        사용자의 거래소 클라이언트 가져오기

        Args:
            session: DB 세션
            user_id: 사용자 ID

        Returns:
            (거래소 클라이언트, 거래소 이름)

        Raises:
            HTTPException: API 키 없음
        """
        # 사용자 정보 조회
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalars().first()

        # API 키 조회
        api_key_result = await session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id)
        )
        api_key = api_key_result.scalars().first()

        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="API keys not configured. Please add your exchange API keys first."
            )

        # 거래소 이름 결정
        exchange_name = user.exchange if user and user.exchange else "bitget"

        # 클라이언트 생성
        client = exchange_manager.get_client(
            user_id=user_id,
            exchange_name=exchange_name,
            api_key=decrypt_secret(api_key.encrypted_api_key),
            secret_key=decrypt_secret(api_key.encrypted_secret_key),
            passphrase=decrypt_secret(api_key.encrypted_passphrase)
                if api_key.encrypted_passphrase else None
        )

        return client, exchange_name
```

**사용**:

```python
# backend/src/api/account.py
from ..services.exchange_service import ExchangeService

@router.get("/balance")
async def balance(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """계정 잔고 조회"""
    if not await has_api_key(session, user_id):
        return get_mock_balance_response("API key not configured")

    try:
        # ✅ 한 줄로 간단해짐
        client, exchange_name = await ExchangeService.get_user_exchange_client(
            session, user_id
        )

        balance_data = await client.get_futures_balance()
        # ... 나머지 로직
```

---

### 🟡 Issue #9: 광범위한 예외 처리

**파일**: 여러 파일
**심각도**: MEDIUM

#### 문제점

```python
except Exception as e:  # ❌ 너무 광범위!
    logger.error(f"Error: {e}")
```

**문제**:
- `KeyboardInterrupt`, `SystemExit`도 잡음
- 프로그래밍 에러 숨김
- 디버깅 어려움

#### 해결 방안

```python
# backend/src/utils/exceptions.py
"""커스텀 예외 정의"""

class TradingException(Exception):
    """거래 관련 기본 예외"""
    pass

class ExchangeConnectionError(TradingException):
    """거래소 연결 에러"""
    pass

class InsufficientBalanceError(TradingException):
    """잔고 부족"""
    pass

class InvalidOrderError(TradingException):
    """잘못된 주문"""
    pass

class StrategyExecutionError(TradingException):
    """전략 실행 에러"""
    pass
```

**사용**:

```python
# backend/src/services/bot_runner.py
from ..utils.exceptions import (
    ExchangeConnectionError,
    StrategyExecutionError
)

async def run_bot(self):
    try:
        # ... 봇 로직 ...

    except ExchangeConnectionError as e:
        # 거래소 연결 에러 - 재시도
        logger.warning(f"Exchange connection failed: {e}. Retrying in 10s...")
        await asyncio.sleep(10)

    except StrategyExecutionError as e:
        # 전략 실행 에러 - 전략 비활성화
        logger.error(f"Strategy failed: {e}. Disabling strategy.")
        await self.disable_strategy(strategy_id)

    except (ValueError, KeyError) as e:
        # 예상된 에러 - 로그만
        logger.error(f"Known error: {e}")

    except Exception as e:
        # 예상 못한 에러 - 재발생
        logger.exception(f"Unexpected error in bot: {e}")
        raise  # ✅ 재발생시켜서 상위에서 처리
```

---

### 🟡 Issue #10: Magic Numbers

**파일**: 여러 파일
**심각도**: LOW

#### 문제점

```python
await asyncio.wait_for(self.market_queue.get(), timeout=60.0)  # ❌ Magic number
await asyncio.sleep(0.1)  # ❌
limit=5,  # 분당 5회  # ❌
```

#### 해결 방안

```python
# backend/src/config.py
class BotConfig:
    """봇 설정"""
    MARKET_DATA_TIMEOUT = 60.0  # seconds
    LOOP_SLEEP_INTERVAL = 0.1  # seconds
    MAX_CONSECUTIVE_ERRORS = 10
    ERROR_RETRY_DELAY = 1.0  # seconds

class RateLimitConfig:
    """Rate Limit 설정"""
    BACKTEST_PER_MINUTE = 5
    BACKTEST_PER_HOUR = 10
    GENERAL_API_PER_MINUTE = 60

class StrategyConfig:
    """전략 설정"""
    CANDLE_BUFFER_SIZE = 200
    MIN_CANDLES_REQUIRED = 50
```

**사용**:

```python
# backend/src/workers/bot_runner.py
from ..config import BotConfig

market_data = await asyncio.wait_for(
    self.market_queue.get(),
    timeout=BotConfig.MARKET_DATA_TIMEOUT  # ✅
)

await asyncio.sleep(BotConfig.LOOP_SLEEP_INTERVAL)  # ✅
```

---

## 3. 성능 최적화

### 🟠 Issue #11: 데이터베이스 인덱스 부족

**파일**: `backend/src/database/models.py`
**심각도**: **HIGH**

#### 문제점

자주 조회하는 컬럼에 인덱스가 없음:

```python
class Trade(Base):
    user_id = Column(Integer, ForeignKey("users.id"))  # ❌ 인덱스 없음
    symbol = Column(String, nullable=False)  # ❌
    created_at = Column(DateTime, default=datetime.utcnow)  # ❌
```

**쿼리 예시**:
```sql
-- 사용자별 거래 내역 (느림!)
SELECT * FROM trades WHERE user_id = 6 ORDER BY created_at DESC LIMIT 50;
```

#### 영향

- 거래 내역 1000건 이상 시 쿼리 속도 저하
- `ORDER BY created_at` 시 Full Table Scan
- 사용자 증가 시 성능 급격히 나빠짐

#### 해결 방안

```python
# backend/src/database/models.py
from sqlalchemy import Index

class Trade(Base):
    """거래 내역"""
    __tablename__ = "trades"

    # ✅ 복합 인덱스 정의
    __table_args__ = (
        # user_id + created_at 복합 인덱스 (거래 내역 조회용)
        Index('idx_trade_user_created', 'user_id', 'created_at'),

        # symbol 인덱스 (심볼별 거래 조회용)
        Index('idx_trade_symbol', 'symbol'),

        # status 인덱스 (미체결 주문 조회용)
        Index('idx_trade_status', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    # ... 나머지 컬럼

class Equity(Base):
    """자산 기록"""
    __tablename__ = "equity"

    __table_args__ = (
        # ✅ user_id + timestamp 복합 인덱스
        Index('idx_equity_user_time', 'user_id', 'timestamp'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    # ...

class BacktestResult(Base):
    """백테스트 결과"""
    __tablename__ = "backtest_results"

    __table_args__ = (
        # ✅ user_id + created_at 복합 인덱스
        Index('idx_backtest_user_created', 'user_id', 'created_at'),

        # status 인덱스 (실행 중인 백테스트 조회용)
        Index('idx_backtest_status', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    # ...
```

**마이그레이션 생성**:

```bash
cd backend
alembic revision -m "add_performance_indexes"
```

```python
# alembic/versions/xxx_add_performance_indexes.py
def upgrade():
    # Trade 인덱스
    op.create_index('idx_trade_user_created', 'trades', ['user_id', 'created_at'])
    op.create_index('idx_trade_symbol', 'trades', ['symbol'])
    op.create_index('idx_trade_status', 'trades', ['status'])

    # Equity 인덱스
    op.create_index('idx_equity_user_time', 'equity', ['user_id', 'timestamp'])

    # BacktestResult 인덱스
    op.create_index('idx_backtest_user_created', 'backtest_results', ['user_id', 'created_at'])
    op.create_index('idx_backtest_status', 'backtest_results', ['status'])

def downgrade():
    op.drop_index('idx_trade_user_created', 'trades')
    op.drop_index('idx_trade_symbol', 'trades')
    op.drop_index('idx_trade_status', 'trades')
    op.drop_index('idx_equity_user_time', 'equity')
    op.drop_index('idx_backtest_user_created', 'backtest_results')
    op.drop_index('idx_backtest_status', 'backtest_results')
```

**실행**:
```bash
alembic upgrade head
```

---

### 🟠 Issue #12: 페이지네이션 없음

**파일**: `backend/src/api/order.py:26-50`
**심각도**: **HIGH**

#### 문제점

```python
result = await session.execute(
    select(Trade).where(Trade.user_id == user_id).order_by(Trade.created_at.desc())
)
trades = result.scalars().all()  # ❌ 모든 거래 내역 로드!
```

사용자가 거래를 10,000건 했다면 **10,000건 전부 메모리에 로드**.

#### 해결 방안

```python
# backend/src/api/order.py
from fastapi import Query
from sqlalchemy import func

@router.get("/history")
async def order_history(
    limit: int = Query(default=50, ge=1, le=500, description="페이지 크기"),
    offset: int = Query(default=0, ge=0, description="시작 위치"),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    거래 내역 조회 (페이지네이션 지원)

    - limit: 한 페이지에 가져올 개수 (최대 500)
    - offset: 건너뛸 개수 (페이지 계산: offset = page * limit)
    """
    # 거래 내역 조회 (페이지네이션)
    result = await session.execute(
        select(Trade)
        .where(Trade.user_id == user_id)
        .order_by(Trade.created_at.desc())
        .limit(limit)  # ✅ 제한
        .offset(offset)  # ✅ 오프셋
    )
    trades = result.scalars().all()

    # 전체 개수 조회 (페이지 정보용)
    count_result = await session.execute(
        select(func.count()).select_from(Trade).where(Trade.user_id == user_id)
    )
    total_count = count_result.scalar()

    return {
        "trades": [
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "side": trade.side,
                "price": str(trade.price),
                "quantity": str(trade.quantity),
                "created_at": trade.created_at.isoformat() if trade.created_at else None,
            }
            for trade in trades
        ],
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_count,
            "current_page": offset // limit + 1,
            "total_pages": (total_count + limit - 1) // limit,
        }
    }
```

**프론트엔드 사용 예시**:
```javascript
// 첫 페이지
fetch('/order/history?limit=50&offset=0')

// 두 번째 페이지
fetch('/order/history?limit=50&offset=50')

// 세 번째 페이지
fetch('/order/history?limit=50&offset=100')
```

---

### 🟡 Issue #13: 동기 파일 I/O

**파일**: `backend/src/services/backtest_engine.py:34-55`
**심각도**: MEDIUM

#### 문제점

```python
with open(path, "r") as f:  # ❌ Blocking I/O
    reader = csv.DictReader(f)
    for row in reader:
        # ...
```

대용량 CSV (100MB) 읽을 때 이벤트 루프 블록됨.

#### 해결 방안

```bash
pip install aiofiles
```

```python
# backend/src/services/backtest_engine.py
import aiofiles
import csv
from io import StringIO

async def load_candles(self, path: str):
    """CSV에서 캔들 데이터 비동기 로드"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")

    candles = []

    # ✅ 비동기 파일 읽기
    async with aiofiles.open(path, "r") as f:
        content = await f.read()

    # CSV 파싱 (메모리에서)
    reader = csv.DictReader(StringIO(content))

    for row in reader:
        try:
            candles.append({
                "timestamp": row["timestamp"],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            })
        except (KeyError, ValueError) as e:
            logger.warning(f"Invalid candle data: {e}")
            continue

    return candles
```

---

### 🟡 Issue #14: 캔들 버퍼 메모리 누수

**파일**: `backend/src/services/strategy_engine.py:7-8`
**심각도**: MEDIUM

#### 문제점

```python
_candle_buffers: dict[str, Deque[dict]] = {}  # ❌ 무한 증가

def _ensure_buffer(symbol: str) -> Deque[dict]:
    if symbol not in _candle_buffers:
        _candle_buffers[symbol] = deque(maxlen=BUFFER_SIZE)
    return _candle_buffers[symbol]
```

100개 심볼 거래 → 100개 버퍼 → 메모리 누수

#### 해결 방안

```python
# backend/src/services/strategy_engine.py
from collections import OrderedDict, deque

class CandleBufferManager:
    """캔들 버퍼 관리 (LRU 캐시)"""

    def __init__(self, max_buffers: int = 50, buffer_size: int = 200):
        self._buffers: OrderedDict[str, deque] = OrderedDict()
        self._max_buffers = max_buffers
        self._buffer_size = buffer_size

    def get_buffer(self, symbol: str) -> deque:
        """버퍼 가져오기 (LRU)"""
        # 이미 있으면 최근 사용으로 이동
        if symbol in self._buffers:
            self._buffers.move_to_end(symbol)
            return self._buffers[symbol]

        # 새 버퍼 생성
        buffer = deque(maxlen=self._buffer_size)
        self._buffers[symbol] = buffer

        # 최대 개수 초과 시 가장 오래된 것 제거 (LRU)
        if len(self._buffers) > self._max_buffers:
            oldest_symbol, _ = self._buffers.popitem(last=False)
            logger.debug(f"Evicted candle buffer for {oldest_symbol}")

        return buffer

# ✅ 전역 매니저
_buffer_manager = CandleBufferManager(max_buffers=50, buffer_size=200)

def _ensure_buffer(symbol: str) -> deque:
    """캔들 버퍼 가져오기"""
    return _buffer_manager.get_buffer(symbol)
```

---

## 4. 아키텍처 개선

### 🟡 Issue #15: 비즈니스 로직이 API 레이어에 있음

**파일**: `backend/src/api/backtest.py:21-76`
**심각도**: MEDIUM

#### 문제점

50줄의 백테스트 로직이 API 파일에 있음 → 테스트 어려움, 재사용 불가

#### 해결 방안

**서비스 레이어 생성**:

```python
# backend/src/services/backtest_service.py
from typing import Dict, Any
from sqlalchemy.orm import Session
from ..database.models import BacktestResult
from .backtest_engine import BacktestEngine
import logging

logger = logging.getLogger(__name__)

class BacktestService:
    """백테스트 서비스"""

    @staticmethod
    async def create_pending_backtest(
        session: Session,
        user_id: int,
        params: Dict[str, Any]
    ) -> BacktestResult:
        """대기 중인 백테스트 레코드 생성"""
        result = BacktestResult(
            user_id=user_id,
            symbol=params.get("symbol", "BTCUSDT"),
            strategy_name=params.get("strategy_name", ""),
            status="pending",
            initial_capital=params.get("initial_capital", 10000),
        )
        session.add(result)
        await session.commit()
        await session.refresh(result)
        return result

    @staticmethod
    async def run_backtest_task(result_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """백테스트 실행 (백그라운드 태스크)"""
        from ..database.session import SessionLocal

        with SessionLocal() as session:
            try:
                # 상태 업데이트: running
                await BacktestService.update_status(session, result_id, "running")

                # 백테스트 실행
                engine = BacktestEngine(
                    initial_capital=params["initial_capital"],
                    fee_rate=params.get("fee_rate", 0.0005),
                )

                await engine.load_candles(params["csv_path"])
                await engine.run(
                    strategy_name=params["strategy_name"],
                    strategy_params=params.get("strategy_params", {})
                )

                # 결과 저장
                metrics = engine.get_metrics()
                await BacktestService.save_result(session, result_id, metrics)

                # 상태 업데이트: completed
                await BacktestService.update_status(session, result_id, "completed")

                return metrics

            except Exception as e:
                logger.error(f"Backtest failed: {e}", exc_info=True)
                await BacktestService.update_status(
                    session, result_id, "failed", error_message=str(e)
                )
                raise

    @staticmethod
    async def update_status(
        session: Session,
        result_id: int,
        status: str,
        error_message: str = None
    ):
        """백테스트 상태 업데이트"""
        result = session.get(BacktestResult, result_id)
        if result:
            result.status = status
            if error_message:
                result.error_message = error_message
            session.commit()

    @staticmethod
    async def save_result(
        session: Session,
        result_id: int,
        metrics: Dict[str, Any]
    ):
        """백테스트 결과 저장"""
        result = session.get(BacktestResult, result_id)
        if result:
            result.final_balance = metrics.get("final_balance")
            result.total_return = metrics.get("total_return")
            result.win_rate = metrics.get("win_rate")
            result.sharpe_ratio = metrics.get("sharpe_ratio")
            result.max_drawdown = metrics.get("max_drawdown")
            session.commit()
```

**API 레이어는 간단하게**:

```python
# backend/src/api/backtest.py
from ..services.backtest_service import BacktestService

@router.post("/start")
async def start_backtest(
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """백테스트 시작 (간단해짐!)"""

    # ✅ 서비스 레이어 사용
    result = await BacktestService.create_pending_backtest(
        session, user_id, request.dict()
    )

    # 백그라운드 태스크 등록
    background_tasks.add_task(
        BacktestService.run_backtest_task,
        result.id,
        request.dict()
    )

    return {
        "result_id": result.id,
        "status": "queued",
        "message": "Backtest started"
    }
```

---

### 🟡 Issue #16: 중앙화된 에러 핸들러 없음

**파일**: 없음 (누락)
**심각도**: MEDIUM

#### 해결 방안

```python
# backend/src/exceptions.py
"""중앙화된 예외 정의"""

class AppException(Exception):
    """애플리케이션 기본 예외"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        super().__init__(message)

class ValidationError(AppException):
    """입력 검증 에러 (400)"""
    def __init__(self, message: str):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR")

class AuthenticationError(AppException):
    """인증 실패 (401)"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401, error_code="AUTH_ERROR")

class AuthorizationError(AppException):
    """권한 없음 (403)"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403, error_code="FORBIDDEN")

class ResourceNotFoundError(AppException):
    """리소스 없음 (404)"""
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", status_code=404, error_code="NOT_FOUND")

class ExchangeAPIError(AppException):
    """거래소 API 에러 (502)"""
    def __init__(self, message: str):
        super().__init__(message, status_code=502, error_code="EXCHANGE_ERROR")
```

**전역 예외 핸들러**:

```python
# backend/src/main.py
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid
from .exceptions import AppException

def create_app() -> FastAPI:
    app = FastAPI(...)

    # ✅ 커스텀 예외 핸들러
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """애플리케이션 예외 처리"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": str(request.url),
                }
            }
        )

    # ✅ 일반 예외 핸들러
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """예상치 못한 예외 처리"""
        error_id = str(uuid.uuid4())

        logger.exception(
            f"Unhandled exception",
            extra={"error_id": error_id, "path": str(request.url)},
            exc_info=exc
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "error_id": error_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            }
        )

    return app
```

---

### 🟡 Issue #17: 설정 관리 분산

**파일**: 여러 파일
**심각도**: MEDIUM

#### 해결 방안

**중앙화된 설정**:

```python
# backend/src/config.py
from pydantic import BaseSettings, Field, validator
from typing import List

class Settings(BaseSettings):
    """애플리케이션 설정 (환경 변수 기반)"""

    # ===== 앱 설정 =====
    app_name: str = "Auto Trading Dashboard"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # ===== 데이터베이스 =====
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # ===== 보안 =====
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_seconds: int = 86400  # 24시간
    encryption_key: str

    # ===== CORS =====
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        """CORS origins 리스트로 변환"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # ===== Rate Limiting =====
    rate_limit_per_minute: int = 60
    rate_limit_backtest_per_minute: int = 5
    rate_limit_backtest_per_hour: int = 10

    # ===== 봇 설정 =====
    bot_market_data_timeout: float = 60.0
    bot_loop_sleep_interval: float = 0.1
    bot_max_consecutive_errors: int = 10

    # ===== 전략 설정 =====
    strategy_buffer_size: int = 200
    strategy_min_candles: int = 50

    # ===== 거래소 설정 =====
    bitget_ws_url: str = "wss://ws.bitget.com/mix/v1/stream"

    # ===== 외부 API =====
    deepseek_api_key: str = ""

    # ===== 파일 경로 =====
    data_dir: str = "./data"

    # ===== 검증 =====
    @validator("jwt_secret")
    def validate_jwt_secret(cls, v):
        forbidden = ["change_me", "change_me_to_random_secret_key"]
        if not v or v in forbidden:
            raise ValueError("JWT_SECRET must be set to a secure value")
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @validator("encryption_key")
    def validate_encryption_key(cls, v):
        forbidden = ["5ztmGVttW8FnSiwrmwh4QYbEiS2wWSDB6h-kQsRq4dk="]
        if not v or v in forbidden:
            raise ValueError("ENCRYPTION_KEY must not use example value")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

# ✅ 싱글톤 인스턴스
settings = Settings()
```

**사용**:

```python
# 어디서든 import해서 사용
from src.config import settings

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ✅
    ...
)

# 봇 설정
timeout = settings.bot_market_data_timeout  # ✅
```

---

## 5. 실행 계획

### Phase 1: 긴급 보안 수정 (1주차)

**목표**: Critical 보안 이슈 수정

- [ ] **1일차**: 관리자 RBAC 구현
  - User 모델에 role 필드 추가
  - Alembic 마이그레이션
  - `require_admin` dependency 생성
  - 모든 admin 엔드포인트에 적용
  - 첫 관리자 계정 생성

- [ ] **2일차**: WebSocket 인증 추가
  - JWT 토큰 검증 로직
  - 프론트엔드 연결 코드 업데이트

- [ ] **3일차**: API 키 노출 수정
  - `mask_secret()` 함수 구현
  - `/my_keys` 엔드포인트 수정
  - `/reveal_keys` 엔드포인트 추가 (Rate Limited)
  - Admin 엔드포인트 수정

- [ ] **4일차**: Path Traversal 수정
  - `validate_csv_path()` 함수 구현
  - 백테스트 엔드포인트 적용
  - 테스트

- [ ] **5일차**: CORS/Secrets 수정
  - CORS 설정 수정
  - `.env.example` 업데이트
  - 암호화 키 검증 로직 추가
  - JWT Secret 검증 추가

**검증**:
```bash
# 보안 테스트
pytest tests/security/
```

---

### Phase 2: 입력 검증 및 에러 처리 (2주차)

- [ ] **6-7일차**: 입력 검증
  - `OrderValidator` 클래스 구현
  - 모든 주문 관련 함수에 적용
  - 심볼/수량/레버리지 검증
  - Pydantic 스키마로 전략 파라미터 검증

- [ ] **8-9일차**: 예외 처리 개선
  - 커스텀 예외 정의 (`exceptions.py`)
  - 전역 예외 핸들러 추가
  - 광범위한 `except Exception` 제거
  - 로그 메시지 개선

- [ ] **10일차**: 에러 응답 표준화
  - 모든 에러를 일관된 형식으로 반환
  - 민감한 정보 제거
  - Error ID 추가

---

### Phase 3: 성능 최적화 (3주차)

- [ ] **11-12일차**: 데이터베이스 최적화
  - 인덱스 추가 (Trade, Equity, BacktestResult)
  - Alembic 마이그레이션
  - 쿼리 성능 측정 (EXPLAIN ANALYZE)

- [ ] **13일차**: 페이지네이션 추가
  - `/order/history` 수정
  - `/trades/positions` 수정
  - Response 모델 정의

- [ ] **14-15일차**: 비동기 I/O
  - `aiofiles` 설치
  - 백테스트 CSV 로드 비동기화
  - DeepSeek API 호출 비동기화

**성능 테스트**:
```bash
# 부하 테스트
locust -f tests/performance/locustfile.py
```

---

### Phase 4: 코드 품질 및 아키텍처 (4-5주차)

- [ ] **16-17일차**: 서비스 레이어 생성
  - `ExchangeService`
  - `BacktestService`
  - `UserService`

- [ ] **18-19일차**: 코드 정리
  - 중복 코드 제거
  - Magic numbers → 상수
  - Type hints 추가
  - Docstrings 통일

- [ ] **20-21일차**: 설정 및 로깅
  - 중앙화된 설정 (`config.py`)
  - 구조화된 로깅 (JSON)
  - 로그 레벨 통일

- [ ] **22-24일차**: 테스트 작성
  - 보안 테스트
  - API 엔드포인트 테스트
  - 서비스 레이어 유닛 테스트

---

### Phase 5: 모니터링 및 문서화 (6주차)

- [ ] **25-26일차**: 모니터링
  - Health check 엔드포인트 개선
  - Metrics 수집 (Prometheus)
  - Sentry 에러 트래킹

- [ ] **27-28일차**: 문서화
  - API 문서 (OpenAPI/Swagger)
  - 아키텍처 다이어그램
  - 배포 가이드

- [ ] **29-30일차**: 최종 점검
  - 보안 감사
  - 성능 테스트
  - 코드 리뷰

---

## 6. 우선순위별 요약

### 🔴 즉시 수정 필요 (Critical)

1. ✅ 관리자 RBAC 추가
2. ✅ WebSocket 인증
3. ✅ API 키 노출 방지
4. ✅ Path Traversal 수정
5. ✅ CORS 제한
6. ✅ 예제 키 검증
7. ✅ 입력 검증

### 🟠 1-2주 내 수정 (High)

8. 데이터베이스 인덱스
9. 페이지네이션
10. 에러 처리 개선

### 🟡 1개월 내 수정 (Medium)

11. 서비스 레이어 리팩토링
12. 코드 중복 제거
13. 설정 중앙화
14. 비동기 I/O

### 🟢 장기 개선 (Low)

15. 테스트 커버리지 향상
16. 문서화
17. 모니터링

---

## 7. 참고 자료

### 보안 체크리스트

```markdown
- [ ] 모든 관리자 엔드포인트에 RBAC 적용
- [ ] WebSocket JWT 인증
- [ ] API 키 마스킹
- [ ] 파일 경로 검증
- [ ] CORS origins 제한
- [ ] 환경 변수 검증 (예제 키 거부)
- [ ] SQL Injection 방지 (ORM 사용)
- [ ] XSS 방지 (입력 sanitize)
- [ ] Rate Limiting (사용자별)
- [ ] HTTPS 강제 (프로덕션)
- [ ] 민감한 로그 제거
- [ ] 에러 메시지에서 내부 정보 제거
```

### 성능 체크리스트

```markdown
- [ ] 데이터베이스 인덱스
- [ ] N+1 쿼리 제거
- [ ] 페이지네이션
- [ ] Connection Pooling
- [ ] 비동기 I/O
- [ ] Caching (Redis)
- [ ] CDN (정적 파일)
- [ ] Gzip 압축
```

### 코드 품질 체크리스트

```markdown
- [ ] Type hints
- [ ] Docstrings
- [ ] 중복 코드 제거
- [ ] Magic numbers 제거
- [ ] Pydantic 검증
- [ ] 서비스 레이어 분리
- [ ] 테스트 커버리지 80%+
- [ ] Linting (black, ruff)
```

---

## 8. 문의

개선 사항 관련 질문:
- 이슈 트래커: GitHub Issues
- 문서: `/docs` 디렉토리

**마지막 업데이트**: 2025년 12월 1일
