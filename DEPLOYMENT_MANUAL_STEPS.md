# 🚀 수동 배포 가이드 (Manual Deployment Guide)

서버 IP: **158.247.245.197**

## ⚠️ SSH 접속 설정 필요

자동 배포 스크립트를 사용하려면 먼저 SSH 키 설정이 필요합니다.

### SSH 키 설정 방법

```bash
# 1. SSH 키가 없다면 생성
ssh-keygen -t rsa -b 4096

# 2. SSH 키를 서버에 복사
ssh-copy-id root@158.247.245.197

# 3. 접속 테스트
ssh root@158.247.245.197
```

---

## 📋 수동 배포 단계별 가이드

### 1️⃣ 서버 접속

```bash
ssh root@158.247.245.197
```

비밀번호를 입력하여 서버에 접속합니다.

### 2️⃣ 프로젝트 디렉토리 설정

```bash
# 프로젝트 디렉토리가 없다면 생성
mkdir -p /root/auto-dashboard
cd /root/auto-dashboard
```

### 3️⃣ 파일 업로드

**로컬 컴퓨터에서 새 터미널을 열고 실행:**

```bash
# 프로젝트 파일을 서버로 복사
cd /Users/mr.joo/Desktop/auto-dashboard

# SCP로 전체 프로젝트 복사
scp -r ./* root@158.247.245.197:/root/auto-dashboard/
```

또는 rsync 사용 (더 효율적):

```bash
rsync -avz --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'dist' \
  --exclude 'build' \
  --exclude '.env' \
  ./ root@158.247.245.197:/root/auto-dashboard/
```

### 4️⃣ 환경 변수 파일 생성

**서버에서 실행:**

```bash
cd /root/auto-dashboard

# .env.production 파일 생성
cat > .env.production << 'EOF'
# PostgreSQL
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=TradingBot2024!SecurePassword
POSTGRES_DB=trading_prod

# Redis
REDIS_PASSWORD=Redis2024!SecurePassword

# Backend Security
ENCRYPTION_KEY=Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=
JWT_SECRET=super-secret-jwt-key-change-this-in-production-2024

# Frontend URLs
VITE_API_URL=http://158.247.245.197:8000

# CORS Origins
ALLOWED_ORIGINS=http://158.247.245.197:3000,http://158.247.245.197:4000,http://158.247.245.197

# Logging
LOG_LEVEL=INFO

# Database URL for backend
DATABASE_URL=postgresql+asyncpg://trading_user:TradingBot2024!SecurePassword@postgres:5432/trading_prod
EOF
```

### 5️⃣ Docker 설치 확인

```bash
# Docker가 설치되어 있는지 확인
docker --version
docker-compose --version

# 설치되지 않았다면 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Compose 설치
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### 6️⃣ 방화벽 포트 오픈

```bash
# UFW 방화벽 사용 시
ufw allow 3000/tcp  # Frontend
ufw allow 4000/tcp  # Admin Frontend
ufw allow 8000/tcp  # Backend
ufw reload

# firewalld 사용 시
firewall-cmd --permanent --add-port=3000/tcp
firewall-cmd --permanent --add-port=4000/tcp
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload
```

### 7️⃣ Docker 이미지 빌드 및 실행

```bash
cd /root/auto-dashboard

# 기존 컨테이너 중지 및 제거
docker-compose --env-file .env.production down

# 캐시 없이 이미지 빌드
docker-compose --env-file .env.production build --no-cache

# 백그라운드에서 컨테이너 시작
docker-compose --env-file .env.production up -d

# 서비스가 시작될 때까지 대기 (10초)
sleep 10

# 컨테이너 상태 확인
docker-compose --env-file .env.production ps
```

### 8️⃣ 관리자 계정 생성

```bash
# 백엔드 컨테이너에서 관리자 계정 생성 스크립트 실행
docker exec trading-backend python -m src.scripts.create_admin_user

# 또는 직접 컨테이너 안으로 들어가서 실행
docker exec -it trading-backend bash
python -m src.scripts.create_admin_user
exit
```

### 9️⃣ 로그 확인

```bash
# 모든 서비스 로그 확인
docker-compose --env-file .env.production logs

# 실시간 로그 보기
docker-compose --env-file .env.production logs -f

# 특정 서비스 로그만 보기
docker logs trading-backend
docker logs trading-frontend
docker logs trading-admin-frontend
docker logs trading-postgres
docker logs trading-redis
```

---

## ✅ 배포 확인

### 1. 헬스 체크

**로컬 컴퓨터에서 실행:**

```bash
# 백엔드 헬스 체크
curl http://158.247.245.197:8000/health

# 프론트엔드 확인
curl -I http://158.247.245.197:3000

# 관리자 프론트엔드 확인
curl -I http://158.247.245.197:4000
```

### 2. 로그인 테스트

```bash
# 로그인 API 테스트
curl -X POST http://158.247.245.197:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'
```

성공 시 JWT 토큰이 반환됩니다.

### 3. 웹 브라우저에서 접속

- **사용자 프론트엔드**: http://158.247.245.197:3000
- **관리자 프론트엔드**: http://158.247.245.197:4000
- **백엔드 API 문서**: http://158.247.245.197:8000/docs

### 4. 로그인 정보

- **이메일**: admin@admin.com
- **비밀번호**: Admin123!

---

## 🔧 문제 해결

### 컨테이너가 시작되지 않을 때

```bash
# 상세 로그 확인
docker-compose --env-file .env.production logs

# 특정 컨테이너 재시작
docker-compose --env-file .env.production restart backend
docker-compose --env-file .env.production restart frontend
```

### 데이터베이스 연결 오류

```bash
# PostgreSQL 컨테이너 상태 확인
docker exec trading-postgres pg_isready

# PostgreSQL 로그 확인
docker logs trading-postgres

# PostgreSQL 접속 테스트
docker exec -it trading-postgres psql -U trading_user -d trading_prod
```

### 프론트엔드 빌드 오류

```bash
# 프론트엔드 컨테이너 로그 확인
docker logs trading-frontend

# 컨테이너 내부 파일 확인
docker exec trading-frontend ls -la /usr/share/nginx/html

# 빌드 재시도
docker-compose --env-file .env.production build --no-cache frontend
docker-compose --env-file .env.production up -d frontend
```

### 관리자 계정 생성 실패

```bash
# 백엔드 컨테이너에 직접 접속
docker exec -it trading-backend bash

# Python 스크립트 직접 실행
cd /app
python -m src.scripts.create_admin_user

# 또는 수동으로 관리자 생성
python << 'EOFPYTHON'
import asyncio
from src.database.database import get_db, engine, Base
from src.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async for db in get_db():
        admin = User(
            email="admin@admin.com",
            name="Admin User",
            hashed_password=pwd_context.hash("Admin123!"),
            role="admin"
        )
        db.add(admin)
        await db.commit()
        print("✅ Admin user created!")
        break

asyncio.run(create_admin())
EOFPYTHON

exit
```

### 포트가 이미 사용 중일 때

```bash
# 포트 사용 프로세스 확인
netstat -tlnp | grep 8000
netstat -tlnp | grep 3000
netstat -tlnp | grep 4000

# 프로세스 종료
kill -9 <PID>

# 또는 모든 컨테이너 중지
docker-compose --env-file .env.production down
```

---

## 🔄 업데이트 방법

코드를 수정한 후 다시 배포하는 방법:

```bash
# 1. 로컬에서 서버로 파일 복사 (로컬 컴퓨터에서)
cd /Users/mr.joo/Desktop/auto-dashboard
rsync -avz --exclude 'node_modules' --exclude '.git' ./ root@158.247.245.197:/root/auto-dashboard/

# 2. 서버에서 재배포 (서버에서)
ssh root@158.247.245.197
cd /root/auto-dashboard
docker-compose --env-file .env.production down
docker-compose --env-file .env.production build --no-cache
docker-compose --env-file .env.production up -d
```

---

## 📊 모니터링

```bash
# 실시간 리소스 사용량
docker stats

# 디스크 사용량
docker system df

# 로그 실시간 확인
docker-compose --env-file .env.production logs -f

# 특정 서비스만 모니터링
docker logs -f trading-backend
```

---

## 🛑 서비스 중지

```bash
# 모든 컨테이너 중지
docker-compose --env-file .env.production down

# 볼륨까지 삭제 (⚠️ 데이터베이스 데이터 삭제됨!)
docker-compose --env-file .env.production down -v

# 이미지까지 삭제
docker-compose --env-file .env.production down --rmi all
```

---

## 📞 지원

배포 중 문제가 발생하면:

1. ✅ 로그 확인: `docker-compose logs`
2. ✅ 컨테이너 상태 확인: `docker ps -a`
3. ✅ 방화벽 설정 확인
4. ✅ 환경 변수 확인: `.env.production` 파일
5. ✅ Docker 버전 확인: `docker --version`

---

## 🎯 자동 배포 스크립트 사용 (SSH 키 설정 후)

SSH 키를 설정한 후에는 간단하게 배포할 수 있습니다:

```bash
# 로컬 컴퓨터에서
cd /Users/mr.joo/Desktop/auto-dashboard
./deploy-to-server.sh
```

이 스크립트는 자동으로:
- 파일을 서버로 복사
- Docker 이미지 빌드
- 컨테이너 시작
- 관리자 계정 생성

모든 작업을 자동으로 수행합니다!
