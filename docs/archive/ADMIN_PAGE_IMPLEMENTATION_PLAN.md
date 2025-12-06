# 관리자 페이지 구현 계획서 (Admin Dashboard Implementation Plan)

> **작성일**: 2025-12-04
> **목적**: 일반 회원 프론트엔드와 완전히 분리된 독립 관리자 인터페이스 구축
> **기반 문서**: Admin_Structure_Outline.md 분석 및 현재 백엔드/프론트엔드 역량 검증

---

## 📋 Executive Summary

본 계획서는 자동매매 플랫폼의 **완전히 독립된 관리자 대시보드**를 구축하기 위한 상세 로드맵입니다.

### 핵심 전략
1. **완전 분리**: `/frontend` (사용자용)과 `/admin` (관리자용) 완전 분리
2. **실용 중심**: Admin_Structure_Outline.md의 9대 모듈을 현재 백엔드 API 역량에 맞춰 재구성
3. **단계적 구현**: Phase 1 (핵심), Phase 2 (고급), Phase 3 (미래 확장)

---

## 🔍 현재 시스템 분석 (Current System Analysis)

### ✅ 백엔드 API 현황

#### 구현 완료된 Admin APIs
| API 엔드포인트 | 기능 | 상태 |
|---------------|------|------|
| `GET /admin/users` | 전체 사용자 목록 조회 | ✅ 완료 |
| `GET /admin/users/{user_id}` | 사용자 상세 정보 | ✅ 완료 |
| `GET /admin/users/{user_id}/api-keys` | 사용자 API 키 조회 (마스킹) | ✅ 완료 |
| `POST /admin/users/{user_id}/api-keys` | API 키 등록 | ✅ 완료 |
| `PUT /admin/users/{user_id}/api-keys/{key_id}` | API 키 수정 | ✅ 완료 |
| `DELETE /admin/users/{user_id}/api-keys/{key_id}` | API 키 삭제 | ✅ 완료 |
| `GET /admin/monitoring/stats` | 실시간 모니터링 통계 | ✅ 완료 |
| `GET /admin/monitoring/backtest/summary` | 백테스트 요약 통계 | ✅ 완료 |
| `GET /admin/monitoring/health` | 시스템 헬스체크 | ✅ 완료 |
| `POST /admin/monitoring/reset-stats` | 모니터링 통계 초기화 | ✅ 완료 |
| `GET /admin/system/diagnostics/encryption` | 암호화 시스템 진단 | ✅ 완료 |

#### 전략 관리 APIs (Strategy Management)
| API 엔드포인트 | 기능 | 상태 |
|---------------|------|------|
| `POST /strategy/create` | 공용 전략 생성 (관리자) | ✅ 완료 |
| `POST /strategy/update/{id}` | 공용 전략 수정 | ✅ 완료 |
| `GET /strategy/list` | 공용 전략 목록 조회 | ✅ 완료 |
| `DELETE /strategy/{id}` | 공용 전략 삭제 | ✅ 완료 |
| `PATCH /strategy/{id}/toggle` | 전략 활성화/비활성화 | ✅ 완료 |
| `POST /ai/strategies/generate` | AI 전략 생성 (사용자용) | ✅ 완료 |
| `GET /ai/status` | AI 서비스 상태 확인 | ✅ 완료 |

#### 모니터링 시스템 (SimpleMonitor)
- ✅ API 요청 통계 (endpoint별 count, response time, errors)
- ✅ 시스템 리소스 모니터링 (CPU, Memory, Disk)
- ✅ 활성 사용자 추적
- ✅ 백테스트 통계 (total, queued, running, completed, failed)

#### 데이터베이스 모델
- ✅ User (id, email, created_at)
- ✅ ApiKey (암호화된 API 키 관리)
- ✅ Strategy (전략 정보)
- ✅ BotStatus (봇 상태 추적)
- ✅ Trade (거래 기록)
- ✅ Position (포지션 정보)
- ✅ Equity (자산 변동 기록)
- ✅ BotLog (봇 로그)
- ✅ BotConfig (봇 설정)
- ✅ OpenOrder (미체결 주문)
- ✅ BacktestResult (백테스트 결과)
- ✅ BacktestTrade (백테스트 거래)
- ✅ SystemAlert (시스템 알림)
- ✅ RiskSettings (리스크 설정)
- ✅ TradingSignal (트레이딩 시그널)

### ❌ 부족한 백엔드 기능 (현재 미구현)

#### Critical - 즉시 구현 필요
1. **봇 제어 API**
   - ❌ `POST /admin/bots/{user_id}/pause` - 특정 사용자 봇 강제 정지
   - ❌ `POST /admin/bots/{user_id}/restart` - 특정 사용자 봇 재시작
   - ❌ `POST /admin/bots/pause-all` - 전체 봇 긴급 정지 (비상 제어)
   - ❌ `GET /admin/bots/active` - 활성 봇 목록 및 상태

2. **사용자 제어 API**
   - ❌ `POST /admin/users/{user_id}/suspend` - 계정 정지
   - ❌ `POST /admin/users/{user_id}/activate` - 계정 활성화
   - ❌ `POST /admin/users/{user_id}/force-logout` - 강제 로그아웃

3. **글로벌 통계 API**
   - ❌ `GET /admin/analytics/global-pnl` - 전체 사용자 P&L 합계
   - ❌ `GET /admin/analytics/total-aum` - 총 관리 자산 (Total AUM)
   - ❌ `GET /admin/analytics/risk-users` - 위험 사용자 Top 5 (MDD, 청산 위험)

4. **로그 및 이벤트 API**
   - ❌ `GET /admin/logs/system` - 시스템 로그 조회 (필터: CRITICAL, ERROR, WARNING)
   - ❌ `GET /admin/logs/trading` - 거래 로그 조회
   - ❌ `GET /admin/events/timeline` - 전체 이벤트 타임라인

#### Optional - 향후 고도화
5. **전략 배포 관리**
   - ❌ `POST /admin/strategy/upload` - 신규 전략 업로드
   - ❌ `POST /admin/strategy/deploy` - 전략 배포 (전체/선택)
   - ❌ `POST /admin/strategy/rollback` - 전략 롤백

6. **알림 및 공지**
   - ❌ `POST /admin/notifications/create` - 시스템 공지 생성
   - ❌ `GET /admin/alerts/system` - 시스템 알림 목록
   - ❌ `POST /admin/alerts/{alert_id}/acknowledge` - 알림 확인 처리

7. **보안 및 감사**
   - ❌ `GET /admin/audit/login-attempts` - 로그인 시도 기록
   - ❌ `GET /admin/audit/policy-violations` - 정책 위반 목록
   - ❌ `GET /admin/audit/api-key-changes` - API 키 변경 감사 로그

---

## 🎯 Admin_Structure_Outline.md 분석 및 적용 전략

### ✅ 채택: 현재 백엔드로 즉시 구현 가능

| 모듈 | 채택 여부 | 백엔드 지원 | 우선순위 |
|------|----------|-----------|---------|
| **I. 통합 관제 대시보드** | ✅ 부분 채택 | `/admin/monitoring/stats`, `/admin/monitoring/health` | **P0 (즉시)** |
| **II. 사용자 및 봇 모니터링** | ✅ 부분 채택 | `/admin/users`, `/admin/users/{id}` | **P0 (즉시)** |
| **III. 보안 및 감사** | ✅ 부분 채택 | `/admin/users/{id}/api-keys` (CRUD) | **P1 (우선)** |
| **IV. 전략 관리** | ✅ **완전 채택** | `/strategy/*` (CRUD, toggle), `/ai/*` (AI 생성, 상태) | **P0 (즉시)** |
| **V. 서버 및 인프라 관리** | ✅ 부분 채택 | `/admin/monitoring/stats` (CPU, Memory, Disk) | **P0 (즉시)** |

### 🔧 수정 필요: 백엔드 API 추가 개발 후 구현

| 모듈 | 수정 사항 | 필요한 백엔드 작업 | 우선순위 |
|------|-----------|-------------------|---------|
| **II. 봇 제어 기능** | 봇 강제 정지/재시작 추가 필요 | `POST /admin/bots/{user_id}/pause` 등 | **P0 (즉시)** |
| **I. 글로벌 P&L/AUM** | 통계 계산 API 필요 | `GET /admin/analytics/global-pnl` | **P1 (우선)** |
| **VII. 통합 이벤트 타임라인** | 이벤트 로그 조회 API 필요 | `GET /admin/events/timeline` | **P2 (차순위)** |

### ❌ 제외: 현재 시스템에 불필요하거나 과도한 기능

| 모듈 | 제외 이유 |
|------|-----------|
| **VI. 글로벌 알림 및 공지 - 템플릿 관리** | 초기 단계에서는 단순 공지 생성만으로 충분. 템플릿 관리는 과도 |
| **VIII. 전역 검색 기능** | 유용하지만 ElasticSearch 등 추가 인프라 필요. Phase 3로 연기 |
| **IX. 운영자 알림 라우팅** | Slack/Telegram 연동은 고도화 기능. Phase 2로 연기 |

---

## 🏗️ 프로젝트 구조 (Project Structure)

### 폴더 구조

```
/Users/mr.joo/Desktop/auto-dashboard/
├── backend/                  # 기존 백엔드 (변경 없음)
│   ├── src/
│   │   ├── api/
│   │   │   ├── admin_*.py   # 관리자 API (기존 + 신규)
│   │   └── ...
│
├── frontend/                 # 일반 사용자 프론트엔드 (변경 없음)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── LiveTrading.jsx
│   │   │   └── ...
│   └── ...
│
└── admin/                    # 🆕 관리자 전용 프론트엔드 (신규)
    ├── public/
    ├── src/
    │   ├── api/             # 백엔드 API 호출
    │   │   ├── adminAPI.js  # Admin API wrapper
    │   │   └── auth.js      # Admin 인증
    │   │
    │   ├── components/      # 공통 컴포넌트
    │   │   ├── layout/
    │   │   │   ├── AdminLayout.jsx
    │   │   │   ├── AdminSidebar.jsx
    │   │   │   └── AdminHeader.jsx
    │   │   ├── charts/
    │   │   │   ├── SystemResourceChart.jsx
    │   │   │   ├── GlobalPnLChart.jsx
    │   │   │   └── ...
    │   │   └── common/
    │   │       ├── DataTable.jsx
    │   │       ├── StatCard.jsx
    │   │       └── StatusBadge.jsx
    │   │
    │   ├── context/         # Context Providers
    │   │   ├── AdminAuthContext.jsx
    │   │   └── AdminThemeContext.jsx
    │   │
    │   ├── pages/           # 관리자 페이지
    │   │   ├── AdminLogin.jsx
    │   │   ├── Dashboard.jsx              # I. 통합 관제 대시보드
    │   │   ├── UserManagement.jsx         # II. 사용자 관리
    │   │   ├── BotMonitoring.jsx          # II. 봇 모니터링 및 제어
    │   │   ├── ApiKeySecurity.jsx         # III. API 키 보안 관리
    │   │   ├── SystemInfra.jsx            # V. 서버 및 인프라
    │   │   ├── BacktestMonitoring.jsx     # 백테스트 통계
    │   │   └── Settings.jsx               # 관리자 설정
    │   │
    │   ├── utils/           # 유틸리티
    │   │   ├── formatters.js
    │   │   └── validators.js
    │   │
    │   ├── App.jsx          # 관리자 앱 루트
    │   ├── main.jsx         # 엔트리 포인트
    │   └── index.css
    │
    ├── package.json
    ├── vite.config.js
    └── README.md
```

### 기술 스택

#### Admin Frontend
- **Framework**: React 19.2.0 (일반 사용자와 동일)
- **UI Library**: Ant Design 6.0.0 (일반 사용자와 동일)
- **Routing**: React Router 7.9.6
- **Charts**: Recharts 3.5.1 (시스템 리소스, P&L 차트)
- **HTTP Client**: Axios 1.13.2
- **Build Tool**: Vite 7.2.4

#### 포트 분리 전략
- **일반 사용자**: `http://localhost:5173` (기존)
- **관리자**: `http://localhost:5174` (신규, vite.config.js에서 포트 변경)

---

## 📅 구현 로드맵 (Implementation Roadmap)

### Phase 1: 핵심 기능 (Core Features) - 최우선 구현

#### Backend 작업 (4~5시간)

1. **봇 제어 API 추가** (`/backend/src/api/admin_bots.py`)
   ```python
   # 신규 엔드포인트
   POST /admin/bots/active                    # 활성 봇 목록
   POST /admin/bots/{user_id}/pause           # 봇 강제 정지
   POST /admin/bots/{user_id}/restart         # 봇 재시작
   POST /admin/bots/pause-all                 # 전체 봇 긴급 정지
   ```

2. **사용자 제어 API 추가** (`/backend/src/api/admin_users.py` 확장)
   ```python
   POST /admin/users/{user_id}/suspend        # 계정 정지
   POST /admin/users/{user_id}/activate       # 계정 활성화
   ```

3. **글로벌 통계 API 추가** (`/backend/src/api/admin_analytics.py`)
   ```python
   GET /admin/analytics/global-summary        # 총 AUM, 전체 P&L, 활성 사용자/봇
   GET /admin/analytics/risk-users            # 위험 사용자 Top 5
   ```

4. **로그 조회 API 추가** (`/backend/src/api/admin_logs.py`)
   ```python
   GET /admin/logs/system?level=CRITICAL      # 시스템 로그 필터
   GET /admin/logs/bot?user_id=X              # 봇 로그 조회
   ```

#### Frontend 작업 (8~10시간)

1. **프로젝트 초기화**
   - `/admin` 폴더 생성 및 Vite 프로젝트 설정
   - Ant Design, React Router, Axios 설치
   - 포트 5174로 설정

2. **인증 시스템**
   - `AdminAuthContext.jsx` - JWT 토큰 관리
   - `AdminLogin.jsx` - 관리자 로그인 페이지 (require_admin 검증)
   - Protected Route 설정

3. **핵심 페이지 구현**
   - **Dashboard.jsx** (I. 통합 관제 대시보드)
     - 시스템 건전성 표시 (CPU, Memory, Disk)
     - 글로벌 통계 카드 (Total AUM, 활성 사용자/봇, P&L)
     - 최근 시스템 오류 목록

   - **UserManagement.jsx** (II. 사용자 관리)
     - 전체 사용자 목록 테이블 (User ID, Email, 가입일)
     - 사용자 검색 및 정렬
     - 사용자 상세 보기 모달
     - 계정 정지/활성화 버튼

   - **BotMonitoring.jsx** (II. 봇 모니터링)
     - 활성 봇 목록 (User ID, Strategy, Status, Uptime)
     - 개별 봇 강제 정지/재시작 버튼
     - 🚨 전체 봇 긴급 정지 버튼 (확인 모달 필수)

   - **ApiKeySecurity.jsx** (III. API 키 관리)
     - 사용자별 API 키 조회 (마스킹 표시)
     - API 키 추가/수정/삭제 기능

   - **StrategyManagement.jsx** (IV. 전략 관리)
     - 공용 전략 목록 (관리자가 만든 전략, user_id=NULL)
     - 전략 생성/수정/삭제 (수동)
     - AI 전략 생성 버튼 (DeepSeek AI 활용)
     - 전략 활성화/비활성화 토글
     - AI 서비스 상태 표시

   - **SystemInfra.jsx** (V. 서버 및 인프라)
     - CPU/Memory/Disk 사용량 실시간 게이지
     - 시간별 사용량 추이 차트 (Recharts)
     - 시스템 헬스체크 상태 표시

4. **공통 컴포넌트**
   - `AdminLayout.jsx` - 사이드바, 헤더가 있는 레이아웃
   - `AdminSidebar.jsx` - 관리자 메뉴 네비게이션
   - `StatCard.jsx` - 통계 카드 컴포넌트
   - `SystemResourceChart.jsx` - 시스템 리소스 차트

### Phase 2: 고급 기능 (Advanced Features) - 우선 구현

#### Backend 작업 (3~4시간)

1. **이벤트 타임라인 API** (`/backend/src/api/admin_events.py`)
   ```python
   GET /admin/events/timeline?limit=100       # 통합 이벤트 스트림
   # SystemAlert, BotLog, Trade 테이블 통합 조회
   ```

2. **보안 감사 API** (`/backend/src/api/admin_audit.py`)
   ```python
   GET /admin/audit/api-key-changes          # API 키 변경 이력
   GET /admin/audit/login-attempts           # 로그인 실패 기록
   ```

3. **알림 관리 API** (`/backend/src/api/admin_notifications.py`)
   ```python
   POST /admin/notifications/create          # 시스템 공지 생성
   GET /admin/notifications/list             # 공지 목록
   ```

#### Frontend 작업 (4~5시간)

1. **EventTimeline.jsx** (VII. 통합 이벤트 타임라인)
   - 시간순 이벤트 스트림 표시
   - 이벤트 타입별 필터 (ERROR, TRADE, USER_ACTION)
   - 무한 스크롤 또는 페이지네이션

2. **AuditLogs.jsx** (III. 보안 및 감사)
   - API 키 변경 이력 테이블
   - 로그인 실패 기록
   - 의심 IP 필터

3. **Notifications.jsx** (VI. 공지 관리)
   - 시스템 공지 생성 폼
   - 공지 목록 및 편집

### Phase 3: 미래 확장 (Future Enhancements) - 장기 계획

1. **전역 검색 기능** (VIII)
   - ElasticSearch 또는 MeiliSearch 도입
   - User ID, Order ID, Log 전체 검색

2. **전략 배포 시스템** (IV)
   - 전략 파일 업로드/버전 관리
   - A/B 테스트 배포

3. **외부 알림 연동** (IX)
   - Slack/Telegram Webhook 설정
   - 치명적 오류 자동 알림

4. **대시보드 고도화**
   - WebSocket 실시간 업데이트
   - 커스터마이징 가능한 위젯

---

## 🎨 UI/UX 설계 원칙

### 디자인 가이드라인

1. **색상 체계**
   - Primary: Ant Design Blue (#1890ff) - 일반 액션
   - Success: Green (#52c41a) - 정상 상태
   - Warning: Orange (#faad14) - 경고
   - Error: Red (#f5222d) - 오류, 위험
   - Danger: Dark Red (#cf1322) - 치명적 액션 (전체 봇 정지 등)

2. **레이아웃**
   - 좌측 고정 사이드바 (200px)
   - 상단 헤더 (관리자 정보, 로그아웃)
   - 메인 컨텐츠 영역 (스크롤 가능)

3. **데이터 표시**
   - 테이블: Ant Design Table (정렬, 필터, 페이지네이션)
   - 통계 카드: 4칸 그리드 레이아웃
   - 차트: Recharts (Area Chart, Line Chart, Gauge)

4. **인터랙션**
   - 위험한 작업 (봇 정지, 계정 정지)은 확인 모달 필수
   - 로딩 상태 명확히 표시 (Ant Design Spin)
   - 성공/실패 메시지 (Ant Design message)

### 반응형 디자인
- 최소 해상도: 1280x720 (관리자 작업용 모니터 기준)
- 모바일 지원 없음 (관리자 페이지는 데스크톱 전용)

---

## 🔐 보안 고려사항

### 인증 및 권한

1. **관리자 인증**
   - 백엔드: `require_admin` 의존성 (user.is_admin 체크)
   - 프론트엔드: JWT 토큰에서 is_admin 클레임 확인
   - 관리자 권한 없으면 403 Forbidden

2. **API 보안**
   - 모든 `/admin/*` 엔드포인트는 `require_admin` 필수
   - Rate Limiting 적용 (관리자도 과도한 요청 방지)

3. **민감 정보 보호**
   - API 키는 마스킹 표시 (`****1234`)
   - 비밀번호는 절대 표시하지 않음
   - 로그에 민감 정보 포함 금지

### 감사 로깅

1. **관리자 액션 기록**
   - 사용자 계정 정지/활성화
   - 봇 강제 정지/재시작
   - API 키 추가/수정/삭제
   - 전체 봇 긴급 정지 (CRITICAL 로그)

2. **로그 형식**
   ```json
   {
     "timestamp": "2025-12-04T10:30:00Z",
     "admin_id": 1,
     "admin_email": "admin@example.com",
     "action": "user_suspended",
     "target_user_id": 42,
     "reason": "Policy violation",
     "ip_address": "192.168.1.100"
   }
   ```

---

## 📊 성능 최적화

### 프론트엔드 최적화

1. **React.memo 활용**
   - StatCard, DataTable 등 자주 렌더링되는 컴포넌트 메모이제이션

2. **데이터 페칭 전략**
   - 대시보드 통계: 30초마다 자동 갱신 (setInterval)
   - 사용자 목록: 페이지네이션 (limit=50)
   - 로그 조회: 무한 스크롤 또는 limit=100

3. **차트 최적화**
   - 시스템 리소스 차트: 최근 100개 데이터포인트만 표시
   - 큰 데이터셋은 샘플링 또는 집계

### 백엔드 최적화

1. **캐싱**
   - 글로벌 통계: Redis 캐시 60초 TTL
   - 사용자 목록: 캐시 없음 (실시간 정확성 중요)

2. **쿼리 최적화**
   - 인덱스: user_id, created_at, status 칼럼
   - N+1 문제 방지: SQLAlchemy joinedload 사용

---

## 🧪 테스트 전략

### Phase 1 테스트 항목

1. **백엔드 API 테스트**
   - 관리자 권한 검증 (require_admin)
   - 봇 제어 API 정상 동작 확인
   - 글로벌 통계 계산 정확성 검증

2. **프론트엔드 기능 테스트**
   - 관리자 로그인 및 권한 체크
   - 대시보드 통계 표시 정확성
   - 봇 제어 버튼 동작 확인
   - 사용자 계정 정지/활성화 확인

3. **통합 테스트**
   - 일반 사용자가 `/admin` 접근 시 403 확인
   - 관리자가 봇 정지 시 실제 봇 프로세스 정지 확인

---

## 📝 개발 체크리스트

### Phase 1 - 핵심 기능 구현

#### Backend (4~5시간)
- [ ] `admin_bots.py` 생성 - 봇 제어 API 4개
- [ ] `admin_users.py` 확장 - 계정 정지/활성화 API 2개
- [ ] `admin_analytics.py` 생성 - 글로벌 통계 API 2개
- [ ] `admin_logs.py` 생성 - 로그 조회 API 2개
- [x] ~~전략 관리 API~~ - 이미 완료 (`/strategy/*`, `/ai/*`)
- [ ] Pydantic 스키마 정의
- [ ] API 문서화 (docstring)
- [ ] 관리자 권한 테스트

#### Frontend (9~11시간)
- [ ] `/admin` 프로젝트 초기화
  - [ ] Vite 설정 (포트 5174)
  - [ ] package.json 설정
  - [ ] 기본 폴더 구조 생성
- [ ] 인증 시스템
  - [ ] `AdminAuthContext.jsx` 구현
  - [ ] `AdminLogin.jsx` 페이지
  - [ ] ProtectedRoute 컴포넌트
- [ ] 레이아웃
  - [ ] `AdminLayout.jsx` 구현
  - [ ] `AdminSidebar.jsx` 메뉴
  - [ ] `AdminHeader.jsx` 헤더
- [ ] 핵심 페이지 6개
  - [ ] `Dashboard.jsx` - 통합 관제 대시보드
  - [ ] `UserManagement.jsx` - 사용자 관리
  - [ ] `BotMonitoring.jsx` - 봇 모니터링
  - [ ] `ApiKeySecurity.jsx` - API 키 관리
  - [ ] `StrategyManagement.jsx` - 전략 관리 (공용 전략 CRUD + AI 생성)
  - [ ] `SystemInfra.jsx` - 서버 인프라
- [ ] 공통 컴포넌트
  - [ ] `StatCard.jsx` - 통계 카드
  - [ ] `SystemResourceChart.jsx` - 리소스 차트
- [ ] API 연동
  - [ ] `adminAPI.js` - Axios wrapper
  - [ ] 에러 핸들링
- [ ] 테스트 및 디버깅

### Phase 2 - 고급 기능 (향후)
- [ ] EventTimeline.jsx
- [ ] AuditLogs.jsx
- [ ] Notifications.jsx

---

## 🚀 배포 전략

### 개발 환경
- **백엔드**: `http://localhost:8000`
- **일반 사용자**: `http://localhost:5173`
- **관리자**: `http://localhost:5174`

### 프로덕션 환경
- **백엔드**: `https://api.yourdomain.com`
- **일반 사용자**: `https://app.yourdomain.com`
- **관리자**: `https://admin.yourdomain.com` (별도 서브도메인)

### Docker 배포
```yaml
# docker-compose.yml에 admin 서비스 추가
services:
  admin:
    build:
      context: ./admin
      dockerfile: Dockerfile
    ports:
      - "5174:80"
    environment:
      - VITE_API_BASE_URL=https://api.yourdomain.com
    networks:
      - app-network
```

---

## 📚 참고 자료

### 기술 문서
- [Ant Design Admin Dashboard Template](https://ant.design/components/overview/)
- [React Router Protected Routes](https://reactrouter.com/en/main/start/overview)
- [Recharts Documentation](https://recharts.org/en-US/)
- [FastAPI Admin Best Practices](https://fastapi.tiangolo.com/tutorial/security/)

### 프로젝트 관련 문서
- `Admin_Structure_Outline.md` - 원본 관리자 페이지 설계
- `IMPLEMENTATION_PLAN.md` - 전체 프로젝트 구현 계획
- `backend/src/api/admin_*.py` - 기존 관리자 API
- `backend/src/utils/monitoring.py` - 모니터링 시스템

---

## 🎯 성공 기준 (Success Criteria)

### Phase 1 완료 기준
1. ✅ 관리자 로그인 성공 (일반 사용자는 접근 불가)
2. ✅ 대시보드에서 시스템 리소스 실시간 표시
3. ✅ 전체 사용자 목록 조회 및 검색 가능
4. ✅ 특정 사용자 봇 강제 정지/재시작 가능
5. ✅ 전체 봇 긴급 정지 버튼 동작 (확인 모달 포함)
6. ✅ API 키 조회 및 관리 가능
7. ✅ 계정 정지/활성화 기능 동작
8. ✅ 공용 전략 생성/수정/삭제 가능
9. ✅ AI 전략 생성 버튼 동작 (DeepSeek AI 연동)
10. ✅ 전략 활성화/비활성화 토글 동작
11. ✅ 백엔드 API 모두 관리자 권한 검증

### 전체 프로젝트 성공 기준
- 일반 사용자와 관리자 인터페이스 완전 분리
- 관리자는 시스템 전체를 한눈에 파악 가능
- 긴급 상황 시 신속한 제어 가능 (봇 정지, 계정 정지)
- 보안 감사 및 로깅 완비
- 안정적인 성능 (30초마다 자동 갱신에도 부드러운 UX)

---

## 📞 문의 및 피드백

- **작성자**: Claude Code Assistant
- **작성일**: 2025-12-04
- **버전**: v1.0
- **다음 단계**: Phase 1 백엔드 API 구현 시작

---

**이 계획서를 바탕으로 완벽한 관리자 페이지를 구축하겠습니다!** 🚀
