# 🚀 배포 퀵 스타트 가이드

서버 IP: **158.247.245.197**

## 📋 사전 준비

1. **SSH 키 설정 완료** (비밀번호 없이 접속 가능해야 함)
2. **서버에 Docker 및 Docker Compose 설치 완료**
3. **방화벽 포트 오픈**: 3000, 4000, 8000

## 🎯 원클릭 배포

### 방법 1: 자동 배포 스크립트 사용 (권장)

```bash
# 프로젝트 디렉토리에서 실행
cd /Users/mr.joo/Desktop/auto-dashboard

# 배포 스크립트 실행
./deploy-to-server.sh
```

### 방법 2: 수동 배포

```bash
# 1. 서버 접속
ssh root@158.247.245.197

# 2. 프로젝트 디렉토리로 이동 (없으면 git clone)
cd /root/auto-dashboard

# 3. 최신 코드 가져오기
git pull origin main

# 4. 환경 변수 설정 (.env.production 파일 생성)
cat > .env.production << 'EOF'
# PostgreSQL
POSTGRES_PASSWORD=TradingBot2024!SecurePassword

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
EOF

# 5. 기존 컨테이너 중지 및 제거
docker-compose --env-file .env.production down

# 6. 이미지 빌드 (캐시 없이)
docker-compose --env-file .env.production build --no-cache

# 7. 컨테이너 시작
docker-compose --env-file .env.production up -d

# 8. 로그 확인
docker-compose --env-file .env.production logs -f

# 9. 관리자 계정 생성
docker exec trading-backend python -m src.scripts.create_admin_user
```

## 🔍 배포 확인

### 1. 서비스 상태 확인

```bash
# Docker 컨테이너 상태
docker ps

# 특정 서비스 로그 확인
docker logs trading-backend
docker logs trading-frontend
docker logs trading-admin-frontend
docker logs trading-postgres
docker logs trading-redis
```

### 2. 헬스 체크

```bash
# 백엔드 헬스 체크
curl http://158.247.245.197:8000/health

# 프론트엔드 접속 확인
curl -I http://158.247.245.197:3000

# 관리자 프론트엔드 접속 확인
curl -I http://158.247.245.197:4000
```

### 3. 로그인 테스트

```bash
# 로그인 API 테스트
curl -X POST http://158.247.245.197:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@admin.com","password":"Admin123!"}'
```

## 🔐 로그인 정보

- **이메일**: admin@admin.com
- **비밀번호**: Admin123!

⚠️ **보안**: 첫 로그인 후 반드시 비밀번호를 변경하세요!

## 📡 서비스 URL

- **사용자 프론트엔드**: http://158.247.245.197:3000
- **관리자 프론트엔드**: http://158.247.245.197:4000
- **백엔드 API**: http://158.247.245.197:8000
- **API 문서**: http://158.247.245.197:8000/docs

## 🔧 문제 해결

### 로그인이 안 될 때

```bash
# 1. 백엔드 로그 확인
docker logs trading-backend --tail 100

# 2. 데이터베이스 연결 확인
docker exec trading-postgres pg_isready

# 3. 관리자 계정 재생성
docker exec trading-backend python -m src.scripts.create_admin_user
```

### 프론트엔드가 안 보일 때

```bash
# 1. 프론트엔드 로그 확인
docker logs trading-frontend

# 2. nginx 설정 확인
docker exec trading-frontend cat /etc/nginx/conf.d/default.conf

# 3. 빌드 확인
docker exec trading-frontend ls -la /usr/share/nginx/html
```

### 백엔드 API가 안 될 때

```bash
# 1. 백엔드 로그 상세 확인
docker logs trading-backend --tail 200

# 2. PostgreSQL 접속 테스트
docker exec -it trading-postgres psql -U trading_user -d trading_prod

# 3. 백엔드 재시작
docker-compose --env-file .env.production restart backend
```

## 🔄 업데이트 방법

```bash
# 서버에서
cd /root/auto-dashboard
git pull
docker-compose --env-file .env.production down
docker-compose --env-file .env.production build --no-cache
docker-compose --env-file .env.production up -d
```

## 📊 모니터링

```bash
# 실시간 로그 확인
docker-compose --env-file .env.production logs -f

# 리소스 사용량 확인
docker stats

# 디스크 사용량 확인
docker system df
```

## 🛑 서비스 중지

```bash
# 모든 컨테이너 중지
docker-compose --env-file .env.production down

# 볼륨까지 삭제 (데이터 삭제 주의!)
docker-compose --env-file .env.production down -v
```

## 📞 지원

문제가 지속되면 다음을 확인하세요:
1. 서버 방화벽 설정
2. Docker 로그
3. 네트워크 연결 상태
