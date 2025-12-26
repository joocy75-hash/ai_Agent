# Deep Signal 성능 최적화 작업계획서 (최종본)

> **작성일**: 2025-12-22
> **최종 수정**: 2025-12-22
> **목적**: 즉각 반응 UX 구현 및 시스템 성능 최적화
> **예상 사용자 규모**: 현재 5명 → 목표 1,000명 이상

---

## 🎯 핵심 철학: "대시보드는 서버를 기다리지 않는다"

### UX 우선순위

```
1️⃣ 즉시 화면 표시 (0~100ms 체감)
2️⃣ 이전 상태라도 실제 값 노출
3️⃣ 실시간 보정은 백그라운드에서 조용히 처리
```

**"항상 최신 값"은 UX의 1순위가 아니다.**
**"기다리지 않는 화면"이 최우선이다.**

### 성공 기준

| 기준 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| Skeleton 노출 빈도 | 매 페이지 진입 | 최초 가입 후 1회만 | 사용자 관찰 |
| 화면 표시 시간 | ~1-3초 | <100ms | Performance API |
| 네트워크 지연 체감 | 있음 | 없음 | UX 테스트 |
| 유사 서비스 체감 | - | YouTube, Binance 수준 | 주관적 평가 |

---

## 목차

1. [현재 상태 분석](#1-현재-상태-분석)
2. [문제 정의: Skeleton 로딩 UX](#2-문제-정의-skeleton-로딩-ux)
3. [개선 전략: Stale-While-Revalidate](#3-개선-전략-stale-while-revalidate)
4. [Phase 0: 즉각 반응 UX 구현 (최우선)](#4-phase-0-즉각-반응-ux-구현)
5. [Phase 1-7: 백엔드 최적화](#5-phase-1-7-백엔드-최적화)
6. [모니터링 및 검증](#6-모니터링-및-검증)
7. [롤백 계획](#7-롤백-계획)

---

## 1. 현재 상태 분석

### 1.1 시스템 리소스

| 항목 | 현재 값 | 상태 |
|------|---------|------|
| 메모리 사용량 | 71% | ⚠️ 주의 |
| 디스크 사용량 | 65.2% | ✅ 양호 |
| Swap 사용량 | 6% | ✅ 양호 |
| CPU 부하 | 0.1~0.21 | ✅ 양호 |

### 1.2 데이터베이스 현황

| 테이블 | 행 수 | 증가 속도 | 인덱스 상태 |
|--------|------|----------|------------|
| equities | 36,129 | ~1,200/일 | ✅ `user_id, timestamp` 복합 인덱스 |
| trades | 13 | 느림 | ✅ `user_id, created_at` 복합 인덱스 |
| users | 5 | 느림 | ✅ `email` 유니크 인덱스 |
| bot_status | 1 | 고정 | ✅ PK만 |

**예상 1년 후 (사용자 1,000명 기준)**:
- equities: ~43,800,000 행 (1,000명 × 120행/일 × 365일)
- trades: ~365,000 행 (1,000명 × 1거래/일 × 365일)

### 1.3 API 응답 시간 측정

| API 엔드포인트 | 평균 응답시간 | 목표 | 상태 |
|---------------|-------------|------|------|
| `/auth/login` | 0.13s | <0.3s | ✅ 양호 |
| `/bot/status` | 0.14s | <0.2s | ✅ 양호 |
| `/order/history` | 0.13s~1.4s | <0.3s | ⚠️ 불안정 |
| `/ai/strategies/list` | 0.13s | <0.2s | ✅ 양호 |

### 1.4 프론트엔드 번들 분석

| 번들 파일 | 크기 | gzip | 용도 |
|----------|------|------|------|
| index-BWClgVby.js | 820KB | 273KB | 메인 (Ant Design + React) |
| CategoricalChart.js | 252KB | 82KB | Recharts 차트 |
| Table-KULm_CZk.js | 154KB | 50KB | Ant Design Table |
| BacktestingPage.js | 111KB | 32KB | 백테스팅 페이지 |
| **총합** | **~2.2MB** | **~700KB** | - |

---

## 2. 문제 정의: Skeleton 로딩 UX

### 2.1 현재 문제점

**Dashboard.jsx의 현재 데이터 흐름**:

```
페이지 진입 → loadAllData() 호출 → 서버 응답 대기 → 화면 렌더링
                     ↓
              initialLoading=true
                     ↓
              Skeleton UI 표시 (1~3초)
```

**핵심 코드** (`Dashboard.jsx:589-597`):

```jsx
useEffect(() => {
  loadAllData();  // ← 페이지 진입 시 서버 호출

  const interval = setInterval(() => {
    loadAllData();  // ← 30초마다 전체 데이터 리로드
  }, 30000);

  return () => clearInterval(interval);
}, []);
```

**문제점**:
1. 페이지 진입 시 `initialLoading=true` → Skeleton 표시
2. 서버 응답까지 1~3초 대기
3. 30초마다 불필요한 전체 데이터 리로드
4. localStorage에 대시보드 데이터 캐시 없음

### 2.2 Skeleton UI 허용 규칙

| 상황 | Skeleton 표시 | 이유 |
|------|--------------|------|
| 최초 가입 직후 | ✅ 허용 | 데이터 자체가 없음 |
| 페이지 재진입 | ❌ 금지 | 이전 데이터 있음 |
| 새로고침 | ❌ 금지 | 캐시된 데이터 사용 |
| 탭 전환 후 복귀 | ❌ 금지 | 메모리 데이터 사용 |

### 2.3 금지 행위 (대시보드 진입 시)

```
❌ 서버에서 동기 계산 수행
❌ 전략 상태 재계산
❌ KPI 실시간 산출
❌ 거래소 상태 동기화
❌ 거래소 API 직접 호출
```

**이런 작업은 모두 백그라운드 워커의 책임이다.**

---

## 3. 개선 전략: Stale-While-Revalidate

### 3.1 SWR 패턴 설명

```
┌─────────────────────────────────────────────────────────────┐
│                    현재: Wait-For-Fresh                      │
├─────────────────────────────────────────────────────────────┤
│ 페이지 진입 → API 호출 → 대기... → 응답 → 렌더링           │
│                         ↑                                   │
│                   Skeleton 표시                              │
└─────────────────────────────────────────────────────────────┘

                          ↓ 변경

┌─────────────────────────────────────────────────────────────┐
│                  목표: Stale-While-Revalidate               │
├─────────────────────────────────────────────────────────────┤
│ 페이지 진입 → 캐시 데이터 즉시 표시 → API 호출(백그라운드)  │
│       ↓                                    ↓                │
│  실제 숫자 즉시 렌더링              응답 후 조용히 갱신      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 데이터 레이어 구조

```
┌──────────────────────────────────────────────────────────────┐
│                         브라우저                              │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │ React State │ ← │ SWR Cache   │ ← │ localStorage │      │
│  │ (UI 렌더링) │    │ (메모리)    │    │ (영구저장)  │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                            ↑                                 │
│                     백그라운드 갱신                           │
│                            │                                 │
├──────────────────────────────────────────────────────────────┤
│                         서버                                  │
│  ┌─────────────┐    ┌─────────────┐                         │
│  │ Redis Cache │ ← │ PostgreSQL  │                          │
│  │ (Snapshot)  │    │ (원본 데이터)│                         │
│  └─────────────┘    └─────────────┘                         │
│         ↑                                                    │
│    백그라운드 워커가 주기적 업데이트                          │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Snapshot 데이터 구조

```typescript
interface DashboardSnapshot {
  // 메타데이터
  version: number;           // 스키마 버전
  updatedAt: string;         // ISO 8601 timestamp
  userId: number;

  // 거래 통계
  tradeStats: {
    totalTrades: number;
    winRate: number;
    winningTrades: number;
    losingTrades: number;
    avgPnl: number;
    totalReturn: number;
    bestTrade: number;
    worstTrade: number;
    longCount: number;
    shortCount: number;
  };

  // 기간별 수익
  periodProfits: {
    daily: { return: number; pnl: number };
    weekly: { return: number; pnl: number };
    monthly: { return: number; pnl: number };
    allTime: { return: number; pnl: number };
  };

  // 봇 상태
  botStatus: {
    isRunning: boolean;
    strategy: string | null;
    lastUpdated: string;
  };

  // 최근 거래 (최대 10개)
  recentTrades: Array<{
    timestamp: string;
    symbol: string;
    side: 'buy' | 'sell';
    price: number;
    pnl: number;
  }>;
}
```

---

## 4. Phase 0: 즉각 반응 UX 구현

> **최우선 작업**: 이 Phase가 완료되어야 사용자 체감 개선
> **예상 기간**: 2-3일

### 4.1 프론트엔드: 로컬 캐시 레이어 구현

**파일**: `frontend/src/services/snapshotCache.js` (신규)

```javascript
/**
 * Dashboard Snapshot Cache
 * - localStorage 기반 영구 캐시
 * - 페이지 진입 시 즉시 사용
 * - 백그라운드에서 갱신
 */

const CACHE_KEY = 'dashboard_snapshot';
const CACHE_VERSION = 1;
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24시간 (stale 판단용, 표시는 항상 함)

export const snapshotCache = {
  /**
   * 캐시된 스냅샷 조회
   * @returns {DashboardSnapshot | null}
   */
  get() {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;

      const data = JSON.parse(raw);

      // 버전 체크
      if (data.version !== CACHE_VERSION) {
        this.clear();
        return null;
      }

      return data;
    } catch (e) {
      console.warn('[SnapshotCache] Failed to read cache:', e);
      return null;
    }
  },

  /**
   * 스냅샷 저장
   * @param {Partial<DashboardSnapshot>} snapshot
   */
  set(snapshot) {
    try {
      const userId = localStorage.getItem('userId');
      const data = {
        version: CACHE_VERSION,
        updatedAt: new Date().toISOString(),
        userId: parseInt(userId) || 0,
        ...snapshot,
      };
      localStorage.setItem(CACHE_KEY, JSON.stringify(data));
    } catch (e) {
      console.warn('[SnapshotCache] Failed to write cache:', e);
    }
  },

  /**
   * 캐시 삭제
   */
  clear() {
    localStorage.removeItem(CACHE_KEY);
  },

  /**
   * 캐시가 stale인지 확인 (표시는 하되, 갱신 필요 여부 판단)
   * @returns {boolean}
   */
  isStale() {
    const data = this.get();
    if (!data) return true;

    const age = Date.now() - new Date(data.updatedAt).getTime();
    return age > CACHE_TTL;
  },

  /**
   * 캐시 존재 여부
   * @returns {boolean}
   */
  exists() {
    return this.get() !== null;
  },
};
```

### 4.2 프론트엔드: useDashboardData 훅

**파일**: `frontend/src/hooks/useDashboardData.js` (신규)

```javascript
import { useState, useEffect, useCallback, useRef } from 'react';
import { snapshotCache } from '../services/snapshotCache';
import { analyticsAPI } from '../api/analytics';
import { botAPI } from '../api/bot';
import { orderAPI } from '../api/order';

/**
 * Stale-While-Revalidate 패턴 구현
 *
 * 1. 캐시 데이터 즉시 반환 (Skeleton 없음)
 * 2. 백그라운드에서 서버 데이터 fetch
 * 3. 새 데이터 도착 시 조용히 갱신
 */
export function useDashboardData() {
  // 초기값: 캐시에서 즉시 로드 (동기)
  const cached = snapshotCache.get();

  const [tradeStats, setTradeStats] = useState(cached?.tradeStats || null);
  const [periodProfits, setPeriodProfits] = useState(cached?.periodProfits || null);
  const [botStatus, setBotStatus] = useState(cached?.botStatus || null);
  const [recentTrades, setRecentTrades] = useState(cached?.recentTrades || []);

  // 최초 데이터 존재 여부 (Skeleton 표시 판단)
  const [hasData, setHasData] = useState(snapshotCache.exists());

  // 갱신 중 여부 (UI에 표시 가능하지만, Skeleton은 아님)
  const [isRefreshing, setIsRefreshing] = useState(false);

  // 마지막 갱신 시간
  const [lastUpdated, setLastUpdated] = useState(cached?.updatedAt || null);

  const isFirstMount = useRef(true);

  /**
   * 백그라운드에서 데이터 갱신
   * - UI 차단 없음
   * - 실패해도 기존 데이터 유지
   */
  const revalidate = useCallback(async () => {
    setIsRefreshing(true);

    try {
      // 병렬 호출
      const [summary, status, trades] = await Promise.all([
        analyticsAPI.getDashboardSummary().catch(() => null),
        botAPI.getStatus().catch(() => null),
        orderAPI.getOrderHistory(10).catch(() => []),
      ]);

      // Trade Stats 업데이트
      if (summary) {
        const perfAll = summary.performance_all || {};
        const riskMetrics = summary.risk_metrics || {};
        const perfDaily = summary.performance_daily || {};
        const perfWeekly = summary.performance_weekly || {};
        const perfMonthly = summary.performance_monthly || {};

        const newTradeStats = {
          totalTrades: riskMetrics.total_trades || 0,
          winRate: riskMetrics.win_rate || 0,
          winningTrades: perfAll.winning_trades || 0,
          losingTrades: perfAll.losing_trades || 0,
          avgPnl: perfAll.total_pnl && perfAll.total_trades
            ? (perfAll.total_pnl / perfAll.total_trades)
            : 0,
          totalReturn: perfAll.total_return || 0,
          bestTrade: perfAll.best_trade?.pnl_percent || 0,
          worstTrade: perfAll.worst_trade?.pnl_percent || 0,
          longCount: perfAll.total_trades || 0,
          shortCount: 0,
        };

        const newPeriodProfits = {
          daily: { return: perfDaily.total_return || 0, pnl: perfDaily.total_pnl || 0 },
          weekly: { return: perfWeekly.total_return || 0, pnl: perfWeekly.total_pnl || 0 },
          monthly: { return: perfMonthly.total_return || 0, pnl: perfMonthly.total_pnl || 0 },
          allTime: { return: perfAll.total_return || 0, pnl: perfAll.total_pnl || 0 },
        };

        setTradeStats(newTradeStats);
        setPeriodProfits(newPeriodProfits);
      }

      // Bot Status 업데이트
      if (status) {
        const newBotStatus = {
          isRunning: status.is_running,
          strategy: typeof status.strategy === 'object'
            ? (status.strategy?.name || status.strategy?.strategy_name)
            : status.strategy,
          lastUpdated: new Date().toISOString(),
        };
        setBotStatus(newBotStatus);
      }

      // Recent Trades 업데이트
      const tradeList = Array.isArray(trades) ? trades : (trades?.trades || []);
      setRecentTrades(tradeList.slice(0, 10));

      // 캐시 업데이트
      snapshotCache.set({
        tradeStats: tradeStats,
        periodProfits: periodProfits,
        botStatus: botStatus,
        recentTrades: tradeList.slice(0, 10),
      });

      setHasData(true);
      setLastUpdated(new Date().toISOString());

    } catch (error) {
      console.error('[useDashboardData] Revalidation failed:', error);
      // 실패해도 기존 데이터 유지 - UI에 영향 없음
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // 마운트 시 백그라운드 갱신 시작
  useEffect(() => {
    if (isFirstMount.current) {
      isFirstMount.current = false;
      // 데이터가 있어도 백그라운드에서 갱신
      revalidate();
    }
  }, [revalidate]);

  // WebSocket 이벤트로 갱신 (폴링 대체)
  // 이 부분은 Phase 7에서 구현

  return {
    tradeStats,
    periodProfits,
    botStatus,
    recentTrades,
    hasData,         // Skeleton 표시 여부 결정에 사용
    isRefreshing,    // 갱신 중 인디케이터 (선택적 표시)
    lastUpdated,     // 마지막 갱신 시간
    revalidate,      // 수동 갱신 트리거
  };
}
```

### 4.3 프론트엔드: Dashboard.jsx 수정

**변경 전 (현재)**:
```jsx
const [tradeStats, setTradeStats] = useState(null);
const [initialLoading, setInitialLoading] = useState(true);

useEffect(() => {
  loadAllData();  // 서버 호출 후 Skeleton 표시
}, []);
```

**변경 후**:
```jsx
import { useDashboardData } from '../hooks/useDashboardData';

// 컴포넌트 내부
const {
  tradeStats,
  periodProfits,
  botStatus,
  recentTrades,
  hasData,
  isRefreshing,
  revalidate,
} = useDashboardData();

// Skeleton은 hasData가 false일 때만 (최초 가입 후)
// isRefreshing은 우측 상단에 작은 인디케이터로만 표시 (선택)
```

**StatCard 수정**:
```jsx
<StatCard
  title="총 거래"
  value={tradeStats?.totalTrades || 0}
  suffix="회"
  icon={<BarChartOutlined />}
  loading={!hasData}  // initialLoading 대신 hasData 사용
/>
```

### 4.4 백엔드: Snapshot API 추가

**파일**: `backend/src/api/dashboard.py` (신규 또는 기존 analytics.py 확장)

```python
from fastapi import APIRouter, Depends
from ..services.cache_service import cache_service
from ..database.db import get_db

router = APIRouter()

@router.get("/snapshot")
async def get_dashboard_snapshot(
    user_id: int = Depends(get_current_user_id),
    db = Depends(get_db)
):
    """
    대시보드 스냅샷 반환
    - Redis에 캐시된 최신 스냅샷 반환
    - 실시간 계산 없음 (백그라운드 워커가 갱신)
    """
    cache_key = f"dashboard_snapshot:{user_id}"

    # Redis에서 스냅샷 조회
    snapshot = await cache_service.get(cache_key)

    if snapshot:
        return snapshot

    # 캐시 미스 시 기본값 반환 (계산하지 않음)
    return {
        "tradeStats": None,
        "periodProfits": None,
        "botStatus": None,
        "recentTrades": [],
        "updatedAt": None,
        "isCached": False,
    }
```

### 4.5 백엔드: Snapshot 갱신 워커

**파일**: `backend/src/services/snapshot_worker.py` (신규)

```python
import asyncio
import logging
from datetime import datetime
from .cache_service import cache_service
from ..database.db import get_async_session
from ..database.models import Trade, BotInstance, Equity

logger = logging.getLogger("snapshot_worker")

async def update_user_snapshot(user_id: int):
    """
    단일 사용자의 대시보드 스냅샷 갱신
    - 봇 러너와 별도로 실행
    - 거래 발생 시 또는 주기적으로 호출
    """
    try:
        async with get_async_session() as session:
            # 거래 통계 계산
            trades = await session.execute(
                select(Trade).where(Trade.user_id == user_id)
            )
            trade_list = trades.scalars().all()

            # 통계 계산 로직...
            trade_stats = calculate_trade_stats(trade_list)
            period_profits = calculate_period_profits(trade_list)

            # 봇 상태 조회
            bot_instance = await session.execute(
                select(BotInstance)
                .where(BotInstance.user_id == user_id)
                .order_by(BotInstance.created_at.desc())
                .limit(1)
            )
            bot = bot_instance.scalar_one_or_none()

            snapshot = {
                "tradeStats": trade_stats,
                "periodProfits": period_profits,
                "botStatus": {
                    "isRunning": bot.status == "running" if bot else False,
                    "strategy": bot.strategy_name if bot else None,
                },
                "recentTrades": [t.to_dict() for t in trade_list[-10:]],
                "updatedAt": datetime.utcnow().isoformat(),
            }

            # Redis에 저장 (TTL 5분 - 워커가 더 자주 갱신하므로)
            cache_key = f"dashboard_snapshot:{user_id}"
            await cache_service.set(cache_key, snapshot, ttl=300)

            logger.info(f"Updated snapshot for user {user_id}")

    except Exception as e:
        logger.error(f"Failed to update snapshot for user {user_id}: {e}")


async def snapshot_worker_loop():
    """
    모든 활성 사용자의 스냅샷 주기적 갱신
    - 1분마다 실행
    """
    while True:
        try:
            # 활성 사용자 목록 조회
            async with get_async_session() as session:
                users = await session.execute(
                    select(User.id).where(User.is_active == True)
                )
                user_ids = [u.id for u in users.scalars().all()]

            # 각 사용자 스냅샷 갱신
            for user_id in user_ids:
                await update_user_snapshot(user_id)

            await asyncio.sleep(60)  # 1분 대기

        except Exception as e:
            logger.error(f"Snapshot worker error: {e}")
            await asyncio.sleep(10)  # 에러 시 10초 후 재시도
```

### 4.6 구현 순서

| 단계 | 작업 | 예상 시간 | 위험도 |
|------|------|----------|--------|
| 1 | `snapshotCache.js` 생성 | 1시간 | 🟢 |
| 2 | `useDashboardData.js` 생성 | 2시간 | 🟢 |
| 3 | `Dashboard.jsx` 수정 | 2시간 | 🟡 |
| 4 | `/snapshot` API 추가 | 1시간 | 🟢 |
| 5 | `snapshot_worker.py` 생성 | 2시간 | 🟢 |
| 6 | 통합 테스트 | 2시간 | 🟢 |

**총 예상 시간**: 10시간 (1.5일)

### 4.7 Phase 0 완료 검증

- [ ] 대시보드 진입 시 Skeleton 표시 안 됨 (데이터 있을 때)
- [ ] 새로고침해도 이전 값 즉시 표시
- [ ] 탭 전환 후 복귀해도 데이터 유지
- [ ] 백그라운드 갱신 동작 확인
- [ ] 최초 가입 사용자만 Skeleton 표시

---

## 5. Phase 1-7: 백엔드 최적화

> Phase 0이 완료된 후 진행

### Phase 1: 모니터링 설정 (1일)

> **목표**: 현재 상태를 정확히 측정할 수 있는 기반 마련

#### 작업 1.1: API 응답 시간 로깅

**파일**: `backend/src/middleware/performance.py` (신규)

```python
import time
import logging
from fastapi import Request

logger = logging.getLogger("performance")

async def performance_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start_time) * 1000  # ms

    # 느린 요청 경고 (500ms 이상)
    if duration > 500:
        logger.warning(f"SLOW API: {request.url.path} took {duration:.2f}ms")
    else:
        logger.info(f"API: {request.url.path} - {duration:.2f}ms")

    response.headers["X-Response-Time"] = f"{duration:.2f}ms"
    return response
```

**적용**: `main.py`에 미들웨어 추가

```python
from .middleware.performance import performance_middleware

app.middleware("http")(performance_middleware)
```

**위험도**: 🟢 매우 낮음 (읽기 전용)

---

#### 작업 1.2: 데이터베이스 쿼리 로깅

**파일**: `backend/src/database/db.py` 수정

```python
import logging
import time
from sqlalchemy import event

# 느린 쿼리 로깅 (100ms 이상)
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.perf_counter())

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = (time.perf_counter() - conn.info['query_start_time'].pop()) * 1000
    if total > 100:
        logging.getLogger("db.slow").warning(f"Slow query ({total:.2f}ms): {statement[:100]}...")
```

**위험도**: 🟢 매우 낮음 (읽기 전용)

---

### Phase 2: Redis 캐싱 강화 (2일)

> **목표**: 반복되는 API 호출 부하 감소

**Phase 0에서 이미 기본 캐싱 구현됨. 여기서는 추가 API에 확장 적용**

| API | 캐시 TTL | 무효화 조건 |
|-----|---------|------------|
| `/ai/strategies/list` | 5분 | 전략 생성/수정/삭제 시 |
| `/bot/status` | 10초 | 봇 시작/중지 시 |
| `/dashboard/snapshot` | 1분 | 워커가 갱신 |
| `/order/history` | 30초 | 새 거래 발생 시 |

---

### Phase 3: 전략 싱글톤 패턴 적용 (1일)

> **목표**: 매 12초마다 전략 재초기화 방지

**파일**: `backend/src/services/strategy_registry.py` (신규)

```python
from typing import Dict, Optional
import asyncio

class StrategyRegistry:
    """전략 인스턴스 싱글톤 레지스트리"""

    def __init__(self):
        self._strategies: Dict[str, object] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(
        self,
        strategy_code: str,
        symbol: str,
        user_id: int,
        factory_func,
    ) -> object:
        """전략 인스턴스 조회 또는 생성"""
        key = f"{strategy_code}:{symbol}:{user_id}"

        if key in self._strategies:
            return self._strategies[key]

        async with self._lock:
            # Double-check locking
            if key in self._strategies:
                return self._strategies[key]

            # 새 인스턴스 생성
            strategy = await factory_func()
            self._strategies[key] = strategy
            return strategy

# 전역 인스턴스
strategy_registry = StrategyRegistry()
```

---

### Phase 4: DB 연결 풀 최적화 (0.5일)

**파일**: `backend/src/database/db.py` 수정

```python
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=QueuePool,
    pool_size=10,           # 기본 연결 수
    max_overflow=20,        # 추가 허용 연결 수
    pool_timeout=30,        # 연결 대기 타임아웃
    pool_recycle=1800,      # 30분마다 연결 재생성
    pool_pre_ping=True,     # 연결 상태 확인
)
```

---

### Phase 5: 프론트엔드 Lazy Loading (1일)

**파일**: `frontend/src/App.jsx` 수정

```jsx
import { lazy, Suspense } from 'react';
import { Spin } from 'antd';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Trading = lazy(() => import('./pages/Trading'));
const BacktestingPage = lazy(() => import('./pages/BacktestingPage'));

// 라우트에서 사용
<Route
  path="/dashboard"
  element={
    <Suspense fallback={<PageLoader />}>
      <Dashboard />
    </Suspense>
  }
/>
```

**예상 효과**: 초기 번들 820KB → ~400KB (50% 감소)

---

### Phase 6: Equity 테이블 관리 (1일)

**권장 정책**:
- 최근 7일: 1분 단위 데이터 유지
- 7일~30일: 1시간 단위로 집계 후 원본 삭제
- 30일~1년: 1일 단위로 집계

---

### Phase 7: WebSocket 확대 적용 (2일)

> **목표**: 폴링 제거로 서버 부하 감소

| 데이터 | 현재 방식 | 개선 방식 |
|--------|----------|----------|
| 가격 | WebSocket ✅ | 유지 |
| 봇 상태 | 30초 폴링 | WebSocket 푸시 |
| 거래내역 | 30초 폴링 | 거래 발생 시 푸시 |
| 포지션 | 30초 폴링 | 변경 시 푸시 |

**프론트엔드 수정** (`useDashboardData.js`에 추가):

```javascript
// WebSocket 이벤트 구독
useEffect(() => {
  if (!wsConnected) return;

  const unsubTrade = subscribe('trade_executed', (data) => {
    setRecentTrades(prev => [data, ...prev.slice(0, 9)]);
    // 캐시도 갱신
    snapshotCache.set({ recentTrades: [data, ...recentTrades.slice(0, 9)] });
  });

  const unsubBot = subscribe('bot_status_changed', (data) => {
    setBotStatus(data);
    snapshotCache.set({ botStatus: data });
  });

  return () => {
    unsubTrade();
    unsubBot();
  };
}, [wsConnected, subscribe]);
```

---

## 6. 모니터링 및 검증

### 6.1 UX KPI (Phase 0)

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| Skeleton 노출 빈도 | 100% | <5% | 사용자 관찰 |
| 화면 표시 시간 | 1-3s | <100ms | Performance API |
| Time to Interactive | ~3s | <500ms | Lighthouse |

### 6.2 성능 KPI (Phase 1-7)

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| API 평균 응답시간 | 0.13s | <0.1s | X-Response-Time 헤더 |
| API 95th percentile | ~1.4s | <0.3s | 로그 분석 |
| 메모리 사용량 | 71% | <60% | `docker stats` |
| DB 쿼리 시간 | ~50ms | <30ms | slow query 로그 |

### 6.3 검증 체크리스트

각 Phase 완료 후:

- [ ] 기존 기능 정상 작동 확인 (회귀 테스트)
- [ ] 성능 지표 측정 및 비교
- [ ] 에러 로그 확인
- [ ] 24시간 모니터링

---

## 7. 롤백 계획

### 7.1 Phase 0 롤백

| 변경 사항 | 롤백 방법 | 소요 시간 |
|----------|----------|----------|
| snapshotCache.js | 파일 삭제, import 제거 | 5분 |
| useDashboardData.js | 기존 로직 복원 | 10분 |
| Dashboard.jsx | git checkout | 1분 |

### 7.2 Backend 롤백

| 변경 사항 | 롤백 방법 | 소요 시간 |
|----------|----------|----------|
| Redis 캐싱 | 캐시 데코레이터 제거 | 5분 |
| 전략 싱글톤 | 직접 생성으로 복귀 | 5분 |
| snapshot_worker | 프로세스 중지 | 1분 |

---

## 8. 일정 및 우선순위

### 8.1 작업 일정

| Phase | 기간 | 우선순위 | 상태 |
|-------|------|---------|------|
| **Phase 0: 즉각 UX** | D+1~3 | **P0 (최우선)** | 대기 |
| Phase 1: 모니터링 | D+4 | P1 | 대기 |
| Phase 2: Redis 강화 | D+5~6 | P1 | 대기 |
| Phase 3: 전략 싱글톤 | D+7 | P2 | 대기 |
| Phase 4: DB 연결 풀 | D+8 | P2 | 대기 |
| Phase 5: Lazy Loading | D+9 | P2 | 대기 |
| Phase 6: Equity 관리 | D+10 | P3 | 대기 |
| Phase 7: WebSocket 확대 | D+11~12 | P3 | 대기 |

### 8.2 예상 효과

| 지표 | Before | After | 개선율 |
|------|--------|-------|--------|
| Skeleton 노출 | 100% | <5% | 95% |
| 화면 표시 시간 | 1-3s | <100ms | 95% |
| API 응답시간 | 0.13~1.4s | 0.05~0.2s | 70% |
| 서버 메모리 | 71% | 55% | 23% |
| 지원 사용자 수 | ~50명 | ~500명 | 10x |

---

## 9. 결론

### 9.1 핵심 변경 사항

1. **Phase 0 (최우선)**: Stale-While-Revalidate 패턴 도입
   - 캐시 → 즉시 표시 → 백그라운드 갱신
   - Skeleton UI 최소화

2. **Phase 1-7**: 백엔드 최적화
   - Redis 캐싱 강화
   - 전략 싱글톤
   - WebSocket 확대

### 9.2 UX 철학 재확인

```
"대시보드는 서버를 기다리지 않는다.
 서버가 대시보드를 따라온다."
```

### 9.3 다음 단계

1. 이 계획서 검토 및 승인
2. **Phase 0 즉시 시작** (가장 중요)
3. 주간 진행상황 리뷰

---

**문서 작성**: Claude Code
**최종 수정**: 2025-12-22
