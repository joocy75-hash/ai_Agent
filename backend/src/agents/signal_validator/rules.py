"""
Signal Validation Rules (시그널 검증 규칙)

시그널을 검증하는 다양한 규칙 정의
"""

import logging
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ValidationRules:
    """
    시그널 검증 규칙 컬렉션

    각 규칙은 (passed: bool, message: str) 튜플을 반환
    """

    @staticmethod
    def check_market_regime_alignment(
        signal_action: str,
        market_regime: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        시장 환경과 시그널 정렬 체크

        Args:
            signal_action: buy/sell/close
            market_regime: 시장 환경 정보

        Returns:
            (통과 여부, 메시지)
        """
        regime_type = market_regime.get("regime_type", "unknown")

        # volatile/low_volume 시장에서는 신규 진입 거부
        if signal_action in {"buy", "sell"}:
            if regime_type in {"volatile", "low_volume"}:
                return False, f"Trading blocked in {regime_type} market (high risk)"

        # 추세 상승장에서 매수, 하락장에서 매도만 허용
        if signal_action == "buy":
            if regime_type == "trending_up":
                return True, "Market regime aligned: buy in uptrend"
            elif regime_type == "ranging":
                return True, "Buy signal in ranging market (caution)"
            else:
                return False, f"Buy signal not aligned with {regime_type}"

        elif signal_action == "sell":
            if regime_type == "trending_down":
                return True, "Market regime aligned: sell in downtrend"
            elif regime_type == "ranging":
                return True, "Sell signal in ranging market (caution)"
            else:
                return False, f"Sell signal not aligned with {regime_type}"

        # close는 항상 허용
        return True, "Close signal allowed in any regime"

    @staticmethod
    def check_volatility_threshold(
        volatility: float,
        max_volatility: float = 5.0
    ) -> Tuple[bool, str]:
        """
        변동성 임계값 체크

        Args:
            volatility: 현재 변동성 (%)
            max_volatility: 최대 허용 변동성

        Returns:
            (통과 여부, 메시지)
        """
        if volatility > max_volatility:
            return False, f"Volatility too high: {volatility:.2f}% > {max_volatility}%"

        return True, f"Volatility acceptable: {volatility:.2f}%"

    @staticmethod
    def check_signal_confidence(
        confidence: float,
        min_confidence: float = 0.6
    ) -> Tuple[bool, str, Optional[float]]:
        """
        시그널 신뢰도 체크

        Args:
            confidence: 시그널 신뢰도 (0.0 ~ 1.0)
            min_confidence: 최소 요구 신뢰도

        Returns:
            (통과 여부, 메시지, 포지션 조정 비율)
            - < 0.6: 거부
            - 0.6 ~ 0.7: 포지션 50% 축소
            - >= 0.7: 정상
        """
        if confidence < 0.6:
            return False, f"Confidence too low: {confidence:.2f} < 0.6 (REJECTED)", None

        elif confidence < 0.7:
            return True, f"Confidence moderate: {confidence:.2f} (POSITION REDUCED 50%)", 0.5

        return True, f"Confidence sufficient: {confidence:.2f}", 1.0

    @staticmethod
    def check_price_near_support_resistance(
        current_price: float,
        support_level: float,
        resistance_level: float,
        signal_action: str,
        threshold_percent: float = 1.0
    ) -> Tuple[bool, str]:
        """
        지지/저항 근처에서의 시그널 체크

        Args:
            current_price: 현재 가격
            support_level: 지지선
            resistance_level: 저항선
            signal_action: buy/sell/close
            threshold_percent: 근접 판단 임계값 (%)

        Returns:
            (통과 여부, 메시지)
        """
        if not support_level or not resistance_level:
            return True, "Support/resistance not available"

        support_dist = abs(current_price - support_level) / current_price * 100
        resistance_dist = abs(current_price - resistance_level) / current_price * 100

        # 매수: 지지선 근처에서 유리
        if signal_action == "buy":
            if support_dist < threshold_percent:
                return True, f"Buy near support (dist: {support_dist:.2f}%)"
            elif resistance_dist < threshold_percent:
                return False, f"Buy near resistance (dist: {resistance_dist:.2f}%)"

        # 매도: 저항선 근처에서 유리
        elif signal_action == "sell":
            if resistance_dist < threshold_percent:
                return True, f"Sell near resistance (dist: {resistance_dist:.2f}%)"
            elif support_dist < threshold_percent:
                return False, f"Sell near support (dist: {support_dist:.2f}%)"

        return True, "Price not near key levels"

    @staticmethod
    def check_trend_strength(
        trend_strength: float,
        signal_action: str,
        min_trend_adx: float = 20.0
    ) -> Tuple[bool, str]:
        """
        추세 강도 체크 (ADX 기반)

        Args:
            trend_strength: ADX 값
            signal_action: buy/sell/close
            min_trend_adx: 최소 요구 ADX

        Returns:
            (통과 여부, 메시지)
        """
        # close는 항상 허용
        if signal_action == "close":
            return True, "Close signal allowed regardless of trend strength"

        # buy/sell은 추세 강도 체크
        if trend_strength < min_trend_adx:
            return False, f"Trend too weak: ADX {trend_strength:.2f} < {min_trend_adx}"

        return True, f"Trend strength sufficient: ADX {trend_strength:.2f}"

    @staticmethod
    def check_recent_trade_frequency(
        recent_trades_count: int,
        max_trades_per_hour: int = 10
    ) -> Tuple[bool, str]:
        """
        최근 거래 빈도 체크 (과매매 방지)

        Args:
            recent_trades_count: 최근 1시간 거래 수
            max_trades_per_hour: 시간당 최대 거래 수

        Returns:
            (통과 여부, 메시지)
        """
        if recent_trades_count >= max_trades_per_hour:
            return False, f"Too many trades: {recent_trades_count} >= {max_trades_per_hour}/hour"

        return True, f"Trade frequency acceptable: {recent_trades_count} trades/hour"

    @staticmethod
    def check_drawdown_limit(
        current_drawdown_percent: float,
        max_drawdown: float = 5.0
    ) -> Tuple[bool, str]:
        """
        최대 낙폭 한도 체크

        Args:
            current_drawdown_percent: 현재 낙폭 (%)
            max_drawdown: 최대 허용 낙폭

        Returns:
            (통과 여부, 메시지)
        """
        if current_drawdown_percent > max_drawdown:
            return False, f"Drawdown limit exceeded: {current_drawdown_percent:.2f}% > {max_drawdown}%"

        return True, f"Drawdown acceptable: {current_drawdown_percent:.2f}%"

    @staticmethod
    def check_sudden_price_change(
        price_change_5min: float,
        max_change_percent: float = 2.0
    ) -> Tuple[bool, str]:
        """
        급등락 필터 (5분 내 급격한 가격 변동 체크)

        Args:
            price_change_5min: 최근 5분간 가격 변동률 (%)
            max_change_percent: 최대 허용 변동률 (%)

        Returns:
            (통과 여부, 메시지)
        """
        abs_change = abs(price_change_5min)

        if abs_change > max_change_percent:
            return False, f"Sudden price change detected: {price_change_5min:+.2f}% (> {max_change_percent}%)"

        return True, f"Price change acceptable: {price_change_5min:+.2f}%"

    @staticmethod
    def check_position_reversal(
        signal_action: str,
        current_position_side: Optional[str],
        confidence: float,
        min_reversal_confidence: float = 0.8
    ) -> Tuple[bool, str]:
        """
        포지션 반전 검증

        현재 포지션과 반대 방향 신호일 때 높은 신뢰도 요구

        Args:
            signal_action: buy/sell/close
            current_position_side: long/short/None
            confidence: 시그널 신뢰도
            min_reversal_confidence: 반전 시 최소 신뢰도

        Returns:
            (통과 여부, 메시지)
        """
        # 포지션이 없으면 반전이 아님
        if not current_position_side or signal_action == "close":
            return True, "No position reversal"

        # 반전 체크
        is_reversal = (
            (current_position_side == "long" and signal_action == "sell") or
            (current_position_side == "short" and signal_action == "buy")
        )

        if is_reversal:
            if confidence < min_reversal_confidence:
                return False, (
                    f"Position reversal requires high confidence: "
                    f"{confidence:.2f} < {min_reversal_confidence} "
                    f"({current_position_side} → {signal_action})"
                )
            return True, f"Position reversal approved: {current_position_side} → {signal_action} (confidence: {confidence:.2f})"

        return True, "Signal direction aligned with current position"

    @staticmethod
    def check_consecutive_signals(
        signal_action: str,
        recent_signals: List[str],
        max_consecutive: int = 3
    ) -> Tuple[bool, str]:
        """
        연속 신호 필터 (같은 방향 3회 연속 시 4번째부터 거부)

        Args:
            signal_action: buy/sell/close
            recent_signals: 최근 신호 목록 (최신순)
            max_consecutive: 최대 허용 연속 횟수

        Returns:
            (통과 여부, 메시지)
        """
        if signal_action == "close" or not recent_signals:
            return True, "No consecutive signal check needed"

        # 최근 신호 중 같은 방향 연속 횟수 계산
        consecutive_count = 0
        for signal in recent_signals:
            if signal == signal_action:
                consecutive_count += 1
            else:
                break

        if consecutive_count >= max_consecutive:
            return False, (
                f"Too many consecutive {signal_action} signals: "
                f"{consecutive_count} >= {max_consecutive} (overtrading prevention)"
            )

        return True, f"Consecutive {signal_action} signals: {consecutive_count}/{max_consecutive}"

    @staticmethod
    def check_balance_limit(
        order_size_usd: float,
        available_balance: float,
        max_position_percent: float = 0.3
    ) -> Tuple[bool, str, Optional[float]]:
        """
        잔고 검증 (주문 크기 > available_balance * 30% → 축소)

        Args:
            order_size_usd: 주문 금액 (USD)
            available_balance: 가용 잔고 (USD)
            max_position_percent: 최대 포지션 비율 (기본 30%)

        Returns:
            (통과 여부, 메시지, 조정된 주문 금액)
        """
        if available_balance <= 0:
            return False, "Insufficient balance", None

        max_allowed = available_balance * max_position_percent

        if order_size_usd > max_allowed:
            adjusted_size = max_allowed
            reduction_pct = (1 - adjusted_size / order_size_usd) * 100
            return True, (
                f"Order size reduced: ${order_size_usd:.2f} → ${adjusted_size:.2f} "
                f"(-{reduction_pct:.1f}%, max {max_position_percent*100:.0f}% of balance)"
            ), adjusted_size

        return True, f"Order size acceptable: ${order_size_usd:.2f} ({order_size_usd/available_balance*100:.1f}% of balance)", order_size_usd
