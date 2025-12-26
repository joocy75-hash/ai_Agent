"""
ML Module - DeepSeek AI + LightGBM Hybrid System

AI의 추론력 + ML의 정밀도 = 최적의 조합

이 모듈은 4단계 의사결정 파이프라인을 제공합니다:
1. 규칙 기반 신호 생성 (빠름, 신뢰성)
2. LightGBM 검증 & 최적화 (빠름, 정밀)
3. DeepSeek AI 최종 확인 (느림, 추론력)
4. 최종 결정: 고품질 신호만 진입

5가지 LightGBM 모델:
1. Direction Model: 방향 확인 (long/short/neutral)
2. Volatility Model: 변동성 분류 (normal/high/extreme)
3. Timing Model: 진입 타이밍 평가
4. Stop Loss Model: 최적 손절 계산
5. Position Size Model: 최적 포지션 크기 계산

Sub-modules:
- features: 피처 추출 파이프라인 (70개 피처)
- models: LightGBM 앙상블 예측기
- training: 데이터 수집, 라벨링, 모델 학습
- validation: 백테스트, A/B 테스트
- monitoring: 성능 모니터링, 알림
"""

# Features
from .features.feature_pipeline import FeaturePipeline

# Models
from .models.ensemble_predictor import EnsemblePredictor, MLPrediction

# Training (lazy import to avoid circular dependencies)
# from .training import DataCollector, Labeler, ModelTrainer

# Validation
from .validation.backtester import Backtester, BacktestResult
from .validation.ab_tester import ABTester, ABTestResult

# Monitoring
from .monitoring.metrics_collector import MetricsCollector, ModelMetrics
from .monitoring.alerter import Alerter, AlertLevel, Alert

__all__ = [
    # Features
    "FeaturePipeline",
    # Models
    "EnsemblePredictor",
    "MLPrediction",
    # Validation
    "Backtester",
    "BacktestResult",
    "ABTester",
    "ABTestResult",
    # Monitoring
    "MetricsCollector",
    "ModelMetrics",
    "Alerter",
    "AlertLevel",
    "Alert",
]
