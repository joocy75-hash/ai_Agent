
# 🚀 배포 가이드 (초보자용)

> Auto Dashboard 프로젝트 배포 및 관리 완벽 가이드
>
> **최종 업데이트**: 2025-12-12

---

## � 목차

1. [기본 개념 설명](#1-기본-개념-설명)
2. [서버 정보](#2-서버-정보)
3. [로컬 개발 환경](#3-로컬-개발-환경)
4. [배포 절차](#4-배포-절차)
5. [다음 작업자가 봐야 할 파일](#5-다음-작업자가-봐야-할-파일)
6. [문제 해결](#6-문제-해결)

---

## 1. 기본 개념 설명

### 1.1 Git 관련 용어

| 용어 | 설명 | 예시 |
|------|------|------|
| **Git** | 코드 버전 관리 도구. 변경 이력을 추적함 | 언제, 누가, 무엇을 변경했는지 기록 |
| **커밋 (Commit)** | 변경사항을 저장소에 기록하는 것 | "로그인 버그 수정"이란 메시지와 함께 변경 저장 |
| **푸시 (Push)** | 로컬 커밋을 원격 저장소(GitHub)로 업로드 | 내 컴퓨터 → GitHub |
| **풀 (Pull)** | 원격 저장소의 변경사항을 다운로드 | GitHub → 서버 |
| **클론 (Clone)** | 원격 저장소를 통째로 복사 | 새 서버에 프로젝트 설치 시 |
| **원격 저장소** | GitHub 같은 클라우드 저장소 | <https://github.com/joocy75-hash/Deep_Finishing.git> |
| **로컬 저장소** | 내 컴퓨터의 Git 저장소 | /Users/mr.joo/Desktop/auto-dashboard |

### 1.2 Docker 관련 용어

| 용어 | 설명 | 예시 |
|------|------|------|
| **Docker** | 애플리케이션을 컨테이너로 패키징 | 서버 환경과 상관없이 동일하게 실행 |
| **컨테이너** | 격리된 실행 환경 | 각 서비스(backend, frontend)가 별도 컨테이너 |
| **이미지** | 컨테이너의 설계도 | Dockerfile로 만든 빌드 결과물 |
| **docker compose** | 여러 컨테이너를 한번에 관리 | backend, frontend, db 동시 실행 |
| **빌드 (Build)** | Dockerfile → 이미지 생성 | `docker compose build` |

### 1.3 환경 변수 (.env 파일)

**비밀번호, API 키 등 민감한 정보**를 코드에 직접 쓰지 않고 `.env` 파일에 저장합니다.

```bash
# .env 파일 예시
JWT_SECRET=super-secret-key     # JWT 토큰 암호화 키
POSTGRES_PASSWORD=db-password   # DB 비밀번호
TELEGRAM_BOT_TOKEN=xxx          # 텔레그램 봇 토큰
```

⚠️ **중요**: `.env` 파일은 Git에 업로드하면 안 됩니다! (보안 위험)

---

## 2. 서버 정보

### 2.1 접속 정보

```
IP 주소: 158.247.245.197
사용자명: root
비밀번호: Vc8,xn7j_fjdnNGy
```

### 2.2 서버 디렉토리 구조

```
/root/auto-dashboard/           # 메인 프로젝트 폴더
├── backend/                    # FastAPI 백엔드
├── frontend/                   # React 프론트엔드
├── admin-frontend/             # 관리자 페이지
├── nginx/                      # 웹 서버 설정
├── docker-compose.yml          # Docker 설정 파일
├── .env                        # 환경 변수 (서버에만 존재)
└── docs/                       # 문서

/root/auto-dashboard-backup/    # 이전 버전 백업
```

### 2.3 서비스 접속 URL

| 서비스 | URL | 설명 |
|--------|-----|------|
| 프론트엔드 | <http://158.247.245.197:3000> | 메인 대시보드 |
| 관리자 페이지 | <http://158.247.245.197:4000> | 관리자 전용 |
| 백엔드 API | <http://158.247.245.197:8000> | REST API |
| API 문서 | <http://158.247.245.197:8000/docs> | Swagger UI |

---

## 3. 로컬 개발 환경

### 3.1 필수 프로그램

```bash
# Git 설치 확인
git --version

# Node.js 설치 확인 (프론트엔드용)
node --version    # v18 이상 권장

# Python 설치 확인 (백엔드용)
python3 --version # 3.11 권장
```

### 3.2 원격 저장소 (GitHub)

```
저장소 URL: https://github.com/joocy75-hash/Deep_Finishing.git
브랜치: main
```

### 3.3 로컬에서 프로젝트 클론 (처음 시작할 때)

```bash
# 바탕화면에 프로젝트 클론
cd ~/Desktop
git clone https://github.com/joocy75-hash/Deep_Finishing.git auto-dashboard
cd auto-dashboard
```

---

## 4. 배포 절차

### 4.1 전체 흐름도

```
┌─────────────────────────────────────────────────────────────────┐
│                        배포 흐름                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [로컬 컴퓨터]                                                     │
│       │                                                           │
│       ├── 1. 코드 수정                                             │
│       │                                                           │
│       ├── 2. git add -A        (변경사항 스테이징)                   │
│       │                                                           │
│       ├── 3. git commit -m "메시지"  (커밋 생성)                     │
│       │                                                           │
│       └── 4. git push origin main  (GitHub로 업로드)               │
│                    │                                              │
│                    ▼                                              │
│  [GitHub - 원격 저장소]                                            │
│                    │                                              │
│                    ▼                                              │
│  [프로덕션 서버]                                                    │
│       │                                                           │
│       ├── 5. SSH 접속                                             │
│       │                                                           │
│       ├── 6. cd /root/auto-dashboard                              │
│       │                                                           │
│       ├── 7. git pull origin main  (GitHub에서 다운로드)            │
│       │                                                           │
│       ├── 8. docker compose down   (기존 컨테이너 중지)              │
│       │                                                           │
│       └── 9. docker compose up -d --build  (새 컨테이너 실행)        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 단계별 상세 설명

#### Step 1: 로컬에서 코드 수정

원하는 에디터(VS Code 등)로 코드 수정

#### Step 2: 변경사항 확인 및 스테이징

```bash
# 현재 디렉토리로 이동
cd /Users/mr.joo/Desktop/auto-dashboard

# 변경된 파일 확인
git status

# 모든 변경사항 스테이징 (Git에 추가)
git add -A

# 또는 특정 파일만
git add backend/src/api/auth.py
```

#### Step 3: 커밋 생성

```bash
# 변경 내용을 설명하는 메시지와 함께 커밋
git commit -m "feat: 로그인 기능 개선"

# 커밋 메시지 규칙
# feat: 새 기능 추가
# fix: 버그 수정
# docs: 문서 수정
# security: 보안 관련
```

#### Step 4: GitHub로 푸시

```bash
git push origin main
```

#### Step 5: 서버 SSH 접속

```bash
# Mac/Linux 터미널에서
ssh root@158.247.245.197

# 비밀번호 입력
Vc8,xn7j_fjdnNGy
```

#### Step 6-9: 서버에서 업데이트 및 재시작

```bash
# 프로젝트 디렉토리 이동
cd /root/auto-dashboard

# GitHub에서 최신 코드 가져오기
git pull origin main

# 기존 컨테이너 중지
docker compose down

# 새 이미지 빌드하고 컨테이너 시작
docker compose up -d --build

# 로그 확인 (문제 있는지 체크)
docker compose logs -f --tail=50
```

### 4.3 빠른 배포 (한 줄 명령어)

```bash
# 로컬에서 (커밋 + 푸시)
git add -A && git commit -m "변경내용" && git push origin main

# 서버에서 (풀 + 재시작)
cd /root/auto-dashboard && git pull && docker compose down && docker compose up -d --build
```

---

## 5. 다음 작업자가 봐야 할 파일

### 5.1 필수 문서 (우선순위 순)

| 순서 | 파일 | 설명 |
|:----:|------|------|
| 1️⃣ | `docs/DEPLOYMENT_GUIDE.md` | **현재 파일** - 배포 방법 |
| 2️⃣ | `docs/PRE_DEPLOYMENT_AUDIT.md` | 배포 전 점검 리포트 |
| 3️⃣ | `skills/backend-trading-api/SKILL.md` | 백엔드 개발 가이드 |
| 4️⃣ | `skills/frontend-trading-dashboard/SKILL.md` | 프론트엔드 개발 가이드 |
| 5️⃣ | `docs/SECURITY_PRIORITY_TASKS.md` | 보안 작업 목록 |

### 5.2 핵심 코드 파일

#### 백엔드 (`backend/src/`)

| 파일 | 설명 |
|------|------|
| `main.py` | FastAPI 앱 진입점 |
| `api/auth.py` | 로그인/회원가입 API |
| `api/bot.py` | 봇 시작/정지 API |
| `utils/jwt_auth.py` | JWT 인증 (Refresh Token 포함) |
| `services/bot_runner.py` | 봇 실행 엔진 (2000줄+) |

#### 프론트엔드 (`frontend/src/`)

| 파일 | 설명 |
|------|------|
| `App.jsx` | React 앱 진입점 |
| `context/AuthContext.jsx` | 인증 상태 관리 (Refresh Token) |
| `pages/Trading.jsx` | 거래 페이지 |
| `api/auth.js` | 인증 API 호출 |

#### 설정 파일

| 파일 | 설명 |
|------|------|
| `docker-compose.yml` | Docker 서비스 정의 |
| `backend/requirements.txt` | Python 패키지 목록 |
| `frontend/package.json` | Node.js 패키지 목록 |
| `nginx/nginx.conf` | 웹 서버 설정 |

### 5.3 환경 변수 (.env)

서버의 `/root/auto-dashboard/.env` 파일:

```bash
# 데이터베이스
POSTGRES_PASSWORD=SecureTradingDB2024

# Redis
REDIS_PASSWORD=SecureRedis2024#

# 보안 키
ENCRYPTION_KEY=KI_ZEzFbsQoURTATJZkIKvao5TTrYA9aVArgAncr_Co=
JWT_SECRET=super-secret-jwt-key-for-trading-dashboard-2024

# CORS (허용 도메인)
ALLOWED_ORIGINS=http://158.247.245.197:3000,http://158.247.245.197:4000

# 프론트엔드 API URL
VITE_API_URL=http://158.247.245.197:8000

# 텔레그램
TELEGRAM_BOT_TOKEN=8289295080:AAHce1EwlO6O33YbTHps_oaUHo7YJ4MBrso
TELEGRAM_CHAT_ID=7980845952
```

---

## 6. 문제 해결

### 6.1 자주 발생하는 문제

#### 문제: "docker compose: command not found"

```bash
# 해결: docker compose (한 칸 띄어쓰기) 사용
docker compose up -d  # ✅ 올바름
docker-compose up -d  # ❌ 구버전 (설치 필요)
```

#### 문제: 컨테이너가 시작되지 않음

```bash
# 로그 확인
docker compose logs backend --tail=100

# 컨테이너 상태 확인
docker compose ps

# 강제 재빌드
docker compose build --no-cache backend
docker compose up -d
```

#### 문제: Git pull이 안 됨 (충돌)

```bash
# 로컬 변경사항 버리고 강제 풀
git fetch origin
git reset --hard origin/main
```

#### 문제: 포트가 이미 사용 중

```bash
# 사용 중인 포트 확인
sudo lsof -i :8000

# 해당 프로세스 종료
sudo kill -9 [PID]
```

### 6.2 서버 재부팅 후 컨테이너 자동 시작

현재 설정: Docker 컨테이너가 서버 재부팅 후 자동 시작됨 (`restart: unless-stopped`)

수동 시작이 필요한 경우:

```bash
cd /root/auto-dashboard
docker compose up -d
```

### 6.3 긴급 롤백 (이전 버전으로 복구)

```bash
# 백업 폴더가 있는 경우
cd /root
mv auto-dashboard auto-dashboard-failed
mv auto-dashboard-backup auto-dashboard

# 컨테이너 재시작
cd auto-dashboard
docker compose up -d --build
```

---

## 📞 지원

문제가 해결되지 않으면:

1. `docker compose logs` 결과 저장
2. 에러 메시지 스크린샷
3. 어떤 작업 중 발생했는지 기록

---

## 📝 변경 이력

| 날짜 | 작업자 | 변경 내용 |
|------|--------|----------|
| 2025-12-12 | AI Assistant | 초기 작성, 보안 강화, Refresh Token 구현 |
