# 자동매매 플랫폼 - 사용자 프론트엔드

사용자용 프론트엔드 애플리케이션입니다.

## 🚀 실행 방법

```bash
# 의존성 설치
npm install

# 개발 서버 시작 (포트 3000)
npm run dev

# 프로덕션 빌드
npm run build
```

## 📁 프로젝트 구조

```
frontend/
├── src/
│   ├── api/           # API 클라이언트
│   │   ├── client.js  # Axios 인스턴스
│   │   └── auth.js    # 인증 API
│   ├── context/       # React Context
│   │   └── AuthContext.jsx
│   ├── pages/         # 페이지 컴포넌트
│   │   ├── Login.jsx
│   │   └── Dashboard.jsx
│   └── App.jsx        # 메인 App
├── vite.config.js     # Vite 설정
└── .env               # 환경 변수
```

## 🌐 포트

- **사용자 프론트엔드**: http://localhost:3000
- **관리자 페이지**: http://localhost:3001
- **백엔드 API**: http://localhost:8000

## 🔐 테스트 계정

### 일반 사용자
- 회원가입 후 사용

### 관리자
- 이메일: admin@admin.com
- 비밀번호: admin123
- **접속**: http://localhost:3001 (관리자 페이지)

## ⚙️ 환경 변수

`.env` 파일:
```
VITE_API_URL=http://localhost:8000
```

## 📝 주요 기능

- 로그인/로그아웃
- JWT 토큰 기반 인증
- 보호된 라우트
- API 클라이언트 자동 토큰 주입

## 🔧 기술 스택

- React 18
- Vite
- React Router v6
- Axios
- Context API
