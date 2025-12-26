# Auto Trading Dashboard - 전략 개발 완벽 가이드

> **이 문서는 새로운 트레이딩 전략을 개발할 때 반드시 참고해야 하는 기술 문서입니다.**
> 플랫폼 아키텍처, 데이터 흐름, 인터페이스 규약을 상세히 설명합니다.

---

## 목차

1. [시스템 아키텍처 개요](#1-시스템-아키텍처-개요)
2. [전략 실행 흐름](#2-전략-실행-흐름)
3. [핵심 인터페이스](#3-핵심-인터페이스)
4. [데이터 구조](#4-데이터-구조)
5. [AI 에이전트 시스템](#5-ai-에이전트-시스템)
6. [마진 관리 시스템](#6-마진-관리-시스템)
7. [전략 유형별 템플릿](#7-전략-유형별-템플릿)
8. [전략 등록 및 배포](#8-전략-등록-및-배포)
9. [테스트 가이드](#9-테스트-가이드)
10. [모범 사례 및 주의사항](#10-모범-사례-및-주의사항)

---

## 1. 시스템 아키텍처 개요

### 1.1 전체 구조도

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BOT RUNNER (bot_runner.py)                       │
│   - 메인 실행 루프                                                        │
│   - 캔들 데이터 수집                                                      │
│   - 포지션 동기화                                                         │
│   - 주문 실행                                                             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     STRATEGY LOADER (strategy_loader.py)                 │
│   - 전략 팩토리 패턴                                                      │
│   - 전략 인스턴스 캐싱                                                    │
│   - AI 에이전트 초기화                                                    │
│   - generate_signal_with_strategy() 엔트리 포인트                         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
          ┌─────────────────┐ ┌─────────────┐ ┌──────────────────┐
          │ Basic Strategy  │ │ AI Strategy │ │ Autonomous       │
          │ (규칙 기반)      │ │ (AI 강화)   │ │ Strategy (자율)  │
          │                 │ │             │ │                  │
          │ proven_         │ │ deepseek_ai │ │ eth_autonomous   │
          │ conservative    │ │             │ │ _40pct           │
          │ proven_balanced │ │             │ │ autonomous_30pct │
          │ proven_         │ │             │ │                  │
          │ aggressive      │ │             │ │                  │
          └─────────────────┘ └──────┬──────┘ └────────┬─────────┘
                                     │                 │
                                     └────────┬────────┘
                                              ▼
                    ┌─────────────────────────────────────────────────┐
                    │              4-AGENT SYSTEM                      │
                    │  ┌────────────────┐  ┌────────────────┐         │
                    │  │ Market Regime  │  │ Signal         │         │
                    │  │ Agent          │  │ Validator      │         │
                    │  │ - 시장환경분석 │  │ - 신호검증     │         │
                    │  │ - 추세/횡보    │  │ - 10가지 규칙  │         │
                    │  └────────────────┘  └────────────────┘         │
                    │  ┌────────────────┐  ┌────────────────┐         │
                    │  │ Risk Monitor   │  │ Portfolio      │         │
                    │  │ Agent          │  │ Optimizer      │         │
                    │  │ - 리스크 감시  │  │ - 자본배분     │         │
                    │  │ - 청산가 경고  │  │ - 레버리지     │         │
                    │  └────────────────┘  └────────────────┘         │
                    └─────────────────────────────────────────────────┘
```

### 1.2 등록된 전략 코드

| 전략 코드 | 유형 | 설명 | 마진 제한 |
|-----------|------|------|-----------|
| `proven_conservative` | Basic | EMA 크로스오버 기반 | 제한 없음 |
| `proven_balanced` | Basic | RSI 다이버전스 기반 | 제한 없음 |
| `proven_aggressive` | Basic | 모멘텀 브레이크아웃 | 제한 없음 |
| `deepseek_ai` | AI | DeepSeek API 직접 호출 | 제한 없음 |
| `ai_role_division` | AI | 역할 분담 AI | 제한 없음 |
| `autonomous_30pct` | Autonomous | 30% 마진 자율 거래 | **30%** |
| `adaptive_market_regime_fighter` | Autonomous | 시장 환경 적응형 | **30%** |
| `eth_autonomous_40pct` | Autonomous | ETH 특화 자율 거래 | **40%** |

### 1.3 핵심 파일 위치

```
backend/
├── src/
│   ├── services/
│   │   ├── bot_runner.py          # 메인 봇 실행 로직 (~2700 lines)
│   │   ├── strategy_loader.py     # 전략 로딩 및 팩토리
│   │   ├── bitget_rest.py         # 거래소 REST API
│   │   └── bitget_ws_collector.py # WebSocket 데이터 수집
│   │
│   ├── strategies/
│   │   ├── __init__.py            # 전략 코드 목록
│   │   ├── proven_conservative_strategy.py
│   │   ├── proven_balanced_strategy.py
│   │   ├── proven_aggressive_strategy.py
│   │   ├── autonomous_30pct_strategy.py
│   │   ├── adaptive_market_regime_fighter.py
│   │   └── eth_ai_autonomous_40pct_strategy.py  # 현재 메인 전략
│   │
│   └── agents/
│       ├── market_regime/agent.py
│       ├── signal_validator/agent.py
│       ├── risk_monitor/agent.py
│       └── portfolio_optimizer/
```

---

## 2. 전략 실행 흐름

### 2.1 신호 생성 파이프라인

```
[1] 캔들 데이터 수집 (Bitget REST API)
     │
     │  candles = [{open, high, low, close, volume, timestamp}, ...]
     │
     ▼
[2] 현재 포지션 확인 (거래소 또는 캐시)
     │
     │  current_position = {side, entry_price, size, pnl, ...}
     │
     ▼
[3] 전략 신호 생성 (generate_signal_with_strategy)
     │
     │  ┌─────────────────────────────────────────────────────┐
     │  │ strategy.generate_signal(price, candles, position) │
     │  │                                                     │
     │  │ [Basic Strategy]                                    │
     │  │   - 기술적 지표 계산 (EMA, RSI, MACD 등)            │
     │  │   - 규칙 기반 신호 생성                             │
     │  │                                                     │
     │  │ [AI Strategy]                                       │
     │  │   - Market Regime 분석 → DeepSeek AI                │
     │  │   - Signal Validation → 10가지 규칙 검증            │
     │  │   - Risk Assessment → 포지션 위험도 평가            │
     │  │   - Portfolio Optimization → 최적 사이즈 계산       │
     │  └─────────────────────────────────────────────────────┘
     │
     │  signal = {action, confidence, reason, stop_loss, take_profit, ...}
     │
     ▼
[4] 신호 검증 (AI 전략의 경우)
     │
     │  - 신뢰도 임계값 확인 (< 0.6 거부)
     │  - 시장 환경 적합성 (volatile/low_volume → 거부)
     │  - 급격한 가격 변동 감지 (5분간 2% 변동 → 거부)
     │  - 포지션 반전 안전성 검사
     │
     ▼
[5] 리스크 체크 및 주문 실행
     │
     │  - 마진 한도 확인 (30% 또는 40%)
     │  - 일일 손실 한도 확인 (5%)
     │  - 레버리지 검증
     │  - 주문 실행 (시장가/지정가)
     │
     ▼
[6] 포지션 업데이트 및 기록
     │
     └─→ DB 저장, WebSocket 브로드캐스트, 로그 기록
```

### 2.2 Bot Runner 핵심 코드 (간략화)

```python
# bot_runner.py:790-850 (simplified)

async def _run_trading_loop(self, ...):
    while running:
        # 1. 캔들 데이터 가져오기
        candles = await fetch_candles(symbol, timeframe, limit=100)
        current_price = candles[-1]['close']

        # 2. 현재 포지션 확인
        current_position = await get_current_position(user_id, symbol)

        # 3. 전략 신호 생성
        signal_result = generate_signal_with_strategy(
            strategy_code=strategy.code,
            current_price=current_price,
            candles=candles,
            params_json=strategy.params,
            current_position=current_position,
            exchange_client=bitget_client,
            user_id=user_id,
        )

        # 4. 신호에 따른 액션
        if signal_result['action'] == 'buy':
            await open_long_position(...)
        elif signal_result['action'] == 'sell':
            await open_short_position(...)
        elif signal_result['action'] == 'close':
            await close_position(...)

        # 5. 다음 루프까지 대기
        await asyncio.sleep(interval_seconds)
```

---

## 3. 핵심 인터페이스

### 3.1 전략 인터페이스 (필수 구현)

모든 전략은 아래 인터페이스를 구현해야 합니다:

```python
class MyStrategy:
    """전략 인터페이스 규약"""

    def generate_signal(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict] = None
    ) -> Dict:
        """
        메인 신호 생성 메서드 (필수)

        Args:
            current_price: 현재 시장가
            candles: OHLCV 캔들 데이터 리스트
            current_position: 현재 보유 포지션 (없으면 None)

        Returns:
            신호 딕셔너리 (아래 Signal 구조 참조)
        """
        pass

    # === 선택적 메서드 (AI 전략용) ===

    def set_exchange(self, exchange_client) -> None:
        """거래소 클라이언트 주입 (잔고 조회 등에 사용)"""
        self._exchange = exchange_client

    def set_ai_service(self, ai_service) -> None:
        """AI 서비스 주입 (DeepSeek 등)"""
        self._ai_service = ai_service

    async def analyze_and_decide(
        self,
        exchange,
        user_id: int,
        current_positions: List[Dict]
    ) -> "AutonomousDecision":
        """비동기 분석 메서드 (Autonomous 전략용)"""
        pass
```

### 3.2 Signal 반환 구조 (필수)

```python
signal_result = {
    # === 필수 필드 ===
    "action": str,           # "buy" | "sell" | "hold" | "close"
    "confidence": float,     # 0.0 ~ 1.0 (신뢰도)
    "reason": str,           # 신호 생성 이유 (로그/UI 표시용)
    "strategy_type": str,    # 전략 코드 (예: "my_new_strategy")

    # === 선택적 필드 ===
    "stop_loss": float,              # 손절가 (% 또는 절대가)
    "take_profit": float,            # 익절가 (% 또는 절대가)
    "leverage": int,                 # 레버리지 (1-125)
    "position_size_percent": float,  # 포지션 크기 (마진 대비 %)
    "market_regime": str,            # 시장 환경 (AI 분석 결과)
    "ai_powered": bool,              # AI 사용 여부
    "warnings": List[str],           # 경고 메시지 목록
}
```

**Action 값 의미:**

| Action | 설명 | 포지션 변화 |
|--------|------|-------------|
| `"buy"` | 롱 포지션 진입 | 없음 → Long |
| `"sell"` | 숏 포지션 진입 | 없음 → Short |
| `"close"` | 현재 포지션 청산 | Long/Short → 없음 |
| `"hold"` | 아무 행동 안함 | 변화 없음 |

### 3.3 Candle 데이터 구조

```python
candles = [
    {
        "open": 43250.5,        # 시가
        "high": 43300.0,        # 고가
        "low": 43200.0,         # 저가
        "close": 43275.5,       # 종가
        "volume": 1234.56,      # 거래량
        "timestamp": 1703001600000  # Unix timestamp (ms)
    },
    # ... 최대 100개 (최신이 마지막)
]

# 최신 캔들 접근
latest_candle = candles[-1]
current_price = latest_candle['close']
```

---

## 4. 데이터 구조

### 4.1 Position (현재 포지션) 구조

```python
current_position = {
    # === 필수 필드 ===
    "side": str,                # "long" | "short"
    "entry_price": float,       # 진입가
    "size": float,              # 포지션 크기 (기본 화폐 단위)

    # === 계산된 필드 ===
    "pnl": float,               # 미실현 손익 (USDT)
    "pnl_percent": float,       # 미실현 손익 (%)
    "leverage": int,            # 적용 레버리지
    "margin": float,            # 사용 마진 (USDT)
    "liquidation_price": float, # 청산가
    "holding_minutes": int,     # 보유 시간 (분)
}

# 포지션이 없을 경우
current_position = None
```

**중요**: 이 구조는 시스템 전반에서 사용되므로 **절대 변경하면 안 됩니다**.

### 4.2 PositionInfo (AI 전략용 확장 구조)

```python
@dataclass
class PositionInfo:
    """AI 전략에서 사용하는 확장된 포지션 정보"""
    symbol: str
    side: str                      # "long" | "short"
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    leverage: int
    margin_used: float
    liquidation_price: float
    entry_time: datetime
    holding_duration: timedelta
```

### 4.3 UserSeedInfo (마진 관리용)

```python
@dataclass
class UserSeedInfo:
    """사용자 시드 및 마진 정보"""
    user_id: int
    total_balance: float           # 총 시드 (예: 1000 USDT)
    available_for_trading: float   # 거래 가능 금액 (40%면 400 USDT)
    used_margin: float             # 사용 중인 마진
    remaining_margin: float        # 남은 마진
    margin_usage_percent: float    # 마진 사용률 (%)
    can_open_position: bool        # 추가 포지션 가능 여부
    daily_pnl: float               # 일일 손익
    daily_pnl_percent: float       # 일일 손익률 (%)
```

### 4.4 TradingDecision (Autonomous 전략용)

```python
class TradingDecision(Enum):
    """자율 전략의 거래 결정 유형"""
    ENTER_LONG = "enter_long"           # 롱 진입
    ENTER_SHORT = "enter_short"         # 숏 진입
    EXIT_LONG = "exit_long"             # 롱 청산
    EXIT_SHORT = "exit_short"           # 숏 청산
    INCREASE_POSITION = "increase_position"  # 추가 매수
    DECREASE_POSITION = "decrease_position"  # 부분 청산
    HOLD = "hold"                       # 유지
    EMERGENCY_EXIT = "emergency_exit"   # 긴급 청산
```

### 4.5 MarketRegime (시장 환경)

```python
class RegimeType(Enum):
    """시장 환경 유형"""
    TRENDING = "trending"           # 추세장
    RANGING = "ranging"             # 횡보장
    VOLATILE = "volatile"           # 고변동성
    LOW_VOLUME = "low_volume"       # 저유동성
    BREAKOUT = "breakout"           # 돌파 국면
    REVERSAL = "reversal"           # 반전 국면

@dataclass
class MarketRegime:
    """MarketRegimeAgent 출력"""
    regime_type: RegimeType
    confidence: float           # 0.0 ~ 1.0
    volatility: float           # ATR 기반
    volume_ratio: float         # 평균 대비
    ai_enhanced: bool           # AI 분석 여부
```

---

## 5. AI 에이전트 시스템

### 5.1 4개 에이전트 역할

#### 1) Market Regime Agent
```
파일: backend/src/agents/market_regime/agent.py

역할:
  - 현재 시장 환경을 분석하여 추세/횡보/변동성 등을 판단
  - ATR, ADX, 볼린저밴드, 거래량 분석
  - DeepSeek AI를 사용한 심층 분석 (옵션)

출력:
  MarketRegime(
      regime_type=RegimeType.TRENDING,
      confidence=0.85,
      volatility=2.5,
      volume_ratio=1.2,
      ai_enhanced=True
  )

캐싱:
  - 45초 TTL (동일 심볼의 결과 재사용)
  - 모든 사용자가 동일한 결과 공유 (비용 절감)
```

#### 2) Signal Validator Agent
```
파일: backend/src/agents/signal_validator/agent.py

역할:
  - 전략 신호를 실행 전에 검증
  - 10가지 규칙으로 필터링

검증 규칙:
  1. 신뢰도 검사 (< 0.6 → 거부)
  2. 시장 환경 적합성 (volatile/low_volume → 거부)
  3. 급격한 가격 변동 (5분간 2% → 거부)
  4. 포지션 반전 안전성
  5. 연속 신호 필터 (너무 빈번한 거래 방지)
  6. 잔고 한도 검사
  7. 변동성 임계값
  8. 지지/저항 근접 여부
  9. 추세 강도
  10. 거래 빈도

출력:
  SignalValidation(
      is_approved=True,
      confidence_score=0.78,
      position_size_adjustment=0.8,  # 20% 크기 축소 권장
      warning="High volatility detected",
      reason="All checks passed"
  )
```

#### 3) Risk Monitor Agent
```
파일: backend/src/agents/risk_monitor/agent.py

역할:
  - 실시간 포지션 위험도 모니터링
  - 청산가 경고 (10% 이내 접근 시)
  - 일일 손실 한도 추적 (5%)
  - 최대 드로다운 모니터링

위험 수준:
  RiskLevel.SAFE      → 정상
  RiskLevel.WARNING   → 주의 (임계값 근접)
  RiskLevel.CRITICAL  → 긴급 (즉시 조치 필요)

출력:
  RiskAssessment(
      level=RiskLevel.WARNING,
      reason="Approaching liquidation price",
      recommended_action="Reduce position size",
      distance_to_liquidation=12.5  # %
  )
```

#### 4) Portfolio Optimizer Agent
```
파일: backend/src/agents/portfolio_optimizer/agent.py

역할:
  - 다중 봇 포트폴리오 분석
  - 마코위츠 이론 기반 최적화
  - 포지션 크기 권장
  - 리밸런싱 트리거

출력:
  PortfolioRecommendation(
      optimal_position_size=0.15,   # 총 자본의 15%
      recommended_leverage=10,
      rebalance_needed=False,
      diversification_score=0.72
  )
```

### 5.2 AI 에이전트 초기화 예시

```python
# eth_ai_autonomous_40pct_strategy.py

def _init_agents(self):
    """4개 AI 에이전트 초기화"""

    # 1. Market Regime Agent
    self.market_regime_agent = MarketRegimeAgent(
        agent_id="eth_market_regime",
        name="ETH Market Analyzer",
        config={
            "symbol": "ETHUSDT",
            "timeframe": "1h",
            "enable_ai": True,      # DeepSeek 사용
            "cache_ttl": 45         # 캐시 유지 시간
        }
    )

    # 2. Signal Validator Agent
    self.signal_validator = SignalValidatorAgent(
        agent_id="eth_signal_validator",
        name="ETH Signal Validator",
        config={
            "enable_ai": True,
            "min_confidence": 0.6,
            "max_daily_trades": 10
        }
    )

    # 3. Risk Monitor Agent
    self.risk_monitor = RiskMonitorAgent(
        agent_id="eth_risk_monitor",
        name="ETH Risk Monitor",
        config={
            "max_position_loss_percent": 5.0,    # 포지션당 최대 손실
            "max_daily_loss_percent": 5.0,       # 일일 최대 손실
            "liquidation_warning_percent": 10.0  # 청산가 경고 거리
        }
    )

    # 4. Portfolio Optimizer Agent
    self.portfolio_optimizer = PortfolioOptimizationAgent(
        agent_id="eth_portfolio_optimizer",
        name="ETH Portfolio Optimizer",
        config={
            "min_allocation_percent": 5.0,    # 최소 배분
            "max_allocation_percent": 40.0,   # 최대 배분 (40% 제한)
            "rebalancing_threshold": 5.0      # 리밸런싱 트리거
        }
    )
```

### 5.3 AI 비용 최적화

```
AI Provider: DeepSeek (deepseek-chat)
비용: ~$0.0002/호출 (~400 토큰)

최적화 전략:
1. 프롬프트 캐싱 (45초 TTL)
2. 사용자간 캐시 공유 (동일 심볼)
3. Smart Sampling (매 호출마다 AI 사용 X)
4. 배치 처리 (여러 심볼 한번에)

예상 비용:
- 시간당 ~80회 호출 (분당 1.3회)
- 일일 비용: ~$0.04
- 월간 비용: ~$1.20
```

---

## 6. 마진 관리 시스템

### 6.1 마진 제한 구조

```python
# ⚠️ 절대 변경 금지 - MarginCapEnforcer40Pct

class MarginCapEnforcer40Pct:
    """40% 마진 제한 강제 적용"""

    # 하드코딩된 제한값
    MAX_MARGIN_PERCENT = 40.0       # 최대 마진 사용률
    SAFETY_BUFFER_PERCENT = 2.0     # 안전 버퍼 (실제 38%)
    MIN_FREE_MARGIN_PERCENT = 3.0   # 최소 유지 마진
    DAILY_LOSS_LIMIT_PERCENT = 5.0  # 일일 손실 제한
```

### 6.2 마진 계산 예시

```
사용자 시드: 1,000 USDT
최대 거래 가능: 400 USDT (40%)
안전 버퍼 적용: 380 USDT (38%)

레버리지 10x 사용 시:
  - 최대 포지션 크기: 3,800 USDT

레버리지 15x 사용 시:
  - 최대 포지션 크기: 5,700 USDT
```

### 6.3 마진 검증 흐름

```python
def validate_order(self, order_size: float, leverage: int) -> bool:
    """주문 전 마진 검증"""

    # 1. 사용자 잔고 조회
    seed_info = await self.get_user_seed_info()

    # 2. 필요 마진 계산
    required_margin = order_size / leverage

    # 3. 제한 확인
    if required_margin > seed_info.remaining_margin:
        return False  # 마진 초과

    if seed_info.margin_usage_percent + (required_margin / seed_info.available_for_trading * 100) > 40.0:
        return False  # 40% 초과

    return True
```

---

## 7. 전략 유형별 템플릿

### 7.1 Basic Strategy (규칙 기반)

```python
# backend/src/strategies/my_basic_strategy.py

"""
Basic Strategy Template
- AI 에이전트 미사용
- 기술적 지표만으로 신호 생성
- 빠른 실행, 낮은 비용
"""

import numpy as np
from typing import List, Dict, Optional


def calculate_ema(prices: List[float], period: int) -> float:
    """지수이동평균 계산"""
    if len(prices) < period:
        return prices[-1]

    multiplier = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """RSI 계산"""
    if len(prices) < period + 1:
        return 50.0

    deltas = np.diff(prices[-period-1:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def generate_signal(
    current_price: float,
    candles: List[Dict],
    params: Dict = None,
    current_position: Optional[Dict] = None
) -> Dict:
    """
    Basic Strategy Signal Generator

    Args:
        current_price: 현재 가격
        candles: 캔들 데이터 [{open, high, low, close, volume}, ...]
        params: 전략 파라미터 (JSON에서 파싱됨)
        current_position: 현재 포지션 정보

    Returns:
        신호 딕셔너리
    """

    # 기본 응답 (데이터 부족 시)
    default_signal = {
        "action": "hold",
        "confidence": 0.0,
        "reason": "Insufficient data",
        "stop_loss": None,
        "take_profit": None,
        "strategy_type": "my_basic_strategy",
        "ai_powered": False,
    }

    # 최소 데이터 확인
    if not candles or len(candles) < 50:
        return default_signal

    # 파라미터 추출 (기본값 포함)
    params = params or {}
    ema_fast = params.get("ema_fast", 9)
    ema_slow = params.get("ema_slow", 21)
    rsi_period = params.get("rsi_period", 14)
    rsi_oversold = params.get("rsi_oversold", 30)
    rsi_overbought = params.get("rsi_overbought", 70)
    stop_loss_pct = params.get("stop_loss_percent", 2.0)
    take_profit_pct = params.get("take_profit_percent", 4.0)
    leverage = params.get("leverage", 5)

    # 가격 데이터 추출
    closes = [c['close'] for c in candles]

    # 지표 계산
    ema_fast_val = calculate_ema(closes, ema_fast)
    ema_slow_val = calculate_ema(closes, ema_slow)
    rsi = calculate_rsi(closes, rsi_period)

    # --- 포지션 청산 로직 (기존 포지션이 있을 때) ---
    if current_position:
        side = current_position.get('side')
        entry_price = current_position.get('entry_price', current_price)
        pnl_percent = current_position.get('pnl_percent', 0)

        # 익절 확인
        if pnl_percent >= take_profit_pct:
            return {
                "action": "close",
                "confidence": 0.9,
                "reason": f"Take Profit: {pnl_percent:.2f}% >= {take_profit_pct}%",
                "stop_loss": None,
                "take_profit": None,
                "strategy_type": "my_basic_strategy",
                "ai_powered": False,
            }

        # 손절 확인
        if pnl_percent <= -stop_loss_pct:
            return {
                "action": "close",
                "confidence": 0.95,
                "reason": f"Stop Loss: {pnl_percent:.2f}% <= -{stop_loss_pct}%",
                "stop_loss": None,
                "take_profit": None,
                "strategy_type": "my_basic_strategy",
                "ai_powered": False,
            }

        # 반전 신호 확인
        if side == 'long' and ema_fast_val < ema_slow_val and rsi > rsi_overbought:
            return {
                "action": "close",
                "confidence": 0.75,
                "reason": "Bearish crossover with overbought RSI",
                "stop_loss": None,
                "take_profit": None,
                "strategy_type": "my_basic_strategy",
                "ai_powered": False,
            }

        if side == 'short' and ema_fast_val > ema_slow_val and rsi < rsi_oversold:
            return {
                "action": "close",
                "confidence": 0.75,
                "reason": "Bullish crossover with oversold RSI",
                "stop_loss": None,
                "take_profit": None,
                "strategy_type": "my_basic_strategy",
                "ai_powered": False,
            }

    # --- 신규 진입 로직 (포지션 없을 때) ---
    if not current_position:
        # 롱 신호: 빠른 EMA가 느린 EMA 위 + RSI 과매도에서 회복
        if ema_fast_val > ema_slow_val and rsi < 50 and rsi > rsi_oversold:
            return {
                "action": "buy",
                "confidence": 0.7,
                "reason": f"Bullish EMA crossover (RSI: {rsi:.1f})",
                "stop_loss": stop_loss_pct,
                "take_profit": take_profit_pct,
                "leverage": leverage,
                "position_size_percent": 10.0,
                "strategy_type": "my_basic_strategy",
                "ai_powered": False,
            }

        # 숏 신호: 빠른 EMA가 느린 EMA 아래 + RSI 과매수에서 하락
        if ema_fast_val < ema_slow_val and rsi > 50 and rsi < rsi_overbought:
            return {
                "action": "sell",
                "confidence": 0.7,
                "reason": f"Bearish EMA crossover (RSI: {rsi:.1f})",
                "stop_loss": stop_loss_pct,
                "take_profit": take_profit_pct,
                "leverage": leverage,
                "position_size_percent": 10.0,
                "strategy_type": "my_basic_strategy",
                "ai_powered": False,
            }

    # 신호 없음
    return {
        "action": "hold",
        "confidence": 0.5,
        "reason": f"No signal (EMA fast: {ema_fast_val:.2f}, slow: {ema_slow_val:.2f}, RSI: {rsi:.1f})",
        "stop_loss": None,
        "take_profit": None,
        "strategy_type": "my_basic_strategy",
        "ai_powered": False,
    }
```

### 7.2 AI-Enhanced Strategy

```python
# backend/src/strategies/my_ai_strategy.py

"""
AI-Enhanced Strategy Template
- MarketRegimeAgent 통합
- SignalValidatorAgent로 검증
- 비용 최적화 (캐싱 활용)
"""

import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass

from src.agents.market_regime.agent import MarketRegimeAgent
from src.agents.signal_validator.agent import SignalValidatorAgent
from src.services.deepseek_service import DeepSeekService


@dataclass
class StrategyConfig:
    """전략 설정"""
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    enable_ai: bool = True
    min_confidence: float = 0.6
    stop_loss_percent: float = 2.0
    take_profit_percent: float = 4.0
    leverage: int = 10


class MyAIStrategy:
    """AI 강화 전략"""

    def __init__(self, params: Dict = None, user_id: int = None):
        self.params = params or {}
        self.user_id = user_id
        self.config = StrategyConfig(**self.params)

        self._exchange = None
        self._ai_service = None

        # AI 에이전트 초기화
        self._init_agents()

    def _init_agents(self):
        """AI 에이전트 초기화"""
        self.market_regime_agent = MarketRegimeAgent(
            agent_id=f"my_ai_market_regime_{self.user_id}",
            name="My AI Market Analyzer",
            config={
                "symbol": self.config.symbol,
                "timeframe": self.config.timeframe,
                "enable_ai": self.config.enable_ai
            }
        )

        self.signal_validator = SignalValidatorAgent(
            agent_id=f"my_ai_signal_validator_{self.user_id}",
            name="My AI Signal Validator",
            config={
                "enable_ai": self.config.enable_ai,
                "min_confidence": self.config.min_confidence
            }
        )

    def set_exchange(self, exchange_client):
        """거래소 클라이언트 설정"""
        self._exchange = exchange_client

    def set_ai_service(self, ai_service):
        """AI 서비스 설정"""
        self._ai_service = ai_service

    async def _analyze_market(self, candles: List[Dict]) -> Dict:
        """시장 환경 분석"""
        try:
            regime = await self.market_regime_agent.get_market_regime(
                candles=candles,
                symbol=self.config.symbol
            )
            return {
                "regime_type": regime.regime_type.value,
                "confidence": regime.confidence,
                "volatility": regime.volatility,
                "ai_enhanced": regime.ai_enhanced
            }
        except Exception as e:
            return {
                "regime_type": "unknown",
                "confidence": 0.5,
                "volatility": 0.0,
                "ai_enhanced": False,
                "error": str(e)
            }

    async def _generate_base_signal(
        self,
        current_price: float,
        candles: List[Dict],
        market_analysis: Dict
    ) -> Dict:
        """기본 신호 생성 (여기에 핵심 로직 구현)"""

        # 시장 환경에 따른 필터링
        regime = market_analysis.get("regime_type", "unknown")

        # 고변동성/저유동성 시장에서는 거래 안함
        if regime in ["volatile", "low_volume"]:
            return {
                "action": "hold",
                "confidence": 0.3,
                "reason": f"Unfavorable market regime: {regime}",
            }

        # TODO: 여기에 실제 신호 생성 로직 구현
        # 예: 기술적 지표, 패턴 인식 등

        closes = [c['close'] for c in candles]

        # 간단한 예시: 20일 이동평균 대비 위치
        if len(closes) >= 20:
            ma20 = sum(closes[-20:]) / 20

            if current_price > ma20 * 1.02:  # MA 2% 위
                return {
                    "action": "buy",
                    "confidence": 0.65,
                    "reason": f"Price above MA20 ({current_price:.2f} > {ma20:.2f})",
                }
            elif current_price < ma20 * 0.98:  # MA 2% 아래
                return {
                    "action": "sell",
                    "confidence": 0.65,
                    "reason": f"Price below MA20 ({current_price:.2f} < {ma20:.2f})",
                }

        return {
            "action": "hold",
            "confidence": 0.5,
            "reason": "No clear signal",
        }

    async def _validate_signal(
        self,
        signal: Dict,
        current_price: float,
        candles: List[Dict]
    ) -> Dict:
        """신호 검증"""
        try:
            validation = await self.signal_validator.validate_signal(
                signal=signal,
                current_price=current_price,
                candles=candles
            )

            if not validation.is_approved:
                return {
                    "action": "hold",
                    "confidence": signal.get("confidence", 0) * 0.5,
                    "reason": f"Signal rejected: {validation.reason}",
                    "original_action": signal.get("action"),
                    "validation_warning": validation.warning
                }

            # 검증 통과 - 포지션 크기 조정 적용
            adjusted_signal = signal.copy()
            adjusted_signal["position_size_adjustment"] = validation.position_size_adjustment

            return adjusted_signal

        except Exception as e:
            # 검증 실패 시 원본 신호 반환 (보수적)
            return signal

    async def analyze_and_decide(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict] = None
    ) -> Dict:
        """비동기 분석 및 결정"""

        # 1. 시장 환경 분석
        market_analysis = await self._analyze_market(candles)

        # 2. 기본 신호 생성
        base_signal = await self._generate_base_signal(
            current_price, candles, market_analysis
        )

        # 3. 신호 검증
        validated_signal = await self._validate_signal(
            base_signal, current_price, candles
        )

        # 4. 최종 신호 구성
        return {
            "action": validated_signal.get("action", "hold"),
            "confidence": validated_signal.get("confidence", 0.5),
            "reason": validated_signal.get("reason", ""),
            "stop_loss": self.config.stop_loss_percent,
            "take_profit": self.config.take_profit_percent,
            "leverage": self.config.leverage,
            "position_size_percent": 10.0 * validated_signal.get("position_size_adjustment", 1.0),
            "market_regime": market_analysis.get("regime_type"),
            "ai_powered": True,
            "strategy_type": "my_ai_strategy",
        }

    def generate_signal(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict] = None
    ) -> Dict:
        """동기 래퍼 (bot_runner 호환용)"""

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 이미 비동기 컨텍스트인 경우
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.analyze_and_decide(
                            current_price, candles, current_position
                        )
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self.analyze_and_decide(
                        current_price, candles, current_position
                    )
                )
        except Exception as e:
            return {
                "action": "hold",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}",
                "ai_powered": True,
                "strategy_type": "my_ai_strategy"
            }
```

### 7.3 Autonomous Strategy (자율 거래)

```python
# backend/src/strategies/my_autonomous_strategy.py

"""
Autonomous Strategy Template
- 4개 AI 에이전트 완전 통합
- 마진 제한 강제 적용
- 자동 익절/손절
- 위험 관리 자동화
"""

import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from src.agents.market_regime.agent import MarketRegimeAgent
from src.agents.signal_validator.agent import SignalValidatorAgent
from src.agents.risk_monitor.agent import RiskMonitorAgent
from src.agents.portfolio_optimizer.agent import PortfolioOptimizationAgent


class TradingDecision(Enum):
    ENTER_LONG = "enter_long"
    ENTER_SHORT = "enter_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    HOLD = "hold"
    EMERGENCY_EXIT = "emergency_exit"


@dataclass
class AutonomousDecision:
    """자율 전략 결정 결과"""
    decision: TradingDecision
    confidence: float
    reasoning: str
    stop_loss_percent: float
    take_profit_percent: float
    position_size_percent: float
    target_leverage: int
    market_regime: str
    risk_level: str


class MarginCapEnforcer:
    """마진 제한 강제 (30% 버전)"""

    MAX_MARGIN_PERCENT = 30.0
    SAFETY_BUFFER = 2.0
    DAILY_LOSS_LIMIT = 5.0

    def __init__(self, exchange_client):
        self._exchange = exchange_client

    async def get_available_margin(self, user_id: int) -> float:
        """사용 가능한 마진 계산"""
        balance = await self._exchange.fetch_balance()
        total = balance.get('USDT', {}).get('total', 0)
        return total * (self.MAX_MARGIN_PERCENT - self.SAFETY_BUFFER) / 100

    async def validate_position_size(
        self,
        size: float,
        leverage: int
    ) -> bool:
        """포지션 크기 검증"""
        required_margin = size / leverage
        available = await self.get_available_margin(0)
        return required_margin <= available


class MyAutonomousStrategy:
    """완전 자율 거래 전략"""

    def __init__(self, params: Dict = None, user_id: int = None):
        self.params = params or {}
        self.user_id = user_id
        self.symbol = self.params.get("symbol", "BTCUSDT")

        self._exchange = None
        self._margin_enforcer = None

        # 4개 에이전트 초기화
        self._init_all_agents()

    def _init_all_agents(self):
        """4개 AI 에이전트 모두 초기화"""

        # 1. Market Regime Agent
        self.market_regime_agent = MarketRegimeAgent(
            agent_id=f"autonomous_market_{self.user_id}",
            name="Autonomous Market Analyzer",
            config={
                "symbol": self.symbol,
                "timeframe": "1h",
                "enable_ai": True
            }
        )

        # 2. Signal Validator Agent
        self.signal_validator = SignalValidatorAgent(
            agent_id=f"autonomous_validator_{self.user_id}",
            name="Autonomous Signal Validator",
            config={
                "enable_ai": True,
                "min_confidence": 0.65
            }
        )

        # 3. Risk Monitor Agent
        self.risk_monitor = RiskMonitorAgent(
            agent_id=f"autonomous_risk_{self.user_id}",
            name="Autonomous Risk Monitor",
            config={
                "max_position_loss_percent": 3.0,
                "max_daily_loss_percent": 5.0,
                "liquidation_warning_percent": 15.0
            }
        )

        # 4. Portfolio Optimizer Agent
        self.portfolio_optimizer = PortfolioOptimizationAgent(
            agent_id=f"autonomous_portfolio_{self.user_id}",
            name="Autonomous Portfolio Optimizer",
            config={
                "min_allocation_percent": 5.0,
                "max_allocation_percent": 30.0,  # 30% 제한
                "rebalancing_threshold": 5.0
            }
        )

    def set_exchange(self, exchange_client):
        """거래소 클라이언트 설정"""
        self._exchange = exchange_client
        self._margin_enforcer = MarginCapEnforcer(exchange_client)

    async def _check_exit_conditions(
        self,
        position: Dict,
        current_price: float
    ) -> Optional[AutonomousDecision]:
        """포지션 청산 조건 확인"""

        if not position:
            return None

        side = position.get('side')
        entry_price = position.get('entry_price', current_price)
        pnl_percent = position.get('pnl_percent', 0)
        holding_minutes = position.get('holding_minutes', 0)

        # 동적 SL/TP (ATR 기반 계산 예시)
        # 실제로는 ATR을 계산하여 적용
        stop_loss = 2.0   # 기본 2%
        take_profit = 4.0  # 기본 4%

        # 익절 확인
        if pnl_percent >= take_profit:
            return AutonomousDecision(
                decision=TradingDecision.EXIT_LONG if side == 'long' else TradingDecision.EXIT_SHORT,
                confidence=0.95,
                reasoning=f"Take Profit triggered: {pnl_percent:.2f}% >= {take_profit}%",
                stop_loss_percent=0,
                take_profit_percent=0,
                position_size_percent=0,
                target_leverage=0,
                market_regime="exit",
                risk_level="safe"
            )

        # 손절 확인
        if pnl_percent <= -stop_loss:
            return AutonomousDecision(
                decision=TradingDecision.EXIT_LONG if side == 'long' else TradingDecision.EXIT_SHORT,
                confidence=0.98,
                reasoning=f"Stop Loss triggered: {pnl_percent:.2f}% <= -{stop_loss}%",
                stop_loss_percent=0,
                take_profit_percent=0,
                position_size_percent=0,
                target_leverage=0,
                market_regime="exit",
                risk_level="critical"
            )

        # 최대 보유 시간 초과 (예: 24시간)
        max_holding = self.params.get("max_holding_hours", 24) * 60
        if holding_minutes > max_holding:
            return AutonomousDecision(
                decision=TradingDecision.EXIT_LONG if side == 'long' else TradingDecision.EXIT_SHORT,
                confidence=0.80,
                reasoning=f"Max holding time exceeded: {holding_minutes}min > {max_holding}min",
                stop_loss_percent=0,
                take_profit_percent=0,
                position_size_percent=0,
                target_leverage=0,
                market_regime="timeout",
                risk_level="warning"
            )

        return None

    async def _check_risk_status(
        self,
        position: Optional[Dict],
        current_price: float
    ) -> Dict:
        """리스크 상태 확인"""
        try:
            risk_assessment = await self.risk_monitor.check_position_risk(
                position=position,
                current_price=current_price
            )
            return {
                "level": risk_assessment.level.value,
                "reason": risk_assessment.reason,
                "action_needed": risk_assessment.level.value == "critical"
            }
        except Exception:
            return {
                "level": "unknown",
                "reason": "Risk check failed",
                "action_needed": False
            }

    async def analyze_and_decide(
        self,
        exchange,
        user_id: int,
        current_positions: List[Dict]
    ) -> AutonomousDecision:
        """메인 분석 및 결정 로직"""

        # 현재 가격 및 캔들 조회
        candles = await exchange.fetch_candles(self.symbol, "1h", 100)
        current_price = candles[-1]['close']

        # 현재 포지션
        position = current_positions[0] if current_positions else None

        # 1. 포지션 청산 조건 확인 (최우선)
        exit_decision = await self._check_exit_conditions(position, current_price)
        if exit_decision:
            return exit_decision

        # 2. 리스크 상태 확인
        risk_status = await self._check_risk_status(position, current_price)
        if risk_status.get("action_needed"):
            return AutonomousDecision(
                decision=TradingDecision.EMERGENCY_EXIT,
                confidence=0.99,
                reasoning=f"Emergency exit: {risk_status.get('reason')}",
                stop_loss_percent=0,
                take_profit_percent=0,
                position_size_percent=0,
                target_leverage=0,
                market_regime="emergency",
                risk_level="critical"
            )

        # 3. 시장 환경 분석
        market_regime = await self.market_regime_agent.get_market_regime(
            candles=candles,
            symbol=self.symbol
        )

        # 4. 불리한 시장 환경에서는 진입 안함
        if market_regime.regime_type.value in ["volatile", "low_volume"]:
            return AutonomousDecision(
                decision=TradingDecision.HOLD,
                confidence=0.6,
                reasoning=f"Unfavorable market: {market_regime.regime_type.value}",
                stop_loss_percent=2.0,
                take_profit_percent=4.0,
                position_size_percent=0,
                target_leverage=0,
                market_regime=market_regime.regime_type.value,
                risk_level=risk_status.get("level", "safe")
            )

        # 5. 이미 포지션이 있으면 유지
        if position:
            return AutonomousDecision(
                decision=TradingDecision.HOLD,
                confidence=0.7,
                reasoning="Maintaining current position",
                stop_loss_percent=2.0,
                take_profit_percent=4.0,
                position_size_percent=0,
                target_leverage=position.get('leverage', 10),
                market_regime=market_regime.regime_type.value,
                risk_level=risk_status.get("level", "safe")
            )

        # 6. 새로운 진입 기회 분석
        # TODO: 여기에 실제 진입 로직 구현
        closes = [c['close'] for c in candles]
        ma20 = sum(closes[-20:]) / 20

        # 포트폴리오 최적화로 크기 결정
        position_size = 10.0  # 기본 10%
        leverage = 10

        try:
            optimization = await self.portfolio_optimizer.suggest_sizing(
                available_margin=await self._margin_enforcer.get_available_margin(user_id),
                current_positions=current_positions
            )
            position_size = optimization.optimal_position_size * 100
            leverage = optimization.recommended_leverage
        except Exception:
            pass

        # 진입 신호 생성
        if current_price > ma20 * 1.01:  # 1% 위
            return AutonomousDecision(
                decision=TradingDecision.ENTER_LONG,
                confidence=0.65,
                reasoning=f"Bullish setup: price {current_price:.2f} > MA20 {ma20:.2f}",
                stop_loss_percent=2.0,
                take_profit_percent=4.0,
                position_size_percent=position_size,
                target_leverage=leverage,
                market_regime=market_regime.regime_type.value,
                risk_level=risk_status.get("level", "safe")
            )
        elif current_price < ma20 * 0.99:  # 1% 아래
            return AutonomousDecision(
                decision=TradingDecision.ENTER_SHORT,
                confidence=0.65,
                reasoning=f"Bearish setup: price {current_price:.2f} < MA20 {ma20:.2f}",
                stop_loss_percent=2.0,
                take_profit_percent=4.0,
                position_size_percent=position_size,
                target_leverage=leverage,
                market_regime=market_regime.regime_type.value,
                risk_level=risk_status.get("level", "safe")
            )

        # 기본: 대기
        return AutonomousDecision(
            decision=TradingDecision.HOLD,
            confidence=0.5,
            reasoning="No clear entry opportunity",
            stop_loss_percent=2.0,
            take_profit_percent=4.0,
            position_size_percent=0,
            target_leverage=10,
            market_regime=market_regime.regime_type.value,
            risk_level=risk_status.get("level", "safe")
        )

    def generate_signal(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict] = None
    ) -> Dict:
        """동기 래퍼 (bot_runner 호환)"""

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.analyze_and_decide(
                            self._exchange,
                            self.user_id,
                            [current_position] if current_position else []
                        )
                    )
                    decision = future.result(timeout=30)
            else:
                decision = loop.run_until_complete(
                    self.analyze_and_decide(
                        self._exchange,
                        self.user_id,
                        [current_position] if current_position else []
                    )
                )
        except Exception as e:
            return {
                "action": "hold",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}",
                "ai_powered": True,
                "strategy_type": "my_autonomous_strategy"
            }

        # Decision을 Signal 형식으로 변환
        action_map = {
            TradingDecision.ENTER_LONG: "buy",
            TradingDecision.ENTER_SHORT: "sell",
            TradingDecision.EXIT_LONG: "close",
            TradingDecision.EXIT_SHORT: "close",
            TradingDecision.EMERGENCY_EXIT: "close",
            TradingDecision.HOLD: "hold",
        }

        return {
            "action": action_map.get(decision.decision, "hold"),
            "confidence": decision.confidence,
            "reason": decision.reasoning,
            "stop_loss": decision.stop_loss_percent,
            "take_profit": decision.take_profit_percent,
            "leverage": decision.target_leverage,
            "position_size_percent": decision.position_size_percent,
            "market_regime": decision.market_regime,
            "risk_level": decision.risk_level,
            "ai_powered": True,
            "strategy_type": "my_autonomous_strategy",
        }
```

---

## 8. 전략 등록 및 배포

### 8.1 Strategy Loader에 등록

```python
# backend/src/services/strategy_loader.py

def _create_strategy_instance_internal(
    strategy_code: str,
    params: Dict,
    user_id: int
):
    """전략 인스턴스 생성"""

    # ... 기존 전략들 ...

    elif strategy_code == "my_basic_strategy":
        logger.info(f"Loading My Basic Strategy for user {user_id}")
        from ..strategies.my_basic_strategy import generate_signal
        return SimpleStrategyWrapper(generate_signal, params)

    elif strategy_code == "my_ai_strategy":
        logger.info(f"Loading My AI Strategy for user {user_id}")
        from ..strategies.my_ai_strategy import MyAIStrategy
        return MyAIStrategy(params, user_id=user_id)

    elif strategy_code == "my_autonomous_strategy":
        logger.info(f"Loading My Autonomous Strategy for user {user_id}")
        from ..strategies.my_autonomous_strategy import MyAutonomousStrategy
        return MyAutonomousStrategy(params, user_id=user_id)

    else:
        raise ValueError(f"Unknown strategy code: {strategy_code}")
```

### 8.2 전략 코드 목록에 추가

```python
# backend/src/strategies/__init__.py

STRATEGY_CODES = [
    # 기존 전략들
    "proven_conservative",
    "proven_balanced",
    "proven_aggressive",
    "deepseek_ai",
    "ai_role_division",
    "autonomous_30pct",
    "adaptive_market_regime_fighter",
    "eth_autonomous_40pct",

    # 새 전략 추가
    "my_basic_strategy",
    "my_ai_strategy",
    "my_autonomous_strategy",
]
```

### 8.3 데이터베이스에 등록

```sql
-- strategies 테이블에 새 전략 추가
INSERT INTO strategies (name, code, type, params, is_active, user_id)
VALUES (
    'My Custom Strategy',
    'my_basic_strategy',
    'basic',
    '{"ema_fast": 9, "ema_slow": 21, "stop_loss_percent": 2.0}',
    true,
    1  -- admin user
);
```

### 8.4 배포 명령어

```bash
# 1. 문법 검증
python3 -m py_compile backend/src/strategies/my_basic_strategy.py

# 2. 서버 동기화
rsync -avz backend/src/strategies/ root@158.247.245.197:/root/auto-dashboard/backend/src/strategies/ \
  -e "sshpass -p 'Vc8,xn7j_fjdnNGy' ssh -o StrictHostKeyChecking=no"

# 3. 컨테이너 재시작
sshpass -p 'Vc8,xn7j_fjdnNGy' ssh -o StrictHostKeyChecking=no root@158.247.245.197 \
  "cd /root/auto-dashboard && docker compose restart backend"

# 4. 로그 확인
sshpass -p 'Vc8,xn7j_fjdnNGy' ssh -o StrictHostKeyChecking=no root@158.247.245.197 \
  "docker logs trading-backend --tail 50"
```

---

## 9. 테스트 가이드

### 9.1 단위 테스트

```python
# backend/tests/strategies/test_my_strategy.py

import pytest
from src.strategies.my_basic_strategy import generate_signal


class TestMyBasicStrategy:
    """기본 전략 단위 테스트"""

    @pytest.fixture
    def sample_candles(self):
        """테스트용 캔들 데이터"""
        return [
            {"open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000}
            for _ in range(100)
        ]

    def test_insufficient_data(self):
        """데이터 부족 시 hold 반환"""
        signal = generate_signal(100, [], {}, None)
        assert signal["action"] == "hold"
        assert signal["confidence"] == 0.0

    def test_buy_signal(self, sample_candles):
        """매수 신호 테스트"""
        # 상승 추세 캔들 구성
        for i in range(50, 100):
            sample_candles[i]["close"] = 100 + i * 0.1

        signal = generate_signal(105, sample_candles, {}, None)
        assert signal["action"] in ["buy", "hold"]

    def test_stop_loss(self, sample_candles):
        """손절 테스트"""
        position = {
            "side": "long",
            "entry_price": 100,
            "pnl_percent": -3.0  # -3% 손실
        }
        params = {"stop_loss_percent": 2.0}

        signal = generate_signal(97, sample_candles, params, position)
        assert signal["action"] == "close"
        assert "Stop Loss" in signal["reason"]

    def test_take_profit(self, sample_candles):
        """익절 테스트"""
        position = {
            "side": "long",
            "entry_price": 100,
            "pnl_percent": 5.0  # +5% 수익
        }
        params = {"take_profit_percent": 4.0}

        signal = generate_signal(105, sample_candles, params, position)
        assert signal["action"] == "close"
        assert "Take Profit" in signal["reason"]
```

### 9.2 통합 테스트

```python
# backend/tests/integration/test_strategy_flow.py

import pytest
import asyncio
from src.services.strategy_loader import generate_signal_with_strategy


class TestStrategyIntegration:
    """전략 통합 테스트"""

    @pytest.mark.asyncio
    async def test_signal_generation_flow(self):
        """신호 생성 전체 흐름 테스트"""

        # Mock 데이터
        candles = [
            {"open": 43000, "high": 43100, "low": 42900, "close": 43050, "volume": 100}
            for _ in range(100)
        ]

        signal = generate_signal_with_strategy(
            strategy_code="my_basic_strategy",
            current_price=43050,
            candles=candles,
            params_json='{"leverage": 5}',
            current_position=None,
            exchange_client=None,
            user_id=1
        )

        assert "action" in signal
        assert "confidence" in signal
        assert "strategy_type" in signal
        assert signal["strategy_type"] == "my_basic_strategy"
```

### 9.3 백테스트 실행

```bash
# 로컬 백테스트
cd backend
python -m scripts.backtest_strategy \
  --strategy my_basic_strategy \
  --symbol BTCUSDT \
  --start 2024-01-01 \
  --end 2024-12-01 \
  --initial_capital 1000
```

---

## 10. 모범 사례 및 주의사항

### 10.1 절대 변경 금지 항목

| 항목 | 위치 | 이유 |
|------|------|------|
| `MAX_MARGIN_PERCENT = 40.0` | eth_ai_autonomous_40pct_strategy.py | 리스크 관리 |
| `current_position` 구조 | 전체 시스템 | 20개+ 파일에서 사용 |
| `_check_exit_conditions()` | 자율 전략들 | 익절/손절 핵심 로직 |
| 포지션 동기화 (bot_runner.py:627-670) | bot_runner.py | 기존 포지션 인식 |
| Signal 반환 구조 | 모든 전략 | bot_runner 호환성 |

### 10.2 권장 사항

```
✅ DO:
- 새 전략 파일은 별도로 생성
- 기존 인터페이스 준수
- 충분한 테스트 후 배포
- 로그 메시지 추가로 디버깅 용이하게
- 에러 핸들링 철저히

❌ DON'T:
- 기존 전략 파일 직접 수정 (복사 후 수정)
- 마진 제한 값 변경
- current_position 구조 변경
- 테스트 없이 프로덕션 배포
- 동기화 없이 docker compose build
```

### 10.3 디버깅 팁

```python
# 로그 추가 예시
import logging
logger = logging.getLogger(__name__)

def generate_signal(...):
    logger.info(f"[MyStrategy] Input: price={current_price}, candles={len(candles)}")

    # ... 로직 ...

    logger.info(f"[MyStrategy] Output: action={signal['action']}, confidence={signal['confidence']}")
    return signal
```

```bash
# 로그 확인
docker logs trading-backend --tail 100 2>&1 | grep "MyStrategy"
```

### 10.4 성능 최적화

```python
# 1. 캐싱 활용
from functools import lru_cache

@lru_cache(maxsize=100)
def calculate_expensive_indicator(candles_tuple):
    # 무거운 계산
    pass

# 2. 불필요한 API 호출 방지
class MyStrategy:
    def __init__(self):
        self._last_analysis = None
        self._last_analysis_time = None

    async def _analyze_market(self, candles):
        now = datetime.now()
        if self._last_analysis and (now - self._last_analysis_time).seconds < 30:
            return self._last_analysis  # 30초 내 재사용

        analysis = await self._do_analysis(candles)
        self._last_analysis = analysis
        self._last_analysis_time = now
        return analysis
```

### 10.5 AI 비용 관리

```python
# AI 호출 전 조건 확인
async def _should_use_ai(self, candles) -> bool:
    """AI 분석이 필요한지 판단"""

    # 변동성이 낮으면 AI 불필요
    volatility = self._calculate_volatility(candles)
    if volatility < 0.5:
        return False

    # 명확한 추세면 AI 불필요
    trend = self._detect_trend(candles)
    if trend.strength > 0.8:
        return False

    return True
```

---

## 부록: 자주 묻는 질문 (FAQ)

### Q1: 전략이 로드되지 않습니다
```
확인사항:
1. strategy_loader.py에 등록되었는지
2. __init__.py의 STRATEGY_CODES에 추가되었는지
3. 문법 오류 없는지 (python -m py_compile)
4. import 경로가 올바른지
```

### Q2: 신호가 생성되지 않습니다
```
확인사항:
1. 캔들 데이터가 충분한지 (최소 50개)
2. current_position 형식이 올바른지
3. 반환 딕셔너리에 필수 필드 있는지
4. 로그에서 에러 확인
```

### Q3: AI 에이전트가 작동하지 않습니다
```
확인사항:
1. DEEPSEEK_API_KEY 환경변수 설정
2. set_exchange() 호출되었는지
3. 비동기 함수가 올바르게 호출되는지
4. 에러 핸들링 확인
```

### Q4: 익절/손절이 작동하지 않습니다
```
확인사항:
1. current_position에 pnl_percent가 있는지
2. _check_exit_conditions() 로직 확인
3. 포지션 동기화가 되고 있는지
4. bot_runner 로그에서 signal 확인
```

---

**문서 버전**: 1.0.0
**최종 수정**: 2025-12-24
**작성자**: Claude AI (Auto Trading Dashboard 분석 기반)

---

> **Note**: 이 문서는 코드 분석을 기반으로 작성되었습니다.
> 실제 구현 시 최신 코드와 일치하는지 확인하세요.
