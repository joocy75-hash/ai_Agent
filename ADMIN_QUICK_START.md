# 관리자 대시보드 빠른 시작 가이드

> 관리자 대시보드 접속 및 사용 방법

---

## 🚀 빠른 시작

### 1. 서버 실행 확인

**백엔드 서버** (포트 8000):
```bash
lsof -i :8000
```

**프론트엔드 서버** (포트 3003):
```bash
lsof -i :3003
```

서버가 실행되지 않았다면:

```bash
# 백엔드 서버 시작
cd backend
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 -m uvicorn src.main:app --reload

# 프론트엔드 서버 시작 (새 터미널)
cd frontend
npm run dev
```

### 2. 관리자 페이지 접속

1. **로그인**: http://localhost:3003/login
   - Email: `admin@admin.com`
   - Password: (관리자 비밀번호)

2. **관리자 대시보드**: http://localhost:3003/admin
   - 왼쪽 사이드바에서 "관리자" (🛡️) 메뉴 클릭

---

## 📊 대시보드 기능

### Overview Tab (개요)

**시스템 통계**:
- 👥 사용자 수 (총 사용자, 활성/비활성)
- 🤖 봇 수 (총 봇, 실행/정지)
- 💰 재무 통계 (AUM, P&L, 거래 수, 미결제 포지션)

**위험 사용자 Top 5**:
- 손실률이 높은 사용자
- 손실 금액 및 백분율 표시

**거래량 통계 (최근 7일)**:
- 일별 거래량 breakdown
- 심볼별 거래량 Top 5
- 평균 거래 크기

### Bots Tab (봇 제어)

**활성 봇 목록**:
- 사용자 이메일
- 봇 전략
- 봇 상태 (Running/Paused)
- 마지막 업데이트 시각

**봇 제어 기능**:
- ⏸️ **개별 봇 정지**: 특정 사용자 봇 강제 정지
- ▶️ **개별 봇 재시작**: 정지된 봇 재시작
- 🚨 **전체 봇 긴급 정지**: 모든 봇을 한번에 정지 (Emergency Stop)

### Users Tab (사용자 관리)
- 향후 구현 예정: 계정 정지/활성화, 강제 로그아웃

### Logs Tab (로그 조회)
- 향후 구현 예정: 시스템/봇/거래 로그 조회 및 필터링

---

## 🔧 API 엔드포인트

### 봇 제어 API
```bash
# 활성 봇 목록 조회
GET /admin/bots/active

# 봇 통계 조회
GET /admin/bots/statistics

# 특정 사용자 봇 정지
POST /admin/bots/{user_id}/pause

# 특정 사용자 봇 재시작
POST /admin/bots/{user_id}/restart

# 전체 봇 긴급 정지
POST /admin/bots/pause-all
```

### 계정 제어 API
```bash
# 계정 정지
POST /admin/users/{user_id}/suspend

# 계정 활성화
POST /admin/users/{user_id}/activate

# 강제 로그아웃
POST /admin/users/{user_id}/force-logout
```

### 글로벌 통계 API
```bash
# 전체 시스템 통계
GET /admin/analytics/global-summary

# 위험 사용자 목록
GET /admin/analytics/risk-users?limit=5

# 거래량 통계
GET /admin/analytics/trading-volume?days=7
```

### 로그 조회 API
```bash
# 시스템 로그 조회
GET /admin/logs/system?level=ERROR&limit=100

# 봇 로그 조회
GET /admin/logs/bot?user_id=6&limit=100

# 거래 로그 조회
GET /admin/logs/trading?user_id=6&symbol=ETHUSDT&limit=100
```

---

## 🧪 테스트 스크립트

**모든 관리자 API 테스트**:
```bash
# 봇 제어 API 테스트
./test_admin_bots_api.sh

# 계정 제어 API 테스트
./test_admin_users_api.sh

# 글로벌 통계 API 테스트
./test_admin_analytics_api.sh

# 로그 조회 API 테스트
./test_admin_logs_api.sh
```

---

## 🔒 보안 주의사항

1. **관리자 권한 필수**: 모든 관리자 API는 `require_admin` 의존성으로 보호됩니다.
2. **감사 로깅**: 모든 관리자 액션은 structured_logger로 기록됩니다.
3. **긴급 정지**: 전체 봇 긴급 정지는 CRITICAL 레벨로 로깅되며, 신중하게 사용해야 합니다.
4. **JWT 토큰**: 401 에러 시 자동으로 로그아웃됩니다.

---

## ⚡ 빠른 명령어

**서버 재시작**:
```bash
# 백엔드 서버 재시작
lsof -ti:8000 | xargs kill -9 2>/dev/null && \
cd backend && \
export DATABASE_URL="sqlite+aiosqlite:///./trading.db" && \
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=" && \
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 -m uvicorn src.main:app --reload

# 프론트엔드 서버 재시작
lsof -ti:3003 | xargs kill -9 2>/dev/null && \
cd frontend && \
npm run dev
```

**서버 상태 확인**:
```bash
# 백엔드 상태 확인
curl http://localhost:8000/health

# 프론트엔드 상태 확인
curl http://localhost:3003
```

**활성 봇 조회** (관리자 토큰 필요):
```bash
TOKEN="your-admin-jwt-token"
curl -X GET "http://localhost:8000/admin/bots/active" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📝 참고 문서

- [ADMIN_IMPLEMENTATION_COMPLETE.md](ADMIN_IMPLEMENTATION_COMPLETE.md) - 전체 구현 완료 보고서
- [ADMIN_API_PROGRESS.md](ADMIN_API_PROGRESS.md) - API 진행 상황 및 테스트 결과
- [ADMIN_PAGE_IMPLEMENTATION_PLAN.md](ADMIN_PAGE_IMPLEMENTATION_PLAN.md) - 원래 구현 계획서

---

## 🆘 문제 해결

### 관리자 메뉴가 보이지 않음
- 관리자 계정으로 로그인했는지 확인
- User 테이블에서 role이 'admin'인지 확인
- 로그아웃 후 다시 로그인

### API 호출 실패 (401 Unauthorized)
- JWT 토큰이 만료되었을 수 있음 (다시 로그인)
- 관리자 권한이 없을 수 있음 (User 테이블에서 role 확인)

### 봇 제어가 작동하지 않음
- 백엔드 서버가 실행 중인지 확인 (`lsof -i :8000`)
- BotStatus 객체가 메모리에 있는지 확인 (서버 재시작 후 봇 재실행 필요)

### 데이터가 표시되지 않음
- 데이터베이스에 데이터가 있는지 확인 (Trade, BotLog, User 테이블)
- 백엔드 로그 확인 (uvicorn 콘솔 출력)

---

**작성일**: 2025-12-04
**마지막 업데이트**: 2025-12-04
