"""
ETH AI Autonomous 40% Margin Strategy (ETH AI 자율 40% 마진 전략)

🎯 핵심 특징:
1. ETH(이더리움) 전용 최적화 전략
2. 각 사용자 시드의 40%를 최대 운용 자본으로 제한 (예: 1000 USDT → 400 USDT 사용)
3. 24시간 자율 운영 - 변동성 기반 자동 조절
4. 4개 AI 에이전트 통합 (MarketRegime, SignalValidator, RiskMonitor, PortfolioOptimizer)
5. ATR 기반 동적 손절/익절

📊 ETH 특화 지표:
- ETH 고유 변동성 패턴 분석
- 가스비/네트워크 활동 기반 추가 분석 (선택적)
- ETH/BTC 상관관계 모니터링

⚙️ 리스크 관리:
- 최대 마진 사용률: 40% (하드코딩)
- 동적 레버리지: 8-15배 (변동성 기반)
- ATR 기반 동적 SL/TP
- 연속 손실 시 자동 보호 모드
- 일일 손실 한도: 시드의 5%
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
from src.agents.market_regime.models import RegimeType  # RegimeType is in models.py
from src.agents.signal_validator.agent import SignalValidatorAgent
from src.agents.signal_validator.models import ValidationResult  # ValidationResult is in models.py
from src.agents.risk_monitor.agent import RiskMonitorAgent
from src.agents.portfolio_optimizer.agent import PortfolioOptimizationAgent

# Alias for naming consistency
PortfolioOptimizerAgent = PortfolioOptimizationAgent

# Type alias for compatibility
MarketRegimeType = RegimeType

# Services
from src.services import get_ai_service_instance

# ML Models (Optional - graceful fallback if not available)
try:
    from src.ml.features import FeaturePipeline
    from src.ml.models import EnsemblePredictor
    ML_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ML models not available: {e}. Using rule-based only.")
    ML_AVAILABLE = False
    FeaturePipeline = None
    EnsemblePredictor = None

logger = logging.getLogger(__name__)


# ============================================================================
# 상수 및 열거형
# ============================================================================

class TradingDecision(Enum):
    """거래 결정 유형"""
    ENTER_LONG = "enter_long"
    ENTER_SHORT = "enter_short"
    EXIT_LONG = "exit_long"
    EXIT_SHORT = "exit_short"
    INCREASE_POSITION = "increase_position"
    DECREASE_POSITION = "decrease_position"
    HOLD = "hold"
    EMERGENCY_EXIT = "emergency_exit"


class ProtectionMode(Enum):
    """보호 모드 - 연속 손실에 따른 거래 제한"""
    NORMAL = "normal"           # 정상 운영
    CAUTIOUS = "cautious"       # 연속 2회 손실 후 - 포지션 50% 축소
    DEFENSIVE = "defensive"     # 연속 3회 손실 후 - 포지션 30% 축소
    LOCKDOWN = "lockdown"       # 연속 5회 손실 또는 일일 손실 한도 - 거래 중지


class MarketPhase(Enum):
    """시장 단계 - ETH 특화"""
    ACCUMULATION = "accumulation"     # 축적기 - 저변동성, 횡보
    MARKUP = "markup"                 # 상승기 - 가격 상승
    DISTRIBUTION = "distribution"    # 분배기 - 고점 횡보
    MARKDOWN = "markdown"            # 하락기 - 가격 하락


# ============================================================================
# 데이터 클래스
# ============================================================================

@dataclass
class UserSeedInfo:
    """사용자 시드 정보"""
    user_id: int
    total_balance: float           # 총 잔고 (시드)
    available_for_trading: float   # 거래 가능 금액 (40%)
    used_margin: float             # 현재 사용 중인 마진
    remaining_margin: float        # 남은 마진
    margin_usage_percent: float    # 마진 사용률 (%)
    can_open_position: bool        # 신규 포지션 가능 여부
    daily_pnl: float               # 일일 손익
    daily_pnl_percent: float       # 일일 손익률 (%)


@dataclass
class PositionInfo:
    """포지션 정보"""
    symbol: str
    side: str                      # "long" or "short"
    size: float                    # 포지션 크기
    entry_price: float             # 진입가
    current_price: float           # 현재가
    unrealized_pnl: float          # 미실현 손익
    unrealized_pnl_percent: float  # 미실현 손익률
    leverage: int                  # 레버리지
    margin_used: float             # 사용 중인 마진
    liquidation_price: float       # 청산가
    entry_time: datetime           # 진입 시간
    holding_duration: Optional[timedelta] = None


@dataclass
class ETHMarketAnalysis:
    """ETH 시장 분석 결과"""
    current_price: float
    regime_type: MarketRegimeType
    market_phase: MarketPhase
    volatility: float              # ATR 기반 변동성
    volatility_percentile: float   # 변동성 백분위 (0-100)
    trend_strength: float          # ADX 기반 추세 강도
    momentum: float                # RSI 기반 모멘텀
    volume_ratio: float            # 거래량 비율
    eth_btc_correlation: float     # ETH/BTC 상관관계
    confidence: float              # 분석 신뢰도
    ai_enhanced: bool              # AI 강화 여부


@dataclass
class DynamicRiskParams:
    """동적 리스크 파라미터"""
    leverage: int                  # 계산된 레버리지
    position_size_percent: float   # 포지션 크기 (마진 대비 %)
    stop_loss_percent: float       # 손절 %
    take_profit_percent: float     # 익절 %
    trailing_stop_percent: Optional[float] = None  # 트레일링 스탑 %


@dataclass
class AutonomousDecision:
    """AI 자율 결정 결과"""
    decision: TradingDecision
    confidence: float
    position_size_percent: float   # 자본 대비 포지션 크기 (%)
    target_leverage: int
    stop_loss_percent: float
    take_profit_percent: float
    reasoning: str
    market_analysis: Optional[ETHMarketAnalysis] = None
    ai_enhanced: bool = True
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# 마진 한도 강제 모듈 (40%)
# ============================================================================

class MarginCapEnforcer40Pct:
    """
    40% 마진 한도 강제 모듈 (Hardcoded)

    이 모듈은 각 사용자의 시드 중 40%만 거래에 사용하도록 강제합니다.
    예: 사용자 시드 1000 USDT → 최대 400 USDT만 마진으로 사용 가능

    ⚠️ 이 값은 하드코딩되어 있으며, 어떠한 상황에서도 초과할 수 없습니다.
    """

    # === 하드코딩된 리스크 파라미터 (수정 불가) ===
    MAX_MARGIN_PERCENT = 40.0      # 최대 마진 사용률 (%)
    SAFETY_BUFFER_PERCENT = 2.0    # 안전 버퍼 (실제 38% 사용)
    MIN_FREE_MARGIN_PERCENT = 3.0  # 최소 유지 마진 (%)
    DAILY_LOSS_LIMIT_PERCENT = 5.0 # 일일 최대 손실률 (%)

    def __init__(self):
        self._effective_max = self.MAX_MARGIN_PERCENT - self.SAFETY_BUFFER_PERCENT
        logger.info(
            f"[MarginCapEnforcer40Pct] Initialized | "
            f"MAX={self.MAX_MARGIN_PERCENT}%, "
            f"EFFECTIVE={self._effective_max}%, "
            f"DAILY_LOSS_LIMIT={self.DAILY_LOSS_LIMIT_PERCENT}%"
        )

    async def get_user_seed_info(
        self,
        exchange_client,
        user_id: int,
        current_positions: List[PositionInfo] = None,
        daily_pnl: float = 0.0
    ) -> UserSeedInfo:
        """
        사용자 시드 정보 조회

        각 사용자의 총 잔고에서 40%만 거래 가능 금액으로 계산
        """
        try:
            # 잔고 조회
            balance = await exchange_client.fetch_balance()
            usdt_balance = balance.get("USDT", {})
            total_balance = float(usdt_balance.get("total", 0))
            used_balance = float(usdt_balance.get("used", 0))

            # 40% 마진 한도 계산
            available_for_trading = total_balance * (self._effective_max / 100)

            # 현재 사용 중인 마진 계산
            used_margin = 0.0
            if current_positions:
                for pos in current_positions:
                    used_margin += pos.margin_used
            else:
                used_margin = min(used_balance, available_for_trading)

            # 마진 사용률 (40% 한도 대비)
            margin_usage_percent = (used_margin / available_for_trading * 100) if available_for_trading > 0 else 100

            # 남은 마진
            remaining_margin = max(0, available_for_trading - used_margin)

            # 일일 손익률
            daily_pnl_percent = (daily_pnl / total_balance * 100) if total_balance > 0 else 0

            # 신규 포지션 가능 여부
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
            logger.error(f"[MarginCapEnforcer40Pct] Error getting seed info for user {user_id}: {e}")
            # 안전 모드: 거래 불가능으로 반환
            return UserSeedInfo(
                user_id=user_id,
                total_balance=0,
                available_for_trading=0,
                used_margin=0,
                remaining_margin=0,
                margin_usage_percent=100,
                can_open_position=False,
                daily_pnl=0,
                daily_pnl_percent=0
            )

    def validate_order(
        self,
        order_margin_required: float,
        seed_info: UserSeedInfo
    ) -> Tuple[bool, str, float]:
        """
        주문 검증 - 40% 한도 초과 여부 확인

        Returns:
            (허용 여부, 메시지, 조정된 마진 금액)
        """
        # 일일 손실 한도 체크
        if seed_info.daily_pnl_percent < -self.DAILY_LOSS_LIMIT_PERCENT:
            return (
                False,
                f"❌ 일일 손실 한도 초과: {seed_info.daily_pnl_percent:.2f}% < -{self.DAILY_LOSS_LIMIT_PERCENT}%",
                0
            )

        # 예상 마진 사용률 계산
        projected_used = seed_info.used_margin + order_margin_required
        projected_percent = (projected_used / seed_info.available_for_trading * 100) if seed_info.available_for_trading > 0 else 100

        if projected_percent > 100:
            # 40% 한도 초과 - 불가
            max_allowed = seed_info.remaining_margin
            return (
                False,
                f"❌ 40% 마진 한도 초과: 요청 ${order_margin_required:.2f}, 가능 ${max_allowed:.2f}",
                max_allowed
            )

        if projected_percent > 90:
            # 90% 이상 사용 - 조정 필요
            adjusted_margin = seed_info.remaining_margin * 0.8  # 80%만 사용
            return (
                True,
                f"⚠️ 마진 조정: ${order_margin_required:.2f} → ${adjusted_margin:.2f} (한도 90% 접근)",
                adjusted_margin
            )

        # 허용
        return (
            True,
            f"✅ 마진 허용: ${order_margin_required:.2f} ({projected_percent:.1f}% of 40% limit)",
            order_margin_required
        )

    def calculate_max_position_size(
        self,
        seed_info: UserSeedInfo,
        current_price: float,
        leverage: int
    ) -> float:
        """
        40% 한도 내에서 최대 포지션 크기 계산

        Returns:
            최대 포지션 크기 (수량)
        """
        if not seed_info.can_open_position:
            return 0.0

        # 사용 가능한 마진의 80%만 사용 (추가 안전 마진)
        safe_margin = seed_info.remaining_margin * 0.8

        # 포지션 가치 = 마진 * 레버리지
        position_value = safe_margin * leverage

        # 포지션 크기 = 포지션 가치 / 현재가
        position_size = position_value / current_price

        # ETH 최소 단위로 반올림 (0.001 ETH)
        position_size = round(position_size, 3)

        return max(0.001, position_size)


# ============================================================================
# ETH 특화 기술적 분석 모듈
# ============================================================================

class ETHIndicatorCalculator:
    """ETH 특화 기술적 지표 계산기"""

    # ETH 최적화 파라미터
    EMA_SHORT = 9
    EMA_MID = 21
    EMA_LONG = 55
    EMA_TREND = 200
    RSI_PERIOD = 14
    ATR_PERIOD = 14
    BB_PERIOD = 20
    BB_STD = 2.0
    VOLUME_MA_PERIOD = 20
    ADX_PERIOD = 14

    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """모든 기술적 지표 계산"""
        df = df.copy()

        # === EMA ===
        df["ema_9"] = df["close"].ewm(span=ETHIndicatorCalculator.EMA_SHORT, adjust=False).mean()
        df["ema_21"] = df["close"].ewm(span=ETHIndicatorCalculator.EMA_MID, adjust=False).mean()
        df["ema_55"] = df["close"].ewm(span=ETHIndicatorCalculator.EMA_LONG, adjust=False).mean()
        df["ema_200"] = df["close"].ewm(span=ETHIndicatorCalculator.EMA_TREND, adjust=False).mean()

        # === RSI ===
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=ETHIndicatorCalculator.RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=ETHIndicatorCalculator.RSI_PERIOD).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(50)

        # === Bollinger Bands ===
        df["bb_middle"] = df["close"].rolling(window=ETHIndicatorCalculator.BB_PERIOD).mean()
        bb_std = df["close"].rolling(window=ETHIndicatorCalculator.BB_PERIOD).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * ETHIndicatorCalculator.BB_STD)
        df["bb_lower"] = df["bb_middle"] - (bb_std * ETHIndicatorCalculator.BB_STD)
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
        df["bb_percent"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        # === MACD ===
        exp12 = df["close"].ewm(span=12, adjust=False).mean()
        exp26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = exp12 - exp26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # === ATR (Average True Range) ===
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=ETHIndicatorCalculator.ATR_PERIOD).mean()
        df["atr_percent"] = df["atr"] / df["close"] * 100  # ATR as percentage

        # === ADX (Average Directional Index) ===
        df = ETHIndicatorCalculator._calculate_adx(df)

        # === Volume ===
        df["volume_sma"] = df["volume"].rolling(window=ETHIndicatorCalculator.VOLUME_MA_PERIOD).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma"]

        # === Stochastic RSI ===
        rsi_min = df["rsi"].rolling(window=14).min()
        rsi_max = df["rsi"].rolling(window=14).max()
        df["stoch_rsi"] = (df["rsi"] - rsi_min) / (rsi_max - rsi_min)
        df["stoch_rsi"] = df["stoch_rsi"].fillna(0.5)

        # === Volatility Percentile (최근 100 캔들 기준) ===
        df["volatility_percentile"] = df["atr_percent"].rolling(window=100).apply(
            lambda x: (x.iloc[-1] > x).mean() * 100 if len(x) > 0 else 50, raw=False
        )

        return df

    @staticmethod
    def _calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
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


# ============================================================================
# 동적 리스크 파라미터 계산기
# ============================================================================

class DynamicRiskCalculator:
    """
    변동성 기반 동적 리스크 파라미터 계산기

    레버리지: 8-15배 (변동성에 따라 조절)
    손절/익절: ATR 기반 동적 계산
    """

    # 레버리지 범위
    MIN_LEVERAGE = 8
    MAX_LEVERAGE = 15

    # ATR 기반 SL/TP 배수
    ATR_SL_MULTIPLIER_LOW_VOL = 1.5    # 저변동성
    ATR_SL_MULTIPLIER_MID_VOL = 2.0    # 중변동성
    ATR_SL_MULTIPLIER_HIGH_VOL = 2.5   # 고변동성

    ATR_TP_MULTIPLIER_LOW_VOL = 3.0    # 저변동성 (1:2 R:R)
    ATR_TP_MULTIPLIER_MID_VOL = 4.0    # 중변동성 (1:2 R:R)
    ATR_TP_MULTIPLIER_HIGH_VOL = 5.0   # 고변동성 (1:2 R:R)

    @classmethod
    def calculate_dynamic_params(
        cls,
        volatility_percentile: float,
        atr_percent: float,
        regime_type: MarketRegimeType,
        protection_mode: ProtectionMode
    ) -> DynamicRiskParams:
        """
        동적 리스크 파라미터 계산

        Args:
            volatility_percentile: 변동성 백분위 (0-100)
            atr_percent: ATR 백분율
            regime_type: 시장 체제
            protection_mode: 보호 모드

        Returns:
            DynamicRiskParams: 계산된 리스크 파라미터
        """
        # === 1. 레버리지 계산 ===
        # 변동성이 높을수록 레버리지 낮춤
        if volatility_percentile > 80:
            base_leverage = cls.MIN_LEVERAGE
        elif volatility_percentile > 60:
            base_leverage = 10
        elif volatility_percentile > 40:
            base_leverage = 12
        else:
            base_leverage = cls.MAX_LEVERAGE

        # 시장 체제에 따른 조정
        if regime_type == MarketRegimeType.HIGH_VOLATILITY:
            base_leverage = max(cls.MIN_LEVERAGE, base_leverage - 3)
        elif regime_type == MarketRegimeType.TRENDING_UP:
            base_leverage = min(cls.MAX_LEVERAGE, base_leverage + 1)
        elif regime_type == MarketRegimeType.RANGING:
            base_leverage = max(cls.MIN_LEVERAGE, base_leverage - 1)

        # 보호 모드에 따른 조정
        if protection_mode == ProtectionMode.CAUTIOUS:
            base_leverage = max(cls.MIN_LEVERAGE, base_leverage - 2)
        elif protection_mode == ProtectionMode.DEFENSIVE:
            base_leverage = cls.MIN_LEVERAGE

        # === 2. ATR 기반 손절/익절 계산 ===
        if volatility_percentile > 70:
            sl_multiplier = cls.ATR_SL_MULTIPLIER_HIGH_VOL
            tp_multiplier = cls.ATR_TP_MULTIPLIER_HIGH_VOL
        elif volatility_percentile > 40:
            sl_multiplier = cls.ATR_SL_MULTIPLIER_MID_VOL
            tp_multiplier = cls.ATR_TP_MULTIPLIER_MID_VOL
        else:
            sl_multiplier = cls.ATR_SL_MULTIPLIER_LOW_VOL
            tp_multiplier = cls.ATR_TP_MULTIPLIER_LOW_VOL

        stop_loss_percent = atr_percent * sl_multiplier
        take_profit_percent = atr_percent * tp_multiplier

        # SL/TP 범위 제한
        stop_loss_percent = max(1.0, min(5.0, stop_loss_percent))
        take_profit_percent = max(2.0, min(10.0, take_profit_percent))

        # === 3. 포지션 크기 계산 ===
        # 변동성이 높을수록 포지션 축소
        if volatility_percentile > 80:
            position_size_percent = 30.0
        elif volatility_percentile > 60:
            position_size_percent = 50.0
        elif volatility_percentile > 40:
            position_size_percent = 70.0
        else:
            position_size_percent = 85.0

        # 보호 모드에 따른 조정
        if protection_mode == ProtectionMode.CAUTIOUS:
            position_size_percent *= 0.5
        elif protection_mode == ProtectionMode.DEFENSIVE:
            position_size_percent *= 0.3

        # 시장 체제에 따른 조정
        if regime_type == MarketRegimeType.HIGH_VOLATILITY:
            position_size_percent *= 0.5
        elif regime_type == MarketRegimeType.RANGING:
            position_size_percent *= 0.7

        # === 4. 트레일링 스탑 (추세장에서만) ===
        trailing_stop = None
        if regime_type in [MarketRegimeType.TRENDING_UP, MarketRegimeType.TRENDING_DOWN]:
            trailing_stop = stop_loss_percent * 1.2

        return DynamicRiskParams(
            leverage=int(base_leverage),
            position_size_percent=min(85.0, position_size_percent),
            stop_loss_percent=stop_loss_percent,
            take_profit_percent=take_profit_percent,
            trailing_stop_percent=trailing_stop
        )


# ============================================================================
# ETH AI 자율 40% 전략 메인 클래스
# ============================================================================

class ETHAutonomous40PctStrategy:
    """
    ETH AI Autonomous 40% Margin Strategy

    각 사용자 시드의 40%를 이용하여 ETH 자율 거래를 수행하는 전략
    24시간 자율 운영, 변동성 기반 동적 조절
    """

    # === 전략 기본 설정 (하드코딩) ===
    SYMBOL = "ETH/USDT"           # ETH 전용
    SYMBOL_BITGET = "ETHUSDT"     # Bitget 심볼
    TIMEFRAME = "1h"             # 기본 타임프레임
    MIN_CONFIDENCE = 0.65        # 최소 신뢰도

    def __init__(self, config: Dict[str, Any] = None):
        """
        전략 초기화

        Args:
            config: 선택적 설정 (대부분 하드코딩됨)
        """
        self.config = config or {}
        self.enable_ai = self.config.get("enable_ai", True)
        self.enable_ml = self.config.get("enable_ml", True) and ML_AVAILABLE
        self.timeframe = self.config.get("timeframe", self.TIMEFRAME)

        # === 40% 마진 한도 강제 모듈 (하드코딩) ===
        self.margin_enforcer = MarginCapEnforcer40Pct()

        # === AI 서비스 초기화 ===
        try:
            self.ai_service = get_ai_service_instance() if self.enable_ai else None
        except Exception as e:
            logger.warning(f"AI service not available: {e}")
            self.ai_service = None
            self.enable_ai = False

        # === ML 모델 초기화 ===
        if self.enable_ml:
            try:
                self.feature_pipeline = FeaturePipeline()
                self.ml_predictor = EnsemblePredictor()
                logger.info("✅ ML models initialized successfully")
            except Exception as e:
                logger.warning(f"ML initialization failed: {e}. Disabling ML.")
                self.enable_ml = False
                self.feature_pipeline = None
                self.ml_predictor = None
        else:
            self.feature_pipeline = None
            self.ml_predictor = None

        # === AI 에이전트 초기화 ===
        self._init_agents()

        # === 사용자별 상태 관리 ===
        # user_id -> 상태 딕셔너리
        self.user_states: Dict[int, Dict[str, Any]] = {}

        # === 전역 통계 ===
        self.global_stats = {
            "total_decisions": 0,
            "total_entries": 0,
            "total_exits": 0,
            "margin_limit_blocks": 0,
            "protection_activations": 0,
            "ai_analysis_count": 0,
            "ml_validation_count": 0,
            "ml_rejections": 0
        }

        logger.info(
            f"✅ ETH Autonomous 40% Strategy initialized | "
            f"Symbol={self.SYMBOL}, AI={self.enable_ai}, ML={self.enable_ml}, "
            f"MaxMargin={MarginCapEnforcer40Pct.MAX_MARGIN_PERCENT}%"
        )

    def _init_agents(self):
        """AI 에이전트 초기화"""
        if self.enable_ai and self.ai_service:
            try:
                self.market_regime_agent = MarketRegimeAgent(
                    agent_id="eth_market_regime",
                    name="ETH Market Regime Agent",
                    config={
                        "enable_ai": True,
                        "atr_period": 14,
                        "adx_period": 14,
                        "volatility_threshold": 0.025,  # ETH는 BTC보다 높은 변동성
                        "symbol": "ETHUSDT",
                    },
                    ai_service=self.ai_service
                )

                self.signal_validator = SignalValidatorAgent(
                    agent_id="eth_signal_validator",
                    name="ETH Signal Validator Agent",
                    config={
                        "enable_ai": True,
                        "min_passed_rules": 6,
                        "critical_rules": ["price_sanity", "balance_check", "volatility_check"],
                    },
                    ai_service=self.ai_service
                )

                self.risk_monitor = RiskMonitorAgent(
                    agent_id="eth_risk_monitor",
                    name="ETH Risk Monitor Agent",
                    config={
                        "max_position_loss_percent": 4.0,  # ETH는 더 타이트하게
                        "max_daily_loss": 500,
                        "max_drawdown_percent": 8.0,
                    }
                )  # RiskMonitorAgent doesn't take ai_service

                self.portfolio_optimizer = PortfolioOptimizerAgent(
                    agent_id="eth_portfolio_optimizer",
                    name="ETH Portfolio Optimizer Agent",
                    config={
                        "enable_ai": True,
                        "max_allocation_percent": 40.0,  # 40% 한도와 일치
                        "rebalancing_threshold": 5.0,
                    },
                    ai_service=self.ai_service
                )

                logger.info("✅ All 4 AI agents initialized for ETH autonomous trading")
            except Exception as e:
                logger.error(f"Failed to initialize AI agents: {e}")
                self.market_regime_agent = None
                self.signal_validator = None
                self.risk_monitor = None
                self.portfolio_optimizer = None
        else:
            self.market_regime_agent = None
            self.signal_validator = None
            self.risk_monitor = None
            self.portfolio_optimizer = None
            logger.warning("⚠️ AI agents disabled or not available")

    def _get_user_state(self, user_id: int) -> Dict[str, Any]:
        """사용자별 상태 가져오기 (없으면 초기화)"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {
                "protection_mode": ProtectionMode.NORMAL,
                "consecutive_losses": 0,
                "daily_pnl": 0.0,
                "last_trade_time": None,
                "trade_count_today": 0,
                "last_reset_date": datetime.now(timezone.utc).date()
            }

        # 일일 리셋 체크
        state = self.user_states[user_id]
        today = datetime.now(timezone.utc).date()
        if state["last_reset_date"] != today:
            state["daily_pnl"] = 0.0
            state["trade_count_today"] = 0
            state["last_reset_date"] = today
            if state["protection_mode"] == ProtectionMode.LOCKDOWN:
                state["protection_mode"] = ProtectionMode.DEFENSIVE
                logger.info(f"[User {user_id}] Daily reset: LOCKDOWN → DEFENSIVE")

        return state

    async def analyze_and_decide(
        self,
        exchange,
        user_id: int,
        current_positions: List[PositionInfo] = None
    ) -> AutonomousDecision:
        """
        자율 분석 및 거래 결정 (메인 진입점)

        Args:
            exchange: CCXT 거래소 인스턴스
            user_id: 사용자 ID
            current_positions: 현재 포지션 목록

        Returns:
            AutonomousDecision: AI의 자율적 거래 결정
        """
        self.global_stats["total_decisions"] += 1
        user_state = self._get_user_state(user_id)

        try:
            # === 1. 사용자 시드 정보 조회 (40% 한도 체크) ===
            seed_info = await self.margin_enforcer.get_user_seed_info(
                exchange, user_id, current_positions, user_state["daily_pnl"]
            )

            logger.info(
                f"[User {user_id}] Seed: ${seed_info.total_balance:.2f} | "
                f"40% Limit: ${seed_info.available_for_trading:.2f} | "
                f"Used: {seed_info.margin_usage_percent:.1f}% | "
                f"Daily PnL: {seed_info.daily_pnl_percent:.2f}%"
            )

            # === 2. 보호 모드 체크 ===
            if user_state["protection_mode"] == ProtectionMode.LOCKDOWN:
                return self._create_hold_decision(
                    "🔒 LOCKDOWN: 연속 손실로 인해 거래 중지됨",
                    warnings=["Trading locked due to consecutive losses"]
                )

            if not seed_info.can_open_position and not current_positions:
                self.global_stats["margin_limit_blocks"] += 1
                return self._create_hold_decision(
                    f"⚠️ 40% 마진 한도 도달 또는 일일 손실 한도 초과",
                    warnings=["40% margin limit reached or daily loss limit exceeded"]
                )

            # === 3. 시장 데이터 가져오기 ===
            ohlcv = await exchange.fetch_ohlcv(self.SYMBOL, self.timeframe, limit=200)
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            current_price = float(df["close"].iloc[-1])

            # === 4. 기술적 지표 계산 ===
            df = ETHIndicatorCalculator.calculate_all_indicators(df)

            # === 5. ETH 시장 분석 ===
            market_analysis = await self._analyze_eth_market(exchange, df, current_price)

            # === 6. 동적 리스크 파라미터 계산 ===
            risk_params = DynamicRiskCalculator.calculate_dynamic_params(
                volatility_percentile=market_analysis.volatility_percentile,
                atr_percent=market_analysis.volatility * 100,
                regime_type=market_analysis.regime_type,
                protection_mode=user_state["protection_mode"]
            )

            logger.info(
                f"[ETH Analysis] Regime: {market_analysis.regime_type.value} | "
                f"Vol%: {market_analysis.volatility_percentile:.1f} | "
                f"Leverage: {risk_params.leverage}x | "
                f"SL: {risk_params.stop_loss_percent:.2f}% | "
                f"TP: {risk_params.take_profit_percent:.2f}%"
            )

            # === 7. 포지션 보유 시 청산 조건 확인 ===
            if current_positions:
                exit_decision = await self._check_exit_conditions(
                    current_positions, df, current_price, market_analysis, risk_params
                )
                if exit_decision.decision != TradingDecision.HOLD:
                    return exit_decision

            # === 8. 신규 진입 불가능하면 HOLD ===
            if not seed_info.can_open_position:
                return self._create_hold_decision(
                    "포지션 보유 중 - 추가 진입 불가",
                    market_analysis=market_analysis
                )

            # === 9. Stage 1: Rule-based Signal Generation ===
            entry_decision = await self._make_entry_decision(
                df, current_price, market_analysis, risk_params, seed_info, user_state
            )

            # === 10. Stage 2: LightGBM ML Validation ===
            if entry_decision.decision not in [TradingDecision.HOLD]:
                entry_decision = await self._ml_validate_signal(entry_decision, df, exchange)

            # === 11. Stage 3: DeepSeek AI Confirmation ===
            # (AI 신호 검증 - 기존 코드 유지)
            if entry_decision.decision not in [TradingDecision.HOLD]:
                entry_decision = await self._validate_decision(entry_decision, current_price, market_analysis)

            # === 12. Stage 4: 40% Margin Limit Enforcement (Final Decision) ===
            entry_decision = self._enforce_margin_limit(entry_decision, seed_info, current_price, risk_params.leverage)

            # === 13. 통계 업데이트 ===
            if entry_decision.decision in [TradingDecision.ENTER_LONG, TradingDecision.ENTER_SHORT]:
                self.global_stats["total_entries"] += 1

            logger.info(
                f"[4-Stage Decision] {entry_decision.decision.value} | "
                f"Confidence: {entry_decision.confidence:.1%} | "
                f"Size: {entry_decision.position_size_percent:.1f}% | "
                f"Leverage: {entry_decision.target_leverage}x | "
                f"ML: {self.enable_ml}"
            )

            return entry_decision

        except Exception as e:
            logger.error(f"[ETH Strategy] Analysis failed for user {user_id}: {e}", exc_info=True)
            return self._create_hold_decision(f"Analysis error: {str(e)}")

    async def _analyze_eth_market(
        self,
        exchange,
        df: pd.DataFrame,
        current_price: float
    ) -> ETHMarketAnalysis:
        """ETH 시장 분석"""
        latest = df.iloc[-1]

        # AI 시장 체제 분석
        regime_type = MarketRegimeType.RANGING
        confidence = 0.6
        ai_enhanced = False

        if self.market_regime_agent:
            try:
                # Bitget API는 슬래시 없는 심볼 형식 사용 (ETH/USDT -> ETHUSDT)
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

        # 시장 단계 판단
        market_phase = self._detect_market_phase(df, latest)

        # 변동성 지표
        volatility = float(latest["atr"] / current_price)
        volatility_percentile = float(latest.get("volatility_percentile", 50))

        # 추세 강도
        trend_strength = float(latest.get("adx", 20))

        # 모멘텀
        momentum = float(latest.get("rsi", 50))

        # 거래량 비율
        volume_ratio = float(latest.get("volume_ratio", 1.0))

        # ETH/BTC 상관관계 (간단히 1로 설정, 실제로는 API에서 가져와야 함)
        eth_btc_correlation = 0.85

        return ETHMarketAnalysis(
            current_price=current_price,
            regime_type=regime_type,
            market_phase=market_phase,
            volatility=volatility,
            volatility_percentile=volatility_percentile,
            trend_strength=trend_strength,
            momentum=momentum,
            volume_ratio=volume_ratio,
            eth_btc_correlation=eth_btc_correlation,
            confidence=confidence,
            ai_enhanced=ai_enhanced
        )

    def _detect_regime_rule_based(self, latest) -> MarketRegimeType:
        """규칙 기반 시장 체제 감지"""
        ema_21 = latest.get("ema_21", 0)
        ema_55 = latest.get("ema_55", 0)
        adx = latest.get("adx", 20)
        atr_percent = latest.get("atr_percent", 2)

        # 고변동성 체크
        if atr_percent > 4:
            return MarketRegimeType.HIGH_VOLATILITY

        # 추세 체크
        if adx > 25:
            if ema_21 > ema_55 * 1.01:
                return MarketRegimeType.TRENDING_UP
            elif ema_21 < ema_55 * 0.99:
                return MarketRegimeType.TRENDING_DOWN

        return MarketRegimeType.RANGING

    def _detect_market_phase(self, df: pd.DataFrame, latest) -> MarketPhase:
        """시장 단계 감지"""
        # 최근 20개 캔들 분석
        recent = df.tail(20)
        price_change = (recent["close"].iloc[-1] - recent["close"].iloc[0]) / recent["close"].iloc[0]
        volume_trend = recent["volume"].iloc[-10:].mean() / recent["volume"].iloc[:10].mean()

        bb_percent = latest.get("bb_percent", 0.5)
        rsi = latest.get("rsi", 50)

        if price_change > 0.03 and volume_trend > 1.2:
            return MarketPhase.MARKUP
        elif price_change < -0.03 and volume_trend > 1.2:
            return MarketPhase.MARKDOWN
        elif bb_percent > 0.8 and rsi > 65:
            return MarketPhase.DISTRIBUTION
        elif bb_percent < 0.2 and rsi < 35:
            return MarketPhase.ACCUMULATION
        else:
            return MarketPhase.ACCUMULATION

    async def _make_entry_decision(
        self,
        df: pd.DataFrame,
        current_price: float,
        market_analysis: ETHMarketAnalysis,
        risk_params: DynamicRiskParams,
        seed_info: UserSeedInfo,
        user_state: Dict[str, Any]
    ) -> AutonomousDecision:
        """AI 자율 진입 결정 (Stage 1: Rule-based Signal)"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        regime = market_analysis.regime_type
        phase = market_analysis.market_phase

        # === 상승 추세 + 상승 신호 ===
        if regime == MarketRegimeType.TRENDING_UP:
            if self._is_bullish_continuation(latest, prev, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.80,
                    position_size_percent=risk_params.position_size_percent,
                    target_leverage=risk_params.leverage,
                    stop_loss_percent=risk_params.stop_loss_percent,
                    take_profit_percent=risk_params.take_profit_percent,
                    reasoning="📈 Strong bullish trend: EMA alignment + momentum + volume confirmation",
                    market_analysis=market_analysis,
                    ai_enhanced=self.enable_ai
                )

        # === 하락 추세 + 숏 신호 ===
        elif regime == MarketRegimeType.TRENDING_DOWN:
            if self._is_bearish_continuation(latest, prev, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.75,
                    position_size_percent=risk_params.position_size_percent * 0.8,  # 숏은 보수적
                    target_leverage=risk_params.leverage,
                    stop_loss_percent=risk_params.stop_loss_percent,
                    take_profit_percent=risk_params.take_profit_percent,
                    reasoning="📉 Strong bearish trend: Price below EMAs + selling pressure",
                    market_analysis=market_analysis,
                    ai_enhanced=self.enable_ai
                )

        # === 횡보 + 지지/저항 반전 ===
        elif regime == MarketRegimeType.RANGING:
            # 디버그: 현재 지표 값 로깅
            logger.info(f"[RANGING Debug] RSI: {latest.get('rsi', 0):.1f} | BB%: {latest.get('bb_percent', 0):.2f} | VolRatio: {latest.get('volume_ratio', 0):.2f}")
            if self._is_support_bounce(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.70,
                    position_size_percent=risk_params.position_size_percent * 0.6,
                    target_leverage=min(risk_params.leverage, 10),
                    stop_loss_percent=risk_params.stop_loss_percent * 0.8,
                    take_profit_percent=risk_params.take_profit_percent * 0.7,
                    reasoning="🔄 Mean reversion: Bounce from support (BB lower + RSI oversold)",
                    market_analysis=market_analysis,
                    ai_enhanced=self.enable_ai
                )
            elif self._is_resistance_rejection(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.65,
                    position_size_percent=risk_params.position_size_percent * 0.5,
                    target_leverage=min(risk_params.leverage, 8),
                    stop_loss_percent=risk_params.stop_loss_percent * 0.8,
                    take_profit_percent=risk_params.take_profit_percent * 0.7,
                    reasoning="🔄 Mean reversion: Rejection from resistance (BB upper + RSI overbought)",
                    market_analysis=market_analysis,
                    ai_enhanced=self.enable_ai
                )

        # === 고변동성 - 극단적 과매도에서만 진입 ===
        elif regime == MarketRegimeType.HIGH_VOLATILITY:
            if self._is_extreme_oversold(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.65,
                    position_size_percent=risk_params.position_size_percent * 0.4,
                    target_leverage=8,  # 최소 레버리지
                    stop_loss_percent=risk_params.stop_loss_percent * 1.5,
                    take_profit_percent=risk_params.take_profit_percent * 1.5,
                    reasoning="⚡ High volatility: Extreme oversold with volume spike",
                    market_analysis=market_analysis,
                    ai_enhanced=self.enable_ai,
                    warnings=["High volatility - reduced position size"]
                )

        # === 저거래량 - RANGING과 유사하게 지지/저항 반전 전략 ===
        elif regime == MarketRegimeType.LOW_VOLUME:
            # 저거래량 시장에서는 보수적으로 지지/저항 반전만 진입
            if self._is_support_bounce(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.65,
                    position_size_percent=risk_params.position_size_percent * 0.5,  # 작은 포지션
                    target_leverage=min(risk_params.leverage, 8),  # 낮은 레버리지
                    stop_loss_percent=risk_params.stop_loss_percent * 0.8,
                    take_profit_percent=risk_params.take_profit_percent * 0.6,  # 짧은 TP
                    reasoning="🔇 Low volume: Conservative bounce from support (BB lower + RSI oversold)",
                    market_analysis=market_analysis,
                    ai_enhanced=self.enable_ai,
                    warnings=["Low volume market - reduced position & leverage"]
                )
            elif self._is_resistance_rejection(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.60,
                    position_size_percent=risk_params.position_size_percent * 0.4,  # 더 작은 포지션
                    target_leverage=min(risk_params.leverage, 6),  # 더 낮은 레버리지
                    stop_loss_percent=risk_params.stop_loss_percent * 0.8,
                    take_profit_percent=risk_params.take_profit_percent * 0.5,
                    reasoning="🔇 Low volume: Conservative rejection from resistance",
                    market_analysis=market_analysis,
                    ai_enhanced=self.enable_ai,
                    warnings=["Low volume market - reduced position & leverage"]
                )

        # === 기본: HOLD ===
        return self._create_hold_decision(
            f"No clear signal in {regime.value} regime / {phase.value} phase",
            market_analysis=market_analysis
        )

    async def _ml_validate_signal(
        self,
        decision: AutonomousDecision,
        df: pd.DataFrame,
        exchange
    ) -> AutonomousDecision:
        """
        Stage 2: LightGBM ML Validation

        규칙 기반 신호를 ML 모델로 검증하고 파라미터 조정

        Args:
            decision: Stage 1에서 생성된 규칙 기반 결정
            df: OHLCV 데이터
            exchange: 거래소 객체 (다중 타임프레임용)

        Returns:
            ML 검증이 적용된 결정
        """
        if not self.enable_ml or decision.decision == TradingDecision.HOLD:
            return decision

        try:
            self.global_stats["ml_validation_count"] += 1

            # 5분봉 데이터 준비 (df는 1시간봉이므로 5분봉 별도 조회)
            try:
                ohlcv_5m = await exchange.fetch_ohlcv(self.SYMBOL, "5m", limit=200)
                candles_5m = [
                    {
                        "timestamp": row[0],
                        "open": row[1],
                        "high": row[2],
                        "low": row[3],
                        "close": row[4],
                        "volume": row[5]
                    }
                    for row in ohlcv_5m
                ]
            except Exception as e:
                logger.warning(f"Failed to fetch 5m candles for ML: {e}")
                return decision

            # 1시간봉 데이터 준비
            candles_1h = [
                {
                    "timestamp": row["timestamp"].timestamp() * 1000 if hasattr(row.get("timestamp", 0), "timestamp") else row.get("timestamp", 0),
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"]
                }
                for _, row in df.tail(100).iterrows()
            ]

            # 피처 추출
            features_df = self.feature_pipeline.extract_features(
                candles_5m=candles_5m,
                candles_1h=candles_1h,
                symbol=self.SYMBOL_BITGET
            )

            if features_df.empty:
                logger.warning("ML feature extraction failed - using rule-based decision")
                return decision

            # ML 예측
            rule_signal = "long" if decision.decision == TradingDecision.ENTER_LONG else "short"
            ml_result = self.ml_predictor.predict(
                features=features_df,
                symbol=self.SYMBOL_BITGET,
                rule_based_signal=rule_signal
            )

            logger.info(
                f"[ML Validation] Direction: {ml_result.direction.direction.value} "
                f"(conf: {ml_result.direction.confidence:.2f}), "
                f"Volatility: {ml_result.volatility.level.value}, "
                f"Timing: {ml_result.timing.is_good_entry}, "
                f"Combined: {ml_result.combined_confidence:.2f}"
            )

            # === Stage 2: ML Rejection Criteria ===

            # 1. ML이 진입을 건너뛰라고 권장
            if ml_result.should_skip_entry():
                self.global_stats["ml_rejections"] += 1
                reason = "ML validation: "
                if ml_result.volatility.is_extreme():
                    reason += "Extreme volatility detected"
                elif not ml_result.timing.is_good_entry:
                    reason += f"Poor timing ({ml_result.timing.reason})"
                else:
                    reason += f"Low ML confidence ({ml_result.combined_confidence:.0%})"

                return self._create_hold_decision(
                    f"🤖 {reason}",
                    warnings=[reason],
                    market_analysis=decision.market_analysis
                )

            # 2. ML 방향이 규칙 기반과 불일치 (낮은 신뢰도)
            if not ml_result.direction.agrees_with_rule and ml_result.direction.confidence > 0.6:
                self.global_stats["ml_rejections"] += 1
                return self._create_hold_decision(
                    f"🤖 ML validation: Direction mismatch (ML suggests {ml_result.direction.direction.value})",
                    warnings=[f"ML disagrees with rule-based signal"],
                    market_analysis=decision.market_analysis
                )

            # === Stage 2: ML Enhancement (통과 시) ===

            # ML 신뢰도 반영
            decision.confidence = (decision.confidence + ml_result.combined_confidence) / 2

            # ML이 제안한 손절/포지션 크기 적용 (신뢰도 높을 때만)
            if ml_result.combined_confidence > 0.7:
                # 손절 조정
                ml_sl = ml_result.stoploss.optimal_sl_percent
                decision.stop_loss_percent = (decision.stop_loss_percent + ml_sl) / 2

                # 포지션 크기 조정
                ml_size = ml_result.position_size.optimal_size_percent
                decision.position_size_percent = min(
                    decision.position_size_percent,
                    ml_size
                )

                decision.reasoning += f" | 🤖 ML-enhanced (conf: {ml_result.combined_confidence:.0%})"
                decision.warnings.append(
                    f"ML adjusted: SL={ml_sl:.2f}%, Size={ml_size:.1f}%"
                )
            else:
                decision.reasoning += f" | 🤖 ML validated (conf: {ml_result.combined_confidence:.0%})"

            logger.info(
                f"[ML Validation] ✅ Signal enhanced | "
                f"Confidence: {decision.confidence:.0%}, "
                f"SL: {decision.stop_loss_percent:.2f}%, "
                f"Size: {decision.position_size_percent:.1f}%"
            )

            return decision

        except Exception as e:
            logger.error(f"ML validation failed: {e}", exc_info=True)
            return decision

    async def _check_exit_conditions(
        self,
        positions: List[PositionInfo],
        df: pd.DataFrame,
        current_price: float,
        market_analysis: ETHMarketAnalysis,
        risk_params: DynamicRiskParams
    ) -> AutonomousDecision:
        """청산 조건 확인"""
        latest = df.iloc[-1]

        for pos in positions:
            pnl_percent = pos.unrealized_pnl_percent

            # === 동적 손절 (ATR 기반) ===
            if pnl_percent < -risk_params.stop_loss_percent:
                self.global_stats["total_exits"] += 1
                return AutonomousDecision(
                    decision=TradingDecision.EXIT_LONG if pos.side == "long" else TradingDecision.EXIT_SHORT,
                    confidence=1.0,
                    position_size_percent=100,
                    target_leverage=pos.leverage,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning=f"⛔ Stop Loss: {pnl_percent:.2f}% < -{risk_params.stop_loss_percent:.2f}% (ATR-based)",
                    market_analysis=market_analysis
                )

            # === 동적 익절 (ATR 기반) ===
            if pnl_percent > risk_params.take_profit_percent:
                self.global_stats["total_exits"] += 1
                return AutonomousDecision(
                    decision=TradingDecision.EXIT_LONG if pos.side == "long" else TradingDecision.EXIT_SHORT,
                    confidence=0.9,
                    position_size_percent=100,
                    target_leverage=pos.leverage,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning=f"✅ Take Profit: {pnl_percent:.2f}% > {risk_params.take_profit_percent:.2f}% (ATR-based)",
                    market_analysis=market_analysis
                )

            # === 청산 위험 ===
            if pos.liquidation_price > 0:
                distance_to_liq = abs(current_price - pos.liquidation_price) / current_price * 100
                if distance_to_liq < 5:  # 청산가까지 5% 미만
                    return AutonomousDecision(
                        decision=TradingDecision.EMERGENCY_EXIT,
                        confidence=1.0,
                        position_size_percent=100,
                        target_leverage=pos.leverage,
                        stop_loss_percent=0,
                        take_profit_percent=0,
                        reasoning=f"🚨 EMERGENCY: Liquidation risk! Distance: {distance_to_liq:.1f}%",
                        market_analysis=market_analysis,
                        warnings=["CRITICAL: Near liquidation price"]
                    )

            # === 추세 반전 청산 ===
            if pos.side == "long" and self._is_trend_reversal_bearish(latest, df):
                if pnl_percent > 0:  # 이익 중일 때만
                    return AutonomousDecision(
                        decision=TradingDecision.EXIT_LONG,
                        confidence=0.75,
                        position_size_percent=100,
                        target_leverage=pos.leverage,
                        stop_loss_percent=0,
                        take_profit_percent=0,
                        reasoning=f"🔄 Trend reversal: Bearish signal detected (PnL: {pnl_percent:.2f}%)",
                        market_analysis=market_analysis
                    )

            if pos.side == "short" and self._is_trend_reversal_bullish(latest, df):
                if pnl_percent > 0:
                    return AutonomousDecision(
                        decision=TradingDecision.EXIT_SHORT,
                        confidence=0.75,
                        position_size_percent=100,
                        target_leverage=pos.leverage,
                        stop_loss_percent=0,
                        take_profit_percent=0,
                        reasoning=f"🔄 Trend reversal: Bullish signal detected (PnL: {pnl_percent:.2f}%)",
                        market_analysis=market_analysis
                    )

        return self._create_hold_decision("Position held - no exit conditions met", market_analysis=market_analysis)

    def _enforce_margin_limit(
        self,
        decision: AutonomousDecision,
        seed_info: UserSeedInfo,
        current_price: float,
        leverage: int
    ) -> AutonomousDecision:
        """40% 마진 한도 강제 적용"""
        if decision.decision == TradingDecision.HOLD:
            return decision

        if decision.decision in [TradingDecision.ENTER_LONG, TradingDecision.ENTER_SHORT]:
            # 요청된 마진 계산
            requested_margin = seed_info.available_for_trading * (decision.position_size_percent / 100)

            # 마진 한도 검증
            allowed, msg, adjusted_margin = self.margin_enforcer.validate_order(requested_margin, seed_info)

            if not allowed:
                self.global_stats["margin_limit_blocks"] += 1
                logger.warning(f"[Margin Enforcer] {msg}")
                return self._create_hold_decision(
                    f"Blocked by 40% margin limit: {msg}",
                    warnings=[msg],
                    market_analysis=decision.market_analysis
                )

            if adjusted_margin < requested_margin:
                adjusted_percent = (adjusted_margin / seed_info.available_for_trading) * 100
                logger.info(f"[Margin Enforcer] {msg}")
                decision.position_size_percent = adjusted_percent
                decision.warnings.append(f"Position size adjusted: {adjusted_percent:.1f}%")

        return decision

    async def _validate_decision(
        self,
        decision: AutonomousDecision,
        current_price: float,
        market_analysis: ETHMarketAnalysis
    ) -> AutonomousDecision:
        """AI 신호 검증"""
        if not self.signal_validator:
            return decision

        try:
            validation = await self.signal_validator.validate_signal({
                "signal_id": f"ETH_AUTO_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "symbol": self.SYMBOL,
                "action": "BUY" if "long" in decision.decision.value else "SELL",
                "confidence": decision.confidence,
                "current_price": current_price,
                "market_regime": {
                    "regime_type": market_analysis.regime_type.value,
                    "volatility": market_analysis.volatility,
                    "trend_strength": market_analysis.trend_strength,  # ADX 값 전달
                    "confidence": market_analysis.confidence
                },
                "volatility": market_analysis.volatility
            })

            if validation.validation_result == ValidationResult.REJECTED:
                return self._create_hold_decision(
                    f"Signal rejected by validator: {', '.join(validation.failed_rules)}",
                    warnings=validation.warnings,
                    market_analysis=market_analysis
                )

            if validation.validation_result == ValidationResult.APPROVED_WITH_CONDITIONS:
                decision.confidence *= 0.85
                decision.warnings.extend(validation.warnings)

        except Exception as e:
            logger.warning(f"Signal validation failed: {e}")

        return decision

    # === 신호 감지 메서드 ===

    def _is_bullish_continuation(self, latest, prev, df) -> bool:
        """상승 추세 지속 신호"""
        conditions = {
            "close > ema_21": latest["close"] > latest["ema_21"],
            "ema_21 > ema_55": latest["ema_21"] > latest["ema_55"],
            "rsi > 50": latest["rsi"] > 50,
            "rsi < 75": latest["rsi"] < 75,
            "macd > signal": latest["macd"] > latest["macd_signal"],
            "macd_hist increasing": latest["macd_hist"] > prev["macd_hist"],
            "volume_ratio > 1.1": latest["volume_ratio"] > 1.1,
            "adx > 20": latest["adx"] > 20,
        }

        all_passed = all(conditions.values())

        # 디버그 로그: 어떤 조건이 실패했는지 표시 (INFO 레벨로 변경)
        if not all_passed:
            failed = [k for k, v in conditions.items() if not v]
            logger.info(
                f"[Bullish Check] Failed: {failed} | "
                f"RSI: {latest['rsi']:.1f}, MACD_hist: {latest['macd_hist']:.4f}, "
                f"Vol_ratio: {latest['volume_ratio']:.2f}, ADX: {latest['adx']:.1f}"
            )
        else:
            logger.info(f"✅ [Bullish Signal] All conditions passed! RSI: {latest['rsi']:.1f}, ADX: {latest['adx']:.1f}")

        return all_passed

    def _is_bearish_continuation(self, latest, prev, df) -> bool:
        """하락 추세 지속 신호"""
        return (
            latest["close"] < latest["ema_21"] and
            latest["ema_21"] < latest["ema_55"] and
            latest["rsi"] < 50 and latest["rsi"] > 25 and
            latest["macd"] < latest["macd_signal"] and
            latest["macd_hist"] < prev["macd_hist"] and
            latest["volume_ratio"] > 1.1 and
            latest["adx"] > 20
        )

    def _is_support_bounce(self, latest, df) -> bool:
        """지지선 반등 신호 (완화된 조건)"""
        return (
            latest["rsi"] < 40 and  # 35 -> 40 (완화)
            latest["bb_percent"] < 0.20 and  # 0.15 -> 0.20 (완화)
            latest["close"] > latest["low"] * 1.001  # 저점에서 반등 (완화)
            # volume_ratio 조건 제거 - 저거래량 시장에서도 진입 가능
        )

    def _is_resistance_rejection(self, latest, df) -> bool:
        """저항선 거부 신호 (완화된 조건)"""
        return (
            latest["rsi"] > 60 and  # 65 -> 60 (완화)
            latest["bb_percent"] > 0.80 and  # 0.85 -> 0.80 (완화)
            latest["close"] < latest["high"] * 0.999  # 고점에서 거부 (완화)
        )

    def _is_extreme_oversold(self, latest, df) -> bool:
        """극단적 과매도"""
        return (
            latest["rsi"] < 25 and
            latest["stoch_rsi"] < 0.1 and
            latest["bb_percent"] < 0.05 and
            latest["volume_ratio"] > 2.0
        )

    def _is_trend_reversal_bearish(self, latest, df) -> bool:
        """하락 반전 신호"""
        return (
            latest["close"] < latest["ema_21"] and
            latest["macd"] < latest["macd_signal"] and
            latest["rsi"] < 45 and
            latest["macd_hist"] < 0
        )

    def _is_trend_reversal_bullish(self, latest, df) -> bool:
        """상승 반전 신호"""
        return (
            latest["close"] > latest["ema_21"] and
            latest["macd"] > latest["macd_signal"] and
            latest["rsi"] > 55 and
            latest["macd_hist"] > 0
        )

    def _create_hold_decision(
        self,
        reasoning: str,
        warnings: List[str] = None,
        market_analysis: ETHMarketAnalysis = None
    ) -> AutonomousDecision:
        """HOLD 결정 생성 헬퍼"""
        return AutonomousDecision(
            decision=TradingDecision.HOLD,
            confidence=0.5,
            position_size_percent=0,
            target_leverage=8,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning=reasoning,
            market_analysis=market_analysis,
            ai_enhanced=self.enable_ai,
            warnings=warnings or []
        )

    # === 상태 관리 ===

    def update_trade_result(self, user_id: int, trade_result: Dict[str, Any]):
        """거래 결과에 따른 상태 업데이트"""
        state = self._get_user_state(user_id)
        pnl = trade_result.get("pnl", 0)

        state["daily_pnl"] += pnl
        state["trade_count_today"] += 1
        state["last_trade_time"] = datetime.now(timezone.utc)

        if pnl < 0:
            state["consecutive_losses"] += 1
        else:
            state["consecutive_losses"] = 0

        # 보호 모드 업데이트
        old_mode = state["protection_mode"]

        if state["consecutive_losses"] >= 5 or state["daily_pnl"] < -state.get("daily_loss_limit", 500):
            state["protection_mode"] = ProtectionMode.LOCKDOWN
        elif state["consecutive_losses"] >= 3:
            state["protection_mode"] = ProtectionMode.DEFENSIVE
        elif state["consecutive_losses"] >= 2:
            state["protection_mode"] = ProtectionMode.CAUTIOUS
        else:
            state["protection_mode"] = ProtectionMode.NORMAL

        if old_mode != state["protection_mode"]:
            self.global_stats["protection_activations"] += 1
            logger.warning(
                f"[User {user_id}] Protection Mode: {old_mode.value} → {state['protection_mode'].value} | "
                f"Consecutive Losses: {state['consecutive_losses']} | Daily PnL: ${state['daily_pnl']:.2f}"
            )

    def get_statistics(self) -> Dict[str, Any]:
        """전략 통계 반환"""
        return {
            "strategy_name": "ETH_AI_Autonomous_40pct",
            "symbol": self.SYMBOL,
            "timeframe": self.timeframe,
            "max_margin_percent": MarginCapEnforcer40Pct.MAX_MARGIN_PERCENT,
            "ai_enabled": self.enable_ai,
            "active_users": len(self.user_states),
            **self.global_stats
        }

    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """사용자별 통계 반환"""
        state = self._get_user_state(user_id)
        return {
            "user_id": user_id,
            "protection_mode": state["protection_mode"].value,
            "consecutive_losses": state["consecutive_losses"],
            "daily_pnl": state["daily_pnl"],
            "trade_count_today": state["trade_count_today"],
            "last_trade_time": state["last_trade_time"].isoformat() if state["last_trade_time"] else None
        }


# ============================================================================
# 전략 인스턴스 팩토리 함수 (strategy_loader.py에서 호출)
# ============================================================================

def create_eth_autonomous_40pct_strategy(config: Dict[str, Any] = None) -> ETHAutonomous40PctStrategy:
    """ETH AI Autonomous 40% 전략 인스턴스 생성"""
    return ETHAutonomous40PctStrategy(config or {})


# ============================================================================
# generate_signal 인터페이스 (기존 strategy_loader와 호환)
# ============================================================================

async def generate_signal(
    strategy_instance: ETHAutonomous40PctStrategy,
    exchange,
    user_id: int,
    current_positions: List[PositionInfo] = None
) -> Dict[str, Any]:
    """
    신호 생성 (strategy_loader 호환 인터페이스)

    Returns:
        Dict with keys: action, confidence, stop_loss, take_profit, position_size, leverage, reasoning
    """
    decision = await strategy_instance.analyze_and_decide(exchange, user_id, current_positions)

    # TradingDecision → action 변환
    action_map = {
        TradingDecision.ENTER_LONG: "buy",
        TradingDecision.ENTER_SHORT: "sell",
        TradingDecision.EXIT_LONG: "close_long",
        TradingDecision.EXIT_SHORT: "close_short",
        TradingDecision.EMERGENCY_EXIT: "emergency_close",
        TradingDecision.HOLD: "hold",
        TradingDecision.INCREASE_POSITION: "increase",
        TradingDecision.DECREASE_POSITION: "decrease"
    }

    # ML validation 여부 체크
    ml_validated = "🤖 ML" in decision.reasoning if decision.reasoning else False

    return {
        "action": action_map.get(decision.decision, "hold"),
        "confidence": decision.confidence,
        "stop_loss_percent": decision.stop_loss_percent,
        "take_profit_percent": decision.take_profit_percent,
        "position_size_percent": decision.position_size_percent,
        "leverage": decision.target_leverage,
        "reasoning": decision.reasoning,
        "warnings": decision.warnings,
        "ai_enhanced": decision.ai_enhanced,
        "ml_validated": ml_validated,
        "strategy_type": "4-stage-pipeline" if strategy_instance.enable_ml else "3-stage-pipeline",
        "market_regime": decision.market_analysis.regime_type.value if decision.market_analysis else "unknown"
    }
