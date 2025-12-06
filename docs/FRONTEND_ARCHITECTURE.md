# 🎨 자동매매 플랫폼 프론트엔드 핵심 구성

## 📋 6대 핵심 모듈 설계

---

## I. 핵심 대시보드 (Dashboard)

### 목적

시스템 전반의 '건강 상태'를 한눈에 파악

### 필수 3대 요소

#### 1. 성과 추이 그래프

**컴포넌트**: `PerformanceChart.jsx`

```
📊 기능:
- 일별/주별/월별 수익률 라인 차트
- 누적 수익률 곡선
- 벤치마크 비교 (BTC 보유 vs 전략)
- 기간 선택 필터 (1D, 1W, 1M, 3M, 1Y, ALL)

📐 데이터:
- GET /api/analytics/equity-curve
- 시간대별 잔고 변화 데이터
```

#### 2. 핵심 리스크 지표

**컴포넌트**: `RiskMetrics.jsx`

```
⚠️ 표시 항목:
- 현재 MDD (Max Drawdown)
- 샤프 비율 (Sharpe Ratio)
- 승률 (Win Rate)
- 평균 손익비 (Avg Profit/Loss Ratio)
- 일일 변동성 (Daily Volatility)

🎨 UI:
- 카드 그리드 레이아웃 (3x2)
- 위험 수준별 색상 코딩 (녹색/노란색/빨간색)
- 진행바 또는 게이지 차트
```

#### 3. 실시간 잔고 현황 및 시스템 상태

**컴포넌트**: `SystemStatus.jsx`

```
💰 잔고 정보:
- 총 자산 (Total Equity)
- 사용 가능 잔고 (Available Balance)
- 증거금 사용률 (Margin Usage %)
- 미실현 손익 (Unrealized P&L)

🤖 시스템 상태:
- 봇 상태 (실행 중/중지/오류)
- 활성 전략 이름
- 마지막 거래 시간
- WebSocket 연결 상태
- API 연결 상태

📡 실시간 업데이트:
- WebSocket으로 1초마다 갱신
```

### 레이아웃 구조

```
┌─────────────────────────────────────────────────┐
│  Dashboard                                       │
├─────────────────────────────────────────────────┤
│  [시스템 상태 카드]  [잔고 현황 카드]            │
├─────────────────────────────────────────────────┤
│  [성과 추이 그래프 - 전체 너비]                  │
├─────────────────────────────────────────────────┤
│  [리스크 지표 카드 그리드 - 3x2]                 │
└─────────────────────────────────────────────────┘
```

---

## II. 실시간 거래 모니터링 (Live Trading)

### 목적

봇의 '현재 활동' 및 '리스크' 실시간 추적

### 핵심 컴포넌트

#### 1. 현재 포지션 목록

**컴포넌트**: `PositionList.jsx` (기존)

```
📊 표시 정보:
- 심볼, 방향 (Long/Short)
- 진입가, 현재가
- 수량, 레버리지
- 미실현 손익 (금액 & %)
- 진입 시간

🎯 액션:
- 개별 포지션 청산 버튼
- 전체 포지션 청산 버튼
- 손절/익절 설정 모달
```

#### 2. 실시간 P&L

**컴포넌트**: `RealtimePnL.jsx`

```
💹 실시간 표시:
- 총 미실현 손익 (큰 글씨)
- 오늘의 실현 손익
- 이번 주 누적 손익
- 이번 달 누적 손익

📈 시각화:
- 실시간 P&L 라인 차트 (최근 1시간)
- 색상 코딩 (수익: 녹색, 손실: 빨간색)
```

#### 3. 주문 로그

**컴포넌트**: `OrderLog.jsx`

```
📝 로그 항목:
- 시간, 심볼, 주문 타입
- 가격, 수량
- 상태 (체결/대기/취소/실패)
- 체결 금액

🔍 필터:
- 시간 범위 선택
- 심볼 필터
- 상태 필터
- 페이지네이션 (50개씩)
```

#### 4. 시스템 로그

**컴포넌트**: `SystemLog.jsx`

```
🖥️ 로그 타입:
- INFO: 일반 정보
- WARNING: 경고
- ERROR: 오류
- TRADE: 거래 실행

📋 표시:
- 시간, 로그 레벨, 메시지
- 자동 스크롤 (최신 로그 상단)
- 로그 레벨별 색상 구분
```

### 레이아웃 구조

```
┌─────────────────────────────────────────────────┐
│  Live Trading Monitor                            │
├──────────────────────┬──────────────────────────┤
│  [실시간 P&L]        │  [봇 제어 패널]          │
├──────────────────────┴──────────────────────────┤
│  [현재 포지션 목록 - 테이블]                     │
├──────────────────────┬──────────────────────────┤
│  [주문 로그]         │  [시스템 로그]           │
└──────────────────────┴──────────────────────────┘
```

---

## III. 성능 및 히스토리 분석 (Performance & History)

### 목적

전략의 '객관적인 효율성' 심층 분석

### 핵심 컴포넌트

#### 1. 거래 히스토리

**컴포넌트**: `TradeHistory.jsx`

```
📊 테이블 컬럼:
- 거래 ID, 시간
- 심볼, 방향
- 진입가, 청산가
- 수량, 손익 (금액 & %)
- 보유 시간
- 청산 사유

🔍 기능:
- 기간 필터 (날짜 범위 선택)
- 심볼 필터
- 손익 필터 (수익만/손실만)
- CSV 다운로드
- 페이지네이션
```

#### 2. 성과 지표 대시보드

**컴포넌트**: `PerformanceMetrics.jsx`

```
📈 핵심 지표:
- 총 거래 수
- 승률 (Win Rate)
- 평균 수익/손실
- 최대 연속 승/패
- 샤프 비율
- 소르티노 비율
- 최대 낙폭 (MDD)
- 회복 기간

📊 시각화:
- 월별 수익률 히트맵
- 승/패 분포 차트
- 손익 분포 히스토그램
```

#### 3. 기간별 성과 보고서

**컴포넌트**: `PerformanceReport.jsx`

```
📅 기간 선택:
- 일간 (Daily)
- 주간 (Weekly)
- 월간 (Monthly)
- 분기 (Quarterly)
- 연간 (Yearly)

📄 보고서 내용:
- 기간별 수익률
- 거래 통계
- 리스크 지표
- 베스트/워스트 거래
- PDF 다운로드 기능
```

### 레이아웃 구조

```
┌─────────────────────────────────────────────────┐
│  Performance & History                           │
├─────────────────────────────────────────────────┤
│  [기간 선택 탭: 일간/주간/월간/전체]             │
├─────────────────────────────────────────────────┤
│  [성과 지표 카드 그리드 - 4x2]                   │
├─────────────────────────────────────────────────┤
│  [월별 수익률 히트맵]  [손익 분포 차트]          │
├─────────────────────────────────────────────────┤
│  [거래 히스토리 테이블 - 페이지네이션]           │
└─────────────────────────────────────────────────┘
```

---

## IV. 전략 및 백테스팅 관리 (Strategy Management)

### 목적

시스템의 '미래 성능' 검증 및 전략 변경

### 핵심 컴포넌트

#### 1. 전략 목록

**컴포넌트**: `StrategyList.jsx`

```
📋 전략 카드:
- 전략 이름, 설명
- 생성일, 마지막 수정일
- 백테스트 결과 요약 (승률, 샤프 비율)
- 상태 (활성/비활성)

🎯 액션:
- 전략 활성화/비활성화
- 전략 편집
- 전략 삭제
- 백테스트 실행
```

#### 2. 백테스트 실행

**컴포넌트**: `BacktestRunner.jsx`

```
⚙️ 설정:
- 전략 선택
- 기간 설정 (시작일 ~ 종료일)
- 초기 자본
- 수수료율
- 슬리피지

▶️ 실행:
- 백테스트 시작 버튼
- 진행 상태 표시 (프로그레스 바)
- 실시간 로그 출력
```

#### 3. 백테스트 결과

**컴포넌트**: `BacktestResults.jsx`

```
📊 결과 표시:
- 수익률 곡선
- 낙폭 차트
- 월별 수익률 테이블
- 거래 통계
- 리스크 지표

📈 비교 기능:
- 여러 전략 결과 비교
- 벤치마크 비교
- 파라미터 최적화 결과
```

#### 4. 전략 에디터

**컴포넌트**: `StrategyEditor.jsx`

```
✏️ 편집 기능:
- 전략 이름, 설명
- 파라미터 설정 (JSON 에디터)
- 진입/청산 조건
- 리스크 관리 설정

💾 저장:
- 초안 저장
- 검증 후 저장
- 버전 관리
```

### 레이아웃 구조

```
┌─────────────────────────────────────────────────┐
│  Strategy Management                             │
├──────────────────────┬──────────────────────────┤
│  [전략 목록]         │  [백테스트 실행 패널]    │
│  - 전략 카드 리스트  │  - 설정                  │
│  - 새 전략 추가      │  - 실행 버튼             │
│                      │  - 진행 상태             │
├──────────────────────┴──────────────────────────┤
│  [백테스트 결과 - 차트 및 통계]                  │
└─────────────────────────────────────────────────┘
```

---

## V. 시스템 및 보안 설정 (Settings)

### 목적

시스템의 '안정적인 운영' 환경 설정 및 제어

### 핵심 컴포넌트

#### 1. API 키 관리

**컴포넌트**: `ApiKeySettings.jsx`

```
🔑 관리 기능:
- 거래소 선택 (Bitget, Binance, etc.)
- API Key 입력 (마스킹 처리)
- Secret Key 입력 (마스킹 처리)
- Passphrase 입력 (선택)
- 연결 테스트 버튼

🔒 보안:
- 암호화 저장
- 마스킹 표시 (****...)
- 권한 확인 (Read/Trade)
```

#### 2. 리스크 한도 설정

**컴포넌트**: `RiskLimitSettings.jsx`

```
⚠️ 설정 항목:
- Max Drawdown (최대 낙폭 한도)
- Max Leverage (최대 레버리지)
- Max Position Size (최대 포지션 크기)
- Daily Loss Limit (일일 손실 한도)
- Max Open Positions (최대 동시 포지션 수)

🎚️ UI:
- 슬라이더 + 입력 필드
- 현재 값 vs 한도 표시
- 경고 메시지
```

#### 3. 알림 설정

**컴포넌트**: `NotificationSettings.jsx`

```
🔔 알림 타입:
- 거래 체결 알림
- 손익 임계값 알림
- 시스템 오류 알림
- 리스크 한도 초과 알림

📱 알림 채널:
- 이메일
- 텔레그램
- 웹 푸시
- SMS (선택)
```

#### 4. 계정 설정

**컴포넌트**: `AccountSettings.jsx`

```
👤 계정 정보:
- 이메일
- 비밀번호 변경
- 2FA 설정
- 세션 관리

🌐 환경 설정:
- 언어 선택
- 타임존 설정
- 테마 (라이트/다크)
- 통화 단위
```

### 레이아웃 구조

```
┌─────────────────────────────────────────────────┐
│  Settings                                        │
├─────────────────────────────────────────────────┤
│  [탭 메뉴: API | 리스크 | 알림 | 계정]           │
├─────────────────────────────────────────────────┤
│  [선택된 탭의 설정 폼]                           │
│  - 입력 필드                                     │
│  - 슬라이더                                      │
│  - 토글 스위치                                   │
├─────────────────────────────────────────────────┤
│  [저장] [취소] [기본값으로 복원]                 │
└─────────────────────────────────────────────────┘
```

---

## VI. 알림 센터 (Notification Center)

### 목적

사용자에게 즉각적인 조치가 필요한 '위험 상황' 전달

### 핵심 컴포넌트

#### 1. 알림 목록

**컴포넌트**: `NotificationList.jsx`

```
📬 알림 타입별 분류:
- 🔴 긴급 (Critical): 시스템 오류, 리스크 한도 초과
- 🟡 경고 (Warning): 주문 실패, 연결 끊김
- 🔵 정보 (Info): 거래 체결, 전략 변경
- 🟢 성공 (Success): 백테스트 완료, 설정 저장

📋 표시 정보:
- 시간, 타입, 제목, 메시지
- 읽음/안읽음 상태
- 액션 버튼 (확인/무시/상세보기)
```

#### 2. 알림 필터

**컴포넌트**: `NotificationFilter.jsx`

```
🔍 필터 옵션:
- 전체/읽지 않음만
- 타입별 필터 (긴급/경고/정보)
- 날짜 범위
- 키워드 검색
```

#### 3. 알림 상세

**컴포넌트**: `NotificationDetail.jsx`

```
📄 상세 정보:
- 전체 메시지
- 발생 시간
- 관련 데이터 (거래 ID, 포지션 정보 등)
- 권장 조치 사항

🎯 액션:
- 관련 페이지로 이동
- 알림 삭제
- 유사 알림 차단
```

#### 4. 실시간 토스트 알림

**컴포넌트**: `ToastNotification.jsx`

```
🍞 토스트 표시:
- 화면 우측 상단
- 자동 사라짐 (5초)
- 타입별 색상 및 아이콘
- 클릭 시 상세 페이지 이동
```

### 레이아웃 구조

```
┌─────────────────────────────────────────────────┐
│  Notification Center                             │
├─────────────────────────────────────────────────┤
│  [필터 바: 전체/읽지않음 | 타입 | 날짜]          │
├─────────────────────────────────────────────────┤
│  [알림 목록]                                     │
│  ┌─────────────────────────────────────────┐    │
│  │ 🔴 [긴급] API 연결 끊김 - 5분 전        │    │
│  │ 🟡 [경고] 주문 실패 - 10분 전           │    │
│  │ 🔵 [정보] 거래 체결 - 15분 전           │    │
│  └─────────────────────────────────────────┘    │
├─────────────────────────────────────────────────┤
│  [페이지네이션]                                  │
└─────────────────────────────────────────────────┘
```

---

## 🗂️ 파일 구조

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Dashboard.jsx              # I. 핵심 대시보드
│   │   ├── LiveTrading.jsx            # II. 실시간 거래 모니터링
│   │   ├── Performance.jsx            # III. 성능 분석
│   │   ├── Strategy.jsx               # IV. 전략 관리
│   │   ├── Settings.jsx               # V. 시스템 설정
│   │   └── Notifications.jsx          # VI. 알림 센터
│   │
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── PerformanceChart.jsx
│   │   │   ├── RiskMetrics.jsx
│   │   │   └── SystemStatus.jsx
│   │   │
│   │   ├── trading/
│   │   │   ├── PositionList.jsx       # ✅ 기존
│   │   │   ├── RealtimePnL.jsx
│   │   │   ├── OrderLog.jsx
│   │   │   └── SystemLog.jsx
│   │   │
│   │   ├── performance/
│   │   │   ├── TradeHistory.jsx
│   │   │   ├── PerformanceMetrics.jsx
│   │   │   └── PerformanceReport.jsx
│   │   │
│   │   ├── strategy/
│   │   │   ├── StrategyList.jsx
│   │   │   ├── BacktestRunner.jsx
│   │   │   ├── BacktestResults.jsx
│   │   │   └── StrategyEditor.jsx
│   │   │
│   │   ├── settings/
│   │   │   ├── ApiKeySettings.jsx
│   │   │   ├── RiskLimitSettings.jsx
│   │   │   ├── NotificationSettings.jsx
│   │   │   └── AccountSettings.jsx
│   │   │
│   │   ├── notifications/
│   │   │   ├── NotificationList.jsx
│   │   │   ├── NotificationFilter.jsx
│   │   │   ├── NotificationDetail.jsx
│   │   │   └── ToastNotification.jsx
│   │   │
│   │   └── common/
│   │       ├── TradingChart.jsx        # ✅ 기존
│   │       ├── Card.jsx
│   │       ├── Table.jsx
│   │       ├── Modal.jsx
│   │       └── Loading.jsx
│   │
│   ├── api/
│   │   ├── account.js                  # ✅ 기존
│   │   ├── order.js                    # ✅ 기존
│   │   ├── chart.js                    # ✅ 기존
│   │   ├── bot.js                      # ✅ 기존
│   │   ├── analytics.js                # 신규
│   │   ├── strategy.js                 # 신규
│   │   ├── backtest.js                 # 신규
│   │   └── notification.js             # 신규
│   │
│   ├── hooks/
│   │   ├── useWebSocket.js             # WebSocket 연결
│   │   ├── useRealtime.js              # 실시간 데이터
│   │   ├── useNotification.js          # 알림 관리
│   │   └── useBacktest.js              # 백테스트 실행
│   │
│   └── utils/
│       ├── formatters.js               # 숫자, 날짜 포맷
│       ├── calculations.js             # 지표 계산
│       └── validators.js               # 입력 검증
```

---

## 🎨 공통 디자인 시스템

### 색상 팔레트

```css
/* 주요 색상 */
--primary: #2196F3;      /* 파란색 - 주요 액션 */
--success: #4CAF50;      /* 녹색 - 수익, 성공 */
--danger: #F44336;       /* 빨간색 - 손실, 위험 */
--warning: #FF9800;      /* 주황색 - 경고 */
--info: #00BCD4;         /* 청록색 - 정보 */

/* 배경 */
--bg-primary: #FFFFFF;
--bg-secondary: #F5F5F5;
--bg-dark: #1A1A1A;

/* 텍스트 */
--text-primary: #212121;
--text-secondary: #757575;
--text-disabled: #BDBDBD;
```

### 타이포그래피

```css
/* 제목 */
--font-h1: 2rem;         /* 32px */
--font-h2: 1.5rem;       /* 24px */
--font-h3: 1.25rem;      /* 20px */

/* 본문 */
--font-body: 1rem;       /* 16px */
--font-small: 0.875rem;  /* 14px */
--font-tiny: 0.75rem;    /* 12px */

/* 폰트 패밀리 */
--font-primary: 'Inter', sans-serif;
--font-mono: 'Roboto Mono', monospace;
```

### 간격 시스템

```css
--spacing-xs: 0.25rem;   /* 4px */
--spacing-sm: 0.5rem;    /* 8px */
--spacing-md: 1rem;      /* 16px */
--spacing-lg: 1.5rem;    /* 24px */
--spacing-xl: 2rem;      /* 32px */
```

---

## 📡 API 엔드포인트 매핑

### Dashboard

- `GET /api/analytics/equity-curve` - 성과 추이
- `GET /api/analytics/risk-metrics` - 리스크 지표
- `GET /api/account/balance` - 잔고 현황
- `GET /api/bot/status` - 봇 상태

### Live Trading

- `GET /api/account/positions` - 현재 포지션
- `GET /api/order/history` - 주문 내역
- `GET /api/bot/logs` - 시스템 로그
- `WS /ws/user/{user_id}` - 실시간 업데이트

### Performance

- `GET /api/trades/history` - 거래 히스토리
- `GET /api/analytics/performance` - 성과 지표
- `GET /api/analytics/report` - 기간별 보고서

### Strategy

- `GET /api/strategy/list` - 전략 목록
- `POST /api/backtest/run` - 백테스트 실행
- `GET /api/backtest/results/{id}` - 백테스트 결과
- `POST /api/strategy/save` - 전략 저장

### Settings

- `POST /api/account/api-keys` - API 키 저장
- `PUT /api/account/risk-limits` - 리스크 한도 설정
- `PUT /api/account/notifications` - 알림 설정

### Notifications

- `GET /api/notifications` - 알림 목록
- `PUT /api/notifications/{id}/read` - 읽음 처리
- `DELETE /api/notifications/{id}` - 알림 삭제

---

## 🚀 개발 우선순위

### Phase 1: 핵심 기능 (2주)

1. ✅ Dashboard - 시스템 상태 모니터링
2. ✅ Live Trading - 포지션 및 주문 관리
3. ⬜ Performance - 기본 성과 분석

### Phase 2: 고급 기능 (2주)

4. ⬜ Strategy - 전략 관리 및 백테스팅
5. ⬜ Settings - 시스템 설정
6. ⬜ Notifications - 알림 센터

### Phase 3: 최적화 (1주)

- 성능 최적화
- UI/UX 개선
- 테스트 및 버그 수정

---

**작성일**: 2025년 12월 2일
**버전**: 1.0.0
**상태**: 설계 완료, 구현 대기
