"""
MA Cross Strategy - 이동평균 교차 전략

특징:
- 빠른 MA와 느린 MA의 교차로 매매 신호 생성
- 골든 크로스: 매수 신호 (빠른 MA가 느린 MA를 상향 돌파)
- 데드 크로스: 매도 신호 (빠른 MA가 느린 MA를 하향 돌파)
- 공격적 설정: 10/30 MA (기본 20/50 대비 빠른 반응)
- Bitget 최소 주문량: 0.01 BTC

⚠️ 테스트용 공격적 설정
"""

import json
from typing import List, Dict, Optional


class MaCrossStrategy:
    """
    이동평균 교차 전략

    진입:
    - 골든 크로스: 빠른 MA > 느린 MA (매수)
    - 데드 크로스: 빠른 MA < 느린 MA (매도)

    청산:
    - 반대 크로스 발생
    - 손익 목표 도달
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}

        # 공격적 MA 설정 (빠른 반응)
        self.ma_fast = self.params.get("ma_fast", 10)  # 10 periods (was 20)
        self.ma_slow = self.params.get("ma_slow", 30)  # 30 periods (was 50)

        # 리스크 관리
        self.stop_loss_pct = self.params.get("stop_loss_pct", 2.0)  # 2% 손절
        self.take_profit_pct = self.params.get("take_profit_pct", 3.0)  # 3% 익절

        # 포지션 관리 - Bitget 최소 주문량
        self.max_position_size = self.params.get("max_position_size", 0.01)  # 0.01 BTC minimum
        self.cooldown_candles = self.params.get("cooldown_candles", 3)  # 3 캔들 쿨다운

        # 신뢰도 설정 (공격적)
        self.min_confidence = self.params.get("min_confidence", 0.4)  # 40% 신뢰도

        # 내부 상태
        self.min_candles = self.ma_slow + 5  # 충분한 데이터 확보
        self.last_signal_candle = -999
        self.signal_count = 0
        self.last_ma_fast = None
        self.last_ma_slow = None

    def calculate_sma(self, values: List[float], period: int) -> float:
        """Simple Moving Average 계산"""
        if not values or len(values) < period:
            return values[-1] if values else 0.0

        return sum(values[-period:]) / period

    def detect_cross(self, ma_fast_prev: float, ma_slow_prev: float,
                     ma_fast_curr: float, ma_slow_curr: float) -> Optional[str]:
        """
        MA 교차 감지

        Returns:
            "golden" - 골든 크로스 (매수 신호)
            "dead" - 데드 크로스 (매도 신호)
            None - 교차 없음
        """
        if ma_fast_prev is None or ma_slow_prev is None:
            return None

        # 골든 크로스: 빠른 MA가 느린 MA를 상향 돌파
        if ma_fast_prev <= ma_slow_prev and ma_fast_curr > ma_slow_curr:
            return "golden"

        # 데드 크로스: 빠른 MA가 느린 MA를 하향 돌파
        if ma_fast_prev >= ma_slow_prev and ma_fast_curr < ma_slow_curr:
            return "dead"

        return None

    def calculate_trend_strength(self, ma_fast: float, ma_slow: float) -> float:
        """트렌드 강도 계산 (MA 간 거리)"""
        if ma_slow == 0:
            return 0.0

        distance_pct = abs(ma_fast - ma_slow) / ma_slow * 100

        # 거리가 클수록 강한 트렌드
        if distance_pct > 2.0:
            return 1.0
        elif distance_pct > 1.0:
            return 0.8
        elif distance_pct > 0.5:
            return 0.6
        else:
            return 0.4

    def generate_signal(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict] = None
    ) -> Dict:
        """
        MA Cross 시그널 생성
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
            response["reason"] = f"Need at least {self.min_candles} candles (have {len(candles)})"
            return response

        # 2. 쿨다운 확인
        current_candle_idx = len(candles)
        if current_candle_idx - self.last_signal_candle < self.cooldown_candles:
            response["reason"] = f"Cooldown ({self.cooldown_candles} candles)"
            return response

        # 3. 포지션 청산 확인
        if current_position and current_position.get("size", 0) > 0:
            entry_price = current_position.get("entry_price", 0)
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            side = current_position.get("side", "")

            # MA 계산
            closes = [c["close"] for c in candles]
            ma_fast = self.calculate_sma(closes, self.ma_fast)
            ma_slow = self.calculate_sma(closes, self.ma_slow)

            if side == "long":
                # 손익 목표 도달 확인
                if pnl_pct >= self.take_profit_pct:
                    response["action"] = "close"
                    response["confidence"] = 1.0
                    response["reason"] = f"Take Profit: {pnl_pct:.2f}%"
                    return response

                if pnl_pct <= -self.stop_loss_pct:
                    response["action"] = "close"
                    response["confidence"] = 1.0
                    response["reason"] = f"Stop Loss: {pnl_pct:.2f}%"
                    return response

                # 데드 크로스 발생시 청산
                if ma_fast < ma_slow:
                    response["action"] = "close"
                    response["confidence"] = 0.8
                    response["reason"] = f"Dead Cross (exit long) | PnL: {pnl_pct:.2f}%"
                    return response

            elif side == "short":
                # 손익 목표 도달 확인 (숏은 반대)
                if pnl_pct <= -self.take_profit_pct:
                    response["action"] = "close"
                    response["confidence"] = 1.0
                    response["reason"] = f"Take Profit (Short): {pnl_pct:.2f}%"
                    return response

                if pnl_pct >= self.stop_loss_pct:
                    response["action"] = "close"
                    response["confidence"] = 1.0
                    response["reason"] = f"Stop Loss (Short): {pnl_pct:.2f}%"
                    return response

                # 골든 크로스 발생시 청산
                if ma_fast > ma_slow:
                    response["action"] = "close"
                    response["confidence"] = 0.8
                    response["reason"] = f"Golden Cross (exit short) | PnL: {pnl_pct:.2f}%"
                    return response

            response["reason"] = f"Position open ({side}), monitoring MA cross"
            return response

        # 4. 새로운 진입 시그널 (MA Cross)
        closes = [c["close"] for c in candles]

        # 현재 MA 계산
        ma_fast = self.calculate_sma(closes, self.ma_fast)
        ma_slow = self.calculate_sma(closes, self.ma_slow)

        # 교차 감지 (이전 값과 비교)
        cross_type = None
        if self.last_ma_fast is not None and self.last_ma_slow is not None:
            cross_type = self.detect_cross(
                self.last_ma_fast, self.last_ma_slow,
                ma_fast, ma_slow
            )

        # MA 값 저장 (다음 캔들에서 사용)
        self.last_ma_fast = ma_fast
        self.last_ma_slow = ma_slow

        # 트렌드 강도 계산
        trend_strength = self.calculate_trend_strength(ma_fast, ma_slow)

        confidence = 0.0
        reasons = []

        # 골든 크로스 - 매수 신호
        if cross_type == "golden":
            response["action"] = "buy"
            confidence = 0.6 + (trend_strength * 0.4)  # 60-100% 신뢰도

            reasons.append(f"Golden Cross detected")
            reasons.append(f"MA Fast ({self.ma_fast}): {ma_fast:.2f}")
            reasons.append(f"MA Slow ({self.ma_slow}): {ma_slow:.2f}")
            reasons.append(f"Trend Strength: {trend_strength:.2f}")

            # 손익 설정
            response["stop_loss"] = current_price * (1 - self.stop_loss_pct / 100)
            response["take_profit"] = current_price * (1 + self.take_profit_pct / 100)
            response["size"] = self.max_position_size

        # 데드 크로스 - 매도 신호
        elif cross_type == "dead":
            response["action"] = "sell"
            confidence = 0.6 + (trend_strength * 0.4)  # 60-100% 신뢰도

            reasons.append(f"Dead Cross detected")
            reasons.append(f"MA Fast ({self.ma_fast}): {ma_fast:.2f}")
            reasons.append(f"MA Slow ({self.ma_slow}): {ma_slow:.2f}")
            reasons.append(f"Trend Strength: {trend_strength:.2f}")

            # 손익 설정 (숏)
            response["stop_loss"] = current_price * (1 + self.stop_loss_pct / 100)
            response["take_profit"] = current_price * (1 - self.take_profit_pct / 100)
            response["size"] = self.max_position_size

        # 교차 없음
        else:
            reasons.append(f"No cross detected")
            reasons.append(f"MA Fast ({self.ma_fast}): {ma_fast:.2f}")
            reasons.append(f"MA Slow ({self.ma_slow}): {ma_slow:.2f}")

            # 현재 MA 관계 표시
            if ma_fast > ma_slow:
                reasons.append("Bullish alignment (fast > slow)")
            else:
                reasons.append("Bearish alignment (fast < slow)")

        response["confidence"] = min(confidence, 1.0)
        response["reason"] = " | ".join(reasons)

        # 5. 신뢰도 필터
        if response["action"] in ["buy", "sell"] and response["confidence"] < self.min_confidence:
            response["action"] = "hold"
            response["reason"] += f" | Low confidence: {response['confidence']:.2f}"

        # 6. 시그널 기록
        if response["action"] in ["buy", "sell"]:
            self.last_signal_candle = current_candle_idx
            self.signal_count += 1

        return response


def create_ma_cross_strategy(params: Optional[Dict] = None) -> MaCrossStrategy:
    """MA Cross 전략 생성"""
    return MaCrossStrategy(params)


# 공격적 MA Cross 파라미터 (테스트용)
AGGRESSIVE_MA_CROSS_PARAMS = {
    "ma_fast": 10,  # 빠른 MA (기본 20 대비 공격적)
    "ma_slow": 30,  # 느린 MA (기본 50 대비 공격적)
    "stop_loss_pct": 2.0,  # 2% 손절
    "take_profit_pct": 3.0,  # 3% 익절
    "max_position_size": 0.01,  # Bitget 최소 주문량
    "cooldown_candles": 3,  # 3 캔들 쿨다운
    "min_confidence": 0.4  # 40% 신뢰도면 진입
}
