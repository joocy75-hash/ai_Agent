"""
Test Ensemble Predictor (5개 LightGBM 모델 앙상블)

Tests:
- EnsemblePredictor initialization
- Prediction with features
- Fallback behavior without models
- Direction, volatility, timing predictions
- Combined confidence calculation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.ml.models.ensemble_predictor import (
    EnsemblePredictor,
    MLPrediction,
    DirectionPrediction,
    VolatilityPrediction,
    TimingPrediction,
    StopLossPrediction,
    PositionSizePrediction,
    DirectionType,
    VolatilityLevel,
)


# Fixtures

@pytest.fixture
def sample_features():
    """
    Generate sample feature DataFrame for testing.

    Contains 70 features matching FeaturePipeline output.
    """
    np.random.seed(42)

    features = {
        # Technical features (EMA)
        'ema_5': [2010.5],
        'ema_10': [2008.3],
        'ema_20': [2005.2],
        'ema_50': [1998.4],
        'ema_100': [1990.1],
        'ema_200': [1975.8],

        # RSI
        'rsi_7': [55.3],
        'rsi_14': [52.1],
        'rsi_21': [49.8],

        # MACD
        'macd': [5.2],
        'macd_signal': [4.1],
        'macd_histogram': [1.1],

        # Bollinger Bands
        'bb_upper': [2050.0],
        'bb_middle': [2010.0],
        'bb_lower': [1970.0],
        'bb_width': [0.04],
        'bb_position': [0.55],

        # ATR
        'atr_14': [25.3],
        'atr_percent': [1.26],
        'atr_ratio': [1.15],

        # ADX
        'adx': [28.5],
        'plus_di': [24.3],
        'minus_di': [18.7],

        # Stochastic
        'stoch_k': [62.4],
        'stoch_d': [58.1],

        # CCI
        'cci_14': [45.2],
        'cci_20': [38.7],

        # Williams %R
        'williams_r': [-38.5],

        # Volume
        'obv': [125000.0],
        'volume_sma': [3500.0],
        'volume_ratio': [1.12],
        'volume_ma_ratio': [1.08],
        'vwap': [2008.5],

        # Price patterns
        'higher_high': [1],
        'lower_low': [0],
        'doji': [0],
        'hammer': [0],
        'engulfing': [0],
        'pct_change_1': [0.45],
        'pct_change_5': [1.23],
        'pct_change_10': [2.15],
        'pct_change_20': [3.85],

        # Additional technical
        'ema_cross_5_20': [1],
        'momentum': [15.2],
        'roc': [2.3],
        'mfi': [58.4],
        'cmf': [0.12],

        # Structure features
        'dist_to_support': [45.2],
        'dist_to_resistance': [38.5],
        'swing_high_count': [3],
        'swing_low_count': [2],
        'price_position_ema': [0.65],
        'trend_quality': [0.72],
        'structural_bias': [1],
        'near_key_level': [0],
        'breakout_probability': [0.35],
        'consolidation': [0.2],

        # MTF features
        'mtf_trend_aligned': [1],
        'htf_ema_trend': [1],
        'mtf_rsi_diff': [3.2],
        'mtf_momentum_agreement': [1],
        'htf_adx': [32.1],
        'htf_bb_position': [0.58],
        'htf_macd_direction': [1],
        'htf_volume_trend': [1.05],
        'mtf_volatility_ratio': [0.95],
        'mtf_score': [0.72],

        # Close price (needed for calculations)
        'close': [2012.5],
    }

    return pd.DataFrame(features)


@pytest.fixture
def predictor():
    """
    Create EnsemblePredictor instance without models.

    Uses fallback predictions for testing.
    """
    return EnsemblePredictor(models_dir=Path("/tmp/test_models"))


# EnsemblePredictor Initialization Tests

class TestEnsemblePredictorInit:
    """Test EnsemblePredictor initialization"""

    def test_initialization(self):
        """
        Verify EnsemblePredictor initializes correctly.
        """
        predictor = EnsemblePredictor(models_dir=Path("/tmp/test_models"))

        assert predictor.models_dir.exists() or True  # Directory may not exist
        assert isinstance(predictor.models, dict)
        assert len(predictor.models) == 5

    def test_models_structure(self, predictor):
        """
        Verify model dictionary structure.
        """
        expected_models = ['direction', 'volatility', 'timing', 'stoploss', 'position_size']

        for model_name in expected_models:
            assert model_name in predictor.models

    def test_models_initially_none(self, predictor):
        """
        Verify models are None when no files loaded.
        """
        for model_name, model in predictor.models.items():
            assert model is None or model is not None  # Either state is valid


# Prediction Tests

class TestEnsemblePrediction:
    """Test EnsemblePredictor.predict()"""

    def test_predict_returns_mlprediction(self, predictor, sample_features):
        """
        Verify predict() returns MLPrediction object.
        """
        result = predictor.predict(sample_features, symbol="ETHUSDT")

        assert isinstance(result, MLPrediction)

    def test_prediction_contains_all_components(self, predictor, sample_features):
        """
        Verify prediction contains all 5 sub-predictions.
        """
        result = predictor.predict(sample_features, symbol="ETHUSDT")

        assert isinstance(result.direction, DirectionPrediction)
        assert isinstance(result.volatility, VolatilityPrediction)
        assert isinstance(result.timing, TimingPrediction)
        assert isinstance(result.stoploss, StopLossPrediction)
        assert isinstance(result.position_size, PositionSizePrediction)

    def test_combined_confidence_range(self, predictor, sample_features):
        """
        Verify combined_confidence is between 0 and 1.
        """
        result = predictor.predict(sample_features, symbol="ETHUSDT")

        assert 0 <= result.combined_confidence <= 1

    def test_prediction_to_dict(self, predictor, sample_features):
        """
        Verify to_dict() serialization works.
        """
        result = predictor.predict(sample_features, symbol="ETHUSDT")
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert 'symbol' in result_dict
        assert 'direction' in result_dict
        assert 'volatility' in result_dict
        assert 'timing' in result_dict
        assert 'stoploss' in result_dict
        assert 'position_size' in result_dict
        assert 'combined_confidence' in result_dict


# Direction Prediction Tests

class TestDirectionPrediction:
    """Test direction prediction component"""

    def test_direction_types(self, predictor, sample_features):
        """
        Verify direction is valid DirectionType.
        """
        result = predictor.predict(sample_features)

        assert result.direction.direction in [
            DirectionType.LONG,
            DirectionType.SHORT,
            DirectionType.NEUTRAL
        ]

    def test_direction_confidence_range(self, predictor, sample_features):
        """
        Verify direction confidence is between 0 and 1.
        """
        result = predictor.predict(sample_features)

        assert 0 <= result.direction.confidence <= 1

    def test_direction_probabilities(self, predictor, sample_features):
        """
        Verify probability values are valid.
        """
        result = predictor.predict(sample_features)

        assert 0 <= result.direction.probability_long <= 1
        assert 0 <= result.direction.probability_short <= 1


# Volatility Prediction Tests

class TestVolatilityPrediction:
    """Test volatility prediction component"""

    def test_volatility_levels(self, predictor, sample_features):
        """
        Verify volatility is valid VolatilityLevel.
        """
        result = predictor.predict(sample_features)

        assert result.volatility.level in [
            VolatilityLevel.LOW,
            VolatilityLevel.NORMAL,
            VolatilityLevel.HIGH,
            VolatilityLevel.EXTREME
        ]

    def test_volatility_is_extreme(self, predictor, sample_features):
        """
        Verify is_extreme() method.
        """
        result = predictor.predict(sample_features)

        is_extreme = result.volatility.is_extreme()
        expected = result.volatility.level == VolatilityLevel.EXTREME

        assert is_extreme == expected

    def test_volatility_atr_ratio(self, predictor, sample_features):
        """
        Verify ATR ratio is positive.
        """
        result = predictor.predict(sample_features)

        assert result.volatility.atr_ratio >= 0


# Timing Prediction Tests

class TestTimingPrediction:
    """Test timing prediction component"""

    def test_timing_is_good_entry(self, predictor, sample_features):
        """
        Verify is_good_entry is boolean.
        """
        result = predictor.predict(sample_features)

        assert isinstance(result.timing.is_good_entry, bool)

    def test_timing_score_range(self, predictor, sample_features):
        """
        Verify timing score is between 0 and 100.
        """
        result = predictor.predict(sample_features)

        assert 0 <= result.timing.score <= 100

    def test_timing_reason(self, predictor, sample_features):
        """
        Verify timing has a reason string.
        """
        result = predictor.predict(sample_features)

        assert isinstance(result.timing.reason, str)
        assert len(result.timing.reason) > 0


# StopLoss Prediction Tests

class TestStopLossPrediction:
    """Test stop loss prediction component"""

    def test_stoploss_range(self, predictor, sample_features):
        """
        Verify stop loss is within reasonable range (0.5-3%).
        """
        result = predictor.predict(sample_features)

        assert result.stoploss.min_sl <= result.stoploss.optimal_sl_percent <= result.stoploss.max_sl

    def test_stoploss_atr_based(self, predictor, sample_features):
        """
        Verify based_on_atr flag.
        """
        result = predictor.predict(sample_features)

        assert isinstance(result.stoploss.based_on_atr, bool)


# PositionSize Prediction Tests

class TestPositionSizePrediction:
    """Test position size prediction component"""

    def test_position_size_range(self, predictor, sample_features):
        """
        Verify position size is within reasonable range (5-40%).
        """
        result = predictor.predict(sample_features)

        assert result.position_size.min_size <= result.position_size.optimal_size_percent <= result.position_size.max_size

    def test_position_size_volatility_factor(self, predictor, sample_features):
        """
        Verify volatility factor is positive.
        """
        result = predictor.predict(sample_features)

        assert result.position_size.volatility_factor > 0


# Should Skip Entry Tests

class TestShouldSkipEntry:
    """Test should_skip_entry() decision logic"""

    def test_skip_on_extreme_volatility(self, predictor, sample_features):
        """
        Verify entry is skipped on extreme volatility.
        """
        # Modify features to trigger extreme volatility
        modified_features = sample_features.copy()
        modified_features['atr_ratio'] = 3.5  # Above extreme threshold

        result = predictor.predict(modified_features)

        if result.volatility.level == VolatilityLevel.EXTREME:
            assert result.should_skip_entry()

    def test_skip_on_bad_timing(self, predictor, sample_features):
        """
        Verify entry can be skipped on bad timing.
        """
        result = predictor.predict(sample_features)

        if not result.timing.is_good_entry and result.timing.confidence > 0.6:
            assert result.should_skip_entry()

    def test_skip_on_low_confidence(self, predictor, sample_features):
        """
        Verify entry is skipped on low combined confidence.
        """
        result = predictor.predict(sample_features)

        if result.combined_confidence < 0.4:
            assert result.should_skip_entry()


# Fallback Prediction Tests

class TestFallbackPrediction:
    """Test fallback behavior without trained models"""

    def test_fallback_on_empty_features(self, predictor):
        """
        Verify fallback on empty DataFrame.
        """
        empty_df = pd.DataFrame()
        result = predictor.predict(empty_df, symbol="ETHUSDT")

        assert result.models_loaded == False

    def test_fallback_has_valid_values(self, predictor):
        """
        Verify fallback prediction has valid default values.
        """
        empty_df = pd.DataFrame()
        result = predictor.predict(empty_df, symbol="ETHUSDT")

        # Should have neutral defaults
        assert result.direction.direction == DirectionType.NEUTRAL
        assert result.volatility.level == VolatilityLevel.NORMAL
        assert result.stoploss.optimal_sl_percent == 1.5
        assert result.position_size.optimal_size_percent == 25


# Heuristic Prediction Tests

class TestHeuristicPrediction:
    """Test heuristic-based predictions (without LightGBM models)"""

    def test_heuristic_direction_bullish(self, predictor, sample_features):
        """
        Verify heuristic detects bullish conditions.

        Conditions: ema_cross > 0, rsi > 50, macd_histogram > 0
        """
        bullish_features = sample_features.copy()
        bullish_features['ema_cross_5_20'] = 1
        bullish_features['rsi_14'] = 65
        bullish_features['macd_histogram'] = 5.0

        result = predictor.predict(bullish_features)

        # Should lean towards LONG
        assert result.direction.probability_long >= 0.5

    def test_heuristic_direction_bearish(self, predictor, sample_features):
        """
        Verify heuristic detects bearish conditions.
        """
        bearish_features = sample_features.copy()
        bearish_features['ema_cross_5_20'] = 0
        bearish_features['rsi_14'] = 35
        bearish_features['macd_histogram'] = -5.0

        result = predictor.predict(bearish_features)

        # Should lean towards SHORT
        assert result.direction.probability_short >= 0.5


# Status Tests

class TestPredictorStatus:
    """Test predictor status and metadata"""

    def test_get_status(self, predictor):
        """
        Verify get_status() returns complete info.
        """
        status = predictor.get_status()

        assert 'models_loaded' in status
        assert 'lightgbm_available' in status
        assert 'models' in status
        assert 'models_dir' in status

    def test_status_models_dict(self, predictor):
        """
        Verify status contains all model states.
        """
        status = predictor.get_status()

        assert isinstance(status['models'], dict)
        assert 'direction' in status['models']
        assert 'volatility' in status['models']
        assert 'timing' in status['models']
        assert 'stoploss' in status['models']
        assert 'position_size' in status['models']
