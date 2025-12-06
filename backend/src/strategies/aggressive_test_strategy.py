"""
공격적 테스트 전략 - 실전 매매 테스트용

특징:
- 매우 빠른 진입/청산
- 최소 수량 (0.001)
- 낮은 진입 문턱 (30% 신뢰도)
- 짧은 쿨다운 (2 캔들)
- 빠른 손익 실현 (1% 손절, 2% 익절)

⚠️ 주의: 테스트 목적으로만 사용!
"""

import json
from typing import List, Dict, Optional


class AggressiveTestStrategy:
    """
    공격적 테스트 전략

    목적: 실전 매매 시스템이 제대로 작동하는지 빠르게 확인
    - 진입이 쉬움 (낮은 기준)
    - 청산이 빠름 (작은 손익폭)
    - 거래 빈도가 높음
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}

        # 매우 공격적인 EMA 설정 (빠른 반응)
        self.ema_fast = self.params.get("ema_fast", 5)
        self.ema_slow = self.params.get("ema_slow", 10)

        # 공격적인 RSI 설정
        self.rsi_period = self.params.get("rsi_period", 7)
        self.rsi_oversold = self.params.get("rsi_oversold", 40)  # 더 쉽게 진입
        self.rsi_overbought = self.params.get("rsi_overbought", 60)  # 더 쉽게 진입

        # 리스크 관리 (작은 손익폭)
        self.stop_loss_pct = self.params.get("stop_loss_pct", 1.0)  # 1% 손절
        self.take_profit_pct = self.params.get("take_profit_pct", 2.0)  # 2% 익절

        # 포지션 관리
        self.max_position_size = self.params.get("max_position_size", 0.001)  # 최소 수량
        self.cooldown_candles = self.params.get("cooldown_candles", 2)  # 짧은 쿨다운

        # 낮은 신뢰도 요구 (빠른 진입)
        self.min_confidence = self.params.get("min_confidence", 0.3)  # 30%만 되면 진입

        # 내부 상태
        self.min_candles = max(self.ema_slow, self.rsi_period) + 2
        self.last_signal_candle = -999
        self.signal_count = 0

    def calculate_ema(self, values: List[float], period: int) -> float:
        """EMA 계산"""
        if not values or len(values) < period:
            return values[-1] if values else 0.0

        k = 2 / (period + 1)
        ema = values[0]
        for price in values[1:]:
            ema = price * k + ema * (1 - k)
        return ema

    def calculate_rsi(self, closes: List[float], period: int = 7) -> float:
        """RSI 계산"""
        if len(closes) < period + 1:
            return 50.0

        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def check_trend(self, closes: List[float]) -> str:
        """빠른 트렌드 확인"""
        if len(closes) < self.ema_slow:
            return "neutral"

        ema_fast = self.calculate_ema(closes[-self.ema_fast:], self.ema_fast)
        ema_slow = self.calculate_ema(closes[-self.ema_slow:], self.ema_slow)

        # 아주 작은 차이도 트렌드로 간주
        if ema_fast > ema_slow:
            return "bullish"
        elif ema_fast < ema_slow:
            return "bearish"
        else:
            return "neutral"

    def check_momentum(self, closes: List[float]) -> str:
        """모멘텀 확인"""
        rsi = self.calculate_rsi(closes, self.rsi_period)

        if rsi < self.rsi_oversold:
            return "oversold"
        elif rsi > self.rsi_overbought:
            return "overbought"
        else:
            return "neutral"

    def generate_signal(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict] = None
    ) -> Dict:
        """
        공격적 시그널 생성 (빠른 진입/청산)
        """

        response = {
            "action": "hold",
            "confidence": 0.0,
            "reason": "Insufficient data",
            "stop_loss": None,
            "take_profit": None,
            "size": 0
        }

        # 1. 데이터 충분성 확인
        if len(candles) < self.min_candles:
            response["reason"] = f"Need at least {self.min_candles} candles"
            return response

        # 2. 쿨다운 확인 (짧음)
        current_candle_idx = len(candles)
        if current_candle_idx - self.last_signal_candle < self.cooldown_candles:
            response["reason"] = f"Cooldown ({self.cooldown_candles} candles)"
            return response

        # 3. 포지션 체크 - 빠른 청산
        if current_position and current_position.get("size", 0) > 0:
            entry_price = current_position.get("entry_price", 0)
            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            side = current_position.get("side", "")

            if side == "long":
                # 빠른 익절/손절
                if pnl_pct >= self.take_profit_pct:
                    response["action"] = "close"
                    response["confidence"] = 1.0
                    response["reason"] = f"Quick TP: {pnl_pct:.2f}%"
                    return response

                if pnl_pct <= -self.stop_loss_pct:
                    response["action"] = "close"
                    response["confidence"] = 1.0
                    response["reason"] = f"Quick SL: {pnl_pct:.2f}%"
                    return response

            elif side == "short":
                # 숏 포지션 청산
                if pnl_pct <= -self.take_profit_pct:
                    response["action"] = "close"
                    response["confidence"] = 1.0
                    response["reason"] = f"Quick TP (Short): {pnl_pct:.2f}%"
                    return response

                if pnl_pct >= self.stop_loss_pct:
                    response["action"] = "close"
                    response["confidence"] = 1.0
                    response["reason"] = f"Quick SL (Short): {pnl_pct:.2f}%"
                    return response

            response["reason"] = "Position open, waiting for exit"
            return response

        # 4. 새로운 진입 시그널 (공격적)
        closes = [c["close"] for c in candles]

        trend = self.check_trend(closes)
        momentum = self.check_momentum(closes)

        confidence = 0.0
        reasons = []

        # 매수 시그널 (매우 쉬운 조건)
        if trend == "bullish" or momentum == "oversold":
            response["action"] = "buy"

            confidence += 0.4 if trend == "bullish" else 0
            confidence += 0.4 if momentum == "oversold" else 0.2
            confidence += 0.2  # 기본 점수

            reasons.append(f"Trend: {trend}")
            reasons.append(f"RSI: {momentum}")

            # 손익 설정
            response["stop_loss"] = current_price * (1 - self.stop_loss_pct / 100)
            response["take_profit"] = current_price * (1 + self.take_profit_pct / 100)
            response["size"] = self.max_position_size

        # 매도 시그널 (매우 쉬운 조건)
        elif trend == "bearish" or momentum == "overbought":
            response["action"] = "sell"

            confidence += 0.4 if trend == "bearish" else 0
            confidence += 0.4 if momentum == "overbought" else 0.2
            confidence += 0.2  # 기본 점수

            reasons.append(f"Trend: {trend}")
            reasons.append(f"RSI: {momentum}")

            # 손익 설정
            response["stop_loss"] = current_price * (1 + self.stop_loss_pct / 100)
            response["take_profit"] = current_price * (1 - self.take_profit_pct / 100)
            response["size"] = self.max_position_size

        else:
            reasons.append(f"Trend: {trend}")
            reasons.append(f"Momentum: {momentum}")

        response["confidence"] = min(confidence, 1.0)
        response["reason"] = " | ".join(reasons)

        # 5. 낮은 신뢰도 필터 (30%만 되면 OK)
        if response["action"] in ["buy", "sell"] and response["confidence"] < self.min_confidence:
            response["action"] = "hold"
            response["reason"] += f" | Low confidence: {response['confidence']:.2f}"

        # 6. 시그널 기록
        if response["action"] in ["buy", "sell"]:
            self.last_signal_candle = current_candle_idx
            self.signal_count += 1

        return response


def create_aggressive_strategy(params: Optional[Dict] = None) -> AggressiveTestStrategy:
    """공격적 테스트 전략 생성"""
    return AggressiveTestStrategy(params)


# 공격적 전략 파라미터
AGGRESSIVE_PARAMS = {
    "ema_fast": 5,
    "ema_slow": 10,
    "rsi_period": 7,
    "rsi_oversold": 40,
    "rsi_overbought": 60,
    "stop_loss_pct": 1.0,  # 1% 손절
    "take_profit_pct": 2.0,  # 2% 익절
    "max_position_size": 0.001,  # 최소 수량
    "cooldown_candles": 2,  # 2 캔들만 대기
    "min_confidence": 0.3  # 30% 신뢰도면 진입
}
