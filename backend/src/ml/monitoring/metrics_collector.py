"""
Metrics Collector - ML 모델 성능 지표 수집

실시간으로 모델 예측 성능을 추적하고 분석
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PredictionRecord:
    """예측 기록"""
    timestamp: datetime
    symbol: str
    predicted_direction: str  # up, down, neutral
    actual_direction: str  # up, down, neutral
    predicted_confidence: float
    actual_return: float  # %
    was_correct: bool
    model_version: str = ""


@dataclass
class ModelMetrics:
    """모델 성능 지표"""
    model_name: str = ""
    window_size: int = 100  # 최근 N개 예측 기준

    # 정확도 지표
    accuracy: float = 0.0  # 전체 정확도
    direction_accuracy: float = 0.0  # 방향 예측 정확도
    up_precision: float = 0.0  # UP 예측 정밀도
    down_precision: float = 0.0  # DOWN 예측 정밀도

    # 신뢰도 보정
    calibration_error: float = 0.0  # 예측 신뢰도 vs 실제 정확도 차이
    overconfidence_ratio: float = 0.0  # 과신 비율

    # 수익 관련
    avg_return_when_correct: float = 0.0
    avg_return_when_wrong: float = 0.0
    expected_value: float = 0.0  # 기대값

    # 시간 관련
    predictions_per_hour: float = 0.0
    last_prediction_at: Optional[datetime] = None

    # 상태
    is_healthy: bool = True
    health_score: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_name': self.model_name,
            'window_size': self.window_size,
            'accuracy': round(self.accuracy, 4),
            'direction_accuracy': round(self.direction_accuracy, 4),
            'up_precision': round(self.up_precision, 4),
            'down_precision': round(self.down_precision, 4),
            'calibration_error': round(self.calibration_error, 4),
            'overconfidence_ratio': round(self.overconfidence_ratio, 4),
            'avg_return_when_correct': round(self.avg_return_when_correct, 4),
            'avg_return_when_wrong': round(self.avg_return_when_wrong, 4),
            'expected_value': round(self.expected_value, 4),
            'predictions_per_hour': round(self.predictions_per_hour, 2),
            'is_healthy': self.is_healthy,
            'health_score': round(self.health_score, 1),
        }


class MetricsCollector:
    """
    ML 모델 성능 지표 수집기

    Usage:
    ```python
    collector = MetricsCollector(window_size=100)

    # 예측 기록
    collector.record_prediction(
        symbol="ETHUSDT",
        predicted_direction="up",
        predicted_confidence=0.75,
    )

    # 실제 결과 업데이트
    collector.update_actual(
        symbol="ETHUSDT",
        actual_direction="up",
        actual_return=1.5,
    )

    # 지표 조회
    metrics = collector.get_metrics()
    ```
    """

    def __init__(
        self,
        window_size: int = 100,
        model_name: str = "ml_predictor",
    ):
        self.window_size = window_size
        self.model_name = model_name

        # 예측 기록 (순환 버퍼)
        self.predictions: deque = deque(maxlen=window_size)

        # 대기 중인 예측 (실제 결과 미수신)
        self.pending_predictions: Dict[str, PredictionRecord] = {}

        # 통계
        self._total_predictions = 0
        self._start_time = datetime.utcnow()

        logger.info(f"MetricsCollector initialized (window: {window_size})")

    def record_prediction(
        self,
        symbol: str,
        predicted_direction: str,
        predicted_confidence: float,
        prediction_id: Optional[str] = None,
        model_version: str = "",
    ):
        """
        예측 기록

        Args:
            symbol: 심볼
            predicted_direction: 예측 방향 (up, down, neutral)
            predicted_confidence: 예측 신뢰도
            prediction_id: 예측 ID (결과 매칭용)
            model_version: 모델 버전
        """
        record = PredictionRecord(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            predicted_direction=predicted_direction,
            actual_direction="",
            predicted_confidence=predicted_confidence,
            actual_return=0.0,
            was_correct=False,
            model_version=model_version,
        )

        # 대기 목록에 추가
        key = prediction_id or f"{symbol}_{record.timestamp.isoformat()}"
        self.pending_predictions[key] = record

        self._total_predictions += 1

        logger.debug(f"Prediction recorded: {symbol} -> {predicted_direction} ({predicted_confidence:.2f})")

    def update_actual(
        self,
        symbol: str,
        actual_direction: str,
        actual_return: float,
        prediction_id: Optional[str] = None,
    ):
        """
        실제 결과 업데이트

        Args:
            symbol: 심볼
            actual_direction: 실제 방향
            actual_return: 실제 수익률 (%)
            prediction_id: 예측 ID
        """
        # 매칭할 예측 찾기
        record = None

        if prediction_id and prediction_id in self.pending_predictions:
            record = self.pending_predictions.pop(prediction_id)
        else:
            # 가장 오래된 해당 심볼 예측 찾기
            for key, pred in list(self.pending_predictions.items()):
                if pred.symbol == symbol:
                    record = self.pending_predictions.pop(key)
                    break

        if not record:
            logger.warning(f"No pending prediction found for {symbol}")
            return

        # 결과 업데이트
        record.actual_direction = actual_direction
        record.actual_return = actual_return
        record.was_correct = (
            record.predicted_direction == actual_direction or
            (record.predicted_direction == "neutral" and abs(actual_return) < 0.5)
        )

        # 완료된 예측 저장
        self.predictions.append(record)

        logger.debug(
            f"Actual recorded: {symbol} -> {actual_direction} "
            f"(return: {actual_return:.2f}%, correct: {record.was_correct})"
        )

    def get_metrics(self) -> ModelMetrics:
        """성능 지표 계산"""
        metrics = ModelMetrics(
            model_name=self.model_name,
            window_size=self.window_size,
        )

        records = list(self.predictions)
        if not records:
            return metrics

        # 정확도 계산
        correct = [r for r in records if r.was_correct]
        metrics.accuracy = len(correct) / len(records)

        # 방향 예측 정확도 (neutral 제외)
        directional = [r for r in records if r.predicted_direction != "neutral"]
        if directional:
            dir_correct = [r for r in directional if r.was_correct]
            metrics.direction_accuracy = len(dir_correct) / len(directional)

        # UP 정밀도
        up_predictions = [r for r in records if r.predicted_direction == "up"]
        if up_predictions:
            up_correct = [r for r in up_predictions if r.actual_direction == "up"]
            metrics.up_precision = len(up_correct) / len(up_predictions)

        # DOWN 정밀도
        down_predictions = [r for r in records if r.predicted_direction == "down"]
        if down_predictions:
            down_correct = [r for r in down_predictions if r.actual_direction == "down"]
            metrics.down_precision = len(down_correct) / len(down_predictions)

        # 신뢰도 보정 (Calibration)
        # 높은 신뢰도 예측이 실제로 더 정확한지
        high_conf = [r for r in records if r.predicted_confidence >= 0.7]
        low_conf = [r for r in records if r.predicted_confidence < 0.7]

        if high_conf:
            high_conf_accuracy = len([r for r in high_conf if r.was_correct]) / len(high_conf)
            expected_accuracy = np.mean([r.predicted_confidence for r in high_conf])
            metrics.calibration_error = abs(expected_accuracy - high_conf_accuracy)

            # 과신 비율
            if high_conf_accuracy < expected_accuracy:
                metrics.overconfidence_ratio = (expected_accuracy - high_conf_accuracy) / expected_accuracy

        # 수익 관련
        correct_returns = [r.actual_return for r in records if r.was_correct]
        wrong_returns = [r.actual_return for r in records if not r.was_correct]

        if correct_returns:
            metrics.avg_return_when_correct = np.mean(correct_returns)
        if wrong_returns:
            metrics.avg_return_when_wrong = np.mean(wrong_returns)

        # 기대값 = P(correct) * avg_win + P(wrong) * avg_loss
        metrics.expected_value = (
            metrics.accuracy * metrics.avg_return_when_correct +
            (1 - metrics.accuracy) * metrics.avg_return_when_wrong
        )

        # 예측 빈도
        if records:
            time_span = (datetime.utcnow() - records[0].timestamp).total_seconds() / 3600
            if time_span > 0:
                metrics.predictions_per_hour = len(records) / time_span

            metrics.last_prediction_at = records[-1].timestamp

        # 건강도 점수 계산
        metrics.health_score = self._calculate_health_score(metrics)
        metrics.is_healthy = metrics.health_score >= 60

        return metrics

    def _calculate_health_score(self, metrics: ModelMetrics) -> float:
        """
        모델 건강도 점수 계산 (0-100)

        기준:
        - 정확도 50% 이상 (25점)
        - 방향 정확도 55% 이상 (25점)
        - 보정 오차 10% 이하 (25점)
        - 양의 기대값 (25점)
        """
        score = 0

        # 정확도 (25점)
        if metrics.accuracy >= 0.5:
            score += min(25, (metrics.accuracy - 0.5) / 0.2 * 25 + 12.5)

        # 방향 정확도 (25점)
        if metrics.direction_accuracy >= 0.55:
            score += min(25, (metrics.direction_accuracy - 0.55) / 0.15 * 25 + 12.5)

        # 보정 오차 (25점)
        if metrics.calibration_error <= 0.1:
            score += 25 - metrics.calibration_error * 100

        # 기대값 (25점)
        if metrics.expected_value > 0:
            score += min(25, metrics.expected_value * 10)

        return max(0, min(100, score))

    def get_recent_predictions(self, limit: int = 20) -> List[Dict]:
        """최근 예측 목록"""
        records = list(self.predictions)[-limit:]
        return [
            {
                'timestamp': r.timestamp.isoformat(),
                'symbol': r.symbol,
                'predicted': r.predicted_direction,
                'actual': r.actual_direction,
                'confidence': round(r.predicted_confidence, 2),
                'return': round(r.actual_return, 2),
                'correct': r.was_correct,
            }
            for r in records
        ]

    def get_pending_count(self) -> int:
        """대기 중인 예측 수"""
        return len(self.pending_predictions)

    def clear_old_pending(self, max_age_minutes: int = 60):
        """오래된 대기 예측 정리"""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        old_keys = [
            k for k, v in self.pending_predictions.items()
            if v.timestamp < cutoff
        ]
        for key in old_keys:
            del self.pending_predictions[key]

        if old_keys:
            logger.info(f"Cleared {len(old_keys)} old pending predictions")

    def reset(self):
        """지표 리셋"""
        self.predictions.clear()
        self.pending_predictions.clear()
        self._total_predictions = 0
        self._start_time = datetime.utcnow()
        logger.info("MetricsCollector reset")
