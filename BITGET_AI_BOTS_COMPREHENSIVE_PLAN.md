# Bitget AI Bots 완벽 구현 계획서

## 📊 Executive Summary

본 문서는 비트겟의 AI 자동매매 봇 시스템을 현재 플랫폼에 구현하기 위한 **완벽한 설계 및 실행 계획**입니다.

**목표**: 초보자도 투자 금액 비율만 설정하면 AI가 자동으로 최적의 전략을 추천하고 실행하는 시스템 구축

**핵심 차별점**:
- ✅ 비트겟보다 **더 쉬운 UX** (투자 비율 % 입력만으로 봇 실행)
- ✅ **무료 AI 추천** (DeepSeek API 활용으로 비용 최소화)
- ✅ **한국어 중심** 인터페이스 및 설명

---

## 🤖 비트겟 AI 봇 시스템 완벽 분석

### 1. 비트겟이 제공하는 봇 종류 (총 7종)

#### **1.1 Spot Grid Bot (현물 그리드)**
- **작동 방식**: 설정된 가격 범위 내에서 저점 매수 → 고점 매도 반복
- **적합한 시장**: 횡보장 (Range-bound market)
- **레버리지**: 없음 (현물)
- **AI 역할**: 최적의 가격 범위, 그리드 개수 추천
- **핵심 파라미터**:
  - Price Range (상단/하단 가격)
  - Number of Grids (10-200개)
  - Investment Amount

#### **1.2 Futures Grid Bot (선물 그리드)** ⭐ 우선순위 1위
- **작동 방식**: 선물 계약으로 그리드 전략 실행
- **그리드 타입**:
  - Long Grid: 상승장에서 저점 매수 → 고점 매도
  - Short Grid: 하락장에서 고점 매도 → 저점 매수
  - Neutral Grid: 양방향 거래 (횡보장 최적)
- **레버리지**: 최대 125x
- **AI 역할**: 7일간 백테스트 기반 파라미터 자동 생성
- **핵심 파라미터**:
  - Direction (Long/Short/Neutral)
  - Price Range (Lowest/Highest)
  - Number of Grids (1-200)
  - Leverage (1-125x)
  - Investment Amount
  - Take Profit / Stop Loss (선택)
  - Trigger Price (선택)
  - Grid Mode (Arithmetic/Geometric)

#### **1.3 Martingale Bot (마틴게일)**
- **작동 방식**: 손실 시 투자 금액을 2배로 늘려 평균 단가 낮춤
- **적합한 시장**: 트렌드 시장 (반등 예상)
- **레버리지**: 지원 (선물)
- **리스크**: 매우 높음 (연속 손실 시 청산 위험)
- **AI 역할**: 리스크 레벨 3단계 제공 (Conservative/Balanced/Aggressive)
- **핵심 파라미터**:
  - Initial Order Size
  - Price Step (몇 % 하락 시 추가 매수)
  - Multiplier (손실 시 배수, 기본 2배)
  - Max Safety Orders (최대 추가 매수 횟수)
  - Risk Level (AI 추천)

#### **1.4 CTA Bot (Commodity Trading Advisor)** ⭐ 우선순위 2위
- **작동 방식**: 기술적 지표 기반 자동 매매
- **지원 지표**: MACD, MA, Bollinger Bands, RSI 등
- **AI 역할**: 현재 시장에 최적화된 지표 조합 추천
- **핵심 파라미터**:
  - Indicator Selection (MACD, RSI 등)
  - Signal Threshold (매수/매도 임계값)
  - Position Size

#### **1.5 Smart Portfolio Bot (스마트 포트폴리오)**
- **작동 방식**: 여러 코인의 비율을 유지하며 자동 리밸런싱
- **예시**: BTC 50%, ETH 30%, SOL 20% 비율 유지
- **리밸런싱 조건**:
  - 시간 기반 (1일, 1주일 등)
  - 편차 기반 (±5% 벗어나면 리밸런싱)
- **AI 역할**: 최적의 포트폴리오 비율 추천
- **핵심 파라미터**:
  - Asset Allocation (코인별 비율)
  - Rebalance Frequency
  - Deviation Threshold

#### **1.6 Auto-Invest Bot (DCA - Dollar Cost Averaging)**
- **작동 방식**: 정기적으로 일정 금액 매수 (적립식 투자)
- **주기**: 매일, 매주, 매월
- **AI 역할**: 시장 변동성 분석 후 최적의 매수 주기 추천
- **핵심 파라미터**:
  - Investment Amount (회당 투자 금액)
  - Frequency (Daily/Weekly/Monthly)
  - Total Cycles (총 몇 회 투자)

#### **1.7 TradingView Signal Bot**
- **작동 방식**: TradingView 지표 시그널을 Webhook으로 받아 자동 주문
- **AI 역할**: 없음 (사용자 정의 지표 사용)
- **핵심 파라미터**:
  - Webhook URL
  - Signal Format (JSON)
  - Position Size

---

## 🎯 우리가 구현할 봇 우선순위

### Phase 1: MVP (3주) ⭐⭐⭐⭐⭐
1. **Futures Grid Bot AI** (가장 인기, ROI 시각화 쉬움)
2. **CTA Bot (RSI + MACD 기반)** (기존 전략 시스템 활용 가능)

### Phase 2: 확장 (2주)
3. **Martingale Bot** (고위험 고수익, 일부 사용자 수요)
4. **Auto-Invest Bot (DCA)** (초보자 친화적)

### Phase 3: 고급 (2주)
5. **Smart Portfolio Bot** (고급 사용자용)
6. **Spot Grid Bot** (선물 그리드와 로직 유사, 레버리지만 제외)

**TradingView Signal Bot은 제외** (사용자층이 한정적이며 구현 복잡도 높음)

---

## 🔍 현재 시스템과 비트겟 비교 분석

| 항목 | 비트겟 | 우리 시스템 (현재) | 격차 |
|------|--------|-------------------|------|
| **봇 종류** | 7종 (Grid, Martingale, CTA 등) | 1종 (단순 전략 봇) | ❌ 큰 격차 |
| **AI 추천** | ✅ 7일 백테스트 기반 파라미터 자동 생성 | ✅ DeepSeek API로 전략 생성 | ✅ 유사 |
| **투자 금액 설정** | 금액 직접 입력 | 금액 직접 입력 | ✅ 동일 |
| **ROI 표시** | ✅ 30일 APY % + 차트 | ❌ 없음 | ❌ 격차 |
| **다중 봇 관리** | ✅ 여러 봇 동시 실행 및 목록 조회 | ✅ 가능 (BotRunner 구조) | ✅ 인프라 준비됨 |
| **레버리지 설정** | ✅ 최대 125x | ✅ Bitget API 지원 | ✅ 동일 |
| **리스크 관리** | ✅ TP/SL, 일일 손실 한도 | ✅ 이미 구현됨 | ✅ 동일 |
| **백테스트** | ✅ 7일 기반 자동 | ✅ 별도 페이지 있음 | ✅ 유사 |
| **그리드 전략** | ✅ 200개 그리드 지원 | ❌ 없음 | ❌ 큰 격차 |
| **포지션 추적** | ✅ 각 그리드 레벨별 포지션 | ⚠️ 단일 포지션만 | ❌ 격차 |
| **UI/UX** | ✅ 매우 직관적 | ⚠️ 복잡함 | ❌ 격차 |

### 종합 평가
- **강점**: AI 연동, 리스크 관리, 백엔드 인프라는 이미 준비됨
- **약점**: 그리드 봇 로직, ROI 시각화, 다중 포지션 관리 미구현
- **결론**: **핵심 로직 추가로 비트겟과 동등한 수준 달성 가능**

---

## 🤖 AI의 역할 명확화

### 1. DeepSeek API 활용 전략

#### **1.1 AI가 할 일**
1. **시장 분석**
   - 과거 7일 캔들 데이터 분석 (변동성, 트렌드, 지지/저항선)
   - 현재 시장 상태 판단 (Uptrend/Downtrend/Sideways)
   - 변동성 지표 계산 (ATR, Bollinger Band Width 등)

2. **전략 추천**
   - 시장 상태에 맞는 봇 타입 추천 (Grid/CTA/Martingale)
   - 최적의 파라미터 생성:
     - Futures Grid: Price Range, Grid Count, Leverage
     - CTA: 지표 조합 (RSI + MACD 등), 임계값
     - Martingale: Risk Level, Safety Orders
   - 3개 전략 제시 (Conservative/Balanced/Aggressive)

3. **ROI 예측**
   - 과거 7일 데이터로 백테스트 실행
   - 30일 예상 ROI 계산 (APY %)
   - 리스크 지표 산출 (Max Drawdown, Win Rate)

4. **리스크 평가**
   - 청산 가격 계산
   - 최대 손실 시나리오 시뮬레이션
   - 권장 손절가 제시

#### **1.2 AI가 하지 않을 일** (백엔드 로직)
- ❌ 실제 주문 실행 (Bitget API 호출은 백엔드)
- ❌ 포지션 모니터링 (실시간 가격 추적은 WebSocket)
- ❌ 자동 재주문 (그리드 체결 후 재배치는 봇 엔진)
- ❌ 수익 계산 (실시간 PnL은 DB + Bitget API)

### 2. DeepSeek API 프롬프트 설계

#### **예시 1: Futures Grid 전략 추천**
```python
prompt = f"""
You are an expert cryptocurrency grid trading strategist. Analyze the market data below and recommend 3 Futures Grid Bot strategies.

**Market Data (Past 7 Days)**:
- Symbol: {symbol}
- Current Price: ${current_price}
- 7-day High: ${high_7d}
- 7-day Low: ${low_7d}
- 24h Volatility: {volatility}%
- Trend: {trend}  # Calculated by backend: uptrend/downtrend/sideways
- Support Level: ${support}
- Resistance Level: ${resistance}

**User Request**:
- Investment Amount: {investment_amount} USDT
- Risk Tolerance: {risk_tolerance}  # low/medium/high

**Task**:
Generate 3 Futures Grid Bot strategies (Conservative, Balanced, Aggressive) with:
1. Grid Type (Long/Short/Neutral)
2. Price Range (Lowest Price, Highest Price)
3. Number of Grids (10-200)
4. Leverage (1-20x for conservative, up to 50x for aggressive)
5. Expected 30-day ROI (% APY) - based on backtesting
6. Risk Level (low/medium/high)
7. Stop Loss Price (optional)
8. Take Profit Price (optional)
9. Explanation (why this strategy suits current market, in Korean)

**Output Format** (JSON):
[
  {{
    "name": "BTC Conservative Grid",
    "grid_type": "long",
    "price_range_lower": 95000,
    "price_range_upper": 105000,
    "grid_count": 20,
    "leverage": 3,
    "expected_roi_30d": 12.5,
    "risk_level": "low",
    "stop_loss": 92000,
    "take_profit": 108000,
    "explanation": "현재 BTC는 횡보 중이며, 95K-105K 범위에서 안정적인 그리드 거래가 예상됩니다. 레버리지 3배로 리스크를 최소화하면서 월 12.5% 수익을 목표로 합니다."
  }},
  ...
]
"""
```

#### **예시 2: CTA 전략 추천**
```python
prompt = f"""
You are a technical analysis expert. Recommend the best indicator combination for the current market.

**Market Data**:
- Symbol: {symbol}
- Current Price: ${current_price}
- RSI (14): {rsi}
- MACD: {macd}
- Moving Average (50/200): {ma_50}/{ma_200}
- Trend: {trend}

**Task**:
Recommend a CTA strategy with:
1. Primary Indicator (RSI/MACD/MA/BB)
2. Signal Threshold (e.g., RSI < 30 = Buy)
3. Position Size (% of investment)
4. Expected Win Rate (%)
5. Explanation (Korean)

**Output**: JSON
"""
```

### 3. AI API 비용 최적화

#### **캐싱 전략**
```python
# backend/src/services/grid_ai_cache.py

import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict

class AIStrategyCache:
    """AI 전략 추천 결과 캐싱 (Redis or In-Memory)"""

    def __init__(self):
        self.cache: Dict[str, Dict] = {}
        self.cache_duration = timedelta(hours=1)  # 1시간 캐시

    def get_cache_key(self, symbol: str, timeframe: str, investment: float) -> str:
        """캐시 키 생성"""
        data = f"{symbol}_{timeframe}_{investment}"
        return hashlib.md5(data.encode()).hexdigest()

    async def get_cached_strategy(
        self, symbol: str, timeframe: str, investment: float
    ) -> Optional[Dict]:
        """캐시된 전략 조회"""
        key = self.get_cache_key(symbol, timeframe, investment)
        if key in self.cache:
            cached = self.cache[key]
            if datetime.utcnow() - cached["timestamp"] < self.cache_duration:
                return cached["data"]
        return None

    async def set_cached_strategy(
        self, symbol: str, timeframe: str, investment: float, data: Dict
    ):
        """전략 캐싱"""
        key = self.get_cache_key(symbol, timeframe, investment)
        self.cache[key] = {
            "timestamp": datetime.utcnow(),
            "data": data
        }
```

#### **사전 생성 전략** (Cron Job)
```python
# backend/src/workers/ai_pregenerate.py

POPULAR_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
INVESTMENT_TIERS = [100, 500, 1000, 5000]  # USDT

async def pregenerate_strategies():
    """인기 코인의 전략을 매 시간마다 미리 생성"""
    for symbol in POPULAR_SYMBOLS:
        for investment in INVESTMENT_TIERS:
            strategies = await grid_ai_service.analyze_market_for_grid(
                symbol=symbol,
                investment_amount=investment
            )
            # DB에 저장
            await save_pregenerated_strategies(strategies)

# Celery Beat 스케줄러로 1시간마다 실행
```

#### **비용 예측**
- **DeepSeek API 가격**: $0.14 / 1M input tokens, $0.28 / 1M output tokens
- **1회 API 호출**: 약 2,000 input + 1,000 output tokens = $0.0006
- **캐싱 효과**: 90% 요청이 캐시 히트 → 실제 API 호출 10%만
- **사용자 100명, 월 1,000회 요청 가정**:
  - 캐싱 없을 때: 1,000 * $0.0006 = $0.60/월
  - 캐싱 있을 때: 100 * $0.0006 = $0.06/월
- **사전 생성 비용**: 4 코인 * 4 투자 티어 * 24시간 * 30일 * $0.0006 = $3.46/월
- **총 예상 비용**: $3.52/월 (사용자 100명 기준)

**결론**: AI API 비용은 무시할 수준 (월 $5 이하)

---

## 🏗️ 시스템 아키텍처 설계

### 1. 데이터베이스 스키마 (신규 모델)

```python
# backend/src/database/models.py (추가)

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

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 봇 기본 정보
    name = Column(String(100), nullable=False)  # "BTC Conservative Grid"
    bot_type = Column(SQLEnum(BotType), nullable=False)
    symbol = Column(String(20), nullable=False)  # "BTCUSDT"
    timeframe = Column(String(10), default="1h")  # "1m", "5m", "15m", "1h", "4h"

    # 투자 설정
    investment_amount = Column(Float, nullable=False)  # USDT
    investment_ratio = Column(Float, nullable=True)  # 계좌 대비 % (선택)
    leverage = Column(Integer, default=1)  # 1-125x

    # === Futures Grid 전용 파라미터 ===
    grid_type = Column(SQLEnum(GridType), nullable=True)
    grid_mode = Column(SQLEnum(GridMode), default=GridMode.ARITHMETIC)
    price_range_lower = Column(Float, nullable=True)
    price_range_upper = Column(Float, nullable=True)
    grid_count = Column(Integer, nullable=True)  # 1-200

    # === Martingale 전용 파라미터 ===
    initial_order_size = Column(Float, nullable=True)  # USDT
    price_step_percent = Column(Float, nullable=True)  # 몇 % 하락 시 추가 매수
    multiplier = Column(Float, default=2.0)  # 손실 시 배수
    max_safety_orders = Column(Integer, nullable=True)  # 최대 추가 매수 횟수

    # === CTA 전용 파라미터 ===
    indicator_type = Column(String(20), nullable=True)  # "RSI", "MACD", "MA"
    signal_params = Column(JSON, nullable=True)  # {"rsi_buy": 30, "rsi_sell": 70}

    # === Smart Portfolio 전용 파라미터 ===
    asset_allocation = Column(JSON, nullable=True)  # {"BTC": 50, "ETH": 30, "SOL": 20}
    rebalance_frequency = Column(String(20), nullable=True)  # "daily", "weekly"

    # 리스크 관리
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    trigger_price = Column(Float, nullable=True)  # 트리거 가격 (시작 조건)

    # 봇 상태
    status = Column(String(20), default="stopped")  # stopped, running, paused, error
    is_ai_recommended = Column(Boolean, default=True)  # AI 추천 전략 여부

    # 성과 지표
    total_profit = Column(Float, default=0.0)  # 총 수익 (USDT)
    total_profit_percent = Column(Float, default=0.0)  # 총 수익률 (%)
    roi_30d = Column(Float, nullable=True)  # 30일 예상 ROI (%)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)  # 승률 (%)
    max_drawdown = Column(Float, default=0.0)  # 최대 낙폭 (%)

    # AI 메타데이터
    ai_analysis = Column(JSON, nullable=True)  # AI 분석 결과 저장
    risk_level = Column(String(20), nullable=True)  # "low", "medium", "high"

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    user = relationship("User", backref="ai_bots")
    grid_positions = relationship("GridPosition", back_populates="bot", cascade="all, delete-orphan")


class GridPosition(Base):
    """그리드 봇의 개별 포지션 추적"""
    __tablename__ = "grid_positions"

    id = Column(Integer, primary_key=True)
    bot_id = Column(Integer, ForeignKey("ai_bots.id"), nullable=False)

    # 그리드 레벨
    grid_level = Column(Integer, nullable=False)  # 0부터 시작
    target_price = Column(Float, nullable=False)  # 목표 가격
    order_size = Column(Float, nullable=False)  # 주문 수량 (BTC)

    # 주문 상태
    status = Column(String(20), default="pending")  # pending, open, filled, closed
    side = Column(String(10), nullable=True)  # "buy" or "sell"

    # Bitget 주문 ID
    buy_order_id = Column(String(100), nullable=True)
    sell_order_id = Column(String(100), nullable=True)

    # 체결 정보
    entry_price = Column(Float, nullable=True)  # 실제 체결 가격
    entry_time = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime, nullable=True)

    # 수익
    profit = Column(Float, default=0.0)  # 실현 수익 (USDT)
    profit_percent = Column(Float, default=0.0)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    bot = relationship("AIBot", back_populates="grid_positions")


class AIStrategyRecommendation(Base):
    """AI 추천 전략 캐시 (사전 생성용)"""
    __tablename__ = "ai_strategy_recommendations"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    bot_type = Column(SQLEnum(BotType), nullable=False)
    investment_tier = Column(Float, nullable=False)  # 100, 500, 1000, 5000

    # 추천 파라미터 (JSON)
    parameters = Column(JSON, nullable=False)

    # 예측 지표
    expected_roi_30d = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    win_rate = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)

    # 시장 분석 (AI 응답 저장)
    market_analysis = Column(JSON, nullable=True)

    # 유효 기간
    expires_at = Column(DateTime, nullable=False)  # 1시간 후 만료
    created_at = Column(DateTime, default=datetime.utcnow)

    # 인덱스
    __table_args__ = (
        Index("idx_recommendation_active", "symbol", "bot_type", "expires_at"),
    )
```

### 2. 핵심 서비스 설계

#### **2.1 AI 분석 서비스**
```python
# backend/src/services/ai_strategy_service.py

from typing import List, Dict, Any
from .deepseek_service import deepseek_service
from .bitget_rest import BitgetRestClient
import numpy as np

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
            "volatility": 3.2,  # %
            "trend": "sideways",  # uptrend, downtrend, sideways
            "support_level": 95000.0,
            "resistance_level": 97500.0,
            "rsi": 52.3,
            "macd": {"signal": "neutral"},
            "volume_24h": 1234567890.0
        }
        """
        # 1. Bitget에서 과거 캔들 데이터 가져오기
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

        # 변동성 (7일 표준편차 / 평균)
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

        # 지지/저항선 (단순화: 7일 최저/최고)
        support_level = low_7d
        resistance_level = high_7d

        # RSI 계산
        rsi = self._calculate_rsi(closes, period=14)

        return {
            "symbol": symbol,
            "current_price": current_price,
            "high_7d": high_7d,
            "low_7d": low_7d,
            "volatility": round(volatility, 2),
            "trend": trend,
            "support_level": support_level,
            "resistance_level": resistance_level,
            "rsi": round(rsi, 2),
            "macd": {"signal": "neutral"},  # TODO: MACD 계산
            "candles": candles  # AI 백테스트용
        }

    async def recommend_futures_grid_strategies(
        self,
        symbol: str,
        investment_amount: float,
        risk_tolerance: str = "medium"  # low, medium, high
    ) -> List[Dict]:
        """
        Futures Grid 전략 3개 추천 (Conservative, Balanced, Aggressive)
        """
        # 1. 시장 분석
        market_data = await self.analyze_market(symbol)

        # 2. DeepSeek API 호출
        prompt = self._build_grid_strategy_prompt(
            market_data, investment_amount, risk_tolerance
        )

        strategies = await deepseek_service.generate_strategies_with_prompt(prompt)

        # 3. 백테스트 (AI가 제안한 파라미터로)
        for strategy in strategies:
            backtest_result = await self._backtest_grid_strategy(
                strategy, market_data["candles"]
            )
            strategy["backtest"] = backtest_result

        return strategies

    def _build_grid_strategy_prompt(
        self, market_data: Dict, investment: float, risk: str
    ) -> str:
        """Futures Grid 프롬프트 생성"""
        return f"""
        You are a cryptocurrency grid trading expert. Based on the market data below, recommend 3 Futures Grid Bot strategies.

        **Market Data (Past 7 Days)**:
        - Symbol: {market_data["symbol"]}
        - Current Price: ${market_data["current_price"]:,.2f}
        - 7-day High: ${market_data["high_7d"]:,.2f}
        - 7-day Low: ${market_data["low_7d"]:,.2f}
        - Volatility: {market_data["volatility"]}%
        - Trend: {market_data["trend"]}
        - Support: ${market_data["support_level"]:,.2f}
        - Resistance: ${market_data["resistance_level"]:,.2f}
        - RSI: {market_data["rsi"]}

        **User Requirements**:
        - Investment: {investment} USDT
        - Risk Tolerance: {risk}

        **Task**:
        Generate 3 strategies (Conservative, Balanced, Aggressive) with these fields:
        1. name (strategy name in Korean)
        2. grid_type (long/short/neutral)
        3. price_range_lower (number)
        4. price_range_upper (number)
        5. grid_count (10-200)
        6. leverage (1-20 for low risk, up to 50 for high)
        7. expected_roi_30d (% APY, realistic estimate)
        8. risk_level ("low"/"medium"/"high")
        9. stop_loss (price, optional)
        10. take_profit (price, optional)
        11. explanation (why this strategy suits current market, in Korean, 2-3 sentences)

        **Return JSON array only, no markdown**:
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
            "explanation": "현재 횡보장이므로 중립 그리드가 적합합니다. 3배 레버리지로 안전하게 월 15% 수익을 목표로 합니다."
          }},
          ...
        ]
        """

    async def _backtest_grid_strategy(
        self, strategy: Dict, candles: List[Dict]
    ) -> Dict:
        """
        그리드 전략 백테스트 (간단한 시뮬레이션)

        Returns:
        {
            "total_trades": 45,
            "win_rate": 78.5,
            "total_profit": 125.50,
            "max_drawdown": -8.2
        }
        """
        # TODO: 실제 백테스트 로직 구현
        # 1. 각 그리드 레벨에서 매수/매도 시뮬레이션
        # 2. 수익 계산
        # 3. 최대 낙폭 계산
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
            "max_drawdown": 0.0
        }

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

#### **2.2 그리드 봇 실행 엔진**
```python
# backend/src/services/grid_bot_engine.py

from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .bitget_rest import BitgetRestClient, OrderSide, OrderType
import asyncio
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
            logger.warning(f"Bot {bot.id} is already running")
            return

        # 1. 그리드 레벨 계산
        grid_levels = self._calculate_grid_levels(
            lower=bot.price_range_lower,
            upper=bot.price_range_upper,
            count=bot.grid_count,
            mode=bot.grid_mode
        )

        # 2. DB에 GridPosition 생성
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

    async def stop_bot(self, bot_id: int, session: AsyncSession):
        """그리드 봇 정지"""
        if bot_id in self.running_bots:
            self.running_bots[bot_id].cancel()
            del self.running_bots[bot_id]

        # 봇 상태 업데이트
        result = await session.execute(
            select(AIBot).where(AIBot.id == bot_id)
        )
        bot = result.scalars().first()
        if bot:
            bot.status = "stopped"
            bot.stopped_at = datetime.utcnow()
            await session.commit()

    async def _run_bot_loop(
        self,
        bot: AIBot,
        bitget_client: BitgetRestClient,
        session: AsyncSession
    ):
        """
        그리드 봇 메인 루프

        1. 초기 주문 배치 (현재가 기준 매수/매도 지정가 주문)
        2. 주문 체결 모니터링
        3. 체결된 주문의 반대 주문 생성
        4. 수익 계산
        """
        try:
            logger.info(f"Starting grid bot {bot.id} for {bot.symbol}")

            # 1. 초기 주문 배치
            await self._place_initial_orders(bot, bitget_client, session)

            # 2. 모니터링 루프
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
                    # Bitget API로 주문 상태 확인
                    if position.buy_order_id:
                        order_status = await bitget_client.get_order_status(
                            position.buy_order_id
                        )
                        if order_status == "filled":
                            # 매수 체결 완료 -> 매도 주문 생성
                            await self._create_sell_order(
                                position, bitget_client, session
                            )

                    if position.sell_order_id:
                        order_status = await bitget_client.get_order_status(
                            position.sell_order_id
                        )
                        if order_status == "filled":
                            # 매도 체결 완료 -> 수익 계산 및 매수 주문 재생성
                            await self._handle_sell_filled(
                                position, bitget_client, session
                            )

                # 3초마다 체크
                await asyncio.sleep(3.0)

        except asyncio.CancelledError:
            logger.info(f"Grid bot {bot.id} cancelled")
            # 모든 미체결 주문 취소
            await self._cancel_all_orders(bot, bitget_client, session)

        except Exception as e:
            logger.error(f"Grid bot {bot.id} error: {e}", exc_info=True)
            bot.status = "error"
            await session.commit()

    async def _place_initial_orders(
        self,
        bot: AIBot,
        bitget_client: BitgetRestClient,
        session: AsyncSession
    ):
        """초기 그리드 주문 배치"""
        # 현재가 조회
        ticker = await bitget_client.get_ticker(bot.symbol)
        current_price = float(ticker.get("lastPr", 0))

        # GridPosition 조회
        result = await session.execute(
            select(GridPosition).where(GridPosition.bot_id == bot.id)
        )
        positions = result.scalars().all()

        for position in positions:
            if bot.grid_type == GridType.LONG:
                # Long Grid: 현재가 이하에 매수 주문
                if position.target_price < current_price:
                    order = await bitget_client.place_limit_order(
                        symbol=bot.symbol,
                        side=OrderSide.BUY,
                        size=position.order_size,
                        price=position.target_price,
                        reduce_only=False
                    )
                    position.buy_order_id = order["orderId"]
                    position.status = "open"
                    position.side = "buy"

            elif bot.grid_type == GridType.SHORT:
                # Short Grid: 현재가 이상에 매도 주문
                if position.target_price > current_price:
                    order = await bitget_client.place_limit_order(
                        symbol=bot.symbol,
                        side=OrderSide.SELL,
                        size=position.order_size,
                        price=position.target_price,
                        reduce_only=False
                    )
                    position.sell_order_id = order["orderId"]
                    position.status = "open"
                    position.side = "sell"

            elif bot.grid_type == GridType.NEUTRAL:
                # Neutral Grid: 양방향 주문
                # TODO: 복잡한 로직 (현재가 기준 매수/매도 구분)
                pass

        await session.commit()

    async def _create_sell_order(
        self,
        position: GridPosition,
        bitget_client: BitgetRestClient,
        session: AsyncSession
    ):
        """매수 체결 후 매도 주문 생성"""
        # 다음 그리드 레벨 가격 계산 (profit_per_grid)
        next_grid_price = position.target_price * 1.01  # 1% 상승 시 매도

        order = await bitget_client.place_limit_order(
            symbol=position.bot.symbol,
            side=OrderSide.SELL,
            size=position.order_size,
            price=next_grid_price,
            reduce_only=True
        )

        position.sell_order_id = order["orderId"]
        position.entry_price = position.target_price
        position.entry_time = datetime.utcnow()
        await session.commit()

    async def _handle_sell_filled(
        self,
        position: GridPosition,
        bitget_client: BitgetRestClient,
        session: AsyncSession
    ):
        """매도 체결 후 수익 계산 및 재주문"""
        # 1. 수익 계산
        profit = (position.exit_price - position.entry_price) * position.order_size
        position.profit = profit
        position.status = "closed"
        position.exit_time = datetime.utcnow()

        # 2. 봇 통계 업데이트
        bot = position.bot
        bot.total_profit += profit
        bot.total_trades += 1

        # 3. 새로운 매수 주문 생성 (무한 반복)
        new_buy_order = await bitget_client.place_limit_order(
            symbol=bot.symbol,
            side=OrderSide.BUY,
            size=position.order_size,
            price=position.target_price,
            reduce_only=False
        )

        # 새 GridPosition 생성
        new_position = GridPosition(
            bot_id=bot.id,
            grid_level=position.grid_level,
            target_price=position.target_price,
            order_size=position.order_size,
            buy_order_id=new_buy_order["orderId"],
            status="open",
            side="buy"
        )
        session.add(new_position)

        await session.commit()

    def _calculate_grid_levels(
        self, lower: float, upper: float, count: int, mode: GridMode
    ) -> List[float]:
        """그리드 레벨 가격 계산"""
        if mode == GridMode.ARITHMETIC:
            # 등차수열 (가격 간격 동일)
            step = (upper - lower) / count
            return [lower + i * step for i in range(count + 1)]
        elif mode == GridMode.GEOMETRIC:
            # 등비수열 (% 간격 동일)
            ratio = (upper / lower) ** (1 / count)
            return [lower * (ratio ** i) for i in range(count + 1)]

    def _calculate_order_size(
        self, investment: float, grid_count: int, leverage: int
    ) -> float:
        """각 그리드 주문 수량 계산"""
        # 투자 금액을 그리드 개수로 나눔
        per_grid_investment = investment / grid_count
        # 레버리지 고려
        return per_grid_investment * leverage
```

---

## 📱 프론트엔드 UI/UX 설계

### 1. Futures Grid Bot 페이지 구조

```jsx
// frontend/src/pages/FuturesGridBot.jsx

import { useState, useEffect } from 'react';
import { Card, Tabs, Button, Slider, Select, Tag, Row, Col, Statistic, Table } from 'antd';
import { ThunderboltOutlined, RobotOutlined, LineChartOutlined } from '@ant-design/icons';
import { Line } from 'react-chartjs-2';
import axios from 'axios';

export default function FuturesGridBot() {
  const [activeTab, setActiveTab] = useState('ai');
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [investmentRatio, setInvestmentRatio] = useState(10); // %
  const [aiStrategies, setAiStrategies] = useState([]);
  const [runningBots, setRunningBots] = useState([]);
  const [loading, setLoading] = useState(false);

  // AI 전략 추천 가져오기
  const fetchAIStrategies = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/grid-bot/analyze', {
        symbol: symbol,
        investment_ratio: investmentRatio
      });
      setAiStrategies(response.data.strategies);
    } catch (error) {
      console.error('Failed to fetch AI strategies:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAIStrategies();
  }, [symbol]);

  // 전략 사용하기
  const handleUseStrategy = async (strategy) => {
    try {
      await axios.post('/api/grid-bot/create', {
        ...strategy,
        investment_ratio: investmentRatio
      });
      alert('Grid Bot이 시작되었습니다!');
      // 실행 중인 봇 목록 새로고침
      fetchRunningBots();
    } catch (error) {
      alert('봇 실행 실패: ' + error.message);
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
          <Col span={8}>
            <label>거래쌍</label>
            <Select
              value={symbol}
              onChange={setSymbol}
              style={{ width: '100%' }}
              options={[
                { label: 'BTC/USDT', value: 'BTCUSDT' },
                { label: 'ETH/USDT', value: 'ETHUSDT' },
                { label: 'SOL/USDT', value: 'SOLUSDT' },
              ]}
            />
          </Col>
          <Col span={12}>
            <label>투자 금액 비율 (%)</label>
            <Slider
              value={investmentRatio}
              onChange={setInvestmentRatio}
              min={5}
              max={50}
              marks={{ 5: '5%', 10: '10%', 20: '20%', 50: '50%' }}
            />
          </Col>
          <Col span={4}>
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={fetchAIStrategies}
              loading={loading}
              block
            >
              AI 분석
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 탭: AI 추천 vs 수동 설정 */}
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        {/* AI 추천 전략 */}
        <Tabs.TabPane tab="AI 추천" key="ai">
          <Row gutter={[16, 16]}>
            {aiStrategies.map((strategy, index) => (
              <Col span={8} key={index}>
                <Card
                  hoverable
                  style={{
                    border: strategy.risk_level === 'low' ? '2px solid #52c41a' : '1px solid #d9d9d9'
                  }}
                >
                  {/* 전략 헤더 */}
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <h3>{strategy.name}</h3>
                    <Tag color={strategy.grid_type === 'long' ? 'green' : 'red'}>
                      {strategy.grid_type.toUpperCase()} {strategy.leverage}X
                    </Tag>
                  </div>

                  {/* ROI 표시 (비트겟 스타일) */}
                  <div style={{ textAlign: 'center', margin: '20px 0' }}>
                    <div style={{ fontSize: '48px', fontWeight: 'bold', color: '#52c41a' }}>
                      {strategy.expected_roi_30d.toFixed(2)}%
                    </div>
                    <div style={{ color: '#888' }}>30-day APY</div>
                  </div>

                  {/* ROI 차트 (간단한 라인 차트) */}
                  <div style={{ height: '100px', marginBottom: '16px' }}>
                    <Line
                      data={{
                        labels: ['0', '7d', '14d', '21d', '30d'],
                        datasets: [{
                          data: [0, 5, 10, 15, strategy.expected_roi_30d],
                          borderColor: '#52c41a',
                          fill: true,
                          backgroundColor: 'rgba(82, 196, 26, 0.1)',
                          tension: 0.4
                        }]
                      }}
                      options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                          x: { display: false },
                          y: { display: false }
                        }
                      }}
                    />
                  </div>

                  {/* 투자 정보 */}
                  <div style={{ marginBottom: '16px' }}>
                    <p><strong>가격 범위:</strong> {strategy.price_range_lower.toLocaleString()} - {strategy.price_range_upper.toLocaleString()} USDT</p>
                    <p><strong>그리드 개수:</strong> {strategy.grid_count}개</p>
                    <p><strong>리스크:</strong> <Tag color={
                      strategy.risk_level === 'low' ? 'green' :
                      strategy.risk_level === 'medium' ? 'orange' : 'red'
                    }>{strategy.risk_level.toUpperCase()}</Tag></p>
                  </div>

                  {/* 설명 */}
                  <p style={{ color: '#666', fontSize: '14px' }}>
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
        </Tabs.TabPane>

        {/* 수동 설정 */}
        <Tabs.TabPane tab="Manual" key="manual">
          <Card>
            <p>수동 설정 폼 (나중에 구현)</p>
          </Card>
        </Tabs.TabPane>
      </Tabs>

      {/* 하단: 실행 중인 봇 목록 */}
      <div style={{ marginTop: '32px' }}>
        <h2>
          <LineChartOutlined /> My Grid Bots
        </h2>
        <Table
          dataSource={runningBots}
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
              render: (profit) => `$${profit.toFixed(2)}`
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
              render: (bot) => (
                <>
                  <Button size="small" onClick={() => handleStopBot(bot.id)}>Stop</Button>
                  <Button size="small" style={{ marginLeft: '8px' }}>Details</Button>
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

## 📅 단계별 구현 일정

### Phase 1: 기본 인프라 (3-4일)
- ✅ **Day 1**: 데이터베이스 모델 추가
  - `AIBot`, `GridPosition`, `AIStrategyRecommendation` 모델
  - Alembic 마이그레이션 생성 및 실행
- ✅ **Day 2**: AI 분석 서비스 기본 구조
  - `AIStrategyService` 클래스
  - 시장 분석 로직 (변동성, 트렌드, RSI 계산)
- ✅ **Day 3**: DeepSeek 프롬프트 최적화
  - Futures Grid 전략 추천 프롬프트
  - 응답 파싱 및 검증
- ✅ **Day 4**: API 엔드포인트 기본 틀
  - `/grid-bot/analyze` (AI 전략 추천)
  - `/grid-bot/create` (봇 생성)

### Phase 2: 그리드 봇 엔진 (5-7일)
- ✅ **Day 5-6**: GridBotEngine 기본 구조
  - 그리드 레벨 계산 (Arithmetic/Geometric)
  - 주문 수량 계산
- ✅ **Day 7-8**: 초기 주문 배치 로직
  - Long/Short/Neutral Grid 구분
  - Bitget API 지정가 주문 실행
- ✅ **Day 9-10**: 주문 체결 모니터링 및 재주문
  - 주문 상태 폴링
  - 매수 체결 후 매도 주문 생성
  - 매도 체결 후 수익 계산 및 재주문
- ✅ **Day 11**: 에러 처리 및 리스크 관리
  - 주문 실패 처리
  - Stop Loss / Take Profit 트리거

### Phase 3: 프론트엔드 (4-5일)
- ✅ **Day 12-13**: Futures Grid Bot 페이지 제작
  - AI 전략 카드 컴포넌트
  - ROI 차트 (react-chartjs-2)
  - 투자 비율 슬라이더
- ✅ **Day 14**: 실행 중인 봇 목록 UI
  - Table 컴포넌트
  - 실시간 ROI 업데이트 (WebSocket)
- ✅ **Day 15**: 봇 상세 페이지
  - 그리드 레벨별 포지션 현황
  - 거래 내역
  - 수익 차트

### Phase 4: 테스트 및 최적화 (3-4일)
- ✅ **Day 16**: 단위 테스트
  - GridBotEngine 로직 테스트
  - AI 프롬프트 응답 테스트
- ✅ **Day 17**: 모의 거래 테스트
  - 소액(10 USDT)으로 실제 Bitget 환경 테스트
  - 주문 체결 및 재주문 검증
- ✅ **Day 18**: 성능 최적화
  - DB 쿼리 최적화 (인덱스 추가)
  - WebSocket 부하 테스트
- ✅ **Day 19**: 문서화 및 배포
  - 사용자 가이드 작성
  - 프로덕션 배포

**총 예상 기간**: 약 3주 (19일 풀타임)

---

## 🚀 최종 결론 및 권장사항

### ✅ 구현 가능성: 매우 높음
1. **백엔드 인프라**: 이미 80% 준비됨 (Bitget API, 비동기 봇 실행, AI 연동)
2. **격차**: 그리드 봇 로직과 다중 포지션 관리만 추가하면 됨
3. **AI 비용**: 월 $5 이하로 매우 저렴
4. **차별화**: 비트겟보다 **더 쉬운 UX** (투자 비율 % 입력만으로 봇 실행)

### 📌 우선순위 추천
1. **MVP (3주)**: Futures Grid Bot AI만 먼저 완성
   - 가장 인기 있고 ROI 시각화가 쉬움
   - 초보자에게 가장 직관적
2. **Phase 2 (2주)**: CTA Bot (RSI/MACD 기반)
   - 기존 전략 시스템 활용 가능
3. **Phase 3**: Martingale, DCA, Smart Portfolio (선택사항)

### ⚠️ 리스크 및 주의사항
1. **실제 거래 테스트 필수**: 소액으로 충분히 검증 후 배포
2. **청산 리스크**: 레버리지 높을수록 위험, 초보자에게 경고 메시지 필수
3. **API Rate Limit**: Bitget API 호출 빈도 제한 확인
4. **법적 책임**: 투자 손실에 대한 면책 조항 명시

### 💡 다음 단계
작업을 시작하시겠습니까? 원하시면 **Phase 1 (Day 1)**부터 바로 시작할 수 있습니다!

---

## 📚 참고 자료

**Sources:**
- [A Complete Guide to AI Trading Bots on Bitget](https://beincrypto.com/learn/ai-trading-bots-bitget-guide/)
- [Mastering Bitget Trading Bots With Use Cases](https://www.bitget.com/support/articles/12560603805406)
- [Bitget Futures Grid Bot Setup Guide](https://www.bitget.com/academy/futures-grid-101)
- [Futures Grid parameters explained](https://www.bitget.com/support/articles/12560603791590)
- [Bitget's Martingale Strategy](https://www.bitget.com/academy/bitget-martingale-strategy-a-hands-on-tutorial)
- [Best Bitget Bots for 2025](https://algobot.com/bitget-bot/)
