"""
Market Regime Agent (시장 환경 분석 에이전트)

실제 Bitget API 데이터를 사용하여 시장 환경을 분석하고 Redis에 저장

AI Enhancement:
- DeepSeek-V3.2 API를 사용한 AI 기반 시장 분석
- 규칙 기반 + AI 분석 결합으로 정확도 향상
- 비용 최적화 (Prompt Caching, Response Caching, Smart Sampling)
"""

import logging
import asyncio
import json
from typing import Any, Optional
from datetime import datetime

from ..base import BaseAgent, AgentTask
from .models import MarketRegime, RegimeType
from .indicators import RegimeIndicators

logger = logging.getLogger(__name__)


class MarketRegimeAgent(BaseAgent):
    """
    시장 환경 분석 에이전트 (실제 데이터 연동)

    주요 기능:
    1. Bitget API / Candle Cache에서 실시간 캔들 데이터 수집
    2. 기술적 지표 계산 (ATR, ADX, Bollinger Bands, EMA, Volume)
    3. 시장 환경 판단:
       - TRENDING: ADX > 25
       - RANGING: ADX < 20
       - VOLATILE: ATR이 평균의 2배 이상
       - LOW_VOLUME: 거래량이 평균의 30% 미만
    4. 결과를 Redis에 저장 (agent:market_regime:current)
    5. 1분마다 자동 실행

    작업 타입:
    - analyze_market: 시장 환경 분석 (실시간)
    - get_current_regime: 현재 시장 환경 조회
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        config: dict = None,
        bitget_client=None,
        candle_cache=None,
        redis_client=None,
        ai_service=None
    ):
        super().__init__(agent_id, name, config)
        self.indicators = RegimeIndicators()
        self._current_regime: Optional[MarketRegime] = None

        # 외부 의존성
        self.bitget_client = bitget_client
        self.candle_cache = candle_cache
        self.redis_client = redis_client
        self.ai_service = ai_service  # IntegratedAIService

        # 설정 (config에서 가져오거나 기본값)
        self.symbol = config.get("symbol", "BTCUSDT") if config else "BTCUSDT"
        self.timeframe = config.get("timeframe", "1h") if config else "1h"
        self.candle_limit = config.get("candle_limit", 200) if config else 200
        self.enable_ai = config.get("enable_ai", True) if config else True  # AI 활성화

        # 임계값
        self.trending_adx_threshold = 25.0
        self.ranging_adx_threshold = 20.0
        self.volatile_atr_multiplier = 2.0
        self.low_volume_threshold = 0.3  # 30%

        logger.info(
            f"MarketRegimeAgent initialized: {self.symbol} @ {self.timeframe}, "
            f"candle_limit={self.candle_limit}, AI={self.enable_ai}"
        )

    async def process_task(self, task: AgentTask) -> Any:
        """
        작업 처리

        Args:
            task: 처리할 작업

        Returns:
            분석 결과
        """
        task_type = task.task_type
        params = task.params

        logger.debug(
            f"MarketRegimeAgent processing task: {task_type}, params: {params}"
        )

        # 타임아웃 설정 (5초)
        try:
            if task_type == "analyze_market":
                result = await asyncio.wait_for(
                    self._analyze_market_realtime(params),
                    timeout=5.0
                )
                return result

            elif task_type == "get_current_regime":
                return self._current_regime

            else:
                raise ValueError(f"Unknown task type: {task_type}")

        except asyncio.TimeoutError:
            logger.error(f"Task {task.task_id} timed out after 5 seconds")
            raise

    async def _analyze_market_realtime(self, params: dict) -> MarketRegime:
        """
        실시간 시장 환경 분석 (실제 데이터 사용)

        Args:
            params: {
                "symbol": str (optional),
                "timeframe": str (optional),
                "force_refresh": bool (optional)
            }

        Returns:
            MarketRegime 객체
        """
        symbol = params.get("symbol", self.symbol)
        timeframe = params.get("timeframe", self.timeframe)
        force_refresh = params.get("force_refresh", False)

        logger.info(f"📊 Analyzing market regime: {symbol} @ {timeframe}")

        # 1. 캔들 데이터 가져오기
        try:
            candles = await self._fetch_candles(symbol, timeframe, force_refresh)

            if not candles or len(candles) < 50:
                logger.warning(
                    f"Insufficient candles for {symbol}: {len(candles) if candles else 0}"
                )
                return self._create_unknown_regime(symbol)

            current_price = candles[-1]["close"]

        except Exception as e:
            logger.error(f"Failed to fetch candles: {e}", exc_info=True)
            return self._create_unknown_regime(symbol)

        # 2. 기술적 지표 계산
        try:
            atr = self.indicators.calculate_atr(candles, period=14)
            adx = self.indicators.calculate_adx(candles, period=14)
            upper_bb, middle_bb, lower_bb = self.indicators.calculate_bollinger_bands(
                candles, period=20
            )
            bb_width = self.indicators.calculate_bollinger_width(candles, period=20)
            ema_20 = self.indicators.calculate_ema(candles, period=20)
            ema_50 = self.indicators.calculate_ema(candles, period=50)
            support, resistance = self.indicators.detect_support_resistance(
                candles, lookback=50
            )
            avg_volume = self.indicators.calculate_average_volume(candles, period=20)
            current_volume = candles[-1]["volume"]

            logger.debug(
                f"Indicators: ATR={atr:.2f}, ADX={adx:.2f}, "
                f"BB_width={bb_width:.2f}%, Avg_volume={avg_volume:.0f}"
            )

        except Exception as e:
            logger.error(f"Failed to calculate indicators: {e}", exc_info=True)
            return self._create_unknown_regime(symbol)

        # 3. 변동성 계산 (ATR / 현재가 * 100)
        volatility = (atr / current_price * 100) if current_price > 0 else 0.0

        # ATR 평균 계산 (최근 20개 ATR)
        atr_history = []
        for i in range(max(0, len(candles) - 20), len(candles)):
            if i >= 14:  # ATR 계산에 최소 15개 필요
                atr_i = self.indicators.calculate_atr(candles[:i + 1], period=14)
                atr_history.append(atr_i)

        avg_atr = sum(atr_history) / len(atr_history) if atr_history else atr

        # 4. 시장 환경 판단 (규칙 기반)
        regime_type, confidence = self._determine_regime_enhanced(
            current_price=current_price,
            adx=adx,
            atr=atr,
            avg_atr=avg_atr,
            volatility=volatility,
            bb_width=bb_width,
            ema_20=ema_20,
            ema_50=ema_50,
            upper_bb=upper_bb,
            lower_bb=lower_bb,
            current_volume=current_volume,
            avg_volume=avg_volume
        )

        # 4.5. AI 기반 분석 (선택적)
        ai_regime_type = regime_type
        ai_confidence = confidence

        if self.enable_ai and self.ai_service:
            try:
                ai_result = await self._analyze_with_ai(
                    symbol=symbol,
                    current_price=current_price,
                    indicators={
                        "atr": atr,
                        "adx": adx,
                        "volatility": volatility,
                        "bb_width": bb_width,
                        "ema_20": ema_20,
                        "ema_50": ema_50,
                        "upper_bb": upper_bb,
                        "lower_bb": lower_bb,
                        "current_volume": current_volume,
                        "avg_volume": avg_volume,
                    },
                    rule_based_regime=regime_type.value,
                    rule_based_confidence=confidence
                )

                if ai_result:
                    ai_regime_type = ai_result.get("regime_type", regime_type)
                    ai_confidence = ai_result.get("confidence", confidence)

                    logger.info(
                        f"🤖 AI Analysis: {symbol} -> {ai_regime_type.value if hasattr(ai_regime_type, 'value') else ai_regime_type} "
                        f"(rule: {regime_type.value}, AI conf: {ai_confidence:.2f})"
                    )

            except Exception as e:
                logger.warning(f"AI analysis failed, using rule-based result: {e}")

        # 5. MarketRegime 객체 생성 (AI 또는 규칙 기반)
        regime = MarketRegime(
            symbol=symbol,
            regime_type=ai_regime_type if isinstance(ai_regime_type, RegimeType) else regime_type,
            confidence=ai_confidence,
            volatility=volatility,
            trend_strength=adx,
            support_level=support,
            resistance_level=resistance
        )

        # 6. 현재 환경 저장 (메모리)
        self._current_regime = regime

        # 7. Redis에 저장
        if self.redis_client:
            try:
                await self._save_to_redis(regime)
            except Exception as e:
                logger.warning(f"Failed to save to Redis: {e}")

        logger.info(
            f"✅ Market regime: {symbol} -> {regime_type.value} "
            f"(confidence: {confidence:.2f}, volatility: {volatility:.2f}%, ADX: {adx:.2f})"
        )

        return regime

    async def _fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        force_refresh: bool = False
    ) -> list:
        """
        캔들 데이터 가져오기 (Candle Cache 우선, Bitget API 대체)

        Args:
            symbol: 심볼
            timeframe: 타임프레임
            force_refresh: 강제 새로고침

        Returns:
            캔들 데이터 리스트
        """
        # 1. Candle Cache 사용 (있으면)
        if self.candle_cache and not force_refresh:
            try:
                logger.debug(f"Fetching candles from cache: {symbol} @ {timeframe}")
                candles = await self.candle_cache.get_candles(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=self.candle_limit
                )
                if candles and len(candles) >= 50:
                    logger.debug(f"✅ Got {len(candles)} candles from cache")
                    return candles
            except Exception as e:
                logger.warning(f"Cache fetch failed, falling back to API: {e}")

        # 2. Bitget API 사용 (캐시 없거나 실패 시)
        if self.bitget_client:
            try:
                logger.debug(f"Fetching candles from Bitget API: {symbol} @ {timeframe}")
                candles = await self.bitget_client.get_historical_candles(
                    symbol=symbol,
                    interval=timeframe,
                    limit=self.candle_limit
                )

                if candles:
                    logger.debug(f"✅ Got {len(candles)} candles from Bitget API")
                    return candles

            except Exception as e:
                logger.error(f"Bitget API fetch failed: {e}", exc_info=True)

        # 3. 둘 다 실패
        logger.error(f"Failed to fetch candles from both cache and API")
        return []

    def _determine_regime_enhanced(
        self,
        current_price: float,
        adx: float,
        atr: float,
        avg_atr: float,
        volatility: float,
        bb_width: float,
        ema_20: float,
        ema_50: float,
        upper_bb: float,
        lower_bb: float,
        current_volume: float,
        avg_volume: float
    ) -> tuple[RegimeType, float]:
        """
        향상된 시장 환경 결정 로직

        우선순위:
        1. LOW_VOLUME: 거래량이 평균의 30% 미만
        2. VOLATILE: ATR이 평균의 2배 이상
        3. TRENDING: ADX > 25
        4. RANGING: ADX < 20

        Returns:
            (regime_type, confidence)
        """
        confidence = 0.5  # 기본 신뢰도

        # 1. LOW_VOLUME 체크 (최우선)
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        if volume_ratio < self.low_volume_threshold:
            confidence = 0.8
            logger.debug(
                f"LOW_VOLUME detected: current={current_volume:.0f}, "
                f"avg={avg_volume:.0f}, ratio={volume_ratio:.2f}"
            )
            return RegimeType.LOW_VOLUME, confidence

        # 2. VOLATILE 체크 (두 번째 우선순위)
        atr_ratio = atr / avg_atr if avg_atr > 0 else 1.0
        if atr_ratio >= self.volatile_atr_multiplier:
            confidence = 0.85
            logger.debug(
                f"VOLATILE detected: ATR={atr:.2f}, avg_ATR={avg_atr:.2f}, "
                f"ratio={atr_ratio:.2f}"
            )
            return RegimeType.VOLATILE, confidence

        # 3. TRENDING 체크 (ADX > 25)
        if adx > self.trending_adx_threshold:
            # EMA로 방향 확인
            if ema_20 > ema_50 and current_price > ema_20:
                confidence = min(0.9, adx / 100 + 0.5)
                logger.debug(
                    f"TRENDING_UP detected: ADX={adx:.2f}, "
                    f"EMA20={ema_20:.2f}, EMA50={ema_50:.2f}, price={current_price:.2f}"
                )
                return RegimeType.TRENDING_UP, confidence

            elif ema_20 < ema_50 and current_price < ema_20:
                confidence = min(0.9, adx / 100 + 0.5)
                logger.debug(
                    f"TRENDING_DOWN detected: ADX={adx:.2f}, "
                    f"EMA20={ema_20:.2f}, EMA50={ema_50:.2f}, price={current_price:.2f}"
                )
                return RegimeType.TRENDING_DOWN, confidence

        # 4. RANGING 체크 (ADX < 20)
        if adx < self.ranging_adx_threshold:
            # 볼린저밴드 중간에 위치하는지 확인
            price_range = upper_bb - lower_bb
            bb_percent = (
                (current_price - lower_bb) / price_range if price_range > 0 else 0.5
            )

            if 0.3 < bb_percent < 0.7:
                confidence = 0.75
                logger.debug(
                    f"RANGING detected: ADX={adx:.2f}, BB%={bb_percent:.2f}"
                )
                return RegimeType.RANGING, confidence

        # 5. 불명확한 시장
        logger.debug(f"UNKNOWN regime: ADX={adx:.2f}, ATR_ratio={atr_ratio:.2f}")
        return RegimeType.UNKNOWN, 0.4

    def _create_unknown_regime(self, symbol: str) -> MarketRegime:
        """불명확한 시장 환경 생성 (에러 시)"""
        return MarketRegime(
            symbol=symbol,
            regime_type=RegimeType.UNKNOWN,
            confidence=0.0,
            volatility=0.0,
            trend_strength=0.0
        )

    async def _analyze_with_ai(
        self,
        symbol: str,
        current_price: float,
        indicators: dict,
        rule_based_regime: str,
        rule_based_confidence: float
    ) -> Optional[dict]:
        """
        AI 기반 시장 환경 분석 (DeepSeek-V3.2)

        Args:
            symbol: 심볼
            current_price: 현재가
            indicators: 기술적 지표 딕셔너리
            rule_based_regime: 규칙 기반 판단 결과
            rule_based_confidence: 규칙 기반 신뢰도

        Returns:
            {"regime_type": RegimeType, "confidence": float} 또는 None
        """
        if not self.ai_service:
            return None

        # 시스템 프롬프트
        system_prompt = f"""You are an expert cryptocurrency market regime analyzer.

Analyze technical indicators and classify the market regime into one of these categories:
- TRENDING_UP: Strong upward trend (ADX > 25, price above EMAs)
- TRENDING_DOWN: Strong downward trend (ADX > 25, price below EMAs)
- RANGING: Sideways market (ADX < 20)
- VOLATILE: High volatility (ATR spike, wide Bollinger Bands)
- LOW_VOLUME: Low trading activity
- UNKNOWN: Unclear market state

Return ONLY a valid JSON object:
{{"regime_type": "TRENDING_UP|TRENDING_DOWN|RANGING|VOLATILE|LOW_VOLUME|UNKNOWN", "confidence": 0.0-1.0, "reason": "brief explanation"}}"""

        # 사용자 프롬프트
        user_prompt = f"""Analyze {symbol} market regime:

Current Price: ${current_price:,.2f}

Technical Indicators:
- ATR: {indicators['atr']:.2f}
- ADX: {indicators['adx']:.2f}
- Volatility: {indicators['volatility']:.2f}%
- Bollinger Width: {indicators['bb_width']:.2f}%
- EMA 20: ${indicators['ema_20']:,.2f}
- EMA 50: ${indicators['ema_50']:,.2f}
- BB Upper: ${indicators['upper_bb']:,.2f}
- BB Lower: ${indicators['lower_bb']:,.2f}
- Current Volume: {indicators['current_volume']:.0f}
- Avg Volume: {indicators['avg_volume']:.0f}

Rule-based Analysis: {rule_based_regime} (confidence: {rule_based_confidence:.2f})

Provide your AI-based market regime analysis. Return JSON only:"""

        try:
            # AI API 호출 (비용 최적화 적용)
            result = await self.ai_service.call_ai(
                agent_type="market_regime",
                prompt=user_prompt,
                context={
                    "symbol": symbol,
                    "price": current_price,
                    "adx": indicators['adx'],
                    "atr": indicators['atr'],
                },
                system_prompt=system_prompt,
                response_type="market_analysis",
                temperature=0.3,
                max_tokens=200,
                enable_caching=True,
                enable_sampling=True
            )

            response_text = result.get("response", "")

            if not response_text:
                return None

            # JSON 파싱
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text)

            if json_match:
                ai_analysis = json.loads(json_match.group())

                regime_str = ai_analysis.get("regime_type", "UNKNOWN").upper()
                ai_confidence = float(ai_analysis.get("confidence", 0.5))

                # RegimeType으로 변환
                try:
                    ai_regime = RegimeType(regime_str)
                except ValueError:
                    ai_regime = RegimeType.UNKNOWN

                logger.debug(
                    f"AI analysis result: {regime_str}, confidence: {ai_confidence:.2f}, "
                    f"reason: {ai_analysis.get('reason', 'N/A')}"
                )

                return {
                    "regime_type": ai_regime,
                    "confidence": ai_confidence,
                    "reason": ai_analysis.get("reason", "")
                }

            return None

        except Exception as e:
            logger.error(f"AI analysis error: {e}", exc_info=True)
            return None

    async def _save_to_redis(self, regime: MarketRegime):
        """Redis에 현재 시장 환경 저장"""
        if not self.redis_client:
            return

        try:
            key = f"agent:market_regime:current:{regime.symbol}"
            await self.redis_client.set(
                key=key,
                value=regime.to_dict(),
                ttl=300,  # 5분
                serialize=True
            )
            logger.debug(f"Saved to Redis: {key}")

        except Exception as e:
            logger.error(f"Redis save error: {e}", exc_info=True)

    def get_current_regime(self) -> Optional[MarketRegime]:
        """현재 시장 환경 조회 (메모리)"""
        return self._current_regime

    async def run_periodic_analysis(self, interval_seconds: int = 60):
        """
        주기적 시장 분석 실행 (1분마다)

        Args:
            interval_seconds: 실행 간격 (초)
        """
        logger.info(
            f"🔄 Starting periodic market analysis: {self.symbol} @ {self.timeframe}, "
            f"interval={interval_seconds}s"
        )

        while not self._shutdown_event.is_set():
            try:
                # 분석 작업 생성 및 제출
                task = AgentTask(
                    task_id=f"analyze_{datetime.utcnow().timestamp()}",
                    task_type="analyze_market",
                    params={
                        "symbol": self.symbol,
                        "timeframe": self.timeframe,
                        "force_refresh": False
                    },
                    timeout=5.0
                )

                await self.submit_task(task)

                # 다음 실행까지 대기
                await asyncio.sleep(interval_seconds)

            except asyncio.CancelledError:
                logger.info("Periodic analysis cancelled")
                break

            except Exception as e:
                logger.error(f"Error in periodic analysis: {e}", exc_info=True)
                await asyncio.sleep(interval_seconds)

        logger.info("Periodic market analysis stopped")
