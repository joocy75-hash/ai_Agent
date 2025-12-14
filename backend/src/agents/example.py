"""
에이전트 시스템 사용 예제 (Agent System Example)

기본적인 에이전트 구현 및 사용법 예제
"""

import asyncio
import logging
from typing import Any

from .base import BaseAgent, AgentTask, TaskPriority

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarketAnalyzerAgent(BaseAgent):
    """
    시장 분석 에이전트 예제

    시장 데이터를 분석하여 인사이트를 생성하는 에이전트
    """

    async def process_task(self, task: AgentTask) -> Any:
        """
        시장 분석 작업 처리

        Args:
            task: 분석 작업

        Returns:
            분석 결과
        """
        task_type = task.task_type
        params = task.params

        logger.info(f"Processing {task_type} task with params: {params}")

        # 작업 타입별 처리
        if task_type == "analyze_price":
            return await self._analyze_price(params)

        elif task_type == "analyze_volume":
            return await self._analyze_volume(params)

        elif task_type == "analyze_trend":
            return await self._analyze_trend(params)

        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _analyze_price(self, params: dict) -> dict:
        """가격 분석"""
        symbol = params.get("symbol", "BTCUSDT")
        price = params.get("price", 50000)

        # 간단한 가격 분석 로직 (실제로는 더 복잡한 분석)
        await asyncio.sleep(0.5)  # 분석 시뮬레이션

        return {
            "symbol": symbol,
            "current_price": price,
            "analysis": "Price is trending upward",
            "signal": "buy" if price < 45000 else "hold",
            "confidence": 0.75,
        }

    async def _analyze_volume(self, params: dict) -> dict:
        """거래량 분석"""
        symbol = params.get("symbol", "BTCUSDT")
        volume = params.get("volume", 1000000)

        await asyncio.sleep(0.3)

        return {
            "symbol": symbol,
            "volume": volume,
            "volume_trend": "increasing",
            "volume_strength": "strong" if volume > 500000 else "weak",
        }

    async def _analyze_trend(self, params: dict) -> dict:
        """트렌드 분석"""
        symbol = params.get("symbol", "BTCUSDT")
        timeframe = params.get("timeframe", "1h")

        await asyncio.sleep(0.7)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "trend": "bullish",
            "strength": 0.82,
        }


class SignalGeneratorAgent(BaseAgent):
    """
    시그널 생성 에이전트 예제

    시장 분석 결과를 기반으로 트레이딩 시그널을 생성
    """

    async def process_task(self, task: AgentTask) -> Any:
        """
        시그널 생성 작업 처리

        Args:
            task: 시그널 생성 작업

        Returns:
            생성된 시그널
        """
        params = task.params
        market_data = params.get("market_data", {})

        logger.info(f"Generating signal from market data: {market_data}")

        # 시그널 생성 로직 (간단한 예제)
        await asyncio.sleep(0.5)

        price = market_data.get("price", 50000)
        volume = market_data.get("volume", 1000000)

        # 간단한 시그널 로직
        if price < 45000 and volume > 800000:
            signal = "strong_buy"
            confidence = 0.9
        elif price > 55000:
            signal = "sell"
            confidence = 0.75
        else:
            signal = "hold"
            confidence = 0.6

        return {
            "signal": signal,
            "confidence": confidence,
            "reason": f"Price: {price}, Volume: {volume}",
            "timestamp": asyncio.get_event_loop().time(),
        }


async def example_single_agent():
    """
    단일 에이전트 사용 예제
    """
    print("\n" + "="*60)
    print("Example 1: Single Agent Usage")
    print("="*60 + "\n")

    # 에이전트 생성
    agent = MarketAnalyzerAgent(
        agent_id="market_analyzer_1",
        name="Market Analyzer",
        config={"interval": 60}
    )

    # 에이전트 시작
    await agent.start()

    # 작업 제출
    tasks = [
        AgentTask(
            task_id="task_1",
            task_type="analyze_price",
            priority=TaskPriority.HIGH,
            params={"symbol": "BTCUSDT", "price": 42000}
        ),
        AgentTask(
            task_id="task_2",
            task_type="analyze_volume",
            priority=TaskPriority.NORMAL,
            params={"symbol": "BTCUSDT", "volume": 1500000}
        ),
        AgentTask(
            task_id="task_3",
            task_type="analyze_trend",
            priority=TaskPriority.LOW,
            params={"symbol": "BTCUSDT", "timeframe": "1h"}
        ),
    ]

    for task in tasks:
        await agent.submit_task(task)
        logger.info(f"Submitted task: {task.task_id}")

    # 작업 처리 대기
    await asyncio.sleep(5)

    # 상태 확인
    status = agent.get_status()
    print("\n" + "-"*60)
    print("Agent Status:")
    print(f"  State: {status['state']}")
    print(f"  Queue Size: {status['queue_size']}")
    print(f"  Metrics:")
    print(f"    Total Tasks: {status['metrics']['total_tasks']}")
    print(f"    Completed: {status['metrics']['completed_tasks']}")
    print(f"    Failed: {status['metrics']['failed_tasks']}")
    print(f"    Success Rate: {status['metrics']['success_rate']}%")
    print(f"    Avg Duration: {status['metrics']['avg_task_duration']:.2f}s")
    print("-"*60 + "\n")

    # 에이전트 중지
    await agent.stop()


async def example_multiple_agents():
    """
    다중 에이전트 협업 예제
    """
    print("\n" + "="*60)
    print("Example 2: Multiple Agents Collaboration")
    print("="*60 + "\n")

    # 에이전트들 생성
    analyzer = MarketAnalyzerAgent(
        agent_id="analyzer_1",
        name="Market Analyzer"
    )
    signal_gen = SignalGeneratorAgent(
        agent_id="signal_gen_1",
        name="Signal Generator"
    )

    # 에이전트들 시작
    await analyzer.start()
    await signal_gen.start()

    # 1단계: 시장 분석
    analyze_task = AgentTask(
        task_id="analyze_1",
        task_type="analyze_price",
        priority=TaskPriority.HIGH,
        params={"symbol": "BTCUSDT", "price": 42000}
    )
    await analyzer.submit_task(analyze_task)

    # 분석 완료 대기
    await asyncio.sleep(2)

    # 2단계: 시그널 생성 (분석 결과 사용)
    signal_task = AgentTask(
        task_id="signal_1",
        task_type="generate_signal",
        priority=TaskPriority.CRITICAL,
        params={
            "market_data": {
                "price": 42000,
                "volume": 1500000
            }
        }
    )
    await signal_gen.submit_task(signal_task)

    # 시그널 생성 대기
    await asyncio.sleep(2)

    # 상태 확인
    print("\n" + "-"*60)
    print("Analyzer Status:")
    print(f"  Completed Tasks: {analyzer.get_status()['metrics']['completed_tasks']}")
    print("\nSignal Generator Status:")
    print(f"  Completed Tasks: {signal_gen.get_status()['metrics']['completed_tasks']}")
    print("-"*60 + "\n")

    # 에이전트들 중지
    await analyzer.stop()
    await signal_gen.stop()


async def main():
    """메인 함수"""
    try:
        # 예제 1: 단일 에이전트
        await example_single_agent()

        # 예제 2: 다중 에이전트 협업
        await example_multiple_agents()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Agent System Examples")
    print("="*60)
    asyncio.run(main())
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")
