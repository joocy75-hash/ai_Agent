# 🚨 긴급 문제 해결 가이드

## 현재 발생한 문제들

### 1. Rate Limit 초과 오류 ⚠️

**증상**:

```
RateLimitExceededError: IP rate limit exceeded. Try again after 54 seconds
```

**원인**:

- 짧은 시간에 너무 많은 API 요청
- Rate Limit 미들웨어가 IP를 차단

**즉시 해결 방법**:

#### 옵션 1: Rate Limit 일시 비활성화 (개발 환경)

**파일**: `backend/src/main.py`

```python
# Rate Limit 미들웨어 주석 처리
# app.add_middleware(RateLimitMiddleware)
```

#### 옵션 2: Rate Limit 설정 완화

**파일**: `backend/src/middleware/rate_limit_improved.py`

```python
# IP별 Rate Limit 설정 (현재)
IP_RATE_LIMIT = 100  # 기본: 100 requests/minute
IP_RATE_WINDOW = 60  # 기본: 60 seconds

# 개발 환경용으로 변경
IP_RATE_LIMIT = 1000  # 1000 requests/minute으로 증가
IP_RATE_WINDOW = 60
```

#### 옵션 3: 서버 재시작 (메모리 초기화)

```bash
# 1. 백엔드 서버 중지
pkill -f "uvicorn src.main:app"

# 2. 1분 대기 (Rate Limit 윈도우 만료)
sleep 60

# 3. 서버 재시작
cd backend
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### 2. 로그인 API 실패

**증상**:

```json
{
    "success": false,
    "error": {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "Internal server error"
    }
}
```

**원인**:

- Rate Limit으로 인한 요청 차단
- 또는 JWT_SECRET 환경 변수 문제

**해결 방법**:

#### 1) Rate Limit 해결 후 재시도

위의 Rate Limit 해결 방법 적용 후 로그인 재시도

#### 2) 환경 변수 확인

```bash
cd backend

# .env 파일 존재 확인
ls -la .env

# 필수 환경 변수 확인 (직접 파일 열어서 확인)
# - JWT_SECRET
# - ENCRYPTION_KEY
# - DATABASE_URL
```

---

### 3. 차트 데이터 로드 실패

**증상**:

```
차트 데이터 로드에 실패했습니다.
```

**원인**:

- 인증 실패 (로그인 API 오류로 인한 토큰 없음)
- Rate Limit 초과

**해결 방법**:

1. Rate Limit 해결
2. 로그인 성공 확인
3. 브라우저 새로고침

---

### 4. 잔고 조회 실패

**증상**:

```
잔고 조회 실패
```

**원인**:

- 인증 실패
- Rate Limit 초과

**해결 방법**:

동일하게 Rate Limit 해결 후 재시도

---

### 5. PositionList 오류

**증상**:

```
Uncaught TypeError: positions.map is not a function
```

**원인**:

- API 응답이 배열이 아닌 객체 또는 undefined
- 인증 실패로 인한 빈 응답

**해결 방법**:

#### 임시 수정 (frontend/src/components/PositionList.jsx)

```javascript
const loadPositions = async () =\u003e {
  try {
    setLoading(true);
    const data = await accountAPI.getPositions();
    console.log('[PositionList] Positions loaded:', data);
    
    // ✅ 배열 검증 추가
    if (Array.isArray(data)) {
      setPositions(data);
    } else if (data \u0026\u0026 Array.isArray(data.positions)) {
      setPositions(data.positions);
    } else {
      console.warn('[PositionList] Invalid data format:', data);
      setPositions([]);
    }
    
    setError('');
  } catch (err) {
    console.error('[PositionList] Error loading positions:', err);
    setError('포지션 조회 실패');
    setPositions([]); // ✅ 오류 시 빈 배열 설정
  } finally {
    setLoading(false);
  }
};
```

---

## 🚀 권장 해결 순서

### 1단계: Rate Limit 해결 (가장 중요!)

```bash
# 방법 1: 서버 재시작 + 대기
pkill -f "uvicorn src.main:app"
sleep 60
cd backend && python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2단계: 로그인 테스트

```bash
# 1분 후 로그인 테스트
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"admin1234"}'
```

**성공 응답 예시**:

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": 6,
    "email": "admin@admin.com"
  }
}
```

### 3단계: 프론트엔드 새로고침

브라우저에서 `Ctrl+Shift+R` (강제 새로고침)

### 4단계: 각 기능 확인

- [ ] 로그인 성공
- [ ] 잔고 조회 성공
- [ ] 포지션 조회 성공
- [ ] 차트 로드 성공

---

## 🔧 영구적인 해결 방법

### 1. Rate Limit 설정 조정

**파일**: `backend/src/middleware/rate_limit_improved.py`

```python
# 개발 환경에서는 더 관대한 설정 사용
import os

# 환경에 따라 다른 설정
if os.getenv('ENVIRONMENT') == 'development':
    IP_RATE_LIMIT = 1000  # 개발: 1000 req/min
    IP_RATE_WINDOW = 60
else:
    IP_RATE_LIMIT = 100   # 프로덕션: 100 req/min
    IP_RATE_WINDOW = 60
```

### 2. PositionList 방어적 코딩

**파일**: `frontend/src/components/PositionList.jsx`

Line 14-16 수정:

```javascript
const data = await accountAPI.getPositions();
console.log('[PositionList] Positions loaded:', data);

// 방어적 코딩
const positionsArray = Array.isArray(data) 
  ? data 
  : (data?.positions \u0026\u0026 Array.isArray(data.positions) ? data.positions : []);

setPositions(positionsArray);
```

### 3. API 응답 표준화

모든 API가 일관된 형식으로 응답하도록 수정:

```python
# 성공 응답
{
  "success": true,
  "data": [...],
  "meta": {...}
}

# 실패 응답
{
  "success": false,
  "error": {...}
}
```

---

## 📊 현재 상태 체크리스트

### 백엔드

- [x] 서버 실행 중
- [x] 데이터베이스 연결 정상
- [ ] Rate Limit 문제 해결 필요
- [ ] 로그인 API 정상화 필요

### 프론트엔드

- [ ] 로그인 성공 필요
- [ ] API 호출 정상화 필요
- [ ] 차트 표시 필요
- [ ] 포지션 목록 표시 필요

---

## 🎯 즉시 실행할 명령어

```bash
# 1. 백엔드 서버 중지
pkill -f "uvicorn src.main:app"

# 2. 1분 대기 (Rate Limit 리셋)
echo "Waiting for rate limit reset..."
sleep 60

# 3. 백엔드 재시작
cd /Users/mr.joo/Desktop/auto-dashboard/backend
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload &

# 4. 10초 대기 (서버 시작)
sleep 10

# 5. 로그인 테스트
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"admin1234"}' | python3 -m json.tool

# 6. 성공하면 브라우저 새로고침
echo "✅ 로그인 성공! 브라우저를 새로고침하세요."
```

---

**작성일**: 2025년 12월 2일
**상태**: 긴급 해결 필요
**우선순위**: 🔴 높음
