"""
AI Role Division Strategy & Proven Aggressive Strategy

사용자 정의 전략에 대한 백테스트 호환성 구현
"""

from .base import StrategyBase


class AIRoleDivisionStrategy(StrategyBase):
    """
    AI 역할분담 전략

    진입 조건:
    - LONG: 단기 EMA > 장기 EMA 크로스오버 + RSI < overbought
    - SHORT: 단기 EMA < 장기 EMA 크로스오버 + RSI > oversold

    리스크 관리:
    - 손절: -1.5%
    - 익절: +3.0%
    """

    def __init__(
        self,
        ema_short: int = 9,
        ema_long: int = 21,
        rsi_period: int = 14,
        rsi_oversold: float = 35,
        rsi_overbought: float = 65,
    ):
        self.ema_short = ema_short
        self.ema_long = ema_long
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

        # 데이터 버퍼
        self._closes = []
        self._prev_short_ema = None
        self._prev_long_ema = None

        # EMA multipliers
        self._short_mult = 2.0 / (ema_short + 1)
        self._long_mult = 2.0 / (ema_long + 1)
        self._short_ema = None
        self._long_ema = None

    def _update_ema(self, close: float):
        """EMA 업데이트"""
        self._closes.append(close)

        if len(self._closes) < self.ema_long:
            return None, None

        # 초기화
        if self._short_ema is None:
            self._short_ema = sum(self._closes[-self.ema_short :]) / self.ema_short
            self._long_ema = sum(self._closes[-self.ema_long :]) / self.ema_long
        else:
            self._prev_short_ema = self._short_ema
            self._prev_long_ema = self._long_ema
            self._short_ema = (
                close - self._short_ema
            ) * self._short_mult + self._short_ema
            self._long_ema = (close - self._long_ema) * self._long_mult + self._long_ema

        return self._short_ema, self._long_ema

    def _calculate_rsi(self) -> float:
        """RSI 계산"""
        if len(self._closes) < self.rsi_period + 1:
            return 50  # 중립

        changes = [
            self._closes[i] - self._closes[i - 1] for i in range(-self.rsi_period, 0)
        ]
        gains = [c if c > 0 else 0 for c in changes]
        losses = [-c if c < 0 else 0 for c in changes]

        avg_gain = sum(gains) / self.rsi_period
        avg_loss = sum(losses) / self.rsi_period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def on_candle(self, candle: dict, position: dict | None) -> str:
        """
        캔들 처리 및 신호 생성

        Args:
            candle: dict with 'close' price
            position: current position or None

        Returns:
            'buy', 'sell', or 'hold'
        """
        close = candle["close"]
        short_ema, long_ema = self._update_ema(close)

        # 데이터 부족
        if short_ema is None or long_ema is None:
            return "hold"

        if self._prev_short_ema is None or self._prev_long_ema is None:
            return "hold"

        rsi = self._calculate_rsi()

        # 포지션 없을 때 - 크로스오버 시 진입
        if position is None:
            # 골든 크로스 (상향 돌파) + RSI 확인
            if self._prev_short_ema <= self._prev_long_ema and short_ema > long_ema:
                if rsi < self.rsi_overbought:
                    return "buy"

            # 데드 크로스 (하향 돌파) + RSI 확인
            if self._prev_short_ema >= self._prev_long_ema and short_ema < long_ema:
                if rsi > self.rsi_oversold:
                    return "sell"

        # 포지션 있을 때 - 반대 크로스오버 시 청산
        else:
            if position["direction"] == "long":
                if self._prev_short_ema >= self._prev_long_ema and short_ema < long_ema:
                    return "sell"
            elif position["direction"] == "short":
                if self._prev_short_ema <= self._prev_long_ema and short_ema > long_ema:
                    return "buy"

        return "hold"


class ProvenAggressiveStrategy(StrategyBase):
    """
    공격적 모멘텀 브레이크아웃 전략

    진입 조건:
    - 볼린저 밴드 상단 돌파 + EMA 골든 크로스
    - 볼린저 밴드 하단 이탈 + EMA 데드 크로스
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        ema_short: int = 9,
        ema_long: int = 21,
    ):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.ema_short = ema_short
        self.ema_long = ema_long

        self._closes = []
        self._prev_close = None

        # EMA
        self._short_mult = 2.0 / (ema_short + 1)
        self._long_mult = 2.0 / (ema_long + 1)
        self._short_ema = None
        self._long_ema = None

    def _update_ema(self, close: float):
        """EMA 업데이트"""
        if len(self._closes) < self.ema_long:
            return None, None

        if self._short_ema is None:
            self._short_ema = sum(self._closes[-self.ema_short :]) / self.ema_short
            self._long_ema = sum(self._closes[-self.ema_long :]) / self.ema_long
        else:
            self._short_ema = (
                close - self._short_ema
            ) * self._short_mult + self._short_ema
            self._long_ema = (close - self._long_ema) * self._long_mult + self._long_ema

        return self._short_ema, self._long_ema

    def _calculate_bollinger_bands(self) -> tuple:
        """볼린저 밴드 계산"""
        if len(self._closes) < self.bb_period:
            return None, None, None

        recent = self._closes[-self.bb_period :]
        sma = sum(recent) / self.bb_period
        variance = sum((p - sma) ** 2 for p in recent) / self.bb_period
        std = variance**0.5

        upper = sma + (self.bb_std * std)
        lower = sma - (self.bb_std * std)

        return lower, sma, upper

    def on_candle(self, candle: dict, position: dict | None) -> str:
        """캔들 처리 및 신호 생성"""
        close = candle["close"]
        self._closes.append(close)

        short_ema, long_ema = self._update_ema(close)
        bands = self._calculate_bollinger_bands()

        if short_ema is None or bands[0] is None:
            self._prev_close = close
            return "hold"

        lower, middle, upper = bands

        # 포지션 없을 때
        if position is None:
            if self._prev_close is not None:
                # 상단 밴드 돌파 + EMA 골든 크로스
                if self._prev_close < upper and close >= upper:
                    if short_ema > long_ema:
                        self._prev_close = close
                        return "buy"

                # 하단 밴드 이탈 + EMA 데드 크로스
                if self._prev_close > lower and close <= lower:
                    if short_ema < long_ema:
                        self._prev_close = close
                        return "sell"

        # 포지션 있을 때 - 중간 밴드 복귀 시 청산
        else:
            if position["direction"] == "long":
                # 가격이 중간 밴드 아래로 떨어지면 청산
                if close < middle and short_ema < long_ema:
                    self._prev_close = close
                    return "sell"
            elif position["direction"] == "short":
                # 가격이 중간 밴드 위로 올라가면 청산
                if close > middle and short_ema > long_ema:
                    self._prev_close = close
                    return "buy"

        self._prev_close = close
        return "hold"
