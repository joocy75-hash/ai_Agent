"""
Adaptive Market Regime Fighter Strategy (적응형 시장체제 전투 전략)

**Strategy Name:** Adaptive_Market_Regime_Fighter

**Goal:** 시장 체제별 최적의 서브 전략을 동적으로 적용하여 우수한 P&L 달성

**Core Features:**
1. Market Regime Classification: Bull, Bear, Sideways, High Volatility
2. Dynamic Sub-Strategy Switching based on regime
3. Smooth Transition Logic with Anti-Whipsaw Protection
4. 30% Margin Allocation Enforcement
5. AI-Enhanced Regime Detection and Signal Validation

**Sub-Strategy Implementation:**
- Bull Market: Aggressive Momentum-Following (RSI/MACD Breakouts, Volume Spikes)
- Bear Market: Controlled Short-Selling/Range Fade (Quick Exits, Trailing Stops)
- Sideways Market: Mean Reversion/Oscillator Trading (Bollinger Bands)
- High Volatility: Breakout Confirmation/Risk Reduction (Defensive Mode)

Author: AI Trading System
Version: 1.0.0
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class MarketRegime(str, Enum):
    """시장 체제 분류"""
    BULL = "bull"                    # 강세장 (상승 추세)
    BEAR = "bear"                    # 약세장 (하락 추세)
    SIDEWAYS = "sideways"            # 횡보장 (레인지)
    HIGH_VOLATILITY = "high_volatility"  # 변동성 확대장
    UNKNOWN = "unknown"              # 불명확


class TradingAction(str, Enum):
    """거래 액션"""
    ENTER_LONG = "enter_long"
    ENTER_SHORT = "enter_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    HOLD = "hold"
    DEFENSIVE_MODE = "defensive_mode"


class ProtectionLevel(str, Enum):
    """보호 수준"""
    NORMAL = "normal"
    CAUTIOUS = "cautious"       # 연속 2회 손실
    DEFENSIVE = "defensive"     # 연속 3회 손실
    LOCKDOWN = "lockdown"       # 연속 5회 손실 또는 일일 손실 한도


@dataclass
class RegimeClassification:
    """시장 체제 분류 결과"""
    regime: MarketRegime
    confidence: float               # 0.0 ~ 1.0
    volatility_percentile: float    # 변동성 백분위
    trend_strength: float           # 추세 강도 (ADX)
    trend_direction: float          # 추세 방향 (-1 ~ 1)
    support_level: float
    resistance_level: float
    indicators: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ai_enhanced: bool = False


@dataclass
class SubStrategySignal:
    """서브 전략 시그널"""
    action: TradingAction
    confidence: float
    position_size_percent: float    # 30% 한도 대비 비율
    leverage: int
    stop_loss_percent: float
    take_profit_percent: float
    reasoning: str
    regime: MarketRegime
    sub_strategy: str
    warnings: List[str] = field(default_factory=list)


@dataclass
class RegimeTransition:
    """체제 전환 기록"""
    from_regime: MarketRegime
    to_regime: MarketRegime
    timestamp: datetime
    confidence: float
    held_duration_minutes: int


# ============================================================================
# MARGIN CAP ENFORCER (30% HARD LIMIT)
# ============================================================================

class MarginCapEnforcer:
    """
    30% 마진 한도 강제 모듈
    모든 서브 전략에 공통 적용
    """
    MAX_MARGIN_PERCENT = 30.0
    SAFETY_BUFFER_PERCENT = 2.0
    MIN_FREE_MARGIN_PERCENT = 5.0

    def __init__(self):
        self._effective_max = self.MAX_MARGIN_PERCENT - self.SAFETY_BUFFER_PERCENT
        logger.info(
            f"[MarginCapEnforcer] MAX={self.MAX_MARGIN_PERCENT}%, "
            f"EFFECTIVE={self._effective_max}%"
        )

    async def get_margin_status(self, exchange_client) -> Dict[str, Any]:
        """현재 마진 상태 조회"""
        try:
            balance = await exchange_client.fetch_balance()
            usdt = balance.get("USDT", {})
            total = float(usdt.get("total", 0))
            used = float(usdt.get("used", 0))

            max_margin = total * (self._effective_max / 100)
            usage_percent = (used / total * 100) if total > 0 else 0
            remaining = max(0, max_margin - used)
            can_open = remaining > (total * self.MIN_FREE_MARGIN_PERCENT / 100)

            return {
                "total_balance": total,
                "used_margin": used,
                "max_margin": max_margin,
                "remaining_margin": remaining,
                "usage_percent": usage_percent,
                "can_open_position": can_open
            }
        except Exception as e:
            logger.error(f"[MarginCapEnforcer] Error: {e}")
            return {
                "total_balance": 0,
                "used_margin": 0,
                "max_margin": 0,
                "remaining_margin": 0,
                "usage_percent": 100,
                "can_open_position": False
            }

    def validate_position_size(
        self,
        requested_percent: float,
        margin_status: Dict[str, Any]
    ) -> Tuple[bool, float, str]:
        """
        포지션 크기 검증 및 조정

        Returns:
            (allowed, adjusted_percent, message)
        """
        if not margin_status["can_open_position"]:
            return False, 0.0, "마진 한도 도달 - 신규 포지션 불가"

        total = margin_status["total_balance"]
        remaining = margin_status["remaining_margin"]

        requested_margin = total * (requested_percent / 100)

        if requested_margin > remaining:
            adjusted_percent = (remaining / total * 100) * 0.9  # 90% of remaining
            return True, adjusted_percent, f"포지션 크기 조정: {requested_percent:.1f}% → {adjusted_percent:.1f}%"

        return True, requested_percent, f"✅ 포지션 승인: {requested_percent:.1f}%"


# ============================================================================
# ENHANCED REGIME CLASSIFIER
# ============================================================================

class EnhancedRegimeClassifier:
    """
    향상된 시장 체제 분류기

    다중 지표를 종합 분석하여 4가지 시장 체제 분류:
    1. Bull (강세장): ADX > 25, EMA alignment up, price above MA
    2. Bear (약세장): ADX > 25, EMA alignment down, price below MA
    3. Sideways (횡보장): ADX < 20, price within Bollinger Bands
    4. High Volatility (변동성 확대장): VIX-like > 2x average, ATR spike
    """

    # 분류 임계값
    TRENDING_ADX_THRESHOLD = 25.0
    RANGING_ADX_THRESHOLD = 20.0
    HIGH_VOL_MULTIPLIER = 2.0
    BULL_TREND_THRESHOLD = 0.02      # 2% above MA
    BEAR_TREND_THRESHOLD = -0.02     # 2% below MA

    # 전환 안정화 파라미터
    MIN_REGIME_HOLD_CANDLES = 3      # 최소 3개 캔들 유지
    CONFIRMATION_THRESHOLD = 0.7     # 70% 이상 신뢰도로 전환

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.regime_history: deque = deque(maxlen=20)
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_start_time: Optional[datetime] = None
        self.candles_in_regime = 0

        # AI 서비스 연결 (선택적)
        self.ai_service = None
        self.enable_ai = self.config.get("enable_ai", True)

    def set_ai_service(self, ai_service):
        """AI 서비스 설정"""
        self.ai_service = ai_service
        logger.info("AI service connected to RegimeClassifier")

    async def classify_regime(
        self,
        df: pd.DataFrame,
        current_price: float
    ) -> RegimeClassification:
        """
        시장 체제 분류 수행

        Args:
            df: OHLCV DataFrame (최소 200개 캔들)
            current_price: 현재가

        Returns:
            RegimeClassification 객체
        """
        # 1. 기술적 지표 계산
        indicators = self._calculate_all_indicators(df)

        # 2. 규칙 기반 분류
        regime, confidence = self._rule_based_classification(
            df, current_price, indicators
        )

        # 3. AI 강화 (선택적)
        if self.enable_ai and self.ai_service:
            try:
                ai_result = await self._ai_enhanced_classification(
                    df, current_price, indicators, regime, confidence
                )
                if ai_result:
                    regime = ai_result["regime"]
                    confidence = ai_result["confidence"]
            except Exception as e:
                logger.warning(f"AI classification failed, using rule-based: {e}")

        # 4. 전환 안정화 (Anti-Whipsaw)
        regime, confidence = self._apply_transition_smoothing(regime, confidence)

        # 5. 지지/저항선 계산
        support, resistance = self._calculate_sr_levels(df, indicators)

        # 6. 결과 생성
        classification = RegimeClassification(
            regime=regime,
            confidence=confidence,
            volatility_percentile=indicators.get("volatility_percentile", 0.5),
            trend_strength=indicators.get("adx", 0),
            trend_direction=indicators.get("trend_direction", 0),
            support_level=support,
            resistance_level=resistance,
            indicators=indicators,
            ai_enhanced=self.ai_service is not None and self.enable_ai
        )

        # 7. 히스토리 기록
        self.regime_history.append(classification)
        self.candles_in_regime += 1

        logger.info(
            f"[Regime] {regime.value.upper()} (conf: {confidence:.0%}, "
            f"ADX: {indicators.get('adx', 0):.1f}, "
            f"Vol%: {indicators.get('volatility_percentile', 0):.0%})"
        )

        return classification

    def _calculate_all_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """모든 기술적 지표 계산"""
        indicators = {}

        # EMA (9, 21, 50, 200)
        for period in [9, 21, 50, 200]:
            if len(df) >= period:
                indicators[f"ema_{period}"] = df["close"].ewm(span=period).mean().iloc[-1]

        # RSI (14)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        indicators["rsi"] = float(100 - (100 / (1 + rs.iloc[-1]))) if not pd.isna(rs.iloc[-1]) else 50

        # MACD
        exp12 = df["close"].ewm(span=12).mean()
        exp26 = df["close"].ewm(span=26).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9).mean()
        indicators["macd"] = float(macd.iloc[-1])
        indicators["macd_signal"] = float(signal.iloc[-1])
        indicators["macd_hist"] = float((macd - signal).iloc[-1])

        # Bollinger Bands
        bb_period = 20
        bb_middle = df["close"].rolling(bb_period).mean()
        bb_std = df["close"].rolling(bb_period).std()
        indicators["bb_upper"] = float((bb_middle + 2 * bb_std).iloc[-1])
        indicators["bb_middle"] = float(bb_middle.iloc[-1])
        indicators["bb_lower"] = float((bb_middle - 2 * bb_std).iloc[-1])
        indicators["bb_width"] = float((indicators["bb_upper"] - indicators["bb_lower"]) / indicators["bb_middle"] * 100)

        # ATR (14)
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        indicators["atr"] = float(atr.iloc[-1])

        # ATR % (변동성)
        current_price = df["close"].iloc[-1]
        indicators["atr_percent"] = float(atr.iloc[-1] / current_price * 100)

        # 변동성 백분위 (최근 100개 ATR 대비)
        atr_history = atr.tail(100).dropna()
        if len(atr_history) > 0:
            current_atr = atr.iloc[-1]
            indicators["volatility_percentile"] = float(
                (atr_history < current_atr).sum() / len(atr_history)
            )
        else:
            indicators["volatility_percentile"] = 0.5

        # ADX (14)
        indicators["adx"] = self._calculate_adx(df, 14)

        # DI+, DI-
        di_plus, di_minus = self._calculate_di(df, 14)
        indicators["di_plus"] = di_plus
        indicators["di_minus"] = di_minus

        # 추세 방향 (-1 ~ 1)
        ema_21 = indicators.get("ema_21", current_price)
        ema_50 = indicators.get("ema_50", current_price)
        if ema_50 > 0:
            indicators["trend_direction"] = float((ema_21 - ema_50) / ema_50)
        else:
            indicators["trend_direction"] = 0

        # 거래량 분석
        vol_sma = df["volume"].rolling(20).mean()
        indicators["volume_ratio"] = float(df["volume"].iloc[-1] / vol_sma.iloc[-1]) if vol_sma.iloc[-1] > 0 else 1

        # VIX-like 지표 (볼린저밴드 폭 기반)
        bb_width_history = ((df["close"].rolling(20).mean() + 2 * df["close"].rolling(20).std() -
                            (df["close"].rolling(20).mean() - 2 * df["close"].rolling(20).std())) /
                           df["close"].rolling(20).mean() * 100).tail(50)
        if len(bb_width_history) > 0:
            avg_bb_width = bb_width_history.mean()
            indicators["vix_like_ratio"] = float(indicators["bb_width"] / avg_bb_width) if avg_bb_width > 0 else 1
        else:
            indicators["vix_like_ratio"] = 1

        return indicators

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """ADX 계산"""
        if len(df) < period * 2:
            return 25.0  # 기본값

        high = df["high"]
        low = df["low"]
        close = df["close"]

        plus_dm = high.diff()
        minus_dm = low.diff().abs() * -1

        plus_dm = plus_dm.where((plus_dm > minus_dm.abs()) & (plus_dm > 0), 0)
        minus_dm = minus_dm.abs().where((minus_dm.abs() > plus_dm) & (minus_dm < 0), 0)

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001))
        adx = dx.rolling(period).mean()

        return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 25.0

    def _calculate_di(self, df: pd.DataFrame, period: int = 14) -> Tuple[float, float]:
        """DI+, DI- 계산"""
        if len(df) < period * 2:
            return 25.0, 25.0

        high = df["high"]
        low = df["low"]
        close = df["close"]

        plus_dm = high.diff()
        minus_dm = low.diff().abs()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)

        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

        return float(plus_di.iloc[-1]) if not pd.isna(plus_di.iloc[-1]) else 25.0, \
               float(minus_di.iloc[-1]) if not pd.isna(minus_di.iloc[-1]) else 25.0

    def _rule_based_classification(
        self,
        df: pd.DataFrame,
        current_price: float,
        indicators: Dict[str, float]
    ) -> Tuple[MarketRegime, float]:
        """규칙 기반 시장 체제 분류"""
        adx = indicators.get("adx", 0)
        volatility_percentile = indicators.get("volatility_percentile", 0.5)
        vix_like_ratio = indicators.get("vix_like_ratio", 1)
        trend_direction = indicators.get("trend_direction", 0)
        ema_21 = indicators.get("ema_21", current_price)
        ema_50 = indicators.get("ema_50", current_price)
        di_plus = indicators.get("di_plus", 25)
        di_minus = indicators.get("di_minus", 25)
        rsi = indicators.get("rsi", 50)

        confidence = 0.5

        # 1. HIGH VOLATILITY 체크 (최우선)
        if volatility_percentile > 0.85 or vix_like_ratio >= self.HIGH_VOL_MULTIPLIER:
            confidence = min(0.9, 0.5 + volatility_percentile * 0.4)
            return MarketRegime.HIGH_VOLATILITY, confidence

        # 2. TRENDING 체크 (ADX > 25)
        if adx > self.TRENDING_ADX_THRESHOLD:
            # Bull vs Bear 결정
            if di_plus > di_minus and trend_direction > self.BULL_TREND_THRESHOLD:
                if current_price > ema_21 > ema_50:
                    confidence = min(0.9, 0.5 + adx / 100)
                    return MarketRegime.BULL, confidence

            if di_minus > di_plus and trend_direction < self.BEAR_TREND_THRESHOLD:
                if current_price < ema_21 < ema_50:
                    confidence = min(0.9, 0.5 + adx / 100)
                    return MarketRegime.BEAR, confidence

        # 3. SIDEWAYS 체크 (ADX < 20)
        if adx < self.RANGING_ADX_THRESHOLD:
            bb_lower = indicators.get("bb_lower", 0)
            bb_upper = indicators.get("bb_upper", float("inf"))

            if bb_lower < current_price < bb_upper:
                # 볼린저밴드 내 가격 위치 기반 신뢰도
                bb_range = bb_upper - bb_lower
                if bb_range > 0:
                    position_in_bb = (current_price - bb_lower) / bb_range
                    # 중앙에 가까울수록 높은 신뢰도
                    confidence = 0.5 + 0.3 * (1 - abs(position_in_bb - 0.5) * 2)
                else:
                    confidence = 0.6
                return MarketRegime.SIDEWAYS, confidence

        # 4. 애매한 경우 - RSI와 추세 방향으로 판단
        if trend_direction > 0.01 and rsi > 50:
            return MarketRegime.BULL, 0.55
        elif trend_direction < -0.01 and rsi < 50:
            return MarketRegime.BEAR, 0.55

        return MarketRegime.SIDEWAYS, 0.5

    async def _ai_enhanced_classification(
        self,
        df: pd.DataFrame,
        current_price: float,
        indicators: Dict[str, float],
        rule_regime: MarketRegime,
        rule_confidence: float
    ) -> Optional[Dict[str, Any]]:
        """AI 강화 분류 (DeepSeek)"""
        if not self.ai_service:
            return None

        system_prompt = """You are an expert cryptocurrency market regime classifier.
Classify the current market into one of these regimes:
- BULL: Strong uptrend (ADX>25, price above EMAs, DI+ > DI-)
- BEAR: Strong downtrend (ADX>25, price below EMAs, DI- > DI+)
- SIDEWAYS: Ranging market (ADX<20, price within Bollinger Bands)
- HIGH_VOLATILITY: Extreme volatility (VIX-like > 2x, ATR spike)

Return ONLY valid JSON: {"regime": "BULL|BEAR|SIDEWAYS|HIGH_VOLATILITY", "confidence": 0.0-1.0}"""

        user_prompt = f"""Analyze market regime:

Price: ${current_price:,.2f}
ADX: {indicators.get('adx', 0):.1f}
DI+: {indicators.get('di_plus', 0):.1f}
DI-: {indicators.get('di_minus', 0):.1f}
RSI: {indicators.get('rsi', 50):.1f}
MACD: {indicators.get('macd', 0):.2f}
Volatility%: {indicators.get('volatility_percentile', 0.5):.0%}
VIX-like Ratio: {indicators.get('vix_like_ratio', 1):.2f}
EMA21/EMA50: {indicators.get('ema_21', 0):.2f}/{indicators.get('ema_50', 0):.2f}

Rule-based: {rule_regime.value} ({rule_confidence:.0%})

Return JSON classification:"""

        try:
            result = await self.ai_service.call_ai(
                agent_type="market_regime",
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=100,
                enable_caching=True
            )

            import re
            import json
            response = result.get("response", "")
            match = re.search(r'\{[^{}]*\}', response)

            if match:
                ai_result = json.loads(match.group())
                regime_map = {
                    "BULL": MarketRegime.BULL,
                    "BEAR": MarketRegime.BEAR,
                    "SIDEWAYS": MarketRegime.SIDEWAYS,
                    "HIGH_VOLATILITY": MarketRegime.HIGH_VOLATILITY
                }
                return {
                    "regime": regime_map.get(ai_result.get("regime", "").upper(), rule_regime),
                    "confidence": float(ai_result.get("confidence", rule_confidence))
                }
        except Exception as e:
            logger.warning(f"AI classification parse error: {e}")

        return None

    def _apply_transition_smoothing(
        self,
        new_regime: MarketRegime,
        confidence: float
    ) -> Tuple[MarketRegime, float]:
        """
        체제 전환 안정화 (Anti-Whipsaw)

        Rules:
        1. 최소 3개 캔들 동안 현재 체제 유지
        2. 전환 시 70% 이상 신뢰도 필요
        3. 체제 히스토리 기반 일관성 체크
        """
        # 첫 분류
        if self.current_regime == MarketRegime.UNKNOWN:
            self.current_regime = new_regime
            self.regime_start_time = datetime.utcnow()
            self.candles_in_regime = 1
            return new_regime, confidence

        # 동일 체제 유지
        if new_regime == self.current_regime:
            self.candles_in_regime += 1
            return new_regime, confidence

        # 체제 전환 시도
        # Rule 1: 최소 캔들 수 체크
        if self.candles_in_regime < self.MIN_REGIME_HOLD_CANDLES:
            logger.debug(
                f"[Transition Blocked] Held {self.candles_in_regime}/{self.MIN_REGIME_HOLD_CANDLES} candles"
            )
            return self.current_regime, confidence * 0.8

        # Rule 2: 신뢰도 체크
        if confidence < self.CONFIRMATION_THRESHOLD:
            logger.debug(
                f"[Transition Blocked] Confidence {confidence:.0%} < {self.CONFIRMATION_THRESHOLD:.0%}"
            )
            return self.current_regime, confidence * 0.9

        # Rule 3: 히스토리 일관성 (최근 3개 중 2개 이상 일치)
        if len(self.regime_history) >= 3:
            recent_regimes = [r.regime for r in list(self.regime_history)[-3:]]
            if recent_regimes.count(new_regime) < 2:
                logger.debug(
                    f"[Transition Blocked] Inconsistent history: {recent_regimes}"
                )
                return self.current_regime, confidence * 0.85

        # 전환 승인
        old_regime = self.current_regime
        self.current_regime = new_regime
        self.candles_in_regime = 1
        self.regime_start_time = datetime.utcnow()

        logger.info(
            f"🔄 Regime Transition: {old_regime.value.upper()} → {new_regime.value.upper()} "
            f"(conf: {confidence:.0%})"
        )

        return new_regime, confidence

    def _calculate_sr_levels(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, float]
    ) -> Tuple[float, float]:
        """지지/저항선 계산"""
        # 최근 50개 캔들 기준
        recent = df.tail(50)

        # 피벗 포인트 기반
        high = recent["high"].max()
        low = recent["low"].min()
        close = df["close"].iloc[-1]

        pivot = (high + low + close) / 3

        # S1, R1
        support = 2 * pivot - high
        resistance = 2 * pivot - low

        # 볼린저밴드로 보정
        bb_lower = indicators.get("bb_lower", support)
        bb_upper = indicators.get("bb_upper", resistance)

        support = min(support, bb_lower)
        resistance = max(resistance, bb_upper)

        return support, resistance


# ============================================================================
# SUB-STRATEGIES
# ============================================================================

class BullMarketStrategy:
    """
    강세장 전략: Aggressive Momentum-Following

    - RSI/MACD 브레이크아웃 신호
    - 거래량 스파이크 확인
    - 추세 추종 진입
    - 넓은 익절 목표
    """

    NAME = "Bull_Momentum_Follower"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base_leverage = self.config.get("base_leverage", 10)
        self.max_leverage = self.config.get("max_leverage", 15)

    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        indicators: Dict[str, float],
        regime: RegimeClassification,
        current_position: Optional[Dict] = None
    ) -> SubStrategySignal:
        """강세장 매매 시그널 생성"""
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        macd_hist = indicators.get("macd_hist", 0)
        volume_ratio = indicators.get("volume_ratio", 1)
        ema_9 = indicators.get("ema_9", current_price)
        ema_21 = indicators.get("ema_21", current_price)

        # 포지션 보유 시 청산 조건 먼저 확인
        if current_position and current_position.get("side") == "long":
            return self._check_exit_conditions(
                current_price, indicators, regime, current_position
            )

        # 진입 조건
        # 1. RSI 50-70 (과매수 아닌 상승 모멘텀)
        # 2. MACD > Signal (상승 모멘텀)
        # 3. MACD 히스토그램 증가
        # 4. 거래량 스파이크 (1.2x 이상)
        # 5. 가격 > EMA9 > EMA21 (정배열)

        conditions_met = 0
        reasons = []

        if 50 < rsi < 70:
            conditions_met += 1
            reasons.append(f"RSI={rsi:.0f}")

        if macd > macd_signal:
            conditions_met += 1
            reasons.append("MACD↑")

        if macd_hist > 0:
            conditions_met += 1
            reasons.append("Hist+")

        if volume_ratio > 1.2:
            conditions_met += 1
            reasons.append(f"Vol={volume_ratio:.1f}x")

        if current_price > ema_9 > ema_21:
            conditions_met += 1
            reasons.append("EMA정배열")

        # 최소 4개 조건 충족 시 진입
        if conditions_met >= 4:
            confidence = min(0.85, 0.5 + conditions_met * 0.1)
            leverage = min(
                self.max_leverage,
                self.base_leverage + int(regime.confidence * 5)
            )

            return SubStrategySignal(
                action=TradingAction.ENTER_LONG,
                confidence=confidence,
                position_size_percent=min(80, 50 + conditions_met * 10),  # 30% 한도 대비
                leverage=leverage,
                stop_loss_percent=2.0,
                take_profit_percent=5.0,  # 강세장 넓은 익절
                reasoning=f"Bull Momentum: {', '.join(reasons)}",
                regime=MarketRegime.BULL,
                sub_strategy=self.NAME
            )

        return SubStrategySignal(
            action=TradingAction.HOLD,
            confidence=0.5,
            position_size_percent=0,
            leverage=self.base_leverage,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning=f"Bull: 조건 미충족 ({conditions_met}/4)",
            regime=MarketRegime.BULL,
            sub_strategy=self.NAME
        )

    def _check_exit_conditions(
        self,
        current_price: float,
        indicators: Dict[str, float],
        regime: RegimeClassification,
        position: Dict
    ) -> SubStrategySignal:
        """청산 조건 확인"""
        rsi = indicators.get("rsi", 50)
        macd_hist = indicators.get("macd_hist", 0)
        entry_price = position.get("entry_price", current_price)
        pnl_percent = (current_price - entry_price) / entry_price * 100

        # 익절 조건
        if pnl_percent >= 5.0:
            return SubStrategySignal(
                action=TradingAction.EXIT_LONG,
                confidence=0.9,
                position_size_percent=100,
                leverage=0,
                stop_loss_percent=0,
                take_profit_percent=0,
                reasoning=f"✅ Take Profit: {pnl_percent:.1f}%",
                regime=MarketRegime.BULL,
                sub_strategy=self.NAME
            )

        # 손절 조건
        if pnl_percent <= -2.0:
            return SubStrategySignal(
                action=TradingAction.EXIT_LONG,
                confidence=1.0,
                position_size_percent=100,
                leverage=0,
                stop_loss_percent=0,
                take_profit_percent=0,
                reasoning=f"⛔ Stop Loss: {pnl_percent:.1f}%",
                regime=MarketRegime.BULL,
                sub_strategy=self.NAME
            )

        # 추세 반전 신호
        if rsi > 75 and macd_hist < 0:
            return SubStrategySignal(
                action=TradingAction.EXIT_LONG,
                confidence=0.75,
                position_size_percent=100,
                leverage=0,
                stop_loss_percent=0,
                take_profit_percent=0,
                reasoning=f"Trend Reversal: RSI={rsi:.0f}, MACD Hist<0",
                regime=MarketRegime.BULL,
                sub_strategy=self.NAME
            )

        return SubStrategySignal(
            action=TradingAction.HOLD,
            confidence=0.6,
            position_size_percent=0,
            leverage=0,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning=f"Holding Long: PnL={pnl_percent:.1f}%",
            regime=MarketRegime.BULL,
            sub_strategy=self.NAME
        )


class BearMarketStrategy:
    """
    약세장 전략: Controlled Short-Selling / Range Fade

    - 보수적 숏 진입
    - 빠른 청산 (Quick Exits)
    - 트레일링 스탑 적극 활용
    - 자본 보존 우선
    """

    NAME = "Bear_Range_Fade"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base_leverage = self.config.get("base_leverage", 5)  # 숏은 보수적
        self.max_leverage = self.config.get("max_leverage", 8)

    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        indicators: Dict[str, float],
        regime: RegimeClassification,
        current_position: Optional[Dict] = None
    ) -> SubStrategySignal:
        """약세장 매매 시그널 생성"""
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        volume_ratio = indicators.get("volume_ratio", 1)
        ema_9 = indicators.get("ema_9", current_price)
        ema_21 = indicators.get("ema_21", current_price)
        bb_upper = indicators.get("bb_upper", current_price * 1.05)

        # 포지션 보유 시 청산 조건 먼저 확인
        if current_position and current_position.get("side") == "short":
            return self._check_exit_conditions(
                current_price, indicators, regime, current_position
            )

        # 숏 진입 조건 (보수적)
        # 1. RSI 30-50 (과매도 아닌 하락 모멘텀)
        # 2. MACD < Signal
        # 3. 저항선 근처 (BB Upper 근처)
        # 4. 가격 < EMA9 < EMA21 (역배열)

        conditions_met = 0
        reasons = []

        if 30 < rsi < 50:
            conditions_met += 1
            reasons.append(f"RSI={rsi:.0f}")

        if macd < macd_signal:
            conditions_met += 1
            reasons.append("MACD↓")

        # 저항선 근처에서 숏
        distance_to_resistance = (bb_upper - current_price) / current_price * 100
        if distance_to_resistance < 1.5:
            conditions_met += 1
            reasons.append("저항선근처")

        if current_price < ema_9 < ema_21:
            conditions_met += 1
            reasons.append("EMA역배열")

        # 최소 3개 조건 충족 시 진입 (숏은 더 보수적)
        if conditions_met >= 3:
            confidence = min(0.75, 0.4 + conditions_met * 0.1)

            return SubStrategySignal(
                action=TradingAction.ENTER_SHORT,
                confidence=confidence,
                position_size_percent=min(60, 40 + conditions_met * 5),  # 숏은 작은 사이즈
                leverage=self.base_leverage,  # 숏은 기본 레버리지 유지
                stop_loss_percent=1.5,  # 빠른 손절
                take_profit_percent=3.0,  # 빠른 익절
                reasoning=f"Bear Short: {', '.join(reasons)}",
                regime=MarketRegime.BEAR,
                sub_strategy=self.NAME
            )

        return SubStrategySignal(
            action=TradingAction.HOLD,
            confidence=0.5,
            position_size_percent=0,
            leverage=self.base_leverage,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning=f"Bear: 조건 미충족 ({conditions_met}/3)",
            regime=MarketRegime.BEAR,
            sub_strategy=self.NAME
        )

    def _check_exit_conditions(
        self,
        current_price: float,
        indicators: Dict[str, float],
        regime: RegimeClassification,
        position: Dict
    ) -> SubStrategySignal:
        """숏 청산 조건 확인"""
        rsi = indicators.get("rsi", 50)
        entry_price = position.get("entry_price", current_price)
        pnl_percent = (entry_price - current_price) / entry_price * 100  # 숏 PnL

        # 익절 (숏은 빠르게)
        if pnl_percent >= 3.0:
            return SubStrategySignal(
                action=TradingAction.EXIT_SHORT,
                confidence=0.9,
                position_size_percent=100,
                leverage=0,
                stop_loss_percent=0,
                take_profit_percent=0,
                reasoning=f"✅ Short TP: {pnl_percent:.1f}%",
                regime=MarketRegime.BEAR,
                sub_strategy=self.NAME
            )

        # 손절 (숏은 타이트하게)
        if pnl_percent <= -1.5:
            return SubStrategySignal(
                action=TradingAction.EXIT_SHORT,
                confidence=1.0,
                position_size_percent=100,
                leverage=0,
                stop_loss_percent=0,
                take_profit_percent=0,
                reasoning=f"⛔ Short SL: {pnl_percent:.1f}%",
                regime=MarketRegime.BEAR,
                sub_strategy=self.NAME
            )

        # 반전 신호
        if rsi < 25:
            return SubStrategySignal(
                action=TradingAction.EXIT_SHORT,
                confidence=0.7,
                position_size_percent=100,
                leverage=0,
                stop_loss_percent=0,
                take_profit_percent=0,
                reasoning=f"Oversold Exit: RSI={rsi:.0f}",
                regime=MarketRegime.BEAR,
                sub_strategy=self.NAME
            )

        return SubStrategySignal(
            action=TradingAction.HOLD,
            confidence=0.6,
            position_size_percent=0,
            leverage=0,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning=f"Holding Short: PnL={pnl_percent:.1f}%",
            regime=MarketRegime.BEAR,
            sub_strategy=self.NAME
        )


class SidewaysMarketStrategy:
    """
    횡보장 전략: Mean Reversion / Oscillator Trading

    - 볼린저밴드 경계에서 거래
    - RSI 과매수/과매도 활용
    - 작은 포지션, 높은 확률
    - 레인지 내 빠른 익절
    """

    NAME = "Sideways_Mean_Reversion"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base_leverage = self.config.get("base_leverage", 5)
        self.max_leverage = self.config.get("max_leverage", 8)

    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        indicators: Dict[str, float],
        regime: RegimeClassification,
        current_position: Optional[Dict] = None
    ) -> SubStrategySignal:
        """횡보장 매매 시그널 생성"""
        rsi = indicators.get("rsi", 50)
        bb_upper = indicators.get("bb_upper", current_price * 1.02)
        bb_lower = indicators.get("bb_lower", current_price * 0.98)
        bb_middle = indicators.get("bb_middle", current_price)

        # 포지션 보유 시 청산 조건 먼저 확인
        if current_position:
            return self._check_exit_conditions(
                current_price, indicators, regime, current_position
            )

        # BB 내 가격 위치
        bb_range = bb_upper - bb_lower
        if bb_range > 0:
            bb_position = (current_price - bb_lower) / bb_range  # 0 ~ 1
        else:
            bb_position = 0.5

        # 롱 진입: 하단 밴드 + RSI 과매도
        if bb_position < 0.15 and rsi < 35:
            confidence = 0.75 + (35 - rsi) / 100
            return SubStrategySignal(
                action=TradingAction.ENTER_LONG,
                confidence=min(0.85, confidence),
                position_size_percent=40,  # 횡보장은 작은 사이즈
                leverage=self.base_leverage,
                stop_loss_percent=1.5,
                take_profit_percent=2.0,  # 짧은 익절
                reasoning=f"Mean Reversion Long: BB={bb_position:.0%}, RSI={rsi:.0f}",
                regime=MarketRegime.SIDEWAYS,
                sub_strategy=self.NAME
            )

        # 숏 진입: 상단 밴드 + RSI 과매수
        if bb_position > 0.85 and rsi > 65:
            confidence = 0.70 + (rsi - 65) / 100
            return SubStrategySignal(
                action=TradingAction.ENTER_SHORT,
                confidence=min(0.80, confidence),
                position_size_percent=35,  # 숏은 더 작게
                leverage=self.base_leverage,
                stop_loss_percent=1.5,
                take_profit_percent=2.0,
                reasoning=f"Mean Reversion Short: BB={bb_position:.0%}, RSI={rsi:.0f}",
                regime=MarketRegime.SIDEWAYS,
                sub_strategy=self.NAME
            )

        return SubStrategySignal(
            action=TradingAction.HOLD,
            confidence=0.5,
            position_size_percent=0,
            leverage=self.base_leverage,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning=f"Sideways: BB내 대기 (BB={bb_position:.0%}, RSI={rsi:.0f})",
            regime=MarketRegime.SIDEWAYS,
            sub_strategy=self.NAME
        )

    def _check_exit_conditions(
        self,
        current_price: float,
        indicators: Dict[str, float],
        regime: RegimeClassification,
        position: Dict
    ) -> SubStrategySignal:
        """횡보장 청산 조건"""
        bb_middle = indicators.get("bb_middle", current_price)
        entry_price = position.get("entry_price", current_price)
        side = position.get("side", "long")

        if side == "long":
            pnl_percent = (current_price - entry_price) / entry_price * 100
            # 중앙선 도달 시 익절
            if current_price >= bb_middle or pnl_percent >= 2.0:
                return SubStrategySignal(
                    action=TradingAction.EXIT_LONG,
                    confidence=0.8,
                    position_size_percent=100,
                    leverage=0,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning=f"MR Exit: BB중앙 도달, PnL={pnl_percent:.1f}%",
                    regime=MarketRegime.SIDEWAYS,
                    sub_strategy=self.NAME
                )
            if pnl_percent <= -1.5:
                return SubStrategySignal(
                    action=TradingAction.EXIT_LONG,
                    confidence=1.0,
                    position_size_percent=100,
                    leverage=0,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning=f"MR SL: {pnl_percent:.1f}%",
                    regime=MarketRegime.SIDEWAYS,
                    sub_strategy=self.NAME
                )
        else:
            pnl_percent = (entry_price - current_price) / entry_price * 100
            if current_price <= bb_middle or pnl_percent >= 2.0:
                return SubStrategySignal(
                    action=TradingAction.EXIT_SHORT,
                    confidence=0.8,
                    position_size_percent=100,
                    leverage=0,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning=f"MR Exit: BB중앙 도달, PnL={pnl_percent:.1f}%",
                    regime=MarketRegime.SIDEWAYS,
                    sub_strategy=self.NAME
                )
            if pnl_percent <= -1.5:
                return SubStrategySignal(
                    action=TradingAction.EXIT_SHORT,
                    confidence=1.0,
                    position_size_percent=100,
                    leverage=0,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning=f"MR SL: {pnl_percent:.1f}%",
                    regime=MarketRegime.SIDEWAYS,
                    sub_strategy=self.NAME
                )

        return SubStrategySignal(
            action=TradingAction.HOLD,
            confidence=0.6,
            position_size_percent=0,
            leverage=0,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning="MR Holding",
            regime=MarketRegime.SIDEWAYS,
            sub_strategy=self.NAME
        )


class HighVolatilityStrategy:
    """
    고변동성 전략: Breakout Confirmation / Defensive Mode

    - 명확한 브레이크아웃 확인 후에만 진입
    - 대부분 Defensive Mode (거래 축소/중단)
    - 휩소 방지
    - 리스크 감소 우선
    """

    NAME = "HighVol_Breakout_Confirm"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.base_leverage = self.config.get("base_leverage", 3)  # 매우 보수적
        self.max_leverage = self.config.get("max_leverage", 5)

    def generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        indicators: Dict[str, float],
        regime: RegimeClassification,
        current_position: Optional[Dict] = None
    ) -> SubStrategySignal:
        """고변동성 매매 시그널 생성"""
        volume_ratio = indicators.get("volume_ratio", 1)
        adx = indicators.get("adx", 0)
        atr_percent = indicators.get("atr_percent", 0)
        rsi = indicators.get("rsi", 50)
        bb_upper = indicators.get("bb_upper", current_price * 1.05)
        bb_lower = indicators.get("bb_lower", current_price * 0.95)

        # 포지션 보유 시 즉시 청산 고려
        if current_position:
            return self._check_defensive_exit(
                current_price, indicators, regime, current_position
            )

        # 고변동성에서는 대부분 Defensive Mode
        # 진입 조건: 매우 강한 브레이크아웃 확인만

        # 상단 브레이크아웃 (매우 강한 신호만)
        if (current_price > bb_upper * 1.01 and
            volume_ratio > 2.0 and
            adx > 30 and
            rsi > 60):
            return SubStrategySignal(
                action=TradingAction.ENTER_LONG,
                confidence=0.65,  # 고변동성은 낮은 신뢰도
                position_size_percent=25,  # 매우 작은 사이즈
                leverage=self.base_leverage,
                stop_loss_percent=3.0,  # 넓은 손절
                take_profit_percent=5.0,
                reasoning=f"Confirmed Breakout Up: Vol={volume_ratio:.1f}x, ADX={adx:.0f}",
                regime=MarketRegime.HIGH_VOLATILITY,
                sub_strategy=self.NAME
            )

        # 하단 브레이크아웃 (극히 드물게)
        if (current_price < bb_lower * 0.99 and
            volume_ratio > 2.5 and
            adx > 35 and
            rsi < 25):
            return SubStrategySignal(
                action=TradingAction.ENTER_LONG,  # 역추세 롱 (과매도 반등)
                confidence=0.55,
                position_size_percent=20,
                leverage=self.base_leverage,
                stop_loss_percent=4.0,
                take_profit_percent=6.0,
                reasoning=f"Extreme Oversold Bounce: RSI={rsi:.0f}, Vol={volume_ratio:.1f}x",
                regime=MarketRegime.HIGH_VOLATILITY,
                sub_strategy=self.NAME,
                warnings=["고변동성 - 리스크 주의"]
            )

        # 기본: Defensive Mode
        return SubStrategySignal(
            action=TradingAction.DEFENSIVE_MODE,
            confidence=0.8,
            position_size_percent=0,
            leverage=0,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning=f"🛡️ Defensive Mode: ATR={atr_percent:.1f}%, 변동성 {regime.volatility_percentile:.0%}ile",
            regime=MarketRegime.HIGH_VOLATILITY,
            sub_strategy=self.NAME,
            warnings=["거래 축소/중단 권장", f"변동성 상위 {regime.volatility_percentile:.0%}"]
        )

    def _check_defensive_exit(
        self,
        current_price: float,
        indicators: Dict[str, float],
        regime: RegimeClassification,
        position: Dict
    ) -> SubStrategySignal:
        """고변동성에서 방어적 청산"""
        entry_price = position.get("entry_price", current_price)
        side = position.get("side", "long")

        if side == "long":
            pnl_percent = (current_price - entry_price) / entry_price * 100
        else:
            pnl_percent = (entry_price - current_price) / entry_price * 100

        # 고변동성에서는 이익이 나면 즉시 청산
        if pnl_percent > 1.0:
            action = TradingAction.EXIT_LONG if side == "long" else TradingAction.EXIT_SHORT
            return SubStrategySignal(
                action=action,
                confidence=0.9,
                position_size_percent=100,
                leverage=0,
                stop_loss_percent=0,
                take_profit_percent=0,
                reasoning=f"🛡️ Defensive Exit (이익 확보): {pnl_percent:.1f}%",
                regime=MarketRegime.HIGH_VOLATILITY,
                sub_strategy=self.NAME
            )

        # 손실이 커지면 즉시 손절
        if pnl_percent < -2.0:
            action = TradingAction.EXIT_LONG if side == "long" else TradingAction.EXIT_SHORT
            return SubStrategySignal(
                action=action,
                confidence=1.0,
                position_size_percent=100,
                leverage=0,
                stop_loss_percent=0,
                take_profit_percent=0,
                reasoning=f"🛡️ Defensive SL: {pnl_percent:.1f}%",
                regime=MarketRegime.HIGH_VOLATILITY,
                sub_strategy=self.NAME
            )

        return SubStrategySignal(
            action=TradingAction.HOLD,
            confidence=0.5,
            position_size_percent=0,
            leverage=0,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning=f"HighVol Holding: PnL={pnl_percent:.1f}%",
            regime=MarketRegime.HIGH_VOLATILITY,
            sub_strategy=self.NAME,
            warnings=["포지션 청산 권장"]
        )


# ============================================================================
# MAIN STRATEGY CLASS
# ============================================================================

class AdaptiveMarketRegimeFighter:
    """
    Adaptive Market Regime Fighter Strategy

    시장 체제를 자동으로 분류하고, 각 체제에 최적화된 서브 전략을 동적으로 적용합니다.
    30% 마진 한도를 엄격히 준수합니다.
    """

    STRATEGY_NAME = "Adaptive_Market_Regime_Fighter"
    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None):
        """
        전략 초기화

        Args:
            config: 전략 설정
                - symbol: 거래 심볼 (기본: "BTC/USDT")
                - timeframe: 시간프레임 (기본: "1h")
                - enable_ai: AI 활성화 (기본: True)
                - base_leverage: 기본 레버리지 (기본: 10)
                - max_leverage: 최대 레버리지 (기본: 15)
        """
        self.config = config or {}
        self.symbol = self.config.get("symbol", "BTC/USDT")
        self.timeframe = self.config.get("timeframe", "1h")
        self.enable_ai = self.config.get("enable_ai", True)

        # 마진 한도 강제 모듈
        self.margin_enforcer = MarginCapEnforcer()

        # 체제 분류기
        self.regime_classifier = EnhancedRegimeClassifier({
            "enable_ai": self.enable_ai
        })

        # 서브 전략들
        self.sub_strategies = {
            MarketRegime.BULL: BullMarketStrategy(self.config),
            MarketRegime.BEAR: BearMarketStrategy(self.config),
            MarketRegime.SIDEWAYS: SidewaysMarketStrategy(self.config),
            MarketRegime.HIGH_VOLATILITY: HighVolatilityStrategy(self.config),
        }

        # 보호 모드
        self.protection_level = ProtectionLevel.NORMAL
        self.consecutive_losses = 0
        self.daily_pnl = 0.0

        # 통계
        self.stats = {
            "total_signals": 0,
            "signals_by_regime": {r.value: 0 for r in MarketRegime},
            "regime_transitions": 0,
            "margin_blocks": 0,
            "defensive_mode_activations": 0
        }

        # AI 서비스 (나중에 설정)
        self.ai_service = None
        self._exchange = None

        logger.info(
            f"✅ {self.STRATEGY_NAME} v{self.VERSION} initialized: "
            f"Symbol={self.symbol}, AI={self.enable_ai}, "
            f"MaxMargin={MarginCapEnforcer.MAX_MARGIN_PERCENT}%"
        )

    def set_exchange(self, exchange):
        """거래소 클라이언트 설정"""
        self._exchange = exchange

    def set_ai_service(self, ai_service):
        """AI 서비스 설정"""
        self.ai_service = ai_service
        self.regime_classifier.set_ai_service(ai_service)
        logger.info("AI service connected to AdaptiveMarketRegimeFighter")

    async def analyze_and_decide(
        self,
        exchange,
        user_id: int,
        current_positions: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        시장 분석 및 거래 결정

        Args:
            exchange: CCXT 거래소 인스턴스
            user_id: 사용자 ID
            current_positions: 현재 포지션 목록

        Returns:
            거래 결정 딕셔너리
        """
        self.stats["total_signals"] += 1

        try:
            # 1. 마진 상태 확인
            margin_status = await self.margin_enforcer.get_margin_status(exchange)

            logger.info(
                f"[Margin] Total: ${margin_status['total_balance']:.2f}, "
                f"Used: {margin_status['usage_percent']:.1f}%, "
                f"Remaining: ${margin_status['remaining_margin']:.2f}"
            )

            # 2. 보호 모드 체크
            if self.protection_level == ProtectionLevel.LOCKDOWN:
                return self._create_hold_response(
                    "🔒 LOCKDOWN: 거래 중지 (연속 손실)",
                    {"protection_level": self.protection_level.value}
                )

            # 3. 시장 데이터 가져오기
            ohlcv = await exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=200)
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            current_price = float(df["close"].iloc[-1])

            # 4. 시장 체제 분류
            regime = await self.regime_classifier.classify_regime(df, current_price)
            self.stats["signals_by_regime"][regime.regime.value] += 1

            # 5. 서브 전략 선택 및 시그널 생성
            sub_strategy = self.sub_strategies.get(regime.regime)

            if sub_strategy is None:
                return self._create_hold_response(
                    f"Unknown regime: {regime.regime.value}",
                    {"regime": regime.regime.value}
                )

            # 현재 포지션 정보 정리
            current_position = None
            if current_positions and len(current_positions) > 0:
                pos = current_positions[0]
                current_position = {
                    "side": pos.get("side", "long"),
                    "entry_price": pos.get("entry_price", current_price),
                    "size": pos.get("size", 0)
                }

            # 서브 전략 시그널 생성
            signal = sub_strategy.generate_signal(
                df, current_price, regime.indicators, regime, current_position
            )

            # 6. 마진 한도 적용
            if signal.action in [TradingAction.ENTER_LONG, TradingAction.ENTER_SHORT]:
                allowed, adjusted_percent, msg = self.margin_enforcer.validate_position_size(
                    signal.position_size_percent, margin_status
                )

                if not allowed:
                    self.stats["margin_blocks"] += 1
                    return self._create_hold_response(msg, {"regime": regime.regime.value})

                signal.position_size_percent = adjusted_percent
                if signal.position_size_percent < signal.position_size_percent:
                    signal.warnings.append(msg)

            # 7. Defensive Mode 처리
            if signal.action == TradingAction.DEFENSIVE_MODE:
                self.stats["defensive_mode_activations"] += 1
                return self._create_hold_response(
                    signal.reasoning,
                    {
                        "regime": regime.regime.value,
                        "sub_strategy": signal.sub_strategy,
                        "defensive_mode": True,
                        "warnings": signal.warnings
                    }
                )

            # 8. 보호 모드에 따른 조정
            signal = self._apply_protection_adjustments(signal)

            # 9. 결과 반환
            return self._create_signal_response(signal, regime, margin_status)

        except Exception as e:
            logger.error(f"[{self.STRATEGY_NAME}] Error: {e}", exc_info=True)
            return self._create_hold_response(f"Error: {str(e)}", {})

    def _apply_protection_adjustments(self, signal: SubStrategySignal) -> SubStrategySignal:
        """보호 모드에 따른 시그널 조정"""
        if self.protection_level == ProtectionLevel.CAUTIOUS:
            signal.position_size_percent *= 0.7
            signal.leverage = max(3, signal.leverage - 2)
            signal.warnings.append("⚠️ CAUTIOUS 모드: 포지션 축소")

        elif self.protection_level == ProtectionLevel.DEFENSIVE:
            signal.position_size_percent *= 0.5
            signal.leverage = max(2, signal.leverage - 4)
            signal.warnings.append("🛡️ DEFENSIVE 모드: 리스크 감소")

        return signal

    def update_protection_mode(self, trade_result: Dict[str, Any]):
        """거래 결과에 따른 보호 모드 업데이트"""
        pnl = trade_result.get("pnl", 0)

        if pnl < 0:
            self.consecutive_losses += 1
            self.daily_pnl += pnl
        else:
            self.consecutive_losses = 0
            self.daily_pnl += pnl

        old_level = self.protection_level

        if self.consecutive_losses >= 5 or self.daily_pnl < -500:
            self.protection_level = ProtectionLevel.LOCKDOWN
        elif self.consecutive_losses >= 3:
            self.protection_level = ProtectionLevel.DEFENSIVE
        elif self.consecutive_losses >= 2:
            self.protection_level = ProtectionLevel.CAUTIOUS
        else:
            self.protection_level = ProtectionLevel.NORMAL

        if old_level != self.protection_level:
            logger.warning(
                f"[Protection] {old_level.value} → {self.protection_level.value}"
            )

    def reset_daily_stats(self):
        """일일 통계 초기화"""
        self.daily_pnl = 0.0
        if self.protection_level == ProtectionLevel.LOCKDOWN:
            self.protection_level = ProtectionLevel.DEFENSIVE
            logger.info("[Protection] Daily reset: LOCKDOWN → DEFENSIVE")

    def _create_hold_response(self, reason: str, extra: Dict) -> Dict[str, Any]:
        """HOLD 응답 생성"""
        return {
            "action": "hold",
            "confidence": 0.5,
            "reason": reason,
            "stop_loss": None,
            "take_profit": None,
            "leverage": 0,
            "position_size_percent": 0,
            "ai_powered": self.enable_ai,
            "strategy_type": self.STRATEGY_NAME,
            **extra
        }

    def _create_signal_response(
        self,
        signal: SubStrategySignal,
        regime: RegimeClassification,
        margin_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """시그널 응답 생성"""
        action_map = {
            TradingAction.ENTER_LONG: "buy",
            TradingAction.ENTER_SHORT: "sell",
            TradingAction.EXIT_LONG: "close",
            TradingAction.EXIT_SHORT: "close",
            TradingAction.HOLD: "hold",
            TradingAction.DEFENSIVE_MODE: "hold"
        }

        return {
            "action": action_map.get(signal.action, "hold"),
            "confidence": signal.confidence,
            "reason": signal.reasoning,
            "stop_loss": signal.stop_loss_percent,
            "take_profit": signal.take_profit_percent,
            "leverage": signal.leverage,
            "position_size_percent": signal.position_size_percent,
            "market_regime": regime.regime.value,
            "regime_confidence": regime.confidence,
            "sub_strategy": signal.sub_strategy,
            "support_level": regime.support_level,
            "resistance_level": regime.resistance_level,
            "volatility_percentile": regime.volatility_percentile,
            "trend_strength": regime.trend_strength,
            "ai_powered": regime.ai_enhanced,
            "strategy_type": self.STRATEGY_NAME,
            "warnings": signal.warnings,
            "margin_status": {
                "total_balance": margin_status["total_balance"],
                "usage_percent": margin_status["usage_percent"],
                "remaining_margin": margin_status["remaining_margin"]
            },
            "protection_level": self.protection_level.value
        }

    def get_statistics(self) -> Dict[str, Any]:
        """전략 통계 반환"""
        return {
            "strategy_name": self.STRATEGY_NAME,
            "version": self.VERSION,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "max_margin_percent": MarginCapEnforcer.MAX_MARGIN_PERCENT,
            "ai_enabled": self.enable_ai,
            "protection_level": self.protection_level.value,
            "consecutive_losses": self.consecutive_losses,
            "daily_pnl": self.daily_pnl,
            "current_regime": self.regime_classifier.current_regime.value,
            "candles_in_regime": self.regime_classifier.candles_in_regime,
            **self.stats
        }

    # =========================================================================
    # COMPATIBILITY METHODS (기존 인터페이스와 호환)
    # =========================================================================

    def generate_signal(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        동기 시그널 생성 (기존 인터페이스 호환)

        Note: 비동기 analyze_and_decide()를 권장합니다.
        """
        import asyncio

        if self._exchange is None:
            return {
                "action": "hold",
                "confidence": 0.0,
                "reason": "Exchange client not configured",
                "stop_loss": None,
                "take_profit": None,
                "strategy_type": self.STRATEGY_NAME
            }

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._async_generate_signal(current_price, candles, current_position)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self._async_generate_signal(current_price, candles, current_position)
                )
        except Exception as e:
            logger.error(f"Signal generation error: {e}")
            return {
                "action": "hold",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}",
                "stop_loss": None,
                "take_profit": None,
                "strategy_type": self.STRATEGY_NAME
            }

    async def _async_generate_signal(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict]
    ) -> Dict[str, Any]:
        """비동기 시그널 생성"""
        positions = []
        if current_position and current_position.get("size", 0) > 0:
            positions.append(current_position)

        return await self.analyze_and_decide(
            exchange=self._exchange,
            user_id=1,
            current_positions=positions
        )
