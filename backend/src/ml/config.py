"""
ML Configuration - 피처 및 모델 설정

LightGBM 하이퍼파라미터, 피처 설정, 모델 경로 등
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

# 모델 저장 경로
ML_MODELS_DIR = Path(__file__).parent / "saved_models"
ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class FeatureConfig:
    """피처 설정"""
    # 기술적 지표 설정
    ema_periods: List[int] = None
    rsi_periods: List[int] = None
    atr_period: int = 14
    adx_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0

    def __post_init__(self):
        if self.ema_periods is None:
            self.ema_periods = [5, 10, 20, 50, 100, 200]
        if self.rsi_periods is None:
            self.rsi_periods = [7, 14, 21]


@dataclass
class LightGBMConfig:
    """LightGBM 모델 설정"""
    # Classifier 기본값
    classifier_params: Dict[str, Any] = None
    # Regressor 기본값
    regressor_params: Dict[str, Any] = None
    # 학습 설정
    num_boost_round: int = 500
    early_stopping_rounds: int = 50

    def __post_init__(self):
        if self.classifier_params is None:
            self.classifier_params = {
                "objective": "multiclass",
                "metric": "multi_logloss",
                "boosting_type": "gbdt",
                "num_leaves": 31,
                "learning_rate": 0.05,
                "feature_fraction": 0.8,
                "bagging_fraction": 0.8,
                "bagging_freq": 5,
                "verbose": -1,
                "num_threads": 4,
                "max_depth": 6,
                "min_data_in_leaf": 20,
            }
        if self.regressor_params is None:
            self.regressor_params = {
                "objective": "regression",
                "metric": "rmse",
                "boosting_type": "gbdt",
                "num_leaves": 31,
                "learning_rate": 0.05,
                "feature_fraction": 0.8,
                "bagging_fraction": 0.8,
                "bagging_freq": 5,
                "verbose": -1,
                "num_threads": 4,
                "max_depth": 6,
                "min_data_in_leaf": 20,
            }


@dataclass
class MLConfig:
    """통합 ML 설정"""
    feature_config: FeatureConfig = None
    lightgbm_config: LightGBMConfig = None
    # 모델 경로
    models_dir: Path = ML_MODELS_DIR
    # 캐시 설정
    prediction_cache_ttl: float = 5.0  # 초
    # 예측 임계값
    direction_confidence_threshold: float = 0.6
    timing_confidence_threshold: float = 0.55
    extreme_volatility_atr_ratio: float = 3.0

    def __post_init__(self):
        if self.feature_config is None:
            self.feature_config = FeatureConfig()
        if self.lightgbm_config is None:
            self.lightgbm_config = LightGBMConfig()


# 변동성 기반 조정 계수
VOLATILITY_ADJUSTMENTS = {
    "low": {
        "size_mult": 1.2,      # 사이즈 20% 증가
        "sl_mult": 0.8,        # SL 20% 감소
        "leverage_mult": 1.2,  # 레버리지 20% 증가
    },
    "normal": {
        "size_mult": 1.0,
        "sl_mult": 1.0,
        "leverage_mult": 1.0,
    },
    "high": {
        "size_mult": 0.6,      # 사이즈 40% 감소
        "sl_mult": 1.3,        # SL 30% 증가
        "leverage_mult": 0.7,  # 레버리지 30% 감소
    },
    "extreme": {
        "size_mult": 0.3,      # 사이즈 70% 감소
        "sl_mult": 1.5,        # SL 50% 증가
        "leverage_mult": 0.5,  # 레버리지 50% 감소
    },
}


# 기본 설정 인스턴스
default_ml_config = MLConfig()
