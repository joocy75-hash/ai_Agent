# 🚀 Auto Dashboard 빠른 시작 가이드

**최종 업데이트**: 2025-12-03
**상태**: ✅ Production Ready

---

## 📦 시스템 요구사항

### 최소 사양
- **CPU**: 2 Core
- **RAM**: 4GB
- **Disk**: 20GB
- **OS**: Linux, macOS, Windows (Docker 필요)

### 권장 사양
- **CPU**: 4 Core
- **RAM**: 8GB
- **Disk**: 50GB SSD
- **OS**: Ubuntu 22.04 LTS

---

## ⚡ 빠른 시작 (개발 환경)

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/auto-dashboard.git
cd auto-dashboard
```

### 2. 환경 변수 설정
```bash
cp .env.example .env

# Encryption Key 생성
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# .env 파일에 생성된 키 입력
nano .env
```

### 3. 배포 스크립트 실행
```bash
./deploy.sh
# 옵션 1 선택 (개발 환경)
```

### 4. 접속
- **프론트엔드**: http://localhost:3000
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

---

## 🐳 Docker Compose 배포 (운영 환경)

### 1. 환경 변수 설정
```bash
cp .env.example .env

# 필수 값 설정
POSTGRES_PASSWORD=your-secure-password
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
JWT_SECRET=$(openssl rand -hex 32)
```

### 2. Docker Compose 실행
```bash
# 백엔드 + 프론트엔드 + DB
docker-compose up -d

# 로그 확인
docker-compose logs -f backend
```

### 3. 서비스 확인
```bash
# Health check
curl http://localhost:8000/health

# 컨테이너 상태
docker-compose ps
```

---

## 📊 모니터링 추가

### Prometheus + Grafana 실행
```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### 접속
- **Grafana**: http://localhost:3001
  - ID: `admin`
  - PW: `admin` (첫 로그인 시 변경)
- **Prometheus**: http://localhost:9090

---

## 🔐 HTTPS 설정 (운영 환경)

### 1. SSL 인증서 발급 (Let's Encrypt)
```bash
sudo apt install certbot

# 도메인 인증서 발급
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d api.yourdomain.com

# 인증서 복사
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
```

### 2. Nginx 설정 수정
```bash
# nginx/nginx.conf 에서 yourdomain.com을 실제 도메인으로 변경
nano nginx/nginx.conf
```

### 3. Nginx 포함하여 실행
```bash
docker-compose --profile production up -d
```

---

## 🗄️ PostgreSQL 마이그레이션

### SQLite → PostgreSQL 이전

```bash
# 1. PostgreSQL 환경 변수 설정
export POSTGRES_URL="postgresql+asyncpg://trading_user:password@localhost:5432/trading_prod"

# 2. 마이그레이션 실행
cd backend
python3 scripts/migrate_sqlite_to_postgres.py

# 3. 검증
python3 scripts/migrate_sqlite_to_postgres.py --verify

# 4. .env 파일 업데이트
# DATABASE_URL을 PostgreSQL로 변경

# 5. 재시작
docker-compose restart backend
```

---

## 🚨 긴급 대응

### 모든 봇 정지
```bash
# 시뮬레이션 (실제 실행 안 함)
python3 backend/scripts/emergency_stop_all.py --dry-run

# 실제 정지
python3 backend/scripts/emergency_stop_all.py

# 특정 사용자만 정지
python3 backend/scripts/emergency_stop_all.py --user-id 6
```

### 봇 상태 확인
```bash
python3 backend/scripts/emergency_stop_all.py --status
```

### 로그 확인
```bash
# Docker 로그
docker-compose logs -f backend | grep ERROR

# 파일 로그 (컨테이너 내부)
docker exec -it trading-backend tail -f /app/logs/app.log
```

---

## 🔧 일반적인 문제 해결

### 1. 백엔드가 시작되지 않음
```bash
# 환경 변수 확인
docker-compose config

# 데이터베이스 연결 확인
docker-compose exec postgres psql -U trading_user -d trading_prod

# 로그 확인
docker-compose logs backend
```

### 2. 프론트엔드 연결 오류
```bash
# 환경 변수 확인
echo $NEXT_PUBLIC_API_URL

# 백엔드 Health Check
curl http://localhost:8000/health

# 프론트엔드 재빌드
docker-compose build frontend
docker-compose up -d frontend
```

### 3. 차트가 업데이트 안 됨
```bash
# WebSocket 연결 확인
wscat -c ws://localhost:8000/ws/user/6?token=YOUR_TOKEN

# 시장 데이터 수신 확인
docker-compose logs backend | grep "Market data"
```

### 4. 주문 실행 실패
```bash
# Bitget API 키 확인
curl http://localhost:8000/account/balance \
  -H "Authorization: Bearer YOUR_TOKEN"

# 봇 상태 확인
curl http://localhost:8000/bot/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📱 첫 거래 실행하기

### 1. 계정 생성 및 로그인
```bash
# 프론트엔드에서 회원가입
# http://localhost:3000/register

# 또는 cURL로 계정 생성
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"trader@example.com","password":"SecurePass123!"}'
```

### 2. Bitget API 키 등록
```bash
# 프론트엔드 Settings 페이지에서 입력
# 또는 API 직접 호출

curl -X POST http://localhost:8000/account/save_keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "api_key": "YOUR_BITGET_API_KEY",
    "secret_key": "YOUR_BITGET_SECRET_KEY",
    "passphrase": ""
  }'
```

### 3. 전략 생성
```bash
# 프론트엔드에서 또는 API로
curl -X POST http://localhost:8000/strategies/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "My First Strategy",
    "code": "ultra_aggressive",
    "parameters": {}
  }'
```

### 4. 봇 시작
```bash
curl -X POST http://localhost:8000/bot/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "strategy_code": "ultra_aggressive",
    "symbol": "ETHUSDT",
    "timeframe": "5m"
  }'
```

### 5. 실시간 모니터링
- 프론트엔드 대시보드: http://localhost:3000
- WebSocket 스트림으로 실시간 업데이트 확인

---

## 🎯 다음 단계

### Phase 1: 안정화
- [ ] 1-2주간 실전 거래 모니터링
- [ ] 버그 수정 및 로그 분석
- [ ] 사용자 피드백 반영

### Phase 2: 고도화
- [ ] 추가 전략 개발
- [ ] 백테스팅 엔진 개선
- [ ] 알림 시스템 (텔레그램, 이메일)
- [ ] 모바일 반응형 개선

### Phase 3: 확장
- [ ] 다중 거래소 지원 (Binance, Bybit)
- [ ] 포트폴리오 관리 기능
- [ ] 소셜 트레이딩
- [ ] API 제공 (외부 개발자)

---

## 📚 추가 문서

- [PRODUCTION_READY_SUMMARY.md](PRODUCTION_READY_SUMMARY.md) - 전체 시스템 요약
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - 상세 배포 체크리스트
- [ORDER_EXECUTION_DIAGNOSIS.md](ORDER_EXECUTION_DIAGNOSIS.md) - 디버깅 가이드
- [REAL_TRADING_SETUP.md](REAL_TRADING_SETUP.md) - 실전 거래 설정

---

## 💬 문의 및 지원

### 이슈 발생 시
1. 로그 확인: `docker-compose logs -f backend`
2. Health Check: `curl http://localhost:8000/health`
3. GitHub Issues에 버그 리포트

### 커뮤니티
- GitHub: https://github.com/yourusername/auto-dashboard
- Discord: (링크 추가)
- Email: support@yourdomain.com

---

**⚠️ 경고**: 이 시스템은 실제 자금으로 거래합니다. 충분한 테스트와 리스크 관리 없이 운영하지 마세요.

**📜 라이선스**: MIT License

---

**작성**: Claude Code
**버전**: 1.0.0
**최종 업데이트**: 2025-12-03
