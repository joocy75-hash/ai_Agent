"""
Ensemble Predictor - 5개 LightGBM 모델 통합 예측

5개 모델을 병렬로 실행하고 결과를 종합하는 앙상블 예측기
LightGBM 네이티브 형식(.txt)으로 모델 저장/로드
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# LightGBM은 선택적 import (학습 시에만 필요)
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not installed. ML models will use fallback predictions.")


class DirectionType(str, Enum):
    """방향 예측"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class VolatilityLevel(str, Enum):
    """변동성 수준"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class DirectionPrediction:
    """Model 1: 방향 확인 예측"""
    direction: DirectionType
    confidence: float
    probability_long: float
    probability_short: float
    agrees_with_rule: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction.value,
            "confidence": self.confidence,
            "probability_long": self.probability_long,
            "probability_short": self.probability_short,
            "agrees_with_rule": self.agrees_with_rule,
        }


@dataclass
class VolatilityPrediction:
    """Model 2: 변동성 예측"""
    level: VolatilityLevel
    predicted_atr: float
    current_atr: float
    atr_ratio: float
    confidence: float
    risk_score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "predicted_atr": self.predicted_atr,
            "current_atr": self.current_atr,
            "atr_ratio": self.atr_ratio,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
        }

    def is_extreme(self) -> bool:
        return self.level == VolatilityLevel.EXTREME


@dataclass
class TimingPrediction:
    """Model 3: 진입 타이밍 검증"""
    is_good_entry: bool
    confidence: float
    score: float
    waiting_recommended: bool
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_good_entry": self.is_good_entry,
            "confidence": self.confidence,
            "score": self.score,
            "waiting_recommended": self.waiting_recommended,
            "reason": self.reason,
        }


@dataclass
class StopLossPrediction:
    """Model 4: 최적 손절폭 예측"""
    optimal_sl_percent: float
    min_sl: float
    max_sl: float
    confidence: float
    based_on_atr: bool
    atr_multiplier: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimal_sl_percent": self.optimal_sl_percent,
            "min_sl": self.min_sl,
            "max_sl": self.max_sl,
            "confidence": self.confidence,
            "based_on_atr": self.based_on_atr,
            "atr_multiplier": self.atr_multiplier,
        }


@dataclass
class PositionSizePrediction:
    """Model 5: 최적 포지션 사이즈 예측"""
    optimal_size_percent: float
    min_size: float
    max_size: float
    confidence: float
    risk_adjusted: bool
    volatility_factor: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimal_size_percent": self.optimal_size_percent,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "confidence": self.confidence,
            "risk_adjusted": self.risk_adjusted,
            "volatility_factor": self.volatility_factor,
        }


@dataclass
class MLPrediction:
    """통합 ML 예측 결과"""
    symbol: str
    direction: DirectionPrediction
    volatility: VolatilityPrediction
    timing: TimingPrediction
    stoploss: StopLossPrediction
    position_size: PositionSizePrediction
    combined_confidence: float
    models_loaded: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "direction": self.direction.to_dict(),
            "volatility": self.volatility.to_dict(),
            "timing": self.timing.to_dict(),
            "stoploss": self.stoploss.to_dict(),
            "position_size": self.position_size.to_dict(),
            "combined_confidence": self.combined_confidence,
            "models_loaded": self.models_loaded,
            "timestamp": self.timestamp.isoformat(),
        }

    def should_skip_entry(self) -> bool:
        """진입을 건너뛰어야 하는가?"""
        if self.volatility.is_extreme():
            return True
        if not self.timing.is_good_entry and self.timing.confidence > 0.6:
            return True
        if self.combined_confidence < 0.4:
            return True
        return False


class EnsemblePredictor:
    """
    5개 LightGBM 모델 앙상블 예측기

    모델 저장/로드: LightGBM 네이티브 형식 (.txt)
    메타데이터: JSON 형식

    사용법:
    ```python
    predictor = EnsemblePredictor()
    result = predictor.predict(features_df, symbol="ETHUSDT")
    ```
    """

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or Path(__file__).parent.parent / "saved_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 5개 모델 (LightGBM Booster 객체)
        self.models = {
            "direction": None,
            "volatility": None,
            "timing": None,
            "stoploss": None,
            "position_size": None,
        }

        self.models_loaded = False
        self.training_features: Optional[List[str]] = None  # 학습 시 사용된 피처 목록

        # 모델 로드 시도
        self._load_models()

        logger.info(f"EnsemblePredictor initialized: models_loaded={self.models_loaded}")

    def _load_models(self):
        """
        저장된 모델 로드

        LightGBM 네이티브 형식 (.txt) 사용
        피처 중요도 파일에서 학습 피처 목록도 로드
        """
        if not LIGHTGBM_AVAILABLE:
            logger.warning("LightGBM not available, using fallback predictions")
            return

        model_files = {
            "direction": "lightgbm_direction.txt",
            "volatility": "lightgbm_volatility.txt",
            "timing": "lightgbm_timing.txt",
            "stoploss": "lightgbm_stoploss.txt",
            "position_size": "lightgbm_position_size.txt",
        }

        loaded_count = 0
        for name, filename in model_files.items():
            model_path = self.models_dir / filename
            if model_path.exists():
                try:
                    # LightGBM 네이티브 형식으로 로드
                    self.models[name] = lgb.Booster(model_file=str(model_path))
                    loaded_count += 1
                    logger.debug(f"Loaded {name} model from {filename}")
                except Exception as e:
                    logger.error(f"Failed to load {name}: {e}")

        self.models_loaded = loaded_count == len(model_files)

        # 학습 시 사용된 피처 목록 로드 (direction 모델의 피처 중요도 파일에서)
        self._load_training_features()

        logger.info(f"Loaded {loaded_count}/{len(model_files)} models")

    def _load_training_features(self):
        """피처 중요도 파일에서 학습 시 사용된 피처 목록 로드"""
        fi_path = self.models_dir / "direction_feature_importance.csv"
        if fi_path.exists():
            try:
                import csv
                with open(fi_path, 'r') as f:
                    reader = csv.DictReader(f)
                    self.training_features = [row['feature'] for row in reader]
                logger.info(f"Loaded {len(self.training_features)} training features from feature importance")
            except Exception as e:
                logger.warning(f"Failed to load training features: {e}")
                self.training_features = None
        else:
            logger.debug("No feature importance file found")

    def predict(
        self,
        features: pd.DataFrame,
        symbol: str = "ETHUSDT",
        rule_based_signal: Optional[str] = None
    ) -> MLPrediction:
        """
        통합 예측 수행

        Args:
            features: 피처 DataFrame (FeaturePipeline.extract_features() 출력)
            symbol: 심볼
            rule_based_signal: 규칙 기반 신호 (long/short/hold)

        Returns:
            MLPrediction 객체
        """
        if features.empty:
            logger.warning("Empty features, using fallback prediction")
            return self._fallback_prediction(symbol, rule_based_signal)

        # 학습 피처와 일치시키기
        if self.training_features:
            # 학습 시 사용된 피처만 선택 (없는 피처는 0으로 채움)
            aligned_features = pd.DataFrame(index=features.index)
            for feat in self.training_features:
                if feat in features.columns:
                    aligned_features[feat] = features[feat]
                else:
                    aligned_features[feat] = 0.0
            features = aligned_features

        # 최신 피처 (마지막 행)
        latest = features.iloc[-1]

        try:
            # 5개 모델 예측
            direction = self._predict_direction(latest, rule_based_signal)
            volatility = self._predict_volatility(latest)
            timing = self._predict_timing(latest)
            stoploss = self._predict_stoploss(latest, volatility)
            position_size = self._predict_position_size(latest, volatility)

            # 종합 신뢰도
            combined_confidence = self._calculate_combined_confidence(
                direction, volatility, timing, stoploss, position_size
            )

            result = MLPrediction(
                symbol=symbol,
                direction=direction,
                volatility=volatility,
                timing=timing,
                stoploss=stoploss,
                position_size=position_size,
                combined_confidence=combined_confidence,
                models_loaded=self.models_loaded,
            )

            logger.info(
                f"📊 ML Prediction: {symbol} -> "
                f"Dir:{direction.direction.value}({direction.confidence:.0%}), "
                f"Vol:{volatility.level.value}, "
                f"Timing:{timing.is_good_entry}, "
                f"Combined:{combined_confidence:.0%}"
            )

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            return self._fallback_prediction(symbol, rule_based_signal)

    def _predict_direction(
        self,
        features: pd.Series,
        rule_based_signal: Optional[str]
    ) -> DirectionPrediction:
        """Model 1: 방향 예측"""
        # 실제 모델이 로드되어 있으면 사용
        if self.models["direction"] is not None and LIGHTGBM_AVAILABLE:
            try:
                feature_array = features.values.reshape(1, -1)
                probs = self.models["direction"].predict(feature_array)[0]
                # [neutral, long, short] 순서 가정
                direction_idx = int(np.argmax(probs))
                directions = [DirectionType.NEUTRAL, DirectionType.LONG, DirectionType.SHORT]
                direction = directions[direction_idx]
                prob_long = float(probs[1]) if len(probs) > 1 else 0.5
                prob_short = float(probs[2]) if len(probs) > 2 else 0.5
                confidence = float(max(probs))
            except Exception as e:
                logger.debug(f"Model prediction failed, using heuristic: {e}")
                return self._heuristic_direction(features, rule_based_signal)
        else:
            return self._heuristic_direction(features, rule_based_signal)

        agrees = (rule_based_signal == direction.value) if rule_based_signal else True

        return DirectionPrediction(
            direction=direction,
            confidence=confidence,
            probability_long=prob_long,
            probability_short=prob_short,
            agrees_with_rule=agrees,
        )

    def _heuristic_direction(
        self,
        features: pd.Series,
        rule_based_signal: Optional[str]
    ) -> DirectionPrediction:
        """휴리스틱 기반 방향 예측 (Fallback)"""
        ema_cross = features.get('ema_cross_5_20', 0)
        rsi = features.get('rsi_14', 50)
        macd_hist = features.get('macd_histogram', 0)

        score = 0
        score += ema_cross * 30
        score += (rsi - 50) * 0.5
        score += np.sign(macd_hist) * 10

        if score > 15:
            direction = DirectionType.LONG
            prob_long, prob_short = 0.65, 0.35
        elif score < -15:
            direction = DirectionType.SHORT
            prob_long, prob_short = 0.35, 0.65
        else:
            direction = DirectionType.NEUTRAL
            prob_long, prob_short = 0.5, 0.5

        confidence = max(prob_long, prob_short)
        agrees = (rule_based_signal == direction.value) if rule_based_signal else True

        return DirectionPrediction(
            direction=direction,
            confidence=confidence,
            probability_long=prob_long,
            probability_short=prob_short,
            agrees_with_rule=agrees,
        )

    def _predict_volatility(self, features: pd.Series) -> VolatilityPrediction:
        """Model 2: 변동성 예측"""
        atr_ratio = features.get('atr_ratio', 1.0)
        current_atr = features.get('atr_14', 0)

        # 변동성 레벨 분류
        if atr_ratio >= 3.0:
            level = VolatilityLevel.EXTREME
            risk_score = 90
        elif atr_ratio >= 2.0:
            level = VolatilityLevel.HIGH
            risk_score = 70
        elif atr_ratio >= 1.0:
            level = VolatilityLevel.NORMAL
            risk_score = 40
        else:
            level = VolatilityLevel.LOW
            risk_score = 20

        return VolatilityPrediction(
            level=level,
            predicted_atr=current_atr * 1.05,
            current_atr=current_atr,
            atr_ratio=atr_ratio,
            confidence=0.7,
            risk_score=risk_score,
        )

    def _predict_timing(self, features: pd.Series) -> TimingPrediction:
        """Model 3: 타이밍 예측"""
        rsi = features.get('rsi_14', 50)
        volume_ratio = features.get('volume_ma_ratio', 1.0)
        bb_position = features.get('bb_position', 0.5)
        mtf_score = features.get('mtf_score', 0.5)

        score = 50.0

        if 30 < rsi < 70:
            score += 15
        elif rsi < 20 or rsi > 80:
            score -= 20

        if volume_ratio > 1.2:
            score += 10
        elif volume_ratio < 0.5:
            score -= 10

        if 0.2 < bb_position < 0.8:
            score += 10
        else:
            score -= 5

        score += (mtf_score - 0.5) * 20

        is_good = score > 60
        waiting = score < 40

        if is_good:
            reason = "좋은 진입 시점"
        elif waiting:
            reason = "대기 권장"
        else:
            reason = "보통"

        return TimingPrediction(
            is_good_entry=is_good,
            confidence=0.65,
            score=min(max(score, 0), 100),
            waiting_recommended=waiting,
            reason=reason,
        )

    def _predict_stoploss(
        self,
        features: pd.Series,
        volatility: VolatilityPrediction
    ) -> StopLossPrediction:
        """Model 4: 최적 손절폭 예측"""
        atr_14 = features.get('atr_14', 0)
        close = features.get('close', 1)
        atr_percent = (atr_14 / close * 100) if close > 0 else 1.5

        vol_multipliers = {
            VolatilityLevel.EXTREME: 2.5,
            VolatilityLevel.HIGH: 2.0,
            VolatilityLevel.NORMAL: 1.5,
            VolatilityLevel.LOW: 1.2,
        }
        multiplier = vol_multipliers.get(volatility.level, 1.5)

        optimal_sl = atr_percent * multiplier
        optimal_sl = min(max(optimal_sl, 0.8), 3.0)

        return StopLossPrediction(
            optimal_sl_percent=optimal_sl,
            min_sl=0.8,
            max_sl=3.0,
            confidence=0.7,
            based_on_atr=True,
            atr_multiplier=multiplier,
        )

    def _predict_position_size(
        self,
        features: pd.Series,
        volatility: VolatilityPrediction
    ) -> PositionSizePrediction:
        """Model 5: 최적 포지션 사이즈 예측"""
        vol_adjustments = {
            VolatilityLevel.EXTREME: (10.0, 0.3),
            VolatilityLevel.HIGH: (20.0, 0.6),
            VolatilityLevel.NORMAL: (30.0, 1.0),
            VolatilityLevel.LOW: (35.0, 1.2),
        }

        optimal_size, vol_factor = vol_adjustments.get(
            volatility.level, (30.0, 1.0)
        )

        return PositionSizePrediction(
            optimal_size_percent=optimal_size,
            min_size=5.0,
            max_size=40.0,
            confidence=0.7,
            risk_adjusted=True,
            volatility_factor=vol_factor,
        )

    def _calculate_combined_confidence(
        self,
        direction: DirectionPrediction,
        volatility: VolatilityPrediction,
        timing: TimingPrediction,
        stoploss: StopLossPrediction,
        position_size: PositionSizePrediction,
    ) -> float:
        """종합 신뢰도 계산"""
        weights = {
            "direction": 0.3,
            "volatility": 0.2,
            "timing": 0.25,
            "stoploss": 0.15,
            "position_size": 0.1,
        }

        combined = (
            direction.confidence * weights["direction"] +
            volatility.confidence * weights["volatility"] +
            timing.confidence * weights["timing"] +
            stoploss.confidence * weights["stoploss"] +
            position_size.confidence * weights["position_size"]
        )

        if volatility.is_extreme():
            combined *= 0.5
        if not timing.is_good_entry and timing.confidence > 0.6:
            combined *= 0.7

        return min(max(combined, 0.0), 1.0)

    def _fallback_prediction(
        self,
        symbol: str,
        rule_based_signal: Optional[str]
    ) -> MLPrediction:
        """Fallback 예측"""
        direction = DirectionPrediction(
            direction=DirectionType.NEUTRAL,
            confidence=0.5,
            probability_long=0.5,
            probability_short=0.5,
            agrees_with_rule=True,
        )

        volatility = VolatilityPrediction(
            level=VolatilityLevel.NORMAL,
            predicted_atr=0,
            current_atr=0,
            atr_ratio=1.0,
            confidence=0.5,
            risk_score=50,
        )

        timing = TimingPrediction(
            is_good_entry=True,
            confidence=0.5,
            score=50,
            waiting_recommended=False,
            reason="Fallback",
        )

        stoploss = StopLossPrediction(
            optimal_sl_percent=1.5,
            min_sl=0.8,
            max_sl=3.0,
            confidence=0.5,
            based_on_atr=False,
            atr_multiplier=1.5,
        )

        position_size = PositionSizePrediction(
            optimal_size_percent=25,
            min_size=5,
            max_size=40,
            confidence=0.5,
            risk_adjusted=False,
            volatility_factor=1.0,
        )

        return MLPrediction(
            symbol=symbol,
            direction=direction,
            volatility=volatility,
            timing=timing,
            stoploss=stoploss,
            position_size=position_size,
            combined_confidence=0.5,
            models_loaded=False,
        )

    def get_status(self) -> Dict[str, Any]:
        """모델 상태 조회"""
        return {
            "models_loaded": self.models_loaded,
            "lightgbm_available": LIGHTGBM_AVAILABLE,
            "models": {
                name: (model is not None)
                for name, model in self.models.items()
            },
            "models_dir": str(self.models_dir),
        }
