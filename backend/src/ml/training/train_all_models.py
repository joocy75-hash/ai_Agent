"""
Model Trainer - 5개 LightGBM 모델 학습

1. Direction Model (Classifier): 방향 예측
2. Volatility Model (Classifier): 변동성 레벨
3. Timing Model (Classifier): 진입 타이밍
4. StopLoss Model (Regressor): 최적 SL
5. PositionSize Model (Regressor): 최적 사이즈
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# LightGBM optional import
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logger.warning("LightGBM not installed. Training will be disabled.")


class ModelTrainer:
    """
    LightGBM 모델 학습기

    Usage:
    ```python
    trainer = ModelTrainer()
    trainer.train_all(df_labeled, feature_columns)
    trainer.save_all()
    ```
    """

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        classifier_params: Optional[Dict] = None,
        regressor_params: Optional[Dict] = None,
    ):
        self.models_dir = models_dir or Path(__file__).parent.parent / "saved_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 기본 하이퍼파라미터
        self.classifier_params = classifier_params or {
            "objective": "multiclass",
            "metric": "multi_logloss",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "num_threads": 4,
            "max_depth": 6,
            "min_data_in_leaf": 20,
        }

        self.regressor_params = regressor_params or {
            "objective": "regression",
            "metric": "rmse",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "num_threads": 4,
            "max_depth": 6,
            "min_data_in_leaf": 20,
        }

        # 학습된 모델 저장
        self.models: Dict[str, Any] = {}
        self.feature_importance: Dict[str, pd.DataFrame] = {}

        logger.info(f"ModelTrainer initialized, models_dir: {self.models_dir}")

    def train_all(
        self,
        df: pd.DataFrame,
        feature_columns: List[str],
        test_size: float = 0.2,
        num_boost_round: int = 500,
        early_stopping_rounds: int = 50,
    ) -> Dict[str, Dict]:
        """
        모든 모델 학습

        Args:
            df: 라벨이 포함된 DataFrame
            feature_columns: 피처 컬럼 목록
            test_size: 테스트 데이터 비율
            num_boost_round: 부스팅 라운드
            early_stopping_rounds: 조기 종료 라운드

        Returns:
            각 모델의 학습 결과
        """
        if not LIGHTGBM_AVAILABLE:
            logger.error("LightGBM not available. Cannot train models.")
            return {}

        results = {}

        # 데이터 분할
        train_df, val_df = self._split_data(df, test_size)

        X_train = train_df[feature_columns]
        X_val = val_df[feature_columns]

        # 1. Direction Model
        if 'label_direction' in df.columns:
            logger.info("Training Direction model...")
            results['direction'] = self._train_classifier(
                X_train, train_df['label_direction'],
                X_val, val_df['label_direction'],
                model_name='direction',
                num_classes=3,
                num_boost_round=num_boost_round,
                early_stopping_rounds=early_stopping_rounds,
            )

        # 2. Volatility Model
        if 'label_volatility' in df.columns:
            logger.info("Training Volatility model...")
            results['volatility'] = self._train_classifier(
                X_train, train_df['label_volatility'],
                X_val, val_df['label_volatility'],
                model_name='volatility',
                num_classes=4,
                num_boost_round=num_boost_round,
                early_stopping_rounds=early_stopping_rounds,
            )

        # 3. Timing Model
        if 'label_timing' in df.columns:
            logger.info("Training Timing model...")
            results['timing'] = self._train_classifier(
                X_train, train_df['label_timing'],
                X_val, val_df['label_timing'],
                model_name='timing',
                num_classes=3,
                num_boost_round=num_boost_round,
                early_stopping_rounds=early_stopping_rounds,
            )

        # 4. StopLoss Model
        if 'label_stop_loss' in df.columns:
            logger.info("Training StopLoss model...")
            results['stop_loss'] = self._train_regressor(
                X_train, train_df['label_stop_loss'],
                X_val, val_df['label_stop_loss'],
                model_name='stop_loss',
                num_boost_round=num_boost_round,
                early_stopping_rounds=early_stopping_rounds,
            )

        # 5. PositionSize Model
        if 'label_position_size' in df.columns:
            logger.info("Training PositionSize model...")
            results['position_size'] = self._train_regressor(
                X_train, train_df['label_position_size'],
                X_val, val_df['label_position_size'],
                model_name='position_size',
                num_boost_round=num_boost_round,
                early_stopping_rounds=early_stopping_rounds,
            )

        logger.info(f"Training complete. Models: {list(self.models.keys())}")
        return results

    def _train_classifier(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        model_name: str,
        num_classes: int,
        num_boost_round: int,
        early_stopping_rounds: int,
    ) -> Dict:
        """분류 모델 학습"""
        params = self.classifier_params.copy()
        params['num_class'] = num_classes

        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        callbacks = [
            lgb.early_stopping(stopping_rounds=early_stopping_rounds),
            lgb.log_evaluation(period=100),
        ]

        model = lgb.train(
            params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'valid'],
            callbacks=callbacks,
        )

        self.models[model_name] = model
        self._save_feature_importance(model, model_name, X_train.columns)

        # 평가
        y_pred = model.predict(X_val)
        y_pred_class = np.argmax(y_pred, axis=1)
        accuracy = (y_pred_class == y_val).mean()

        return {
            'accuracy': accuracy,
            'best_iteration': model.best_iteration,
            'num_classes': num_classes,
        }

    def _train_regressor(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        model_name: str,
        num_boost_round: int,
        early_stopping_rounds: int,
    ) -> Dict:
        """회귀 모델 학습"""
        params = self.regressor_params.copy()

        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

        callbacks = [
            lgb.early_stopping(stopping_rounds=early_stopping_rounds),
            lgb.log_evaluation(period=100),
        ]

        model = lgb.train(
            params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'valid'],
            callbacks=callbacks,
        )

        self.models[model_name] = model
        self._save_feature_importance(model, model_name, X_train.columns)

        # 평가
        y_pred = model.predict(X_val)
        rmse = np.sqrt(np.mean((y_pred - y_val) ** 2))
        mae = np.mean(np.abs(y_pred - y_val))

        return {
            'rmse': rmse,
            'mae': mae,
            'best_iteration': model.best_iteration,
        }

    def _split_data(
        self,
        df: pd.DataFrame,
        test_size: float
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """시계열 데이터 분할 (시간순)"""
        split_idx = int(len(df) * (1 - test_size))
        return df.iloc[:split_idx], df.iloc[split_idx:]

    def _save_feature_importance(
        self,
        model: Any,
        model_name: str,
        feature_names: List[str]
    ):
        """피처 중요도 저장"""
        importance = model.feature_importance(importance_type='gain')
        fi_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

        self.feature_importance[model_name] = fi_df

    def save_all(self):
        """모든 모델 저장 (EnsemblePredictor와 호환되는 파일명 사용)"""
        # EnsemblePredictor가 기대하는 파일명 매핑
        filename_map = {
            "direction": "lightgbm_direction.txt",
            "volatility": "lightgbm_volatility.txt",
            "timing": "lightgbm_timing.txt",
            "stop_loss": "lightgbm_stoploss.txt",
            "position_size": "lightgbm_position_size.txt",
        }

        for name, model in self.models.items():
            # EnsemblePredictor 호환 파일명 사용
            filename = filename_map.get(name, f"lightgbm_{name}.txt")
            model_path = self.models_dir / filename
            model.save_model(str(model_path))
            logger.info(f"Saved {name} model to {model_path}")

            # 피처 중요도 저장
            if name in self.feature_importance:
                fi_path = self.models_dir / f"{name}_feature_importance.csv"
                self.feature_importance[name].to_csv(fi_path, index=False)

    def load_model(self, model_name: str) -> Optional[Any]:
        """모델 로드"""
        if not LIGHTGBM_AVAILABLE:
            logger.warning("LightGBM not available")
            return None

        model_path = self.models_dir / f"{model_name}_model.txt"
        if model_path.exists():
            model = lgb.Booster(model_file=str(model_path))
            self.models[model_name] = model
            logger.info(f"Loaded {model_name} model from {model_path}")
            return model
        else:
            logger.warning(f"Model file not found: {model_path}")
            return None

    def get_training_summary(self) -> Dict:
        """학습 요약 반환"""
        return {
            'models_trained': list(self.models.keys()),
            'models_dir': str(self.models_dir),
            'feature_importance_available': list(self.feature_importance.keys()),
        }
