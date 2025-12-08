# 🔧 로그인 문제 해결 가이드

## 📊 문제 진단 결과

### ✅ 정상 작동 항목
1. **백엔드 서버**: 정상 실행 중 (http://158.247.245.197:8000)
2. **프론트엔드 서버**: 정상 실행 중 (http://158.247.245.197:3000)
3. **API 응답**: 헬스 체크 정상

### ❌ 발견된 문제들

#### 1. **관리자 계정 미존재** (가장 중요!)
```
상태: 데이터베이스에 관리자 계정이 없음
원인: 배포 시 관리자 계정 생성 스크립트가 실행되지 않음
결과: 로그인 시도 시 "Invalid email or password" 에러 (401)
```

#### 2. **회원가입 기능 에러**
```
상태: 500 Internal Server Error
원인: 데이터베이스 연결 또는 환경 변수 문제
결과: 새로운 사용자 등록 불가
```

#### 3. **프론트엔드 테스트 계정 정보 불일치**
```
표시된 비밀번호: admin123 (잘못됨)
실제 비밀번호: Admin123! (올바름)
상태: ✅ 수정 완료
```

---

## 🚀 해결 방법

### 방법 1: 자동 수정 스크립트 사용 (권장)

```bash
# 스크립트에 실행 권한 부여
chmod +x fix-deployment-login.sh

# 스크립트 실행
./fix-deployment-login.sh
```

이 스크립트는 자동으로:
- ✅ 서버 연결 확인
- ✅ Docker 컨테이너 상태 확인
- ✅ 관리자 계정 생성
- ✅ 로그인 테스트
- ✅ 로그 확인

---

### 방법 2: 수동으로 문제 해결

#### Step 1: 서버에 SSH 접속

```bash
ssh root@158.247.245.197
```

#### Step 2: Docker 컨테이너 확인

```bash
# 실행 중인 컨테이너 확인
docker ps

# 다음 컨테이너들이 실행 중이어야 합니다:
# - trading-backend
# - trading-frontend
# - trading-admin-frontend (optional)
# - trading-postgres
# - trading-redis
```

만약 컨테이너가 실행되지 않는다면:

```bash
cd /root/auto-dashboard
docker-compose --env-file .env.production up -d
```

#### Step 3: 관리자 계정 생성

```bash
# 관리자 계정 생성 스크립트 실행
docker exec trading-backend python -m src.scripts.create_admin_user
```

**예상 출력:**
```
🔧 Initializing database...
👤 Creating admin user...
✅ Admin user created successfully!
   Email: admin@admin.com
   Password: Admin123!
   Role: admin

🔐 Please change the password after first login!
```

만약 이미 계정이 있다면:
```
⚠️  Admin user already exists!
   Email: admin@admin.com
   Name: Admin User
   Role: admin
```

#### Step 4: 로그인 테스트

```bash
# 서버에서 직접 로그인 API 테스트
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'
```

**성공 시 응답:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "admin@admin.com",
      "name": "Admin User",
      "role": "admin"
    }
  }
}
```

**실패 시 응답:**
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Invalid email or password"
  }
}
```

---

## 🔍 추가 문제 해결

### 문제: 계정 생성 스크립트 실패

#### 데이터베이스 연결 확인

```bash
# PostgreSQL 컨테이너 상태 확인
docker exec trading-postgres pg_isready -U trading_user -d trading_prod

# PostgreSQL 로그 확인
docker logs trading-postgres --tail 50

# PostgreSQL 직접 접속
docker exec -it trading-postgres psql -U trading_user -d trading_prod

# Users 테이블 확인
SELECT id, email, name, role, is_active FROM users;

# 종료
\q
```

#### 백엔드 로그 확인

```bash
# 백엔드 로그 전체 확인
docker logs trading-backend

# 실시간 로그 모니터링
docker logs -f trading-backend

# 최근 100줄만 확인
docker logs trading-backend --tail 100
```

### 문제: 500 Internal Server Error (회원가입)

이 문제는 다음 원인일 수 있습니다:

1. **환경 변수 누락**
```bash
# .env.production 파일 확인
cat /root/auto-dashboard/.env.production

# 필수 환경 변수:
# - DATABASE_URL
# - ENCRYPTION_KEY
# - JWT_SECRET
# - POSTGRES_PASSWORD
```

2. **데이터베이스 마이그레이션 미실행**
```bash
# 데이터베이스 초기화 (주의: 모든 데이터 삭제됨!)
docker exec trading-backend python -m src.database.init_db
```

3. **권한 문제**
```bash
# 백엔드 컨테이너 내부 확인
docker exec -it trading-backend bash

# Python 환경 확인
python -m src.scripts.create_admin_user

# 종료
exit
```

---

## 🧪 완전한 테스트 절차

### 1. 로컬에서 배포 서버 테스트

```bash
# 헬스 체크
curl http://158.247.245.197:8000/health

# 로그인 테스트
curl -X POST http://158.247.245.197:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'
```

### 2. 웹 브라우저에서 테스트

1. **프론트엔드 접속**: http://158.247.245.197:3000
2. **로그인 클릭**
3. **테스트 계정 정보 입력:**
   - 이메일: `admin@admin.com`
   - 비밀번호: `Admin123!`
4. **로그인 버튼 클릭**
5. **대시보드 접속 확인**

---

## 📋 체크리스트

해결 전에 다음을 확인하세요:

- [ ] 서버에 SSH 접속 가능
- [ ] Docker가 서버에 설치되어 있음
- [ ] 모든 Docker 컨테이너 실행 중
- [ ] 백엔드 헬스 체크 정상 응답
- [ ] PostgreSQL 컨테이너 정상 작동
- [ ] `.env.production` 파일 존재
- [ ] 방화벽 포트 오픈 (3000, 4000, 8000)

해결 후 확인사항:

- [ ] 관리자 계정 생성 성공
- [ ] 로그인 API 테스트 성공
- [ ] 웹 브라우저에서 로그인 성공
- [ ] 대시보드 접근 가능

---

## 🔐 로그인 정보 (최종)

```
이메일:    admin@admin.com
비밀번호:  Admin123!
역할:      admin
```

⚠️ **보안 주의사항**: 첫 로그인 후 반드시 비밀번호를 변경하세요!

---

## 📞 여전히 문제가 있다면?

1. **백엔드 로그 수집**
```bash
docker logs trading-backend > backend-logs.txt
```

2. **PostgreSQL 로그 수집**
```bash
docker logs trading-postgres > postgres-logs.txt
```

3. **컨테이너 상태 확인**
```bash
docker ps -a > container-status.txt
```

4. **환경 변수 확인**
```bash
docker exec trading-backend env | grep -E "DATABASE|JWT|ENCRYPTION" > env-vars.txt
```

로그 파일을 확인하여 구체적인 에러 메시지를 찾으세요.

---

## 🎯 요약

**문제**: 배포 서버 로그인 실패
**원인**: 관리자 계정 미생성
**해결**: `docker exec trading-backend python -m src.scripts.create_admin_user`
**테스트**: http://158.247.245.197:3000 접속 후 `admin@admin.com` / `Admin123!` 로그인

---

## 🔄 다음 단계

로그인이 성공한 후:

1. **비밀번호 변경** (Settings 페이지에서)
2. **API 키 설정** (거래소 연동)
3. **봇 설정** (자동매매 전략 설정)
4. **백테스트** (전략 검증)
5. **실전 트레이딩** 시작!

