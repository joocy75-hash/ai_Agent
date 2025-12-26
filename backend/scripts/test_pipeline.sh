#!/bin/bash
#
# ML Model Test Script
# 학습된 모델이 제대로 작동하는지 테스트
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find Python
if [ -f "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11" ]; then
    PYTHON="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11"
else
    PYTHON="python3"
fi

echo "=========================================="
echo "   ML Model Test"
echo "=========================================="
echo ""

cd "$PROJECT_ROOT"

$PYTHON << 'EOF'
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path.cwd()))

print("1. Loading EnsemblePredictor...")
from src.ml.models import EnsemblePredictor

predictor = EnsemblePredictor()
print(f"   Models loaded: {predictor.models_loaded}")
print(f"   Available models: {list(predictor.models.keys())}")

if not predictor.models_loaded:
    print("\n   ❌ Models not loaded. Run training first.")
    sys.exit(1)

print("\n2. Testing with sample data...")
from src.ml.features import FeaturePipeline
import asyncio
import aiohttp

async def get_test_data(granularity, limit):
    """공개 API로 테스트 데이터 가져오기"""
    url = "https://api.bitget.com/api/v2/mix/market/candles"
    params = {
        "symbol": "ETHUSDT",
        "productType": "USDT-FUTURES",
        "granularity": granularity,
        "limit": str(limit)
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            candles = []
            for c in data.get("data", []):
                candles.append({
                    "timestamp": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5])
                })
            return candles

# 5분봉 + 1시간봉 데이터 가져오기 (MTF 피처용)
async def fetch_all():
    candles_5m = await get_test_data("5m", 200)
    candles_1h = await get_test_data("1H", 200)
    return candles_5m, candles_1h

candles_5m, candles_1h = asyncio.run(fetch_all())
print(f"   Fetched {len(candles_5m)} 5m candles, {len(candles_1h)} 1h candles")

# 피처 추출
print("\n3. Extracting features...")
pipeline = FeaturePipeline()
features_df = pipeline.extract_features(candles_5m, candles_1h, symbol="ETHUSDT")
print(f"   Features: {len(features_df.columns)} columns, {len(features_df)} rows")

# 예측
print("\n4. Running prediction...")
result = predictor.predict(features_df, symbol="ETHUSDT")

print(f"\n   ✅ Prediction Result:")
print(f"      Direction: {result.direction.direction.value}")
print(f"      Direction Confidence: {result.direction.confidence:.2f}")
print(f"      Volatility: {result.volatility.level.value}")
print(f"      Volatility Risk Score: {result.volatility.risk_score:.1f}")
print(f"      Timing Score: {result.timing.score:.1f}")
print(f"      Is Good Entry: {result.timing.is_good_entry}")
print(f"      Stop Loss: {result.stoploss.optimal_sl_percent:.2f}%")
print(f"      Position Size: {result.position_size.optimal_size_percent:.2f}%")
print(f"      Combined Confidence: {result.combined_confidence:.2f}")
print(f"      Should Skip Entry: {result.should_skip_entry()}")

print("\n==========================================")
print("   ✅ All Tests Passed!")
print("==========================================")
EOF

echo ""
echo "Done!"
