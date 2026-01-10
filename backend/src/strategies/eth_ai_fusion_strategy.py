from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

try:
    from src.ml.features import FeaturePipeline
    from src.ml.models import EnsemblePredictor
    ML_AVAILABLE = True
except Exception:
    FeaturePipeline = None
    EnsemblePredictor = None
    ML_AVAILABLE = False

# FinBERT 감성 분석 에이전트 (선택적)
try:
    from src.agents.sentiment_analyzer import SentimentAnalyzerAgent
    SENTIMENT_AVAILABLE = True
except Exception:
    SentimentAnalyzerAgent = None
    SENTIMENT_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PositionState:
    side: Optional[str] = None
    add_count: int = 0
    max_profit_percent: float = 0.0


@dataclass
class IndicatorSnapshot:
    close: float
    ema_fast: float
    ema_slow: float
    ema_trend: float
    rsi: float
    macd_hist: float
    atr_percent: float
    volume_ratio: float


class ETHAIFusionStrategy:
    def __init__(self, params: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None):
        self.params = params or {}
        self.user_id = user_id
        self.symbol = self.params.get("symbol", "ETH/USDT")
        self.timeframe = self.params.get("timeframe", "5m")
        self.enable_ml = self.params.get("enable_ml", True) and ML_AVAILABLE

        # FinBERT 감성 분석 에이전트 (선택적)
        self.enable_sentiment = self.params.get("enable_sentiment", True) and SENTIMENT_AVAILABLE
        self._sentiment_agent = None
        if self.enable_sentiment:
            try:
                self._sentiment_agent = SentimentAnalyzerAgent(
                    agent_id=f"sentiment_{user_id or 'default'}",
                    name="SentimentAnalyzer",
                    config={
                        "extreme_positive": 0.5,
                        "extreme_negative": -0.5,
                        "block_entry": -0.7,
                        "cache_ttl_minutes": 30,
                    }
                )
                logger.info(f"✅ 감성 분석 에이전트 초기화 완료 (user_id={user_id})")
            except Exception as e:
                logger.error(f"❌ 감성 분석 에이전트 초기화 실패: {e}")
                self._sentiment_agent = None
                self.enable_sentiment = False

        self._state = PositionState()
        self._feature_pipeline = FeaturePipeline() if self.enable_ml and FeaturePipeline else None
        self._ml_predictor = EnsemblePredictor() if self.enable_ml and EnsemblePredictor else None

        self._ema_fast = int(self.params.get("ema_fast", 9))
        self._ema_slow = int(self.params.get("ema_slow", 21))
        self._ema_trend = int(self.params.get("ema_trend", 55))
        self._rsi_length = int(self.params.get("rsi_length", 14))
        self._atr_length = int(self.params.get("atr_length", 14))
        # 진입 조건 강화: 4.0 → 5.0 (더 엄격한 진입)
        self._entry_threshold = float(self.params.get("entry_threshold", 5.0))
        self._max_adds = int(self.params.get("max_adds", 3))
        self._add_step = float(self.params.get("add_step_percent", 1.5))  # 0.8 → 1.5% (추매 간격 확대)
        self._add_scale = float(self.params.get("add_scale", 0.35))

        # 손절/익절 범위 설정 (개선됨)
        self._min_stop_loss = float(self.params.get("min_stop_loss", 1.5))  # 0.6 → 1.5%
        self._max_stop_loss = float(self.params.get("max_stop_loss", 3.0))  # 1.6 → 3.0%
        self._min_take_profit = float(self.params.get("min_take_profit", 3.0))  # 1.2 → 3.0%
        self._max_take_profit = float(self.params.get("max_take_profit", 8.0))  # 4.5 → 8.0%
        self._min_rr_ratio = float(self.params.get("min_rr_ratio", 2.0))  # 최소 R/R 1:2

        # 진입 쿨다운 (연속 진입 방지)
        self._last_exit_candle_count = 0
        self._cooldown_candles = int(self.params.get("cooldown_candles", 6))  # 6개 캔들 쿨다운 (30분)

    def generate_signal(
        self,
        current_price: float,
        candles: list,
        current_position: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not candles or len(candles) < 60:
            return self._hold("insufficient_candles")

        snapshot = self._compute_indicators(candles)
        ml_result = self._get_ml_prediction(candles, snapshot)

        if current_position and current_position.get("size", 0) > 0:
            return self._manage_position(current_price, snapshot, ml_result, current_position)

        self._reset_state()
        return self._evaluate_entry(snapshot, ml_result)

    def _evaluate_entry(self, snapshot: IndicatorSnapshot, ml_result: Any) -> Dict[str, Any]:
        long_score, short_score, reasons = self._score_entry(snapshot)
        action = "hold"

        if long_score >= self._entry_threshold and long_score >= short_score + 1:
            action = "buy"
        elif short_score >= self._entry_threshold and short_score >= long_score + 1:
            action = "sell"

        if action == "hold":
            return self._hold("no_entry")

        if ml_result:
            if ml_result.should_skip_entry():
                return self._hold("ml_skip")
            ml_dir = ml_result.direction.direction.value
            if ml_result.direction.confidence > 0.55 and ml_dir != ("long" if action == "buy" else "short"):
                return self._hold("ml_mismatch")
            if not ml_result.timing.is_good_entry and ml_result.timing.confidence > 0.6:
                return self._hold("timing_block")

        # FinBERT 감성 분석 필터 (선택적)
        sentiment_signal = self._get_sentiment_signal()
        confidence_multiplier = 1.0

        if sentiment_signal:
            # 극단적 부정 감성 시 진입 차단
            if sentiment_signal.get("should_block", False):
                return self._hold(f"sentiment_block: {sentiment_signal.get('reason', 'extreme_negative')}")

            # 감성에 따른 신뢰도 조정
            confidence_multiplier = sentiment_signal.get("confidence_multiplier", 1.0)

            # 감성과 방향 불일치 시 신뢰도 감소
            sentiment_score = sentiment_signal.get("score", 0)
            if action == "buy" and sentiment_score < -0.3:
                confidence_multiplier *= 0.8  # Long 진입 시 부정 감성이면 신뢰도 20% 감소
            elif action == "sell" and sentiment_score > 0.3:
                confidence_multiplier *= 0.8  # Short 진입 시 긍정 감성이면 신뢰도 20% 감소

            if sentiment_signal.get("reason"):
                reasons.append(f"sentiment: {sentiment_signal.get('reason')}")

        confidence = self._confidence_from_score(max(long_score, short_score), ml_result)
        confidence = min(confidence * confidence_multiplier, 1.0)  # 감성 조정 적용

        stop_loss, take_profit = self._risk_targets(snapshot, ml_result)
        return {
            "action": action,
            "confidence": confidence,
            "reason": "; ".join(reasons) if reasons else "entry",
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "size": None,
            "strategy_type": "eth_ai_fusion",
        }

    def _get_sentiment_signal(self) -> Optional[Dict[str, Any]]:
        """
        감성 분석 시그널 가져오기 (동기 래퍼)

        Returns:
            감성 시그널 또는 None
        """
        if not self._sentiment_agent:
            return None

        try:
            import asyncio

            # 심볼에서 코인 이름 추출 (ETH/USDT -> ETH)
            coin_symbol = self.symbol.split("/")[0] if "/" in self.symbol else self.symbol

            # 비동기 메서드를 동기적으로 호출
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # 이미 이벤트 루프가 실행 중이면 캐시된 값 사용
                cached = getattr(self, "_cached_sentiment", None)
                if cached:
                    return cached
                return None
            else:
                # 새 이벤트 루프 생성
                sentiment = asyncio.run(
                    self._sentiment_agent.analyze_market_sentiment(coin_symbol, hours=24)
                )

            if sentiment:
                signal = self._sentiment_agent.generate_sentiment_signal(sentiment)
                result = {
                    "score": sentiment.score,
                    "strength": sentiment.strength.value if sentiment.strength else "unknown",
                    "should_block": signal.should_block if signal else False,
                    "confidence_multiplier": signal.confidence_multiplier if signal else 1.0,
                    "reason": signal.reason if signal else None,
                }
                self._cached_sentiment = result  # 캐싱
                return result

        except Exception as e:
            logger.debug(f"감성 분석 실패 (무시됨): {e}")

        return None

    def _manage_position(
        self,
        current_price: float,
        snapshot: IndicatorSnapshot,
        ml_result: Any,
        current_position: Dict[str, Any],
    ) -> Dict[str, Any]:
        side = current_position.get("side", "long")
        entry_price = float(current_position.get("entry_price", snapshot.close))
        leverage = float(current_position.get("leverage", 1))
        raw_pnl_percent = self._pnl_percent(side, entry_price, current_price, 1)
        pnl_percent = self._pnl_percent(side, entry_price, current_price, leverage)

        self._sync_state(side, pnl_percent)
        stop_loss, take_profit = self._risk_targets(snapshot, ml_result)

        if pnl_percent <= -stop_loss:
            return self._close("stop_loss", stop_loss, take_profit)

        if self._state.max_profit_percent >= take_profit:
            trailing_floor = max(stop_loss, self._state.max_profit_percent * 0.5)
            if pnl_percent <= trailing_floor:
                return self._close("trailing_stop", stop_loss, take_profit)

        if self._should_exit_on_reversal(side, snapshot):
            return self._close("trend_reversal", stop_loss, take_profit)

        add_signal = self._check_add(side, raw_pnl_percent, snapshot, ml_result)
        if add_signal:
            add_size = max(current_position.get("size", 0) * self._add_scale, 0.0)
            return {
                "action": "buy" if side == "long" else "sell",
                "confidence": add_signal,
                "reason": "add_on_profit",
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "size": add_size,
                "strategy_type": "eth_ai_fusion",
            }

        return self._hold("manage_hold", stop_loss, take_profit)

    def _check_add(self, side: str, pnl_percent: float, snapshot: IndicatorSnapshot, ml_result: Any) -> Optional[float]:
        if self._state.add_count >= self._max_adds:
            return None
        next_add = self._add_step * (self._state.add_count + 1)
        if pnl_percent < next_add:
            return None
        if side == "long" and snapshot.rsi >= 75:
            return None
        if side == "short" and snapshot.rsi <= 25:
            return None
        if side == "long" and (snapshot.ema_fast < snapshot.ema_slow or snapshot.macd_hist < 0):
            return None
        if side == "short" and (snapshot.ema_fast > snapshot.ema_slow or snapshot.macd_hist > 0):
            return None
        if ml_result and ml_result.direction.confidence > 0.55:
            ml_dir = ml_result.direction.direction.value
            if ml_dir != ("long" if side == "long" else "short"):
                return None
        self._state.add_count += 1
        return max(0.55, self._confidence_from_score(5.0, ml_result))

    def _score_entry(self, snapshot: IndicatorSnapshot) -> Tuple[float, float, list]:
        """
        개선된 진입 스코어링 (더 엄격함)
        - 추세 필터 추가 (EMA 55)
        - RSI 중립 구간 제외 (45~55는 점수 없음)
        - 거래량 기준 상향 (1.2배 이상)
        - 추가 필터: 가격과 EMA 트렌드 정렬
        """
        long_score = 0.0
        short_score = 0.0
        reasons = []

        # 1. EMA 크로스 (기본)
        if snapshot.ema_fast > snapshot.ema_slow:
            long_score += 1.0
            reasons.append("ema_fast>ema_slow")
        elif snapshot.ema_fast < snapshot.ema_slow:
            short_score += 1.0
            reasons.append("ema_fast<ema_slow")

        # 2. 가격 위치 (EMA fast 대비)
        if snapshot.close > snapshot.ema_fast:
            long_score += 1.0
            reasons.append("price>ema_fast")
        elif snapshot.close < snapshot.ema_fast:
            short_score += 1.0
            reasons.append("price<ema_fast")

        # 3. 장기 추세 필터 (EMA 55) - 새로 추가
        if snapshot.close > snapshot.ema_trend:
            long_score += 1.5  # 장기 추세 정렬 시 가산점
            reasons.append("price>ema_trend")
        elif snapshot.close < snapshot.ema_trend:
            short_score += 1.5
            reasons.append("price<ema_trend")

        # 4. RSI (중립 구간 제외, 더 명확한 신호만)
        if snapshot.rsi >= 55 and snapshot.rsi <= 70:  # 적당히 강한 구간
            long_score += 1.0
        elif snapshot.rsi >= 70:  # 과매수는 롱 진입에 불리
            long_score -= 0.5
        if snapshot.rsi <= 45 and snapshot.rsi >= 30:  # 적당히 약한 구간
            short_score += 1.0
        elif snapshot.rsi <= 30:  # 과매도는 숏 진입에 불리
            short_score -= 0.5

        # 5. MACD 히스토그램 (방향 및 강도)
        if snapshot.macd_hist > 0:
            long_score += 1.0
            if snapshot.macd_hist > snapshot.atr_percent * 0.1:  # 강한 MACD
                long_score += 0.5
                reasons.append("strong_macd")
        elif snapshot.macd_hist < 0:
            short_score += 1.0
            if snapshot.macd_hist < -snapshot.atr_percent * 0.1:
                short_score += 0.5
                reasons.append("strong_macd")

        # 6. 거래량 확인 (기준 상향: 1.2배 이상)
        if snapshot.volume_ratio >= 1.2:
            long_score += 1.0
            short_score += 1.0
            reasons.append("high_volume")
        elif snapshot.volume_ratio < 0.8:  # 거래량 부족 시 감점
            long_score -= 0.5
            short_score -= 0.5

        return long_score, short_score, reasons

    def _risk_targets(self, snapshot: IndicatorSnapshot, ml_result: Any) -> Tuple[float, float]:
        """
        개선된 손절/익절 계산
        - 손절: 1.5% ~ 3.0% (기존 0.6~1.6%에서 확대)
        - 익절: 3.0% ~ 8.0% (기존 1.2~4.5%에서 확대)
        - R/R 비율: 최소 1:2 보장
        """
        # ATR 기반 손절 계산 (더 넓은 범위)
        atr_based_sl = snapshot.atr_percent * 1.5  # ATR의 1.5배
        stop_loss = max(self._min_stop_loss, min(self._max_stop_loss, atr_based_sl))

        # ATR 기반 익절 계산 (더 높은 목표)
        atr_based_tp = snapshot.atr_percent * 4.0  # ATR의 4배
        take_profit = max(self._min_take_profit, min(self._max_take_profit, atr_based_tp))

        # ML 결과 반영 (손절만, 범위 내에서)
        if ml_result and hasattr(ml_result, 'stoploss') and ml_result.stoploss.confidence > 0.6:
            ml_sl = ml_result.stoploss.optimal_sl_percent
            stop_loss = max(self._min_stop_loss, min(self._max_stop_loss, ml_sl))

        # R/R 비율 보장: 익절이 손절의 최소 2배 이상이 되도록
        min_take_profit_by_rr = stop_loss * self._min_rr_ratio
        if take_profit < min_take_profit_by_rr:
            take_profit = min(self._max_take_profit, min_take_profit_by_rr)

        return stop_loss, take_profit

    def _compute_indicators(self, candles: list) -> IndicatorSnapshot:
        closes = [c.get("close", 0) for c in candles]
        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]
        volumes = [c.get("volume", 0) for c in candles]

        ema_fast = self._ema(closes, self._ema_fast)
        ema_slow = self._ema(closes, self._ema_slow)
        ema_trend = self._ema(closes, self._ema_trend)
        rsi = self._rsi(closes, self._rsi_length)
        macd_hist = self._macd_hist(closes)
        atr_percent = self._atr_percent(highs, lows, closes, self._atr_length)
        volume_ratio = self._volume_ratio(volumes, 20)

        return IndicatorSnapshot(
            close=closes[-1],
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            ema_trend=ema_trend,
            rsi=rsi,
            macd_hist=macd_hist,
            atr_percent=atr_percent,
            volume_ratio=volume_ratio,
        )

    def _get_ml_prediction(self, candles: list, snapshot: IndicatorSnapshot) -> Any:
        if not self._ml_predictor or not self._feature_pipeline:
            return None
        symbol = self.symbol.replace("/", "").replace(":USDT", "")
        features = self._feature_pipeline.extract_features(candles, symbol=symbol)
        if features.empty:
            return None
        rule_signal = "long" if snapshot.ema_fast > snapshot.ema_slow else "short"
        return self._ml_predictor.predict(features, symbol=symbol, rule_based_signal=rule_signal)

    def _sync_state(self, side: str, pnl_percent: float) -> None:
        if self._state.side != side:
            self._state = PositionState(side=side, add_count=0, max_profit_percent=pnl_percent)
            return
        if pnl_percent > self._state.max_profit_percent:
            self._state.max_profit_percent = pnl_percent

    def _reset_state(self) -> None:
        self._state = PositionState()

    def _pnl_percent(self, side: str, entry_price: float, current_price: float, leverage: float) -> float:
        if entry_price <= 0:
            return 0.0
        if side == "long":
            return ((current_price - entry_price) / entry_price) * 100 * leverage
        return ((entry_price - current_price) / entry_price) * 100 * leverage

    def _should_exit_on_reversal(self, side: str, snapshot: IndicatorSnapshot) -> bool:
        """
        추세 반전 청산 조건 (완화됨)
        - 기존: EMA 크로스 + RSI 45/55 → 너무 민감
        - 개선: EMA 크로스 + RSI 극단값(35/65) + MACD 반전 확인
        """
        if side == "long":
            # 롱 청산: EMA 데드크로스 + RSI 과매도 구간 + MACD 음수
            ema_cross_down = snapshot.ema_fast < snapshot.ema_slow
            rsi_weak = snapshot.rsi < 35  # 45 → 35 (더 극단적일 때만)
            macd_negative = snapshot.macd_hist < 0
            # 3개 조건 중 2개 이상 충족 시에만 청산
            reversal_signals = sum([ema_cross_down, rsi_weak, macd_negative])
            return reversal_signals >= 2 and ema_cross_down  # EMA 크로스는 필수

        # 숏 청산: EMA 골든크로스 + RSI 과매수 구간 + MACD 양수
        ema_cross_up = snapshot.ema_fast > snapshot.ema_slow
        rsi_strong = snapshot.rsi > 65  # 55 → 65 (더 극단적일 때만)
        macd_positive = snapshot.macd_hist > 0
        reversal_signals = sum([ema_cross_up, rsi_strong, macd_positive])
        return reversal_signals >= 2 and ema_cross_up  # EMA 크로스는 필수

    def _confidence_from_score(self, score: float, ml_result: Any) -> float:
        base = 0.45 + min(score, 6.0) * 0.05
        if ml_result:
            base = max(base, ml_result.combined_confidence)
        return min(0.95, max(0.35, base))

    def _hold(self, reason: str, stop_loss: Optional[float] = None, take_profit: Optional[float] = None) -> Dict[str, Any]:
        return {
            "action": "hold",
            "confidence": 0.0,
            "reason": reason,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "size": None,
            "strategy_type": "eth_ai_fusion",
        }

    def _close(self, reason: str, stop_loss: float, take_profit: float) -> Dict[str, Any]:
        return {
            "action": "close",
            "confidence": 0.7,
            "reason": reason,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "size": None,
            "strategy_type": "eth_ai_fusion",
        }

    def _ema(self, values: list, period: int) -> float:
        if not values:
            return 0.0
        if len(values) < period:
            return values[-1]
        k = 2 / (period + 1)
        ema = values[0]
        for price in values[1:]:
            ema = price * k + ema * (1 - k)
        return ema

    def _ema_series(self, values: list, period: int) -> list:
        if not values:
            return []
        if len(values) < period:
            return values[:]
        k = 2 / (period + 1)
        ema_values = [values[0]]
        for price in values[1:]:
            ema_values.append(price * k + ema_values[-1] * (1 - k))
        return ema_values

    def _rsi(self, closes: list, period: int) -> float:
        if len(closes) <= period:
            return 50.0
        gains = 0.0
        losses = 0.0
        for i in range(-period, 0):
            change = closes[i] - closes[i - 1]
            if change >= 0:
                gains += change
            else:
                losses += abs(change)
        if losses == 0:
            return 100.0
        rs = gains / losses
        return 100 - (100 / (1 + rs))

    def _macd_hist(self, closes: list) -> float:
        if len(closes) < 35:
            return 0.0
        ema_fast = self._ema_series(closes, 12)
        ema_slow = self._ema_series(closes, 26)
        macd_line = [f - s for f, s in zip(ema_fast[-len(ema_slow):], ema_slow)]
        signal_line = self._ema_series(macd_line, 9)
        if not signal_line:
            return 0.0
        return macd_line[-1] - signal_line[-1]

    def _atr_percent(self, highs: list, lows: list, closes: list, period: int) -> float:
        if len(closes) < period + 1:
            return 0.6
        trs = []
        for i in range(-period, 0):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i - 1]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            trs.append(tr)
        atr = sum(trs) / len(trs) if trs else 0.0
        price = closes[-1] if closes else 1.0
        if price <= 0:
            return 0.6
        return (atr / price) * 100

    def _volume_ratio(self, volumes: list, window: int) -> float:
        if not volumes:
            return 1.0
        current = volumes[-1]
        window_values = volumes[-window:] if len(volumes) >= window else volumes
        avg = sum(window_values) / len(window_values) if window_values else 0.0
        if avg == 0:
            return 1.0
        return current / avg


def create_eth_ai_fusion_strategy(
    params: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
) -> ETHAIFusionStrategy:
    return ETHAIFusionStrategy(params=params, user_id=user_id)
