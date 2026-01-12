"""
Signal Validator Agent 사용 예제

실제 시그널 검증 예제
"""

import asyncio
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.base import AgentTask, TaskPriority
from src.agents.signal_validator import SignalValidatorAgent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_basic_validation():
    """
    기본 시그널 검증 예제
    """
    print("\n" + "="*60)
    print("Example 1: Basic Signal Validation")
    print("="*60 + "\n")

    # Signal Validator Agent 생성
    agent = SignalValidatorAgent(
        agent_id="validator_1",
        name="Signal Validator",
        redis_client=None  # Redis 없이 테스트
    )

    await agent.start()

    # 시그널 검증 작업 생성 (정상 신호)
    task = AgentTask(
        task_id="validate_btc_buy_1",
        task_type="validate_signal",
        priority=TaskPriority.HIGH,
        params={
            "signal_id": "sig_001",
            "symbol": "BTCUSDT",
            "action": "buy",
            "confidence": 0.85,  # 높은 신뢰도
            "current_price": 50000.0,
            "price_change_5min": 0.5,  # 0.5% 변동
            "current_position_side": None,  # 포지션 없음
            "recent_signals": [],
            "order_size_usd": 1000.0,
            "available_balance": 5000.0,
            "support_level": 49000.0,
            "resistance_level": 51000.0,
            "recent_trades_count": 2,
            "current_drawdown": 1.5,
        },
        timeout=1.0
    )

    await agent.submit_task(task)
    await asyncio.sleep(0.2)

    # 결과 확인
    validation = task.result
    if validation:
        print("\n" + "-"*60)
        print("Validation Result:")
        print(f"  Signal: {validation.symbol} {validation.action}")
        print(f"  Result: {validation.validation_result.value}")
        print(f"  Confidence Score: {validation.confidence_score:.2f}")
        print(f"  Passed Rules: {len(validation.passed_rules)}")
        print(f"  Failed Rules: {len(validation.failed_rules)}")
        if validation.warnings:
            print("  Warnings:")
            for warning in validation.warnings:
                print(f"    - {warning}")
        print("-"*60 + "\n")

    await agent.stop()


async def example_low_confidence_signal():
    """
    낮은 신뢰도 시그널 검증 (포지션 50% 축소)
    """
    print("\n" + "="*60)
    print("Example 2: Low Confidence Signal (Position Reduction)")
    print("="*60 + "\n")

    agent = SignalValidatorAgent(
        agent_id="validator_2",
        name="Signal Validator",
        redis_client=None
    )

    await agent.start()

    # 낮은 신뢰도 신호 (0.65 → 포지션 50% 축소)
    task = AgentTask(
        task_id="validate_eth_buy_2",
        task_type="validate_signal",
        priority=TaskPriority.HIGH,
        params={
            "signal_id": "sig_002",
            "symbol": "ETHUSDT",
            "action": "buy",
            "confidence": 0.65,  # 낮은 신뢰도 (< 0.7)
            "current_price": 3000.0,
            "price_change_5min": 0.3,
            "current_position_side": None,
            "recent_signals": [],
            "order_size_usd": 500.0,
            "available_balance": 2000.0,
            "support_level": 2950.0,
            "resistance_level": 3050.0,
            "recent_trades_count": 1,
            "current_drawdown": 0.5,
        },
        timeout=1.0
    )

    await agent.submit_task(task)
    await asyncio.sleep(0.2)

    validation = task.result
    if validation:
        print("\n" + "-"*60)
        print("Validation Result:")
        print(f"  Signal: {validation.symbol} {validation.action}")
        print(f"  Result: {validation.validation_result.value}")
        print(f"  Position Adjustment: {validation.metadata.get('position_adjustment', 1.0)*100:.0f}%")
        print(f"  Original Order: ${validation.metadata.get('original_order_size', 0):.2f}")
        print(f"  Adjusted Order: ${validation.metadata.get('order_size_adjustment', 0):.2f}")
        if validation.warnings:
            print("  Warnings:")
            for warning in validation.warnings:
                print(f"    - {warning}")
        print("-"*60 + "\n")

    await agent.stop()


async def example_rejected_signal():
    """
    거부된 시그널 예제
    """
    print("\n" + "="*60)
    print("Example 3: Rejected Signals")
    print("="*60 + "\n")

    agent = SignalValidatorAgent(
        agent_id="validator_3",
        name="Signal Validator",
        redis_client=None
    )

    await agent.start()

    # 테스트 케이스들
    test_cases = [
        {
            "name": "Very Low Confidence (< 0.6)",
            "params": {
                "signal_id": "sig_003",
                "symbol": "BTCUSDT",
                "action": "buy",
                "confidence": 0.55,  # < 0.6 → 거부
                "current_price": 50000.0,
                "price_change_5min": 0.5,
                "current_position_side": None,
                "recent_signals": [],
                "order_size_usd": 1000.0,
                "available_balance": 5000.0,
            }
        },
        {
            "name": "Sudden Price Change (> 2%)",
            "params": {
                "signal_id": "sig_004",
                "symbol": "BTCUSDT",
                "action": "buy",
                "confidence": 0.8,
                "current_price": 50000.0,
                "price_change_5min": 3.5,  # 3.5% 급등 → 거부
                "current_position_side": None,
                "recent_signals": [],
                "order_size_usd": 1000.0,
                "available_balance": 5000.0,
            }
        },
        {
            "name": "Too Many Consecutive Signals",
            "params": {
                "signal_id": "sig_005",
                "symbol": "BTCUSDT",
                "action": "buy",
                "confidence": 0.8,
                "current_price": 50000.0,
                "price_change_5min": 0.5,
                "current_position_side": None,
                "recent_signals": ["buy", "buy", "buy"],  # 3회 연속 buy → 4번째 거부
                "order_size_usd": 1000.0,
                "available_balance": 5000.0,
            }
        },
        {
            "name": "Position Reversal (Low Confidence)",
            "params": {
                "signal_id": "sig_006",
                "symbol": "BTCUSDT",
                "action": "buy",
                "confidence": 0.75,  # < 0.8 → 포지션 반전 시 거부
                "current_price": 50000.0,
                "price_change_5min": 0.5,
                "current_position_side": "short",  # 현재 short → buy는 반전
                "recent_signals": [],
                "order_size_usd": 1000.0,
                "available_balance": 5000.0,
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n📌 Test: {test_case['name']}")

        # 기본 파라미터 추가
        params = {
            "support_level": None,
            "resistance_level": None,
            "recent_trades_count": 0,
            "current_drawdown": 0.0,
        }
        params.update(test_case['params'])

        task = AgentTask(
            task_id=test_case['params']['signal_id'],
            task_type="validate_signal",
            priority=TaskPriority.HIGH,
            params=params,
            timeout=1.0
        )

        await agent.submit_task(task)
        await asyncio.sleep(0.2)

        validation = task.result
        if validation:
            result_emoji = "✅" if validation.is_approved() else "🚫"
            print(f"{result_emoji} Result: {validation.validation_result.value}")
            if validation.failed_rules:
                print(f"   Failed Rules: {', '.join(validation.failed_rules)}")
            if validation.warnings:
                print(f"   Warning: {validation.warnings[0]}")

    await agent.stop()


async def example_order_size_adjustment():
    """
    주문 크기 조정 예제
    """
    print("\n" + "="*60)
    print("Example 4: Order Size Adjustment")
    print("="*60 + "\n")

    agent = SignalValidatorAgent(
        agent_id="validator_4",
        name="Signal Validator",
        redis_client=None
    )

    await agent.start()

    # 주문 크기가 잔고의 30%를 초과하는 경우
    task = AgentTask(
        task_id="validate_btc_buy_3",
        task_type="validate_signal",
        priority=TaskPriority.HIGH,
        params={
            "signal_id": "sig_007",
            "symbol": "BTCUSDT",
            "action": "buy",
            "confidence": 0.8,
            "current_price": 50000.0,
            "price_change_5min": 0.5,
            "current_position_side": None,
            "recent_signals": [],
            "order_size_usd": 2000.0,  # 잔고의 50%
            "available_balance": 4000.0,  # 30% = $1200
            "support_level": None,
            "resistance_level": None,
            "recent_trades_count": 0,
            "current_drawdown": 0.0,
        },
        timeout=1.0
    )

    await agent.submit_task(task)
    await asyncio.sleep(0.2)

    validation = task.result
    if validation:
        print("\n" + "-"*60)
        print("Order Size Adjustment:")
        print(f"  Original Order: ${validation.metadata.get('original_order_size', 0):.2f}")
        print("  Available Balance: $4000.00")
        print("  Max Allowed (30%): $1200.00")
        print(f"  Adjusted Order: ${validation.metadata.get('order_size_adjustment', 0):.2f}")
        print(f"  Result: {validation.validation_result.value}")
        print("-"*60 + "\n")

    await agent.stop()


async def main():
    """메인 함수"""
    try:
        # 예제 1: 기본 검증
        await example_basic_validation()

        # 예제 2: 낮은 신뢰도 (포지션 축소)
        await example_low_confidence_signal()

        # 예제 3: 거부된 시그널들
        await example_rejected_signal()

        # 예제 4: 주문 크기 조정
        await example_order_size_adjustment()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Signal Validator Agent Examples")
    print("="*60)
    asyncio.run(main())
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")
