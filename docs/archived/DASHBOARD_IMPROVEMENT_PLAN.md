# 대시보드 핵심 기능 개선 계획

**작성일**: 2025-12-02
**우선순위**: 높음 (기능 우선 원칙)

## 🎯 개선 목표

사용자가 **"지금 무슨 일이 일어나고 있는지"**를 즉시 파악할 수 있도록 핵심 모니터링 기능 강화

---

## 📊 1. 봇/시스템 작동 무결성 확인 강화

### 현재 문제점

- 봇 상태: "알 수 없음" - 실제로 무엇을 하는지 불명확
- 연결 상태: "연결 끊김" - 언제부터 끊겼는지 모름
- 잔고 정보: 데이터 신선도 불명확

### 개선 사항

#### A. 현재 실행 전략 명시

```javascript
{
  strategyName: "SuperTrend_v3.1",
  strategyStatus: "RUNNING",
  lastSignal: "BUY",
  lastSignalTime: "2025-12-02 17:30:15"
}
```

#### B. 마지막 데이터 수신 시각

```javascript
{
  lastDataReceived: "2025-12-02 17:30:15",
  timeSinceLastUpdate: "5초 전",
  isStale: false  // 30초 이상이면 true
}
```

#### C. 데이터 신선도 표시

```javascript
{
  balance: 10000,
  balanceUpdatedAt: "2025-12-02 17:30:10",
  isFresh: true  // 10초 이내면 true
}
```

---

## ⚡ 2. 즉각적인 운영 피드백 추가

### 현재 문제점

- 미실현 손익 부재 - 현재 포지션의 실시간 손익 불명확
- 긴급 알림 목록 부재 - 치명적 문제 인지 불가
- 최근 거래 내역 부재 - 전략 작동 여부 확인 어려움

### 개선 사항

#### A. 미실현 손익 (Unrealized P&L)

```javascript
{
  unrealizedPnL: 125.50,
  unrealizedPnLPercent: 1.25,
  positionCount: 3,
  totalPositionValue: 10000
}
```

**표시 위치**: SystemStatus 카드 상단 (가장 눈에 띄는 위치)
**색상 코딩**:

- 양수: 녹색 (#3f8600)
- 음수: 빨간색 (#cf1322)
- 0: 회색 (#888)

#### B. 긴급 알림 위젯

```javascript
{
  alerts: [
    {
      level: "ERROR",
      message: "API 연결 실패",
      timestamp: "2025-12-02 17:25:00",
      isResolved: false
    },
    {
      level: "WARNING",
      message: "잔고 부족 (10% 미만)",
      timestamp: "2025-12-02 17:20:00",
      isResolved: false
    }
  ]
}
```

**표시 위치**: 대시보드 상단 (전체 너비)
**알림 레벨**:

- ERROR: 빨간색, 즉시 조치 필요
- WARNING: 노란색, 주의 필요
- INFO: 파란색, 정보성

#### C. 최근 거래 요약 (최근 5개)

```javascript
{
  recentTrades: [
    {
      symbol: "BTC/USDT",
      side: "BUY",
      pnl: 45.20,
      pnlPercent: 0.45,
      closedAt: "2025-12-02 17:15:00"
    }
  ]
}
```

**표시 위치**: RiskMetrics 아래 새로운 섹션
**색상 코딩**: 수익/손실에 따라 녹색/빨간색

---

## 🔧 구현 우선순위

### Phase 1: 즉시 구현 (긴급)

1. ✅ 미실현 손익 표시
2. ✅ 긴급 알림 위젯
3. ✅ 마지막 업데이트 시각

### Phase 2: 단기 구현 (1주일 내)

4. ✅ 현재 실행 전략 표시
5. ✅ 최근 거래 요약
6. ✅ 데이터 신선도 표시

### Phase 3: 중기 구현 (2주일 내)

7. ⬜ 실시간 WebSocket 연결
8. ⬜ 자동 알림 푸시
9. ⬜ 성능 최적화

---

## 📝 API 엔드포인트 요구사항

### 필요한 백엔드 API

```python
# 1. 시스템 상태 (강화)
GET /api/bot/status
Response:
{
  "status": "RUNNING",
  "strategy": {
    "name": "SuperTrend_v3.1",
    "status": "ACTIVE",
    "lastSignal": "BUY",
    "lastSignalTime": "2025-12-02T17:30:15Z"
  },
  "connection": {
    "exchange": "CONNECTED",
    "lastDataReceived": "2025-12-02T17:30:15Z",
    "timeSinceLastUpdate": 5
  },
  "balance": {
    "total": 10000,
    "free": 5000,
    "used": 5000,
    "updatedAt": "2025-12-02T17:30:10Z"
  }
}

# 2. 미실현 손익
GET /api/positions/unrealized-pnl
Response:
{
  "unrealizedPnL": 125.50,
  "unrealizedPnLPercent": 1.25,
  "positionCount": 3,
  "positions": [...]
}

# 3. 긴급 알림
GET /api/alerts/urgent
Response:
{
  "alerts": [
    {
      "id": 1,
      "level": "ERROR",
      "message": "API 연결 실패",
      "timestamp": "2025-12-02T17:25:00Z",
      "isResolved": false
    }
  ]
}

# 4. 최근 거래
GET /api/trades/recent?limit=5
Response:
{
  "trades": [
    {
      "id": 123,
      "symbol": "BTC/USDT",
      "side": "BUY",
      "pnl": 45.20,
      "pnlPercent": 0.45,
      "closedAt": "2025-12-02T17:15:00Z"
    }
  ]
}
```

---

## 🎨 UI/UX 개선 사항 (나중에)

- 색상 테마 통일
- 애니메이션 효과
- 반응형 디자인 최적화
- 다크 모드 지원

**참고**: 디자인 개선은 모든 기능 구현 후 마지막에 진행
