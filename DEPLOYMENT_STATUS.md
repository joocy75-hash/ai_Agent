# 🚀 배포 현황 및 문제 해결 인수인계 문서

작성일: 2025-12-06
프로젝트: Deep Signal Auto Trading Dashboard

---

## 📍 배포 서버 정보

### 서버 접속 정보
- **IP 주소**: 158.247.245.197
- **SSH 계정**: root
- **프로젝트 경로**: `/root/auto-dashboard` (예상)

### 서비스 URL
| 서비스 | URL | 상태 |
|--------|-----|------|
| 프론트엔드 (사용자) | http://158.247.245.197:3000 | ✅ 실행 중 |
| 관리자 프론트엔드 | http://158.247.245.197:4000 | ❓ 미확인 |
| 백엔드 API | http://158.247.245.197:8000 | ✅ 실행 중 |
| API 문서 | http://158.247.245.197:8000/docs | ✅ 접근 가능 |

---

## ✅ 정상 작동 중인 부분

### 1. 백엔드 서버
```bash
# 상태: 정상 실행 중
# 확인: curl http://158.247.245.197:8000/health
```

**응답:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-06T09:05:07.169561",
  "uptime_seconds": 2024,
  "uptime_human": "33m 44s",
  "version": "1.0.0",
  "environment": "production"
}
```

### 2. 프론트엔드 서버
```bash
# 상태: 정상 실행 중
# 확인: curl -I http://158.247.245.197:3000
```

**응답:**
```
HTTP/1.1 200 OK
Server: nginx/1.29.3
```

### 3. 프론트엔드-백엔드 연결 설정
- ✅ **API URL**: 올바르게 설정됨 (`http://158.247.245.197:8000`)
- ✅ **CORS**: 정상 설정됨
- ✅ **네트워크 통신**: 정상

**확인 결과:**
```bash
# JavaScript 번들에서 API URL 확인
curl -s http://158.247.245.197:3000/assets/index-*.js | grep -o 'http://[^"]*:8000'
# 출력: http://158.247.245.197:8000 ← 정상
```

---

## ❌ 현재 발생 중인 문제

### 🔴 주요 문제: 로그인 불가 (관리자 계정 없음)

#### 증상
- 사용자가 http://158.247.245.197:3000 접속
- 로그인 시도 시 "연결 안됨" 또는 인증 실패 메시지
- 회원가입도 500 에러 발생

#### 원인
**배포 서버의 PostgreSQL 데이터베이스에 관리자 계정이 생성되지 않음**

#### 로그인 API 테스트 결과
```bash
# 테스트 명령어
curl -X POST http://158.247.245.197:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'
```

**현재 응답:**
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid email or password",
    "details": {},
    "timestamp": "2025-12-06T09:05:07.345502",
    "request_id": null
  }
}
```

---

## 🔧 해결 방법 (3가지 옵션)

### 방법 1: 자동 스크립트 실행 (가장 빠름)

프로젝트 루트에 `fix-deployment-login.sh` 스크립트가 준비되어 있습니다.

```bash
# 로컬에서 실행 (SSH 비밀번호 필요)
cd /Users/mr.joo/Desktop/auto-dashboard
chmod +x fix-deployment-login.sh
./fix-deployment-login.sh
```

**스크립트가 수행하는 작업:**
1. 서버 연결 확인
2. Docker 컨테이너 상태 확인
3. 관리자 계정 자동 생성
4. 로그인 테스트
5. 로그 확인

---

### 방법 2: SSH로 직접 해결 (수동, 권장)

```bash
# 1. 서버 접속
ssh root@158.247.245.197

# 2. Docker 컨테이너 확인
docker ps

# 다음 컨테이너들이 실행 중이어야 함:
# - trading-backend
# - trading-frontend
# - trading-postgres
# - trading-redis

# 3. 관리자 계정 생성
docker exec trading-backend python -m src.scripts.create_admin_user

# 예상 출력:
# 🔧 Initializing database...
# ✅ Database initialized
# 👤 Creating admin user...
# ✅ Admin user created successfully!
#    Email: admin@admin.com
#    Password: Admin123!
#    Role: admin

# 4. 로그인 테스트
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'

# 성공 시 access_token이 포함된 응답 반환됨

# 5. 서버에서 나가기
exit
```

---

### 방법 3: 컨테이너가 실행되지 않는 경우

```bash
# SSH 접속 후
ssh root@158.247.245.197

# 프로젝트 디렉토리로 이동 (경로는 실제 위치에 맞게 조정)
cd /root/auto-dashboard

# .env.production 파일 확인
cat .env.production

# 필수 환경 변수가 있는지 확인:
# - POSTGRES_PASSWORD
# - ENCRYPTION_KEY
# - JWT_SECRET
# - VITE_API_URL=http://158.247.245.197:8000

# Docker Compose로 모든 서비스 시작
docker-compose --env-file .env.production up -d

# 로그 확인 (서비스 시작까지 1-2분 소요)
docker-compose --env-file .env.production logs -f

# Ctrl+C로 로그 종료 후 관리자 계정 생성
docker exec trading-backend python -m src.scripts.create_admin_user
```

---

## 📊 진단 스크립트 사용

상세한 진단이 필요한 경우 `debug-deployment.sh` 스크립트를 실행하세요:

```bash
cd /Users/mr.joo/Desktop/auto-dashboard
chmod +x debug-deployment.sh
./debug-deployment.sh
```

**스크립트가 확인하는 항목:**
1. ✅ 백엔드 API 상태
2. ✅ 프론트엔드 접속 가능 여부
3. ✅ 로그인 API 동작 여부
4. ✅ CORS 헤더 설정
5. ✅ 프론트엔드가 사용하는 API URL

---

## 🔐 로그인 정보

관리자 계정 생성 후 사용할 로그인 정보:

```
이메일:    admin@admin.com
비밀번호:  Admin123!
역할:      관리자 (admin)
```

**⚠️ 보안 주의사항:**
- 첫 로그인 후 즉시 비밀번호 변경 필요
- 설정(Settings) 페이지에서 비밀번호 변경 가능

---

## 🗄️ 데이터베이스 정보

### 로컬 환경 (개발)
- **종류**: SQLite
- **파일**: `/Users/mr.joo/Desktop/auto-dashboard/backend/trading.db`
- **상태**: ✅ 관리자 계정 있음 (admin@admin.com / Admin123!)

### 배포 환경 (프로덕션)
- **종류**: PostgreSQL
- **컨테이너**: trading-postgres
- **데이터베이스**: trading_prod
- **사용자**: trading_user
- **상태**: ❌ 관리자 계정 없음 → **생성 필요**

**PostgreSQL 직접 접속:**
```bash
# 서버에서
docker exec -it trading-postgres psql -U trading_user -d trading_prod

# 사용자 확인
SELECT id, email, name, role FROM users;

# 종료
\q
```

---

## 🐳 Docker 구성

### 실행 중인 컨테이너

```bash
# 확인 명령어
docker ps

# 예상 출력:
# CONTAINER ID   IMAGE                    PORTS                    NAMES
# xxxxxxxxx      auto-dashboard-backend   0.0.0.0:8000->8000/tcp   trading-backend
# xxxxxxxxx      auto-dashboard-frontend  0.0.0.0:3000->3000/tcp   trading-frontend
# xxxxxxxxx      postgres:15-alpine       0.0.0.0:5432->5432/tcp   trading-postgres
# xxxxxxxxx      redis:7-alpine           0.0.0.0:6379->6379/tcp   trading-redis
```

### 컨테이너 로그 확인

```bash
# 백엔드 로그
docker logs trading-backend --tail 50

# 프론트엔드 로그
docker logs trading-frontend --tail 50

# PostgreSQL 로그
docker logs trading-postgres --tail 50

# 실시간 로그 모니터링
docker logs -f trading-backend
```

---

## 🔄 환경 변수 설정

### 로컬 개발 환경

**파일**: `/Users/mr.joo/Desktop/auto-dashboard/frontend/.env`
```env
VITE_API_URL=http://localhost:8000
```

**백엔드 환경 변수** (터미널에서 export로 설정):
```env
DATABASE_URL=sqlite+aiosqlite:///./trading.db
ENCRYPTION_KEY=Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=
```

### 배포 환경

**파일**: `/root/auto-dashboard/.env.production` (서버에 있어야 함)
```env
# PostgreSQL
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=TradingBot2024!SecurePassword
POSTGRES_DB=trading_prod

# Redis
REDIS_PASSWORD=Redis2024!SecurePassword

# Backend Security
ENCRYPTION_KEY=Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=
JWT_SECRET=super-secret-jwt-key-change-this-in-production-2024

# Frontend API URL (중요!)
VITE_API_URL=http://158.247.245.197:8000

# CORS Origins
ALLOWED_ORIGINS=http://158.247.245.197:3000,http://158.247.245.197:4000,http://158.247.245.197

# Database URL for backend
DATABASE_URL=postgresql+asyncpg://trading_user:TradingBot2024!SecurePassword@postgres:5432/trading_prod

# Logging
LOG_LEVEL=INFO
```

---

## 📝 관련 스크립트 및 문서

프로젝트 루트에 다음 파일들이 준비되어 있습니다:

| 파일명 | 용도 | 사용 시기 |
|--------|------|-----------|
| `fix-deployment-login.sh` | 로그인 문제 자동 해결 | SSH 접근 가능 시 |
| `debug-deployment.sh` | 배포 서버 진단 | 문제 원인 파악 필요 시 |
| `deploy-to-server.sh` | 전체 배포 자동화 | 처음 배포 또는 재배포 시 |
| `DEPLOYMENT_MANUAL_STEPS.md` | 수동 배포 가이드 | 단계별 배포 필요 시 |
| `DEPLOYMENT_QUICK_START.md` | 빠른 배포 가이드 | 빠르게 배포할 때 |
| `LOGIN_PROBLEM_SOLUTION.md` | 로그인 문제 해결 가이드 | 로그인 실패 시 |
| `fix-frontend-connection.md` | 프론트엔드 연결 문제 해결 | API 연결 실패 시 |

---

## 🧪 테스트 절차

### 1. 백엔드 헬스 체크
```bash
curl http://158.247.245.197:8000/health
```

**예상 결과:** `{"status":"healthy",...}`

### 2. 로그인 API 테스트
```bash
curl -X POST http://158.247.245.197:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'
```

**성공 시:** `{"success":true,"data":{"access_token":"eyJ..."}}`
**실패 시:** `{"success":false,"error":{"code":"AUTHENTICATION_ERROR"}}`

### 3. 웹 브라우저 테스트
1. http://158.247.245.197:3000 접속
2. 로그인 버튼 클릭
3. 이메일: `admin@admin.com`, 비밀번호: `Admin123!` 입력
4. 로그인 클릭
5. 대시보드로 이동하면 성공

### 4. 브라우저 개발자 도구 확인
1. F12 누르기
2. Network 탭 선택
3. 로그인 시도
4. `/auth/login` 요청 확인
5. Request URL이 `http://158.247.245.197:8000/auth/login`인지 확인

---

## 🚨 문제 해결 체크리스트

### 관리자 계정 생성 전
- [ ] 서버 SSH 접속 가능
- [ ] Docker 설치됨
- [ ] Docker Compose 설치됨
- [ ] 모든 컨테이너 실행 중 (`docker ps` 확인)
- [ ] PostgreSQL 컨테이너 정상 작동
- [ ] 백엔드 헬스 체크 성공

### 관리자 계정 생성 후
- [ ] 관리자 계정 생성 스크립트 성공
- [ ] 로그인 API 테스트 성공 (access_token 반환)
- [ ] 웹 브라우저에서 로그인 성공
- [ ] 대시보드 접근 가능
- [ ] API 키 설정 가능
- [ ] 봇 설정 가능

---

## 🔍 문제별 해결 가이드

### 문제 1: "docker: command not found"
```bash
# Docker가 설치되지 않음
# 서버에 Docker 설치 필요
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

### 문제 2: "Error: No such container: trading-backend"
```bash
# 컨테이너가 실행되지 않음
cd /root/auto-dashboard
docker-compose --env-file .env.production up -d
```

### 문제 3: "ModuleNotFoundError"
```bash
# create_admin_user.py 스크립트 오류
# 최신 버전으로 업데이트 필요

# 로컬의 수정된 파일을 서버로 복사:
scp /Users/mr.joo/Desktop/auto-dashboard/backend/src/scripts/create_admin_user.py \
    root@158.247.245.197:/root/auto-dashboard/backend/src/scripts/

# 백엔드 컨테이너 재시작
ssh root@158.247.245.197
cd /root/auto-dashboard
docker-compose --env-file .env.production restart backend
```

### 문제 4: "회원가입 500 에러"
```bash
# 데이터베이스 연결 또는 환경 변수 문제
# 백엔드 로그 확인
docker logs trading-backend --tail 100

# 환경 변수 확인
docker exec trading-backend env | grep -E "DATABASE|ENCRYPTION|JWT"
```

---

## 📞 긴급 문제 발생 시

### 즉시 확인할 사항

1. **서버 접속 가능 여부**
   ```bash
   ping 158.247.245.197
   ssh root@158.247.245.197 "echo 'Connection OK'"
   ```

2. **컨테이너 상태**
   ```bash
   ssh root@158.247.245.197 "docker ps -a"
   ```

3. **포트 오픈 여부**
   ```bash
   nc -zv 158.247.245.197 8000  # 백엔드
   nc -zv 158.247.245.197 3000  # 프론트엔드
   ```

4. **로그 수집**
   ```bash
   ssh root@158.247.245.197 "docker logs trading-backend" > backend.log
   ssh root@158.247.245.197 "docker logs trading-postgres" > postgres.log
   ```

---

## 🎯 최종 목표 상태

배포가 완료되면 다음 상태가 되어야 합니다:

✅ http://158.247.245.197:3000 → 프론트엔드 정상 접속
✅ http://158.247.245.197:8000 → 백엔드 API 정상 동작
✅ 로그인 성공 (admin@admin.com / Admin123!)
✅ 대시보드 접근 가능
✅ API 키 설정 가능
✅ 봇 생성 및 실행 가능
✅ 백테스트 실행 가능

---

## 📌 요약

### 현재 상태
- ✅ 서버 실행 중
- ✅ 프론트엔드-백엔드 연결 정상
- ❌ 관리자 계정 없음 → **로그인 불가**

### 해결 방법 (한 줄)
```bash
ssh root@158.247.245.197 "docker exec trading-backend python -m src.scripts.create_admin_user"
```

### 로그인 정보
- 이메일: `admin@admin.com`
- 비밀번호: `Admin123!`

---

**작성자**: Claude Code Assistant
**마지막 업데이트**: 2025-12-06
**다음 작업자에게**: 위의 해결 방법 중 하나를 선택하여 관리자 계정을 생성하면 모든 문제가 해결됩니다.
