"""
AI Integrated Smart Strategy (AI 통합 스마트 전략)

4개의 AI 에이전트를 활용한 완벽한 트레이딩 전략:
- Market Regime Agent: 시장 체제 실시간 분석
- Signal Validator Agent: 11가지 규칙 기반 신호 검증
- Anomaly Detector Agent: 이상 거래 패턴 감지
- Portfolio Optimizer Agent: 리스크 관리 및 포트폴리오 최적화

DeepSeek-V3.2 API를 활용하여 비용 효율적으로 운영됩니다.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd
import ccxt

# AI Agents
from src.agents.market_regime.agent import MarketRegimeAgent, MarketRegimeType
from src.agents.signal_validator.agent import SignalValidatorAgent, ValidationResult
from src.agents.anomaly_detector.agent import AnomalyDetectorAgent
from src.agents.portfolio_optimizer.agent import PortfolioOptimizerAgent

# AI Service
from src.services import get_ai_service_instance

logger = logging.getLogger(__name__)


class AIIntegratedSmartStrategy:
    """
    AI 통합 스마트 전략

    특징:
    - 시장 체제 기반 동적 파라미터 조정
    - AI 신호 검증으로 정확도 향상
    - 이상 감지로 리스크 최소화
    - 포트폴리오 최적화로 수익 극대화
    """

    def __init__(self, config: Dict[str, Any]):
        """
        전략 초기화

        Args:
            config: 전략 설정
                - symbol: 거래 심볼 (예: "BTC/USDT")
                - timeframe: 시간프레임 (예: "1h")
                - enable_ai: AI 에이전트 활성화 여부
                - risk_level: 리스크 레벨 ("conservative", "moderate", "aggressive")
                - max_position_size: 최대 포지션 크기 (예: 0.3 = 30%)
        """
        self.config = config
        self.symbol = config.get("symbol", "BTC/USDT")
        self.timeframe = config.get("timeframe", "1h")
        self.enable_ai = config.get("enable_ai", True)
        self.risk_level = config.get("risk_level", "moderate")
        self.max_position_size = config.get("max_position_size", 0.3)

        # AI Service 초기화
        try:
            self.ai_service = get_ai_service_instance() if self.enable_ai else None
        except Exception as e:
            logger.warning(f"AI service not available: {e}. Running without AI.")
            self.ai_service = None
            self.enable_ai = False

        # AI Agents 초기화
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
                    "min_passed_rules": 8,  # 11개 중 8개 이상 통과
                    "critical_rules": ["price_sanity", "market_hours"],
                },
                ai_service=self.ai_service
            )

            self.anomaly_detector = AnomalyDetectorAgent(
                config={
                    "enable_ai": True,
                    "check_interval_seconds": 60,
                    "anomaly_thresholds": {
                        "latency_ms": 5000,
                        "error_rate_percent": 5.0,
                        "loss_streak": 3,  # 연속 3회 손실 시 경고
                    }
                },
                ai_service=self.ai_service
            )

            self.portfolio_optimizer = PortfolioOptimizerAgent(
                config={
                    "enable_ai": True,
                    "rebalance_threshold": 0.1,
                    "max_position_size": self.max_position_size,
                    "risk_levels": {
                        "conservative": {"max_drawdown": 0.05, "target_sharpe": 1.0},
                        "moderate": {"max_drawdown": 0.10, "target_sharpe": 1.5},
                        "aggressive": {"max_drawdown": 0.15, "target_sharpe": 2.0}
                    }
                },
                ai_service=self.ai_service
            )

            logger.info("✅ AI Integrated Smart Strategy initialized with 4 AI agents")
        else:
            self.market_regime_agent = None
            self.signal_validator = None
            self.anomaly_detector = None
            self.portfolio_optimizer = None
            logger.warning("⚠️  AI agents disabled")

        # 전략 상태
        self.current_regime = None
        self.last_signal_time = None
        self.consecutive_losses = 0
        self.trade_history = []

    async def analyze(
        self,
        exchange: ccxt.Exchange,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        시장 분석 및 거래 신호 생성

        Args:
            exchange: CCXT 거래소 인스턴스
            symbol: 거래 심볼
            timeframe: 시간프레임
            limit: 캔들 개수

        Returns:
            분석 결과 및 신호
        """
        try:
            # 1. 시장 데이터 가져오기
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            current_price = float(df["close"].iloc[-1])

            # 2. Market Regime 분석 (AI Enhanced)
            if self.market_regime_agent:
                regime = await self.market_regime_agent.analyze_market_realtime({
                    "symbol": symbol,
                    "exchange": exchange,
                    "timeframe": timeframe
                })
                self.current_regime = regime

                logger.info(
                    f"Market Regime: {regime.regime_type.value} "
                    f"(Confidence: {regime.confidence:.2%}, AI: {regime.ai_enhanced})"
                )
            else:
                # Fallback: 간단한 규칙 기반 분석
                regime = self._simple_regime_detection(df)
                self.current_regime = regime

            # 3. 신호 생성 (체제 기반)
            signal = await self._generate_signal(df, current_price, regime)

            # 4. Signal Validation (AI Enhanced)
            if signal["action"] != "HOLD" and self.signal_validator:
                validation = await self.signal_validator.validate_signal({
                    "signal_id": f"SIG_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "symbol": symbol,
                    "action": signal["action"],
                    "confidence": signal["confidence"],
                    "current_price": current_price,
                    "market_regime": regime,
                    "exchange": exchange
                })

                logger.info(
                    f"Signal Validation: {validation.validation_result.value} "
                    f"(Score: {validation.confidence_score:.2%}, AI: {validation.ai_enhanced})"
                )

                # 검증 실패 시 신호 취소
                if validation.validation_result == ValidationResult.REJECTED:
                    logger.warning(
                        f"Signal REJECTED by validator. "
                        f"Failed rules: {validation.failed_rules}"
                    )
                    signal["action"] = "HOLD"
                    signal["reason"] = f"Validation failed: {', '.join(validation.failed_rules)}"
                elif validation.validation_result == ValidationResult.APPROVED_WITH_CONDITIONS:
                    # 조건부 승인 시 신뢰도 조정
                    signal["confidence"] *= 0.8
                    signal["warnings"] = validation.warnings

            # 5. Anomaly Detection (비동기 실행, 신호에 영향 안 줌)
            if self.anomaly_detector:
                asyncio.create_task(self._check_anomalies())

            # 6. 최종 신호 반환
            return {
                "action": signal["action"],
                "price": current_price,
                "confidence": signal["confidence"],
                "regime": regime.regime_type.value if regime else "unknown",
                "regime_confidence": regime.confidence if regime else 0.0,
                "reason": signal.get("reason", ""),
                "warnings": signal.get("warnings", []),
                "timestamp": datetime.now().isoformat(),
                "ai_enhanced": self.enable_ai
            }

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                "action": "HOLD",
                "price": 0.0,
                "confidence": 0.0,
                "reason": f"Analysis error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def _generate_signal(
        self,
        df: pd.DataFrame,
        current_price: float,
        regime: Any
    ) -> Dict[str, Any]:
        """
        시장 체제 기반 신호 생성

        Args:
            df: OHLCV 데이터프레임
            current_price: 현재 가격
            regime: 시장 체제 정보

        Returns:
            신호 정보
        """
        # 기술적 지표 계산
        df = self._calculate_indicators(df)

        # 최근 데이터
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # 시장 체제별 전략
        regime_type = regime.regime_type if regime else None

        if regime_type == MarketRegimeType.TRENDING_UP:
            # 상승 추세: 추세 추종 전략
            if (
                latest["close"] > latest["ema_20"] and
                latest["ema_20"] > latest["ema_50"] and
                latest["rsi"] > 50 and latest["rsi"] < 70 and
                latest["macd"] > latest["macd_signal"]
            ):
                return {
                    "action": "BUY",
                    "confidence": 0.85,
                    "reason": "Trending up: Strong bullish momentum"
                }

        elif regime_type == MarketRegimeType.TRENDING_DOWN:
            # 하락 추세: 공매도 또는 관망
            if (
                latest["close"] < latest["ema_20"] and
                latest["ema_20"] < latest["ema_50"] and
                latest["rsi"] < 50 and latest["rsi"] > 30 and
                latest["macd"] < latest["macd_signal"]
            ):
                return {
                    "action": "SELL",
                    "confidence": 0.80,
                    "reason": "Trending down: Strong bearish momentum"
                }

        elif regime_type == MarketRegimeType.RANGING:
            # 횡보장: 평균 회귀 전략
            if latest["rsi"] < 30 and latest["close"] < latest["bb_lower"]:
                return {
                    "action": "BUY",
                    "confidence": 0.75,
                    "reason": "Ranging: Oversold, near support"
                }
            elif latest["rsi"] > 70 and latest["close"] > latest["bb_upper"]:
                return {
                    "action": "SELL",
                    "confidence": 0.75,
                    "reason": "Ranging: Overbought, near resistance"
                }

        elif regime_type == MarketRegimeType.HIGH_VOLATILITY:
            # 고변동성: 보수적 접근, 강한 신호만
            if (
                latest["rsi"] < 25 and
                latest["close"] < latest["bb_lower"] * 0.98 and
                latest["volume"] > df["volume"].rolling(20).mean().iloc[-1] * 1.5
            ):
                return {
                    "action": "BUY",
                    "confidence": 0.70,
                    "reason": "High volatility: Extreme oversold with volume"
                }
            elif (
                latest["rsi"] > 75 and
                latest["close"] > latest["bb_upper"] * 1.02 and
                latest["volume"] > df["volume"].rolling(20).mean().iloc[-1] * 1.5
            ):
                return {
                    "action": "SELL",
                    "confidence": 0.70,
                    "reason": "High volatility: Extreme overbought with volume"
                }

        # 기본: HOLD
        return {
            "action": "HOLD",
            "confidence": 0.5,
            "reason": f"No clear signal in {regime_type.value if regime_type else 'unknown'} regime"
        }

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        # EMA
        df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
        df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
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

        return df

    def _simple_regime_detection(self, df: pd.DataFrame) -> Any:
        """간단한 규칙 기반 체제 감지 (AI 미사용 시 fallback)"""
        from src.agents.market_regime.agent import MarketRegime, MarketRegimeType

        df = self._calculate_indicators(df)
        latest = df.iloc[-1]

        # 추세 판단
        if latest["ema_20"] > latest["ema_50"] * 1.02:
            regime_type = MarketRegimeType.TRENDING_UP
        elif latest["ema_20"] < latest["ema_50"] * 0.98:
            regime_type = MarketRegimeType.TRENDING_DOWN
        else:
            regime_type = MarketRegimeType.RANGING

        # 변동성 판단
        atr = (df["high"] - df["low"]).rolling(14).mean().iloc[-1]
        volatility = atr / latest["close"]

        if volatility > 0.03:
            regime_type = MarketRegimeType.HIGH_VOLATILITY

        return MarketRegime(
            regime_type=regime_type,
            confidence=0.6,  # Rule-based는 낮은 신뢰도
            volatility=volatility,
            trend_strength=0.5,
            timestamp=datetime.now(),
            indicators={},
            ai_enhanced=False
        )

    async def _check_anomalies(self):
        """이상 거래 패턴 감지 (비동기)"""
        try:
            if not self.anomaly_detector:
                return

            # TODO: 실제 user_id, bot_id 전달 필요
            anomalies = await self.anomaly_detector.detect_anomalies({
                "user_id": 1,  # Placeholder
                "bot_id": 1,   # Placeholder
                "timeframe_minutes": 60
            })

            if anomalies:
                logger.warning(f"⚠️  Detected {len(anomalies)} anomalies:")
                for anomaly in anomalies:
                    logger.warning(
                        f"  - {anomaly.anomaly_type.value}: {anomaly.severity.value} "
                        f"(AI: {anomaly.ai_enhanced})"
                    )
                    if anomaly.recommended_action:
                        logger.warning(f"    Action: {anomaly.recommended_action}")

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")

    async def optimize_portfolio(self, user_id: int) -> Dict[str, Any]:
        """
        포트폴리오 최적화 (별도 호출 필요)

        Args:
            user_id: 사용자 ID

        Returns:
            최적화 결과 및 AI 인사이트
        """
        try:
            if not self.portfolio_optimizer:
                return {
                    "status": "disabled",
                    "message": "Portfolio optimizer not available"
                }

            optimization = await self.portfolio_optimizer.optimize_portfolio({
                "user_id": user_id,
                "risk_level": self.risk_level,
                "include_ai_insights": True
            })

            logger.info(f"Portfolio optimization complete:")
            logger.info(f"  Sharpe Ratio: {optimization.portfolio_sharpe:.2f}")
            logger.info(f"  Max Drawdown: {optimization.max_drawdown:.2%}")

            if optimization.ai_insights:
                logger.info(f"  AI Insights: {len(optimization.ai_insights)}")
                for insight in optimization.ai_insights:
                    logger.info(f"    - {insight}")

            if optimization.ai_warnings:
                logger.warning(f"  AI Warnings: {len(optimization.ai_warnings)}")
                for warning in optimization.ai_warnings:
                    logger.warning(f"    ⚠️  {warning}")

            return {
                "status": "success",
                "portfolio_sharpe": optimization.portfolio_sharpe,
                "max_drawdown": optimization.max_drawdown,
                "recommendations": optimization.recommendations,
                "ai_insights": optimization.ai_insights,
                "ai_warnings": optimization.ai_warnings,
                "ai_recommendations": optimization.ai_recommendations
            }

        except Exception as e:
            logger.error(f"Portfolio optimization failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }

    def get_parameters(self) -> Dict[str, Any]:
        """전략 파라미터 반환"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "enable_ai": self.enable_ai,
            "risk_level": self.risk_level,
            "max_position_size": self.max_position_size,
            "current_regime": self.current_regime.regime_type.value if self.current_regime else "unknown",
            "consecutive_losses": self.consecutive_losses
        }

    def update_config(self, new_config: Dict[str, Any]):
        """전략 설정 업데이트"""
        self.config.update(new_config)

        if "risk_level" in new_config:
            self.risk_level = new_config["risk_level"]

        if "max_position_size" in new_config:
            self.max_position_size = new_config["max_position_size"]

        logger.info(f"Strategy config updated: {new_config}")
