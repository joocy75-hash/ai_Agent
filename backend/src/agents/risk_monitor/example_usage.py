"""
Risk Monitor Agent 사용 예제

실제 포지션 리스크 모니터링 예제
"""

import asyncio
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.agents.risk_monitor import RiskMonitorAgent, RiskAlert, RiskLevel, RiskAction
from src.agents.risk_monitor.models import PositionRisk
from src.agents.base import AgentTask, TaskPriority

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_position_risk_monitoring():
    """
    기본 포지션 리스크 모니터링 예제
    """
    print("\n" + "="*60)
    print("Example 1: Position Risk Monitoring")
    print("="*60 + "\n")

    # Risk Monitor Agent 생성
    agent = RiskMonitorAgent(
        agent_id="risk_monitor_1",
        name="Risk Monitor",
        config={
            "max_position_loss_percent": 5.0,  # 포지션 손실 5% 초과 시 청산
            "max_daily_loss": 1000.0,  # 일일 손실 $1000 초과 시 거래 중지
            "max_drawdown_percent": 10.0,  # 최대 낙폭 10%
            "liquidation_warning_percent": 10.0  # 청산가 10% 이내 접근 시 경고
        }
    )

    await agent.start()

    # 정상 포지션 (손실 3%, 안전)
    position_safe = {
        "symbol": "BTCUSDT",
        "side": "long",
        "size": 0.1,
        "entry_price": 50000.0,
        "current_price": 48500.0,  # -3% 손실
        "unrealized_pnl": -150.0,
        "unrealized_pnl_percent": -3.0,
        "leverage": 10,
        "liquidation_price": 45000.0,
        "distance_to_liquidation": 7.8  # 7.8% 거리
    }

    task = AgentTask(
        task_id="monitor_safe_position",
        task_type="monitor_position",
        priority=TaskPriority.NORMAL,
        params={
            "position": position_safe,
            "bitget_client": None,
            "auto_execute": False
        }
    )

    await agent.submit_task(task)
    await asyncio.sleep(0.2)

    alerts = task.result
    print("\n" + "-"*60)
    print("Safe Position Monitoring:")
    print(f"  Position: {position_safe['symbol']} {position_safe['side']}")
    print(f"  Unrealized PnL: {position_safe['unrealized_pnl_percent']:.2f}%")
    print(f"  Distance to Liquidation: {position_safe['distance_to_liquidation']:.2f}%")
    if alerts:
        print(f"  Alerts: {len(alerts)}")
        for alert in alerts:
            print(f"    - {alert.message}")
    else:
        print("  Status: ✅ No risk detected")
    print("-"*60 + "\n")

    await agent.stop()


async def example_high_loss_position():
    """
    높은 손실 포지션 감지 예제 (5% 초과 → 청산 권장)
    """
    print("\n" + "="*60)
    print("Example 2: High Loss Position Detection")
    print("="*60 + "\n")

    agent = RiskMonitorAgent(
        agent_id="risk_monitor_2",
        name="Risk Monitor",
        config={"max_position_loss_percent": 5.0}
    )

    await agent.start()

    # 높은 손실 포지션 (-6%, 임계값 초과)
    position_high_loss = {
        "symbol": "ETHUSDT",
        "side": "short",
        "size": 2.0,
        "entry_price": 3000.0,
        "current_price": 3180.0,  # +6% (short이므로 손실)
        "unrealized_pnl": -360.0,
        "unrealized_pnl_percent": -6.0,
        "leverage": 10,
        "liquidation_price": 3300.0,
        "distance_to_liquidation": 3.9
    }

    task = AgentTask(
        task_id="monitor_high_loss",
        task_type="monitor_position",
        priority=TaskPriority.HIGH,
        params={
            "position": position_high_loss,
            "bitget_client": None,
            "auto_execute": False
        }
    )

    await agent.submit_task(task)
    await asyncio.sleep(0.2)

    alerts = task.result
    print("\n" + "-"*60)
    print("High Loss Position Detected:")
    if alerts:
        for alert in alerts:
            print(f"  🚨 Alert ID: {alert.alert_id}")
            print(f"  Type: {alert.alert_type}")
            print(f"  Risk Level: {alert.risk_level.value.upper()}")
            print(f"  Message: {alert.message}")
            print(f"  Current Value: {alert.current_value:.2f}%")
            print(f"  Threshold: {alert.threshold_value:.2f}%")
            print(f"  Recommended Action: {alert.recommended_action.value}")
            print()
    print("-"*60 + "\n")

    await agent.stop()


async def example_liquidation_warning():
    """
    청산가 근접 감지 예제 (10% 이내)
    """
    print("\n" + "="*60)
    print("Example 3: Liquidation Warning")
    print("="*60 + "\n")

    agent = RiskMonitorAgent(
        agent_id="risk_monitor_3",
        name="Risk Monitor",
        config={"liquidation_warning_percent": 10.0}
    )

    await agent.start()

    # 청산가 근접 포지션 (5% 거리)
    position_near_liq = {
        "symbol": "BTCUSDT",
        "side": "long",
        "size": 0.2,
        "entry_price": 50000.0,
        "current_price": 47500.0,  # -5% 손실
        "unrealized_pnl": -500.0,
        "unrealized_pnl_percent": -5.0,
        "leverage": 20,  # 높은 레버리지
        "liquidation_price": 47200.0,
        "distance_to_liquidation": 0.6  # 청산가까지 0.6% (매우 위험!)
    }

    task = AgentTask(
        task_id="monitor_liq_warning",
        task_type="monitor_position",
        priority=TaskPriority.CRITICAL,
        params={
            "position": position_near_liq,
            "bitget_client": None,
            "auto_execute": False
        }
    )

    await agent.submit_task(task)
    await asyncio.sleep(0.2)

    alerts = task.result
    print("\n" + "-"*60)
    print("⚠️ LIQUIDATION WARNING ⚠️")
    print(f"  Position: {position_near_liq['symbol']} @ {position_near_liq['current_price']}")
    print(f"  Liquidation Price: ${position_near_liq['liquidation_price']}")
    print(f"  Distance: {position_near_liq['distance_to_liquidation']:.2f}%")
    if alerts:
        for alert in alerts:
            if alert.alert_type == "liquidation_risk":
                print(f"\n  🔴 {alert.message}")
                print(f"  Risk Level: {alert.risk_level.value.upper()}")
                print(f"  Action: {alert.recommended_action.value}")
    print("-"*60 + "\n")

    await agent.stop()


async def example_daily_loss_and_drawdown():
    """
    일일 손실 한도 및 최대 낙폭 체크 예제
    """
    print("\n" + "="*60)
    print("Example 4: Daily Loss & Drawdown Check")
    print("="*60 + "\n")

    agent = RiskMonitorAgent(
        agent_id="risk_monitor_4",
        name="Risk Monitor",
        config={
            "max_daily_loss": 500.0,  # 일일 손실 $500 한도
            "max_drawdown_percent": 8.0  # 최대 낙폭 8%
        }
    )

    await agent.start()

    # 테스트 케이스들
    test_cases = [
        {
            "name": "Normal Daily Loss",
            "task_type": "check_daily_loss",
            "params": {
                "today_pnl": -300.0,  # -$300 (정상)
                "user_id": 1,
                "auto_execute": False
            }
        },
        {
            "name": "Exceeded Daily Loss Limit",
            "task_type": "check_daily_loss",
            "params": {
                "today_pnl": -650.0,  # -$650 (한도 초과!)
                "user_id": 1,
                "auto_execute": False
            }
        },
        {
            "name": "Normal Drawdown",
            "task_type": "check_drawdown",
            "params": {
                "current_drawdown": 5.5,  # 5.5% (정상)
                "user_id": 1,
                "auto_execute": False
            }
        },
        {
            "name": "Exceeded Max Drawdown",
            "task_type": "check_drawdown",
            "params": {
                "current_drawdown": 9.2,  # 9.2% (한도 초과!)
                "user_id": 1,
                "auto_execute": False
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n📌 Test: {test_case['name']}")

        task = AgentTask(
            task_id=f"test_{test_case['name'].lower().replace(' ', '_')}",
            task_type=test_case['task_type'],
            priority=TaskPriority.HIGH,
            params=test_case['params']
        )

        await agent.submit_task(task)
        await asyncio.sleep(0.2)

        alert = task.result
        if alert:
            emoji = "🔴" if alert.is_critical() else "⚠️"
            print(f"{emoji} Alert Triggered:")
            print(f"   Type: {alert.alert_type}")
            print(f"   Message: {alert.message}")
            print(f"   Current: {alert.current_value:.2f}")
            print(f"   Threshold: {alert.threshold_value:.2f}")
            print(f"   Action: {alert.recommended_action.value}")
        else:
            print("✅ No alert (within limits)")

    print()
    await agent.stop()


async def example_auto_execute_actions():
    """
    자동 조치 실행 예제 (시뮬레이션)
    """
    print("\n" + "="*60)
    print("Example 5: Auto-Execute Risk Actions (Simulation)")
    print("="*60 + "\n")

    agent = RiskMonitorAgent(
        agent_id="risk_monitor_5",
        name="Risk Monitor (Auto)",
        config={
            "max_position_loss_percent": 5.0,
            "liquidation_warning_percent": 10.0
        }
    )

    await agent.start()

    # 위험 포지션 (auto_execute=True)
    position_risky = {
        "symbol": "SOLUSDT",
        "side": "long",
        "size": 10.0,
        "entry_price": 100.0,
        "current_price": 94.0,  # -6% 손실
        "unrealized_pnl": -60.0,
        "unrealized_pnl_percent": -6.0,
        "leverage": 10,
        "liquidation_price": 90.0,
        "distance_to_liquidation": 4.4
    }

    task = AgentTask(
        task_id="auto_execute_test",
        task_type="monitor_position",
        priority=TaskPriority.CRITICAL,
        params={
            "position": position_risky,
            "bitget_client": None,  # 실제로는 Bitget API 클라이언트 필요
            "auto_execute": True  # 자동 실행 활성화
        }
    )

    await agent.submit_task(task)
    await asyncio.sleep(0.3)

    alerts = task.result
    print("\n" + "-"*60)
    print("Auto-Execute Simulation:")
    print(f"  Position: {position_risky['symbol']} (Loss: {position_risky['unrealized_pnl_percent']:.2f}%)")
    if alerts:
        for alert in alerts:
            print(f"\n  Alert: {alert.alert_type}")
            print(f"  Auto-Execute: {alert.auto_execute}")
            print(f"  Action: {alert.recommended_action.value}")
            if alert.auto_execute:
                print(f"  ⚡ Action would be executed automatically in production")
                print(f"     (Currently in simulation mode - no actual orders)")
    print("-"*60 + "\n")

    # 활성 알림 확인
    active_alerts = agent.get_active_alerts()
    print(f"Active Alerts: {len(active_alerts)}")
    for i, alert in enumerate(active_alerts, 1):
        print(f"  {i}. [{alert.risk_level.value}] {alert.alert_type}: {alert.message}")

    await agent.stop()


async def example_multiple_positions():
    """
    여러 포지션 동시 모니터링 예제
    """
    print("\n" + "="*60)
    print("Example 6: Multiple Positions Monitoring")
    print("="*60 + "\n")

    agent = RiskMonitorAgent(
        agent_id="risk_monitor_6",
        name="Multi-Position Monitor",
        config={
            "max_position_loss_percent": 5.0,
            "liquidation_warning_percent": 10.0
        }
    )

    await agent.start()

    # 여러 포지션
    positions = [
        {
            "symbol": "BTCUSDT",
            "side": "long",
            "size": 0.1,
            "entry_price": 50000.0,
            "current_price": 51000.0,  # +2% 수익
            "unrealized_pnl": 100.0,
            "unrealized_pnl_percent": 2.0,
            "leverage": 10,
            "liquidation_price": 45000.0,
            "distance_to_liquidation": 11.8
        },
        {
            "symbol": "ETHUSDT",
            "side": "short",
            "size": 2.0,
            "entry_price": 3000.0,
            "current_price": 2900.0,  # +3.3% 수익 (short)
            "unrealized_pnl": 200.0,
            "unrealized_pnl_percent": 3.3,
            "leverage": 10,
            "liquidation_price": 3300.0,
            "distance_to_liquidation": 13.8
        },
        {
            "symbol": "SOLUSDT",
            "side": "long",
            "size": 10.0,
            "entry_price": 100.0,
            "current_price": 93.5,  # -6.5% 손실 (위험!)
            "unrealized_pnl": -65.0,
            "unrealized_pnl_percent": -6.5,
            "leverage": 15,
            "liquidation_price": 93.0,
            "distance_to_liquidation": 0.5  # 매우 위험!
        }
    ]

    total_alerts = 0
    for position in positions:
        task = AgentTask(
            task_id=f"monitor_{position['symbol']}",
            task_type="monitor_position",
            priority=TaskPriority.HIGH,
            params={
                "position": position,
                "bitget_client": None,
                "auto_execute": False
            }
        )

        await agent.submit_task(task)
        await asyncio.sleep(0.1)

        alerts = task.result

        status_emoji = "✅" if not alerts else ("🔴" if any(a.is_critical() for a in alerts) else "⚠️")
        print(f"{status_emoji} {position['symbol']} {position['side']}: {position['unrealized_pnl_percent']:+.2f}%")

        if alerts:
            total_alerts += len(alerts)
            for alert in alerts:
                print(f"   └─ {alert.alert_type}: {alert.message}")

    print(f"\nTotal Alerts: {total_alerts}")

    await agent.stop()


async def main():
    """메인 함수"""
    try:
        # 예제 1: 정상 포지션 모니터링
        await example_position_risk_monitoring()

        # 예제 2: 높은 손실 포지션
        await example_high_loss_position()

        # 예제 3: 청산가 근접 경고
        await example_liquidation_warning()

        # 예제 4: 일일 손실 & 낙폭 체크
        await example_daily_loss_and_drawdown()

        # 예제 5: 자동 조치 실행
        await example_auto_execute_actions()

        # 예제 6: 다중 포지션 모니터링
        await example_multiple_positions()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Risk Monitor Agent Examples")
    print("="*60)
    asyncio.run(main())
    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60 + "\n")
