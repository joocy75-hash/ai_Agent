#!/usr/bin/env python3
"""
ML Model Training Script

Complete training pipeline for all 5 LightGBM models:
1. Direction Model (Classifier): 방향 예측
2. Volatility Model (Classifier): 변동성 레벨
3. Timing Model (Classifier): 진입 타이밍
4. StopLoss Model (Regressor): 최적 SL
5. PositionSize Model (Regressor): 최적 사이즈

Usage:
    python scripts/train_ml_models.py --days 30 --symbol ETHUSDT
    python scripts/train_ml_models.py --days 60 --symbol BTCUSDT --dry-run
    python scripts/train_ml_models.py --days 30 --symbol ETHUSDT --num-boost-round 1000
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ml.training.data_collector import DataCollector
from ml.training.labeler import Labeler
from ml.training.train_all_models import ModelTrainer
from ml.features.feature_pipeline import FeaturePipeline
from services.bitget_rest import BitgetRestClient
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / 'logs' / 'training.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


class TrainingPipeline:
    """Complete ML Training Pipeline"""

    def __init__(
        self,
        symbol: str = "ETHUSDT",
        days_5m: int = 30,
        days_1h: int = 30,
        dry_run: bool = False,
        models_dir: Optional[Path] = None,
        data_dir: Optional[Path] = None,
    ):
        self.symbol = symbol
        self.days_5m = days_5m
        self.days_1h = days_1h
        self.dry_run = dry_run

        # Directories
        self.models_dir = models_dir or project_root / "src" / "ml" / "saved_models"
        self.data_dir = data_dir or project_root / "src" / "ml" / "data"
        self.logs_dir = project_root / "logs"

        # Create directories
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Components
        self.bitget_client = None
        self.data_collector = DataCollector(data_dir=self.data_dir)
        self.feature_pipeline = FeaturePipeline()
        self.labeler = Labeler()
        self.model_trainer = ModelTrainer(models_dir=self.models_dir)

        logger.info(f"TrainingPipeline initialized for {symbol}")
        logger.info(f"Models dir: {self.models_dir}")
        logger.info(f"Data dir: {self.data_dir}")
        logger.info(f"Dry run: {dry_run}")

    async def initialize_bitget_client(self):
        """Initialize Bitget REST client for data collection"""
        # Get credentials from environment
        api_key = os.getenv("BITGET_API_KEY", "")
        api_secret = os.getenv("BITGET_API_SECRET", "")
        passphrase = os.getenv("BITGET_PASSPHRASE", "")

        if not all([api_key, api_secret, passphrase]):
            logger.warning("Bitget credentials not found in environment")
            logger.warning("Data collection will be skipped. Set BITGET_API_KEY, BITGET_API_SECRET, BITGET_PASSPHRASE")
            return False

        self.bitget_client = BitgetRestClient(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase
        )
        self.data_collector.set_client(self.bitget_client)

        logger.info("Bitget client initialized")
        return True

    async def step1_collect_data(self):
        """Step 1: Collect historical data"""
        logger.info("=" * 80)
        logger.info("STEP 1: Data Collection")
        logger.info("=" * 80)

        if self.dry_run:
            logger.info("[DRY RUN] Skipping data collection")
            # Try to load existing data
            df_5m = self.data_collector.load_data(self.symbol, "5m")
            df_1h = self.data_collector.load_data(self.symbol, "1h")

            if df_5m.empty or df_1h.empty:
                logger.error("No existing data found for dry run")
                return None, None

            logger.info(f"Loaded existing data: 5m={len(df_5m)}, 1h={len(df_1h)}")
            return df_5m, df_1h

        # Collect 5m candles
        logger.info(f"Collecting {self.days_5m} days of 5m candles for {self.symbol}...")
        df_5m = await self.data_collector.collect_historical(
            symbol=self.symbol,
            timeframe="5m",
            days=self.days_5m,
            save=True
        )

        if df_5m.empty:
            logger.error("Failed to collect 5m data")
            return None, None

        logger.info(f"Collected {len(df_5m)} 5m candles")

        # Collect 1h candles
        logger.info(f"Collecting {self.days_1h} days of 1h candles for {self.symbol}...")
        df_1h = await self.data_collector.collect_historical(
            symbol=self.symbol,
            timeframe="1h",
            days=self.days_1h,
            save=True
        )

        if df_1h.empty:
            logger.error("Failed to collect 1h data")
            return None, None

        logger.info(f"Collected {len(df_1h)} 1h candles")

        # Summary
        logger.info(f"\nData Collection Summary:")
        logger.info(f"  5m candles: {len(df_5m)}")
        logger.info(f"  1h candles: {len(df_1h)}")
        logger.info(f"  Date range: {df_5m.index[0]} to {df_5m.index[-1]}")

        return df_5m, df_1h

    def step2_extract_features(self, df_5m, df_1h):
        """Step 2: Extract features"""
        logger.info("=" * 80)
        logger.info("STEP 2: Feature Extraction")
        logger.info("=" * 80)

        # Convert to list of dicts for feature pipeline
        candles_5m = df_5m.reset_index().to_dict('records')
        candles_1h = df_1h.reset_index().to_dict('records') if df_1h is not None else None

        # Extract features
        logger.info("Extracting 70 features (50 technical + 10 structure + 10 MTF)...")
        df_features = self.feature_pipeline.extract_features(
            candles_5m=candles_5m,
            candles_1h=candles_1h,
            symbol=self.symbol
        )

        if df_features.empty:
            logger.error("Feature extraction failed")
            return None

        # Handle NaN values
        nan_count_before = df_features.isna().sum().sum()
        df_features = df_features.ffill().bfill().fillna(0)
        nan_count_after = df_features.isna().sum().sum()

        logger.info(f"Extracted features: {len(df_features)} rows, {len(df_features.columns)} columns")
        logger.info(f"NaN values handled: {nan_count_before} -> {nan_count_after}")

        # Feature summary
        feature_names = self.feature_pipeline.get_feature_names()
        logger.info(f"\nFeature Groups:")
        logger.info(f"  Total features: {len(feature_names)}")

        return df_features

    def step3_generate_labels(self, df_features):
        """Step 3: Generate labels"""
        logger.info("=" * 80)
        logger.info("STEP 3: Label Generation")
        logger.info("=" * 80)

        logger.info("Generating all 5 labels...")
        df_labeled = self.labeler.generate_all_labels(df_features)

        if df_labeled.empty:
            logger.error("Label generation failed")
            return None

        # Get label statistics
        stats = self.labeler.get_label_stats(df_labeled)

        logger.info(f"\nLabeled data: {len(df_labeled)} samples")
        logger.info("\nLabel Distribution:")

        # Direction
        if 'direction' in stats:
            logger.info(f"  Direction (0=down, 1=neutral, 2=up):")
            for key, value in stats['direction'].items():
                pct = value / len(df_labeled) * 100
                logger.info(f"    {key}: {value} ({pct:.1f}%)")

        # Volatility
        if 'volatility' in stats:
            logger.info(f"  Volatility (0=low, 1=normal, 2=high, 3=extreme):")
            for key, value in stats['volatility'].items():
                pct = value / len(df_labeled) * 100
                logger.info(f"    {key}: {value} ({pct:.1f}%)")

        # Timing
        if 'timing' in stats:
            logger.info(f"  Timing (0=bad, 1=ok, 2=good):")
            for key, value in stats['timing'].items():
                pct = value / len(df_labeled) * 100
                logger.info(f"    {key}: {value} ({pct:.1f}%)")

        # StopLoss
        if 'stop_loss' in stats:
            logger.info(f"  StopLoss (regression):")
            logger.info(f"    mean: {stats['stop_loss']['mean']:.2f}%")
            logger.info(f"    std: {stats['stop_loss']['std']:.2f}%")
            logger.info(f"    range: {stats['stop_loss']['min']:.2f}% - {stats['stop_loss']['max']:.2f}%")

        # PositionSize
        if 'position_size' in stats:
            logger.info(f"  PositionSize (regression):")
            logger.info(f"    mean: {stats['position_size']['mean']:.2f}%")
            logger.info(f"    std: {stats['position_size']['std']:.2f}%")
            logger.info(f"    range: {stats['position_size']['min']:.2f}% - {stats['position_size']['max']:.2f}%")

        return df_labeled

    def step4_train_models(
        self,
        df_labeled,
        test_size: float = 0.2,
        num_boost_round: int = 500,
        early_stopping_rounds: int = 50
    ):
        """Step 4: Train all models"""
        logger.info("=" * 80)
        logger.info("STEP 4: Model Training")
        logger.info("=" * 80)

        if self.dry_run:
            logger.info("[DRY RUN] Skipping model training")
            return {}

        # Get feature columns (exclude label columns)
        exclude_cols = [
            'label_direction', 'label_volatility', 'label_timing',
            'label_stop_loss', 'label_position_size',
            'future_return', 'atr_pct', 'timing_efficiency',
            'open', 'high', 'low', 'close', 'volume'
        ]
        feature_columns = [col for col in df_labeled.columns if col not in exclude_cols]

        logger.info(f"Training with {len(feature_columns)} features")
        logger.info(f"Train/Val split: {int((1-test_size)*100)}/{int(test_size*100)}")
        logger.info(f"Boosting rounds: {num_boost_round}")
        logger.info(f"Early stopping: {early_stopping_rounds}")

        # Train all models
        results = self.model_trainer.train_all(
            df=df_labeled,
            feature_columns=feature_columns,
            test_size=test_size,
            num_boost_round=num_boost_round,
            early_stopping_rounds=early_stopping_rounds
        )

        # Print results
        logger.info("\nTraining Results:")
        for model_name, metrics in results.items():
            logger.info(f"  {model_name.upper()}:")
            for key, value in metrics.items():
                if isinstance(value, float):
                    logger.info(f"    {key}: {value:.4f}")
                else:
                    logger.info(f"    {key}: {value}")

        return results

    def step5_save_models(self):
        """Step 5: Save models and feature importance"""
        logger.info("=" * 80)
        logger.info("STEP 5: Save Models")
        logger.info("=" * 80)

        if self.dry_run:
            logger.info("[DRY RUN] Skipping model saving")
            return

        self.model_trainer.save_all()

        # List saved files
        logger.info("\nSaved files:")
        for file in sorted(self.models_dir.glob("*")):
            logger.info(f"  {file.name}")

        # Print feature importance summary
        logger.info("\nTop 10 Features by Model:")
        for model_name, fi_df in self.model_trainer.feature_importance.items():
            logger.info(f"\n  {model_name.upper()}:")
            top_10 = fi_df.head(10)
            for idx, row in top_10.iterrows():
                logger.info(f"    {row['feature']}: {row['importance']:.0f}")

    def print_summary(self, results):
        """Print final summary"""
        logger.info("=" * 80)
        logger.info("TRAINING COMPLETE")
        logger.info("=" * 80)

        logger.info(f"\nSymbol: {self.symbol}")
        logger.info(f"Training Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Models Directory: {self.models_dir}")

        if results:
            logger.info("\nModels Trained:")
            for model_name in results.keys():
                logger.info(f"  - {model_name}")

        logger.info("\nNext Steps:")
        logger.info("  1. Review feature importance files")
        logger.info("  2. Test models with inference script")
        logger.info("  3. Integrate with ML Predictor Agent")
        logger.info("  4. Run backtests to validate performance")

    async def run(
        self,
        test_size: float = 0.2,
        num_boost_round: int = 500,
        early_stopping_rounds: int = 50
    ):
        """Run complete training pipeline"""
        start_time = datetime.now()

        try:
            # Initialize Bitget client
            client_ready = await self.initialize_bitget_client()
            if not client_ready and not self.dry_run:
                logger.error("Cannot proceed without Bitget credentials")
                return False

            # Step 1: Collect data
            df_5m, df_1h = await self.step1_collect_data()
            if df_5m is None:
                return False

            # Step 2: Extract features
            df_features = self.step2_extract_features(df_5m, df_1h)
            if df_features is None:
                return False

            # Step 3: Generate labels
            df_labeled = self.step3_generate_labels(df_features)
            if df_labeled is None:
                return False

            # Step 4: Train models
            results = self.step4_train_models(
                df_labeled,
                test_size=test_size,
                num_boost_round=num_boost_round,
                early_stopping_rounds=early_stopping_rounds
            )

            # Step 5: Save models
            self.step5_save_models()

            # Summary
            self.print_summary(results)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"\nTotal time: {elapsed:.1f} seconds")

            return True

        except Exception as e:
            logger.error(f"Training pipeline failed: {e}", exc_info=True)
            return False


def main():
    parser = argparse.ArgumentParser(description="Train ML Models for Trading")

    # Data collection
    parser.add_argument(
        "--symbol",
        type=str,
        default="ETHUSDT",
        help="Trading symbol (default: ETHUSDT)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Days of data to collect (default: 30)"
    )
    parser.add_argument(
        "--days-5m",
        type=int,
        help="Days of 5m data (overrides --days)"
    )
    parser.add_argument(
        "--days-1h",
        type=int,
        help="Days of 1h data (overrides --days)"
    )

    # Training parameters
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Validation split ratio (default: 0.2)"
    )
    parser.add_argument(
        "--num-boost-round",
        type=int,
        default=500,
        help="Number of boosting rounds (default: 500)"
    )
    parser.add_argument(
        "--early-stopping-rounds",
        type=int,
        default=50,
        help="Early stopping rounds (default: 50)"
    )

    # Directories
    parser.add_argument(
        "--models-dir",
        type=Path,
        help="Models output directory"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Data cache directory"
    )

    # Dry run
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (use existing data, skip training)"
    )

    args = parser.parse_args()

    # Resolve days
    days_5m = args.days_5m or args.days
    days_1h = args.days_1h or args.days

    # Create pipeline
    pipeline = TrainingPipeline(
        symbol=args.symbol,
        days_5m=days_5m,
        days_1h=days_1h,
        dry_run=args.dry_run,
        models_dir=args.models_dir,
        data_dir=args.data_dir
    )

    # Run
    success = asyncio.run(pipeline.run(
        test_size=args.test_size,
        num_boost_round=args.num_boost_round,
        early_stopping_rounds=args.early_stopping_rounds
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
