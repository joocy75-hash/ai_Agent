# 🚀 Vultr 서울 배포 완벽 가이드

> 작성일: 2025-12-06
> 대상: Auto Dashboard (암호화폐 AI 자동매매 플랫폼)
> 예상 소요 시간: 1-2시간
> 난이도: ⭐⭐⭐ (중급)

---

## 📋 목차

1. [사전 준비 사항](#1-사전-준비-사항)
2. [Vultr 계정 생성 및 서버 생성](#2-vultr-계정-생성-및-서버-생성)
3. [서버 초기 설정](#3-서버-초기-설정)
4. [Docker 및 Docker Compose 설치](#4-docker-및-docker-compose-설치)
5. [프로젝트 배포](#5-프로젝트-배포)
6. [도메인 및 SSL 설정](#6-도메인-및-ssl-설정)
7. [방화벽 설정](#7-방화벽-설정)
8. [서비스 시작 및 확인](#8-서비스-시작-및-확인)
9. [자동 재시작 설정](#9-자동-재시작-설정)
10. [모니터링 및 유지보수](#10-모니터링-및-유지보수)
11. [문제 해결](#11-문제-해결)

---

## 1. 사전 준비 사항

### ✅ 필요한 것들

| 항목 | 설명 | 체크 |
|------|------|------|
| 신용카드/체크카드 | Vultr 결제용 | ☐ |
| 도메인 | 예: yourdomain.com | ☐ |
| GitHub 저장소 | 프로젝트 코드 | ☐ |
| SSH 클라이언트 | Mac: 터미널 / Windows: PuTTY 또는 PowerShell | ☐ |

### 📝 필요한 환경 변수 값 준비

배포 전에 다음 값들을 미리 준비하세요:

```bash
# [필수] 보안 키 (아래 명령어로 생성)
# JWT_SECRET: 32자 이상의 랜덤 문자열
# ENCRYPTION_KEY: Python으로 생성

# JWT_SECRET 생성 (터미널에서)
openssl rand -base64 32

# ENCRYPTION_KEY 생성 (Python에서)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**준비할 값 목록:**

- [ ] JWT_SECRET: `________________________________`
- [ ] ENCRYPTION_KEY: `________________________________`
- [ ] POSTGRES_PASSWORD: `________________________________`
- [ ] REDIS_PASSWORD: `________________________________`
- [ ] 도메인 이름: `________________________________`

---

## 2. Vultr 계정 생성 및 서버 생성

### Step 2.1: Vultr 회원가입

1. [https://www.vultr.com](https://www.vultr.com) 접속
2. **Sign Up** 클릭
3. 이메일, 비밀번호 입력
4. 결제 정보 입력 (신용카드)
5. 이메일 인증 완료

### Step 2.2: 서버 생성

1. 로그인 후 **Products** → **Compute** 클릭
2. **Deploy Server** 버튼 클릭

### Step 2.3: 서버 옵션 선택

#### ① Choose Type

```
☑️ Cloud Compute - Shared CPU
```

#### ② Choose Location

```
☑️ Seoul (서울) - 한국에서 가장 빠름!
```

#### ③ Choose Image

```
☑️ Ubuntu 24.04 LTS x64
   (또는 Ubuntu 22.04 LTS x64)
```

#### ④ Choose Plan

```
추천 플랜 (20명 기준):
☑️ $12/month
   - 1 vCPU
   - 2 GB RAM
   - 55 GB NVMe SSD
   - 2 TB Bandwidth
```

> 💡 **팁**: 처음에는 $12 플랜으로 시작하고, 필요시 업그레이드 가능

#### ⑤ Additional Features

```
☑️ Enable IPv6 (선택사항)
☐ Enable Auto Backups ($2.40/month 추가, 권장)
```

#### ⑥ SSH Keys (강력 권장)

```
1. "Add New" 클릭
2. 로컬에서 SSH 키 생성:
   ssh-keygen -t ed25519 -C "your-email@example.com"
3. 공개키 복사:
   cat ~/.ssh/id_ed25519.pub
4. Vultr에 붙여넣기
5. 이름 입력 (예: my-mac)
6. "Add SSH Key" 클릭
```

#### ⑦ Server Hostname & Label

```
Hostname: trading-server
Label: Auto Dashboard Production
```

### Step 2.4: 서버 생성 완료

1. **Deploy Now** 클릭
2. 2-3분 대기 (Server Status: Running이 될 때까지)
3. **IP Address** 복사해두기 (예: `149.28.xxx.xxx`)

---

## 3. 서버 초기 설정

### Step 3.1: SSH 접속

```bash
# Mac/Linux 터미널에서
ssh root@149.28.xxx.xxx

# 처음 접속 시 fingerprint 확인
# "yes" 입력
```

> Windows 사용자: PowerShell 또는 PuTTY 사용

### Step 3.2: 시스템 업데이트

```bash
# 패키지 목록 업데이트
apt update

# 시스템 업그레이드
apt upgrade -y

# 필수 패키지 설치
apt install -y curl wget git nano htop ufw
```

### Step 3.3: 새 사용자 생성 (보안)

```bash
# 새 사용자 생성 (root 대신 사용)
adduser deploy

# 비밀번호 설정 프롬프트가 나옴
# 강력한 비밀번호 입력

# sudo 권한 부여
usermod -aG sudo deploy

# SSH 키 복사
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys
```

### Step 3.4: SSH 보안 설정

```bash
# SSH 설정 파일 편집
nano /etc/ssh/sshd_config
```

다음 항목들을 찾아서 수정:

```bash
# root 로그인 비활성화 (SSH 키 설정 후)
PermitRootLogin no

# 비밀번호 인증 비활성화 (SSH 키만 허용)
PasswordAuthentication no

# 저장: Ctrl+O, Enter, Ctrl+X
```

```bash
# SSH 재시작
systemctl restart sshd
```

### Step 3.5: 새 사용자로 재접속 테스트

**새 터미널 창을 열고:**

```bash
ssh deploy@149.28.xxx.xxx

# 접속 되면 성공!
# 이제부터 deploy 계정 사용
```

---

## 4. Docker 및 Docker Compose 설치

### Step 4.1: Docker 설치

```bash
# Docker 설치 스크립트 다운로드 및 실행
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker 그룹에 현재 사용자 추가
sudo usermod -aG docker deploy

# 그룹 변경 적용 (재로그인 또는)
newgrp docker

# Docker 버전 확인
docker --version
# 출력 예: Docker version 24.0.x
```

### Step 4.2: Docker Compose 설치

```bash
# Docker Compose 플러그인 설치 (최신 방식)
sudo apt install docker-compose-plugin -y

# 버전 확인
docker compose version
# 출력 예: Docker Compose version v2.x.x
```

### Step 4.3: Docker 서비스 시작

```bash
# Docker 서비스 시작 및 자동 시작 설정
sudo systemctl start docker
sudo systemctl enable docker

# 상태 확인
sudo systemctl status docker
# Active: active (running) 확인
```

---

## 5. 프로젝트 배포

### Step 5.1: 프로젝트 클론

```bash
# 홈 디렉토리로 이동
cd ~

# Git 저장소 클론
git clone https://github.com/your-username/auto-dashboard.git

# 프로젝트 디렉토리로 이동
cd auto-dashboard
```

> 💡 **Private 저장소인 경우:**
>
> ```bash
> # GitHub Personal Access Token 사용
> git clone https://<token>@github.com/your-username/auto-dashboard.git
> ```

### Step 5.2: 환경 변수 파일 생성

```bash
# .env 파일 생성
nano .env
```

다음 내용을 복사하여 붙여넣기 (값은 실제 값으로 교체):

```bash
# ============================================
# 프로덕션 환경 설정
# ============================================

# 환경
ENVIRONMENT=production
DEBUG=false

# ============================================
# 보안 (반드시 변경!)
# ============================================

# JWT 시크릿 (32자 이상)
JWT_SECRET=여기에_openssl_rand_base64_32_결과_붙여넣기

# 암호화 키 (Fernet.generate_key() 결과)
ENCRYPTION_KEY=여기에_ENCRYPTION_KEY_붙여넣기

# ============================================
# 데이터베이스
# ============================================

# PostgreSQL 비밀번호 (강력한 비밀번호로 변경)
POSTGRES_PASSWORD=Super_Secure_Postgres_P@ssw0rd!

# PostgreSQL 연결 URL (docker-compose 내부용)
DATABASE_URL=postgresql+asyncpg://trading_user:${POSTGRES_PASSWORD}@postgres:5432/trading_prod

# ============================================
# Redis
# ============================================

# Redis 비밀번호
REDIS_PASSWORD=Super_Secure_Redis_P@ssw0rd!

# Redis 연결 URL
REDIS_URL=redis://default:${REDIS_PASSWORD}@redis:6379

# ============================================
# CORS 및 도메인
# ============================================

# 허용할 도메인 (실제 도메인으로 변경)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
FRONTEND_URL=https://yourdomain.com

# ============================================
# 관리자 보안
# ============================================

# 관리자 API 접근 허용 IP (쉼표로 구분)
# 본인 IP 확인: curl ifconfig.me
ADMIN_IP_WHITELIST=123.45.67.89,111.222.333.444

# ============================================
# 텔레그램 (선택사항)
# ============================================

TELEGRAM_BOT_TOKEN=여기에_봇_토큰
TELEGRAM_CHAT_ID=여기에_채팅_ID

# ============================================
# OAuth (선택사항)
# ============================================

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=https://api.yourdomain.com/auth/google/callback

KAKAO_CLIENT_ID=
KAKAO_CLIENT_SECRET=
KAKAO_REDIRECT_URI=https://api.yourdomain.com/auth/kakao/callback

# ============================================
# AI 전략 (선택사항)
# ============================================

DEEPSEEK_API_KEY=

# ============================================
# 기타
# ============================================

LOG_LEVEL=INFO
```

저장: `Ctrl+O`, `Enter`, `Ctrl+X`

### Step 5.3: 환경 변수 파일 권한 설정

```bash
# .env 파일 권한 제한 (소유자만 읽기/쓰기)
chmod 600 .env

# 확인
ls -la .env
# -rw------- 1 deploy deploy ... .env
```

### Step 5.4: Nginx 설정 수정

```bash
# nginx 설정 파일 편집
nano nginx/nginx.conf
```

`yourdomain.com`을 실제 도메인으로 변경:

```nginx
# 52번째 줄 근처
server_name yourdomain.com www.yourdomain.com api.yourdomain.com;

# 66번째 줄 근처
server_name yourdomain.com www.yourdomain.com;

# 102번째 줄 근처
server_name api.yourdomain.com;

# 161번째 줄 근처
add_header Access-Control-Allow-Origin "https://yourdomain.com" always;
```

저장: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## 6. 도메인 및 SSL 설정

### Step 6.1: 도메인 DNS 설정

도메인 관리 사이트(가비아, Cloudflare 등)에서:

| 레코드 타입 | 이름 | 값 |
|------------|------|-----|
| A | @ | 149.28.xxx.xxx (Vultr IP) |
| A | www | 149.28.xxx.xxx |
| A | api | 149.28.xxx.xxx |
| A | admin | 149.28.xxx.xxx (관리자 페이지용) |

> 💡 DNS 전파에 최대 24시간 소요 가능 (보통 5-30분)

### Step 6.2: DNS 전파 확인

```bash
# DNS 확인
nslookup yourdomain.com
nslookup api.yourdomain.com

# 또는
dig yourdomain.com
```

### Step 6.3: SSL 인증서 발급 (Let's Encrypt)

```bash
# Certbot 설치
sudo apt install certbot -y

# 방화벽 임시 허용
sudo ufw allow 80
sudo ufw allow 443

# SSL 인증서 발급 (독립 모드)
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com \
  -d api.yourdomain.com \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive
```

### Step 6.4: 인증서 위치 확인

```bash
# 인증서 확인
sudo ls -la /etc/letsencrypt/live/yourdomain.com/

# 출력:
# fullchain.pem  -> 인증서
# privkey.pem    -> 개인키
```

### Step 6.5: Nginx SSL 디렉토리 설정

```bash
# nginx ssl 디렉토리 생성
mkdir -p ~/auto-dashboard/nginx/ssl

# 인증서 심볼릭 링크 생성
sudo ln -sf /etc/letsencrypt/live/yourdomain.com/fullchain.pem ~/auto-dashboard/nginx/ssl/fullchain.pem
sudo ln -sf /etc/letsencrypt/live/yourdomain.com/privkey.pem ~/auto-dashboard/nginx/ssl/privkey.pem

# 권한 설정
sudo chmod 644 ~/auto-dashboard/nginx/ssl/*.pem
```

### Step 6.6: SSL 자동 갱신 설정

```bash
# Certbot 자동 갱신 테스트
sudo certbot renew --dry-run

# 성공 메시지 확인
# Congratulations, all simulated renewals succeeded

# 자동 갱신 크론 설정
sudo crontab -e
```

다음 줄 추가:

```bash
# 매일 새벽 3시에 인증서 갱신 시도
0 3 * * * certbot renew --quiet && docker compose -f /home/deploy/auto-dashboard/docker-compose.yml restart nginx
```

---

## 7. 방화벽 설정

### Step 7.1: UFW 방화벽 설정

```bash
# 기본 정책 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH 허용 (필수! 안 하면 서버 접속 불가)
sudo ufw allow 22/tcp

# HTTP/HTTPS 허용
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 방화벽 활성화
sudo ufw enable
# y 입력

# 상태 확인
sudo ufw status
```

예상 출력:

```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
22/tcp (v6)                ALLOW       Anywhere (v6)
80/tcp (v6)                ALLOW       Anywhere (v6)
443/tcp (v6)               ALLOW       Anywhere (v6)
```

---

## 8. 서비스 시작 및 확인

### Step 8.1: Docker 이미지 빌드

```bash
cd ~/auto-dashboard

# 이미지 빌드 (5-10분 소요)
docker compose build

# 빌드 진행 상황 확인
```

### Step 8.2: 서비스 시작

```bash
# 프로덕션 프로파일로 서비스 시작
docker compose --profile production up -d

# 또는 백그라운드 실행 (nginx 포함)
docker compose up -d

# 컨테이너 상태 확인
docker compose ps
```

예상 출력:

```
NAME                    COMMAND                  STATUS
trading-backend         "uvicorn src.main:app"   Up
trading-frontend        "npm start"              Up
trading-postgres        "docker-entrypoint.s…"   Up (healthy)
trading-redis           "docker-entrypoint.s…"   Up (healthy)
trading-nginx           "nginx -g 'daemon of…"   Up
```

### Step 8.3: 로그 확인

```bash
# 전체 로그
docker compose logs -f

# 백엔드 로그만
docker compose logs -f backend

# 에러만 확인
docker compose logs backend | grep -i error
```

### Step 8.4: 서비스 동작 확인

```bash
# 헬스 체크
curl http://localhost:8000/health

# 예상 응답
# {"status":"healthy","timestamp":"..."}

# 외부에서 확인 (도메인 설정 후)
curl https://api.yourdomain.com/health
```

### Step 8.5: 데이터베이스 확인

```bash
# PostgreSQL 접속
docker compose exec postgres psql -U trading_user -d trading_prod

# 테이블 확인
\dt

# 종료
\q
```

---

## 9. 자동 재시작 설정

### Step 9.1: Docker Compose 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/auto-dashboard.service
```

다음 내용 입력:

```ini
[Unit]
Description=Auto Dashboard Docker Compose Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/deploy/auto-dashboard
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
User=deploy
Group=docker

[Install]
WantedBy=multi-user.target
```

저장: `Ctrl+O`, `Enter`, `Ctrl+X`

### Step 9.2: 서비스 활성화

```bash
# 서비스 데몬 리로드
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable auto-dashboard

# 서비스 상태 확인
sudo systemctl status auto-dashboard
```

### Step 9.3: 서버 재부팅 테스트

```bash
# 서버 재부팅
sudo reboot

# 2-3분 대기 후 재접속
ssh deploy@149.28.xxx.xxx

# 컨테이너 자동 시작 확인
docker compose ps
```

---

## 10. 모니터링 및 유지보수

### Step 10.1: 리소스 모니터링

```bash
# 실시간 리소스 사용량
htop

# Docker 리소스 사용량
docker stats

# 디스크 사용량
df -h
```

### Step 10.2: 로그 로테이션 설정

```bash
sudo nano /etc/logrotate.d/docker
```

```
/var/lib/docker/containers/*/*.log {
    daily
    rotate 7
    compress
    missingok
    delaycompress
    copytruncate
}
```

### Step 10.3: 백업 스크립트 생성

```bash
nano ~/backup.sh
```

```bash
#!/bin/bash
# 데이터베이스 백업 스크립트

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/deploy/backups"

mkdir -p $BACKUP_DIR

# PostgreSQL 백업
docker compose exec -T postgres pg_dump -U trading_user trading_prod > $BACKUP_DIR/db_backup_$DATE.sql

# 오래된 백업 삭제 (7일 이상)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/db_backup_$DATE.sql"
```

```bash
chmod +x ~/backup.sh

# 크론탭에 추가 (매일 새벽 4시 백업)
crontab -e
# 추가: 0 4 * * * /home/deploy/backup.sh
```

### Step 10.4: 업데이트 배포 방법

```bash
cd ~/auto-dashboard

# 최신 코드 가져오기
git pull origin main

# 이미지 재빌드 및 재시작
docker compose build
docker compose up -d

# 다운타임 없는 업데이트 (권장)
docker compose up -d --build
```

---

## 11. 문제 해결

### ❌ 문제: SSH 접속 안됨

```bash
# Vultr 콘솔에서 접속 (웹 콘솔 사용)
# Products → 서버 선택 → View Console

# 방화벽 확인
sudo ufw status
sudo ufw allow 22/tcp
```

### ❌ 문제: 502 Bad Gateway

```bash
# 백엔드 컨테이너 상태 확인
docker compose ps
docker compose logs backend

# 백엔드 재시작
docker compose restart backend
```

### ❌ 문제: 데이터베이스 연결 실패

```bash
# PostgreSQL 상태 확인
docker compose ps postgres
docker compose logs postgres

# 환경 변수 확인
cat .env | grep POSTGRES
```

### ❌ 문제: SSL 인증서 오류

```bash
# 인증서 상태 확인
sudo certbot certificates

# 강제 갱신
sudo certbot renew --force-renewal

# Nginx 재시작
docker compose restart nginx
```

### ❌ 문제: 디스크 공간 부족

```bash
# 사용하지 않는 Docker 리소스 정리
docker system prune -a

# 디스크 사용량 확인
df -h
du -sh /var/lib/docker/
```

### ❌ 문제: 메모리 부족

```bash
# 스왑 파일 추가 (4GB)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 영구 설정
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📋 배포 체크리스트

### 배포 전

- [ ] Vultr 계정 생성 및 서버 생성 완료
- [ ] SSH 키 설정 완료
- [ ] 도메인 DNS 설정 완료

### 배포 중

- [ ] 시스템 업데이트 완료
- [ ] Docker 설치 완료
- [ ] 프로젝트 클론 완료
- [ ] .env 파일 설정 완료
- [ ] SSL 인증서 발급 완료
- [ ] 방화벽 설정 완료

### 배포 후

- [ ] 모든 서비스 Running 상태 확인
- [ ] Health Check API 응답 확인
- [ ] 웹사이트 접속 확인
- [ ] 로그인 테스트 완료
- [ ] 관리자 기본 비밀번호 변경
- [ ] 텔레그램 알림 테스트 (설정한 경우)
- [ ] 백업 스크립트 설정 완료
- [ ] SSL 자동 갱신 설정 완료

---

## 📞 유용한 명령어 모음

```bash
# === 서비스 관리 ===
docker compose up -d          # 서비스 시작
docker compose down           # 서비스 중지
docker compose restart        # 서비스 재시작
docker compose ps             # 상태 확인

# === 로그 확인 ===
docker compose logs -f        # 전체 로그
docker compose logs -f backend # 백엔드 로그
docker compose logs --tail 100 backend # 최근 100줄

# === 데이터베이스 ===
docker compose exec postgres psql -U trading_user -d trading_prod

# === 컨테이너 접속 ===
docker compose exec backend bash
docker compose exec frontend sh

# === 업데이트 ===
git pull && docker compose up -d --build

# === 정리 ===
docker system prune -a        # 미사용 리소스 정리
```

---

## ✅ 완료

축하합니다! 🎉 Vultr 서울 서버에 Auto Dashboard가 성공적으로 배포되었습니다.

**접속 URL:**

- 프론트엔드: <https://yourdomain.com>
- API 서버: <https://api.yourdomain.com>
- API 문서: <https://api.yourdomain.com/docs>

**다음 단계:**

1. 기본 관리자 비밀번호 변경 (<admin@admin.com> / admin123)
2. 2FA 활성화 권장
3. 텔레그램 알림 설정 (Settings 페이지)
4. API 키 등록 (Settings 페이지)

---

> 📌 문서 작성: 2025-12-06
> 📌 문의: 개발팀
