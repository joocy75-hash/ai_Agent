"""
Ultra Aggressive Momentum Strategy - 초공격적 모멘텀 전략

특징:
- 가격 변동에 즉시 반응하여 주문 생성
- 매우 짧은 MA 기간 (3/7) 사용
- 낮은 진입 장벽 (confidence threshold)
- 높은 거래 빈도
- Bitget 최소 주문량: 0.01 BTC

⚠️ 매우 공격적인 테스트용 전략 - 실제 거래 시 주의!
"""

import json
from typing import List, Dict, Optional


class UltraAggressiveStrategy:
    """
    초공격적 모멘텀 전략

    진입 조건 (ANY):
    1. 가격이 단기 MA(3) 위/아래로 움직이면 즉시 진입
    2. MA(3) > MA(7): BUY
    3. MA(3) < MA(7): SELL
    4. 2캔들 이상 같은 방향 움직임: 추세 진입

    청산:
    - 반대 신호 발생
    - 손익 목표 도달
    """

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}

        # 초단기 MA 설정 (매우 빠른 반응)
        self.ma_fast = self.params.get("ma_fast", 3)  # 3 periods
        self.ma_slow = self.params.get("ma_slow", 7)  # 7 periods

        # 리스크 관리 (타이트한 손익)
        self.stop_loss_pct = self.params.get("stop_loss_pct", 1.5)  # 1.5% 손절
        self.take_profit_pct = self.params.get("take_profit_pct", 2.0)  # 2% 익절

        # 포지션 관리 - Bitget 최소 주문량
        self.max_position_size = self.params.get("max_position_size", 0.01)  # 0.01 BTC
        self.cooldown_candles = self.params.get("cooldown_candles", 0)  # No cooldown!

        # 신뢰도 설정 (매우 낮은 진입 장벽)
        self.min_confidence = self.params.get("min_confidence", 0.2)  # 20% 신뢰도만 있어도 진입

        # 내부 상태
        self.min_candles = self.ma_slow + 2
        self.last_signal_candle = -999
        self.signal_count = 0
        self.last_ma_fast = None
        self.last_ma_slow = None
        self.last_price = None
        self.consecutive_moves = 0
        self.last_move_direction = None

    def calculate_sma(self, values: List[float], period: int) -> float:
        """Simple Moving Average 계산"""
        if not values or len(values) < period:
            return values[-1] if values else 0.0

        return sum(values[-period:]) / period

    def detect_momentum(self, prices: List[float]) -> Optional[str]:
        """
        모멘텀 감지 - 연속된 가격 움직임

        Returns:
            "bullish" - 상승 모멘텀
            "bearish" - 하락 모멘텀
            None - 모멘텀 없음
        """
        if len(prices) < 3:
            return None

        # 최근 3개 캔들의 움직임
        recent = prices[-3:]

        # 연속 상승
        if recent[0] < recent[1] < recent[2]:
            return "bullish"

        # 연속 하락
        if recent[0] > recent[1] > recent[2]:
            return "bearish"

        # 최근 2개만 체크
        if len(prices) >= 2:
            if prices[-2] < prices[-1]:
                return "bullish"
            elif prices[-2] > prices[-1]:
                return "bearish"

        return None

    def calculate_price_change_pct(self, prices: List[float]) -> float:
        """최근 가격 변동률 계산"""
        if len(prices) < 2:
            return 0.0

        return ((prices[-1] - prices[-2]) / prices[-2]) * 100

    def generate_signal(
        self,
        candles: List[Dict],
        current_position: Optional[Dict] = None,
        account_info: Optional[Dict] = None
    ) -> Dict:
        """
        초공격적 매매 신호 생성

        Args:
            candles: OHLCV 캔들 데이터
            current_position: 현재 포지션 정보
            account_info: 계정 정보

        Returns:
            신호 딕셔너리 (action, confidence, reason, stop_loss, take_profit, size)
        """

        # 기본 신호
        signal = {
            "action": "hold",
            "confidence": 0.0,
            "reason": "Insufficient data",
            "stop_loss": None,
            "take_profit": None,
            "size": 0
        }

        # 최소 캔들 수 체크
        if len(candles) < self.min_candles:
            signal["reason"] = f"Need {self.min_candles} candles, have {len(candles)}"
            return signal

        # 가격 데이터 추출
        closes = [c['close'] for c in candles]
        current_price = closes[-1]

        # MA 계산
        ma_fast = self.calculate_sma(closes, self.ma_fast)
        ma_slow = self.calculate_sma(closes, self.ma_slow)

        # 모멘텀 감지
        momentum = self.detect_momentum(closes)

        # 가격 변동률
        price_change = self.calculate_price_change_pct(closes)

        # 포지션 확인
        has_position = current_position and float(current_position.get("contracts", 0)) != 0

        # === 청산 로직 (포지션 있을 때) ===
        if has_position:
            position_side = current_position.get("side", "")
            entry_price = float(current_position.get("entryPrice", current_price))
            pnl_pct = ((current_price - entry_price) / entry_price) * 100

            # LONG 포지션 청산
            if position_side == "long":
                # 익절 또는 손절
                if pnl_pct >= self.take_profit_pct:
                    return {
                        "action": "close_long",
                        "confidence": 1.0,
                        "reason": f"Take profit: {pnl_pct:.2f}%",
                        "stop_loss": None,
                        "take_profit": None,
                        "size": abs(float(current_position.get("contracts", 0)))
                    }

                if pnl_pct <= -self.stop_loss_pct:
                    return {
                        "action": "close_long",
                        "confidence": 1.0,
                        "reason": f"Stop loss: {pnl_pct:.2f}%",
                        "stop_loss": None,
                        "take_profit": None,
                        "size": abs(float(current_position.get("contracts", 0)))
                    }

                # 반대 신호 발생 시 즉시 청산
                if ma_fast < ma_slow or momentum == "bearish":
                    return {
                        "action": "close_long",
                        "confidence": 0.8,
                        "reason": f"Reversal signal | MA: {ma_fast:.2f} < {ma_slow:.2f}",
                        "stop_loss": None,
                        "take_profit": None,
                        "size": abs(float(current_position.get("contracts", 0)))
                    }

            # SHORT 포지션 청산
            elif position_side == "short":
                # PnL 계산 (SHORT는 반대)
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

                # 익절 또는 손절
                if pnl_pct >= self.take_profit_pct:
                    return {
                        "action": "close_short",
                        "confidence": 1.0,
                        "reason": f"Take profit: {pnl_pct:.2f}%",
                        "stop_loss": None,
                        "take_profit": None,
                        "size": abs(float(current_position.get("contracts", 0)))
                    }

                if pnl_pct <= -self.stop_loss_pct:
                    return {
                        "action": "close_short",
                        "confidence": 1.0,
                        "reason": f"Stop loss: {pnl_pct:.2f}%",
                        "stop_loss": None,
                        "take_profit": None,
                        "size": abs(float(current_position.get("contracts", 0)))
                    }

                # 반대 신호 발생 시 즉시 청산
                if ma_fast > ma_slow or momentum == "bullish":
                    return {
                        "action": "close_short",
                        "confidence": 0.8,
                        "reason": f"Reversal signal | MA: {ma_fast:.2f} > {ma_slow:.2f}",
                        "stop_loss": None,
                        "take_profit": None,
                        "size": abs(float(current_position.get("contracts", 0)))
                    }

        # === 진입 로직 (포지션 없을 때) ===
        else:
            confidence = 0.0
            reasons = []
            action = "hold"

            # 조건 1: MA 기반
            if ma_fast > ma_slow:
                confidence += 0.4
                reasons.append(f"MA bullish: {ma_fast:.2f} > {ma_slow:.2f}")
                action = "buy"
            elif ma_fast < ma_slow:
                confidence += 0.4
                reasons.append(f"MA bearish: {ma_fast:.2f} < {ma_slow:.2f}")
                action = "sell"

            # 조건 2: 모멘텀
            if momentum == "bullish":
                confidence += 0.3
                reasons.append("Bullish momentum")
                if action != "buy":
                    action = "buy"
            elif momentum == "bearish":
                confidence += 0.3
                reasons.append("Bearish momentum")
                if action != "sell":
                    action = "sell"

            # 조건 3: 급격한 가격 변동
            if abs(price_change) > 0.1:  # 0.1% 이상 변동
                confidence += 0.2
                if price_change > 0:
                    reasons.append(f"Price surge: +{price_change:.2f}%")
                    if action != "buy":
                        action = "buy"
                else:
                    reasons.append(f"Price drop: {price_change:.2f}%")
                    if action != "sell":
                        action = "sell"

            # 조건 4: 가격이 MA 위/아래
            if current_price > ma_fast:
                confidence += 0.2
                reasons.append("Price above fast MA")
                if action == "hold":
                    action = "buy"
            elif current_price < ma_fast:
                confidence += 0.2
                reasons.append("Price below fast MA")
                if action == "hold":
                    action = "sell"

            # 신뢰도 정규화
            confidence = min(confidence, 1.0)

            # 진입 결정
            if confidence >= self.min_confidence and action != "hold":
                # 손익 가격 계산
                if action == "buy":
                    stop_loss = current_price * (1 - self.stop_loss_pct / 100)
                    take_profit = current_price * (1 + self.take_profit_pct / 100)
                else:  # sell
                    stop_loss = current_price * (1 + self.stop_loss_pct / 100)
                    take_profit = current_price * (1 - self.take_profit_pct / 100)

                return {
                    "action": action,
                    "confidence": confidence,
                    "reason": " | ".join(reasons),
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "size": self.max_position_size
                }

            # Hold
            signal["action"] = "hold"
            signal["confidence"] = confidence
            signal["reason"] = f"Waiting for signal (confidence: {confidence:.2f}) | " + " | ".join(reasons) if reasons else "No clear signal"

        # 내부 상태 업데이트
        self.last_ma_fast = ma_fast
        self.last_ma_slow = ma_slow
        self.last_price = current_price

        return signal


def create_ultra_aggressive_strategy(params: Optional[Dict] = None):
    """초공격적 전략 인스턴스 생성"""
    return UltraAggressiveStrategy(params)
