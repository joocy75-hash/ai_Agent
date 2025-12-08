# 🔧 배포 서버 프론트엔드-백엔드 연결 문제 해결

## 🎯 문제

배포 서버(http://158.247.245.197:3000)의 프론트엔드가 백엔드에 연결되지 않습니다.

**원인**: 프론트엔드가 빌드될 때 `VITE_API_URL`이 `localhost:8000`으로 설정되어 빌드됨

## ✅ 해결 방법

### 방법 1: 서버에서 직접 재빌드 (권장)

```bash
# 1. 서버 접속
ssh root@158.247.245.197

# 2. 프로젝트 디렉토리로 이동
cd /root/auto-dashboard

# 3. .env.production 파일 확인
cat .env.production | grep VITE_API_URL

# 출력이 다음과 같아야 합니다:
# VITE_API_URL=http://158.247.245.197:8000

# 4. 프론트엔드 컨테이너 재빌드
docker-compose --env-file .env.production stop frontend
docker-compose --env-file .env.production build --no-cache frontend
docker-compose --env-file .env.production up -d frontend

# 5. 빌드 완료 확인 (1-2분 소요)
docker logs -f trading-frontend

# 6. 테스트
curl -I http://localhost:3000
```

### 방법 2: 전체 재배포

```bash
# 서버에서
cd /root/auto-dashboard
docker-compose --env-file .env.production down
docker-compose --env-file .env.production build --no-cache
docker-compose --env-file .env.production up -d

# 관리자 계정 생성 (아직 안했다면)
docker exec trading-backend python -m src.scripts.create_admin_user
```

## 🧪 연결 확인 방법

### 브라우저 개발자 도구로 확인

1. http://158.247.245.197:3000 접속
2. F12 (개발자 도구 열기)
3. Network 탭 선택
4. 로그인 시도
5. 요청 URL 확인:
   - ✅ 정상: `http://158.247.245.197:8000/auth/login`
   - ❌ 문제: `http://localhost:8000/auth/login`

### 콘솔에서 확인

서버에서:
```bash
# 프론트엔드 빌드 확인
docker exec trading-frontend cat /usr/share/nginx/html/index.html | grep -o "158.247.245.197"

# 결과가 나와야 정상
```

## 📋 .env.production 파일 내용 확인

올바른 `.env.production` 파일:

```bash
# PostgreSQL
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=TradingBot2024!SecurePassword
POSTGRES_DB=trading_prod

# Redis
REDIS_PASSWORD=Redis2024!SecurePassword

# Backend Security
ENCRYPTION_KEY=Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8=
JWT_SECRET=super-secret-jwt-key-change-this-in-production-2024

# 🔴 이 부분이 중요!
VITE_API_URL=http://158.247.245.197:8000

# CORS Origins
ALLOWED_ORIGINS=http://158.247.245.197:3000,http://158.247.245.197:4000,http://158.247.245.197

# Database URL for backend
DATABASE_URL=postgresql+asyncpg://trading_user:TradingBot2024!SecurePassword@postgres:5432/trading_prod

# Logging
LOG_LEVEL=INFO
```

## 🚨 주의사항

1. **Vite 환경 변수는 빌드 시점에 번들에 포함됩니다**
   - 런타임에 변경할 수 없습니다
   - 재빌드가 필수입니다

2. **Docker 빌드 캐시**
   - `--no-cache` 옵션 사용 권장
   - 환경 변수 변경 시 반드시 재빌드

3. **CORS 설정**
   - 백엔드의 `ALLOWED_ORIGINS`에 프론트엔드 URL 포함 필요
   - 현재 설정은 정상적으로 되어 있음

## ✅ 확인 체크리스트

재빌드 후 다음을 확인하세요:

- [ ] 프론트엔드 접속: http://158.247.245.197:3000
- [ ] 백엔드 헬스 체크: http://158.247.245.197:8000/health
- [ ] 브라우저 개발자 도구 Network 탭에서 API 요청 URL 확인
- [ ] 로그인 시도 (admin@admin.com / Admin123!)
- [ ] 대시보드 접근 확인

## 🎯 한 번에 해결하기

```bash
# SSH로 서버 접속 후
cd /root/auto-dashboard

# .env.production 업데이트 (기존 파일 백업)
cp .env.production .env.production.backup

# 정확한 환경 변수로 업데이트
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

# Frontend API URL (중요!)
VITE_API_URL=http://158.247.245.197:8000

# CORS Origins
ALLOWED_ORIGINS=http://158.247.245.197:3000,http://158.247.245.197:4000,http://158.247.245.197

# Database URL for backend
DATABASE_URL=postgresql+asyncpg://trading_user:TradingBot2024!SecurePassword@postgres:5432/trading_prod

# Logging
LOG_LEVEL=INFO
EOF

# 프론트엔드만 재빌드 (빠름)
docker-compose --env-file .env.production stop frontend
docker-compose --env-file .env.production build --no-cache frontend
docker-compose --env-file .env.production up -d frontend

# 완료까지 대기
echo "프론트엔드 빌드 중... (1-2분 소요)"
sleep 90

# 테스트
echo "테스트 중..."
curl -I http://localhost:3000

echo "✅ 완료! 브라우저에서 http://158.247.245.197:3000 접속하세요"
```

## 💡 디버깅 팁

문제가 계속되면:

```bash
# 프론트엔드 빌드 로그 확인
docker logs trading-frontend --tail 100

# 환경 변수가 제대로 전달되었는지 확인
docker-compose --env-file .env.production config | grep VITE_API_URL

# 빌드된 파일에서 API URL 확인
docker exec trading-frontend find /usr/share/nginx/html -name "*.js" -exec grep -l "158.247.245.197" {} \;
```
