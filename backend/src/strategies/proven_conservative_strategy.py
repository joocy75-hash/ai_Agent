"""
Proven Conservative Strategy - EMA Crossover + Volume Confirmation

보수적인 EMA 크로스오버 전략으로 안정적인 수익을 추구합니다.
- 진입 조건: EMA 골든/데드 크로스 + 거래량 확인
- 손절/익절: ATR 기반 동적 설정
- 리스크 관리: 낮은 레버리지, 작은 포지션 사이즈
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def calculate_ema(prices: List[float], period: int) -> float:
    """지수이동평균 계산"""
    if len(prices) < period:
        return prices[-1] if prices else 0

    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period

    for price in prices[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))

    return ema


def calculate_atr(candles: List[Dict], period: int = 14) -> float:
    """Average True Range 계산"""
    if len(candles) < period + 1:
        return 0

    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i].get('high', 0)
        low = candles[i].get('low', 0)
        prev_close = candles[i-1].get('close', 0)

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0

    return sum(true_ranges[-period:]) / period


def calculate_volume_ratio(candles: List[Dict], period: int = 20) -> float:
    """현재 거래량 / 평균 거래량 비율"""
    if len(candles) < period + 1:
        return 1.0

    volumes = [c.get('volume', 0) for c in candles[-(period+1):-1]]
    avg_volume = sum(volumes) / len(volumes) if volumes else 1
    current_volume = candles[-1].get('volume', 0)

    return current_volume / avg_volume if avg_volume > 0 else 1.0


def generate_signal(
    current_price: float,
    candles: List[Dict],
    params: Optional[Dict] = None,
    current_position: Optional[Dict] = None
) -> Dict:
    """
    EMA 크로스오버 + 거래량 확인 기반 매매 신호 생성

    Args:
        current_price: 현재 가격
        candles: 캔들 데이터 리스트
        params: 전략 파라미터
        current_position: 현재 포지션 정보

    Returns:
        {
            "action": "buy" | "sell" | "hold" | "close",
            "confidence": 0.0 ~ 1.0,
            "reason": str,
            "stop_loss": float,
            "take_profit": float,
            "size": float
        }
    """
    params = params or {}

    # 파라미터 설정
    fast_period = params.get('fast_ema', 9)
    slow_period = params.get('slow_ema', 21)
    volume_threshold = params.get('volume_threshold', 1.2)
    atr_stop_multiplier = params.get('atr_stop_multiplier', 2.0)
    atr_profit_multiplier = params.get('atr_profit_multiplier', 3.0)
    min_confidence = params.get('min_confidence', 0.6)

    # 기본 응답
    default_response = {
        "action": "hold",
        "confidence": 0.5,
        "reason": "Analyzing market conditions",
        "stop_loss": None,
        "take_profit": None,
        "size": 0.001,
        "strategy_type": "proven_conservative"
    }

    # 데이터 검증
    if not candles or len(candles) < slow_period + 5:
        default_response["reason"] = f"Insufficient data: {len(candles) if candles else 0} candles (need {slow_period + 5})"
        return default_response

    try:
        # 종가 추출
        closes = [c.get('close', 0) for c in candles]

        # EMA 계산
        fast_ema = calculate_ema(closes, fast_period)
        slow_ema = calculate_ema(closes, slow_period)

        # 이전 EMA 계산 (크로스오버 확인용)
        prev_closes = closes[:-1]
        prev_fast_ema = calculate_ema(prev_closes, fast_period)
        prev_slow_ema = calculate_ema(prev_closes, slow_period)

        # ATR 계산
        atr = calculate_atr(candles)

        # 거래량 비율
        volume_ratio = calculate_volume_ratio(candles)

        # 크로스오버 감지
        golden_cross = prev_fast_ema <= prev_slow_ema and fast_ema > slow_ema
        death_cross = prev_fast_ema >= prev_slow_ema and fast_ema < slow_ema

        # 거래량 확인
        volume_confirmed = volume_ratio >= volume_threshold

        # 트렌드 강도 계산
        ema_diff_percent = abs(fast_ema - slow_ema) / slow_ema * 100 if slow_ema > 0 else 0
        trend_strength = min(ema_diff_percent / 2, 1.0)  # 0~1 정규화

        # 손절/익절 계산
        stop_loss_distance = atr * atr_stop_multiplier
        take_profit_distance = atr * atr_profit_multiplier

        # 현재 포지션 확인
        has_long = current_position and current_position.get('side') == 'long' and current_position.get('size', 0) > 0
        has_short = current_position and current_position.get('side') == 'short' and current_position.get('size', 0) > 0

        # 매수 신호: 골든 크로스 + 거래량 확인
        if golden_cross and volume_confirmed and not has_long:
            confidence = 0.5 + (trend_strength * 0.3) + (min(volume_ratio - 1, 1) * 0.2)
            confidence = min(confidence, 0.95)

            if confidence >= min_confidence:
                return {
                    "action": "buy",
                    "confidence": round(confidence, 2),
                    "reason": f"Golden Cross (EMA{fast_period}>{slow_ema:.0f}) + Volume {volume_ratio:.1f}x",
                    "stop_loss": round(current_price - stop_loss_distance, 2),
                    "take_profit": round(current_price + take_profit_distance, 2),
                    "size": 0.001,
                    "strategy_type": "proven_conservative",
                    "indicators": {
                        "fast_ema": round(fast_ema, 2),
                        "slow_ema": round(slow_ema, 2),
                        "atr": round(atr, 2),
                        "volume_ratio": round(volume_ratio, 2)
                    }
                }

        # 매도 신호: 데드 크로스 + 거래량 확인
        if death_cross and volume_confirmed and not has_short:
            confidence = 0.5 + (trend_strength * 0.3) + (min(volume_ratio - 1, 1) * 0.2)
            confidence = min(confidence, 0.95)

            if confidence >= min_confidence:
                return {
                    "action": "sell",
                    "confidence": round(confidence, 2),
                    "reason": f"Death Cross (EMA{fast_period}<{slow_ema:.0f}) + Volume {volume_ratio:.1f}x",
                    "stop_loss": round(current_price + stop_loss_distance, 2),
                    "take_profit": round(current_price - take_profit_distance, 2),
                    "size": 0.001,
                    "strategy_type": "proven_conservative",
                    "indicators": {
                        "fast_ema": round(fast_ema, 2),
                        "slow_ema": round(slow_ema, 2),
                        "atr": round(atr, 2),
                        "volume_ratio": round(volume_ratio, 2)
                    }
                }

        # 포지션 청산 조건: 반대 크로스
        if has_long and death_cross:
            return {
                "action": "close",
                "confidence": 0.7,
                "reason": "Close Long: Death Cross detected",
                "stop_loss": None,
                "take_profit": None,
                "size": current_position.get('size', 0.001),
                "strategy_type": "proven_conservative"
            }

        if has_short and golden_cross:
            return {
                "action": "close",
                "confidence": 0.7,
                "reason": "Close Short: Golden Cross detected",
                "stop_loss": None,
                "take_profit": None,
                "size": current_position.get('size', 0.001),
                "strategy_type": "proven_conservative"
            }

        # 홀드 (신호 없음)
        trend_direction = "Bullish" if fast_ema > slow_ema else "Bearish"
        return {
            "action": "hold",
            "confidence": 0.5,
            "reason": f"{trend_direction} trend, waiting for crossover signal",
            "stop_loss": None,
            "take_profit": None,
            "size": 0.001,
            "strategy_type": "proven_conservative",
            "indicators": {
                "fast_ema": round(fast_ema, 2),
                "slow_ema": round(slow_ema, 2),
                "atr": round(atr, 2),
                "volume_ratio": round(volume_ratio, 2)
            }
        }

    except Exception as e:
        logger.error(f"Strategy error: {e}", exc_info=True)
        default_response["reason"] = f"Error: {str(e)}"
        return default_response


class ProvenConservativeStrategy:
    """클래스 기반 전략 인터페이스"""

    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}

    def generate_signal(
        self,
        current_price: float,
        candles: List[Dict],
        current_position: Optional[Dict] = None
    ) -> Dict:
        return generate_signal(current_price, candles, self.params, current_position)
