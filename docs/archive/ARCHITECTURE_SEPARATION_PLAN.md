# 프론트엔드 완전 분리 아키텍처

## 🎯 목표
일반 유저 페이지와 관리자 페이지를 **완전히 물리적으로 분리**

---

## 📊 현재 구조 (문제)

```
auto-dashboard/
├── backend/ (포트 8000)
│   └── 14개 admin API 엔드포인트
│
└── frontend/ (포트 3003)
    ├── /dashboard (일반 유저) ← MainLayout
    └── /admin (관리자) ← AdminLayout
```

**문제점**:
- ❌ 같은 서버에서 라우팅으로만 분리
- ❌ 물리적 분리 없음
- ❌ 코드 혼재 (일반 유저 + 관리자)
- ❌ 의존성 혼재
- ❌ 보안 위험 (같은 번들에 관리자 코드 포함)

---

## ✅ 새로운 구조 (해결)

```
auto-dashboard/
├── backend/ (포트 8000)
│   ├── /api/... (일반 유저 API)
│   └── /admin/... (관리자 API)
│
├── frontend/ (포트 3000) ⭐ 일반 유저 전용
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── LiveTrading.jsx
│   │   │   ├── Performance.jsx
│   │   │   └── Settings.jsx
│   │   ├── components/layout/
│   │   │   └── MainLayout.jsx (사이드바 있음)
│   │   └── App.jsx (관리자 라우트 없음)
│   └── vite.config.js (포트 3000)
│
└── admin-frontend/ (포트 4000) ⭐ 관리자 전용
    ├── src/
    │   ├── pages/
    │   │   └── AdminDashboard.jsx
    │   ├── components/layout/
    │   │   └── AdminLayout.jsx (사이드바 없음)
    │   └── App.jsx (관리자 라우트만)
    └── vite.config.js (포트 4000)
```

**장점**:
- ✅ **완전한 물리적 분리** (다른 포트, 다른 서버)
- ✅ **독립적인 빌드** (번들 분리)
- ✅ **보안 강화** (일반 유저 번들에 관리자 코드 없음)
- ✅ **명확한 책임 분리**
- ✅ **독립적인 배포 가능**
- ✅ **의존성 분리** (각각 필요한 패키지만)

---

## 🏗️ 구현 계획

### 1단계: admin-frontend 프로젝트 생성 ✅

```bash
# 1. 디렉토리 생성
mkdir admin-frontend
cd admin-frontend

# 2. Vite React 프로젝트 초기화
npm create vite@latest . -- --template react

# 3. 필요한 패키지 설치
npm install axios lucide-react react-router-dom

# 4. 포트 변경 (vite.config.js)
# server.port: 4000
```

### 2단계: 관리자 코드 이동

**이동할 파일**:
```
frontend/src/ → admin-frontend/src/

이동:
- pages/AdminDashboard.jsx
- pages/AdminDashboard.css
- components/layout/AdminLayout.jsx
- context/AuthContext.jsx (복사)
- api/client.js (복사)
```

**admin-frontend/src/App.jsx** (새로 작성):
```javascript
// 관리자 라우트만 포함
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/" element={
    <AdminProtectedRoute>
      <AdminDashboard />
    </AdminProtectedRoute>
  } />
</Routes>
```

### 3단계: frontend 정리 (일반 유저 전용)

**제거할 파일**:
```
frontend/src/
- pages/AdminDashboard.jsx ❌
- pages/AdminDashboard.css ❌
- components/layout/AdminLayout.jsx ❌
```

**frontend/src/App.jsx** 수정:
```javascript
// AdminProtectedRoute 제거
// /admin 라우트 제거
// AdminDashboard import 제거
```

**frontend/src/components/layout/MainLayout.jsx** 수정:
```javascript
// 사이드바에서 "관리자" 메뉴 아이템 제거
// role !== 'admin' 체크 제거
```

### 4단계: 독립 실행

**일반 유저 서버**:
```bash
cd frontend
npm run dev
# → http://localhost:3000
```

**관리자 서버**:
```bash
cd admin-frontend
npm run dev
# → http://localhost:4000
```

---

## 🔧 파일별 상세 변경

### admin-frontend/vite.config.js
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 4000,  // ⭐ 관리자 전용 포트
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

### admin-frontend/src/App.jsx
```javascript
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AdminLayout from './components/layout/AdminLayout';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';

function AdminProtectedRoute({ children }) {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" />;
  if (user?.role !== 'admin') return <div>Access Denied</div>;

  return <AdminLayout>{children}</AdminLayout>;
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <AdminProtectedRoute>
              <AdminDashboard />
            </AdminProtectedRoute>
          } />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
```

### frontend/vite.config.js
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,  // ⭐ 일반 유저 전용 포트
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
```

### frontend/src/App.jsx (수정)
```javascript
// AdminProtectedRoute 제거
// AdminLayout import 제거
// AdminDashboard import 제거
// /admin 라우트 제거

// 일반 유저 라우트만 유지
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/dashboard" element={
    <ProtectedRoute><Dashboard /></ProtectedRoute>
  } />
  <Route path="/live-trading" element={
    <ProtectedRoute><LiveTrading /></ProtectedRoute>
  } />
  {/* ... 기타 일반 유저 라우트 ... */}
</Routes>
```

---

## 🚀 실행 방법

### 백엔드 (1개 서버)
```bash
cd backend
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="
python -m uvicorn src.main:app --reload

# ✅ http://localhost:8000
```

### 일반 유저 프론트엔드
```bash
cd frontend
npm run dev

# ✅ http://localhost:3000
```

### 관리자 프론트엔드
```bash
cd admin-frontend
npm run dev

# ✅ http://localhost:4000
```

---

## 🎯 접속 방법

### 일반 유저
1. http://localhost:3000 접속
2. 로그인 (일반 계정)
3. 대시보드 사용
4. ❌ /admin 라우트 없음 (404)

### 관리자
1. http://localhost:4000 접속
2. 로그인 (관리자 계정)
3. 관리자 대시보드 사용
4. ❌ /dashboard, /live-trading 등 없음 (404)

---

## 🔒 보안 강화

### 1. 번들 분리
- 일반 유저 번들에 관리자 코드 포함 안 됨
- 관리자 번들에 일반 유저 코드 포함 안 됨

### 2. 네트워크 분리
- 다른 포트로 완전 분리
- 프로덕션 환경에서 다른 도메인 사용 가능
  - 일반 유저: `https://app.yourdomain.com`
  - 관리자: `https://admin.yourdomain.com`

### 3. 인증 분리
- 각각 독립적인 AuthContext
- 관리자는 role 체크 필수

---

## 📦 배포 시나리오

### Docker Compose 예시
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"

  user-frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://backend:8000

  admin-frontend:
    build: ./admin-frontend
    ports:
      - "4000:80"
    environment:
      - VITE_API_URL=http://backend:8000
```

### Nginx 리버스 프록시 예시
```nginx
# 일반 유저
server {
    listen 80;
    server_name app.yourdomain.com;
    location / {
        proxy_pass http://localhost:3000;
    }
}

# 관리자
server {
    listen 80;
    server_name admin.yourdomain.com;
    location / {
        proxy_pass http://localhost:4000;
    }
}
```

---

## ✅ 검증 방법

### 1. 포트 분리 확인
```bash
lsof -i :3000  # 일반 유저 프론트엔드
lsof -i :4000  # 관리자 프론트엔드
lsof -i :8000  # 백엔드
```

### 2. 번들 분리 확인
```bash
# 일반 유저 번들에 AdminDashboard 없음
grep -r "AdminDashboard" frontend/dist/

# 관리자 번들에 MainLayout 없음
grep -r "MainLayout" admin-frontend/dist/
```

### 3. 라우트 분리 확인
- http://localhost:3000/admin → 404 (라우트 없음)
- http://localhost:4000/dashboard → 404 (라우트 없음)

---

## 🎉 완료 후 상태

```
✅ 백엔드: 1개 서버 (포트 8000)
✅ 일반 유저 프론트엔드: 독립 서버 (포트 3000)
✅ 관리자 프론트엔드: 독립 서버 (포트 4000)
✅ 완전한 물리적 분리
✅ 보안 강화
✅ 독립 배포 가능
```

---

**작성일**: 2025-12-04
**버전**: 2.0.0 - 완전 분리 아키텍처
