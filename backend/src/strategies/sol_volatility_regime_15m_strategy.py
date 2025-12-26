"""
SOL Volatility Regime 15-Minute Strategy (SOL 변동성 레짐 15분 전략)

🎯 핵심 특징:
1. SOL(솔라나) 전용 최적화 15분 타임프레임 전략
2. 4가지 변동성 레짐 감지 (COMPRESSION, EXPANSION, HIGH_VOLATILITY, EXHAUSTION)
3. ATR Percentile Ranking - 과거 대비 현재 변동성 순위
4. Volatility Contraction Pattern (VCP) - 브레이크아웃 예측
5. 다단계 익절 시스템 (1.5x, 2.5x, 4x ATR)

📊 Pine Script 기반 GainzAlgo 변동성 레짐 인디케이터 구현:
- ATR 밴드 (상단/중단/하단)
- 변동성 신호 및 추세 감지
- S/R 레벨 기반 진입/청산
- 동적 손절 및 다단계 익절

⚙️ 리스크 관리:
- 최대 마진 사용률: 35% (SOL 변동성 고려)
- 동적 레버리지: 5-12배 (변동성 기반)
- ATR 기반 동적 SL/TP (다단계)
- VCP 기반 진입 필터링
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

# AI Agents
from src.agents.market_regime.agent import MarketRegimeAgent
from src.agents.market_regime.models import RegimeType
from src.agents.signal_validator.agent import SignalValidatorAgent
from src.agents.signal_validator.models import ValidationResult
from src.agents.risk_monitor.agent import RiskMonitorAgent
from src.agents.portfolio_optimizer.agent import PortfolioOptimizationAgent

# Alias
PortfolioOptimizerAgent = PortfolioOptimizationAgent
MarketRegimeType = RegimeType

# Services
from src.services import get_ai_service_instance

logger = logging.getLogger(__name__)


# ============================================================================
# 변동성 레짐 열거형 (Pine Script 기반)
# ============================================================================

class VolatilityRegime(Enum):
    """변동성 레짐 (GainzAlgo 기반)"""
    COMPRESSION = "compression"       # 저변동성, 스퀴즈 (브레이크아웃 대기)
    EXPANSION = "expansion"           # 확장기, 브레이크아웃 진행
    HIGH_VOLATILITY = "high_volatility"  # 고변동성, 위험 구간
    EXHAUSTION = "exhaustion"         # 피로 구간, 추세 전환 예상


class TradingDecision(Enum):
    """거래 결정 유형"""
    ENTER_LONG = "enter_long"
    ENTER_SHORT = "enter_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    PARTIAL_EXIT = "partial_exit"     # 부분 청산 (다단계 익절)
    HOLD = "hold"
    EMERGENCY_EXIT = "emergency_exit"


class ProtectionMode(Enum):
    """보호 모드"""
    NORMAL = "normal"
    CAUTIOUS = "cautious"
    DEFENSIVE = "defensive"
    LOCKDOWN = "lockdown"


# ============================================================================
# 데이터 클래스
# ============================================================================

@dataclass
class PositionInfo:
    """포지션 정보"""
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    leverage: int
    margin_used: float
    liquidation_price: float
    entry_time: datetime
    holding_duration: Optional[timedelta] = None
    # 다단계 익절 추적
    tp1_hit: bool = False  # 1.5x ATR 익절 여부
    tp2_hit: bool = False  # 2.5x ATR 익절 여부


@dataclass
class UserSeedInfo:
    """사용자 시드 정보"""
    user_id: int
    total_balance: float
    available_for_trading: float   # 35% SOL 전략
    used_margin: float
    remaining_margin: float
    margin_usage_percent: float
    can_open_position: bool
    daily_pnl: float
    daily_pnl_percent: float


@dataclass
class SOLMarketAnalysis:
    """SOL 시장 분석 결과"""
    current_price: float
    regime_type: MarketRegimeType
    volatility_regime: VolatilityRegime  # Pine Script 기반 변동성 레짐
    atr: float                           # ATR 값
    atr_percent: float                   # ATR 백분율
    atr_percentile: float                # ATR Percentile (0-100)
    is_compression: bool                 # 스퀴즈 상태
    vcp_detected: bool                   # Volatility Contraction Pattern
    trend_strength: float                # ADX
    momentum: float                      # RSI
    bb_squeeze: float                    # BB 폭 (좁을수록 스퀴즈)
    volume_ratio: float
    confidence: float
    ai_enhanced: bool


@dataclass
class DynamicRiskParams:
    """동적 리스크 파라미터"""
    leverage: int
    position_size_percent: float
    stop_loss_percent: float       # ATR 기반 손절
    tp1_percent: float             # 1.5x ATR (부분 익절 30%)
    tp2_percent: float             # 2.5x ATR (부분 익절 40%)
    tp3_percent: float             # 4.0x ATR (최종 익절 30%)
    trailing_stop_percent: Optional[float] = None


@dataclass
class AutonomousDecision:
    """AI 자율 결정 결과"""
    decision: TradingDecision
    confidence: float
    position_size_percent: float
    target_leverage: int
    stop_loss_percent: float
    take_profit_percent: float     # 메인 TP (3단계 평균)
    tp1_percent: Optional[float] = None
    tp2_percent: Optional[float] = None
    tp3_percent: Optional[float] = None
    reasoning: str = ""
    market_analysis: Optional[SOLMarketAnalysis] = None
    ai_enhanced: bool = True
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# 35% 마진 한도 강제 모듈 (SOL용)
# ============================================================================

class MarginCapEnforcer35Pct:
    """
    35% 마진 한도 강제 모듈 (SOL 전략용)

    SOL은 ETH보다 변동성이 높으므로 35% 한도 적용
    """

    MAX_MARGIN_PERCENT = 35.0
    SAFETY_BUFFER_PERCENT = 2.0
    MIN_FREE_MARGIN_PERCENT = 3.0
    DAILY_LOSS_LIMIT_PERCENT = 5.0

    def __init__(self):
        self._effective_max = self.MAX_MARGIN_PERCENT - self.SAFETY_BUFFER_PERCENT
        logger.info(
            f"[MarginCapEnforcer35Pct] Initialized | "
            f"MAX={self.MAX_MARGIN_PERCENT}%, "
            f"EFFECTIVE={self._effective_max}%"
        )

    async def get_user_seed_info(
        self,
        exchange_client,
        user_id: int,
        current_positions: List[PositionInfo] = None,
        daily_pnl: float = 0.0
    ) -> UserSeedInfo:
        """사용자 시드 정보 조회"""
        try:
            balance = await exchange_client.fetch_balance()
            usdt_balance = balance.get("USDT", {})
            total_balance = float(usdt_balance.get("total", 0))
            used_balance = float(usdt_balance.get("used", 0))

            available_for_trading = total_balance * (self._effective_max / 100)

            used_margin = 0.0
            if current_positions:
                for pos in current_positions:
                    used_margin += pos.margin_used
            else:
                used_margin = min(used_balance, available_for_trading)

            margin_usage_percent = (used_margin / available_for_trading * 100) if available_for_trading > 0 else 100
            remaining_margin = max(0, available_for_trading - used_margin)
            daily_pnl_percent = (daily_pnl / total_balance * 100) if total_balance > 0 else 0

            min_margin_required = total_balance * (self.MIN_FREE_MARGIN_PERCENT / 100)
            daily_loss_exceeded = daily_pnl_percent < -self.DAILY_LOSS_LIMIT_PERCENT
            can_open = remaining_margin > min_margin_required and not daily_loss_exceeded

            return UserSeedInfo(
                user_id=user_id,
                total_balance=total_balance,
                available_for_trading=available_for_trading,
                used_margin=used_margin,
                remaining_margin=remaining_margin,
                margin_usage_percent=margin_usage_percent,
                can_open_position=can_open,
                daily_pnl=daily_pnl,
                daily_pnl_percent=daily_pnl_percent
            )

        except Exception as e:
            logger.error(f"[MarginCapEnforcer35Pct] Error: {e}")
            return UserSeedInfo(
                user_id=user_id,
                total_balance=0, available_for_trading=0,
                used_margin=0, remaining_margin=0,
                margin_usage_percent=100, can_open_position=False,
                daily_pnl=0, daily_pnl_percent=0
            )

    def validate_order(
        self,
        order_margin_required: float,
        seed_info: UserSeedInfo
    ) -> Tuple[bool, str, float]:
        """주문 검증"""
        if seed_info.daily_pnl_percent < -self.DAILY_LOSS_LIMIT_PERCENT:
            return (False, f"❌ 일일 손실 한도 초과", 0)

        projected_used = seed_info.used_margin + order_margin_required
        projected_percent = (projected_used / seed_info.available_for_trading * 100) if seed_info.available_for_trading > 0 else 100

        if projected_percent > 100:
            return (False, f"❌ 35% 마진 한도 초과", seed_info.remaining_margin)

        return (True, f"✅ 마진 허용: ${order_margin_required:.2f}", order_margin_required)


# ============================================================================
# SOL 변동성 레짐 분석기 (Pine Script 기반)
# ============================================================================

class SOLVolatilityRegimeAnalyzer:
    """
    Pine Script GainzAlgo Volatility Regimes 구현

    핵심 알고리즘:
    1. ATR Percentile - 과거 100 캔들 대비 현재 ATR 순위
    2. BB Squeeze 감지 - 볼린저 밴드 폭이 ATR보다 좁으면 스퀴즈
    3. VCP 패턴 - 변동성이 연속 축소되면 브레이크아웃 예상
    4. 4가지 레짐 분류
    """

    ATR_PERIOD = 14
    ATR_PERCENTILE_LOOKBACK = 100
    BB_PERIOD = 20
    BB_STD = 2.0
    EMA_SHORT = 9
    EMA_MID = 21
    EMA_LONG = 55
    ADX_PERIOD = 14
    RSI_PERIOD = 14

    # 레짐 임계값 (AI 자율 매매용 - 완화됨)
    COMPRESSION_THRESHOLD = 30      # ATR percentile < 30% (스퀴즈)
    EXPANSION_THRESHOLD = 50        # ATR percentile > 50% (확장)
    HIGH_VOL_THRESHOLD = 95         # ATR percentile > 95% (극단적 변동성만 회피)
    EXHAUSTION_CANDLE_COUNT = 10    # 연속 같은 방향 캔들 (더 관대하게)

    @classmethod
    def calculate_all_indicators(cls, df: pd.DataFrame) -> pd.DataFrame:
        """모든 지표 계산"""
        df = df.copy()

        # === ATR ===
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=cls.ATR_PERIOD).mean()
        df["atr_percent"] = df["atr"] / df["close"] * 100

        # === ATR Percentile (핵심!) ===
        # 현재 ATR이 과거 100개 중 몇 번째인지 (0-100%)
        df["atr_percentile"] = df["atr"].rolling(window=cls.ATR_PERCENTILE_LOOKBACK).apply(
            lambda x: (x.iloc[-1] >= x).sum() / len(x) * 100 if len(x) > 0 else 50,
            raw=False
        )

        # === Bollinger Bands ===
        df["bb_middle"] = df["close"].rolling(window=cls.BB_PERIOD).mean()
        bb_std = df["close"].rolling(window=cls.BB_PERIOD).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * cls.BB_STD)
        df["bb_lower"] = df["bb_middle"] - (bb_std * cls.BB_STD)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"] * 100
        df["bb_percent"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        # === BB Squeeze Detection ===
        # BB 폭이 ATR×2 보다 좁으면 스퀴즈
        df["bb_squeeze"] = df["bb_width"] < (df["atr_percent"] * 2)

        # === EMA ===
        df["ema_9"] = df["close"].ewm(span=cls.EMA_SHORT, adjust=False).mean()
        df["ema_21"] = df["close"].ewm(span=cls.EMA_MID, adjust=False).mean()
        df["ema_55"] = df["close"].ewm(span=cls.EMA_LONG, adjust=False).mean()

        # === RSI ===
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=cls.RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=cls.RSI_PERIOD).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(50)

        # === ADX ===
        df = cls._calculate_adx(df)

        # === MACD ===
        exp12 = df["close"].ewm(span=12, adjust=False).mean()
        exp26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = exp12 - exp26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # === Volume ===
        df["volume_sma"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma"]

        # === VCP Detection (Volatility Contraction Pattern) ===
        df["vcp"] = cls._detect_vcp(df)

        # === Exhaustion Detection ===
        df["exhaustion"] = cls._detect_exhaustion(df)

        return df

    @classmethod
    def _calculate_adx(cls, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """ADX 계산"""
        plus_dm = df["high"].diff()
        minus_dm = -df["low"].diff()

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr = pd.concat([
            df["high"] - df["low"],
            abs(df["high"] - df["close"].shift()),
            abs(df["low"] - df["close"].shift())
        ], axis=1).max(axis=1)

        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)
        df["adx"] = dx.rolling(window=period).mean()
        df["plus_di"] = plus_di
        df["minus_di"] = minus_di

        return df

    @classmethod
    def _detect_vcp(cls, df: pd.DataFrame) -> pd.Series:
        """
        Volatility Contraction Pattern 감지

        연속 3개 캔들의 레인지가 줄어들면 VCP
        (브레이크아웃 직전 신호)
        """
        ranges = df["high"] - df["low"]

        # 3개 연속 레인지 축소
        vcp = (
            (ranges < ranges.shift(1)) &
            (ranges.shift(1) < ranges.shift(2)) &
            (df["atr_percentile"] < 40)  # 낮은 변동성 구간에서만
        )

        return vcp.fillna(False)

    @classmethod
    def _detect_exhaustion(cls, df: pd.DataFrame) -> pd.Series:
        """
        Exhaustion (피로) 감지

        같은 방향 캔들이 연속으로 나오고 변동성이 감소하면 피로
        """
        # 캔들 방향
        direction = (df["close"] > df["open"]).astype(int) - (df["close"] < df["open"]).astype(int)

        # 연속 같은 방향 카운트
        def count_consecutive(series):
            result = []
            count = 1
            prev = None
            for val in series:
                if val == prev:
                    count += 1
                else:
                    count = 1
                result.append(count)
                prev = val
            return pd.Series(result, index=series.index)

        consecutive = count_consecutive(direction)

        # 8개 이상 연속 + RSI 극단값
        exhaustion = (
            (consecutive >= cls.EXHAUSTION_CANDLE_COUNT) &
            ((df["rsi"] > 75) | (df["rsi"] < 25))
        )

        return exhaustion.fillna(False)

    @classmethod
    def detect_volatility_regime(
        cls,
        atr_percentile: float,
        bb_squeeze: bool,
        vcp: bool,
        exhaustion: bool,
        rsi: float
    ) -> VolatilityRegime:
        """
        변동성 레짐 판단 (Pine Script 핵심 로직)

        Args:
            atr_percentile: ATR 백분위 (0-100)
            bb_squeeze: BB 스퀴즈 여부
            vcp: VCP 패턴 감지 여부
            exhaustion: 피로 감지 여부
            rsi: RSI 값

        Returns:
            VolatilityRegime
        """
        # 1. 피로 구간 체크 (최우선)
        if exhaustion:
            return VolatilityRegime.EXHAUSTION

        # 2. 고변동성 구간
        if atr_percentile > cls.HIGH_VOL_THRESHOLD:
            return VolatilityRegime.HIGH_VOLATILITY

        # 3. 확장 구간 (브레이크아웃 진행)
        if atr_percentile > cls.EXPANSION_THRESHOLD:
            return VolatilityRegime.EXPANSION

        # 4. 압축 구간 (스퀴즈)
        if atr_percentile < cls.COMPRESSION_THRESHOLD or bb_squeeze or vcp:
            return VolatilityRegime.COMPRESSION

        # 5. 기본값: 확장
        return VolatilityRegime.EXPANSION


# ============================================================================
# 동적 리스크 파라미터 계산기 (다단계 익절)
# ============================================================================

class SOLDynamicRiskCalculator:
    """
    SOL 동적 리스크 파라미터 계산기

    다단계 익절 시스템:
    - TP1: 1.5x ATR (30% 포지션 청산)
    - TP2: 2.5x ATR (40% 포지션 청산)
    - TP3: 4.0x ATR (나머지 30% 청산)
    """

    MIN_LEVERAGE = 5
    MAX_LEVERAGE = 12

    # ATR 기반 SL/TP 배수
    ATR_SL_MULTIPLIER = 1.5
    ATR_TP1_MULTIPLIER = 1.5   # 30% 청산
    ATR_TP2_MULTIPLIER = 2.5   # 40% 청산
    ATR_TP3_MULTIPLIER = 4.0   # 30% 청산

    @classmethod
    def calculate_dynamic_params(
        cls,
        volatility_regime: VolatilityRegime,
        atr_percentile: float,
        atr_percent: float,
        regime_type: MarketRegimeType,
        protection_mode: ProtectionMode
    ) -> DynamicRiskParams:
        """동적 리스크 파라미터 계산"""

        # === 1. 레버리지 결정 (변동성 레짐 기반) ===
        if volatility_regime == VolatilityRegime.HIGH_VOLATILITY:
            base_leverage = cls.MIN_LEVERAGE
        elif volatility_regime == VolatilityRegime.EXHAUSTION:
            base_leverage = cls.MIN_LEVERAGE + 1
        elif volatility_regime == VolatilityRegime.COMPRESSION:
            # 스퀴즈 구간: 브레이크아웃 대비 중간 레버리지
            base_leverage = 8
        else:  # EXPANSION
            base_leverage = 10

        # 추세 강도에 따른 조정
        if regime_type == MarketRegimeType.TRENDING_UP or regime_type == MarketRegimeType.TRENDING_DOWN:
            base_leverage = min(cls.MAX_LEVERAGE, base_leverage + 1)
        elif regime_type == MarketRegimeType.RANGING:
            base_leverage = max(cls.MIN_LEVERAGE, base_leverage - 2)

        # 보호 모드 조정
        if protection_mode == ProtectionMode.CAUTIOUS:
            base_leverage = max(cls.MIN_LEVERAGE, base_leverage - 2)
        elif protection_mode == ProtectionMode.DEFENSIVE:
            base_leverage = cls.MIN_LEVERAGE

        # === 2. ATR 기반 SL/TP 계산 ===
        # 변동성 레짐에 따라 ATR 배수 조정
        sl_multiplier = cls.ATR_SL_MULTIPLIER
        if volatility_regime == VolatilityRegime.HIGH_VOLATILITY:
            sl_multiplier = 2.0  # 고변동성엔 더 넓은 SL
        elif volatility_regime == VolatilityRegime.COMPRESSION:
            sl_multiplier = 1.2  # 스퀴즈엔 타이트한 SL

        stop_loss_percent = atr_percent * sl_multiplier
        tp1_percent = atr_percent * cls.ATR_TP1_MULTIPLIER
        tp2_percent = atr_percent * cls.ATR_TP2_MULTIPLIER
        tp3_percent = atr_percent * cls.ATR_TP3_MULTIPLIER

        # SL/TP 범위 제한
        stop_loss_percent = max(0.8, min(4.0, stop_loss_percent))
        tp1_percent = max(1.0, min(3.0, tp1_percent))
        tp2_percent = max(2.0, min(5.0, tp2_percent))
        tp3_percent = max(3.0, min(8.0, tp3_percent))

        # === 3. 포지션 크기 결정 ===
        if volatility_regime == VolatilityRegime.HIGH_VOLATILITY:
            position_size_percent = 25.0
        elif volatility_regime == VolatilityRegime.EXHAUSTION:
            position_size_percent = 30.0
        elif volatility_regime == VolatilityRegime.COMPRESSION:
            # VCP/스퀴즈: 중간 사이즈, 브레이크아웃 시 추가
            position_size_percent = 50.0
        else:
            position_size_percent = 70.0

        # 보호 모드 조정
        if protection_mode == ProtectionMode.CAUTIOUS:
            position_size_percent *= 0.5
        elif protection_mode == ProtectionMode.DEFENSIVE:
            position_size_percent *= 0.3

        # === 4. 트레일링 스탑 ===
        trailing_stop = None
        if regime_type in [MarketRegimeType.TRENDING_UP, MarketRegimeType.TRENDING_DOWN]:
            trailing_stop = stop_loss_percent * 1.5

        return DynamicRiskParams(
            leverage=int(base_leverage),
            position_size_percent=min(80.0, position_size_percent),
            stop_loss_percent=stop_loss_percent,
            tp1_percent=tp1_percent,
            tp2_percent=tp2_percent,
            tp3_percent=tp3_percent,
            trailing_stop_percent=trailing_stop
        )


# ============================================================================
# SOL 변동성 레짐 15분 전략 메인 클래스
# ============================================================================

class SOLVolatilityRegime15mStrategy:
    """
    SOL Volatility Regime 15-Minute Strategy

    Pine Script GainzAlgo Volatility Regimes 인디케이터 기반 전략
    """

    SYMBOL = "SOL/USDT"
    SYMBOL_BITGET = "SOLUSDT"
    TIMEFRAME = "15m"
    MIN_CONFIDENCE = 0.60

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enable_ai = self.config.get("enable_ai", True)
        self.timeframe = self.config.get("timeframe", self.TIMEFRAME)

        # 35% 마진 한도
        self.margin_enforcer = MarginCapEnforcer35Pct()

        # AI 서비스
        try:
            self.ai_service = get_ai_service_instance() if self.enable_ai else None
        except Exception as e:
            logger.warning(f"AI service not available: {e}")
            self.ai_service = None
            self.enable_ai = False

        # AI 에이전트 초기화
        self._init_agents()

        # 사용자 상태
        self.user_states: Dict[int, Dict[str, Any]] = {}

        # 통계
        self.global_stats = {
            "total_decisions": 0,
            "total_entries": 0,
            "total_exits": 0,
            "compression_entries": 0,
            "expansion_entries": 0,
            "vcp_triggers": 0,
            "partial_exits": 0,
            "ai_analysis_count": 0
        }

        logger.info(
            f"✅ SOL Volatility Regime 15m Strategy initialized | "
            f"Symbol={self.SYMBOL}, Timeframe={self.TIMEFRAME}, "
            f"AI={self.enable_ai}, MaxMargin={MarginCapEnforcer35Pct.MAX_MARGIN_PERCENT}%"
        )

    def _init_agents(self):
        """AI 에이전트 초기화"""
        if self.enable_ai and self.ai_service:
            try:
                self.market_regime_agent = MarketRegimeAgent(
                    agent_id="sol_market_regime",
                    name="SOL Market Regime Agent",
                    config={
                        "enable_ai": True,
                        "atr_period": 14,
                        "adx_period": 14,
                        "volatility_threshold": 0.035,  # SOL은 더 높은 변동성
                        "symbol": "SOLUSDT",
                    },
                    ai_service=self.ai_service
                )

                self.signal_validator = SignalValidatorAgent(
                    agent_id="sol_signal_validator",
                    name="SOL Signal Validator Agent",
                    config={
                        "enable_ai": True,
                        "min_passed_rules": 5,
                        "critical_rules": ["price_sanity", "volatility_check"],
                    },
                    ai_service=self.ai_service
                )

                self.risk_monitor = RiskMonitorAgent(
                    agent_id="sol_risk_monitor",
                    name="SOL Risk Monitor Agent",
                    config={
                        "max_position_loss_percent": 4.0,
                        "max_daily_loss": 400,
                        "max_drawdown_percent": 10.0,
                    }
                )

                self.portfolio_optimizer = PortfolioOptimizerAgent(
                    agent_id="sol_portfolio_optimizer",
                    name="SOL Portfolio Optimizer Agent",
                    config={
                        "enable_ai": True,
                        "max_allocation_percent": 35.0,
                        "rebalancing_threshold": 5.0,
                    },
                    ai_service=self.ai_service
                )

                logger.info("✅ All 4 AI agents initialized for SOL volatility regime trading")
            except Exception as e:
                logger.error(f"Failed to initialize AI agents: {e}")
                self._set_agents_none()
        else:
            self._set_agents_none()
            logger.warning("⚠️ AI agents disabled or not available")

    def _set_agents_none(self):
        self.market_regime_agent = None
        self.signal_validator = None
        self.risk_monitor = None
        self.portfolio_optimizer = None

    def _get_user_state(self, user_id: int) -> Dict[str, Any]:
        """사용자별 상태 가져오기"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                "protection_mode": ProtectionMode.NORMAL,
                "consecutive_losses": 0,
                "daily_pnl": 0.0,
                "last_trade_time": None,
                "trade_count_today": 0,
                "last_reset_date": datetime.now(timezone.utc).date(),
                "tp1_triggered": False,
                "tp2_triggered": False
            }

        state = self.user_states[user_id]
        today = datetime.now(timezone.utc).date()
        if state["last_reset_date"] != today:
            state["daily_pnl"] = 0.0
            state["trade_count_today"] = 0
            state["last_reset_date"] = today
            state["tp1_triggered"] = False
            state["tp2_triggered"] = False
            if state["protection_mode"] == ProtectionMode.LOCKDOWN:
                state["protection_mode"] = ProtectionMode.DEFENSIVE

        return state

    async def analyze_and_decide(
        self,
        exchange,
        user_id: int,
        current_positions: List[PositionInfo] = None
    ) -> AutonomousDecision:
        """
        자율 분석 및 거래 결정 (메인 진입점)
        """
        self.global_stats["total_decisions"] += 1
        user_state = self._get_user_state(user_id)

        try:
            # 1. 시드 정보 조회
            seed_info = await self.margin_enforcer.get_user_seed_info(
                exchange, user_id, current_positions, user_state["daily_pnl"]
            )

            logger.info(
                f"[SOL User {user_id}] Seed: ${seed_info.total_balance:.2f} | "
                f"35% Limit: ${seed_info.available_for_trading:.2f} | "
                f"Used: {seed_info.margin_usage_percent:.1f}%"
            )

            # 2. 보호 모드 체크
            if user_state["protection_mode"] == ProtectionMode.LOCKDOWN:
                return self._create_hold_decision(
                    "🔒 LOCKDOWN: 거래 중지",
                    warnings=["Trading locked"]
                )

            if not seed_info.can_open_position and not current_positions:
                return self._create_hold_decision(
                    "⚠️ 35% 마진 한도 도달",
                    warnings=["35% margin limit reached"]
                )

            # 3. 시장 데이터 가져오기
            ohlcv = await exchange.fetch_ohlcv(self.SYMBOL, self.timeframe, limit=150)
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            current_price = float(df["close"].iloc[-1])

            # 4. 지표 계산 (Pine Script 로직)
            df = SOLVolatilityRegimeAnalyzer.calculate_all_indicators(df)

            # 5. 시장 분석
            market_analysis = await self._analyze_sol_market(exchange, df, current_price)

            # 6. 동적 리스크 파라미터
            risk_params = SOLDynamicRiskCalculator.calculate_dynamic_params(
                volatility_regime=market_analysis.volatility_regime,
                atr_percentile=market_analysis.atr_percentile,
                atr_percent=market_analysis.atr_percent,
                regime_type=market_analysis.regime_type,
                protection_mode=user_state["protection_mode"]
            )

            logger.info(
                f"[SOL Analysis] Regime: {market_analysis.regime_type.value} | "
                f"VolRegime: {market_analysis.volatility_regime.value} | "
                f"ATR%tile: {market_analysis.atr_percentile:.1f} | "
                f"VCP: {market_analysis.vcp_detected} | "
                f"Leverage: {risk_params.leverage}x"
            )

            # 7. 포지션 보유 시 청산 조건 확인
            if current_positions:
                exit_decision = await self._check_exit_conditions(
                    current_positions, df, current_price, market_analysis, risk_params, user_state
                )
                if exit_decision.decision != TradingDecision.HOLD:
                    return exit_decision

            # 8. 신규 진입 불가능하면 HOLD
            if not seed_info.can_open_position:
                return self._create_hold_decision(
                    "포지션 보유 중 - 추가 진입 불가",
                    market_analysis=market_analysis
                )

            # 9. 진입 결정
            entry_decision = await self._make_entry_decision(
                df, current_price, market_analysis, risk_params, seed_info, user_state
            )

            # 10. AI 신호 검증
            if entry_decision.decision not in [TradingDecision.HOLD]:
                entry_decision = await self._validate_decision(entry_decision, current_price, market_analysis)

            # 11. 마진 한도 강제
            entry_decision = self._enforce_margin_limit(entry_decision, seed_info, current_price, risk_params.leverage)

            # 12. 통계 업데이트
            if entry_decision.decision in [TradingDecision.ENTER_LONG, TradingDecision.ENTER_SHORT]:
                self.global_stats["total_entries"] += 1
                if market_analysis.volatility_regime == VolatilityRegime.COMPRESSION:
                    self.global_stats["compression_entries"] += 1
                if market_analysis.vcp_detected:
                    self.global_stats["vcp_triggers"] += 1

            logger.info(
                f"[SOL Decision] {entry_decision.decision.value} | "
                f"Confidence: {entry_decision.confidence:.1%} | "
                f"TP1: {entry_decision.tp1_percent:.2f}% | "
                f"TP2: {entry_decision.tp2_percent:.2f}% | "
                f"TP3: {entry_decision.tp3_percent:.2f}%"
            )

            return entry_decision

        except Exception as e:
            logger.error(f"[SOL Strategy] Analysis failed for user {user_id}: {e}", exc_info=True)
            return self._create_hold_decision(f"Analysis error: {str(e)}")

    async def _analyze_sol_market(
        self,
        exchange,
        df: pd.DataFrame,
        current_price: float
    ) -> SOLMarketAnalysis:
        """SOL 시장 분석"""
        latest = df.iloc[-1]

        # AI 시장 체제 분석
        regime_type = MarketRegimeType.RANGING
        confidence = 0.6
        ai_enhanced = False

        if self.market_regime_agent:
            try:
                bitget_symbol = self.SYMBOL.replace("/", "")
                regime = await self.market_regime_agent.analyze_market_realtime({
                    "symbol": bitget_symbol,
                    "exchange": exchange,
                    "timeframe": self.timeframe
                })
                regime_type = regime.regime_type
                confidence = regime.confidence
                ai_enhanced = True
                self.global_stats["ai_analysis_count"] += 1
            except Exception as e:
                logger.warning(f"AI market regime analysis failed: {e}")
                regime_type = self._detect_regime_rule_based(latest)
        else:
            regime_type = self._detect_regime_rule_based(latest)

        # 변동성 레짐 분석 (Pine Script 핵심)
        atr_percentile = float(latest.get("atr_percentile", 50))
        bb_squeeze = bool(latest.get("bb_squeeze", False))
        vcp = bool(latest.get("vcp", False))
        exhaustion = bool(latest.get("exhaustion", False))
        rsi = float(latest.get("rsi", 50))

        volatility_regime = SOLVolatilityRegimeAnalyzer.detect_volatility_regime(
            atr_percentile=atr_percentile,
            bb_squeeze=bb_squeeze,
            vcp=vcp,
            exhaustion=exhaustion,
            rsi=rsi
        )

        return SOLMarketAnalysis(
            current_price=current_price,
            regime_type=regime_type,
            volatility_regime=volatility_regime,
            atr=float(latest.get("atr", 0)),
            atr_percent=float(latest.get("atr_percent", 2)),
            atr_percentile=atr_percentile,
            is_compression=volatility_regime == VolatilityRegime.COMPRESSION,
            vcp_detected=vcp,
            trend_strength=float(latest.get("adx", 20)),
            momentum=rsi,
            bb_squeeze=float(latest.get("bb_width", 5)),
            volume_ratio=float(latest.get("volume_ratio", 1.0)),
            confidence=confidence,
            ai_enhanced=ai_enhanced
        )

    def _detect_regime_rule_based(self, latest) -> MarketRegimeType:
        """규칙 기반 시장 체제 감지"""
        ema_21 = latest.get("ema_21", 0)
        ema_55 = latest.get("ema_55", 0)
        adx = latest.get("adx", 20)
        atr_percent = latest.get("atr_percent", 2)

        if atr_percent > 5:
            return MarketRegimeType.HIGH_VOLATILITY

        if adx > 25:
            if ema_21 > ema_55 * 1.01:
                return MarketRegimeType.TRENDING_UP
            elif ema_21 < ema_55 * 0.99:
                return MarketRegimeType.TRENDING_DOWN

        return MarketRegimeType.RANGING

    async def _check_exit_conditions(
        self,
        current_positions: List[PositionInfo],
        df: pd.DataFrame,
        current_price: float,
        market_analysis: SOLMarketAnalysis,
        risk_params: DynamicRiskParams,
        user_state: Dict[str, Any]
    ) -> AutonomousDecision:
        """청산 조건 확인 (다단계 익절 포함)"""
        pos = current_positions[0]
        latest = df.iloc[-1]

        pnl_percent = pos.unrealized_pnl_percent
        is_long = pos.side == "long"

        # === 손절 조건 ===
        if pnl_percent < -risk_params.stop_loss_percent:
            self.global_stats["total_exits"] += 1
            return AutonomousDecision(
                decision=TradingDecision.EXIT_LONG if is_long else TradingDecision.EXIT_SHORT,
                confidence=0.95,
                position_size_percent=100.0,
                target_leverage=risk_params.leverage,
                stop_loss_percent=risk_params.stop_loss_percent,
                take_profit_percent=risk_params.tp3_percent,
                reasoning=f"🛑 Stop Loss: {pnl_percent:.2f}% < -{risk_params.stop_loss_percent:.2f}%",
                market_analysis=market_analysis,
                warnings=["Stop loss triggered"]
            )

        # === 다단계 익절 ===
        # TP1: 1.5x ATR (30% 청산)
        if pnl_percent >= risk_params.tp1_percent and not user_state.get("tp1_triggered"):
            user_state["tp1_triggered"] = True
            self.global_stats["partial_exits"] += 1
            return AutonomousDecision(
                decision=TradingDecision.PARTIAL_EXIT,
                confidence=0.85,
                position_size_percent=30.0,  # 30% 청산
                target_leverage=risk_params.leverage,
                stop_loss_percent=risk_params.stop_loss_percent,
                take_profit_percent=risk_params.tp1_percent,
                tp1_percent=risk_params.tp1_percent,
                tp2_percent=risk_params.tp2_percent,
                tp3_percent=risk_params.tp3_percent,
                reasoning=f"✅ TP1 Hit: {pnl_percent:.2f}% >= {risk_params.tp1_percent:.2f}% (30% exit)",
                market_analysis=market_analysis
            )

        # TP2: 2.5x ATR (40% 청산)
        if pnl_percent >= risk_params.tp2_percent and not user_state.get("tp2_triggered"):
            user_state["tp2_triggered"] = True
            self.global_stats["partial_exits"] += 1
            return AutonomousDecision(
                decision=TradingDecision.PARTIAL_EXIT,
                confidence=0.88,
                position_size_percent=40.0,  # 40% 청산
                target_leverage=risk_params.leverage,
                stop_loss_percent=risk_params.stop_loss_percent,
                take_profit_percent=risk_params.tp2_percent,
                tp1_percent=risk_params.tp1_percent,
                tp2_percent=risk_params.tp2_percent,
                tp3_percent=risk_params.tp3_percent,
                reasoning=f"✅ TP2 Hit: {pnl_percent:.2f}% >= {risk_params.tp2_percent:.2f}% (40% exit)",
                market_analysis=market_analysis
            )

        # TP3: 4.0x ATR (최종 30% 청산)
        if pnl_percent >= risk_params.tp3_percent:
            self.global_stats["total_exits"] += 1
            user_state["tp1_triggered"] = False
            user_state["tp2_triggered"] = False
            return AutonomousDecision(
                decision=TradingDecision.EXIT_LONG if is_long else TradingDecision.EXIT_SHORT,
                confidence=0.92,
                position_size_percent=100.0,  # 나머지 전체 청산
                target_leverage=risk_params.leverage,
                stop_loss_percent=risk_params.stop_loss_percent,
                take_profit_percent=risk_params.tp3_percent,
                tp1_percent=risk_params.tp1_percent,
                tp2_percent=risk_params.tp2_percent,
                tp3_percent=risk_params.tp3_percent,
                reasoning=f"🎯 TP3 Final: {pnl_percent:.2f}% >= {risk_params.tp3_percent:.2f}% (full exit)",
                market_analysis=market_analysis
            )

        # === 피로/반전 신호 ===
        if market_analysis.volatility_regime == VolatilityRegime.EXHAUSTION:
            if pnl_percent > 1.0:
                return AutonomousDecision(
                    decision=TradingDecision.EXIT_LONG if is_long else TradingDecision.EXIT_SHORT,
                    confidence=0.75,
                    position_size_percent=100.0,
                    target_leverage=risk_params.leverage,
                    stop_loss_percent=risk_params.stop_loss_percent,
                    take_profit_percent=pnl_percent,
                    reasoning=f"⚠️ Exhaustion detected - securing {pnl_percent:.2f}% profit",
                    market_analysis=market_analysis,
                    warnings=["Exhaustion regime - trend reversal expected"]
                )

        return self._create_hold_decision(
            f"포지션 유지 (PnL: {pnl_percent:.2f}%)",
            market_analysis=market_analysis
        )

    async def _make_entry_decision(
        self,
        df: pd.DataFrame,
        current_price: float,
        market_analysis: SOLMarketAnalysis,
        risk_params: DynamicRiskParams,
        seed_info: UserSeedInfo,
        user_state: Dict[str, Any]
    ) -> AutonomousDecision:
        """진입 결정 (변동성 레짐 기반)"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        ema_9 = latest["ema_9"]
        ema_21 = latest["ema_21"]
        ema_55 = latest["ema_55"]
        rsi = latest["rsi"]
        macd_hist = latest["macd_hist"]
        prev_macd_hist = prev["macd_hist"]
        volume_ratio = market_analysis.volume_ratio
        adx = market_analysis.trend_strength

        # =======================================================================
        # AI 자율 매매 진입 로직 (적극적 진입)
        # =======================================================================

        # === 1. 추세 강도 기반 진입 (모든 레짐에서 적용) ===
        # 강한 상승 추세: EMA 정배열 + RSI 모멘텀
        is_strong_uptrend = (
            ema_9 > ema_21 and
            ema_21 > ema_55 and
            rsi > 45 and rsi < 75
        )

        # 강한 하락 추세: EMA 역배열 + RSI 모멘텀
        is_strong_downtrend = (
            ema_9 < ema_21 and
            ema_21 < ema_55 and
            rsi < 55 and rsi > 25
        )

        # MACD 크로스 감지
        macd_bullish_cross = macd_hist > 0 and prev_macd_hist <= 0
        macd_bearish_cross = macd_hist < 0 and prev_macd_hist >= 0

        # === 2. COMPRESSION 레짐: 스퀴즈 브레이크아웃 ===
        if market_analysis.volatility_regime == VolatilityRegime.COMPRESSION:
            # 스퀴즈 상태에서 방향성 있으면 진입 (VCP 여부 상관없이)
            if ema_9 > ema_21 and (macd_hist > 0 or rsi > 55):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.72,
                    position_size_percent=risk_params.position_size_percent,
                    target_leverage=risk_params.leverage,
                    stop_loss_percent=risk_params.stop_loss_percent,
                    take_profit_percent=risk_params.tp3_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📈 Compression Breakout LONG: Low volatility squeeze + bullish bias",
                    market_analysis=market_analysis
                )
            elif ema_9 < ema_21 and (macd_hist < 0 or rsi < 45):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.72,
                    position_size_percent=risk_params.position_size_percent,
                    target_leverage=risk_params.leverage,
                    stop_loss_percent=risk_params.stop_loss_percent,
                    take_profit_percent=risk_params.tp3_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📉 Compression Breakout SHORT: Low volatility squeeze + bearish bias",
                    market_analysis=market_analysis
                )

        # === 3. EXPANSION 레짐: 추세 추종 (완화된 조건) ===
        elif market_analysis.volatility_regime == VolatilityRegime.EXPANSION:
            # 상승 추세 진입 (ADX 조건 완화: 20 이상이면 OK)
            if is_strong_uptrend and adx > 20:
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.68,
                    position_size_percent=risk_params.position_size_percent * 0.85,
                    target_leverage=risk_params.leverage,
                    stop_loss_percent=risk_params.stop_loss_percent,
                    take_profit_percent=risk_params.tp3_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📈 Expansion LONG: Uptrend confirmed (ADX={adx:.1f}, RSI={rsi:.1f})",
                    market_analysis=market_analysis
                )
            elif is_strong_downtrend and adx > 20:
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.68,
                    position_size_percent=risk_params.position_size_percent * 0.85,
                    target_leverage=risk_params.leverage,
                    stop_loss_percent=risk_params.stop_loss_percent,
                    take_profit_percent=risk_params.tp3_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📉 Expansion SHORT: Downtrend confirmed (ADX={adx:.1f}, RSI={rsi:.1f})",
                    market_analysis=market_analysis
                )
            # MACD 크로스 기반 진입 (약한 추세에서도)
            elif macd_bullish_cross and rsi > 45:
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.62,
                    position_size_percent=risk_params.position_size_percent * 0.6,
                    target_leverage=max(5, risk_params.leverage - 2),
                    stop_loss_percent=risk_params.stop_loss_percent * 1.2,
                    take_profit_percent=risk_params.tp2_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📈 MACD Cross LONG: Bullish momentum (RSI={rsi:.1f})",
                    market_analysis=market_analysis
                )
            elif macd_bearish_cross and rsi < 55:
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.62,
                    position_size_percent=risk_params.position_size_percent * 0.6,
                    target_leverage=max(5, risk_params.leverage - 2),
                    stop_loss_percent=risk_params.stop_loss_percent * 1.2,
                    take_profit_percent=risk_params.tp2_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📉 MACD Cross SHORT: Bearish momentum (RSI={rsi:.1f})",
                    market_analysis=market_analysis
                )

        # === 4. HIGH_VOLATILITY: 추세 방향으로만 진입 (작은 사이즈) ===
        elif market_analysis.volatility_regime == VolatilityRegime.HIGH_VOLATILITY:
            # 강한 추세가 있으면 진입 허용 (포지션 크기 축소)
            if is_strong_uptrend and adx > 30 and macd_hist > 0:
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.60,
                    position_size_percent=risk_params.position_size_percent * 0.5,  # 50% 축소
                    target_leverage=max(5, risk_params.leverage - 3),  # 레버리지 낮춤
                    stop_loss_percent=risk_params.stop_loss_percent * 1.5,  # SL 넓힘
                    take_profit_percent=risk_params.tp2_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📈 High Vol LONG: Strong trend in volatile market (ADX={adx:.1f})",
                    market_analysis=market_analysis,
                    warnings=["High volatility - reduced position size"]
                )
            elif is_strong_downtrend and adx > 30 and macd_hist < 0:
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.60,
                    position_size_percent=risk_params.position_size_percent * 0.5,
                    target_leverage=max(5, risk_params.leverage - 3),
                    stop_loss_percent=risk_params.stop_loss_percent * 1.5,
                    take_profit_percent=risk_params.tp2_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📉 High Vol SHORT: Strong trend in volatile market (ADX={adx:.1f})",
                    market_analysis=market_analysis,
                    warnings=["High volatility - reduced position size"]
                )

        # === 5. EXHAUSTION: 역추세 진입 기회 ===
        elif market_analysis.volatility_regime == VolatilityRegime.EXHAUSTION:
            # RSI 극단값에서 반전 진입
            if rsi < 25 and macd_bullish_cross:
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.58,
                    position_size_percent=risk_params.position_size_percent * 0.4,
                    target_leverage=5,
                    stop_loss_percent=risk_params.stop_loss_percent * 1.5,
                    take_profit_percent=risk_params.tp1_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📈 Exhaustion Reversal LONG: Oversold bounce (RSI={rsi:.1f})",
                    market_analysis=market_analysis,
                    warnings=["Counter-trend entry - small size"]
                )
            elif rsi > 75 and macd_bearish_cross:
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.58,
                    position_size_percent=risk_params.position_size_percent * 0.4,
                    target_leverage=5,
                    stop_loss_percent=risk_params.stop_loss_percent * 1.5,
                    take_profit_percent=risk_params.tp1_percent,
                    tp1_percent=risk_params.tp1_percent,
                    tp2_percent=risk_params.tp2_percent,
                    tp3_percent=risk_params.tp3_percent,
                    reasoning=f"📉 Exhaustion Reversal SHORT: Overbought drop (RSI={rsi:.1f})",
                    market_analysis=market_analysis,
                    warnings=["Counter-trend entry - small size"]
                )

        # === 6. 폴백: EMA 크로스 기반 진입 (어떤 레짐에서든) ===
        # EMA 9/21 크로스 감지
        prev_ema_9 = df.iloc[-2]["ema_9"]
        prev_ema_21 = df.iloc[-2]["ema_21"]

        ema_bullish_cross = ema_9 > ema_21 and prev_ema_9 <= prev_ema_21
        ema_bearish_cross = ema_9 < ema_21 and prev_ema_9 >= prev_ema_21

        if ema_bullish_cross and rsi > 40 and rsi < 70:
            return AutonomousDecision(
                decision=TradingDecision.ENTER_LONG,
                confidence=0.60,
                position_size_percent=risk_params.position_size_percent * 0.5,
                target_leverage=max(5, risk_params.leverage - 2),
                stop_loss_percent=risk_params.stop_loss_percent * 1.2,
                take_profit_percent=risk_params.tp2_percent,
                tp1_percent=risk_params.tp1_percent,
                tp2_percent=risk_params.tp2_percent,
                tp3_percent=risk_params.tp3_percent,
                reasoning=f"📈 EMA Cross LONG: 9/21 golden cross (RSI={rsi:.1f})",
                market_analysis=market_analysis
            )
        elif ema_bearish_cross and rsi > 30 and rsi < 60:
            return AutonomousDecision(
                decision=TradingDecision.ENTER_SHORT,
                confidence=0.60,
                position_size_percent=risk_params.position_size_percent * 0.5,
                target_leverage=max(5, risk_params.leverage - 2),
                stop_loss_percent=risk_params.stop_loss_percent * 1.2,
                take_profit_percent=risk_params.tp2_percent,
                tp1_percent=risk_params.tp1_percent,
                tp2_percent=risk_params.tp2_percent,
                tp3_percent=risk_params.tp3_percent,
                reasoning=f"📉 EMA Cross SHORT: 9/21 death cross (RSI={rsi:.1f})",
                market_analysis=market_analysis
            )

        return self._create_hold_decision(
            f"대기 중 (VolRegime: {market_analysis.volatility_regime.value})",
            market_analysis=market_analysis
        )

    async def _validate_decision(
        self,
        decision: AutonomousDecision,
        current_price: float,
        market_analysis: SOLMarketAnalysis
    ) -> AutonomousDecision:
        """AI 신호 검증"""
        if not self.signal_validator:
            return decision

        try:
            action = "BUY" if "long" in decision.decision.value else "SELL"
            validation = await self.signal_validator.validate_signal({
                "signal_id": f"SOL_VOL_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "symbol": self.SYMBOL_BITGET,
                "action": action,
                "confidence": decision.confidence,
                "current_price": current_price,
                "market_regime": {
                    "regime_type": market_analysis.regime_type.value,
                    "volatility": market_analysis.atr_percent / 100,
                    "trend_strength": market_analysis.trend_strength,
                    "confidence": market_analysis.confidence
                },
                "volatility": market_analysis.atr_percent / 100
            })

            if validation.status.value == "REJECTED":
                logger.warning(f"Signal rejected: {validation.reasons}")
                return self._create_hold_decision(
                    f"Signal rejected: {', '.join(validation.reasons[:2])}",
                    market_analysis=market_analysis,
                    warnings=validation.reasons
                )

            # 신뢰도 조정
            if validation.adjusted_confidence:
                decision.confidence = min(decision.confidence, validation.adjusted_confidence)

            return decision

        except Exception as e:
            logger.error(f"Signal validation error: {e}")
            return decision

    def _enforce_margin_limit(
        self,
        decision: AutonomousDecision,
        seed_info: UserSeedInfo,
        current_price: float,
        leverage: int
    ) -> AutonomousDecision:
        """마진 한도 강제"""
        if decision.decision == TradingDecision.HOLD:
            return decision

        max_position_value = seed_info.remaining_margin * leverage
        max_size_percent = (max_position_value / seed_info.total_balance * 100) if seed_info.total_balance > 0 else 0

        if decision.position_size_percent > max_size_percent:
            decision.position_size_percent = max_size_percent
            decision.warnings.append(f"Position size reduced to {max_size_percent:.1f}% (35% margin limit)")

        return decision

    def _create_hold_decision(
        self,
        reason: str,
        market_analysis: Optional[SOLMarketAnalysis] = None,
        warnings: List[str] = None
    ) -> AutonomousDecision:
        """HOLD 결정 생성"""
        return AutonomousDecision(
            decision=TradingDecision.HOLD,
            confidence=0.5,
            position_size_percent=0.0,
            target_leverage=10,
            stop_loss_percent=1.5,
            take_profit_percent=3.0,
            tp1_percent=1.5,
            tp2_percent=2.5,
            tp3_percent=4.0,
            reasoning=reason,
            market_analysis=market_analysis,
            ai_enhanced=False,
            warnings=warnings or []
        )

    def update_trade_result(self, user_id: int, trade_result: Dict[str, Any]):
        """거래 결과 업데이트"""
        state = self._get_user_state(user_id)
        pnl = trade_result.get("pnl", 0)

        state["daily_pnl"] += pnl
        state["trade_count_today"] += 1
        state["last_trade_time"] = datetime.now(timezone.utc)

        # TP 플래그 리셋
        if trade_result.get("is_full_exit", True):
            state["tp1_triggered"] = False
            state["tp2_triggered"] = False

        # 보호 모드 업데이트
        if pnl < 0:
            state["consecutive_losses"] += 1
            if state["consecutive_losses"] >= 5:
                state["protection_mode"] = ProtectionMode.LOCKDOWN
                self.global_stats["protection_activations"] += 1
            elif state["consecutive_losses"] >= 3:
                state["protection_mode"] = ProtectionMode.DEFENSIVE
            elif state["consecutive_losses"] >= 2:
                state["protection_mode"] = ProtectionMode.CAUTIOUS
        else:
            state["consecutive_losses"] = 0
            if state["protection_mode"] != ProtectionMode.LOCKDOWN:
                state["protection_mode"] = ProtectionMode.NORMAL

    def get_statistics(self) -> Dict[str, Any]:
        """전략 통계 반환"""
        return {
            **self.global_stats,
            "strategy_name": "SOL Volatility Regime 15m",
            "symbol": self.SYMBOL,
            "timeframe": self.TIMEFRAME,
            "max_margin_percent": MarginCapEnforcer35Pct.MAX_MARGIN_PERCENT,
            "ai_enabled": self.enable_ai
        }
