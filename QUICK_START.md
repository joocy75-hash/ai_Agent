# ⚡ Quick Start Guide

> **Auto Trading Dashboard - 빠른 시작 가이드**
>
> 이 문서는 프로젝트를 5분 안에 시작할 수 있도록 돕습니다.

---

## 📋 사전 준비

필요한 소프트웨어:
- ✅ Python 3.11
- ✅ Node.js 18+ 및 npm
- ✅ Git

---

## 🚀 1단계: 서버 시작 (3개 터미널)

### 터미널 1: 백엔드 서버
```bash
cd /Users/mr.joo/Desktop/auto-dashboard/backend

# 환경 변수 설정
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="

# 서버 실행
python3.11 -m uvicorn src.main:app --reload
```

**확인**: http://localhost:8000/docs 접속 → API 문서 표시

---

### 터미널 2: 일반 사용자 프론트엔드
```bash
cd /Users/mr.joo/Desktop/auto-dashboard/frontend

# 서버 실행
npm run dev
```

**확인**: http://localhost:3000 접속 → 로그인 페이지 표시

---

### 터미널 3: 관리자 프론트엔드
```bash
cd /Users/mr.joo/Desktop/auto-dashboard/admin-frontend

# 서버 실행
npm run dev
```

**확인**: http://localhost:4000 접속 → 관리자 로그인 페이지 표시

---

## 👤 2단계: 로그인

### 일반 사용자 (http://localhost:3000)
- 이메일: `admin@admin.com`
- 비밀번호: `admin123`

### 관리자 (http://localhost:4000)
- 이메일: `admin@admin.com`
- 비밀번호: `admin123`

---

## 🎯 3단계: 기능 테스트

### 일반 사용자 대시보드
1. **Dashboard** - 계정 잔고 및 포지션 확인
2. **Settings** - API 키 등록 (Bitget API 키 필요)
3. **Bot Control** - 봇 시작/정지
4. **Live Trading** - 실시간 거래 모니터링

### 관리자 대시보드
1. **Overview** - 전체 통계 확인
2. **Bots** - 모든 봇 상태 관리
3. **Users** - 사용자 관리
4. **Logs** - 시스템 로그 조회

---

## 🔧 문제 해결

### 백엔드 서버가 시작되지 않을 때
```bash
# Python 버전 확인
python3.11 --version

# 패키지 재설치
cd backend
pip3 install -r requirements.txt

# DB 마이그레이션 확인
alembic current
alembic upgrade head
```

### 프론트엔드가 시작되지 않을 때
```bash
# Node 버전 확인
node --version
npm --version

# 패키지 재설치
cd frontend  # 또는 admin-frontend
rm -rf node_modules package-lock.json
npm install
```

### CORS 에러가 발생할 때
- `backend/src/main.py` 파일에서 CORS 설정 확인
- 현재 설정: `http://localhost:3000`, `http://localhost:4000` 허용

### API 키 조회 한도 초과
- 시간당 3회 제한
- 1시간 후 다시 시도하거나 백엔드 재시작

---

## 📚 다음 단계

### 상세 문서 읽기
1. [HANDOVER_FINAL.md](HANDOVER_FINAL.md) - 전체 인수인계 문서 ⭐
2. [PROJECT_COMPLETION_SUMMARY.md](PROJECT_COMPLETION_SUMMARY.md) - 완료 요약
3. [REMAINING_TASKS.md](REMAINING_TASKS.md) - 작업 상세 가이드

### 개발 시작
- API 문서: http://localhost:8000/docs
- 코드 구조: `HANDOVER_FINAL.md` 참조
- 디버깅: Chrome DevTools (F12)

---

## ⚙️ 환경 변수 (참고)

### 백엔드 (`backend/.env`)
```bash
DATABASE_URL=sqlite+aiosqlite:///./trading.db
ENCRYPTION_KEY=Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=
SECRET_KEY=your-secret-key-here
```

### 프론트엔드 (`.env` 불필요)
- API URL은 코드에 하드코딩: `http://localhost:8000`

---

## 🎯 주요 포트

| 서비스 | 포트 | URL |
|--------|------|-----|
| 백엔드 API | 8000 | http://localhost:8000 |
| API 문서 | 8000 | http://localhost:8000/docs |
| 일반 사용자 | 3000 | http://localhost:3000 |
| 관리자 | 4000 | http://localhost:4000 |

---

## ✅ 체크리스트

시작 전 확인사항:
- [ ] Python 3.11 설치 확인
- [ ] Node.js 18+ 설치 확인
- [ ] 백엔드 서버 실행 (포트 8000)
- [ ] 일반 사용자 프론트엔드 실행 (포트 3000)
- [ ] 관리자 프론트엔드 실행 (포트 4000)
- [ ] 로그인 테스트 완료
- [ ] API 통신 정상 작동 확인

---

> **작성일**: 2025-12-04
> **도움이 필요하면**: [HANDOVER_FINAL.md](HANDOVER_FINAL.md) 참조

**즐거운 개발 되세요! 🚀**
