"""
Test Feature Pipeline and Feature Calculators

Tests:
- TechnicalFeatures with sample OHLCV data
- StructureFeatures
- MTFFeatures
- FeaturePipeline integration
- Verify 70 features are generated
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.ml.features.technical_features import TechnicalFeatures
from src.ml.features.structure_features import StructureFeatures
from src.ml.features.mtf_features import MTFFeatures
from src.ml.features.feature_pipeline import FeaturePipeline


# Fixtures

@pytest.fixture
def sample_ohlcv_data():
    """
    Generate sample OHLCV data for testing.

    Creates 200 candles with realistic price movements.
    """
    np.random.seed(42)
    n = 200

    # Generate price data with trend
    base_price = 2000.0
    prices = [base_price]

    for _ in range(n - 1):
        change = np.random.randn() * 20 + 0.5  # Slight upward bias
        prices.append(prices[-1] + change)

    # Create OHLCV DataFrame
    data = []
    for i, close in enumerate(prices):
        high = close + abs(np.random.randn() * 10)
        low = close - abs(np.random.randn() * 10)
        open_price = low + (high - low) * np.random.random()
        volume = np.random.uniform(1000, 5000)

        timestamp = datetime.utcnow() - timedelta(minutes=(n - i) * 5)

        data.append({
            'timestamp': timestamp,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
        })

    return data


@pytest.fixture
def sample_df(sample_ohlcv_data):
    """
    Convert sample OHLCV data to DataFrame.
    """
    df = pd.DataFrame(sample_ohlcv_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    return df


@pytest.fixture
def sample_candles_list(sample_ohlcv_data):
    """
    Sample candles as list of dicts (API format).
    """
    return sample_ohlcv_data


# TechnicalFeatures Tests

class TestTechnicalFeatures:
    """Test TechnicalFeatures calculator"""

    def test_initialization(self):
        """
        Verify TechnicalFeatures initializes with default parameters.
        """
        tech = TechnicalFeatures()

        assert tech.ema_periods == [5, 10, 20, 50, 100, 200]
        assert tech.rsi_periods == [7, 14, 21]
        assert tech.atr_period == 14
        assert tech.adx_period == 14

    def test_calculate_all_features(self, sample_df):
        """
        Verify calculate_all() generates all technical features.

        Expected features:
        - EMA: 6 features
        - RSI: 3 features
        - MACD: 3 features
        - Bollinger: 4 features
        - ATR: 2 features
        - ADX: 3 features
        - Stochastic: 2 features
        - CCI: 2 features
        - Williams %R: 1 feature
        - Volume: 5 features
        - Price patterns: 10 features
        - Additional: 9 features
        Total: 50 technical features
        """
        tech = TechnicalFeatures()
        result = tech.calculate_all(sample_df)

        # Verify essential features exist
        assert 'ema_5' in result.columns
        assert 'ema_200' in result.columns
        assert 'rsi_14' in result.columns
        assert 'macd' in result.columns
        assert 'bb_upper' in result.columns
        assert 'atr_14' in result.columns
        assert 'adx' in result.columns
        assert 'stoch_k' in result.columns
        assert 'cci_14' in result.columns
        assert 'williams_r' in result.columns
        assert 'obv' in result.columns
        assert 'vwap' in result.columns

        # Price patterns
        assert 'higher_high' in result.columns
        assert 'pct_change_1' in result.columns

        # Additional features
        assert 'ema_cross_5_20' in result.columns
        assert 'bb_position' in result.columns

        # Verify no NaN in recent data (last 50 rows)
        assert not result.iloc[-50:].isnull().all().any()

    def test_ema_calculation(self, sample_df):
        """
        Verify EMA is calculated correctly.
        """
        tech = TechnicalFeatures()
        result = tech.calculate_all(sample_df)

        # EMA should exist
        assert 'ema_20' in result.columns

        # EMA should be numeric
        assert pd.api.types.is_numeric_dtype(result['ema_20'])

        # Recent EMA should be close to price
        last_close = result['close'].iloc[-1]
        last_ema = result['ema_20'].iloc[-1]

        # EMA should be within 5% of price
        assert abs(last_ema - last_close) / last_close < 0.05

    def test_rsi_bounds(self, sample_df):
        """
        Verify RSI is bounded between 0 and 100.
        """
        tech = TechnicalFeatures()
        result = tech.calculate_all(sample_df)

        rsi = result['rsi_14'].dropna()

        assert rsi.min() >= 0
        assert rsi.max() <= 100

    def test_bollinger_bands_order(self, sample_df):
        """
        Verify Bollinger Bands: upper > middle > lower.
        """
        tech = TechnicalFeatures()
        result = tech.calculate_all(sample_df)

        # Get last 50 valid rows
        valid = result.dropna(subset=['bb_upper', 'bb_middle', 'bb_lower']).tail(50)

        # Upper should be >= middle
        assert (valid['bb_upper'] >= valid['bb_middle']).all()

        # Middle should be >= lower
        assert (valid['bb_middle'] >= valid['bb_lower']).all()


# StructureFeatures Tests

class TestStructureFeatures:
    """Test StructureFeatures calculator"""

    def test_initialization(self):
        """
        Verify StructureFeatures initializes.
        """
        struct = StructureFeatures(lookback_period=50)
        assert struct.lookback_period == 50

    def test_calculate_all_features(self, sample_df):
        """
        Verify calculate_all() generates all structure features.

        Expected: 10 structure features
        """
        struct = StructureFeatures()
        result = struct.calculate_all(sample_df)

        # Verify all 10 structure features
        assert 'dist_to_support' in result.columns
        assert 'dist_to_resistance' in result.columns
        assert 'swing_high_count' in result.columns
        assert 'swing_low_count' in result.columns
        assert 'price_position_ema' in result.columns
        assert 'trend_quality' in result.columns
        assert 'structural_bias' in result.columns
        assert 'near_key_level' in result.columns
        assert 'breakout_probability' in result.columns
        assert 'consolidation' in result.columns

    def test_swing_point_detection(self, sample_df):
        """
        Verify swing points are detected.
        """
        struct = StructureFeatures()
        swing_highs, swing_lows = struct._detect_swing_points(sample_df)

        # Should detect some swing points
        assert swing_highs.sum() > 0
        assert swing_lows.sum() > 0

        # Should be boolean series
        assert swing_highs.dtype == bool
        assert swing_lows.dtype == bool

    def test_trend_quality_bounds(self, sample_df):
        """
        Verify trend_quality is bounded between 0 and 1.
        """
        struct = StructureFeatures()
        result = struct.calculate_all(sample_df)

        quality = result['trend_quality'].dropna()

        assert quality.min() >= 0
        assert quality.max() <= 1

    def test_structural_bias_values(self, sample_df):
        """
        Verify structural_bias is -1, 0, or 1.
        """
        struct = StructureFeatures()
        result = struct.calculate_all(sample_df)

        bias = result['structural_bias'].dropna()
        unique_values = bias.unique()

        # Should only contain -1, 0, 1
        assert all(v in [-1, 0, 1] for v in unique_values)


# MTFFeatures Tests

class TestMTFFeatures:
    """Test MTFFeatures calculator"""

    def test_initialization(self):
        """
        Verify MTFFeatures initializes.
        """
        mtf = MTFFeatures()
        assert mtf is not None

    def test_calculate_all_with_1h_data(self, sample_df):
        """
        Verify calculate_all() with 1h data generates MTF features.
        """
        mtf = MTFFeatures()

        # Create 1h data by resampling
        df_1h = mtf._resample_to_1h(sample_df)

        result = mtf.calculate_all(sample_df, df_1h)

        # Verify all 10 MTF features
        assert 'mtf_trend_aligned' in result.columns
        assert 'htf_ema_trend' in result.columns
        assert 'mtf_rsi_diff' in result.columns
        assert 'mtf_momentum_agreement' in result.columns
        assert 'htf_adx' in result.columns
        assert 'htf_bb_position' in result.columns
        assert 'htf_macd_direction' in result.columns
        assert 'htf_volume_trend' in result.columns
        assert 'mtf_volatility_ratio' in result.columns
        assert 'mtf_score' in result.columns

    def test_calculate_all_without_1h_data(self, sample_df):
        """
        Verify calculate_all() works without explicit 1h data.

        Should auto-resample from 5m data.
        """
        mtf = MTFFeatures()
        result = mtf.calculate_all(sample_df, df_1h=None)

        # Should still generate MTF features
        assert 'mtf_trend_aligned' in result.columns
        assert 'mtf_score' in result.columns

    def test_resample_to_1h(self, sample_df):
        """
        Verify 5m to 1h resampling works.
        """
        mtf = MTFFeatures()
        df_1h = mtf._resample_to_1h(sample_df)

        # Should have fewer rows
        assert len(df_1h) < len(sample_df)

        # Should have OHLCV columns
        assert 'open' in df_1h.columns
        assert 'high' in df_1h.columns
        assert 'low' in df_1h.columns
        assert 'close' in df_1h.columns
        assert 'volume' in df_1h.columns

    def test_mtf_score_bounds(self, sample_df):
        """
        Verify mtf_score is bounded between 0 and 1.
        """
        mtf = MTFFeatures()
        result = mtf.calculate_all(sample_df)

        score = result['mtf_score'].dropna()

        assert score.min() >= 0
        assert score.max() <= 1


# FeaturePipeline Tests

class TestFeaturePipeline:
    """Test integrated FeaturePipeline"""

    def test_initialization(self):
        """
        Verify FeaturePipeline initializes all sub-components.
        """
        pipeline = FeaturePipeline()

        assert pipeline.technical is not None
        assert pipeline.structure is not None
        assert pipeline.mtf is not None
        assert isinstance(pipeline._cache, dict)

    def test_extract_features_generates_70_features(self, sample_candles_list):
        """
        Verify extract_features() generates 70 total features.

        Breakdown:
        - Technical: 50 features
        - Structure: 10 features
        - MTF: 10 features
        Total: 70 features
        """
        pipeline = FeaturePipeline()
        result = pipeline.extract_features(sample_candles_list)

        # Should return DataFrame
        assert isinstance(result, pd.DataFrame)

        # Get feature names
        feature_names = pipeline.get_feature_names()

        # Should have 70 features
        assert len(feature_names) == 70

        # All features should exist in result
        for feat in feature_names:
            assert feat in result.columns, f"Missing feature: {feat}"

    def test_extract_latest_features(self, sample_candles_list):
        """
        Verify extract_latest_features() returns dict of latest features.
        """
        pipeline = FeaturePipeline()
        result = pipeline.extract_latest_features(sample_candles_list)

        # Should return dict
        assert isinstance(result, dict)

        # Should contain feature values
        assert len(result) > 0

        # All values should be numeric
        for key, value in result.items():
            assert isinstance(value, (int, float, np.integer, np.floating))

    def test_empty_data_handling(self):
        """
        Verify pipeline handles empty data gracefully.
        """
        pipeline = FeaturePipeline()

        # Empty list
        result = pipeline.extract_features([])
        assert result.empty

        # Insufficient data
        short_data = [
            {'open': 100, 'high': 101, 'low': 99, 'close': 100.5, 'volume': 1000}
            for _ in range(10)
        ]
        result = pipeline.extract_features(short_data)
        assert result.empty or len(result) == 0

    def test_feature_caching(self, sample_candles_list):
        """
        Verify feature caching works.
        """
        pipeline = FeaturePipeline()

        # First call
        result1 = pipeline.extract_features(sample_candles_list, symbol="ETHUSDT")

        # Second call (should use cache)
        result2 = pipeline.extract_features(sample_candles_list, symbol="ETHUSDT")

        # Should return same data
        pd.testing.assert_frame_equal(result1, result2)

    def test_clear_cache(self, sample_candles_list):
        """
        Verify cache clearing works.
        """
        pipeline = FeaturePipeline()

        # Extract features (populate cache)
        pipeline.extract_features(sample_candles_list, symbol="ETHUSDT")

        assert len(pipeline._cache) > 0

        # Clear cache
        pipeline.clear_cache()

        assert len(pipeline._cache) == 0

    def test_nan_handling(self, sample_candles_list):
        """
        Verify NaN values are handled properly.
        """
        pipeline = FeaturePipeline()
        result = pipeline.extract_features(sample_candles_list)

        # Last row should have no NaN
        last_row = result.iloc[-1]
        assert not last_row.isnull().any(), "Last row contains NaN values"

        # Check for infinite values
        assert not np.isinf(result.iloc[-1]).any(), "Last row contains infinite values"

    def test_with_1h_candles(self, sample_candles_list):
        """
        Verify pipeline works with both 5m and 1h candles.
        """
        pipeline = FeaturePipeline()

        # Create simplified 1h candles (every 12th candle)
        candles_1h = sample_candles_list[::12]

        result = pipeline.extract_features(
            candles_5m=sample_candles_list,
            candles_1h=candles_1h,
            symbol="ETHUSDT"
        )

        assert not result.empty
        assert 'mtf_score' in result.columns


# Integration Tests

class TestFeatureIntegration:
    """Test feature pipeline integration scenarios"""

    def test_full_pipeline_execution(self, sample_candles_list):
        """
        Verify full pipeline executes without errors.
        """
        pipeline = FeaturePipeline()

        # Extract features
        df_features = pipeline.extract_features(sample_candles_list)

        # Get latest features
        latest_features = pipeline.extract_latest_features(sample_candles_list)

        # Verify consistency
        for feature_name in pipeline.get_feature_names():
            assert feature_name in df_features.columns
            assert feature_name in latest_features

    def test_feature_value_ranges(self, sample_candles_list):
        """
        Verify feature values are within reasonable ranges.
        """
        pipeline = FeaturePipeline()
        result = pipeline.extract_features(sample_candles_list)

        last_row = result.iloc[-1]

        # RSI should be 0-100
        assert 0 <= last_row['rsi_14'] <= 100

        # BB position should be 0-1 (approximately)
        assert 0 <= last_row['bb_position'] <= 2  # Allow some overshoot

        # ATR ratio should be positive
        assert last_row['atr_ratio'] >= 0

        # EMA cross should be 0 or 1
        assert last_row['ema_cross_5_20'] in [0, 1]

    def test_reproducibility(self, sample_candles_list):
        """
        Verify feature extraction is reproducible.
        """
        pipeline1 = FeaturePipeline()
        pipeline2 = FeaturePipeline()

        result1 = pipeline1.extract_features(sample_candles_list)
        result2 = pipeline2.extract_features(sample_candles_list)

        # Should produce identical results
        pd.testing.assert_frame_equal(result1, result2)
