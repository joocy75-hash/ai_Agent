# 🔧 AI Bots 기술 사양서

> **작성일**: 2024년 12월 8일
> **문서 타입**: 기술 상세 설계 (Database Schema, API Spec, Architecture)

---

## 📋 목차

1. [데이터베이스 설계](#데이터베이스-설계)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [API 엔드포인트 명세](#api-엔드포인트-명세)
4. [핵심 서비스 설계](#핵심-서비스-설계)
5. [AI 프롬프트 설계](#ai-프롬프트-설계)
6. [프론트엔드 컴포넌트](#프론트엔드-컴포넌트)

---

## 📊 데이터베이스 설계

### 1. AIBot 모델 (통합 봇 관리)

```python
# backend/src/database/models.py

from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class BotType(str, Enum):
    """봇 타입"""
    FUTURES_GRID = "futures_grid"
    SPOT_GRID = "spot_grid"
    MARTINGALE = "martingale"
    CTA = "cta"
    SMART_PORTFOLIO = "smart_portfolio"
    AUTO_INVEST = "auto_invest"


class GridType(str, Enum):
    """그리드 타입"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class GridMode(str, Enum):
    """그리드 모드"""
    ARITHMETIC = "arithmetic"  # 등차수열 (가격 간격 동일)
    GEOMETRIC = "geometric"    # 등비수열 (% 간격 동일)


class AIBot(Base):
    """AI 자동매매 봇 통합 모델"""
    __tablename__ = "ai_bots"

    # === 기본 정보 ===
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # "BTC Conservative Grid"
    bot_type = Column(Enum(BotType), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # "BTCUSDT"
    timeframe = Column(String(10), default="1h")  # "1m", "5m", "15m", "1h", "4h"

    # === 투자 설정 ===
    investment_amount = Column(Float, nullable=False)  # USDT
    investment_ratio = Column(Float, nullable=True)  # 계좌 대비 % (선택)
    leverage = Column(Integer, default=1)  # 1-125x

    # === Futures Grid 전용 파라미터 ===
    grid_type = Column(Enum(GridType), nullable=True)
    grid_mode = Column(Enum(GridMode), default=GridMode.ARITHMETIC)
    price_range_lower = Column(Float, nullable=True)  # 하단 가격
    price_range_upper = Column(Float, nullable=True)  # 상단 가격
    grid_count = Column(Integer, nullable=True)  # 그리드 개수 (1-200)

    # === Martingale 전용 파라미터 ===
    initial_order_size = Column(Float, nullable=True)  # 초기 주문 크기 (USDT)
    price_step_percent = Column(Float, nullable=True)  # 몇 % 하락 시 추가 매수
    multiplier = Column(Float, default=2.0)  # 손실 시 배수 (기본 2배)
    max_safety_orders = Column(Integer, nullable=True)  # 최대 추가 매수 횟수

    # === CTA 전용 파라미터 ===
    indicator_type = Column(String(20), nullable=True)  # "RSI", "MACD", "MA"
    signal_params = Column(JSON, nullable=True)  # {"rsi_buy": 30, "rsi_sell": 70}

    # === Smart Portfolio 전용 파라미터 ===
    asset_allocation = Column(JSON, nullable=True)  # {"BTC": 50, "ETH": 30, "SOL": 20}
    rebalance_frequency = Column(String(20), nullable=True)  # "daily", "weekly"

    # === 리스크 관리 ===
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    trigger_price = Column(Float, nullable=True)  # 트리거 가격 (시작 조건)

    # === 봇 상태 ===
    status = Column(String(20), default="stopped", index=True)
    # stopped, running, paused, error
    is_ai_recommended = Column(Boolean, default=True)  # AI 추천 전략 여부

    # === 성과 지표 ===
    total_profit = Column(Float, default=0.0)  # 총 수익 (USDT)
    total_profit_percent = Column(Float, default=0.0)  # 총 수익률 (%)
    roi_30d = Column(Float, nullable=True)  # 30일 예상 ROI (%)
    total_trades = Column(Integer, default=0)  # 총 거래 횟수
    win_rate = Column(Float, default=0.0)  # 승률 (%)
    max_drawdown = Column(Float, default=0.0)  # 최대 낙폭 (%)

    # === AI 메타데이터 ===
    ai_analysis = Column(JSON, nullable=True)  # AI 분석 결과 저장
    risk_level = Column(String(20), nullable=True)  # "low", "medium", "high"

    # === 타임스탬프 ===
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # === 관계 ===
    user = relationship("User", backref="ai_bots")
    grid_positions = relationship(
        "GridPosition",
        back_populates="bot",
        cascade="all, delete-orphan"
    )

    # === 인덱스 ===
    __table_args__ = (
        Index("idx_aibot_user_status", "user_id", "status"),
        Index("idx_aibot_symbol_type", "symbol", "bot_type"),
    )
```

### 2. GridPosition 모델 (그리드 레벨별 포지션)

```python
class GridPosition(Base):
    """그리드 봇의 개별 포지션 추적"""
    __tablename__ = "grid_positions"

    # === 기본 정보 ===
    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("ai_bots.id"), nullable=False, index=True)

    # === 그리드 레벨 ===
    grid_level = Column(Integer, nullable=False)  # 0부터 시작 (0, 1, 2, ...)
    target_price = Column(Float, nullable=False)  # 목표 가격
    order_size = Column(Float, nullable=False)  # 주문 수량 (BTC)

    # === 주문 상태 ===
    status = Column(String(20), default="pending", index=True)
    # pending, open, filled, closed
    side = Column(String(10), nullable=True)  # "buy" or "sell"

    # === Bitget 주문 ID ===
    buy_order_id = Column(String(100), nullable=True, index=True)
    sell_order_id = Column(String(100), nullable=True, index=True)

    # === 체결 정보 ===
    entry_price = Column(Float, nullable=True)  # 실제 체결 가격
    entry_time = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime, nullable=True)

    # === 수익 ===
    profit = Column(Float, default=0.0)  # 실현 수익 (USDT)
    profit_percent = Column(Float, default=0.0)  # 수익률 (%)

    # === 타임스탬프 ===
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # === 관계 ===
    bot = relationship("AIBot", back_populates="grid_positions")

    # === 인덱스 ===
    __table_args__ = (
        Index("idx_gridpos_bot_status", "bot_id", "status"),
        Index("idx_gridpos_level", "bot_id", "grid_level"),
    )
```

### 3. AIStrategyRecommendation 모델 (AI 추천 전략 캐싱)

```python
class AIStrategyRecommendation(Base):
    """AI 추천 전략 캐시 (사전 생성용)"""
    __tablename__ = "ai_strategy_recommendations"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)  # "BTCUSDT"
    bot_type = Column(Enum(BotType), nullable=False)
    investment_tier = Column(Float, nullable=False)  # 100, 500, 1000, 5000

    # === 추천 파라미터 (JSON) ===
    parameters = Column(JSON, nullable=False)
    # 예시: {
    #   "grid_type": "neutral",
    #   "price_range_lower": 95000,
    #   "price_range_upper": 105000,
    #   "grid_count": 30,
    #   "leverage": 3
    # }

    # === 예측 지표 ===
    expected_roi_30d = Column(Float, nullable=False)  # 30일 예상 ROI (%)
    risk_level = Column(String(20), nullable=False)  # "low", "medium", "high"
    win_rate = Column(Float, nullable=True)  # 예상 승률 (%)
    max_drawdown = Column(Float, nullable=True)  # 예상 최대 낙폭 (%)

    # === 시장 분석 (AI 응답 저장) ===
    market_analysis = Column(JSON, nullable=True)
    # 예시: {
    #   "trend": "sideways",
    #   "volatility": 3.2,
    #   "support": 94000,
    #   "resistance": 106000
    # }

    # === 유효 기간 ===
    expires_at = Column(DateTime, nullable=False, index=True)  # 1시간 후 만료
    created_at = Column(DateTime, default=datetime.utcnow)

    # === 인덱스 ===
    __table_args__ = (
        Index("idx_recommendation_active", "symbol", "bot_type", "expires_at"),
    )
```

### 4. Alembic 마이그레이션 파일 생성

```bash
# 마이그레이션 파일 생성
alembic revision --autogenerate -m "Add AI bots models"

# 마이그레이션 실행
alembic upgrade head
```

---

## 🏗️ 시스템 아키텍처

### 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                        사용자 (웹 브라우저)                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                   │
│  - FuturesGridBot.jsx (AI 추천 전략 페이지)                 │
│  - BotList.jsx (실행 중인 봇 목록)                           │
│  - BotDetails.jsx (봇 상세 페이지)                           │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket + REST API
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  API Layer                                            │  │
│  │  - /grid-bot/analyze (AI 전략 추천)                   │  │
│  │  - /grid-bot/create (봇 생성)                         │  │
│  │  - /grid-bot/{id}/start (봇 시작)                     │  │
│  │  - /grid-bot/{id}/stop (봇 정지)                      │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          ↓                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Service Layer                                        │  │
│  │  - AIStrategyService (AI 분석 및 추천)                │  │
│  │  - GridBotEngine (그리드 봇 실행)                     │  │
│  │  - MultiBotManager (다중 봇 관리)                     │  │
│  │  - AccountHelper (계좌 잔고 조회)                     │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          ↓                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Database (PostgreSQL / SQLite)                       │  │
│  │  - ai_bots                                            │  │
│  │  - grid_positions                                     │  │
│  │  - ai_strategy_recommendations                        │  │
│  │  - users, trades, etc.                                │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ DeepSeek API │ │ Bitget API   │ │ WebSocket    │
│ (AI 추천)    │ │ (주문 실행)  │ │ (실시간)     │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 데이터 흐름 (AI 전략 추천)

```
1. 사용자: "BTC 그리드 봇 AI 추천 요청"
   ↓
2. Frontend → Backend: POST /grid-bot/analyze
   {
     "symbol": "BTCUSDT",
     "investment_ratio": 10  // 잔고의 10%
   }
   ↓
3. Backend → Bitget API: 계좌 잔고 조회
   응답: { "available_balance": 10000 }
   ↓
4. Backend: 투자 금액 계산
   10000 * 10% = 1000 USDT
   ↓
5. Backend → Bitget API: 과거 7일 캔들 데이터 조회
   응답: [캔들 168개]
   ↓
6. Backend: 시장 분석 (변동성, 트렌드, RSI 계산)
   결과: {
     "volatility": 3.2,
     "trend": "sideways",
     "rsi": 52.3
   }
   ↓
7. Backend → DeepSeek API: AI 전략 추천 요청
   프롬프트: "현재 시장은 횡보장이며 변동성 3.2%입니다. 1000 USDT로..."
   응답: [Conservative, Balanced, Aggressive 전략 3개]
   ↓
8. Backend → Frontend: 3개 전략 반환
   [
     {
       "name": "BTC 안전 그리드",
       "grid_type": "neutral",
       "price_range_lower": 95000,
       "price_range_upper": 105000,
       "grid_count": 30,
       "leverage": 3,
       "expected_roi_30d": 15.2,
       "risk_level": "low"
     },
     ...
   ]
```

### 데이터 흐름 (봇 실행)

```
1. 사용자: "Conservative 전략 선택 → Use 클릭"
   ↓
2. Frontend → Backend: POST /grid-bot/create
   {
     "name": "BTC 안전 그리드",
     "symbol": "BTCUSDT",
     "grid_type": "neutral",
     "price_range_lower": 95000,
     "price_range_upper": 105000,
     "grid_count": 30,
     "leverage": 3,
     "investment_amount": 1000
   }
   ↓
3. Backend: AIBot 레코드 생성 (DB 저장)
   ↓
4. Frontend → Backend: POST /grid-bot/{bot_id}/start
   ↓
5. Backend: GridBotEngine.start_bot() 호출
   ↓
6. GridBotEngine: 그리드 레벨 30개 계산
   [95000, 95333, 95666, ..., 105000]
   ↓
7. GridBotEngine: GridPosition 30개 생성 (DB 저장)
   ↓
8. GridBotEngine: 현재가 조회 (96500)
   ↓
9. GridBotEngine → Bitget API: 지정가 주문 15개 배치 (현재가 이하)
   - 95000에 매수 주문
   - 95333에 매수 주문
   - ...
   - 96333에 매수 주문
   ↓
10. GridBotEngine: 비동기 모니터링 루프 시작 (3초마다)
    while True:
      - GridPosition 조회 (status='open')
      - Bitget API로 주문 상태 확인
      - 체결되면 반대 주문 생성 (매수 → 매도)
      - 수익 계산 및 DB 업데이트
      - WebSocket으로 프론트엔드에 알림
      - sleep(3초)
```

---

## 🌐 API 엔드포인트 명세

### 1. AI 전략 추천

#### `POST /grid-bot/analyze`

**설명**: AI 기반 그리드 전략 3개 추천

**Request**:
```json
{
  "symbol": "BTCUSDT",
  "investment_ratio": 10,  // 잔고의 10%
  "risk_tolerance": "medium"  // low, medium, high (선택)
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "account_balance": 10000.0,
  "investment_amount": 1000.0,
  "market_analysis": {
    "current_price": 96500.0,
    "trend": "sideways",
    "volatility": 3.2,
    "rsi": 52.3
  },
  "strategies": [
    {
      "name": "BTC 안전 그리드",
      "grid_type": "neutral",
      "price_range_lower": 95000,
      "price_range_upper": 105000,
      "grid_count": 30,
      "leverage": 3,
      "expected_roi_30d": 15.2,
      "risk_level": "low",
      "stop_loss": 93000,
      "take_profit": null,
      "explanation": "현재 횡보장이므로 중립 그리드가 적합합니다. 3배 레버리지로 안전하게 월 15% 수익을 목표로 합니다.",
      "backtest": {
        "total_trades": 45,
        "win_rate": 78.5,
        "max_drawdown": -8.2
      }
    },
    {
      "name": "BTC 밸런스 그리드",
      "grid_type": "neutral",
      "price_range_lower": 94000,
      "price_range_upper": 106000,
      "grid_count": 50,
      "leverage": 5,
      "expected_roi_30d": 28.5,
      "risk_level": "medium",
      "explanation": "중간 리스크로 월 28% 수익을 목표로 합니다."
    },
    {
      "name": "BTC 공격 그리드",
      "grid_type": "neutral",
      "price_range_lower": 92000,
      "price_range_upper": 108000,
      "grid_count": 100,
      "leverage": 10,
      "expected_roi_30d": 52.8,
      "risk_level": "high",
      "explanation": "고위험 고수익 전략입니다. 변동성을 최대한 활용합니다."
    }
  ]
}
```

**Error (400 Bad Request)**:
```json
{
  "success": false,
  "error": "투자 금액이 최소 요구사항(10 USDT)보다 적습니다."
}
```

### 2. 봇 생성

#### `POST /grid-bot/create`

**설명**: AI 추천 전략으로 봇 생성

**Request**:
```json
{
  "name": "BTC 안전 그리드",
  "symbol": "BTCUSDT",
  "bot_type": "futures_grid",
  "grid_type": "neutral",
  "price_range_lower": 95000,
  "price_range_upper": 105000,
  "grid_count": 30,
  "leverage": 3,
  "investment_amount": 1000,
  "stop_loss": 93000,
  "take_profit": null,
  "is_ai_recommended": true,
  "ai_analysis": {
    "trend": "sideways",
    "volatility": 3.2,
    "rsi": 52.3
  }
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "봇이 생성되었습니다.",
  "bot": {
    "id": 123,
    "name": "BTC 안전 그리드",
    "status": "stopped",
    "created_at": "2024-12-08T10:30:00Z"
  }
}
```

### 3. 봇 시작

#### `POST /grid-bot/{bot_id}/start`

**설명**: 봇 실행 시작

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "Bot started successfully",
  "bot_id": 123,
  "status": "running",
  "grid_positions_created": 30,
  "initial_orders_placed": 15
}
```

**Error (400 Bad Request)**:
```json
{
  "success": false,
  "error": "잔고 부족: 필요 1000 USDT, 사용 가능 500 USDT"
}
```

### 4. 봇 정지

#### `POST /grid-bot/{bot_id}/stop`

**설명**: 봇 정지 및 모든 미체결 주문 취소

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "Bot stopped successfully",
  "bot_id": 123,
  "status": "stopped",
  "cancelled_orders": 12,
  "total_profit": 45.50,
  "total_profit_percent": 4.55
}
```

### 5. 봇 목록 조회

#### `GET /grid-bot/list`

**설명**: 사용자의 모든 봇 조회

**Response (200 OK)**:
```json
{
  "success": true,
  "bots": [
    {
      "id": 123,
      "name": "BTC 안전 그리드",
      "symbol": "BTCUSDT",
      "bot_type": "futures_grid",
      "status": "running",
      "investment_amount": 1000,
      "total_profit": 45.50,
      "total_profit_percent": 4.55,
      "total_trades": 23,
      "win_rate": 78.5,
      "started_at": "2024-12-08T10:35:00Z"
    },
    {
      "id": 124,
      "name": "ETH 공격 그리드",
      "symbol": "ETHUSDT",
      "bot_type": "futures_grid",
      "status": "running",
      "investment_amount": 500,
      "total_profit": 28.30,
      "total_profit_percent": 5.66
    }
  ],
  "total_investment": 1500,
  "total_profit": 73.80
}
```

### 6. 봇 성과 조회

#### `GET /grid-bot/{bot_id}/performance`

**설명**: 봇 상세 성과 및 그리드 포지션 현황

**Response (200 OK)**:
```json
{
  "success": true,
  "bot": {
    "id": 123,
    "name": "BTC 안전 그리드",
    "status": "running",
    "total_profit": 45.50,
    "total_trades": 23,
    "win_rate": 78.5
  },
  "grid_positions": [
    {
      "grid_level": 0,
      "target_price": 95000,
      "status": "filled",
      "entry_price": 95000,
      "exit_price": 95333,
      "profit": 1.50
    },
    {
      "grid_level": 1,
      "target_price": 95333,
      "status": "open",
      "entry_price": null
    }
  ],
  "recent_trades": [
    {
      "timestamp": "2024-12-08T11:00:00Z",
      "side": "buy",
      "price": 95000,
      "size": 0.01,
      "profit": 1.50
    }
  ]
}
```

---

## 🧠 핵심 서비스 설계

### 1. AIStrategyService (AI 분석 및 추천)

```python
# backend/src/services/ai_strategy_service.py

from typing import List, Dict, Any
import numpy as np
from datetime import datetime, timedelta

class AIStrategyService:
    """AI 기반 전략 추천 및 시장 분석"""

    async def analyze_market(
        self,
        symbol: str,
        timeframe: str = "1h",
        days: int = 7
    ) -> Dict[str, Any]:
        """
        시장 분석 (AI 프롬프트용 데이터 생성)

        Returns:
        {
            "current_price": 96500.0,
            "high_7d": 98000.0,
            "low_7d": 94000.0,
            "volatility": 3.2,
            "trend": "sideways",
            "support_level": 95000.0,
            "resistance_level": 97500.0,
            "rsi": 52.3,
            "macd": {"signal": "neutral"}
        }
        """
        # 1. Bitget에서 과거 캔들 가져오기
        bitget = BitgetRestClient()
        candles = await bitget.get_historical_candles(
            symbol=symbol,
            interval=timeframe,
            limit=168  # 7일 * 24시간
        )

        # 2. 기술적 지표 계산
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        current_price = closes[-1]
        high_7d = max(highs)
        low_7d = min(lows)

        # 변동성 (표준편차 / 평균)
        volatility = (np.std(closes) / np.mean(closes)) * 100

        # 트렌드 판단 (이동평균 기반)
        ma_50 = np.mean(closes[-50:]) if len(closes) >= 50 else current_price
        ma_200 = np.mean(closes) if len(closes) >= 200 else current_price

        if current_price > ma_50 > ma_200:
            trend = "uptrend"
        elif current_price < ma_50 < ma_200:
            trend = "downtrend"
        else:
            trend = "sideways"

        # RSI 계산
        rsi = self._calculate_rsi(closes, period=14)

        return {
            "symbol": symbol,
            "current_price": current_price,
            "high_7d": high_7d,
            "low_7d": low_7d,
            "volatility": round(volatility, 2),
            "trend": trend,
            "support_level": low_7d,
            "resistance_level": high_7d,
            "rsi": round(rsi, 2),
            "candles": candles
        }

    async def recommend_futures_grid_strategies(
        self,
        symbol: str,
        investment_amount: float,
        risk_tolerance: str = "medium"
    ) -> List[Dict]:
        """
        Futures Grid 전략 3개 추천
        """
        # 1. 시장 분석
        market_data = await self.analyze_market(symbol)

        # 2. DeepSeek API 호출
        prompt = self._build_grid_strategy_prompt(
            market_data, investment_amount, risk_tolerance
        )

        strategies = await deepseek_service.generate_strategies_with_prompt(prompt)

        # 3. 백테스트
        for strategy in strategies:
            backtest_result = await self._backtest_grid_strategy(
                strategy, market_data["candles"]
            )
            strategy["backtest"] = backtest_result

        return strategies

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
```

### 2. GridBotEngine (그리드 봇 실행 엔진)

```python
# backend/src/services/grid_bot_engine.py

import asyncio
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class GridBotEngine:
    """Futures Grid Bot 실행 엔진"""

    def __init__(self, market_queue: asyncio.Queue):
        self.market_queue = market_queue
        self.running_bots: Dict[int, asyncio.Task] = {}

    async def start_bot(
        self,
        bot: AIBot,
        bitget_client: BitgetRestClient,
        session: AsyncSession
    ):
        """그리드 봇 시작"""
        if bot.id in self.running_bots:
            raise ValueError(f"Bot {bot.id} is already running")

        # 1. 그리드 레벨 계산
        grid_levels = self._calculate_grid_levels(
            lower=bot.price_range_lower,
            upper=bot.price_range_upper,
            count=bot.grid_count,
            mode=bot.grid_mode
        )

        # 2. GridPosition 생성
        for i, price in enumerate(grid_levels):
            grid_position = GridPosition(
                bot_id=bot.id,
                grid_level=i,
                target_price=price,
                order_size=self._calculate_order_size(
                    bot.investment_amount, bot.grid_count, bot.leverage
                ),
                status="pending"
            )
            session.add(grid_position)

        await session.commit()

        # 3. 비동기 태스크로 봇 실행
        task = asyncio.create_task(
            self._run_bot_loop(bot, bitget_client, session)
        )
        self.running_bots[bot.id] = task

        # 4. 봇 상태 업데이트
        bot.status = "running"
        bot.started_at = datetime.utcnow()
        await session.commit()

        logger.info(f"✅ Bot {bot.id} started with {len(grid_levels)} grid levels")

    async def _run_bot_loop(
        self,
        bot: AIBot,
        bitget_client: BitgetRestClient,
        session: AsyncSession
    ):
        """봇 메인 루프"""
        try:
            # 초기 주문 배치
            await self._place_initial_orders(bot, bitget_client, session)

            # 모니터링 루프
            while True:
                # GridPosition 조회
                result = await session.execute(
                    select(GridPosition).where(
                        GridPosition.bot_id == bot.id,
                        GridPosition.status.in_(["open", "filled"])
                    )
                )
                positions = result.scalars().all()

                for position in positions:
                    # 주문 상태 확인
                    if position.buy_order_id:
                        order = await bitget_client.get_order(position.buy_order_id)
                        if order["status"] == "filled":
                            await self._handle_buy_filled(position, bitget_client, session)

                    if position.sell_order_id:
                        order = await bitget_client.get_order(position.sell_order_id)
                        if order["status"] == "filled":
                            await self._handle_sell_filled(position, bitget_client, session)

                await asyncio.sleep(3.0)  # 3초마다 체크

        except asyncio.CancelledError:
            logger.info(f"Bot {bot.id} cancelled")
            await self._cancel_all_orders(bot, bitget_client, session)

    def _calculate_grid_levels(
        self, lower: float, upper: float, count: int, mode: GridMode
    ) -> List[float]:
        """그리드 레벨 계산"""
        if mode == GridMode.ARITHMETIC:
            # 등차수열
            step = (upper - lower) / count
            return [lower + i * step for i in range(count + 1)]
        elif mode == GridMode.GEOMETRIC:
            # 등비수열
            ratio = (upper / lower) ** (1 / count)
            return [lower * (ratio ** i) for i in range(count + 1)]

    def _calculate_order_size(
        self, investment: float, grid_count: int, leverage: int
    ) -> float:
        """주문 수량 계산"""
        per_grid_investment = investment / grid_count
        return per_grid_investment * leverage
```

### 3. MultiBotManager (다중 봇 관리)

```python
# backend/src/services/multi_bot_manager.py

class MultiBotManager:
    """한 사용자의 여러 봇을 동시에 관리"""

    def __init__(self):
        # user_id → {bot_id: asyncio.Task}
        self.running_bots: Dict[int, Dict[int, asyncio.Task]] = {}

    async def start_bot(
        self, user_id: int, bot_id: int, session: AsyncSession
    ):
        """사용자의 봇 시작"""
        # 1. 사용자별 봇 딕셔너리 초기화
        if user_id not in self.running_bots:
            self.running_bots[user_id] = {}

        # 2. 잔고 체크
        bitget_client = await get_user_bitget_client(user_id)
        balance = await get_user_balance(user_id, bitget_client)

        # 3. 모든 실행 중인 봇의 총 투자 금액
        total_investment = sum(
            bot.investment_amount
            for bot_id, task in self.running_bots[user_id].items()
            if not task.done()
        )

        # 4. 새 봇 투자 금액 추가
        new_bot = await session.get(AIBot, bot_id)
        total_investment += new_bot.investment_amount

        # 5. 잔고 부족 체크
        if total_investment > balance["available_balance"]:
            raise ValueError(
                f"잔고 부족: 필요 {total_investment} USDT, "
                f"사용 가능 {balance['available_balance']} USDT"
            )

        # 6. 봇 실행
        task = asyncio.create_task(
            grid_bot_engine.start_bot(new_bot, bitget_client, session)
        )
        self.running_bots[user_id][bot_id] = task

        logger.info(f"User {user_id}: {len(self.running_bots[user_id])} bots running")
```

---

## 🎨 AI 프롬프트 설계

### DeepSeek 프롬프트 템플릿 (Futures Grid)

```python
# backend/src/services/deepseek_service.py

def _build_grid_strategy_prompt(
    self, market_data: Dict, investment: float, risk: str
) -> str:
    """Futures Grid 전략 추천 프롬프트"""
    return f"""
You are a professional cryptocurrency grid trading expert. Based on the market data below, recommend 3 Futures Grid Bot strategies optimized for different risk levels.

**Market Data (Past 7 Days)**:
- Symbol: {market_data["symbol"]}
- Current Price: ${market_data["current_price"]:,.2f}
- 7-day High: ${market_data["high_7d"]:,.2f}
- 7-day Low: ${market_data["low_7d"]:,.2f}
- Volatility: {market_data["volatility"]}%
- Trend: {market_data["trend"]}
- Support Level: ${market_data["support_level"]:,.2f}
- Resistance Level: ${market_data["resistance_level"]:,.2f}
- RSI (14): {market_data["rsi"]}

**User Investment**:
- Amount: {investment} USDT
- Risk Tolerance: {risk}

**Task**:
Generate 3 strategies (Conservative, Balanced, Aggressive) with these fields:

1. **name**: Strategy name in Korean (e.g., "BTC 안전 그리드")
2. **grid_type**: "long" (uptrend), "short" (downtrend), or "neutral" (sideways)
3. **price_range_lower**: Lower bound price (number)
4. **price_range_upper**: Upper bound price (number)
5. **grid_count**: Number of grids (10-200)
6. **leverage**: Leverage multiplier
   - Conservative: 1-5x
   - Balanced: 5-10x
   - Aggressive: 10-20x
7. **expected_roi_30d**: Expected 30-day APY in % (realistic estimate based on volatility)
8. **risk_level**: "low", "medium", or "high"
9. **stop_loss**: Stop loss price (optional, null if none)
10. **take_profit**: Take profit price (optional, null if none)
11. **explanation**: 2-3 sentences in Korean explaining why this strategy suits the current market

**Guidelines**:
- For sideways markets (trend="sideways"), prefer "neutral" grid type
- For uptrends, prefer "long" grid type
- For downtrends, prefer "short" grid type
- Price range should be within support-resistance levels
- Higher volatility → more grids and wider range
- Lower volatility → fewer grids and tighter range
- Conservative: Prioritize safety, lower leverage, tighter stop loss
- Aggressive: Higher leverage, wider range, no stop loss

**Output Format** (JSON array only, no markdown):
[
  {{
    "name": "BTC 안전 그리드",
    "grid_type": "neutral",
    "price_range_lower": 95000,
    "price_range_upper": 98000,
    "grid_count": 30,
    "leverage": 3,
    "expected_roi_30d": 15.2,
    "risk_level": "low",
    "stop_loss": 93000,
    "take_profit": null,
    "explanation": "현재 횡보장이므로 중립 그리드가 적합합니다. 3배 레버리지로 안전하게 월 15% 수익을 목표로 합니다. 손절가를 타이트하게 설정하여 리스크를 최소화합니다."
  }},
  {{
    "name": "BTC 밸런스 그리드",
    "grid_type": "neutral",
    "price_range_lower": 94000,
    "price_range_upper": 100000,
    "grid_count": 50,
    "leverage": 7,
    "expected_roi_30d": 28.5,
    "risk_level": "medium",
    "stop_loss": 92000,
    "take_profit": 102000,
    "explanation": "변동성을 적극 활용하는 중간 리스크 전략입니다. 50개 그리드로 촘촘하게 배치하여 거래 기회를 극대화합니다."
  }},
  {{
    "name": "BTC 공격 그리드",
    "grid_type": "neutral",
    "price_range_lower": 92000,
    "price_range_upper": 105000,
    "grid_count": 100,
    "leverage": 15,
    "expected_roi_30d": 52.8,
    "risk_level": "high",
    "stop_loss": null,
    "take_profit": null,
    "explanation": "고위험 고수익 전략입니다. 넓은 가격 범위와 높은 레버리지로 변동성을 최대한 활용하여 월 50% 이상의 수익을 목표로 합니다."
  }}
]
"""
```

### 프롬프트 최적화 팁

1. **명확한 지시**: "JSON array only, no markdown" → DeepSeek이 markdown 없이 순수 JSON 반환
2. **구체적인 예시**: 실제 출력 형식을 보여줘서 정확도 향상
3. **가이드라인 제공**: 시장 상황별 전략 선택 기준 명시
4. **한국어 요구**: `explanation` 필드는 한국어로 작성 요청

---

## 💻 프론트엔드 컴포넌트

### 1. FuturesGridBot.jsx (메인 페이지)

```jsx
// frontend/src/pages/FuturesGridBot.jsx

import React, { useState, useEffect } from 'react';
import { Card, Tabs, Button, Slider, Select, Tag, Row, Col, Table, Spin } from 'antd';
import { RobotOutlined, ThunderboltOutlined, LineChartOutlined } from '@ant-design/icons';
import { Line } from 'react-chartjs-2';
import axios from 'axios';

export default function FuturesGridBot() {
  const [activeTab, setActiveTab] = useState('ai');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [investmentRatio, setInvestmentRatio] = useState(10);
  const [aiStrategies, setAiStrategies] = useState([]);
  const [runningBots, setRunningBots] = useState([]);
  const [accountBalance, setAccountBalance] = useState(0);
  const [loading, setLoading] = useState(false);

  // 계좌 잔고 조회
  useEffect(() => {
    fetchAccountBalance();
    fetchRunningBots();
  }, []);

  const fetchAccountBalance = async () => {
    try {
      const res = await axios.get('/api/account/balance');
      setAccountBalance(res.data.available_balance);
    } catch (error) {
      console.error('Failed to fetch balance:', error);
    }
  };

  // AI 전략 추천
  const fetchAIStrategies = async () => {
    setLoading(true);
    try {
      const res = await axios.post('/api/grid-bot/analyze', {
        symbol: symbol,
        investment_ratio: investmentRatio
      });
      setAiStrategies(res.data.strategies);
    } catch (error) {
      console.error('AI 분석 실패:', error);
      alert('AI 분석에 실패했습니다: ' + error.response?.data?.error);
    } finally {
      setLoading(false);
    }
  };

  // 실행 중인 봇 목록 조회
  const fetchRunningBots = async () => {
    try {
      const res = await axios.get('/api/grid-bot/list');
      setRunningBots(res.data.bots);
    } catch (error) {
      console.error('Failed to fetch bots:', error);
    }
  };

  // 전략 사용하기
  const handleUseStrategy = async (strategy) => {
    try {
      // 1. 봇 생성
      const createRes = await axios.post('/api/grid-bot/create', {
        ...strategy,
        symbol: symbol,
        investment_amount: accountBalance * (investmentRatio / 100)
      });

      const botId = createRes.data.bot.id;

      // 2. 봇 시작
      await axios.post(`/api/grid-bot/${botId}/start`);

      alert('Grid Bot이 시작되었습니다!');

      // 3. 목록 새로고침
      fetchRunningBots();
      fetchAccountBalance();

    } catch (error) {
      alert('봇 실행 실패: ' + error.response?.data?.error);
    }
  };

  // 봇 정지
  const handleStopBot = async (botId) => {
    if (!confirm('정말 이 봇을 정지하시겠습니까?')) return;

    try {
      await axios.post(`/api/grid-bot/${botId}/stop`);
      alert('봇이 정지되었습니다.');
      fetchRunningBots();
      fetchAccountBalance();
    } catch (error) {
      alert('봇 정지 실패: ' + error.message);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* 페이지 헤더 */}
      <h1>
        <RobotOutlined /> Futures Grid Bot AI
      </h1>
      <p style={{ color: '#888' }}>
        AI가 추천하는 최적의 그리드 전략으로 자동 거래를 시작하세요
      </p>

      {/* 상단: 심볼 및 투자 비율 선택 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={16}>
          <Col span={6}>
            <label><strong>거래쌍</strong></label>
            <Select
              value={symbol}
              onChange={setSymbol}
              style={{ width: '100%', marginTop: '8px' }}
              options={[
                { label: 'BTC/USDT', value: 'BTCUSDT' },
                { label: 'ETH/USDT', value: 'ETHUSDT' },
                { label: 'SOL/USDT', value: 'SOLUSDT' },
                { label: 'BNB/USDT', value: 'BNBUSDT' },
              ]}
            />
          </Col>

          <Col span={14}>
            <label><strong>투자 금액 비율 (%)</strong></label>
            <Slider
              value={investmentRatio}
              onChange={setInvestmentRatio}
              min={5}
              max={50}
              marks={{ 5: '5%', 10: '10%', 20: '20%', 30: '30%', 50: '50%' }}
              style={{ marginTop: '16px' }}
            />
            <p style={{ color: '#52c41a', fontSize: '16px', marginTop: '8px' }}>
              💰 투자 금액: <strong>${(accountBalance * investmentRatio / 100).toFixed(2)}</strong> USDT
              <span style={{ color: '#888', marginLeft: '16px' }}>
                (잔고: ${accountBalance.toFixed(2)} USDT)
              </span>
            </p>
          </Col>

          <Col span={4}>
            <Button
              type="primary"
              size="large"
              icon={<ThunderboltOutlined />}
              onClick={fetchAIStrategies}
              loading={loading}
              block
              style={{ marginTop: '24px' }}
            >
              AI 분석
            </Button>
          </Col>
        </Row>
      </Card>

      {/* AI 추천 전략 */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px' }}>
          <Spin size="large" />
          <p style={{ marginTop: '16px', color: '#888' }}>AI가 시장을 분석하고 있습니다...</p>
        </div>
      ) : (
        <Row gutter={[16, 16]} style={{ marginBottom: '32px' }}>
          {aiStrategies.map((strategy, index) => (
            <Col span={8} key={index}>
              <Card
                hoverable
                style={{
                  border: strategy.risk_level === 'low' ? '2px solid #52c41a' : '1px solid #d9d9d9',
                  height: '100%'
                }}
              >
                {/* 전략 헤더 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <h3>{strategy.name}</h3>
                  <Tag color={strategy.grid_type === 'long' ? 'green' : strategy.grid_type === 'short' ? 'red' : 'blue'}>
                    {strategy.grid_type.toUpperCase()} {strategy.leverage}X
                  </Tag>
                </div>

                {/* ROI 표시 */}
                <div style={{ textAlign: 'center', margin: '24px 0' }}>
                  <div style={{ fontSize: '48px', fontWeight: 'bold', color: '#52c41a' }}>
                    {strategy.expected_roi_30d.toFixed(1)}%
                  </div>
                  <div style={{ color: '#888' }}>30-day APY</div>
                </div>

                {/* 투자 정보 */}
                <div style={{ marginBottom: '16px' }}>
                  <p><strong>가격 범위:</strong> ${strategy.price_range_lower.toLocaleString()} - ${strategy.price_range_upper.toLocaleString()}</p>
                  <p><strong>그리드 개수:</strong> {strategy.grid_count}개</p>
                  <p><strong>리스크:</strong> <Tag color={
                    strategy.risk_level === 'low' ? 'green' :
                    strategy.risk_level === 'medium' ? 'orange' : 'red'
                  }>{strategy.risk_level.toUpperCase()}</Tag></p>
                </div>

                {/* 설명 */}
                <p style={{ color: '#666', fontSize: '14px', lineHeight: '1.6', marginBottom: '16px' }}>
                  {strategy.explanation}
                </p>

                {/* 사용하기 버튼 */}
                <Button
                  type="primary"
                  size="large"
                  block
                  onClick={() => handleUseStrategy(strategy)}
                >
                  Use
                </Button>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 실행 중인 봇 목록 */}
      <div style={{ marginTop: '48px' }}>
        <h2>
          <LineChartOutlined /> My Grid Bots ({runningBots.length}개 실행 중)
        </h2>
        <Table
          dataSource={runningBots}
          rowKey="id"
          columns={[
            {
              title: 'Bot Name',
              dataIndex: 'name',
              key: 'name'
            },
            {
              title: 'Symbol',
              dataIndex: 'symbol',
              key: 'symbol'
            },
            {
              title: 'ROI',
              dataIndex: 'total_profit_percent',
              key: 'roi',
              render: (roi) => (
                <span style={{ color: roi > 0 ? '#52c41a' : '#ff4d4f', fontWeight: 'bold' }}>
                  {roi > 0 ? '+' : ''}{roi.toFixed(2)}%
                </span>
              )
            },
            {
              title: 'Profit',
              dataIndex: 'total_profit',
              key: 'profit',
              render: (profit) => (
                <span style={{ color: profit > 0 ? '#52c41a' : '#ff4d4f' }}>
                  ${profit.toFixed(2)}
                </span>
              )
            },
            {
              title: 'Investment',
              dataIndex: 'investment_amount',
              key: 'investment',
              render: (amount) => `$${amount.toFixed(2)}`
            },
            {
              title: 'Trades',
              dataIndex: 'total_trades',
              key: 'trades'
            },
            {
              title: 'Status',
              dataIndex: 'status',
              key: 'status',
              render: (status) => (
                <Tag color={status === 'running' ? 'green' : 'default'}>
                  {status.toUpperCase()}
                </Tag>
              )
            },
            {
              title: 'Actions',
              key: 'actions',
              render: (_, bot) => (
                <>
                  <Button size="small" danger onClick={() => handleStopBot(bot.id)}>
                    Stop
                  </Button>
                  <Button size="small" style={{ marginLeft: '8px' }} href={`/grid-bot/${bot.id}`}>
                    Details
                  </Button>
                </>
              )
            }
          ]}
        />
      </div>
    </div>
  );
}
```

---

## 📚 참고 자료

### Bitget 공식 문서
- [Futures Grid parameters explained](https://www.bitget.com/support/articles/12560603791590)
- [Bitget Futures Grid Bot Setup Guide](https://www.bitget.com/academy/futures-grid-101)

### 기술 문서
- [DeepSeek API](https://platform.deepseek.com/api-docs/)
- [Bitget API v2](https://www.bitget.com/api-doc/common/intro)
- [FastAPI Async](https://fastapi.tiangolo.com/async/)
- [SQLAlchemy Async ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

---

**작성자**: Claude AI
**최종 업데이트**: 2024년 12월 8일
**버전**: 1.0.0
