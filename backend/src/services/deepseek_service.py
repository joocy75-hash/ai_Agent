"""
DeepSeek AI 서비스
전략 생성, 시장 분석 등에 AI를 활용합니다.
"""

import os
import requests
from typing import Dict, List, Any, Optional
from src.config import settings


class DeepSeekAIService:
    """DeepSeek AI 서비스 클래스"""

    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"

    def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Optional[str]:
        """DeepSeek API 요청"""
        if not self.api_key:
            raise ValueError("DeepSeek API key is not configured")

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
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]

            return None

        except Exception as e:
            print(f"DeepSeek API error: {str(e)}")
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
            response = self._make_request(messages, temperature=0.8, max_tokens=2000)

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
            print(f"Error generating strategies with AI: {str(e)}")
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
            response = self._make_request(messages, temperature=0.7, max_tokens=1000)
            return response or "시장 분석을 수행할 수 없습니다."
        except Exception as e:
            return f"시장 분석 중 오류 발생: {str(e)}"


# 싱글톤 인스턴스
deepseek_service = DeepSeekAIService()
