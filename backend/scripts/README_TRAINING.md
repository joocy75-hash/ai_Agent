# ML Model Training Guide

## Quick Start

### 1. Set Environment Variables

```bash
export BITGET_API_KEY="your_api_key"
export BITGET_API_SECRET="your_api_secret"
export BITGET_PASSPHRASE="your_passphrase"
```

### 2. Run Training

```bash
# Basic training (30 days of data)
python scripts/train_ml_models.py --symbol ETHUSDT

# Extended training (60 days)
python scripts/train_ml_models.py --days 60 --symbol ETHUSDT

# Custom parameters
python scripts/train_ml_models.py \
  --symbol ETHUSDT \
  --days 30 \
  --num-boost-round 1000 \
  --early-stopping-rounds 100 \
  --test-size 0.2
```

## Script Options

| Option | Default | Description |
|--------|---------|-------------|
| `--symbol` | ETHUSDT | Trading symbol |
| `--days` | 30 | Days of historical data |
| `--days-5m` | - | Days of 5m data (overrides --days) |
| `--days-1h` | - | Days of 1h data (overrides --days) |
| `--test-size` | 0.2 | Validation split ratio |
| `--num-boost-round` | 500 | LightGBM boosting rounds |
| `--early-stopping-rounds` | 50 | Early stopping patience |
| `--models-dir` | src/ml/saved_models | Output directory for models |
| `--data-dir` | src/ml/data | Data cache directory |
| `--dry-run` | False | Test mode (use cached data, skip training) |

## Training Pipeline Steps

### Step 1: Data Collection
- Fetches historical candle data from Bitget API
- Collects both 5m and 1h timeframes
- Saves data to cache directory

### Step 2: Feature Extraction
- Extracts 70 features from raw OHLCV data
- 50 technical indicators
- 10 structural features
- 10 multi-timeframe features
- Handles NaN values

### Step 3: Label Generation
- Creates labels for all 5 models:
  1. **Direction**: 0=down, 1=neutral, 2=up
  2. **Volatility**: 0=low, 1=normal, 2=high, 3=extreme
  3. **Timing**: 0=bad, 1=ok, 2=good
  4. **StopLoss**: Optimal SL percentage (regression)
  5. **PositionSize**: Optimal position size (regression)

### Step 4: Model Training
- Trains all 5 LightGBM models
- Uses time-based train/validation split
- Applies early stopping
- Saves feature importance

### Step 5: Model Saving
- Saves trained models to `saved_models/`
- Saves feature importance CSVs
- Format: `{model_name}_model.txt`, `{model_name}_feature_importance.csv`

## Output Files

After successful training, you'll find:

```
backend/src/ml/saved_models/
├── direction_model.txt
├── direction_feature_importance.csv
├── volatility_model.txt
├── volatility_feature_importance.csv
├── timing_model.txt
├── timing_feature_importance.csv
├── stop_loss_model.txt
├── stop_loss_feature_importance.csv
├── position_size_model.txt
└── position_size_feature_importance.csv
```

## Logs

Training logs are saved to:
- Console output: Real-time progress
- File: `backend/logs/training.log`

## Dry Run Mode

Test the pipeline without collecting data or training:

```bash
python scripts/train_ml_models.py --dry-run
```

This will:
- Use previously cached data
- Extract features and generate labels
- Skip actual model training
- Useful for testing feature extraction pipeline

## Example Output

```
================================================================================
STEP 1: Data Collection
================================================================================
Collecting 30 days of 5m candles for ETHUSDT...
Collected 8640 5m candles
Collecting 30 days of 1h candles for ETHUSDT...
Collected 720 1h candles

Data Collection Summary:
  5m candles: 8640
  1h candles: 720
  Date range: 2024-11-21 to 2024-12-21

================================================================================
STEP 2: Feature Extraction
================================================================================
Extracting 70 features (50 technical + 10 structure + 10 MTF)...
Extracted features: 8640 rows, 70 columns
NaN values handled: 500 -> 0

================================================================================
STEP 3: Label Generation
================================================================================
Generating all 5 labels...
Labeled data: 8634 samples

Label Distribution:
  Direction (0=down, 1=neutral, 2=up):
    down: 2890 (33.5%)
    neutral: 2856 (33.1%)
    up: 2888 (33.4%)

  StopLoss (regression):
    mean: 1.52%
    std: 0.85%
    range: 0.50% - 5.00%

================================================================================
STEP 4: Model Training
================================================================================
Training with 70 features
Train/Val split: 80/20

Training Results:
  DIRECTION:
    accuracy: 0.4523
    best_iteration: 342

  STOP_LOSS:
    rmse: 0.6234
    mae: 0.4512
    best_iteration: 398

================================================================================
STEP 5: Save Models
================================================================================
Saved direction model to .../direction_model.txt
Saved volatility model to .../volatility_model.txt
...

Top 10 Features by Model:

  DIRECTION:
    ema_20: 1523
    rsi_14: 1234
    macd_histogram: 987
    ...

================================================================================
TRAINING COMPLETE
================================================================================

Total time: 342.5 seconds
```

## Troubleshooting

### No Bitget credentials
```
ERROR: Bitget credentials not found in environment
Set BITGET_API_KEY, BITGET_API_SECRET, BITGET_PASSPHRASE
```

Solution: Export environment variables before running

### Insufficient data
```
WARNING: Insufficient data: 10 candles
```

Solution: Increase --days parameter or check Bitget API

### LightGBM not installed
```
ERROR: LightGBM not installed. Training will be disabled.
```

Solution: Install LightGBM
```bash
pip install lightgbm
```

### Memory issues
If you run out of memory with large datasets:
- Reduce --days parameter
- Reduce --num-boost-round
- Use a machine with more RAM

## Integration with Trading Bot

After training, models are automatically available to:
- ML Predictor Agent (`backend/src/agents/ml_predictor/agent.py`)
- Model Inference Engine (`backend/src/ml/inference/model_inference.py`)

No additional configuration needed - models are loaded from `saved_models/` directory.

## Retraining Schedule

Recommended retraining frequency:
- **Weekly**: For active markets (ETH, BTC)
- **Bi-weekly**: For stable markets
- **Monthly**: For low-volatility periods

Always retrain after:
- Major market regime changes
- Extended downtime
- Model performance degradation

## Advanced Usage

### Train multiple symbols
```bash
for symbol in ETHUSDT BTCUSDT SOLUSDT; do
  python scripts/train_ml_models.py --symbol $symbol --days 30
done
```

### Custom train/val split
```bash
python scripts/train_ml_models.py --test-size 0.15  # 85/15 split
```

### Longer training for better accuracy
```bash
python scripts/train_ml_models.py \
  --num-boost-round 2000 \
  --early-stopping-rounds 200
```
