"""
Integration tests for BacktestEngine.

Tests:
1. Basic backtest with SimpleOpenClose strategy
2. RSI strategy with different parameters
3. Error handling (missing CSV, invalid data)
4. Metrics calculation
5. Trade recording
"""
import os
import sys
import tempfile
import csv

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.backtest_engine import BacktestEngine
from src.services.strategies.eth_ai_fusion import EthAIFusionBacktestStrategy


def create_temp_csv(data):
    """Create a temporary CSV file with given data."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
    writer = csv.DictWriter(temp_file, fieldnames=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    writer.writeheader()
    writer.writerows(data)
    temp_file.close()
    return temp_file.name


def test_eth_ai_fusion_strategy_basic():
    """Test basic backtest with EthAIFusionBacktestStrategy."""
    print("\n=== Test 1: Simple Strategy Basic ===")

    # Create test data
    test_data = [
        {'timestamp': '2025-01-01 00:00:00', 'open': 100.0, 'high': 105.0, 'low': 99.0, 'close': 103.0, 'volume': 1000},
        {'timestamp': '2025-01-01 01:00:00', 'open': 103.0, 'high': 107.0, 'low': 102.0, 'close': 106.0, 'volume': 1100},
        {'timestamp': '2025-01-01 02:00:00', 'open': 106.0, 'high': 108.0, 'low': 104.0, 'close': 105.0, 'volume': 900},
        {'timestamp': '2025-01-01 03:00:00', 'open': 105.0, 'high': 106.0, 'low': 102.0, 'close': 103.0, 'volume': 1200},
        {'timestamp': '2025-01-01 04:00:00', 'open': 103.0, 'high': 105.0, 'low': 101.0, 'close': 104.0, 'volume': 1050},
    ]

    csv_path = create_temp_csv(test_data)

    try:
        strategy = EthAIFusionBacktestStrategy()
        engine = BacktestEngine(strategy=strategy)

        result = engine.run({
            'csv_path': csv_path,
            'initial_balance': 1000.0,
            'fee_rate': 0.001,
            'slippage': 0.0005,
        })

        print(f"✅ Final Balance: {result['final_balance']:.2f}")
        print(f"✅ Number of Trades: {len(result['trades'])}")
        print(f"✅ Equity Curve Length: {len(result['equity_curve'])}")
        print(f"✅ Metrics: {result['metrics']}")

        assert 'final_balance' in result
        assert 'trades' in result
        assert 'equity_curve' in result
        assert 'metrics' in result
        assert len(result['equity_curve']) == len(test_data)

        print("✅ Test 1 PASSED")
        return True

    finally:
        os.unlink(csv_path)


def test_eth_ai_fusion_strategy_extended():
    """Test EthAIFusionBacktestStrategy with extended data."""
    print("\n=== Test 2: RSI Strategy ===")

    # Create test data with trend (20 candles for RSI warmup)
    test_data = []
    base_price = 100.0
    for i in range(30):
        # Create uptrend then downtrend
        if i < 15:
            close = base_price + i * 2
        else:
            close = base_price + (30 - i) * 2

        test_data.append({
            'timestamp': f'2025-01-01 {i:02d}:00:00',
            'open': close - 1,
            'high': close + 2,
            'low': close - 2,
            'close': close,
            'volume': 1000 + i * 10,
        })

    csv_path = create_temp_csv(test_data)

    try:
        strategy = EthAIFusionBacktestStrategy()
        engine = BacktestEngine(strategy=strategy)

        result = engine.run({
            'csv_path': csv_path,
            'initial_balance': 10000.0,
            'fee_rate': 0.001,
            'slippage': 0.0005,
        })

        print(f"✅ Final Balance: {result['final_balance']:.2f}")
        print(f"✅ Number of Trades: {len(result['trades'])}")
        print(f"✅ Total Return: {result['metrics']['total_return']:.4f}")
        print(f"✅ Max Drawdown: {result['metrics']['max_drawdown']:.4f}")
        print(f"✅ Win Rate: {result['metrics']['win_rate']:.2%}")

        assert result['final_balance'] > 0
        assert len(result['equity_curve']) == len(test_data)

        print("✅ Test 2 PASSED")
        return True

    finally:
        os.unlink(csv_path)


def test_error_handling_missing_csv():
    """Test error handling for missing CSV file."""
    print("\n=== Test 3: Error Handling - Missing CSV ===")

    strategy = EthAIFusionBacktestStrategy()
    engine = BacktestEngine(strategy=strategy)

    try:
        result = engine.run({
            'csv_path': '/nonexistent/path/to/file.csv',
            'initial_balance': 1000.0,
        })
        print("❌ Test 3 FAILED - Should have raised FileNotFoundError")
        return False
    except FileNotFoundError as e:
        print(f"✅ Correctly caught FileNotFoundError: {e}")
        print("✅ Test 3 PASSED")
        return True


def test_empty_csv():
    """Test handling of empty CSV file."""
    print("\n=== Test 4: Empty CSV ===")

    test_data = []
    csv_path = create_temp_csv(test_data)

    try:
        strategy = EthAIFusionBacktestStrategy()
        engine = BacktestEngine(strategy=strategy)

        result = engine.run({
            'csv_path': csv_path,
            'initial_balance': 1000.0,
        })

        print(f"✅ Final Balance: {result['final_balance']}")
        print(f"✅ Number of Trades: {len(result['trades'])}")

        # With no candles, should have no trades and balance unchanged
        assert result['final_balance'] == 1000.0
        assert len(result['trades']) == 0

        print("✅ Test 4 PASSED")
        return True

    finally:
        os.unlink(csv_path)


def test_metrics_calculation():
    """Test that metrics are calculated correctly."""
    print("\n=== Test 5: Metrics Calculation ===")

    # Create data that should generate some trades
    test_data = [
        {'timestamp': '2025-01-01 00:00:00', 'open': 100.0, 'high': 102.0, 'low': 99.0, 'close': 101.0, 'volume': 1000},
        {'timestamp': '2025-01-01 01:00:00', 'open': 101.0, 'high': 103.0, 'low': 100.0, 'close': 102.0, 'volume': 1000},
        {'timestamp': '2025-01-01 02:00:00', 'open': 102.0, 'high': 104.0, 'low': 101.0, 'close': 103.0, 'volume': 1000},
        {'timestamp': '2025-01-01 03:00:00', 'open': 103.0, 'high': 104.0, 'low': 101.0, 'close': 102.0, 'volume': 1000},
        {'timestamp': '2025-01-01 04:00:00', 'open': 102.0, 'high': 103.0, 'low': 100.0, 'close': 101.0, 'volume': 1000},
        {'timestamp': '2025-01-01 05:00:00', 'open': 101.0, 'high': 102.0, 'low': 99.0, 'close': 100.0, 'volume': 1000},
    ]

    csv_path = create_temp_csv(test_data)

    try:
        strategy = EthAIFusionBacktestStrategy()
        engine = BacktestEngine(strategy=strategy)

        result = engine.run({
            'csv_path': csv_path,
            'initial_balance': 1000.0,
        })

        metrics = result['metrics']

        print(f"✅ Total Return: {metrics['total_return']:.4f}")
        print(f"✅ Max Drawdown: {metrics['max_drawdown']:.4f}")
        print(f"✅ Win Rate: {metrics['win_rate']:.2%}")
        print(f"✅ Number of Trades: {metrics['number_of_trades']}")

        # Verify metrics structure
        assert 'total_return' in metrics
        assert 'max_drawdown' in metrics
        assert 'win_rate' in metrics
        assert 'number_of_trades' in metrics

        # Verify metrics are numeric
        assert isinstance(metrics['total_return'], (int, float))
        assert isinstance(metrics['max_drawdown'], (int, float))
        assert isinstance(metrics['win_rate'], (int, float))
        assert isinstance(metrics['number_of_trades'], int)

        # Verify win rate is between 0 and 1
        assert 0 <= metrics['win_rate'] <= 1

        print("✅ Test 5 PASSED")
        return True

    finally:
        os.unlink(csv_path)


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("BACKTEST ENGINE INTEGRATION TESTS")
    print("=" * 60)

    tests = [
        ("Simple Strategy Basic", test_simple_strategy_basic),
        ("RSI Strategy", test_rsi_strategy),
        ("Error Handling - Missing CSV", test_error_handling_missing_csv),
        ("Empty CSV", test_empty_csv),
        ("Metrics Calculation", test_metrics_calculation),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"❌ Test '{name}' FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    print("=" * 60)

    return passed_count == total_count


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
