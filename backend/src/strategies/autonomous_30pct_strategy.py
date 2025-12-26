"""
RealTime Autonomous 30% Margin Strategy (실시간 자율 30% 마진 전략)

핵심 특징:
1. AI 에이전트에게 완전한 자율권 부여 (진입, 청산, 포지션 크기, 홀딩 기간 결정)
2. 총 증거금의 30%를 최대 운용 자본으로 엄격히 제한
3. 하드코딩된 리스크 관리 모듈로 30% 한도 초과 방지
4. 실시간 시장 분석 및 적응형 거래 전략

리스크 관리:
- 최대 마진 사용률: 30%
- 동적 포지션 사이징 (시장 변동성 기반)
- 자동 손절/익절
- 연속 손실 시 자동 보호 모드
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np

# AI Agents
from src.agents.market_regime.agent import MarketRegimeAgent, MarketRegimeType
from src.agents.signal_validator.agent import SignalValidatorAgent, ValidationResult
from src.agents.risk_monitor.agent import RiskMonitorAgent
from src.agents.portfolio_optimizer.agent import PortfolioOptimizerAgent

# Services
from src.services import get_ai_service_instance
from src.services.risk_engine import (
    calculate_position_size,
    should_stop_loss,
    should_take_profit,
    liquidation_check
)

logger = logging.getLogger(__name__)


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
    """보호 모드"""
    NORMAL = "normal"
    CAUTIOUS = "cautious"      # 연속 2회 손실 후
    DEFENSIVE = "defensive"    # 연속 3회 손실 후
    LOCKDOWN = "lockdown"      # 연속 5회 손실 또는 일일 손실 한도 도달


@dataclass
class MarginStatus:
    """마진 상태 정보"""
    total_balance: float           # 총 잔고
    available_margin: float        # 사용 가능 마진 (30% 한도 내)
    used_margin: float             # 현재 사용 중인 마진
    margin_usage_percent: float    # 마진 사용률 (%)
    remaining_margin: float        # 남은 마진 (30% 한도 - 사용 중)
    can_open_position: bool        # 신규 포지션 진입 가능 여부
    max_position_value: float      # 최대 가능 포지션 가치


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
    holding_duration: timedelta    # 홀딩 시간
    entry_time: datetime           # 진입 시간


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
    market_regime: str
    ai_enhanced: bool = True
    warnings: List[str] = field(default_factory=list)


class MarginCapEnforcer:
    """
    30% 마진 한도 강제 모듈

    이 모듈은 하드코딩되어 있으며, 어떠한 상황에서도
    총 마진 사용률이 30%를 초과하지 않도록 보장합니다.
    """

    # === 하드코딩된 리스크 파라미터 (수정 불가) ===
    MAX_MARGIN_PERCENT = 30.0      # 최대 마진 사용률 (%)
    SAFETY_BUFFER_PERCENT = 2.0   # 안전 버퍼 (실제 28% 사용)
    MIN_FREE_MARGIN_PERCENT = 5.0 # 최소 유지 마진 (%)

    def __init__(self):
        self._effective_max = self.MAX_MARGIN_PERCENT - self.SAFETY_BUFFER_PERCENT
        logger.info(
            f"[MarginCapEnforcer] Initialized with "
            f"MAX={self.MAX_MARGIN_PERCENT}%, "
            f"EFFECTIVE={self._effective_max}%"
        )

    async def get_margin_status(
        self,
        exchange_client,
        current_positions: List[PositionInfo] = None
    ) -> MarginStatus:
        """
        현재 마진 상태 조회

        Returns:
            MarginStatus: 현재 마진 상태
        """
        try:
            # 잔고 조회
            balance = await exchange_client.fetch_balance()
            usdt_balance = balance.get("USDT", {})
            total_balance = float(usdt_balance.get("total", 0))
            free_balance = float(usdt_balance.get("free", 0))
            used_balance = float(usdt_balance.get("used", 0))

            # 30% 마진 한도 계산
            max_margin = total_balance * (self._effective_max / 100)

            # 현재 사용 중인 마진 계산
            used_margin = 0.0
            if current_positions:
                for pos in current_positions:
                    used_margin += pos.margin_used
            else:
                # 거래소에서 직접 조회
                used_margin = used_balance

            # 마진 사용률
            margin_usage_percent = (used_margin / total_balance * 100) if total_balance > 0 else 0

            # 남은 마진
            remaining_margin = max(0, max_margin - used_margin)

            # 신규 포지션 가능 여부
            can_open = remaining_margin > (total_balance * self.MIN_FREE_MARGIN_PERCENT / 100)

            return MarginStatus(
                total_balance=total_balance,
                available_margin=max_margin,
                used_margin=used_margin,
                margin_usage_percent=margin_usage_percent,
                remaining_margin=remaining_margin,
                can_open_position=can_open,
                max_position_value=remaining_margin
            )

        except Exception as e:
            logger.error(f"[MarginCapEnforcer] Error getting margin status: {e}")
            # 안전 모드: 거래 불가능으로 반환
            return MarginStatus(
                total_balance=0,
                available_margin=0,
                used_margin=0,
                margin_usage_percent=100,
                remaining_margin=0,
                can_open_position=False,
                max_position_value=0
            )

    def validate_order(
        self,
        order_margin_required: float,
        margin_status: MarginStatus
    ) -> Tuple[bool, str, float]:
        """
        주문 검증 - 30% 한도 초과 여부 확인

        Args:
            order_margin_required: 주문에 필요한 마진
            margin_status: 현재 마진 상태

        Returns:
            (허용 여부, 메시지, 조정된 마진 금액)
        """
        # 절대 한도 체크
        projected_usage = margin_status.used_margin + order_margin_required
        projected_percent = (projected_usage / margin_status.total_balance * 100) if margin_status.total_balance > 0 else 100

        if projected_percent > self.MAX_MARGIN_PERCENT:
            # 허용 불가 - 한도 초과
            max_allowed = margin_status.remaining_margin
            return (
                False,
                f"❌ 마진 한도 초과: {projected_percent:.1f}% > {self.MAX_MARGIN_PERCENT}%",
                max_allowed
            )

        if projected_percent > self._effective_max:
            # 조정 필요 - 안전 버퍼 침범
            adjusted_margin = margin_status.remaining_margin * 0.9  # 90%만 사용
            return (
                True,
                f"⚠️ 마진 조정: {order_margin_required:.2f} → {adjusted_margin:.2f}",
                adjusted_margin
            )

        # 허용
        return (
            True,
            f"✅ 마진 허용: {projected_percent:.1f}% / {self.MAX_MARGIN_PERCENT}%",
            order_margin_required
        )

    def calculate_safe_position_size(
        self,
        margin_status: MarginStatus,
        current_price: float,
        leverage: int,
        side: str = "long"
    ) -> float:
        """
        30% 한도 내에서 안전한 포지션 크기 계산

        Returns:
            안전한 포지션 크기 (수량)
        """
        if not margin_status.can_open_position:
            return 0.0

        # 사용 가능한 마진의 80%만 사용 (추가 안전 마진)
        safe_margin = margin_status.remaining_margin * 0.8

        # 포지션 크기 = (마진 * 레버리지) / 가격
        position_value = safe_margin * leverage
        position_size = position_value / current_price

        # 최소 주문 단위로 반올림
        position_size = round(position_size, 6)

        return max(0.001, position_size)  # 최소 0.001


class Autonomous30PctStrategy:
    """
    RealTime Autonomous 30% Margin Strategy

    AI 에이전트에게 완전한 자율권을 부여하면서도
    30% 마진 한도를 엄격히 준수하는 실전 거래 전략
    """

    def __init__(self, config: Dict[str, Any]):
        """
        전략 초기화

        Args:
            config: 전략 설정
                - symbol: 거래 심볼 (기본: "BTC/USDT")
                - timeframe: 시간프레임 (기본: "1h")
                - enable_ai: AI 활성화 (기본: True)
                - base_leverage: 기본 레버리지 (기본: 10)
                - max_leverage: 최대 레버리지 (기본: 20)
        """
        self.config = config
        self.symbol = config.get("symbol", "BTC/USDT")
        self.timeframe = config.get("timeframe", "1h")
        self.enable_ai = config.get("enable_ai", True)
        self.base_leverage = config.get("base_leverage", 10)
        self.max_leverage = config.get("max_leverage", 20)

        # === 마진 한도 강제 모듈 (하드코딩) ===
        self.margin_enforcer = MarginCapEnforcer()

        # AI 서비스 초기화
        try:
            self.ai_service = get_ai_service_instance() if self.enable_ai else None
        except Exception as e:
            logger.warning(f"AI service not available: {e}")
            self.ai_service = None
            self.enable_ai = False

        # AI 에이전트 초기화
        self._init_agents()

        # 전략 상태
        self.current_regime = None
        self.protection_mode = ProtectionMode.NORMAL
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.trade_history: List[Dict] = []
        self.current_positions: List[PositionInfo] = []

        # 자율 거래 통계
        self.stats = {
            "total_decisions": 0,
            "autonomous_entries": 0,
            "autonomous_exits": 0,
            "margin_limit_blocks": 0,
            "protection_mode_activations": 0
        }

        logger.info(
            f"✅ Autonomous 30% Strategy initialized: "
            f"Symbol={self.symbol}, AI={self.enable_ai}, "
            f"MaxMargin={MarginCapEnforcer.MAX_MARGIN_PERCENT}%"
        )

    def _init_agents(self):
        """AI 에이전트 초기화"""
        if self.enable_ai and self.ai_service:
            self.market_regime_agent = MarketRegimeAgent(
                config={
                    "enable_ai": True,
                    "atr_period": 14,
                    "adx_period": 14,
                    "volatility_threshold": 0.02,
                },
                ai_service=self.ai_service
            )

            self.signal_validator = SignalValidatorAgent(
                config={
                    "enable_ai": True,
                    "min_passed_rules": 7,
                    "critical_rules": ["price_sanity", "market_hours", "balance_check"],
                },
                ai_service=self.ai_service
            )

            self.risk_monitor = RiskMonitorAgent(
                config={
                    "max_position_loss_percent": 5.0,
                    "max_daily_loss": 1000,
                    "max_drawdown_percent": 10.0,
                    "enable_ai": True
                },
                ai_service=self.ai_service
            )

            self.portfolio_optimizer = PortfolioOptimizerAgent(
                config={
                    "enable_ai": True,
                    "max_position_size": 0.30,  # 30% 한도와 일치
                    "rebalance_threshold": 0.1,
                },
                ai_service=self.ai_service
            )

            logger.info("✅ All 4 AI agents initialized for autonomous trading")
        else:
            self.market_regime_agent = None
            self.signal_validator = None
            self.risk_monitor = None
            self.portfolio_optimizer = None
            logger.warning("⚠️ AI agents disabled")

    async def analyze_and_decide(
        self,
        exchange,
        user_id: int,
        current_positions: List[PositionInfo] = None
    ) -> AutonomousDecision:
        """
        자율 분석 및 거래 결정

        AI 에이전트에게 완전한 자율권을 부여하여 거래 결정을 내립니다.
        단, 30% 마진 한도는 반드시 준수됩니다.

        Args:
            exchange: CCXT 거래소 인스턴스
            user_id: 사용자 ID
            current_positions: 현재 포지션 목록

        Returns:
            AutonomousDecision: AI의 자율적 거래 결정
        """
        self.stats["total_decisions"] += 1

        try:
            # 1. 마진 상태 확인 (30% 한도 체크)
            margin_status = await self.margin_enforcer.get_margin_status(
                exchange, current_positions
            )

            logger.info(
                f"[Margin Status] Total: ${margin_status.total_balance:.2f}, "
                f"Used: {margin_status.margin_usage_percent:.1f}%, "
                f"Remaining: ${margin_status.remaining_margin:.2f}"
            )

            # 2. 보호 모드 체크
            if self.protection_mode == ProtectionMode.LOCKDOWN:
                return AutonomousDecision(
                    decision=TradingDecision.HOLD,
                    confidence=1.0,
                    position_size_percent=0,
                    target_leverage=0,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning="🔒 LOCKDOWN MODE: Trading suspended due to consecutive losses",
                    market_regime="unknown",
                    warnings=["Trading locked due to risk limits"]
                )

            # 3. 시장 데이터 가져오기
            ohlcv = await exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=200)
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            current_price = float(df["close"].iloc[-1])

            # 4. AI 시장 체제 분석
            regime = await self._analyze_market_regime(exchange, df)
            self.current_regime = regime

            # 5. 기술적 지표 계산
            df = self._calculate_indicators(df)

            # 6. AI 자율 결정 생성
            decision = await self._make_autonomous_decision(
                df, current_price, regime, margin_status, current_positions
            )

            # 7. 30% 마진 한도 강제 적용
            decision = self._enforce_margin_limit(decision, margin_status, current_price)

            # 8. 신호 검증 (AI)
            if decision.decision not in [TradingDecision.HOLD, TradingDecision.EMERGENCY_EXIT]:
                decision = await self._validate_decision(decision, current_price, regime)

            # 9. 통계 업데이트
            if decision.decision in [TradingDecision.ENTER_LONG, TradingDecision.ENTER_SHORT]:
                self.stats["autonomous_entries"] += 1
            elif decision.decision in [TradingDecision.EXIT_LONG, TradingDecision.EXIT_SHORT]:
                self.stats["autonomous_exits"] += 1

            logger.info(
                f"[Autonomous Decision] {decision.decision.value} | "
                f"Confidence: {decision.confidence:.1%} | "
                f"Size: {decision.position_size_percent:.1f}% | "
                f"Regime: {decision.market_regime}"
            )

            return decision

        except Exception as e:
            logger.error(f"[Autonomous] Analysis failed: {e}", exc_info=True)
            return AutonomousDecision(
                decision=TradingDecision.HOLD,
                confidence=0.0,
                position_size_percent=0,
                target_leverage=self.base_leverage,
                stop_loss_percent=5.0,
                take_profit_percent=10.0,
                reasoning=f"Analysis error: {str(e)}",
                market_regime="unknown",
                ai_enhanced=False
            )

    async def _analyze_market_regime(self, exchange, df: pd.DataFrame) -> Any:
        """시장 체제 분석"""
        if self.market_regime_agent:
            try:
                regime = await self.market_regime_agent.analyze_market_realtime({
                    "symbol": self.symbol,
                    "exchange": exchange,
                    "timeframe": self.timeframe
                })
                return regime
            except Exception as e:
                logger.warning(f"Market regime analysis failed: {e}")

        # Fallback: 규칙 기반
        return self._simple_regime_detection(df)

    async def _make_autonomous_decision(
        self,
        df: pd.DataFrame,
        current_price: float,
        regime: Any,
        margin_status: MarginStatus,
        current_positions: List[PositionInfo]
    ) -> AutonomousDecision:
        """
        AI 자율 거래 결정

        모든 거래 파라미터(진입, 청산, 크기, 레버리지)를 AI가 자율적으로 결정합니다.
        """
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        regime_type = regime.regime_type if regime else None

        # 현재 포지션 분석
        has_long = any(p.side == "long" for p in (current_positions or []))
        has_short = any(p.side == "short" for p in (current_positions or []))

        # 포지션 보유 중이면 청산 조건 먼저 확인
        if current_positions:
            exit_decision = await self._check_exit_conditions(
                current_positions, df, current_price, regime
            )
            if exit_decision.decision != TradingDecision.HOLD:
                return exit_decision

        # 신규 진입 불가능하면 HOLD
        if not margin_status.can_open_position:
            self.stats["margin_limit_blocks"] += 1
            return AutonomousDecision(
                decision=TradingDecision.HOLD,
                confidence=0.5,
                position_size_percent=0,
                target_leverage=self.base_leverage,
                stop_loss_percent=0,
                take_profit_percent=0,
                reasoning=f"⚠️ Margin limit reached: {margin_status.margin_usage_percent:.1f}%",
                market_regime=regime_type.value if regime_type else "unknown",
                warnings=["30% margin limit reached - no new positions allowed"]
            )

        # === AI 자율 진입 결정 ===

        # 변동성 기반 동적 파라미터
        volatility = self._calculate_volatility(df)
        dynamic_leverage = self._calculate_dynamic_leverage(volatility, regime_type)
        dynamic_position_size = self._calculate_dynamic_position_size(
            volatility, regime_type, margin_status
        )
        dynamic_sl, dynamic_tp = self._calculate_dynamic_sl_tp(volatility, regime_type)

        # 시장 체제별 진입 전략
        if regime_type == MarketRegimeType.TRENDING_UP:
            if self._is_strong_bullish_signal(latest, prev, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.85,
                    position_size_percent=dynamic_position_size,
                    target_leverage=dynamic_leverage,
                    stop_loss_percent=dynamic_sl,
                    take_profit_percent=dynamic_tp,
                    reasoning="Strong bullish trend: EMA alignment + momentum confirmation",
                    market_regime="trending_up",
                    ai_enhanced=self.enable_ai
                )

        elif regime_type == MarketRegimeType.TRENDING_DOWN:
            if self._is_strong_bearish_signal(latest, prev, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.80,
                    position_size_percent=dynamic_position_size * 0.8,  # 숏은 더 보수적
                    target_leverage=dynamic_leverage,
                    stop_loss_percent=dynamic_sl,
                    take_profit_percent=dynamic_tp,
                    reasoning="Strong bearish trend: Price below EMAs + selling pressure",
                    market_regime="trending_down",
                    ai_enhanced=self.enable_ai
                )

        elif regime_type == MarketRegimeType.RANGING:
            if self._is_oversold_reversal(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.75,
                    position_size_percent=dynamic_position_size * 0.6,
                    target_leverage=min(dynamic_leverage, 8),
                    stop_loss_percent=dynamic_sl * 0.8,
                    take_profit_percent=dynamic_tp * 0.7,
                    reasoning="Mean reversion: Oversold at support",
                    market_regime="ranging",
                    ai_enhanced=self.enable_ai
                )
            elif self._is_overbought_reversal(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_SHORT,
                    confidence=0.70,
                    position_size_percent=dynamic_position_size * 0.5,
                    target_leverage=min(dynamic_leverage, 5),
                    stop_loss_percent=dynamic_sl * 0.8,
                    take_profit_percent=dynamic_tp * 0.7,
                    reasoning="Mean reversion: Overbought at resistance",
                    market_regime="ranging",
                    ai_enhanced=self.enable_ai
                )

        elif regime_type == MarketRegimeType.HIGH_VOLATILITY:
            # 고변동성: 매우 강한 신호만
            if self._is_extreme_oversold(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.ENTER_LONG,
                    confidence=0.70,
                    position_size_percent=dynamic_position_size * 0.4,
                    target_leverage=min(dynamic_leverage, 5),
                    stop_loss_percent=dynamic_sl * 1.5,
                    take_profit_percent=dynamic_tp * 1.5,
                    reasoning="Extreme volatility: Extreme oversold with volume spike",
                    market_regime="high_volatility",
                    ai_enhanced=self.enable_ai,
                    warnings=["High volatility - reduced position size"]
                )

        # 기본: HOLD
        return AutonomousDecision(
            decision=TradingDecision.HOLD,
            confidence=0.5,
            position_size_percent=0,
            target_leverage=self.base_leverage,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning=f"No clear signal in {regime_type.value if regime_type else 'unknown'} regime",
            market_regime=regime_type.value if regime_type else "unknown",
            ai_enhanced=self.enable_ai
        )

    async def _check_exit_conditions(
        self,
        positions: List[PositionInfo],
        df: pd.DataFrame,
        current_price: float,
        regime: Any
    ) -> AutonomousDecision:
        """청산 조건 확인"""
        latest = df.iloc[-1]

        for pos in positions:
            # 손절 조건
            if should_stop_loss(pos.entry_price, current_price, pos.unrealized_pnl_percent * -1):
                return AutonomousDecision(
                    decision=TradingDecision.EXIT_LONG if pos.side == "long" else TradingDecision.EXIT_SHORT,
                    confidence=1.0,
                    position_size_percent=100,  # 전량 청산
                    target_leverage=pos.leverage,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning=f"⛔ Stop Loss triggered: {pos.unrealized_pnl_percent:.2f}%",
                    market_regime=regime.regime_type.value if regime else "unknown"
                )

            # 익절 조건
            if should_take_profit(pos.entry_price, current_price, pos.unrealized_pnl_percent):
                return AutonomousDecision(
                    decision=TradingDecision.EXIT_LONG if pos.side == "long" else TradingDecision.EXIT_SHORT,
                    confidence=0.9,
                    position_size_percent=100,
                    target_leverage=pos.leverage,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning=f"✅ Take Profit triggered: {pos.unrealized_pnl_percent:.2f}%",
                    market_regime=regime.regime_type.value if regime else "unknown"
                )

            # 청산 위험
            if liquidation_check(pos.entry_price, current_price, pos.leverage):
                return AutonomousDecision(
                    decision=TradingDecision.EMERGENCY_EXIT,
                    confidence=1.0,
                    position_size_percent=100,
                    target_leverage=pos.leverage,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning="🚨 EMERGENCY: Near liquidation price",
                    market_regime=regime.regime_type.value if regime else "unknown",
                    warnings=["CRITICAL: Position near liquidation"]
                )

            # 추세 반전 청산 (롱 포지션)
            if pos.side == "long" and self._is_trend_reversal_bearish(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.EXIT_LONG,
                    confidence=0.75,
                    position_size_percent=100,
                    target_leverage=pos.leverage,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning="Trend reversal detected: Bearish signal",
                    market_regime=regime.regime_type.value if regime else "unknown"
                )

            # 추세 반전 청산 (숏 포지션)
            if pos.side == "short" and self._is_trend_reversal_bullish(latest, df):
                return AutonomousDecision(
                    decision=TradingDecision.EXIT_SHORT,
                    confidence=0.75,
                    position_size_percent=100,
                    target_leverage=pos.leverage,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning="Trend reversal detected: Bullish signal",
                    market_regime=regime.regime_type.value if regime else "unknown"
                )

        return AutonomousDecision(
            decision=TradingDecision.HOLD,
            confidence=0.5,
            position_size_percent=0,
            target_leverage=self.base_leverage,
            stop_loss_percent=0,
            take_profit_percent=0,
            reasoning="Position held - no exit conditions met",
            market_regime=regime.regime_type.value if regime else "unknown"
        )

    def _enforce_margin_limit(
        self,
        decision: AutonomousDecision,
        margin_status: MarginStatus,
        current_price: float
    ) -> AutonomousDecision:
        """
        30% 마진 한도 강제 적용

        AI의 결정이 30% 한도를 초과할 경우 자동으로 조정합니다.
        """
        if decision.decision == TradingDecision.HOLD:
            return decision

        if decision.decision in [TradingDecision.ENTER_LONG, TradingDecision.ENTER_SHORT]:
            # 요청된 마진 계산
            requested_margin = (
                margin_status.total_balance *
                (decision.position_size_percent / 100)
            )

            # 마진 한도 검증
            allowed, msg, adjusted_margin = self.margin_enforcer.validate_order(
                requested_margin, margin_status
            )

            if not allowed:
                # 한도 초과 - HOLD로 변경
                self.stats["margin_limit_blocks"] += 1
                logger.warning(f"[Margin Enforcer] {msg}")
                return AutonomousDecision(
                    decision=TradingDecision.HOLD,
                    confidence=decision.confidence,
                    position_size_percent=0,
                    target_leverage=decision.target_leverage,
                    stop_loss_percent=decision.stop_loss_percent,
                    take_profit_percent=decision.take_profit_percent,
                    reasoning=f"Blocked by margin limit: {msg}",
                    market_regime=decision.market_regime,
                    ai_enhanced=decision.ai_enhanced,
                    warnings=decision.warnings + [msg]
                )

            if adjusted_margin < requested_margin:
                # 마진 조정됨
                adjusted_percent = (adjusted_margin / margin_status.total_balance) * 100
                logger.info(f"[Margin Enforcer] {msg}")
                decision.position_size_percent = adjusted_percent
                decision.warnings.append(f"Position size adjusted: {adjusted_percent:.1f}%")

        return decision

    async def _validate_decision(
        self,
        decision: AutonomousDecision,
        current_price: float,
        regime: Any
    ) -> AutonomousDecision:
        """AI 신호 검증"""
        if not self.signal_validator:
            return decision

        try:
            validation = await self.signal_validator.validate_signal({
                "signal_id": f"AUTO_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "symbol": self.symbol,
                "action": "BUY" if "long" in decision.decision.value else "SELL",
                "confidence": decision.confidence,
                "current_price": current_price,
                "market_regime": regime,
            })

            if validation.validation_result == ValidationResult.REJECTED:
                return AutonomousDecision(
                    decision=TradingDecision.HOLD,
                    confidence=decision.confidence,
                    position_size_percent=0,
                    target_leverage=decision.target_leverage,
                    stop_loss_percent=0,
                    take_profit_percent=0,
                    reasoning=f"Signal rejected: {', '.join(validation.failed_rules)}",
                    market_regime=decision.market_regime,
                    ai_enhanced=True,
                    warnings=decision.warnings + validation.warnings
                )

            elif validation.validation_result == ValidationResult.APPROVED_WITH_CONDITIONS:
                decision.confidence *= 0.8
                decision.warnings.extend(validation.warnings)

        except Exception as e:
            logger.warning(f"Signal validation failed: {e}")

        return decision

    # === 기술적 분석 헬퍼 메서드 ===

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        # EMA
        df["ema_9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
        df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
        df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()

        # RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df["bb_middle"] = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * 2)
        df["bb_lower"] = df["bb_middle"] - (bb_std * 2)

        # MACD
        exp1 = df["close"].ewm(span=12, adjust=False).mean()
        exp2 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = exp1 - exp2
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # ATR
        high_low = df["high"] - df["low"]
        high_close = abs(df["high"] - df["close"].shift())
        low_close = abs(df["low"] - df["close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(window=14).mean()

        # Volume SMA
        df["volume_sma"] = df["volume"].rolling(window=20).mean()

        return df

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """변동성 계산"""
        if "atr" not in df.columns:
            df = self._calculate_indicators(df)
        return float(df["atr"].iloc[-1] / df["close"].iloc[-1])

    def _calculate_dynamic_leverage(self, volatility: float, regime_type) -> int:
        """동적 레버리지 계산"""
        if volatility > 0.03:
            return min(5, self.base_leverage)
        elif volatility > 0.02:
            return min(8, self.base_leverage)
        elif regime_type == MarketRegimeType.TRENDING_UP:
            return min(15, self.max_leverage)
        else:
            return self.base_leverage

    def _calculate_dynamic_position_size(
        self,
        volatility: float,
        regime_type,
        margin_status: MarginStatus
    ) -> float:
        """동적 포지션 크기 계산 (30% 한도 내)"""
        # 기본: 사용 가능한 마진의 50%
        base_size = 50.0

        # 변동성에 따른 조정
        if volatility > 0.03:
            base_size *= 0.3
        elif volatility > 0.02:
            base_size *= 0.5

        # 시장 체제에 따른 조정
        if regime_type == MarketRegimeType.TRENDING_UP:
            base_size *= 1.0
        elif regime_type == MarketRegimeType.TRENDING_DOWN:
            base_size *= 0.7
        elif regime_type == MarketRegimeType.RANGING:
            base_size *= 0.5
        elif regime_type == MarketRegimeType.HIGH_VOLATILITY:
            base_size *= 0.3

        # 보호 모드에 따른 조정
        if self.protection_mode == ProtectionMode.CAUTIOUS:
            base_size *= 0.5
        elif self.protection_mode == ProtectionMode.DEFENSIVE:
            base_size *= 0.25

        # 30% 한도 대비 비율로 변환
        # (30% 한도 중 X% 사용)
        return min(base_size, 80.0)  # 최대 80% (30%의 80% = 24%)

    def _calculate_dynamic_sl_tp(self, volatility: float, regime_type) -> Tuple[float, float]:
        """동적 손절/익절 계산"""
        base_sl = 2.0
        base_tp = 4.0

        if volatility > 0.03:
            return base_sl * 2.0, base_tp * 2.0
        elif volatility > 0.02:
            return base_sl * 1.5, base_tp * 1.5

        if regime_type == MarketRegimeType.TRENDING_UP:
            return base_sl, base_tp * 1.5
        elif regime_type == MarketRegimeType.RANGING:
            return base_sl * 0.8, base_tp * 0.7

        return base_sl, base_tp

    # === 신호 감지 메서드 ===

    def _is_strong_bullish_signal(self, latest, prev, df) -> bool:
        """강한 상승 신호 감지"""
        return (
            latest["close"] > latest["ema_21"] and
            latest["ema_21"] > latest["ema_50"] and
            latest["rsi"] > 50 and latest["rsi"] < 75 and
            latest["macd"] > latest["macd_signal"] and
            latest["macd_hist"] > prev["macd_hist"] and
            latest["volume"] > latest["volume_sma"] * 1.2
        )

    def _is_strong_bearish_signal(self, latest, prev, df) -> bool:
        """강한 하락 신호 감지"""
        return (
            latest["close"] < latest["ema_21"] and
            latest["ema_21"] < latest["ema_50"] and
            latest["rsi"] < 50 and latest["rsi"] > 25 and
            latest["macd"] < latest["macd_signal"] and
            latest["macd_hist"] < prev["macd_hist"] and
            latest["volume"] > latest["volume_sma"] * 1.2
        )

    def _is_oversold_reversal(self, latest, df) -> bool:
        """과매도 반전 신호"""
        return (
            latest["rsi"] < 30 and
            latest["close"] < latest["bb_lower"] and
            latest["close"] > latest["close"] * 0.99  # 하락세 둔화
        )

    def _is_overbought_reversal(self, latest, df) -> bool:
        """과매수 반전 신호"""
        return (
            latest["rsi"] > 70 and
            latest["close"] > latest["bb_upper"]
        )

    def _is_extreme_oversold(self, latest, df) -> bool:
        """극단적 과매도"""
        return (
            latest["rsi"] < 20 and
            latest["close"] < latest["bb_lower"] * 0.98 and
            latest["volume"] > latest["volume_sma"] * 2.0
        )

    def _is_trend_reversal_bearish(self, latest, df) -> bool:
        """하락 추세 반전 신호"""
        return (
            latest["close"] < latest["ema_21"] and
            latest["macd"] < latest["macd_signal"] and
            latest["rsi"] < 45
        )

    def _is_trend_reversal_bullish(self, latest, df) -> bool:
        """상승 추세 반전 신호"""
        return (
            latest["close"] > latest["ema_21"] and
            latest["macd"] > latest["macd_signal"] and
            latest["rsi"] > 55
        )

    def _simple_regime_detection(self, df: pd.DataFrame):
        """간단한 규칙 기반 체제 감지"""
        from src.agents.market_regime.agent import MarketRegime, MarketRegimeType

        df = self._calculate_indicators(df)
        latest = df.iloc[-1]

        if latest["ema_21"] > latest["ema_50"] * 1.02:
            regime_type = MarketRegimeType.TRENDING_UP
        elif latest["ema_21"] < latest["ema_50"] * 0.98:
            regime_type = MarketRegimeType.TRENDING_DOWN
        else:
            regime_type = MarketRegimeType.RANGING

        volatility = float(latest["atr"] / latest["close"])
        if volatility > 0.03:
            regime_type = MarketRegimeType.HIGH_VOLATILITY

        return MarketRegime(
            regime_type=regime_type,
            confidence=0.6,
            volatility=volatility,
            trend_strength=0.5,
            timestamp=datetime.now(),
            indicators={},
            ai_enhanced=False
        )

    # === 상태 관리 ===

    def update_protection_mode(self, trade_result: Dict[str, Any]):
        """거래 결과에 따른 보호 모드 업데이트"""
        if trade_result.get("pnl", 0) < 0:
            self.consecutive_losses += 1
            self.daily_pnl += trade_result.get("pnl", 0)
        else:
            self.consecutive_losses = 0
            self.daily_pnl += trade_result.get("pnl", 0)

        # 보호 모드 결정
        old_mode = self.protection_mode

        if self.consecutive_losses >= 5 or self.daily_pnl < -1000:
            self.protection_mode = ProtectionMode.LOCKDOWN
        elif self.consecutive_losses >= 3:
            self.protection_mode = ProtectionMode.DEFENSIVE
        elif self.consecutive_losses >= 2:
            self.protection_mode = ProtectionMode.CAUTIOUS
        else:
            self.protection_mode = ProtectionMode.NORMAL

        if old_mode != self.protection_mode:
            self.stats["protection_mode_activations"] += 1
            logger.warning(
                f"[Protection Mode] Changed: {old_mode.value} → {self.protection_mode.value}"
            )

    def reset_daily_stats(self):
        """일일 통계 초기화 (매일 0시)"""
        self.daily_pnl = 0.0
        if self.protection_mode == ProtectionMode.LOCKDOWN:
            self.protection_mode = ProtectionMode.DEFENSIVE
            logger.info("[Protection Mode] Daily reset: LOCKDOWN → DEFENSIVE")

    def get_statistics(self) -> Dict[str, Any]:
        """전략 통계 반환"""
        return {
            "strategy_name": "RealTime_Autonomous_30pct",
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "max_margin_percent": MarginCapEnforcer.MAX_MARGIN_PERCENT,
            "ai_enabled": self.enable_ai,
            "protection_mode": self.protection_mode.value,
            "consecutive_losses": self.consecutive_losses,
            "daily_pnl": self.daily_pnl,
            "current_regime": self.current_regime.regime_type.value if self.current_regime else "unknown",
            **self.stats
        }
