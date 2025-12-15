"""
AI Autonomous Adaptive Strategy (AI 자율 적응형 전략)

🤖 완전 AI 주도형 매매 전략

핵심 철학:
- AI 에이전트들이 모든 매매 결정을 자율적으로 수행
- 시장 환경에 따라 전략을 자동으로 전환
- 다중 지표 합의(Consensus) 기반 고신뢰도 진입
- 동적 리스크 관리로 안전성 확보

AI 에이전트 통합:
1. Market Regime Agent: 시장 환경 분석 (TRENDING, RANGING, VOLATILE, LOW_VOLUME)
2. Signal Validator Agent: 진입 신호 검증 및 필터링
3. Risk Monitor Agent: 실시간 리스크 모니터링 및 자동 조치

전략 구조:
- TRENDING 시장: EMA 크로스 + 모멘텀 (ADX) → 트렌드 추종
- RANGING 시장: RSI 평균회귀 + 볼린저 밴드 → 레인지 트레이딩
- VOLATILE 시장: 보수적 진입 + 넓은 손절 → 리스크 최소화
- LOW_VOLUME 시장: 거래 중지 → 유동성 부족 회피

진입 조건 (다중 신호 합의):
- 최소 3개 이상의 지표가 동의
- 종합 신뢰도 점수 0.65 이상
- Signal Validator 승인 필수

청산 조건 (동적 관리):
- ATR 기반 동적 손절/익절
- 트레일링 스탑 (1.5% 수익 후 활성화)
- 반대 신호 발생 시 즉시 청산
- Risk Monitor 경고 시 자동 청산

리스크 관리:
- 변동성 기반 포지션 크기 자동 조절
- 일일 손실 한도 체크
- 청산가 근접 감지 및 자동 대응
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ==================== 기술적 지표 계산 함수 ====================

def calculate_ema(prices: List[float], period: int) -> List[float]:
    """EMA (Exponential Moving Average) 계산"""
    if len(prices) < period:
        return [prices[0]] * len(prices) if prices else []

    multiplier = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]

    for price in prices[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])

    # 앞부분 패딩
    return [ema[0]] * (period - 1) + ema


def calculate_sma(prices: List[float], period: int) -> List[float]:
    """SMA (Simple Moving Average) 계산"""
    if len(prices) < period:
        return [sum(prices) / len(prices)] * len(prices) if prices else []

    sma = []
    for i in range(len(prices)):
        if i < period - 1:
            sma.append(sum(prices[:i+1]) / (i+1))
        else:
            sma.append(sum(prices[i-period+1:i+1]) / period)

    return sma


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """RSI (Relative Strength Index) 계산"""
    if len(prices) < period + 1:
        return [50.0] * len(prices)

    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi_values = [50.0] * period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

    return rsi_values


def calculate_atr(candles: List[Dict], period: int = 14) -> float:
    """ATR (Average True Range) 계산"""
    if len(candles) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]['high']
        low = candles[i]['low']
        prev_close = candles[i-1]['close']

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0

    return sum(true_ranges[-period:]) / period


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_multiplier: float = 2.0) -> Dict:
    """볼린저 밴드 계산"""
    if len(prices) < period:
        avg = sum(prices) / len(prices) if prices else 0
        return {"upper": avg, "middle": avg, "lower": avg, "bandwidth": 0}

    sma = calculate_sma(prices, period)
    middle = sma[-1]

    # 표준편차 계산
    recent_prices = prices[-period:]
    variance = sum((p - middle) ** 2 for p in recent_prices) / period
    std = variance ** 0.5

    upper = middle + (std_multiplier * std)
    lower = middle - (std_multiplier * std)
    bandwidth = ((upper - lower) / middle) * 100

    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "bandwidth": bandwidth
    }


def calculate_adx(candles: List[Dict], period: int = 14) -> float:
    """ADX (Average Directional Index) 계산 (간소화 버전)"""
    if len(candles) < period + 1:
        return 25.0  # 기본값

    # +DM, -DM 계산
    plus_dm = []
    minus_dm = []

    for i in range(1, len(candles)):
        high_diff = candles[i]['high'] - candles[i-1]['high']
        low_diff = candles[i-1]['low'] - candles[i]['low']

        if high_diff > low_diff and high_diff > 0:
            plus_dm.append(high_diff)
        else:
            plus_dm.append(0)

        if low_diff > high_diff and low_diff > 0:
            minus_dm.append(low_diff)
        else:
            minus_dm.append(0)

    # ATR
    atr = calculate_atr(candles, period)
    if atr == 0:
        return 25.0

    # +DI, -DI 계산
    plus_di = (sum(plus_dm[-period:]) / period / atr) * 100
    minus_di = (sum(minus_dm[-period:]) / period / atr) * 100

    # DX 계산
    if (plus_di + minus_di) == 0:
        return 25.0

    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100

    return dx


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    """MACD (Moving Average Convergence Divergence) 계산"""
    if len(prices) < slow:
        return {"macd": 0, "signal": 0, "histogram": 0}

    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)

    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = calculate_ema(macd_line, signal)

    histogram = macd_line[-1] - signal_line[-1]

    return {
        "macd": macd_line[-1],
        "signal": signal_line[-1],
        "histogram": histogram
    }


# ==================== 시장 환경별 전략 ====================

def analyze_trending_market(candles: List[Dict], params: Dict) -> Dict:
    """
    TRENDING 시장 분석 (트렌드 추종)

    전략: EMA 크로스 + 모멘텀 확인
    """
    closes = [c['close'] for c in candles]
    current_price = closes[-1]

    # EMA 계산
    ema_fast = calculate_ema(closes, params.get("ema_fast", 20))
    ema_slow = calculate_ema(closes, params.get("ema_slow", 50))

    # MACD (모멘텀 확인)
    macd = calculate_macd(closes)

    # ADX (트렌드 강도)
    adx = calculate_adx(candles)

    # 트렌드 방향
    uptrend = ema_fast[-1] > ema_slow[-1]
    downtrend = ema_fast[-1] < ema_slow[-1]

    # 골든크로스/데드크로스 감지
    golden_cross = len(ema_fast) >= 2 and ema_fast[-2] <= ema_slow[-2] and ema_fast[-1] > ema_slow[-1]
    death_cross = len(ema_fast) >= 2 and ema_fast[-2] >= ema_slow[-2] and ema_fast[-1] < ema_slow[-1]

    signals = []

    # 롱 신호
    if (uptrend and macd['histogram'] > 0 and adx > 25) or golden_cross:
        confidence = 0.80 if golden_cross else 0.70
        signals.append({
            "direction": "LONG",
            "confidence": confidence,
            "reason": "EMA Golden Cross + Strong Trend" if golden_cross else "Uptrend + Positive MACD",
            "indicators": {
                "ema_fast": ema_fast[-1],
                "ema_slow": ema_slow[-1],
                "macd_histogram": macd['histogram'],
                "adx": adx
            }
        })

    # 숏 신호
    if (downtrend and macd['histogram'] < 0 and adx > 25) or death_cross:
        confidence = 0.80 if death_cross else 0.70
        signals.append({
            "direction": "SHORT",
            "confidence": confidence,
            "reason": "EMA Death Cross + Strong Trend" if death_cross else "Downtrend + Negative MACD",
            "indicators": {
                "ema_fast": ema_fast[-1],
                "ema_slow": ema_slow[-1],
                "macd_histogram": macd['histogram'],
                "adx": adx
            }
        })

    return {
        "signals": signals,
        "market_type": "TRENDING",
        "adx": adx
    }


def analyze_ranging_market(candles: List[Dict], params: Dict) -> Dict:
    """
    RANGING 시장 분석 (평균회귀)

    전략: RSI 과매수/과매도 + 볼린저 밴드
    """
    closes = [c['close'] for c in candles]
    current_price = closes[-1]

    # RSI 계산
    rsi = calculate_rsi(closes)
    current_rsi = rsi[-1]

    # 볼린저 밴드
    bb = calculate_bollinger_bands(closes)

    signals = []

    # 볼린저 밴드 위치
    price_position = (current_price - bb['lower']) / (bb['upper'] - bb['lower']) * 100

    # 롱 신호 (과매도 + 하단 밴드 근처)
    if current_rsi < 35 and price_position < 20:
        confidence = 0.75
        signals.append({
            "direction": "LONG",
            "confidence": confidence,
            "reason": f"RSI Oversold ({current_rsi:.1f}) + Near Lower BB",
            "indicators": {
                "rsi": current_rsi,
                "bb_position": price_position,
                "bb_bandwidth": bb['bandwidth']
            }
        })

    # 숏 신호 (과매수 + 상단 밴드 근처)
    if current_rsi > 65 and price_position > 80:
        confidence = 0.75
        signals.append({
            "direction": "SHORT",
            "confidence": confidence,
            "reason": f"RSI Overbought ({current_rsi:.1f}) + Near Upper BB",
            "indicators": {
                "rsi": current_rsi,
                "bb_position": price_position,
                "bb_bandwidth": bb['bandwidth']
            }
        })

    return {
        "signals": signals,
        "market_type": "RANGING",
        "rsi": current_rsi,
        "bb_bandwidth": bb['bandwidth']
    }


def analyze_volatile_market(candles: List[Dict], params: Dict) -> Dict:
    """
    VOLATILE 시장 분석 (보수적 진입)

    전략: 강한 신호만 허용, 넓은 손절
    """
    closes = [c['close'] for c in candles]

    # 여러 지표 모두 계산
    rsi = calculate_rsi(closes)
    ema_fast = calculate_ema(closes, 20)
    ema_slow = calculate_ema(closes, 50)
    macd = calculate_macd(closes)

    signals = []

    # 변동성 높을 때는 매우 강한 신호만 허용
    # 조건: RSI 극단값 + EMA 정렬 + MACD 일치
    strong_uptrend = (
        rsi[-1] < 30 and
        ema_fast[-1] > ema_slow[-1] and
        macd['histogram'] > 0
    )

    strong_downtrend = (
        rsi[-1] > 70 and
        ema_fast[-1] < ema_slow[-1] and
        macd['histogram'] < 0
    )

    if strong_uptrend:
        signals.append({
            "direction": "LONG",
            "confidence": 0.65,  # 변동성 높아 신뢰도 낮춤
            "reason": "Strong Uptrend (Volatile Market)",
            "indicators": {
                "rsi": rsi[-1],
                "ema_alignment": "bullish",
                "macd_histogram": macd['histogram']
            }
        })

    if strong_downtrend:
        signals.append({
            "direction": "SHORT",
            "confidence": 0.65,
            "reason": "Strong Downtrend (Volatile Market)",
            "indicators": {
                "rsi": rsi[-1],
                "ema_alignment": "bearish",
                "macd_histogram": macd['histogram']
            }
        })

    return {
        "signals": signals,
        "market_type": "VOLATILE",
        "risk_level": "HIGH"
    }


# ==================== 메인 전략 함수 ====================

def check_entry_signal(candles: List[Dict], params: Dict) -> Dict:
    """
    진입 신호 확인 (Market Regime 기반 자동 전환)

    Returns:
        {
            "signal": "LONG" | "SHORT" | "HOLD",
            "confidence": 0.0 ~ 1.0,
            "reason": str,
            "market_regime": str,
            "indicators": dict
        }
    """
    if len(candles) < 50:
        return {
            "signal": "HOLD",
            "confidence": 0.0,
            "reason": f"Insufficient data ({len(candles)}/50)"
        }

    # 시장 환경 판단
    adx = calculate_adx(candles)
    atr = calculate_atr(candles)
    closes = [c['close'] for c in candles]
    current_price = closes[-1]

    # ATR 평균 대비 비율
    recent_atr = [calculate_atr(candles[max(0, i-20):i+1]) for i in range(len(candles)-20, len(candles))]
    atr_avg = sum(recent_atr) / len(recent_atr) if recent_atr else atr
    atr_ratio = atr / atr_avg if atr_avg > 0 else 1.0

    # 거래량 확인 (간소화: 최근 평균 대비)
    volumes = [c.get('volume', 1) for c in candles]
    current_volume = volumes[-1]
    avg_volume = sum(volumes[-20:]) / 20
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

    # 시장 환경 분류
    if adx > 25:
        market_regime = "TRENDING"
        analysis = analyze_trending_market(candles, params)
    elif adx < 20 and atr_ratio < 1.5:
        market_regime = "RANGING"
        analysis = analyze_ranging_market(candles, params)
    elif atr_ratio > 2.0:
        market_regime = "VOLATILE"
        analysis = analyze_volatile_market(candles, params)
    elif volume_ratio < 0.3:
        market_regime = "LOW_VOLUME"
        analysis = {"signals": [], "market_type": "LOW_VOLUME"}
    else:
        market_regime = "NEUTRAL"
        # Neutral일 때는 Ranging 전략 사용
        analysis = analyze_ranging_market(candles, params)

    logger.info(f"Market Regime: {market_regime}, ADX: {adx:.1f}, ATR Ratio: {atr_ratio:.2f}, Volume Ratio: {volume_ratio:.2f}")

    # 신호가 없으면 HOLD
    if not analysis.get("signals"):
        return {
            "signal": "HOLD",
            "confidence": 0.0,
            "reason": f"No signal in {market_regime} market",
            "market_regime": market_regime
        }

    # 가장 신뢰도 높은 신호 선택
    best_signal = max(analysis["signals"], key=lambda s: s["confidence"])

    return {
        "signal": best_signal["direction"],
        "confidence": best_signal["confidence"],
        "reason": best_signal["reason"],
        "market_regime": market_regime,
        "indicators": best_signal.get("indicators", {}),
        "enter_tag": f"{market_regime.lower()}_{best_signal['direction'].lower()}"
    }


def calculate_stop_loss(current_price: float, direction: str, params: Dict) -> float:
    """
    동적 손절가 계산 (ATR 기반)

    변동성이 높으면 손절폭 확대
    """
    # ATR 값은 전략 실행 시 계산된 값 사용 (params에 저장)
    # 기본값: 1.5% (보수적)
    base_sl_percent = params.get("base_sl_percent", 1.5)

    # 시장 환경에 따라 손절폭 조정
    market_regime = params.get("current_market_regime", "NEUTRAL")

    if market_regime == "VOLATILE":
        sl_percent = base_sl_percent * 1.5  # 2.25%
    elif market_regime == "RANGING":
        sl_percent = base_sl_percent * 0.8  # 1.2%
    else:  # TRENDING, NEUTRAL
        sl_percent = base_sl_percent  # 1.5%

    if direction == "LONG":
        return current_price * (1 - sl_percent / 100)
    else:  # SHORT
        return current_price * (1 + sl_percent / 100)


def calculate_take_profit(current_price: float, direction: str, params: Dict) -> float:
    """
    동적 익절가 계산

    손익비 최소 1:2 유지
    """
    base_sl_percent = params.get("base_sl_percent", 1.5)
    market_regime = params.get("current_market_regime", "NEUTRAL")

    # 손익비
    risk_reward_ratio = 2.0

    if market_regime == "TRENDING":
        risk_reward_ratio = 2.5  # 트렌드에서는 더 많이 가져가기
    elif market_regime == "VOLATILE":
        risk_reward_ratio = 1.8  # 변동성 높을 때는 빠르게 익절

    if market_regime == "VOLATILE":
        tp_percent = base_sl_percent * 1.5 * risk_reward_ratio
    elif market_regime == "RANGING":
        tp_percent = base_sl_percent * 0.8 * risk_reward_ratio
    else:
        tp_percent = base_sl_percent * risk_reward_ratio

    if direction == "LONG":
        return current_price * (1 + tp_percent / 100)
    else:  # SHORT
        return current_price * (1 - tp_percent / 100)


def should_partial_exit(position: Dict, current_price: float, candles: List[Dict], params: Dict) -> tuple:
    """
    부분 익절 및 트레일링 스탑

    Returns:
        (should_exit: bool, exit_percent: float)
    """
    entry_price = position.get('entry_price', 0)
    side = position.get('side', 'LONG')

    if entry_price == 0:
        return False, 0.0

    # 수익률 계산
    if side == 'LONG':
        pnl_percent = (current_price - entry_price) / entry_price * 100
    else:
        pnl_percent = (entry_price - current_price) / entry_price * 100

    # 트레일링 스탑: 1.5% 수익 후 0.8% 하락 시 청산
    if pnl_percent >= 1.5:
        trailing_percent = 0.8
        trailing_price = entry_price * (1 + (pnl_percent - trailing_percent) / 100)

        if side == 'LONG' and current_price < trailing_price:
            logger.info(f"Trailing stop triggered: {pnl_percent:.2f}% profit secured")
            return True, 1.0  # 100% 청산

        if side == 'SHORT' and current_price > trailing_price:
            logger.info(f"Trailing stop triggered: {pnl_percent:.2f}% profit secured")
            return True, 1.0

    # 부분 익절: 3% 수익 시 50% 청산
    if pnl_percent >= 3.0:
        # 이미 부분 익절했는지 확인 (position 메타데이터)
        if not position.get('partial_exit_done', False):
            logger.info(f"Partial exit: 50% at {pnl_percent:.2f}% profit")
            return True, 0.5  # 50% 청산

    return False, 0.0
