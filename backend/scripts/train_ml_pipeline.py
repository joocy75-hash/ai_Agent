#!/usr/bin/env python3
"""
ML Model Training Pipeline - Complete Solution

5개 LightGBM 모델 학습:
1. Direction Model (Classifier): 방향 예측 (up/neutral/down)
2. Volatility Model (Classifier): 변동성 레벨 (low/normal/high/extreme)
3. Timing Model (Classifier): 진입 타이밍 (bad/ok/good)
4. StopLoss Model (Regressor): 최적 손절 % (0.5~5%)
5. PositionSize Model (Regressor): 최적 포지션 크기 % (5~40%)

Usage:
    # 기본 학습 (60일 ETH 데이터)
    python scripts/train_ml_pipeline.py

    # 심볼과 기간 지정
    python scripts/train_ml_pipeline.py --symbol BTCUSDT --days 90

    # 빠른 테스트 (7일 데이터, 100 라운드)
    python scripts/train_ml_pipeline.py --days 7 --rounds 100 --quick

Features:
    - 인증 없이 Bitget 공개 API로 데이터 수집
    - 70개 피처 자동 추출 (기술적 50 + 구조 10 + MTF 10)
    - 5개 LightGBM 모델 학습 및 저장
    - 피처 중요도 분석 및 저장

Requirements:
    pip install lightgbm pandas numpy aiohttp
"""

import sys
import logging
import argparse
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# Configure logging with colors
class ColorFormatter(logging.Formatter):
    """Colored log formatter"""
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


# Setup logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S'))

file_handler = logging.FileHandler(log_dir / f'training_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler, file_handler]
)
logger = logging.getLogger(__name__)


class BitgetPublicAPI:
    """
    Bitget 공개 API 클라이언트 - 인증 불필요

    시장 데이터(캔들)를 수집하는데 사용
    """

    BASE_URL = "https://api.bitget.com/api/v2/mix/market/candles"

    def __init__(self):
        self.session = None

    async def _ensure_session(self):
        """aiohttp 세션 생성"""
        if self.session is None:
            import aiohttp
            self.session = aiohttp.ClientSession()

    async def close(self):
        """세션 종료"""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_candles(
        self,
        symbol: str,
        granularity: str = "5m",
        end_time: Optional[int] = None,
        limit: int = 200
    ) -> List[dict]:
        """
        캔들 데이터 조회

        Args:
            symbol: 심볼 (예: ETHUSDT)
            granularity: 타임프레임 (5m, 15m, 1H, 4H)
            end_time: 종료 시간 (밀리초 타임스탬프)
            limit: 조회 개수 (최대 200)

        Returns:
            캔들 데이터 리스트 [{timestamp, open, high, low, close, volume}, ...]
        """
        await self._ensure_session()

        params = {
            "symbol": symbol,
            "productType": "USDT-FUTURES",
            "granularity": granularity,
            "limit": str(limit)
        }

        if end_time:
            params["endTime"] = str(end_time)

        try:
            async with self.session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"API error: {resp.status}")
                    return []

                data = await resp.json()

                if data.get("code") != "00000":
                    logger.error(f"API error: {data.get('msg')}")
                    return []

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

        except Exception as e:
            logger.error(f"Fetch candles error: {e}")
            return []

    async def collect_historical(
        self,
        symbol: str,
        timeframe: str,
        days: int
    ) -> pd.DataFrame:
        """
        과거 N일 데이터 수집

        Args:
            symbol: 심볼
            timeframe: 타임프레임 (5m, 1h 등)
            days: 수집할 일수

        Returns:
            OHLCV DataFrame
        """
        # 타임프레임 변환
        granularity_map = {
            "5m": "5m", "15m": "15m",
            "1h": "1H", "1H": "1H",
            "4h": "4H", "4H": "4H",
            "1d": "1D", "1D": "1D"
        }
        granularity = granularity_map.get(timeframe, "5m")

        # 캔들당 분 수
        minutes_map = {"5m": 5, "15m": 15, "1H": 60, "4H": 240, "1D": 1440}
        minutes_per_candle = minutes_map.get(granularity, 5)

        # 예상 캔들 수
        total_candles = (days * 24 * 60) // minutes_per_candle

        all_candles = []
        current_end = int(datetime.utcnow().timestamp() * 1000)
        collected = 0
        request_count = 0

        logger.info(f"  Collecting ~{total_candles} {timeframe} candles for {symbol}...")

        while collected < total_candles:
            candles = await self.fetch_candles(
                symbol=symbol,
                granularity=granularity,
                end_time=current_end,
                limit=200
            )

            if not candles:
                break

            all_candles.extend(candles)
            collected += len(candles)
            request_count += 1

            # 가장 오래된 캔들의 시간으로 다음 요청
            oldest_ts = min(c["timestamp"] for c in candles)
            current_end = oldest_ts - 1

            # 진행률 표시 (10번마다)
            if request_count % 10 == 0:
                progress = min(100, int(collected / total_candles * 100))
                logger.info(f"    Progress: {progress}% ({collected}/{total_candles})")

            # Rate limit 방지
            await asyncio.sleep(0.25)

        if not all_candles:
            return pd.DataFrame()

        # DataFrame 변환
        df = pd.DataFrame(all_candles)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp").drop_duplicates(subset="timestamp")
        df = df.set_index("timestamp")

        logger.info(f"  ✅ Collected {len(df)} {timeframe} candles")
        return df


class MLTrainingPipeline:
    """
    End-to-end ML 학습 파이프라인

    5단계 프로세스:
    1. Data Collection - Bitget 공개 API로 캔들 데이터 수집
    2. Feature Extraction - 70개 피처 추출 (기술적 50 + 구조 10 + MTF 10)
    3. Label Generation - 5개 타겟 라벨 생성
    4. Model Training - 5개 LightGBM 모델 학습
    5. Model Saving - 모델 및 피처 중요도 저장
    """

    def __init__(
        self,
        symbol: str = "ETHUSDT",
        models_dir: Optional[Path] = None,
    ):
        self.symbol = symbol
        self.models_dir = models_dir or Path(__file__).parent.parent / "src/ml/saved_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Data directory
        self.data_dir = Path(__file__).parent.parent / "src/ml/data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # API client
        self.api = BitgetPublicAPI()

        # ML components (lazy import)
        self.feature_pipeline = None
        self.labeler = None
        self.trainer = None

    def _init_ml_components(self):
        """ML 컴포넌트 초기화 (지연 로딩)"""
        if self.feature_pipeline is None:
            from src.ml.features import FeaturePipeline
            from src.ml.training.labeler import Labeler
            from src.ml.training.train_all_models import ModelTrainer

            self.feature_pipeline = FeaturePipeline()
            self.labeler = Labeler()
            self.trainer = ModelTrainer(models_dir=self.models_dir)

    async def run(
        self,
        days: int = 60,
        csv_path: Optional[str] = None,
        test_size: float = 0.2,
        num_boost_round: int = 500,
        early_stopping_rounds: int = 50,
    ) -> bool:
        """
        전체 학습 파이프라인 실행

        Args:
            days: 수집할 과거 데이터 일수 (기본: 60)
            csv_path: 기존 CSV 파일 경로 (선택)
            test_size: 검증 데이터 비율 (기본: 0.2)
            num_boost_round: LightGBM 부스팅 라운드 (기본: 500)
            early_stopping_rounds: 조기 종료 인내 (기본: 50)

        Returns:
            성공 여부
        """
        print("\n" + "=" * 60)
        print("   ML Model Training Pipeline")
        print("=" * 60)
        print(f"\n   Symbol:          {self.symbol}")
        print(f"   Data Period:     {days} days")
        print(f"   Test Size:       {test_size * 100:.0f}%")
        print(f"   Boost Rounds:    {num_boost_round}")
        print(f"   Early Stopping:  {early_stopping_rounds}")
        print("=" * 60 + "\n")

        start_time = datetime.now()

        try:
            # Initialize ML components
            self._init_ml_components()

            # Step 1: Data Collection
            logger.info("📊 STEP 1: Data Collection")
            logger.info("-" * 40)

            if csv_path:
                df_5m = self._load_from_csv(csv_path)
                df_1h = None
            else:
                df_5m, df_1h = await self._collect_data(days)

            if df_5m.empty:
                logger.error("❌ No data collected. Aborting.")
                return False

            # Save raw data
            self._save_raw_data(df_5m, df_1h, days)

            # Step 2: Feature Extraction
            logger.info("\n🔧 STEP 2: Feature Extraction")
            logger.info("-" * 40)

            df_features = self._extract_features(df_5m, df_1h)

            if df_features.empty:
                logger.error("❌ Feature extraction failed. Aborting.")
                return False

            logger.info(f"  ✅ Extracted {len(df_features.columns)} features for {len(df_features)} samples")

            # Step 3: Label Generation
            logger.info("\n🏷️  STEP 3: Label Generation")
            logger.info("-" * 40)

            df_labeled = self._generate_labels(df_features)

            if df_labeled.empty:
                logger.error("❌ Label generation failed. Aborting.")
                return False

            logger.info(f"  ✅ Generated labels for {len(df_labeled)} samples")
            self._print_label_distribution(df_labeled)

            # Step 4: Model Training
            logger.info("\n🚀 STEP 4: Model Training")
            logger.info("-" * 40)

            training_results = self._train_models(
                df_labeled,
                test_size=test_size,
                num_boost_round=num_boost_round,
                early_stopping_rounds=early_stopping_rounds
            )

            if not training_results:
                logger.error("❌ Training failed. Check logs.")
                return False

            # Step 5: Save Models
            logger.info("\n💾 STEP 5: Saving Models")
            logger.info("-" * 40)

            self.trainer.save_all()
            self._list_saved_models()

            # Print Summary
            duration = datetime.now() - start_time
            self._print_summary(training_results, duration)

            return True

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return False

        finally:
            await self.api.close()

    async def _collect_data(self, days: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """5분봉과 1시간봉 데이터 수집"""
        # 5분봉 수집
        df_5m = await self.api.collect_historical(self.symbol, "5m", days)

        # 1시간봉 수집 (MTF 피처용)
        df_1h = await self.api.collect_historical(self.symbol, "1h", days)

        return df_5m, df_1h

    def _load_from_csv(self, csv_path: str) -> pd.DataFrame:
        """CSV 파일에서 데이터 로드"""
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"  Loaded {len(df)} rows from {csv_path}")

            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')

            return df
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            return pd.DataFrame()

    def _save_raw_data(self, df_5m: pd.DataFrame, df_1h: Optional[pd.DataFrame], days: int):
        """원본 데이터 저장"""
        try:
            date_str = datetime.now().strftime("%Y%m%d")

            # 5분봉 저장
            path_5m = self.data_dir / f"{self.symbol}_5m_{days}d_{date_str}.parquet"
            df_5m.to_parquet(path_5m)
            logger.info(f"  Saved 5m data to {path_5m}")

            # 1시간봉 저장
            if df_1h is not None and not df_1h.empty:
                path_1h = self.data_dir / f"{self.symbol}_1h_{days}d_{date_str}.parquet"
                df_1h.to_parquet(path_1h)
                logger.info(f"  Saved 1h data to {path_1h}")

        except Exception as e:
            logger.warning(f"Failed to save raw data: {e}")

    def _extract_features(self, df_5m: pd.DataFrame, df_1h: Optional[pd.DataFrame]) -> pd.DataFrame:
        """70개 피처 추출"""
        try:
            # DataFrame을 캔들 리스트로 변환
            df_5m_reset = df_5m.reset_index()
            df_5m_reset['timestamp'] = df_5m_reset['timestamp'].astype('int64') // 10**6

            candles_5m = df_5m_reset.to_dict('records')

            candles_1h = None
            if df_1h is not None and not df_1h.empty:
                df_1h_reset = df_1h.reset_index()
                df_1h_reset['timestamp'] = df_1h_reset['timestamp'].astype('int64') // 10**6
                candles_1h = df_1h_reset.to_dict('records')

            # 피처 추출
            df_features = self.feature_pipeline.extract_features(
                candles_5m=candles_5m,
                candles_1h=candles_1h,
                symbol=self.symbol
            )

            # NaN 처리
            initial_len = len(df_features)
            df_features = df_features.dropna()
            dropped = initial_len - len(df_features)

            if dropped > 0:
                logger.info(f"  Dropped {dropped} rows with NaN values (indicator warmup)")

            return df_features

        except Exception as e:
            logger.error(f"Feature extraction failed: {e}", exc_info=True)
            return pd.DataFrame()

    def _generate_labels(self, df_features: pd.DataFrame) -> pd.DataFrame:
        """5개 타겟 라벨 생성"""
        try:
            df = df_features.copy()

            # close, high, low가 없으면 피처에서 추정
            if 'close' not in df.columns and 'ema_5' in df.columns:
                # EMA5를 close 대용으로 사용
                df['close'] = df['ema_5']

            if 'high' not in df.columns and 'bb_upper' in df.columns:
                df['high'] = df['bb_upper']

            if 'low' not in df.columns and 'bb_lower' in df.columns:
                df['low'] = df['bb_lower']

            # 라벨 생성
            df = self.labeler.generate_all_labels(df)

            # 라벨이 없는 행 제거
            label_columns = [
                'label_direction', 'label_volatility', 'label_timing',
                'label_stop_loss', 'label_position_size'
            ]
            df = df.dropna(subset=label_columns)

            return df

        except Exception as e:
            logger.error(f"Label generation failed: {e}", exc_info=True)
            return pd.DataFrame()

    def _train_models(
        self,
        df_labeled: pd.DataFrame,
        test_size: float,
        num_boost_round: int,
        early_stopping_rounds: int
    ) -> dict:
        """5개 모델 학습"""
        try:
            # 피처 컬럼 (라벨 제외)
            exclude_cols = [
                'label_direction', 'label_volatility', 'label_timing',
                'label_stop_loss', 'label_position_size',
                'future_return', 'atr_pct', 'timing_efficiency',
                'open', 'high', 'low', 'close', 'volume'
            ]
            feature_columns = [col for col in df_labeled.columns if col not in exclude_cols]

            logger.info(f"  Training with {len(feature_columns)} features")
            logger.info(f"  Train/Val split: {int((1-test_size)*100)}/{int(test_size*100)}")

            # 학습 실행
            results = self.trainer.train_all(
                df=df_labeled,
                feature_columns=feature_columns,
                test_size=test_size,
                num_boost_round=num_boost_round,
                early_stopping_rounds=early_stopping_rounds,
            )

            return results

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            return {}

    def _print_label_distribution(self, df: pd.DataFrame):
        """라벨 분포 출력"""
        logger.info("\n  📈 Label Distribution:")

        if 'label_direction' in df.columns:
            counts = df['label_direction'].value_counts().sort_index()
            logger.info(f"     Direction: {dict(counts)} (0=Down, 1=Neutral, 2=Up)")

        if 'label_volatility' in df.columns:
            counts = df['label_volatility'].value_counts().sort_index()
            logger.info(f"     Volatility: {dict(counts)} (0=Low, 1=Normal, 2=High, 3=Extreme)")

        if 'label_timing' in df.columns:
            counts = df['label_timing'].value_counts().sort_index()
            logger.info(f"     Timing: {dict(counts)} (0=Bad, 1=OK, 2=Good)")

        if 'label_stop_loss' in df.columns:
            stats = df['label_stop_loss'].describe()
            logger.info(f"     StopLoss: mean={stats['mean']:.2f}%, std={stats['std']:.2f}%")

        if 'label_position_size' in df.columns:
            stats = df['label_position_size'].describe()
            logger.info(f"     PositionSize: mean={stats['mean']:.2f}%, std={stats['std']:.2f}%")

    def _list_saved_models(self):
        """저장된 모델 목록 출력"""
        model_files = list(self.models_dir.glob("*.txt"))
        csv_files = list(self.models_dir.glob("*.csv"))

        logger.info(f"\n  Saved {len(model_files)} models:")
        for f in sorted(model_files):
            size_kb = f.stat().st_size / 1024
            logger.info(f"    - {f.name} ({size_kb:.1f} KB)")

        if csv_files:
            logger.info(f"\n  Saved {len(csv_files)} feature importance files:")
            for f in sorted(csv_files):
                logger.info(f"    - {f.name}")

    def _print_summary(self, results: dict, duration: timedelta):
        """학습 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("   Training Complete!")
        print("=" * 60)

        print(f"\n   ⏱️  Duration: {duration}")
        print(f"   📁 Models: {self.models_dir}")

        if results:
            print("\n   📊 Model Performance:")
            for model_name, metrics in results.items():
                if 'accuracy' in metrics:
                    print(f"      {model_name}: Accuracy={metrics['accuracy']:.4f}")
                elif 'rmse' in metrics:
                    print(f"      {model_name}: RMSE={metrics['rmse']:.4f}, MAE={metrics['mae']:.4f}")

        print("\n   ✅ Models ready for deployment!")
        print("   Use the following code to load models:")
        print("   ```python")
        print("   from src.ml.models import EnsemblePredictor")
        print("   predictor = EnsemblePredictor()")
        print("   result = predictor.predict(features_df)")
        print("   ```")
        print("=" * 60 + "\n")


def parse_args():
    """커맨드라인 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="ML Model Training Pipeline for Trading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 기본 학습 (60일 ETH 데이터)
  python train_ml_pipeline.py

  # 심볼과 기간 지정
  python train_ml_pipeline.py --symbol BTCUSDT --days 90

  # 빠른 테스트
  python train_ml_pipeline.py --days 7 --rounds 100 --quick

  # CSV 데이터 사용
  python train_ml_pipeline.py --csv data/training_data.csv
        """
    )

    parser.add_argument(
        '--symbol',
        type=str,
        default='ETHUSDT',
        help='Trading symbol (default: ETHUSDT)'
    )

    parser.add_argument(
        '--days',
        type=int,
        default=60,
        help='Days of historical data (default: 60)'
    )

    parser.add_argument(
        '--csv',
        type=str,
        default=None,
        help='Path to CSV file with pre-collected data'
    )

    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Validation split ratio (default: 0.2)'
    )

    parser.add_argument(
        '--rounds',
        type=int,
        default=500,
        help='LightGBM boosting rounds (default: 500)'
    )

    parser.add_argument(
        '--early-stopping',
        type=int,
        default=50,
        help='Early stopping patience (default: 50)'
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode: 7 days, 100 rounds'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Directory to save models'
    )

    return parser.parse_args()


async def main():
    """메인 진입점"""
    args = parse_args()

    # Quick 모드
    if args.quick:
        args.days = 7
        args.rounds = 100

    # 출력 디렉토리
    models_dir = Path(args.output_dir) if args.output_dir else None

    # 파이프라인 초기화
    pipeline = MLTrainingPipeline(
        symbol=args.symbol,
        models_dir=models_dir,
    )

    # 학습 실행
    success = await pipeline.run(
        days=args.days,
        csv_path=args.csv,
        test_size=args.test_size,
        num_boost_round=args.rounds,
        early_stopping_rounds=args.early_stopping,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
