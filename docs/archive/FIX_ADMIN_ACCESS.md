# 관리자 페이지 접속 문제 해결 가이드

## 🚨 문제: /admin 접속 시 일반 대시보드로 이동

---

## ✅ 해결 방법 (순서대로 따라하기)

### 1단계: 백엔드 서버 완전히 재시작

```bash
# 기존 서버 완전 종료
lsof -ti:8000 | xargs kill -9

# 백엔드 재시작
cd /Users/mr.joo/Desktop/auto-dashboard/backend
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 -m uvicorn src.main:app --reload
```

**확인**: 터미널에 "Application startup complete" 메시지 표시

---

### 2단계: 브라우저 localStorage 완전히 초기화

1. http://localhost:3003 접속
2. **F12** 눌러서 개발자 도구 열기
3. **Console** 탭으로 이동
4. 다음 명령어 **복사해서 붙여넣고 Enter**:

```javascript
localStorage.clear();
console.log('✅ localStorage cleared!');
console.log('현재 저장된 항목:', Object.keys(localStorage));
```

5. 출력에 `현재 저장된 항목: []` 표시 확인

---

### 3단계: 페이지 새로고침 (하드 리프레시)

- **Mac**: `Cmd + Shift + R`
- **Windows**: `Ctrl + Shift + R`

또는 브라우저 주소창에서 새로고침 아이콘을 **우클릭** → "**캐시 비우기 및 강력 새로고침**"

---

### 4단계: 관리자 계정으로 로그인

1. 로그인 페이지로 자동 이동
2. 로그인:
   - Email: `admin@admin.com`
   - Password: (관리자 비밀번호)
3. 로그인 버튼 클릭

---

### 5단계: Console 로그 확인

로그인 성공 후 Console에 다음 로그가 표시되는지 확인:

```
[Auth] Login successful, user_id: 6 role: admin
```

**role이 "admin"으로 표시되는지 확인**

만약 `role: undefined` 또는 `role: null`이 표시되면:
- 1단계(백엔드 재시작)가 제대로 안 됨
- 백엔드 터미널에서 서버 종료 후 다시 시작

---

### 6단계: localStorage 확인

Console에 다음 명령어 입력:

```javascript
console.log('Token:', localStorage.getItem('token'));
console.log('UserRole:', localStorage.getItem('userRole'));
console.log('UserEmail:', localStorage.getItem('userEmail'));
```

**출력 예시 (정상)**:
```
Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
UserRole: admin
UserEmail: admin@admin.com
```

만약 `UserRole: null` 또는 `UserRole: user`가 표시되면:
- 2단계(localStorage 초기화)가 제대로 안 됨
- 다시 `localStorage.clear();` 실행 후 로그아웃/재로그인

---

### 7단계: /admin 접속

1. 주소창에 `http://localhost:3003/admin` 직접 입력
2. Console 로그 확인:

```
[AdminProtectedRoute] Debug: { loading: false, isAuthenticated: true, user: {...}, userRole: "admin", isAdmin: true }
[AdminProtectedRoute] User is admin, rendering AdminLayout
```

3. **AdminLayout이 렌더링되어야 함** (사이드바 없는 독립 레이아웃)

---

## 🔍 문제가 계속되면

### 디버깅 로그 확인

/admin 접속 시 Console에 표시되는 모든 로그를 복사해서 보여주세요:

```
[AdminProtectedRoute] Debug: ...
[AdminProtectedRoute] User is not admin, role: ... - redirecting to dashboard
```

특히 **userRole 값**이 무엇인지 확인이 중요합니다.

---

## 💡 문제 원인

### 케이스 1: role이 undefined
- JWT 토큰에 role 정보 없음
- **해결**: 백엔드 재시작 + 로그아웃/재로그인

### 케이스 2: role이 "user"
- DB에 role이 "admin"이 아님
- **해결**: DB 업데이트

```bash
sqlite3 backend/trading.db "UPDATE users SET role='admin' WHERE email='admin@admin.com';"
sqlite3 backend/trading.db "SELECT id, email, role FROM users WHERE email='admin@admin.com';"
```

### 케이스 3: 여전히 일반 대시보드로 이동
- 브라우저 캐시 문제
- **해결**: 시크릿 모드(Incognito)에서 테스트

```
1. 시크릿/프라이빗 브라우징 모드 열기
2. http://localhost:3003 접속
3. 관리자 로그인
4. /admin 접속
```

---

## ✅ 성공 확인 사항

### 관리자 페이지가 정상적으로 표시되면:

1. **헤더**:
   - 왼쪽에 "대시보드로" 버튼
   - 중앙에 "🤖 Auto Trading - 관리자" 타이틀
   - 오른쪽에 사용자 정보 + 로그아웃 버튼

2. **사이드바**: 없음 (완전히 사라짐)

3. **탭**:
   - 전체 개요 (Overview)
   - 봇 관리 (Bots)
   - 사용자 관리 (Users)
   - 로그 조회 (Logs)

4. **통계 카드 4개**:
   - 전체 사용자
   - 실행 중인 봇
   - 총 AUM
   - 총 P&L

---

## 📞 여전히 문제가 있으면

다음 정보를 알려주세요:

1. Console에 표시되는 로그 (전체)
2. `localStorage.getItem('userRole')` 결과
3. 백엔드 터미널 출력 (로그인 시)
4. 어느 단계에서 막혔는지

---

**작성일**: 2025-12-04
