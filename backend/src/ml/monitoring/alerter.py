"""
Alerter - ML 모델 성능 저하 알림

모델 성능이 기준 이하로 떨어지면 알림 발생
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """알림 레벨"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """알림 유형"""
    LOW_ACCURACY = "low_accuracy"
    HIGH_CALIBRATION_ERROR = "high_calibration_error"
    NEGATIVE_EV = "negative_expected_value"
    NO_PREDICTIONS = "no_predictions"
    MODEL_UNHEALTHY = "model_unhealthy"
    CONSECUTIVE_LOSSES = "consecutive_losses"


@dataclass
class Alert:
    """알림"""
    alert_id: str
    alert_type: AlertType
    level: AlertLevel
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'alert_id': self.alert_id,
            'type': self.alert_type.value,
            'level': self.level.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
        }


@dataclass
class AlertThresholds:
    """알림 임계값"""
    min_accuracy: float = 0.45  # 45% 미만 시 경고
    min_direction_accuracy: float = 0.50  # 50% 미만 시 경고
    max_calibration_error: float = 0.15  # 15% 초과 시 경고
    min_expected_value: float = 0.0  # 음수면 경고
    max_no_prediction_minutes: int = 30  # 30분 예측 없으면 경고
    max_consecutive_losses: int = 5  # 연속 5회 실패 시 경고
    min_health_score: float = 50.0  # 50점 미만 시 경고


class Alerter:
    """
    ML 모델 성능 알림 시스템

    Usage:
    ```python
    alerter = Alerter(thresholds=AlertThresholds())

    # 알림 핸들러 등록
    alerter.add_handler(lambda alert: print(alert.message))

    # 메트릭 체크
    alerts = alerter.check_metrics(metrics)

    # 연속 손실 체크
    alerter.record_trade_result(won=False)
    ```
    """

    def __init__(
        self,
        thresholds: Optional[AlertThresholds] = None,
        max_alerts: int = 100,
    ):
        self.thresholds = thresholds or AlertThresholds()
        self.max_alerts = max_alerts

        # 알림 기록
        self.alerts: List[Alert] = []
        self._alert_counter = 0

        # 알림 핸들러
        self._handlers: List[Callable[[Alert], None]] = []

        # 상태 추적
        self._consecutive_losses = 0
        self._last_prediction_time: Optional[datetime] = None
        self._last_alert_times: Dict[AlertType, datetime] = {}

        # 쿨다운 (같은 유형 알림 방지)
        self._cooldown_minutes = 15

        logger.info("Alerter initialized")

    def add_handler(self, handler: Callable[[Alert], None]):
        """알림 핸들러 추가"""
        self._handlers.append(handler)

    def check_metrics(self, metrics: Any) -> List[Alert]:
        """
        메트릭 체크 및 알림 생성

        Args:
            metrics: ModelMetrics 객체

        Returns:
            생성된 알림 목록
        """
        new_alerts = []

        # 1. 정확도 체크
        if metrics.accuracy < self.thresholds.min_accuracy:
            alert = self._create_alert(
                AlertType.LOW_ACCURACY,
                AlertLevel.WARNING,
                f"Model accuracy ({metrics.accuracy:.1%}) is below threshold ({self.thresholds.min_accuracy:.1%})",
                {'accuracy': metrics.accuracy, 'threshold': self.thresholds.min_accuracy}
            )
            if alert:
                new_alerts.append(alert)

        # 2. 방향 정확도 체크
        if metrics.direction_accuracy < self.thresholds.min_direction_accuracy:
            alert = self._create_alert(
                AlertType.LOW_ACCURACY,
                AlertLevel.WARNING,
                f"Direction accuracy ({metrics.direction_accuracy:.1%}) is below threshold",
                {'direction_accuracy': metrics.direction_accuracy}
            )
            if alert:
                new_alerts.append(alert)

        # 3. 보정 오차 체크
        if metrics.calibration_error > self.thresholds.max_calibration_error:
            alert = self._create_alert(
                AlertType.HIGH_CALIBRATION_ERROR,
                AlertLevel.WARNING,
                f"Calibration error ({metrics.calibration_error:.1%}) is too high",
                {'calibration_error': metrics.calibration_error}
            )
            if alert:
                new_alerts.append(alert)

        # 4. 기대값 체크
        if metrics.expected_value < self.thresholds.min_expected_value:
            alert = self._create_alert(
                AlertType.NEGATIVE_EV,
                AlertLevel.CRITICAL,
                f"Expected value is negative ({metrics.expected_value:.2%})",
                {'expected_value': metrics.expected_value}
            )
            if alert:
                new_alerts.append(alert)

        # 5. 건강도 체크
        if metrics.health_score < self.thresholds.min_health_score:
            alert = self._create_alert(
                AlertType.MODEL_UNHEALTHY,
                AlertLevel.CRITICAL,
                f"Model health score ({metrics.health_score:.0f}) is below threshold ({self.thresholds.min_health_score:.0f})",
                {'health_score': metrics.health_score}
            )
            if alert:
                new_alerts.append(alert)

        # 6. 예측 없음 체크
        if metrics.last_prediction_at:
            self._last_prediction_time = metrics.last_prediction_at
            minutes_since = (datetime.utcnow() - metrics.last_prediction_at).total_seconds() / 60
            if minutes_since > self.thresholds.max_no_prediction_minutes:
                alert = self._create_alert(
                    AlertType.NO_PREDICTIONS,
                    AlertLevel.WARNING,
                    f"No predictions for {minutes_since:.0f} minutes",
                    {'minutes_since_last': minutes_since}
                )
                if alert:
                    new_alerts.append(alert)

        return new_alerts

    def record_trade_result(self, won: bool) -> Optional[Alert]:
        """
        거래 결과 기록 및 연속 손실 체크

        Args:
            won: 승리 여부

        Returns:
            연속 손실 알림 (있는 경우)
        """
        if won:
            self._consecutive_losses = 0
            return None

        self._consecutive_losses += 1

        if self._consecutive_losses >= self.thresholds.max_consecutive_losses:
            alert = self._create_alert(
                AlertType.CONSECUTIVE_LOSSES,
                AlertLevel.CRITICAL,
                f"Consecutive losses: {self._consecutive_losses}",
                {'consecutive_losses': self._consecutive_losses}
            )
            return alert

        return None

    def _create_alert(
        self,
        alert_type: AlertType,
        level: AlertLevel,
        message: str,
        details: Dict[str, Any]
    ) -> Optional[Alert]:
        """알림 생성 (쿨다운 적용)"""
        # 쿨다운 체크
        if alert_type in self._last_alert_times:
            last_time = self._last_alert_times[alert_type]
            if datetime.utcnow() - last_time < timedelta(minutes=self._cooldown_minutes):
                return None

        # 알림 생성
        self._alert_counter += 1
        alert = Alert(
            alert_id=f"alert_{self._alert_counter}",
            alert_type=alert_type,
            level=level,
            message=message,
            details=details,
        )

        # 기록
        self.alerts.append(alert)
        self._last_alert_times[alert_type] = datetime.utcnow()

        # 오래된 알림 정리
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]

        # 핸들러 호출
        self._notify_handlers(alert)

        logger.warning(f"Alert created: [{level.value.upper()}] {message}")

        return alert

    def _notify_handlers(self, alert: Alert):
        """핸들러에 알림 전달"""
        for handler in self._handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def acknowledge_alert(self, alert_id: str) -> bool:
        """알림 확인 처리"""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.utcnow()
                return True
        return False

    def get_unacknowledged(self) -> List[Alert]:
        """확인되지 않은 알림 목록"""
        return [a for a in self.alerts if not a.acknowledged]

    def get_recent_alerts(self, limit: int = 20) -> List[Dict]:
        """최근 알림 목록"""
        return [a.to_dict() for a in self.alerts[-limit:]]

    def get_alert_summary(self) -> Dict[str, Any]:
        """알림 요약"""
        unacked = self.get_unacknowledged()
        by_level = {
            'info': len([a for a in unacked if a.level == AlertLevel.INFO]),
            'warning': len([a for a in unacked if a.level == AlertLevel.WARNING]),
            'critical': len([a for a in unacked if a.level == AlertLevel.CRITICAL]),
        }

        return {
            'total_alerts': len(self.alerts),
            'unacknowledged': len(unacked),
            'by_level': by_level,
            'consecutive_losses': self._consecutive_losses,
        }

    def reset_consecutive_losses(self):
        """연속 손실 카운터 리셋"""
        self._consecutive_losses = 0

    def clear_alerts(self):
        """모든 알림 삭제"""
        self.alerts.clear()
        self._alert_counter = 0
        logger.info("All alerts cleared")
