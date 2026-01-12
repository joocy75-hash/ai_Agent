"""
Risk Monitor Agent (리스크 모니터링 에이전트)

실시간 리스크 모니터링 및 자동 조치 실행
"""

import logging
import uuid
from typing import Any, List, Optional

from ..base import AgentTask, BaseAgent
from .actions import RiskActions
from .models import PositionRisk, RiskAction, RiskAlert, RiskLevel

logger = logging.getLogger(__name__)


class RiskMonitorAgent(BaseAgent):
    """
    리스크 모니터링 에이전트

    주요 기능:
    1. 포지션 리스크 실시간 모니터링
    2. 일일 손실 한도 체크
    3. 청산가 근접 감지
    4. 자동 조치 실행 (경고, 축소, 청산)

    작업 타입:
    - monitor_position: 포지션 리스크 모니터링
    - check_daily_loss: 일일 손실 한도 체크
    - check_drawdown: 최대 낙폭 체크
    """

    def __init__(self, agent_id: str, name: str, config: dict = None):
        super().__init__(agent_id, name, config)
        self.actions = RiskActions()
        self._active_alerts: List[RiskAlert] = []

        # 리스크 임계값 (config에서 가져오거나 기본값)
        self.max_position_loss_percent = config.get("max_position_loss_percent", 5.0) if config else 5.0
        self.max_daily_loss = config.get("max_daily_loss", 1000.0) if config else 1000.0
        self.max_drawdown_percent = config.get("max_drawdown_percent", 10.0) if config else 10.0
        self.liquidation_warning_percent = config.get("liquidation_warning_percent", 10.0) if config else 10.0

    async def process_task(self, task: AgentTask) -> Any:
        """
        작업 처리

        Args:
            task: 처리할 작업

        Returns:
            모니터링 결과
        """
        task_type = task.task_type
        params = task.params

        logger.info(
            f"RiskMonitorAgent processing task: {task_type}, params: {params}"
        )

        if task_type == "monitor_position":
            return await self._monitor_position(params)

        elif task_type == "check_daily_loss":
            return await self._check_daily_loss(params)

        elif task_type == "check_drawdown":
            return await self._check_drawdown(params)

        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _monitor_position(self, params: dict) -> List[RiskAlert]:
        """
        포지션 리스크 모니터링

        Args:
            params: {
                "position": PositionRisk,
                "bitget_client": Optional[Any],
                "auto_execute": bool
            }

        Returns:
            리스크 알림 리스트
        """
        position_data = params.get("position", {})
        bitget_client = params.get("bitget_client")
        auto_execute = params.get("auto_execute", False)

        # PositionRisk 객체 생성
        position = PositionRisk(
            symbol=position_data.get("symbol", "BTCUSDT"),
            side=position_data.get("side", "long"),
            size=position_data.get("size", 0.0),
            entry_price=position_data.get("entry_price", 0.0),
            current_price=position_data.get("current_price", 0.0),
            unrealized_pnl=position_data.get("unrealized_pnl", 0.0),
            unrealized_pnl_percent=position_data.get("unrealized_pnl_percent", 0.0),
            leverage=position_data.get("leverage", 10),
            liquidation_price=position_data.get("liquidation_price"),
            distance_to_liquidation=position_data.get("distance_to_liquidation")
        )

        alerts = []

        # 1. 포지션 손실 체크
        if position.unrealized_pnl_percent < -self.max_position_loss_percent:
            alert = RiskAlert(
                alert_id=str(uuid.uuid4()),
                alert_type="position_loss",
                risk_level=RiskLevel.HIGH,
                message=f"Position loss exceeds threshold: {position.unrealized_pnl_percent:.2f}%",
                current_value=position.unrealized_pnl_percent,
                threshold_value=-self.max_position_loss_percent,
                recommended_action=RiskAction.CLOSE_POSITION,
                auto_execute=auto_execute,
                metadata={
                    "symbol": position.symbol,
                    "side": position.side,
                    "unrealized_pnl": position.unrealized_pnl
                }
            )
            alerts.append(alert)

            # 자동 실행
            if auto_execute:
                await self._execute_action(alert, position, bitget_client)

        # 2. 청산가 근접 체크
        if position.is_near_liquidation(self.liquidation_warning_percent):
            alert = RiskAlert(
                alert_id=str(uuid.uuid4()),
                alert_type="liquidation_risk",
                risk_level=RiskLevel.CRITICAL,
                message=f"Position near liquidation: {position.distance_to_liquidation:.2f}%",
                current_value=position.distance_to_liquidation,
                threshold_value=self.liquidation_warning_percent,
                recommended_action=RiskAction.REDUCE_POSITION,
                auto_execute=auto_execute,
                metadata={
                    "symbol": position.symbol,
                    "liquidation_price": position.liquidation_price
                }
            )
            alerts.append(alert)

            # 자동 실행
            if auto_execute:
                await self._execute_action(alert, position, bitget_client)

        # 활성 알림 저장
        self._active_alerts.extend(alerts)

        return alerts

    async def _check_daily_loss(self, params: dict) -> Optional[RiskAlert]:
        """
        일일 손실 한도 체크

        Args:
            params: {
                "today_pnl": float,
                "user_id": int,
                "auto_execute": bool
            }

        Returns:
            리스크 알림 (없으면 None)
        """
        today_pnl = params.get("today_pnl", 0.0)
        user_id = params.get("user_id")
        auto_execute = params.get("auto_execute", False)

        # 손실 한도 초과 체크
        if today_pnl < -self.max_daily_loss:
            alert = RiskAlert(
                alert_id=str(uuid.uuid4()),
                alert_type="daily_loss_limit",
                risk_level=RiskLevel.CRITICAL,
                message=f"Daily loss limit exceeded: ${today_pnl:.2f}",
                current_value=abs(today_pnl),
                threshold_value=self.max_daily_loss,
                recommended_action=RiskAction.STOP_TRADING,
                auto_execute=auto_execute,
                metadata={"user_id": user_id}
            )

            self._active_alerts.append(alert)

            # 자동 실행
            if auto_execute and user_id:
                result = await self.actions.stop_trading(user_id)
                logger.info(f"Auto-executed stop_trading: {result}")

            return alert

        return None

    async def _check_drawdown(self, params: dict) -> Optional[RiskAlert]:
        """
        최대 낙폭 체크

        Args:
            params: {
                "current_drawdown": float,
                "user_id": int,
                "auto_execute": bool
            }

        Returns:
            리스크 알림 (없으면 None)
        """
        current_drawdown = params.get("current_drawdown", 0.0)
        user_id = params.get("user_id")
        auto_execute = params.get("auto_execute", False)

        # 낙폭 한도 초과 체크
        if current_drawdown > self.max_drawdown_percent:
            alert = RiskAlert(
                alert_id=str(uuid.uuid4()),
                alert_type="max_drawdown",
                risk_level=RiskLevel.CRITICAL,
                message=f"Max drawdown exceeded: {current_drawdown:.2f}%",
                current_value=current_drawdown,
                threshold_value=self.max_drawdown_percent,
                recommended_action=RiskAction.STOP_TRADING,
                auto_execute=auto_execute,
                metadata={"user_id": user_id}
            )

            self._active_alerts.append(alert)

            # 자동 실행
            if auto_execute and user_id:
                result = await self.actions.stop_trading(user_id)
                logger.info(f"Auto-executed stop_trading: {result}")

            return alert

        return None

    async def _execute_action(
        self,
        alert: RiskAlert,
        position: Optional[PositionRisk] = None,
        bitget_client: Any = None
    ):
        """
        리스크 조치 실행

        Args:
            alert: 리스크 알림
            position: 포지션 정보 (필요 시)
            bitget_client: Bitget API 클라이언트
        """
        action = alert.recommended_action

        logger.warning(f"Executing risk action: {action.value} for alert {alert.alert_id}")

        try:
            if action == RiskAction.WARNING:
                result = await self.actions.execute_warning(alert.to_dict())

            elif action == RiskAction.REDUCE_POSITION and position:
                result = await self.actions.reduce_position(
                    symbol=position.symbol,
                    current_size=position.size,
                    reduction_percent=50.0,
                    bitget_client=bitget_client
                )

            elif action == RiskAction.CLOSE_POSITION and position:
                result = await self.actions.close_position(
                    symbol=position.symbol,
                    side=position.side,
                    size=position.size,
                    bitget_client=bitget_client
                )

            elif action == RiskAction.STOP_TRADING:
                user_id = alert.metadata.get("user_id")
                result = await self.actions.stop_trading(user_id)

            elif action == RiskAction.EMERGENCY_SHUTDOWN:
                result = await self.actions.emergency_shutdown()

            else:
                result = {"success": False, "error": f"Unknown action: {action}"}

            logger.info(f"Risk action executed: {result}")

        except Exception as e:
            logger.error(f"Failed to execute risk action: {e}", exc_info=True)

    def get_active_alerts(self) -> List[RiskAlert]:
        """활성 알림 조회"""
        return self._active_alerts

    def clear_alerts(self):
        """알림 초기화"""
        self._active_alerts.clear()
