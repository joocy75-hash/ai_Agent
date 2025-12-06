# 관리자 대시보드 - 빠른 참조

> **상태**: ✅ 100% 완료 (프로덕션 준비 완료)
> **최종 업데이트**: 2025-12-04

---

## 🚀 빠른 시작

### 1. 서버 실행

```bash
# 백엔드 (터미널 1)
cd backend
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
python3.11 -m uvicorn src.main:app --reload

# 프론트엔드 (터미널 2)
cd frontend
npm run dev
```

### 2. 관리자 페이지 접속

1. http://localhost:3003/login 로그인
2. http://localhost:3003/admin 관리자 대시보드

---

## 📊 구현된 기능

### 백엔드 API (14개)
- ✅ 봇 제어 (5개): 활성 봇 조회, 통계, 정지, 재시작, 긴급 정지
- ✅ 계정 제어 (3개): 정지, 활성화, 강제 로그아웃
- ✅ 글로벌 통계 (3개): 시스템 통계, 위험 사용자, 거래량
- ✅ 로그 조회 (3개): 시스템, 봇, 거래 로그

### 프론트엔드
- ✅ 관리자 전용 독립 레이아웃 (사이드바 없음)
- ✅ Overview Tab: 실시간 시스템 통계
- ✅ Bots Tab: 봇 모니터링 및 제어
- ✅ 30초 자동 갱신
- ✅ 권한 관리 (관리자만 접근 가능)

---

## 📁 주요 파일

```
backend/src/api/
├── admin_bots.py       # 봇 제어 API
├── admin_users.py      # 계정 제어 API
├── admin_analytics.py  # 글로벌 통계 API
└── admin_logs.py       # 로그 조회 API

frontend/src/
├── pages/
│   ├── AdminDashboard.jsx      # 관리자 대시보드
│   └── AdminDashboard.css      # 전용 스타일
├── components/layout/
│   └── AdminLayout.jsx         # 관리자 레이아웃
└── App.jsx                     # 라우팅 (AdminProtectedRoute)
```

---

## 🧪 테스트

```bash
# 모든 관리자 API 테스트
./test_admin_bots_api.sh
./test_admin_users_api.sh
./test_admin_analytics_api.sh
./test_admin_logs_api.sh
```

---

## 📚 상세 문서

| 문서 | 내용 |
|------|------|
| [ADMIN_FINAL_HANDOVER.md](ADMIN_FINAL_HANDOVER.md) | **⭐ 필독!** 전체 인수인계 문서 |
| [ADMIN_API_PROGRESS.md](ADMIN_API_PROGRESS.md) | API 진행 상황 및 테스트 결과 |
| [ADMIN_IMPLEMENTATION_COMPLETE.md](ADMIN_IMPLEMENTATION_COMPLETE.md) | 구현 완료 보고서 |
| [ADMIN_QUICK_START.md](ADMIN_QUICK_START.md) | 빠른 시작 가이드 |

---

## ⚠️ 해결된 주요 이슈

1. ✅ **사이드바 겹침 문제**: AdminLayout으로 완전 분리
2. ✅ **Tailwind CSS 미설치**: 일반 CSS로 변환
3. ✅ **lucide-react 누락**: 패키지 설치 완료
4. ✅ **API import 경로 오류**: client.js로 수정

---

## 🔜 다음 단계 (선택 사항)

1. **Users Management Tab** (우선순위 1) - 4-6시간
   - 사용자 목록 테이블
   - 계정 정지/활성화 UI
   - 검색 및 필터링

2. **Logs Query Tab** (우선순위 2) - 6-8시간
   - 로그 타입 선택
   - 필터링 및 페이지네이션
   - 로그 상세 보기

3. **차트 시각화** (우선순위 3) - 4-6시간
   - 거래량 라인 차트
   - P&L 트렌드
   - 사용자 증가 차트

---

## 🆘 문제 발생 시

1. **관리자 페이지 접근 불가**
   ```sql
   -- 사용자 역할 확인 및 변경
   sqlite3 backend/trading.db "UPDATE users SET role='admin' WHERE email='admin@admin.com';"
   ```

2. **JWT 토큰 만료**
   ```bash
   # 새 토큰 발급
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@admin.com","password":"your_password"}'
   ```

3. **기타 문제**
   - [ADMIN_FINAL_HANDOVER.md](ADMIN_FINAL_HANDOVER.md)의 "문제 해결 가이드" 섹션 참조

---

**작성**: 2025-12-04 | **상태**: ✅ 완료
