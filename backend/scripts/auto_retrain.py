#!/usr/bin/env python3
"""
ML Model Auto-Retraining Script

매일 새로운 데이터로 모델을 재학습하고 성능을 모니터링합니다.
성능이 기준치 이하로 떨어지면 알림을 보냅니다.

Usage:
    python scripts/auto_retrain.py                    # 기본 재학습
    python scripts/auto_retrain.py --validate-only    # 검증만 (학습 안함)
    python scripts/auto_retrain.py --force            # 성능 상관없이 강제 학습

Cron 설정 예시 (매일 오전 6시):
    0 6 * * * cd /root/auto-dashboard/backend && python3 scripts/auto_retrain.py >> logs/retrain.log 2>&1
"""

import sys
import os
import argparse
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
import json

# 프로젝트 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / 'logs' / 'auto_retrain.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 성능 기준치
PERFORMANCE_THRESHOLDS = {
    "direction_accuracy": 0.55,      # 방향 예측 정확도 최소 55%
    "timing_accuracy": 0.45,         # 타이밍 예측 정확도 최소 45%
    "volatility_accuracy": 0.70,     # 변동성 예측 정확도 최소 70%
    "stop_loss_rmse": 0.50,          # SL RMSE 최대 0.5
    "position_size_rmse": 5.0,       # 포지션 사이즈 RMSE 최대 5
}

# 재학습 상태 파일
STATE_FILE = PROJECT_ROOT / 'src' / 'ml' / 'saved_models' / 'training_state.json'


def load_training_state() -> Dict:
    """학습 상태 로드"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        "last_train_time": None,
        "last_performance": {},
        "train_count": 0,
        "consecutive_failures": 0
    }


def save_training_state(state: Dict):
    """학습 상태 저장"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


async def collect_training_data(symbol: str = "ETHUSDT", days: int = 60) -> Tuple[list, list]:
    """학습 데이터 수집 (공개 API 사용)"""
    import aiohttp

    async def fetch_candles(granularity: str, limit: int) -> list:
        url = "https://api.bitget.com/api/v2/mix/market/candles"
        all_candles = []
        end_time = None

        # 페이징으로 데이터 수집
        requests_needed = (days * (1440 if granularity == "5m" else 24)) // limit + 1

        async with aiohttp.ClientSession() as session:
            for i in range(min(requests_needed, 10)):  # 최대 10회 요청
                params = {
                    "symbol": symbol,
                    "productType": "USDT-FUTURES",
                    "granularity": granularity,
                    "limit": str(limit)
                }
                if end_time:
                    params["endTime"] = str(end_time)

                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    candles = data.get("data", [])
                    if not candles:
                        break

                    for c in candles:
                        all_candles.append({
                            "timestamp": int(c[0]),
                            "open": float(c[1]),
                            "high": float(c[2]),
                            "low": float(c[3]),
                            "close": float(c[4]),
                            "volume": float(c[5])
                        })

                    end_time = int(candles[-1][0]) - 1
                    await asyncio.sleep(0.2)  # Rate limiting

        # 시간순 정렬
        all_candles.sort(key=lambda x: x["timestamp"])
        return all_candles

    logger.info(f"Collecting {days} days of {symbol} data...")

    candles_5m = await fetch_candles("5m", 1000)
    candles_1h = await fetch_candles("1H", 1000)

    logger.info(f"Collected: {len(candles_5m)} 5m candles, {len(candles_1h)} 1h candles")
    return candles_5m, candles_1h


def train_models(candles_5m: list, candles_1h: list) -> Dict:
    """모델 학습 실행"""
    import pandas as pd
    from src.ml.features import FeaturePipeline
    from src.ml.training.labeler import DataLabeler
    from src.ml.training.train_all_models import ModelTrainer

    logger.info("Extracting features...")
    pipeline = FeaturePipeline()
    features_df = pipeline.extract_features(candles_5m, candles_1h)

    if len(features_df) < 500:
        raise ValueError(f"Insufficient data: {len(features_df)} rows (need at least 500)")

    logger.info("Generating labels...")
    labeler = DataLabeler()
    labeled_df = labeler.generate_labels(features_df)

    # NaN 제거
    feature_cols = [c for c in labeled_df.columns if not c.startswith('label_')]
    labeled_df = labeled_df.dropna(subset=feature_cols)

    logger.info(f"Training with {len(labeled_df)} samples, {len(feature_cols)} features...")

    trainer = ModelTrainer()
    results = trainer.train_all(
        labeled_df,
        feature_cols,
        test_size=0.2,
        num_boost_round=500,
        early_stopping_rounds=50
    )

    trainer.save_all()

    return results


def validate_models() -> Dict:
    """현재 모델 성능 검증"""
    from src.ml.models import EnsemblePredictor
    from src.ml.features import FeaturePipeline

    predictor = EnsemblePredictor()

    if not predictor.models_loaded:
        return {"status": "no_models", "message": "Models not loaded"}

    # 최신 데이터로 예측 테스트
    try:
        candles_5m, candles_1h = asyncio.run(collect_training_data(days=7))
        pipeline = FeaturePipeline()
        features_df = pipeline.extract_features(candles_5m, candles_1h)

        if features_df.empty:
            return {"status": "error", "message": "Failed to extract features"}

        result = predictor.predict(features_df, symbol="ETHUSDT")

        return {
            "status": "ok",
            "models_loaded": predictor.models_loaded,
            "direction": result.direction.direction.value,
            "direction_confidence": result.direction.confidence,
            "volatility": result.volatility.level.value,
            "timing_good": result.timing.is_good_entry,
            "combined_confidence": result.combined_confidence
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def check_performance(results: Dict) -> Tuple[bool, str]:
    """학습 결과가 기준치를 만족하는지 확인"""
    issues = []

    if 'direction' in results:
        acc = results['direction'].get('accuracy', 0)
        if acc < PERFORMANCE_THRESHOLDS['direction_accuracy']:
            issues.append(f"Direction accuracy {acc:.1%} < {PERFORMANCE_THRESHOLDS['direction_accuracy']:.0%}")

    if 'timing' in results:
        acc = results['timing'].get('accuracy', 0)
        if acc < PERFORMANCE_THRESHOLDS['timing_accuracy']:
            issues.append(f"Timing accuracy {acc:.1%} < {PERFORMANCE_THRESHOLDS['timing_accuracy']:.0%}")

    if 'volatility' in results:
        acc = results['volatility'].get('accuracy', 0)
        if acc < PERFORMANCE_THRESHOLDS['volatility_accuracy']:
            issues.append(f"Volatility accuracy {acc:.1%} < {PERFORMANCE_THRESHOLDS['volatility_accuracy']:.0%}")

    if 'stop_loss' in results:
        rmse = results['stop_loss'].get('rmse', float('inf'))
        if rmse > PERFORMANCE_THRESHOLDS['stop_loss_rmse']:
            issues.append(f"StopLoss RMSE {rmse:.3f} > {PERFORMANCE_THRESHOLDS['stop_loss_rmse']}")

    if 'position_size' in results:
        rmse = results['position_size'].get('rmse', float('inf'))
        if rmse > PERFORMANCE_THRESHOLDS['position_size_rmse']:
            issues.append(f"PositionSize RMSE {rmse:.3f} > {PERFORMANCE_THRESHOLDS['position_size_rmse']}")

    if issues:
        return False, "\n".join(issues)
    return True, "All metrics meet thresholds"


def send_notification(title: str, message: str, is_error: bool = False):
    """알림 전송 (Telegram 또는 로그)"""
    # 여기에 Telegram 알림 연동 가능
    level = logging.ERROR if is_error else logging.INFO
    logger.log(level, f"[{title}] {message}")

    # TODO: Telegram 알림 추가
    # from src.services.telegram.notifier import TelegramNotifier
    # notifier = TelegramNotifier()
    # notifier.send_admin_message(f"🤖 {title}\n{message}")


def main():
    parser = argparse.ArgumentParser(description="ML Model Auto-Retraining")
    parser.add_argument('--validate-only', action='store_true', help='Only validate current models')
    parser.add_argument('--force', action='store_true', help='Force retrain regardless of performance')
    parser.add_argument('--days', type=int, default=60, help='Days of training data')
    parser.add_argument('--symbol', type=str, default='ETHUSDT', help='Symbol to train on')
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("ML Auto-Retrain Started")
    logger.info("=" * 50)

    state = load_training_state()

    # 검증만 수행
    if args.validate_only:
        logger.info("Validating current models...")
        validation = validate_models()
        logger.info(f"Validation result: {json.dumps(validation, indent=2, default=str)}")
        return

    # 학습 주기 확인 (24시간 이내 학습했으면 스킵)
    if state['last_train_time'] and not args.force:
        last_train = datetime.fromisoformat(state['last_train_time'])
        hours_since = (datetime.now() - last_train).total_seconds() / 3600
        if hours_since < 20:  # 20시간 이내
            logger.info(f"Skipping: Last trained {hours_since:.1f} hours ago")
            return

    try:
        # 1. 데이터 수집
        candles_5m, candles_1h = asyncio.run(
            collect_training_data(symbol=args.symbol, days=args.days)
        )

        if len(candles_5m) < 1000:
            raise ValueError(f"Insufficient 5m candles: {len(candles_5m)}")

        # 2. 모델 학습
        logger.info("Training models...")
        results = train_models(candles_5m, candles_1h)

        # 3. 성능 검증
        passed, message = check_performance(results)

        if passed:
            logger.info(f"✅ Training successful!\n{json.dumps(results, indent=2, default=str)}")
            send_notification(
                "ML Training Complete",
                f"Symbol: {args.symbol}\n"
                f"Samples: {len(candles_5m)}\n"
                f"Direction Acc: {results.get('direction', {}).get('accuracy', 0):.1%}\n"
                f"Volatility Acc: {results.get('volatility', {}).get('accuracy', 0):.1%}"
            )
            state['consecutive_failures'] = 0
        else:
            logger.warning(f"⚠️ Performance below threshold:\n{message}")
            send_notification("ML Training Warning", message, is_error=True)
            state['consecutive_failures'] = state.get('consecutive_failures', 0) + 1

        # 상태 업데이트
        state['last_train_time'] = datetime.now().isoformat()
        state['last_performance'] = results
        state['train_count'] = state.get('train_count', 0) + 1
        save_training_state(state)

    except Exception as e:
        logger.error(f"❌ Training failed: {e}", exc_info=True)
        send_notification("ML Training Failed", str(e), is_error=True)
        state['consecutive_failures'] = state.get('consecutive_failures', 0) + 1
        save_training_state(state)
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("ML Auto-Retrain Completed")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
