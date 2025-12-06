# 📊 관리자 페이지 - 남은 구현 사항

> **작성일**: 2025-12-04  
> **현재 상태**: 기본 기능 완료, 고급 기능 미구현

---

## ✅ 이미 완료된 기능

### Backend API (완료)

| 엔드포인트 | 기능 | 상태 |
|------------|------|------|
| `GET /admin/analytics/global-summary` | 전체 시스템 통계 | ✅ |
| `GET /admin/analytics/risk-users` | 위험 사용자 목록 | ✅ |
| `GET /admin/analytics/trading-volume` | 거래량 통계 | ✅ |
| `GET /admin/bots/active` | 활성 봇 목록 | ✅ |
| `POST /admin/bots/{user_id}/pause` | 봇 정지 | ✅ |
| `POST /admin/bots/{user_id}/restart` | 봇 재시작 | ✅ |
| `POST /admin/bots/pause-all` | 전체 봇 긴급 정지 | ✅ |
| `GET /admin/bots/statistics` | 봇 통계 | ✅ |
| `GET /admin/users` | 사용자 목록 | ✅ |
| `GET /admin/users/{user_id}` | 사용자 기본 정보 | ✅ |
| `GET /admin/users/{user_id}/detail` | 사용자 종합 상세 | ✅ |
| `GET /admin/users/{user_id}/api-keys` | 사용자 API 키 목록 | ✅ |
| `POST /admin/users/{user_id}/api-keys` | API 키 등록 | ✅ |
| `PUT /admin/users/{user_id}/api-keys/{id}` | API 키 수정 | ✅ |
| `DELETE /admin/users/{user_id}/api-keys/{id}` | API 키 삭제 | ✅ |
| `POST /admin/users/{user_id}/suspend` | 계정 정지 | ✅ |
| `POST /admin/users/{user_id}/activate` | 계정 활성화 | ✅ |
| `POST /admin/users/{user_id}/force-logout` | 강제 로그아웃 | ✅ |
| `GET /admin/logs/system` | 시스템 로그 | ✅ |
| `GET /admin/logs/bot` | 봇 로그 | ✅ |
| `GET /admin/logs/trading` | 거래 로그 | ✅ |

### Frontend (완료)

| 탭 | 기능 | 상태 |
|----|------|------|
| **Overview** | 전체 통계 (사용자, 봇, AUM, P&L) | ✅ |
| **Overview** | 위험 사용자 테이블 | ✅ |
| **Overview** | 거래량 통계 | ✅ |
| **Overview** | 수익 상위 사용자 Top 5 | ✅ |
| **Bots** | 활성 봇 목록 | ✅ |
| **Bots** | 봇 정지/재시작 버튼 | ✅ |
| **Bots** | 전체 봇 긴급 정지 | ✅ |
| **Users** | 사용자 목록 테이블 | ✅ |
| **Users** | 검색/필터 (상태, 역할) | ✅ |
| **Users** | 사용자 상세 모달 | ✅ |
| **Users** | 계정 정지/활성화 | ✅ |
| **Users** | 강제 로그아웃 | ✅ |
| **Logs** | 시스템 로그 조회 | ✅ |
| **Logs** | 봇 로그 조회 | ✅ |
| **Logs** | 거래 로그 조회 | ✅ |
| **Logs** | 로그 필터링 (레벨, 사용자) | ✅ |

---

## 🔴 미구현 기능 (높은 우선순위)

### 1. 실시간 모니터링 대시보드

```
현재: 30초마다 polling
필요: WebSocket 기반 실시간 업데이트

구현 필요:
□ 실시간 거래 알림 (새 거래 발생 시 알림)
□ 봇 상태 변화 실시간 반영
□ 시스템 알림 실시간 표시
□ 다중 사용자 동시 접속 알림
```

### 2. 알림/공지사항 시스템

```
현재: 미구현
필요: 관리자 → 사용자 알림 기능

구현 필요:
□ POST /admin/notifications/send - 공지사항 전송
□ GET /admin/notifications - 발송된 공지 목록
□ 특정 사용자 대상 알림
□ 전체 사용자 대상 공지
□ 알림 히스토리 조회
```

### 3. 사용자 역할 관리

```
현재: admin/user 2가지만 구분
필요: 세분화된 권한 관리

구현 필요:
□ PUT /admin/users/{user_id}/role - 역할 변경
□ 역할 추가 (moderator, premium 등)
□ 역할별 권한 설정
□ 역할 변경 히스토리
```

### 4. 시스템 설정 관리

```
현재: 코드에 하드코딩
필요: 관리자 UI에서 설정 변경

구현 필요:
□ GET /admin/settings - 시스템 설정 조회
□ PUT /admin/settings - 시스템 설정 변경
  - Rate Limiting 설정
  - 기본 레버리지 제한
  - 신규 가입 허용 여부
  - 점검 모드 (모든 거래 정지)
□ 설정 변경 로그 기록
```

---

## 🟡 미구현 기능 (중간 우선순위)

### 5. 데이터 내보내기

```
현재: 미구현
필요: CSV/Excel 다운로드

구현 필요:
□ GET /admin/export/users - 사용자 목록 CSV
□ GET /admin/export/trades - 거래 내역 CSV
□ GET /admin/export/logs - 로그 CSV
□ 날짜 범위 필터링
□ 선택 데이터만 내보내기
```

### 6. 백테스트 관리

```
현재: 사용자 본인만 조회 가능
필요: 관리자가 모든 백테스트 조회

구현 필요:
□ GET /admin/backtests - 전체 백테스트 목록
□ GET /admin/backtests/{id} - 상세 조회
□ DELETE /admin/backtests/{id} - 삭제
□ 백테스트 리소스 사용량 모니터링
```

### 7. 감사 로그 (Audit Log)

```
현재: 기본 로그만
필요: 보안 이벤트 전용 로그

구현 필요:
□ 독립된 AuditLog 테이블
□ 로그인/로그아웃 기록
□ 비밀번호 변경 기록
□ API 키 조회/변경 기록
□ 관리자 작업 기록
□ GET /admin/audit-logs - 감사 로그 조회
```

### 8. 시스템 헬스 대시보드

```
현재: /health 엔드포인트만
필요: 상세한 시스템 상태 모니터링

구현 필요:
□ GET /admin/system/health - 시스템 헬스 상세
  - 데이터베이스 연결 상태
  - Redis 연결 상태
  - WebSocket 연결 수
  - API 응답 시간
  - 메모리/CPU 사용량
□ 시스템 상태 그래프
□ 장애 알림 설정
```

---

## 🟢 미구현 기능 (낮은 우선순위)

### 9. 전략 마켓플레이스 관리

```
□ 전략 승인/거부 시스템
□ 전략 사용 통계
□ 인기 전략 순위
```

### 10. 리포트 자동 생성

```
□ 일일/주간/월간 리포트
□ 이메일 자동 발송
□ 리포트 템플릿 관리
```

### 11. IP 화이트리스트 관리

```
□ 관리자 접속 허용 IP 설정
□ 사용자별 IP 제한
□ 비정상 접속 탐지
```

### 12. 다국어 지원

```
□ 관리자 페이지 영어 지원
□ 로그 메시지 다국어
```

---

## 📋 즉시 구현 가능한 빠른 개선

### UI/UX 개선

```
□ 차트 추가 (Chart.js 또는 Recharts)
  - 일별 거래량 그래프
  - 사용자 증가 추이
  - 봇 상태 파이 차트

□ 통계 카드 애니메이션
□ 다크 모드 지원
□ 반응형 모바일 UI

□ 페이지네이션 추가
  - 사용자 목록
  - 로그 목록
  
□ 정렬 기능
  - 각 테이블 컬럼별 정렬
```

### 성능 개선

```
□ 데이터 캐싱 (React Query 또는 SWR)
□ 무한 스크롤 (로그)
□ 가상화 테이블 (대량 데이터)
```

---

## 🎯 우선순위별 구현 로드맵

### Phase 1: 즉시 (1주일)

1. ✅ 기본 기능 완료 (현재)
2. □ 차트 추가 (거래량, 사용자 통계)
3. □ 페이지네이션 추가
4. □ 정렬 기능 추가

### Phase 2: 단기 (2주일)

1. □ 실시간 모니터링 (WebSocket)
2. □ 알림/공지사항 시스템
3. □ 데이터 내보내기 (CSV)

### Phase 3: 중기 (1개월)

1. □ 감사 로그 시스템
2. □ 시스템 헬스 대시보드
3. □ 사용자 역할 관리 세분화

### Phase 4: 장기 (2개월)

1. □ 시스템 설정 관리 UI
2. □ 자동 리포트 생성
3. □ 전략 마켓플레이스 관리

---

## 📊 현재 완성도 평가

| 카테고리 | 완성도 | 설명 |
|----------|--------|------|
| **기본 관리** | 90% | 사용자/봇/로그 CRUD 완료 |
| **모니터링** | 60% | Polling만, 실시간 미지원 |
| **분석/통계** | 70% | 기본 통계만, 차트 미구현 |
| **보안** | 50% | 감사 로그, 역할 관리 미구현 |
| **알림** | 0% | 완전 미구현 |
| **시스템 관리** | 30% | 설정 변경 UI 미구현 |

**전체 완성도: 약 65%**

---

## 💡 빠른 시작: 차트 추가 예시

```jsx
// 필요한 패키지 설치
npm install recharts

// VolumeChart.jsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const VolumeChart = ({ data }) => (
  <ResponsiveContainer width="100%" height={200}>
    <LineChart data={data}>
      <XAxis dataKey="date" />
      <YAxis />
      <Tooltip />
      <Line type="monotone" dataKey="volume" stroke="#2563eb" />
    </LineChart>
  </ResponsiveContainer>
);
```

---

**마지막 업데이트**: 2025-12-04
