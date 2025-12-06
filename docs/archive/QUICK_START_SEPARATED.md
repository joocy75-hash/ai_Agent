# 🚀 빠른 시작 가이드 (완전 분리 버전)

## 📊 시스템 구조

```
✅ 백엔드: http://localhost:8000
✅ 일반 유저: http://localhost:3000
✅ 관리자: http://localhost:4000
```

---

## 1️⃣ 백엔드 서버 실행

```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 -m uvicorn src.main:app --reload
```

**확인**: http://localhost:8000/docs

---

## 2️⃣ 일반 유저 프론트엔드 실행

```bash
cd /Users/mr.joo/Desktop/auto-dashboard/frontend
npm run dev
```

**확인**: http://localhost:3000

**로그인**:
- Email: `user@example.com`
- Password: (일반 사용자 비밀번호)

**사용 가능한 페이지**:
- /dashboard
- /live-trading
- /performance
- /strategy
- /bot
- /charts
- /history
- /alerts
- /settings

---

## 3️⃣ 관리자 프론트엔드 실행

```bash
cd /Users/mr.joo/Desktop/auto-dashboard/admin-frontend
npm run dev
```

**확인**: http://localhost:4000

**로그인**:
- Email: `admin@admin.com`
- Password: (관리자 비밀번호)

**관리자 대시보드 기능**:
- 전체 개요 (전체 사용자, 봇 통계, AUM, P&L)
- 봇 관리 (개별 정지/재시작, 전체 긴급 정지)
- 사용자 관리 (준비 중)
- 로그 조회 (준비 중)

---

## 🔍 포트 확인

```bash
# 모든 서버가 실행 중인지 확인
lsof -i :8000  # 백엔드
lsof -i :3000  # 일반 유저
lsof -i :4000  # 관리자
```

---

## 🎯 접속 방법

### 일반 유저
1. **브라우저에서** http://localhost:3000 접속
2. 일반 계정으로 로그인
3. 대시보드 사용

### 관리자
1. **브라우저에서** http://localhost:4000 접속
2. 관리자 계정으로 로그인 (admin@admin.com)
3. 관리자 대시보드 사용

---

## ❌ 혼동 주의

### 잘못된 접속 방법
- ❌ http://localhost:3000/admin → 404 (라우트 없음)
- ❌ http://localhost:4000/dashboard → 404 (라우트 없음)

### 올바른 접속 방법
- ✅ 일반 유저: http://localhost:3000
- ✅ 관리자: http://localhost:4000

---

## 🛑 서버 종료

```bash
# 포트별로 종료
lsof -ti :8000 | xargs kill -9  # 백엔드
lsof -ti :3000 | xargs kill -9  # 일반 유저
lsof -ti :4000 | xargs kill -9  # 관리자
```

---

## 🔧 문제 해결

### 포트가 이미 사용 중일 때
```bash
# 포트 확인 및 종료
lsof -i :3000
kill -9 <PID>

lsof -i :4000
kill -9 <PID>
```

### npm 의존성 오류
```bash
# frontend 재설치
cd frontend
rm -rf node_modules package-lock.json
npm install

# admin-frontend 재설치
cd admin-frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 📚 상세 문서

- [SEPARATION_COMPLETE.md](SEPARATION_COMPLETE.md) - 완전 분리 완료 문서
- [ARCHITECTURE_SEPARATION_PLAN.md](ARCHITECTURE_SEPARATION_PLAN.md) - 아키텍처 설계
- [ADMIN_FINAL_HANDOVER.md](ADMIN_FINAL_HANDOVER.md) - 관리자 기능 인수인계

---

**작성일**: 2025-12-04
