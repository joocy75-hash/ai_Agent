"""
Unit tests for ETH AI Fusion Strategy
Tests core trading logic without external dependencies
"""
import pytest
from unittest.mock import MagicMock, patch


# Test data
SAMPLE_CANDLES = [
    {"open": 3000, "high": 3050, "low": 2980, "close": 3020, "volume": 1000}
    for _ in range(100)
]


class TestETHAIFusionStrategy:
    """Test suite for ETH AI Fusion Strategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create strategy instance with ML disabled for unit testing"""
        with patch.dict('sys.modules', {'src.ml.features': MagicMock(), 'src.ml.models': MagicMock()}):
            from src.strategies.eth_ai_fusion_strategy import ETHAIFusionStrategy
            return ETHAIFusionStrategy(
                params={"enable_ml": False, "enable_sentiment": False},
                user_id=1
            )
    
    def test_strategy_initialization(self, strategy):
        """Test strategy initializes with correct defaults"""
        assert strategy.symbol == "ETH/USDT"
        assert strategy.timeframe == "5m"
        assert strategy._entry_threshold == 5.0
        assert strategy._max_adds == 3
    
    def test_hold_on_insufficient_candles(self, strategy):
        """Test returns hold when not enough candles"""
        result = strategy.generate_signal(3000.0, [], None)
        assert result["action"] == "hold"
        assert result["reason"] == "insufficient_candles"
    
    def test_ema_calculation(self, strategy):
        """Test EMA calculation is correct"""
        values = [100, 102, 104, 103, 105, 107, 106, 108, 110, 109]
        ema = strategy._ema(values, 5)
        assert isinstance(ema, float)
        assert ema > 0
    
    def test_rsi_calculation(self, strategy):
        """Test RSI calculation returns valid range"""
        closes = [100 + i for i in range(20)]
        rsi = strategy._rsi(closes, 14)
        assert 0 <= rsi <= 100
    
    def test_atr_percent_calculation(self, strategy):
        """Test ATR percent calculation"""
        highs = [105, 106, 107, 108, 109] * 4
        lows = [95, 96, 97, 98, 99] * 4
        closes = [100, 101, 102, 103, 104] * 4
        atr = strategy._atr_percent(highs, lows, closes, 14)
        assert atr > 0
    
    def test_pnl_percent_long(self, strategy):
        """Test PnL calculation for long position"""
        pnl = strategy._pnl_percent("long", 100.0, 110.0, 10)
        assert pnl == 100.0  # 10% * 10x leverage = 100%
    
    def test_pnl_percent_short(self, strategy):
        """Test PnL calculation for short position"""
        pnl = strategy._pnl_percent("short", 100.0, 90.0, 10)
        assert pnl == 100.0  # 10% * 10x leverage = 100%
    
    def test_hold_signal_structure(self, strategy):
        """Test hold signal has correct structure"""
        result = strategy._hold("test_reason")
        assert result["action"] == "hold"
        assert result["confidence"] == 0.0
        assert result["reason"] == "test_reason"
        assert result["strategy_type"] == "eth_ai_fusion"
    
    def test_close_signal_structure(self, strategy):
        """Test close signal has correct structure"""
        result = strategy._close("stop_loss", 2.0, 4.0)
        assert result["action"] == "close"
        assert result["confidence"] == 0.7
        assert result["stop_loss"] == 2.0
        assert result["take_profit"] == 4.0


class TestIndicatorCalculations:
    """Test indicator calculation methods"""
    
    @pytest.fixture
    def strategy(self):
        with patch.dict('sys.modules', {'src.ml.features': MagicMock(), 'src.ml.models': MagicMock()}):
            from src.strategies.eth_ai_fusion_strategy import ETHAIFusionStrategy
            return ETHAIFusionStrategy(
                params={"enable_ml": False, "enable_sentiment": False},
                user_id=1
            )
    
    def test_volume_ratio_normal(self, strategy):
        """Test volume ratio with normal data"""
        volumes = [100] * 20 + [150]  # Last volume is 1.5x average
        ratio = strategy._volume_ratio(volumes, 20)
        assert 1.4 <= ratio <= 1.6
    
    def test_volume_ratio_empty(self, strategy):
        """Test volume ratio with empty data"""
        ratio = strategy._volume_ratio([], 20)
        assert ratio == 1.0
    
    def test_macd_hist_calculation(self, strategy):
        """Test MACD histogram calculation"""
        closes = [100 + i * 0.5 for i in range(50)]  # Uptrend
        macd = strategy._macd_hist(closes)
        assert isinstance(macd, float)


class TestRiskManagement:
    """Test risk management functions"""
    
    @pytest.fixture
    def strategy(self):
        with patch.dict('sys.modules', {'src.ml.features': MagicMock(), 'src.ml.models': MagicMock()}):
            from src.strategies.eth_ai_fusion_strategy import ETHAIFusionStrategy
            return ETHAIFusionStrategy(
                params={"enable_ml": False, "enable_sentiment": False},
                user_id=1
            )
    
    def test_risk_targets_within_bounds(self, strategy):
        """Test risk targets stay within configured bounds"""
        from src.strategies.eth_ai_fusion_strategy import IndicatorSnapshot
        snapshot = IndicatorSnapshot(
            close=3000, ema_fast=3010, ema_slow=2990,
            ema_trend=2950, rsi=55, macd_hist=10,
            atr_percent=2.0, volume_ratio=1.2
        )
        sl, tp = strategy._risk_targets(snapshot, None)
        
        assert strategy._min_stop_loss <= sl <= strategy._max_stop_loss
        assert strategy._min_take_profit <= tp <= strategy._max_take_profit
        assert tp >= sl * strategy._min_rr_ratio  # R/R ratio check
