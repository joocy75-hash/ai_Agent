# 🛠️ 프론트엔드-백엔드 연결 문제 해결 가이드

## 📍 발견된 문제

### 근본 원인

프론트엔드 소스 코드에서 **하드코딩된 localhost:8000 URL**이 배포 환경에서도 그대로 사용되어 API 연결이 실패했습니다.

### 수정된 파일 목록 (총 8개)

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/api/analytics.js` | `const API_URL = import.meta.env.VITE_API_URL \|\| 'http://localhost:8000'` |
| `frontend/src/hooks/useWebSocket.js` | WebSocket URL을 환경변수 기반으로 변경 |
| `frontend/src/context/WebSocketContext.jsx` | WebSocket URL을 환경변수 기반으로 변경 |
| `frontend/src/components/dashboard/SystemStatus.jsx` | API_BASE_URL을 환경변수 기반으로 변경 |
| `frontend/src/components/dashboard/RecentTrades.jsx` | API_BASE_URL을 환경변수 기반으로 변경 |
| `frontend/src/components/dashboard/UrgentAlerts.jsx` | API_BASE_URL을 환경변수 기반으로 변경 |
| `frontend/src/components/alerts/AlertCenter.jsx` | API_BASE_URL을 환경변수 기반으로 변경 |
| `frontend/src/components/strategy/StrategyList.jsx` | fetch 호출 URL을 환경변수 기반으로 변경 |

---

## 🚀 배포 방법

### 방법 1: Docker Compose로 전체 재배포 (권장)

```bash
# 1. 서버에 SSH 접속
ssh root@158.247.245.197

# 2. 프로젝트 디렉토리로 이동
cd /root/auto-dashboard

# 3. 최신 코드 가져오기 (Git 사용시)
git pull origin main

# 또는 로컬에서 rsync로 업로드:
# rsync -avz --exclude 'node_modules' --exclude '.git' /Users/mr.joo/Desktop/auto-dashboard/ root@158.247.245.197:/root/auto-dashboard/

# 4. 프론트엔드 컨테이너만 재빌드 및 재시작
docker-compose stop frontend
docker-compose rm -f frontend
docker-compose build --no-cache frontend --build-arg VITE_API_URL=http://158.247.245.197:8000
docker-compose up -d frontend

# 5. 상태 확인
docker-compose ps
docker logs trading-frontend --tail 50
```

### 방법 2: 빌드된 파일 직접 교체 (빠름)

로컬에서 이미 빌드된 파일(`frontend/dist/`)을 서버로 직접 복사합니다:

```bash
# 1. 로컬에서 빌드된 파일 서버로 복사
scp -r /Users/mr.joo/Desktop/auto-dashboard/frontend/dist/* root@158.247.245.197:/tmp/frontend_dist/

# 2. 서버에 SSH 접속
ssh root@158.247.245.197

# 3. nginx 컨테이너 내부로 파일 복사
docker cp /tmp/frontend_dist/. trading-frontend:/usr/share/nginx/html/

# 4. 프론트엔드 컨테이너 재시작
docker restart trading-frontend

# 5. 캐시 무효화 확인 (선택사항)
docker exec trading-frontend nginx -s reload
```

### 방법 3: 전체 재빌드

```bash
# 서버에서
ssh root@158.247.245.197
cd /root/auto-dashboard

# 모든 컨테이너 중지 및 재빌드
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 관리자 계정 생성 (필요한 경우)
docker exec trading-backend python -m src.scripts.create_admin_user
```

---

## ✅ 배포 후 확인 사항

### 1. API URL 확인

```bash
# 배포된 JavaScript 파일에서 API URL 확인
curl -s http://158.247.245.197:3000/assets/index-*.js | grep -o 'http://158.247.245.197:8000' | head -1
# 출력: http://158.247.245.197:8000 ← 정상
```

### 2. 로그인 테스트

```bash
curl -X POST http://158.247.245.197:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'
```

### 3. 브라우저 테스트

1. <http://158.247.245.197:3000> 접속
2. F12 (개발자 도구) → Network 탭 열기
3. 로그인 버튼 클릭
4. `/auth/login` 요청이 `158.247.245.197:8000`으로 가는지 확인
5. "연결 끊김" 표시가 사라지는지 확인

---

## 📝 로컬 빌드 완료 정보

**빌드된 파일 위치:**

```
/Users/mr.joo/Desktop/auto-dashboard/frontend/dist/
├── index.html
└── assets/
    ├── index-CAwxcKLK.css
    └── index-4kSn6C9m.js
```

**빌드 환경변수:**

```
VITE_API_URL=http://158.247.245.197:8000
```

---

## 🔑 로그인 정보

관리자 계정이 생성되지 않았다면 먼저 생성해야 합니다:

```bash
ssh root@158.247.245.197 "docker exec trading-backend python -m src.scripts.create_admin_user"
```

**로그인 정보:**

- 이메일: `admin@admin.com`
- 비밀번호: `Admin123!`

---

작성일: 2025-12-06
작성자: Claude Code Assistant
