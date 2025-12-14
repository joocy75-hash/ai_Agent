"""
Market Regime Agent 사용 예제

실제 Bitget API와 Redis를 사용하는 예제
"""

import asyncio
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.market_regime import MarketRegimeAgent, RegimeType
from src.agents.base import AgentTask, TaskPriority
from src.services.bitget_rest import get_bitget_rest
from src.services.candle_cache import CandleCacheManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_basic_usage():
    """
    기본 사용 예제 (Bitget API 연동)
    """
    print("\n" + "="*60)
    print("Example 1: Basic Market Regime Analysis")
    print("="*60 + "\n")

    # Bitget API 클라이언트 생성 (공개 데이터는 인증 불필요)
    bitget_client = get_bitget_rest()

    # Market Regime Agent 생성
    agent = MarketRegimeAgent(
        agent_id="market_regime_1",
        name="Market Regime Analyzer",
        config={
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "candle_limit": 200
        },
        bitget_client=bitget_client,
        candle_cache=None,  # 캐시 없이 직접 API 사용
        redis_client=None   # Redis 없이 메모리만 사용
    )

    # 에이전트 시작
    await agent.start()

    # 시장 분석 작업 제출
    task = AgentTask(
        task_id="analyze_btc_1",
        task_type="analyze_market",
        priority=TaskPriority.HIGH,
        params={
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "force_refresh": False
        },
        timeout=5.0
    )

    await agent.submit_task(task)

    # 작업 처리 대기
    await asyncio.sleep(3)

    # 결과 확인
    regime = agent.get_current_regime()
    if regime:
        print("\n" + "-"*60)
        print("Market Regime Analysis Result:")
        print(f"  Symbol: {regime.symbol}")
        print(f"  Regime Type: {regime.regime_type.value}")
        print(f"  Confidence: {regime.confidence:.2%}")
        print(f"  Volatility: {regime.volatility:.2f}%")
        print(f"  Trend Strength (ADX): {regime.trend_strength:.2f}")
        if regime.support_level:
            print(f"  Support Level: ${regime.support_level:,.2f}")
        if regime.resistance_level:
            print(f"  Resistance Level: ${regime.resistance_level:,.2f}")
        print(f"  Timestamp: {regime.timestamp}")
        print("-"*60 + "\n")

    # 에이전트 중지
    await agent.stop()
    await bitget_client.close()


async def example_with_cache():
    """
    Candle Cache 사용 예제 (성능 최적화)
    """
    print("\n" + "="*60)
    print("Example 2: Market Regime Analysis with Cache")
    print("="*60 + "\n")

    # Bitget API 클라이언트
    bitget_client = get_bitget_rest()

    # Candle Cache 매니저 생성
    candle_cache = CandleCacheManager()

    # Market Regime Agent 생성
    agent = MarketRegimeAgent(
        agent_id="market_regime_2",
        name="Cached Market Analyzer",
        config={
            "symbol": "ETHUSDT",
            "timeframe": "15m",
            "candle_limit": 200
        },
        bitget_client=bitget_client,
        candle_cache=candle_cache,  # 캐시 사용
        redis_client=None
    )

    await agent.start()

    # 여러 심볼 분석
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    for symbol in symbols:
        task = AgentTask(
            task_id=f"analyze_{symbol}",
            task_type="analyze_market",
            priority=TaskPriority.NORMAL,
            params={
                "symbol": symbol,
                "timeframe": "15m"
            },
            timeout=5.0
        )
        await agent.submit_task(task)

    # 작업 처리 대기
    await asyncio.sleep(10)

    # 상태 확인
    status = agent.get_status()
    print("\n" + "-"*60)
    print("Agent Status:")
    print(f"  State: {status['state']}")
    print(f"  Total Tasks: {status['metrics']['total_tasks']}")
    print(f"  Completed: {status['metrics']['completed_tasks']}")
    print(f"  Failed: {status['metrics']['failed_tasks']}")
    print(f"  Success Rate: {status['metrics']['success_rate']:.2f}%")
    print(f"  Avg Duration: {status['metrics']['avg_task_duration']:.2f}s")
    print("-"*60 + "\n")

    await agent.stop()
    await bitget_client.close()


async def example_periodic_analysis():
    """
    주기적 분석 예제 (1분마다 자동 실행)
    """
    print("\n" + "="*60)
    print("Example 3: Periodic Market Regime Analysis")
    print("="*60 + "\n")

    bitget_client = get_bitget_rest()

    agent = MarketRegimeAgent(
        agent_id="market_regime_3",
        name="Periodic Analyzer",
        config={
            "symbol": "BTCUSDT",
            "timeframe": "5m",
            "candle_limit": 200
        },
        bitget_client=bitget_client
    )

    await agent.start()

    print("Starting periodic analysis (10초마다, 총 30초)")
    print("Press Ctrl+C to stop...")

    # 주기적 분석 백그라운드 태스크 시작 (테스트용 10초 간격)
    periodic_task = asyncio.create_task(
        agent.run_periodic_analysis(interval_seconds=10)
    )

    try:
        # 30초 동안 실행
        await asyncio.sleep(30)

        # 마지막 결과 확인
        regime = agent.get_current_regime()
        if regime:
            print("\n" + "-"*60)
            print("Latest Market Regime:")
            print(f"  {regime.symbol}: {regime.regime_type.value}")
            print(f"  Confidence: {regime.confidence:.2%}")
            print(f"  Volatility: {regime.volatility:.2f}%")
            print("-"*60 + "\n")

    except KeyboardInterrupt:
        print("\nStopping periodic analysis...")

    finally:
        # 정리
        periodic_task.cancel()
        try:
            await periodic_task
        except asyncio.CancelledError:
            pass

        await agent.stop()
        await bitget_client.close()


async def example_regime_types():
    """
    다양한 시장 환경 감지 예제
    """
    print("\n" + "="*60)
    print("Example 4: Detecting Different Market Regimes")
    print("="*60 + "\n")

    bitget_client = get_bitget_rest()

    # 여러 심볼과 타임프레임 조합
    configs = [
        {"symbol": "BTCUSDT", "timeframe": "1h", "desc": "BTC 1시간봉"},
        {"symbol": "ETHUSDT", "timeframe": "15m", "desc": "ETH 15분봉"},
        {"symbol": "SOLUSDT", "timeframe": "4h", "desc": "SOL 4시간봉"},
    ]

    results = []

    for config in configs:
        agent = MarketRegimeAgent(
            agent_id=f"analyzer_{config['symbol']}",
            name=f"Analyzer {config['symbol']}",
            config=config,
            bitget_client=bitget_client
        )

        await agent.start()

        task = AgentTask(
            task_id=f"analyze_{config['symbol']}_{config['timeframe']}",
            task_type="analyze_market",
            params=config,
            timeout=5.0
        )

        await agent.submit_task(task)
        await asyncio.sleep(2)

        regime = agent.get_current_regime()
        if regime:
            results.append((config['desc'], regime))

        await agent.stop()

    # 결과 출력
    print("\n" + "-"*60)
    print("Market Regime Comparison:")
    print("-"*60)

    for desc, regime in results:
        emoji = {
            RegimeType.TRENDING_UP: "📈",
            RegimeType.TRENDING_DOWN: "📉",
            RegimeType.RANGING: "↔️",
            RegimeType.VOLATILE: "🌊",
            RegimeType.LOW_VOLUME: "💤",
        }.get(regime.regime_type, "❓")

        print(f"\n{emoji} {desc}")
        print(f"  Type: {regime.regime_type.value}")
        print(f"  Confidence: {regime.confidence:.2%}")
        print(f"  Volatility: {regime.volatility:.2f}%")
        print(f"  ADX: {regime.trend_strength:.2f}")

    print("\n" + "-"*60 + "\n")

    await bitget_client.close()


async def main():
    """메인 함수"""
    try:
        # 예제 1: 기본 사용법
        await example_basic_usage()

        # 예제 2: 캐시 사용
        # await example_with_cache()

        # 예제 3: 주기적 분석
        # await example_periodic_analysis()

        # 예제 4: 다양한 시장 환경 감지
        # await example_regime_types()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Market Regime Agent Examples")
    print("="*60)
    asyncio.run(main())
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")
