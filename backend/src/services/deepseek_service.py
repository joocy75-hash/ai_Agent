"""
DeepSeek AI 서비스
전략 생성, 시장 분석 등에 AI를 활용합니다.

모델 정보:
- DeepSeek-V3.2 (2025년 최신 버전) 사용
- API: https://api.deepseek.com/v1/chat/completions
"""

import logging
import os
import requests
from typing import Dict, List, Any, Optional
from src.config import settings

logger = logging.getLogger(__name__)


class DeepSeekAIService:
    """DeepSeek AI 서비스 클래스"""

    # DeepSeek 모델 버전 (2025년 기준 최신)
    # deepseek-chat: DeepSeek-V3.2 호환 모델명
    # 참고: https://www.deepseek.com/docs/api-reference
    MODEL_VERSION = "deepseek-chat"

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.model = self.MODEL_VERSION

    def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        user_id: Optional[int] = None,
        require_user_id: bool = True,
    ) -> Optional[str]:
        """
        DeepSeek API 요청 (Issue #4: Rate Limiting 추가)

        Args:
            messages: API 메시지
            temperature: 온도 설정
            max_tokens: 최대 토큰 수
            user_id: 사용자 ID (Rate Limiting용)
            require_user_id: user_id 필수 여부 (기본: True)
        """
        if not self.api_key:
            raise ValueError("DeepSeek API key is not configured")

        # Issue #4: Rate Limiting 우회 방지 - user_id 필수 검증
        if require_user_id and user_id is None:
            raise ValueError(
                "user_id is required for DeepSeek API calls to enforce rate limiting. "
                "This prevents unlimited API calls and potential cost explosion."
            )

        # Issue #4: Rate Limiting 체크 (user_id가 있는 경우)
        if user_id:
            from src.middleware.rate_limit_improved import (
                deepseek_limiter_minute,
                deepseek_limiter_hour,
                deepseek_limiter_day
            )
            # 분당, 시간당, 일당 제한 모두 체크
            deepseek_limiter_minute.check(user_id)
            deepseek_limiter_hour.check(user_id)
            deepseek_limiter_day.check(user_id)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            # timeout=(connect_timeout, read_timeout)
            # connect: 5초 (연결 설정), read: 30초 (응답 대기)
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=(5, 30),
            )
            response.raise_for_status()

            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]

            return None

        except Exception as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            raise

    def generate_trading_strategies(self) -> List[Dict[str, Any]]:
        """기본 거래 전략 3개 생성"""

        system_prompt = """You are an expert cryptocurrency trading strategist. 
Generate 3 different trading strategies for automated trading on LBANK exchange.
Each strategy should be unique and suitable for different market conditions.

Return ONLY a valid JSON array with exactly 3 strategies. Each strategy must have:
- name: Strategy name (in Korean)
- description: Detailed description (in Korean)
- type: One of ["momentum", "mean_reversion", "breakout"]
- symbol: "btc_usdt"
- timeframe: One of ["1m", "5m", "15m", "1h", "4h"]
- parameters: JSON object with strategy-specific parameters

Example format:
[
  {
    "name": "모멘텀 돌파 전략",
    "description": "RSI와 이동평균을 활용한 모멘텀 기반 전략",
    "type": "momentum",
    "symbol": "btc_usdt",
    "timeframe": "15m",
    "parameters": {
      "rsi_period": 14,
      "rsi_overbought": 70,
      "rsi_oversold": 30,
      "ma_fast": 10,
      "ma_slow": 20,
      "stop_loss": 2.0,
      "take_profit": 5.0
    }
  }
]

Generate 3 complete strategies now."""

        user_prompt = """Create 3 professional trading strategies:
1. Momentum-based strategy (15m timeframe)
2. Mean reversion strategy (5m timeframe)  
3. Breakout strategy (1h timeframe)

Each should have different parameters and be optimized for BTC/USDT trading.
Return ONLY the JSON array, no additional text."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            # generate_trading_strategies는 시스템 초기화 시 호출되므로 rate limit 제외
            response = self._make_request(
                messages, temperature=0.8, max_tokens=2000, require_user_id=False
            )

            if response:
                # JSON 추출 (마크다운 코드 블록 제거)
                import json
                import re

                # ```json ... ``` 형식 제거
                json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
                if json_match:
                    response = json_match.group(1)
                elif "```" in response:
                    # ``` ... ``` 형식 제거
                    response = re.sub(r"```.*?\n", "", response)
                    response = re.sub(r"```", "", response)

                # JSON 파싱
                strategies = json.loads(response.strip())

                # 검증
                if isinstance(strategies, list) and len(strategies) >= 3:
                    return strategies[:3]  # 정확히 3개만 반환
                else:
                    # 기본 전략 반환
                    return self._get_default_strategies()

            return self._get_default_strategies()

        except Exception as e:
            logger.warning(f"Error generating strategies with AI: {str(e)}")
            # AI 실패 시 기본 전략 반환
            return self._get_default_strategies()

    def _get_default_strategies(self) -> List[Dict[str, Any]]:
        """기본 전략 (AI 실패 시 사용)"""
        return [
            {
                "name": "RSI 모멘텀 전략",
                "description": "RSI 지표를 활용한 모멘텀 기반 자동매매 전략입니다. RSI가 과매도 구간에서 매수하고 과매수 구간에서 매도합니다.",
                "type": "momentum",
                "symbol": "btc_usdt",
                "timeframe": "15m",
                "parameters": {
                    "rsi_period": 14,
                    "rsi_overbought": 70,
                    "rsi_oversold": 30,
                    "ma_period": 20,
                    "stop_loss": 2.0,
                    "take_profit": 5.0,
                    "position_size": 0.1,
                },
            },
            {
                "name": "볼린저 밴드 평균회귀",
                "description": "볼린저 밴드를 활용한 평균회귀 전략입니다. 가격이 하단 밴드에 닿으면 매수, 상단 밴드에 닿으면 매도합니다.",
                "type": "mean_reversion",
                "symbol": "btc_usdt",
                "timeframe": "5m",
                "parameters": {
                    "bb_period": 20,
                    "bb_std": 2.0,
                    "rsi_period": 14,
                    "stop_loss": 1.5,
                    "take_profit": 3.0,
                    "position_size": 0.1,
                },
            },
            {
                "name": "돌파 전략",
                "description": "가격이 저항선을 돌파할 때 매수하는 돌파 전략입니다. 높은 거래량과 함께 돌파가 발생할 때 진입합니다.",
                "type": "breakout",
                "symbol": "btc_usdt",
                "timeframe": "1h",
                "parameters": {
                    "lookback_period": 20,
                    "volume_multiplier": 1.5,
                    "atr_period": 14,
                    "stop_loss": 3.0,
                    "take_profit": 8.0,
                    "position_size": 0.1,
                },
            },
        ]

    def get_trading_signal(
        self,
        symbol: str,
        current_price: float,
        candles: List[Dict[str, Any]],
        current_position: Optional[Dict[str, Any]] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        실시간 AI 투자 판단 (Issue #4: Rate Limiting 지원)

        DeepSeek AI가 시장 데이터를 분석하여 매매 시그널을 생성합니다.

        Args:
            user_id: 사용자 ID (Rate Limiting용)

        Returns:
            {
                "action": "buy" | "sell" | "hold" | "close",
                "confidence": 0.0 ~ 1.0,
                "reason": str,
                "stop_loss": float | None,
                "take_profit": float | None,
            }
        """
        import json
        import re

        # 최근 20개 캔들 데이터 준비
        recent_candles = candles[-20:] if len(candles) >= 20 else candles

        # 기술적 지표 계산
        closes = [c.get("close", 0) for c in recent_candles]
        highs = [c.get("high", 0) for c in recent_candles]
        lows = [c.get("low", 0) for c in recent_candles]

        # RSI 계산 (간단 버전)
        rsi = self._calculate_rsi(closes)

        # 이동평균 계산
        ma_short = sum(closes[-9:]) / 9 if len(closes) >= 9 else closes[-1] if closes else 0
        ma_long = sum(closes[-21:]) / 21 if len(closes) >= 21 else closes[-1] if closes else 0

        # 볼린저 밴드 계산
        if len(closes) >= 20:
            ma_20 = sum(closes[-20:]) / 20
            std_dev = (sum((c - ma_20) ** 2 for c in closes[-20:]) / 20) ** 0.5
            bb_upper = ma_20 + 2 * std_dev
            bb_lower = ma_20 - 2 * std_dev
        else:
            bb_upper = bb_lower = current_price

        # 포지션 정보 문자열
        position_info = "포지션 없음"
        if current_position:
            pos_side = current_position.get("side", "unknown")
            pos_entry = current_position.get("entry_price", 0)
            pos_pnl = ((current_price - pos_entry) / pos_entry * 100) if pos_entry > 0 else 0
            if pos_side == "short":
                pos_pnl = -pos_pnl
            position_info = f"{pos_side.upper()} 포지션, 진입가: ${pos_entry:,.2f}, 현재 수익률: {pos_pnl:.2f}%"

        system_prompt = """You are an expert cryptocurrency trader AI. Analyze market data and provide trading signals.

IMPORTANT: You MUST respond with ONLY a valid JSON object. No explanations, no markdown, just pure JSON.

Response format (STRICT JSON):
{"action": "buy|sell|hold|close", "confidence": 0.0-1.0, "reason": "brief reason in Korean", "stop_loss": price_or_null, "take_profit": price_or_null}

Rules:
- action: "buy" for long entry, "sell" for short entry, "hold" for no action, "close" for exit position
- confidence: 0.0 (no confidence) to 1.0 (very confident)
- Only suggest "buy" or "sell" when confidence >= 0.6
- If position exists and losing > 2%, consider "close"
- If position exists and profit > 3%, consider "close" for take profit"""

        user_prompt = f"""Analyze {symbol} and provide trading signal:

Current Price: ${current_price:,.2f}
RSI (14): {rsi:.1f}
MA9: ${ma_short:,.2f}
MA21: ${ma_long:,.2f}
BB Upper: ${bb_upper:,.2f}
BB Lower: ${bb_lower:,.2f}
Recent High: ${max(highs) if highs else current_price:,.2f}
Recent Low: ${min(lows) if lows else current_price:,.2f}

Position: {position_info}

Respond with JSON only:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = self._make_request(
                messages,
                temperature=0.3,
                max_tokens=200,
                user_id=user_id  # Issue #4: Rate Limiting
            )

            if response:
                # JSON 추출
                json_match = re.search(r'\{[^{}]*\}', response)
                if json_match:
                    signal = json.loads(json_match.group())

                    # 유효성 검사
                    action = signal.get("action", "hold").lower()
                    if action not in ["buy", "sell", "hold", "close"]:
                        action = "hold"

                    confidence = float(signal.get("confidence", 0.5))
                    confidence = max(0.0, min(1.0, confidence))

                    return {
                        "action": action,
                        "confidence": confidence,
                        "reason": signal.get("reason", "AI 분석 완료"),
                        "stop_loss": signal.get("stop_loss"),
                        "take_profit": signal.get("take_profit"),
                        "ai_powered": True,
                    }

            # 실패 시 기본 hold
            return self._default_hold_signal("AI 응답 파싱 실패")

        except Exception as e:
            logger.warning(f"DeepSeek trading signal error: {str(e)}")
            return self._default_hold_signal(f"AI 오류: {str(e)}")

    def _calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """RSI 계산"""
        if len(closes) < period + 1:
            return 50.0

        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _default_hold_signal(self, reason: str = "대기") -> Dict[str, Any]:
        """기본 홀드 시그널"""
        return {
            "action": "hold",
            "confidence": 0.5,
            "reason": reason,
            "stop_loss": None,
            "take_profit": None,
            "ai_powered": True,
        }

    def analyze_market(self, symbol: str, timeframe: str, data: Dict[str, Any]) -> str:
        """시장 분석"""

        system_prompt = """You are an expert cryptocurrency market analyst.
Analyze the provided market data and give trading recommendations in Korean."""

        user_prompt = f"""Analyze this market data for {symbol} ({timeframe}):

Current Price: ${data.get("price", "N/A")}
24h Change: {data.get("change", "N/A")}%
24h Volume: {data.get("volume", "N/A")}
24h High: ${data.get("high", "N/A")}
24h Low: ${data.get("low", "N/A")}

Provide:
1. Market trend analysis
2. Support and resistance levels
3. Trading recommendation (Buy/Sell/Hold)
4. Risk assessment

Keep the response concise and in Korean."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            # analyze_market은 내부 분석용으로 rate limit 제외
            response = self._make_request(
                messages, temperature=0.7, max_tokens=1000, require_user_id=False
            )
            return response or "시장 분석을 수행할 수 없습니다."
        except Exception as e:
            return f"시장 분석 중 오류 발생: {str(e)}"


# 싱글톤 인스턴스
deepseek_service = DeepSeekAIService()
