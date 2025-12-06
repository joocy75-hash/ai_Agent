# 🔍 프로젝트 코드 검토 및 개선 가이드

> **작성일**: 2025-12-05  
> **목적**: 다음 개발자가 이어서 작업할 수 있도록 전체 코드베이스 검토 결과, 보완해야 할 점, 추가해야 할 기능을 정리

---

## 📋 목차

1. [전체 프로젝트 구조](#1-전체-프로젝트-구조)
2. [🔴 보안 취약점 및 보완 사항](#2-보안-취약점-및-보완-사항)
3. [🟡 관리자 페이지 미완성 부분](#3-관리자-페이지-미완성-부분)
4. [🟢 추가해야 할 기능](#4-추가해야-할-기능)
5. [🔧 코드 품질 개선](#5-코드-품질-개선)
6. [📝 TODO 목록 정리](#6-todo-목록-정리)
7. [🚀 배포 전 체크리스트](#7-배포-전-체크리스트)
8. [📊 백테스트 오프라인 데이터 관리](#8-백테스트-오프라인-데이터-관리)

---

## 1. 전체 프로젝트 구조

```
auto-dashboard/
├── frontend/                    # 사용자 프론트엔드 (React + Vite + Ant Design)
├── admin-frontend/              # 관리자 프론트엔드 (React + Lucide Icons)
├── backend/                     # FastAPI 백엔드
├── nginx/                       # Nginx 설정
├── monitoring/                  # 모니터링 설정
└── docs/                        # 문서
```

### 주요 기술 스택

| 영역 | 기술 |
|------|------|
| **Frontend** | React 18, Vite, Ant Design 5, Recharts |
| **Admin** | React 18, Vite, Lucide Icons, 순수 CSS |
| **Backend** | FastAPI, SQLAlchemy (async), PostgreSQL, JWT |
| **인증** | JWT + 2FA (TOTP) |
| **배포** | Docker Compose, Nginx |

---

## 2. 🔴 보안 취약점 및 보완 사항

### 2.1 즉시 수정 필요 (Critical)

| 항목 | 위치 | 문제점 | 해결 방법 |
|------|------|--------|----------|
| **JWT Secret 기본값** | `backend/src/config.py:74` | `jwt_secret = "change_me"` 기본값 사용 | 프로덕션에서 반드시 환경변수로 설정 |
| **DB URL 기본값** | `backend/src/config.py:71-72` | 기본값에 `user:password` 포함 | 환경변수 필수 설정 |
| **CORS 설정** | `backend/src/config.py:81` | 빈 문자열 기본값 (전체 허용 가능) | 프로덕션 도메인만 허용 |

### 2.2 높은 우선순위 (High)

| 항목 | 위치 | 문제점 | 해결 방법 |
|------|------|--------|----------|
| **관리자 IP 제한 없음** | `backend/src/api/admin_*.py` | 관리자 API에 IP 화이트리스트 없음 | 미들웨어로 IP 체크 추가 |
| **Redis 토큰 블랙리스트 없음** | `backend/src/api/admin_users.py:530` | 강제 로그아웃 시 JWT 무효화 불가 | Redis 블랙리스트 구현 |
| **비밀번호 초기화 응답** | `backend/src/api/admin_users.py:644` | 새 비밀번호를 API 응답에 포함 | 이메일/SMS로 전송 권장 |
| **API 키 전체 노출 가능** | `backend/src/api/account.py` | 관리자가 API 키 복호화 가능 | 감사 로그 강화 |

### 2.3 중간 우선순위 (Medium)

| 항목 | 문제점 | 해결 방법 |
|------|--------|----------|
| **Rate Limit 우회** | IP 변경 시 우회 가능 | 사용자별 + IP별 복합 제한 |
| **세션 관리 없음** | 동시 로그인 제한 없음 | 디바이스별 세션 관리 추가 |
| **감사 로그 부족** | 일부 관리자 작업만 로깅 | 모든 관리자 작업 로깅 |
| **2FA 백업 코드** | 2FA 복구 방법 없음 | 백업 코드 시스템 구현 |

---

## 3. 🟡 관리자 페이지 미완성 부분

### 3.1 현재 관리자 페이지 구조

```
admin-frontend/src/
├── pages/
│   ├── AdminDashboard.jsx    # 전체 개요, 봇 관리, 사용자 관리, 로그 조회 (탭 형식)
│   └── Login.jsx             # 관리자 로그인
├── components/
│   ├── UserDetailModal.jsx   # 사용자 상세 모달
│   └── layout/AdminLayout.jsx # 레이아웃
└── api/
    ├── client.js             # API 클라이언트
    └── auth.js               # 인증 API
```

### 3.2 🔴 미구현 기능 (반드시 필요)

| 기능 | 설명 | 구현 위치 | 난이도 |
|------|------|----------|--------|
| **사용자 생성 UI** | 관리자가 직접 사용자 생성 | AdminDashboard.jsx > Users 탭 | ⭐⭐ |
| **비밀번호 초기화 UI** | 비밀번호 리셋 버튼 및 결과 표시 | UserDetailModal.jsx | ⭐⭐ |
| **역할 변경 UI** | 관리자/일반 사용자 역할 변경 | UserDetailModal.jsx | ⭐⭐ |
| **API 키 관리 UI** | API 키 조회/수정/삭제 | UserDetailModal.jsx | ⭐⭐⭐ |
| **시스템 설정 페이지** | 전역 설정 변경 기능 | 새 페이지 필요 | ⭐⭐⭐ |
| **실시간 알림** | 긴급 상황 알림 표시 | AdminDashboard.jsx | ⭐⭐⭐ |

### 3.3 🟡 개선 필요 기능 (권장)

| 기능 | 현재 상태 | 개선 방향 |
|------|----------|----------|
| **날짜 필터링** | 로그에만 limit 필터 | 모든 목록에 날짜 범위 필터 추가 |
| **데이터 내보내기** | 미구현 | CSV/Excel 내보내기 기능 |
| **대시보드 차트** | 테이블만 있음 | Chart.js/Recharts로 시각화 |
| **검색 기능** | 기본 검색만 | 고급 검색 (다중 조건) |
| **페이지네이션** | 클라이언트 사이드 | 서버 사이드 페이지네이션 |
| **모바일 반응형** | 미구현 | 관리자 페이지 모바일 대응 |
| **다크 모드** | 미구현 | 테마 스위칭 기능 |

### 3.4 관리자 페이지 개선 작업 체크리스트

```markdown
## 사용자 관리 탭
- [ ] 사용자 생성 버튼 및 모달 추가
- [ ] 비밀번호 초기화 버튼 (UserDetailModal)
- [ ] 역할 변경 드롭다운 (UserDetailModal)
- [ ] API 키 관리 섹션 (UserDetailModal)
- [ ] 사용자 삭제 기능 (주의 필요)
- [ ] 2FA 상태 표시 및 해제 기능

## 봇 관리 탭
- [ ] 봇 상태별 필터링
- [ ] 봇 설정 조회/수정
- [ ] 봇 실행 이력 조회

## 전체 개요 탭
- [ ] 실시간 P&L 차트 (Recharts 사용)
- [ ] 거래량 추이 차트
- [ ] 사용자 가입 추이 차트
- [ ] 날짜 범위 선택기

## 로그 조회 탭
- [ ] 날짜 범위 필터
- [ ] 로그 내용 검색
- [ ] 로그 레벨별 색상 구분 강화
- [ ] 로그 내보내기 (CSV)

## 신규 페이지 필요
- [ ] 시스템 설정 페이지
- [ ] 알림 설정 페이지
- [ ] 보안 설정 페이지 (IP 화이트리스트 등)
```

### 3.5 백엔드 관리자 API 보완 필요 사항

| API | 위치 | 상태 | 필요 작업 |
|-----|------|------|----------|
| `POST /admin/users` | 미구현 | ❌ | 사용자 생성 API 추가 |
| `DELETE /admin/users/{id}` | 미구현 | ❌ | 사용자 삭제 API 추가 |
| `PUT /admin/users/{id}/2fa/disable` | 미구현 | ❌ | 2FA 해제 API 추가 |
| `GET /admin/settings` | 미구현 | ❌ | 시스템 설정 조회 |
| `PUT /admin/settings` | 미구현 | ❌ | 시스템 설정 변경 |
| `GET /admin/audit-log` | 미구현 | ❌ | 관리자 감사 로그 |
| `POST /admin/ip-whitelist` | 미구현 | ❌ | IP 화이트리스트 관리 |

---

## 4. 🟢 추가해야 할 기능

### 4.1 백엔드 기능

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **이메일 알림** | 중요 이벤트 시 이메일 발송 | 높음 |
| **Telegram 봇 통합** | 거래 알림 텔레그램 전송 | 높음 |
| **Redis 캐싱** | API 응답 캐싱, 세션 관리 | 높음 |
| **WebSocket 개선** | 실시간 P&L 업데이트 | 중간 |
| **백업 자동화** | 데이터베이스 자동 백업 | 중간 |
| **다중 거래소 지원** | Binance, OKX 추가 | 낮음 |

### 4.2 프론트엔드 기능

| 기능 | 설명 | 우선순위 |
|------|------|----------|
| **알림 센터** | 인앱 알림 표시 | 높음 |
| **다국어 지원** | 영어/한국어 전환 | 중간 |
| **다크 모드** | 테마 스위칭 | 중간 |
| **PWA 지원** | 모바일 앱 설치 | 낮음 |
| **차트 개선** | TradingView 위젯 통합 | 중간 |

---

## 5. 🔧 코드 품질 개선

### 5.1 백엔드 코드 이슈

| 파일 | 이슈 | 해결 방법 |
|------|------|----------|
| `admin_users.py:182` | `total_balance: 0.0` 하드코딩 | 실제 잔고 조회 구현 |
| `admin_users.py:188-189` | `strategy_name`, `symbol` "N/A" | BotStatus 모델 확장 |
| 여러 파일 | `import logging` 중복 | 통합 로거 사용 |
| 여러 파일 | 예외 처리 불일치 | 통합 예외 핸들러 사용 |

### 5.2 프론트엔드 코드 이슈

| 파일 | 이슈 | 해결 방법 |
|------|------|----------|
| `AdminDashboard.jsx` | 1044줄로 너무 김 | 컴포넌트 분리 |
| `Settings.jsx` | 1000줄+ | 설정별 컴포넌트 분리 |
| 여러 파일 | 인라인 스타일 과다 | CSS 모듈 또는 styled-components |
| 여러 파일 | console.log 남아있음 | 프로덕션 빌드 전 제거 |

### 5.3 테스트 코드 현황

| 영역 | 현재 상태 | 권장 사항 |
|------|----------|----------|
| **백엔드 단위 테스트** | 일부만 존재 | pytest 테스트 확대 |
| **API 통합 테스트** | 미흡 | pytest-asyncio로 API 테스트 |
| **프론트엔드 테스트** | 없음 | Jest + React Testing Library |
| **E2E 테스트** | 없음 | Playwright 또는 Cypress |

---

## 6. 📝 TODO 목록 정리

### 코드에 남아있는 TODO 주석

```python
# backend/src/api/admin_users.py:182
"total_balance": 0.0,  # TODO: 실제 잔고 조회 구현

# backend/src/api/admin_users.py:216
"api_key_last_used": None,  # TODO: 마지막 사용 시각 추적 구현 시 추가

# backend/src/api/admin_users.py:530
# TODO: 향후 Redis 기반 토큰 블랙리스트 구현 시 개선
```

---

## 7. 🚀 배포 전 체크리스트

### 7.1 환경 변수 필수 설정

```bash
# 필수
JWT_SECRET=<매우_복잡한_랜덤_문자열>
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/<db>
ENCRYPTION_KEY=<32바이트_랜덤_키>

# 권장
CORS_ORIGINS=https://your-domain.com
ENVIRONMENT=production
DEBUG=false
DEEPSEEK_API_KEY=<DeepSeek_API_키>
```

### 7.2 보안 체크리스트

- [ ] JWT_SECRET 변경
- [ ] DATABASE_URL 프로덕션 값 설정
- [ ] CORS_ORIGINS 프로덕션 도메인만 허용
- [ ] HTTPS 적용 (Let's Encrypt)
- [ ] Nginx 보안 헤더 설정
- [ ] 방화벽 설정 (필요한 포트만 개방)
- [ ] 관리자 IP 화이트리스트 적용
- [ ] 데이터베이스 백업 설정
- [ ] 로그 모니터링 설정

### 7.3 성능 체크리스트

- [ ] 데이터베이스 인덱스 확인
- [ ] Redis 캐싱 적용
- [ ] 정적 파일 CDN 적용
- [ ] Gzip 압축 활성화
- [ ] Docker 이미지 최적화

---

## 📌 작업 우선순위 요약

### 긴급 (배포 전 필수)

1. ✅ **JWT_SECRET, DATABASE_URL 환경변수 설정** - `ENVIRONMENT_SETUP.md` 가이드 생성
2. ✅ **CORS 프로덕션 도메인 설정** - `ENVIRONMENT_SETUP.md` 가이드 생성
3. ✅ **관리자 IP 제한 구현** - `backend/src/middleware/admin_ip_whitelist.py` 생성

### 높음 (1주일 내)

4. 관리자 페이지 - 사용자 생성/비밀번호 초기화 UI
5. 관리자 페이지 - 역할 변경 UI
6. Redis 토큰 블랙리스트 (강제 로그아웃용)
7. 2FA 백업 코드 시스템

### 중간 (1개월 내)

8. 관리자 페이지 - API 키 관리 UI
9. 관리자 페이지 - 시스템 설정 페이지
10. 관리자 페이지 - 데이터 시각화 차트
11. 이메일/Telegram 알림 시스템
12. 테스트 코드 작성

### 낮음 (추후)

13. 다국어 지원
14. 다크 모드
15. 다중 거래소 지원
16. PWA 지원

---

## 📞 연락처

추가 질문이 있으시면 코드베이스의 `DEVELOPMENT_GUIDE.md` 또는 `README.md`를 참조하세요.

---

## 8. 📊 백테스트 오프라인 데이터 관리

### 8.1 목표

- **API 호출 없이 백테스트 실행**: 다운로드된 캔들 데이터만 사용
- **안정적인 서비스**: Rate Limit 문제 없이 연속 테스트 가능
- **주기적 데이터 업데이트**: 15일 또는 1개월마다 수동 갱신

### 8.2 현재 구현 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| 캐시 시스템 | ✅ 완료 | `backend/src/services/candle_cache.py` |
| cache_only 모드 | ✅ 완료 | API 호출 차단 옵션 |
| 캐시 디렉토리 | ✅ 완료 | `backend/candle_cache/` |
| 다운로드 스크립트 | ⏳ 필요 | 별도 스크립트 작성 필요 |

### 8.3 추가 작업 필요

| # | 작업 | 예상 시간 |
|---|------|----------|
| 1 | 데이터 다운로드 스크립트 생성 | 30분 |
| 2 | 3년치 데이터 초기 다운로드 | 1-2시간 |
| 3 | crontab 자동 업데이트 설정 | 10분 |
| 4 | 프론트엔드 데이터 범위 표시 | 30분 |

### 8.4 상세 가이드

👉 **상세 구현 가이드**: [`BACKTEST_OFFLINE_DATA_GUIDE.md`](./BACKTEST_OFFLINE_DATA_GUIDE.md)

포함 내용:

- 다운로드 스크립트 전체 코드
- 데이터 관리 계획 (심볼, 타임프레임, 용량)
- crontab 설정 방법
- API 엔드포인트 추가
