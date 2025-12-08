# 🛠️ AI Bots 구현 가이드

> **작성일**: 2024년 12월 8일
> **문서 타입**: 단계별 구현 가이드 (Phase 1~5)

---

## 📋 개요

이 문서는 **Bitget AI Bots 시스템 구현을 위한 단계별 가이드**입니다.

**총 작업 기간**: 3주 (15일, 풀타임 기준)

**작업 전 준비사항**:
1. ✅ 운영 중인 코드를 새 브랜치로 복제
2. ✅ 테스트용 Bitget 계좌 준비
3. ✅ DeepSeek API 키 확인

---

## 🚀 Phase 1: 인프라 및 AI 서비스 (Week 1, Day 1-5)

### Day 1: 데이터베이스 모델 추가

#### 1.1 새 Git 브랜치 생성

```bash
# 현재 main 브랜치 상태 확인
git status

# 최신 상태로 업데이트
git pull origin main

# 새 브랜치 생성 및 체크아웃
git checkout -b feature/ai-bots

# 브랜치 확인
git branch
```

#### 1.2 데이터베이스 모델 파일 수정

**파일**: `backend/src/database/models.py`

```python
# 파일 끝에 다음 내용 추가

from enum import Enum

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
    ARITHMETIC = "arithmetic"
    GEOMETRIC = "geometric"


class AIBot(Base):
    """AI 자동매매 봇 통합 모델"""
    __tablename__ = "ai_bots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    bot_type = Column(Enum(BotType), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), default="1h")

    # 투자 설정
    investment_amount = Column(Float, nullable=False)
    investment_ratio = Column(Float, nullable=True)
    leverage = Column(Integer, default=1)

    # Futures Grid 파라미터
    grid_type = Column(Enum(GridType), nullable=True)
    grid_mode = Column(Enum(GridMode), default=GridMode.ARITHMETIC)
    price_range_lower = Column(Float, nullable=True)
    price_range_upper = Column(Float, nullable=True)
    grid_count = Column(Integer, nullable=True)

    # Martingale 파라미터
    initial_order_size = Column(Float, nullable=True)
    price_step_percent = Column(Float, nullable=True)
    multiplier = Column(Float, default=2.0)
    max_safety_orders = Column(Integer, nullable=True)

    # CTA 파라미터
    indicator_type = Column(String(20), nullable=True)
    signal_params = Column(JSON, nullable=True)

    # Smart Portfolio 파라미터
    asset_allocation = Column(JSON, nullable=True)
    rebalance_frequency = Column(String(20), nullable=True)

    # 리스크 관리
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    trigger_price = Column(Float, nullable=True)

    # 봇 상태
    status = Column(String(20), default="stopped", index=True)
    is_ai_recommended = Column(Boolean, default=True)

    # 성과 지표
    total_profit = Column(Float, default=0.0)
    total_profit_percent = Column(Float, default=0.0)
    roi_30d = Column(Float, nullable=True)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)

    # AI 메타데이터
    ai_analysis = Column(JSON, nullable=True)
    risk_level = Column(String(20), nullable=True)

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계
    user = relationship("User", backref="ai_bots")
    grid_positions = relationship(
        "GridPosition",
        back_populates="bot",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_aibot_user_status", "user_id", "status"),
        Index("idx_aibot_symbol_type", "symbol", "bot_type"),
    )


class GridPosition(Base):
    """그리드 봇의 개별 포지션 추적"""
    __tablename__ = "grid_positions"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("ai_bots.id"), nullable=False, index=True)

    grid_level = Column(Integer, nullable=False)
    target_price = Column(Float, nullable=False)
    order_size = Column(Float, nullable=False)

    status = Column(String(20), default="pending", index=True)
    side = Column(String(10), nullable=True)

    buy_order_id = Column(String(100), nullable=True, index=True)
    sell_order_id = Column(String(100), nullable=True, index=True)

    entry_price = Column(Float, nullable=True)
    entry_time = Column(DateTime, nullable=True)
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime, nullable=True)

    profit = Column(Float, default=0.0)
    profit_percent = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bot = relationship("AIBot", back_populates="grid_positions")

    __table_args__ = (
        Index("idx_gridpos_bot_status", "bot_id", "status"),
        Index("idx_gridpos_level", "bot_id", "grid_level"),
    )


class AIStrategyRecommendation(Base):
    """AI 추천 전략 캐시"""
    __tablename__ = "ai_strategy_recommendations"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    bot_type = Column(Enum(BotType), nullable=False)
    investment_tier = Column(Float, nullable=False)

    parameters = Column(JSON, nullable=False)
    expected_roi_30d = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    win_rate = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)

    market_analysis = Column(JSON, nullable=True)

    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_recommendation_active", "symbol", "bot_type", "expires_at"),
    )
```

#### 1.3 Alembic 마이그레이션 생성 및 실행

```bash
# 백엔드 디렉토리로 이동
cd backend

# 마이그레이션 파일 생성
alembic revision --autogenerate -m "Add AI bots models (AIBot, GridPosition, AIStrategyRecommendation)"

# 생성된 마이그레이션 파일 확인
ls alembic/versions/

# 마이그레이션 실행
alembic upgrade head

# 결과 확인
echo "✅ 데이터베이스 마이그레이션 완료"
```

#### 1.4 Git 커밋

```bash
git add backend/src/database/models.py
git add alembic/versions/*.py
git commit -m "feat: Add AI bots database models

- Add AIBot model (통합 봇 관리)
- Add GridPosition model (그리드 레벨별 포지션)
- Add AIStrategyRecommendation model (AI 추천 캐시)
- Add Enum types: BotType, GridType, GridMode"

git push origin feature/ai-bots
```

**✅ Day 1 완료 체크리스트**:
- [ ] 새 Git 브랜치 생성
- [ ] AIBot, GridPosition, AIStrategyRecommendation 모델 추가
- [ ] Alembic 마이그레이션 실행 성공
- [ ] Git 커밋 및 푸시

---

### Day 2: AI 분석 서비스 기본 구조

#### 2.1 새 파일 생성

**파일**: `backend/src/services/ai_strategy_service.py`

```python
"""
AI 기반 전략 추천 및 시장 분석 서비스
"""

from typing import List, Dict, Any
import numpy as np
from datetime import datetime, timedelta
import logging

from ..services.bitget_rest import BitgetRestClient
from ..services.deepseek_service import deepseek_service

logger = logging.getLogger(__name__)


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

        Args:
            symbol: 거래쌍 (예: "BTCUSDT")
            timeframe: 타임프레임 (예: "1h")
            days: 분석 기간 (기본 7일)

        Returns:
            시장 분석 결과 딕셔너리
        """
        logger.info(f"Analyzing market for {symbol} ({timeframe}, {days} days)")

        # 1. Bitget에서 과거 캔들 가져오기
        bitget = BitgetRestClient()
        candles = await bitget.get_historical_candles(
            symbol=symbol,
            interval=timeframe,
            limit=days * 24  # 7일 = 168시간
        )

        if not candles:
            raise ValueError(f"No candle data available for {symbol}")

        # 2. 기술적 지표 계산
        closes = np.array([c["close"] for c in candles])
        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])

        current_price = closes[-1]
        high_7d = np.max(highs)
        low_7d = np.min(lows)

        # 변동성 (표준편차 / 평균 * 100)
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

        # 지지/저항선 (단순화: 7일 최저/최고)
        support_level = low_7d
        resistance_level = high_7d

        result = {
            "symbol": symbol,
            "current_price": float(current_price),
            "high_7d": float(high_7d),
            "low_7d": float(low_7d),
            "volatility": round(float(volatility), 2),
            "trend": trend,
            "support_level": float(support_level),
            "resistance_level": float(resistance_level),
            "rsi": round(float(rsi), 2),
            "candles": candles
        }

        logger.info(f"Market analysis completed: trend={trend}, volatility={volatility:.2f}%, RSI={rsi:.2f}")
        return result

    async def recommend_futures_grid_strategies(
        self,
        symbol: str,
        investment_amount: float,
        risk_tolerance: str = "medium"
    ) -> List[Dict]:
        """
        Futures Grid 전략 3개 추천

        Args:
            symbol: 거래쌍
            investment_amount: 투자 금액 (USDT)
            risk_tolerance: 리스크 선호도 (low/medium/high)

        Returns:
            3개 전략 리스트 (Conservative, Balanced, Aggressive)
        """
        logger.info(f"Recommending strategies for {symbol}, investment={investment_amount}, risk={risk_tolerance}")

        # 1. 시장 분석
        market_data = await self.analyze_market(symbol)

        # 2. DeepSeek API 호출
        prompt = self._build_grid_strategy_prompt(
            market_data, investment_amount, risk_tolerance
        )

        strategies = await deepseek_service.generate_strategies_with_prompt(prompt)

        # 3. 백테스트 (간단한 시뮬레이션)
        for strategy in strategies:
            backtest_result = await self._backtest_grid_strategy(
                strategy, market_data["candles"]
            )
            strategy["backtest"] = backtest_result

        logger.info(f"Generated {len(strategies)} strategies")
        return strategies

    def _build_grid_strategy_prompt(
        self, market_data: Dict, investment: float, risk: str
    ) -> str:
        """Futures Grid 프롬프트 생성"""
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

1. name: Strategy name in Korean
2. grid_type: "long", "short", or "neutral"
3. price_range_lower: number
4. price_range_upper: number
5. grid_count: 10-200
6. leverage: 1-20
7. expected_roi_30d: % APY
8. risk_level: "low", "medium", or "high"
9. stop_loss: price or null
10. take_profit: price or null
11. explanation: 2-3 sentences in Korean

**Output Format** (JSON array only, no markdown):
[
  {{
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
    "explanation": "현재 횡보장이므로 중립 그리드가 적합합니다."
  }}
]
"""

    async def _backtest_grid_strategy(
        self, strategy: Dict, candles: List[Dict]
    ) -> Dict:
        """
        그리드 전략 백테스트 (간단한 시뮬레이션)

        Returns:
            백테스트 결과 (총 거래 수, 승률, 최대 낙폭 등)
        """
        # TODO: 실제 백테스트 로직 구현
        # 현재는 더미 데이터 반환
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
            "max_drawdown": 0.0
        }

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
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


# 싱글톤 인스턴스
ai_strategy_service = AIStrategyService()
```

#### 2.2 DeepSeek 서비스 업데이트

**파일**: `backend/src/services/deepseek_service.py`

```python
# 기존 파일에 다음 메서드 추가

async def generate_strategies_with_prompt(self, prompt: str) -> List[Dict]:
    """
    커스텀 프롬프트로 전략 생성

    Args:
        prompt: DeepSeek API에 전달할 프롬프트

    Returns:
        전략 리스트 (JSON 파싱 결과)
    """
    try:
        response = await self._call_deepseek_api(prompt)

        # JSON 파싱
        import json
        strategies = json.loads(response)

        return strategies

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse DeepSeek response: {e}")
        logger.error(f"Response: {response}")
        raise ValueError("AI 응답을 파싱할 수 없습니다.")

    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        raise


async def _call_deepseek_api(self, prompt: str) -> str:
    """DeepSeek API 호출 (실제 구현)"""
    # TODO: 실제 DeepSeek API 호출 구현
    # 현재는 더미 응답 반환
    return """
[
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
    "explanation": "현재 횡보장이므로 중립 그리드가 적합합니다."
  }
]
"""
```

#### 2.3 Git 커밋

```bash
git add backend/src/services/ai_strategy_service.py
git add backend/src/services/deepseek_service.py
git commit -m "feat: Add AI strategy service

- Add AIStrategyService class
- Add market analysis logic (volatility, trend, RSI)
- Add DeepSeek prompt builder
- Add strategy recommendation method"

git push origin feature/ai-bots
```

**✅ Day 2 완료 체크리스트**:
- [ ] AIStrategyService 클래스 작성
- [ ] 시장 분석 로직 구현 (변동성, 트렌드, RSI)
- [ ] DeepSeek 프롬프트 빌더 작성
- [ ] Git 커밋 및 푸시

---

### Day 3: DeepSeek 프롬프트 최적화 및 테스트

#### 3.1 DeepSeek API 연동 테스트

**파일**: `backend/test_deepseek.py` (테스트용)

```python
"""
DeepSeek API 연동 테스트
"""

import asyncio
from src.services.ai_strategy_service import ai_strategy_service

async def test_ai_recommendation():
    """AI 전략 추천 테스트"""

    symbol = "BTCUSDT"
    investment = 1000.0

    print(f"🤖 AI 전략 추천 테스트 시작...")
    print(f"   Symbol: {symbol}")
    print(f"   Investment: {investment} USDT\n")

    try:
        strategies = await ai_strategy_service.recommend_futures_grid_strategies(
            symbol=symbol,
            investment_amount=investment,
            risk_tolerance="medium"
        )

        print(f"✅ {len(strategies)}개 전략 생성 완료!\n")

        for i, strategy in enumerate(strategies, 1):
            print(f"전략 {i}: {strategy['name']}")
            print(f"  - Grid Type: {strategy['grid_type']}")
            print(f"  - Price Range: ${strategy['price_range_lower']:,} - ${strategy['price_range_upper']:,}")
            print(f"  - Grids: {strategy['grid_count']}개")
            print(f"  - Leverage: {strategy['leverage']}x")
            print(f"  - Expected ROI: {strategy['expected_roi_30d']}%")
            print(f"  - Risk: {strategy['risk_level']}")
            print(f"  - Explanation: {strategy['explanation']}\n")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_recommendation())
```

#### 3.2 테스트 실행

```bash
cd backend

# 환경 변수 설정
export DATABASE_URL="sqlite+aiosqlite:///./trading.db"
export ENCRYPTION_KEY="Dz9w_blEMa-tMD5hqK6V7yiaYecQBdsTaO0PJR3ESn8="

# 테스트 실행
python test_deepseek.py
```

**예상 출력**:
```
🤖 AI 전략 추천 테스트 시작...
   Symbol: BTCUSDT
   Investment: 1000 USDT

Analyzing market for BTCUSDT (1h, 7 days)
Market analysis completed: trend=sideways, volatility=3.20%, RSI=52.30
✅ 3개 전략 생성 완료!

전략 1: BTC 안전 그리드
  - Grid Type: neutral
  - Price Range: $95,000 - $105,000
  - Grids: 30개
  - Leverage: 3x
  - Expected ROI: 15.2%
  - Risk: low
  - Explanation: 현재 횡보장이므로 중립 그리드가 적합합니다.
```

**✅ Day 3 완료 체크리스트**:
- [ ] DeepSeek API 연동 테스트 성공
- [ ] 프롬프트 최적화 (JSON 파싱 성공)
- [ ] 3개 전략 정상 생성 확인

---

### Day 4: API 엔드포인트 기본 틀

#### 4.1 새 API 라우터 생성

**파일**: `backend/src/api/grid_bot.py`

```python
"""
Grid Bot API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel
import logging

from ..database.db import get_session
from ..utils.jwt_auth import get_current_user_id
from ..services.ai_strategy_service import ai_strategy_service
from ..services.bitget_rest import get_bitget_rest
from ..utils.crypto_secrets import decrypt_secret

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grid-bot", tags=["Grid Bot"])


class AnalyzeRequest(BaseModel):
    """AI 전략 분석 요청"""
    symbol: str
    investment_ratio: float  # %
    risk_tolerance: str = "medium"  # low, medium, high


@router.post("/analyze")
async def analyze_market_for_grid(
    request: AnalyzeRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id)
):
    """
    AI 기반 그리드 전략 추천

    - 시장 분석 (변동성, 트렌드, RSI 등)
    - DeepSeek AI로 3개 전략 생성
    - 백테스트 결과 포함
    """
    try:
        # 1. 계좌 잔고 조회
        from ..database.models import ApiKey
        from sqlalchemy import select

        result = await session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id)
        )
        api_key_obj = result.scalars().first()

        if not api_key_obj:
            raise HTTPException(status_code=400, detail="API 키를 먼저 등록해주세요.")

        # API 키 복호화
        api_key = decrypt_secret(api_key_obj.encrypted_api_key)
        api_secret = decrypt_secret(api_key_obj.encrypted_secret_key)
        passphrase = decrypt_secret(api_key_obj.encrypted_passphrase)

        bitget_client = get_bitget_rest(api_key, api_secret, passphrase)

        # 2. 계좌 잔고 조회
        account_info = await bitget_client.get_account_info()
        available_balance = float(account_info.get("available", 0))

        # 3. 투자 금액 계산
        investment_amount = available_balance * (request.investment_ratio / 100)

        # 최소 투자 금액 체크
        if investment_amount < 10:
            raise HTTPException(
                status_code=400,
                detail=f"투자 금액이 최소 요구사항(10 USDT)보다 적습니다. (현재: {investment_amount:.2f} USDT)"
            )

        # 4. AI 전략 추천
        strategies = await ai_strategy_service.recommend_futures_grid_strategies(
            symbol=request.symbol,
            investment_amount=investment_amount,
            risk_tolerance=request.risk_tolerance
        )

        # 5. 시장 분석 결과
        market_analysis = await ai_strategy_service.analyze_market(request.symbol)

        return {
            "success": True,
            "account_balance": available_balance,
            "investment_amount": investment_amount,
            "market_analysis": {
                "current_price": market_analysis["current_price"],
                "trend": market_analysis["trend"],
                "volatility": market_analysis["volatility"],
                "rsi": market_analysis["rsi"]
            },
            "strategies": strategies
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI 분석 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI 분석 실패: {str(e)}")


# TODO: 나머지 엔드포인트 (create, start, stop, list, performance)
```

#### 4.2 메인 앱에 라우터 추가

**파일**: `backend/src/main.py`

```python
# 기존 import에 추가
from .api import grid_bot

# app.include_router() 섹션에 추가
app.include_router(grid_bot.router)
```

#### 4.3 API 테스트 (Postman 또는 curl)

```bash
# 로그인하여 토큰 받기
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com", "password": "admin123"}' \
  | jq -r '.token')

# AI 전략 분석 요청
curl -X POST http://localhost:8000/grid-bot/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "symbol": "BTCUSDT",
    "investment_ratio": 10,
    "risk_tolerance": "medium"
  }' | jq .
```

**✅ Day 4 완료 체크리스트**:
- [ ] `/grid-bot/analyze` 엔드포인트 작성
- [ ] 메인 앱에 라우터 등록
- [ ] API 테스트 성공 (Postman/curl)

---

### Day 5: 투자 금액 비율 계산 로직

#### 5.1 계좌 헬퍼 서비스 생성

**파일**: `backend/src/services/account_helper.py`

```python
"""
계좌 관련 헬퍼 함수
"""

from typing import Dict
from ..services.bitget_rest import BitgetRestClient


async def get_user_balance(
    user_id: int,
    bitget_client: BitgetRestClient
) -> Dict:
    """
    사용자 계좌 잔고 조회

    Returns:
    {
        "total_equity": 5000.0,
        "available_balance": 4500.0,
        "unrealized_pnl": 50.0,
        "margin_used": 500.0
    }
    """
    account_info = await bitget_client.get_account_info()

    return {
        "total_equity": float(account_info.get("equity", 0)),
        "available_balance": float(account_info.get("available", 0)),
        "unrealized_pnl": float(account_info.get("unrealizedPL", 0)),
        "margin_used": float(account_info.get("frozen", 0))
    }


async def calculate_investment_from_ratio(
    user_id: int,
    ratio_percent: float,
    bitget_client: BitgetRestClient
) -> float:
    """
    계좌 잔고 대비 투자 금액 계산

    Args:
        ratio_percent: 투자 비율 (예: 10 = 잔고의 10%)

    Returns:
        투자 금액 (USDT)
    """
    balance = await get_user_balance(user_id, bitget_client)
    available = balance["available_balance"]

    investment = available * (ratio_percent / 100)

    # 최소 투자 금액 체크
    MIN_INVESTMENT = 10  # USDT
    if investment < MIN_INVESTMENT:
        raise ValueError(
            f"투자 금액이 최소 요구사항({MIN_INVESTMENT} USDT)보다 적습니다. "
            f"(계산: {available} * {ratio_percent}% = {investment} USDT)"
        )

    return investment
```

**✅ Week 1 완료!**

---

## ⚙️ Phase 2: 그리드 봇 엔진 (Week 2, Day 6-10)

### Day 6-7: GridBotEngine 기본 구조

**파일**: `backend/src/services/grid_bot_engine.py`

```python
"""
Grid Bot 실행 엔진
"""

import asyncio
from typing import List, Dict, Optional
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import AIBot, GridPosition, GridMode
from ..services.bitget_rest import BitgetRestClient, OrderSide, OrderType

logger = logging.getLogger(__name__)


class GridBotEngine:
    """Futures Grid Bot 실행 엔진"""

    def __init__(self):
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

        logger.info(f"Starting grid bot {bot.id} for {bot.symbol}")

        # 1. 그리드 레벨 계산
        grid_levels = self._calculate_grid_levels(
            lower=bot.price_range_lower,
            upper=bot.price_range_upper,
            count=bot.grid_count,
            mode=bot.grid_mode
        )

        logger.info(f"Calculated {len(grid_levels)} grid levels")

        # 2. GridPosition 생성
        for i, price in enumerate(grid_levels):
            grid_position = GridPosition(
                bot_id=bot.id,
                grid_level=i,
                target_price=price,
                order_size=self._calculate_order_size(
                    bot.investment_amount,
                    bot.grid_count,
                    bot.leverage
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

        logger.info(f"✅ Bot {bot.id} started successfully")

    def _calculate_grid_levels(
        self,
        lower: float,
        upper: float,
        count: int,
        mode: GridMode
    ) -> List[float]:
        """그리드 레벨 가격 계산"""
        if mode == GridMode.ARITHMETIC:
            # 등차수열 (가격 간격 동일)
            step = (upper - lower) / count
            return [lower + i * step for i in range(count + 1)]
        elif mode == GridMode.GEOMETRIC:
            # 등비수열 (% 간격 동일)
            import math
            ratio = (upper / lower) ** (1 / count)
            return [lower * (ratio ** i) for i in range(count + 1)]

    def _calculate_order_size(
        self,
        investment: float,
        grid_count: int,
        leverage: int
    ) -> float:
        """주문 수량 계산"""
        per_grid_investment = investment / grid_count
        return per_grid_investment * leverage

    async def _run_bot_loop(
        self,
        bot: AIBot,
        bitget_client: BitgetRestClient,
        session: AsyncSession
    ):
        """봇 메인 루프"""
        try:
            logger.info(f"Bot {bot.id} main loop started")

            # TODO: 초기 주문 배치 및 모니터링 루프
            # Day 8-9에서 구현

            while True:
                await asyncio.sleep(3.0)

        except asyncio.CancelledError:
            logger.info(f"Bot {bot.id} cancelled")
            raise
```

**✅ Day 6-7 완료 체크리스트**:
- [ ] GridBotEngine 클래스 작성
- [ ] 그리드 레벨 계산 (등차수열, 등비수열)
- [ ] 주문 수량 계산
- [ ] GridPosition 레코드 생성

---

## 🎨 Phase 3: 프론트엔드 (Week 3, Day 11-15)

### Day 11-12: Futures Grid Bot 페이지

**파일**: `frontend/src/pages/FuturesGridBot.jsx`

상세 코드는 `AI_BOTS_TECHNICAL_SPEC.md` 참조

**✅ Day 11-12 완료 체크리스트**:
- [ ] FuturesGridBot.jsx 페이지 작성
- [ ] AI 추천 전략 카드 UI
- [ ] ROI 차트 표시
- [ ] 투자 비율 슬라이더

---

## 📚 참고 자료

- **기술 사양**: `AI_BOTS_TECHNICAL_SPEC.md`
- **Q&A**: `AI_BOTS_QNA.md`
- **마스터 플랜**: `AI_BOTS_MASTER_PLAN.md`

---

**작성자**: Claude AI
**최종 업데이트**: 2024년 12월 8일
**버전**: 1.0.0
