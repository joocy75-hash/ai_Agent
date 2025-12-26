"""
ML Predictor Agent - LightGBM 기반 예측 에이전트

BaseAgent를 상속받아 비동기 예측 처리
5개 모델 앙상블로 거래 신호 강화
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import uuid

from ..base import BaseAgent, AgentTask, TaskPriority
from .models import (
    MLPredictionRequest,
    MLPredictionResult,
    MLPredictorConfig,
    PredictionConfidence,
    DirectionLabel,
    VolatilityLabel,
    TimingLabel,
)

logger = logging.getLogger(__name__)

# ML 모듈 import (optional)
try:
    from ...ml.features import FeaturePipeline
    from ...ml.models import EnsemblePredictor
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger.warning("ML module not available. MLPredictorAgent will use fallback.")


class MLPredictorAgent(BaseAgent):
    """
    ML Predictor Agent

    5개 LightGBM 모델을 사용한 거래 예측:
    1. Direction: 방향 예측 (up/down/neutral)
    2. Volatility: 변동성 레벨 (low/normal/high/extreme)
    3. Timing: 진입 타이밍 (bad/ok/good)
    4. StopLoss: 최적 손절 비율
    5. PositionSize: 최적 포지션 크기

    Usage:
    ```python
    agent = MLPredictorAgent(config=MLPredictorConfig())
    await agent.start()

    result = await agent.predict(
        symbol="ETHUSDT",
        candles_5m=candles,
        candles_1h=hourly_candles
    )
    ```
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[MLPredictorConfig] = None
    ):
        super().__init__(
            agent_id=agent_id or f"ml_predictor_{uuid.uuid4().hex[:8]}",
            name="ML Predictor Agent",
            config=config.to_dict() if config else {}
        )

        self.predictor_config = config or MLPredictorConfig()

        # ML 컴포넌트
        self.feature_pipeline: Optional[Any] = None
        self.ensemble_predictor: Optional[Any] = None

        # 캐시
        self._prediction_cache: Dict[str, tuple] = {}  # {key: (result, timestamp)}
        self._cache_lock = asyncio.Lock()

        # 세마포어 (동시 예측 제한)
        self._prediction_semaphore = asyncio.Semaphore(
            self.predictor_config.max_concurrent_predictions
        )

        # 통계
        self._total_predictions = 0
        self._cache_hits = 0
        self._fallback_count = 0

        logger.info(f"MLPredictorAgent initialized (ML available: {ML_AVAILABLE})")

    async def start(self):
        """에이전트 시작"""
        # ML 컴포넌트 초기화
        if ML_AVAILABLE and self.predictor_config.load_models_on_start:
            await self._initialize_ml_components()

        await super().start()

    async def _initialize_ml_components(self):
        """ML 컴포넌트 초기화"""
        try:
            logger.info("Initializing ML components...")

            # Feature Pipeline
            self.feature_pipeline = FeaturePipeline()

            # Ensemble Predictor
            models_dir = self.predictor_config.models_dir
            if models_dir:
                self.ensemble_predictor = EnsemblePredictor(models_dir=Path(models_dir))
            else:
                self.ensemble_predictor = EnsemblePredictor()

            logger.info("✅ ML components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ML components: {e}")
            if not self.predictor_config.enable_fallback:
                raise

    async def process_task(self, task: AgentTask) -> Any:
        """
        작업 처리 (BaseAgent 추상 메서드 구현)

        Task types:
        - "predict": ML 예측 수행
        - "clear_cache": 캐시 초기화
        - "reload_models": 모델 재로드
        """
        task_type = task.task_type

        if task_type == "predict":
            request = MLPredictionRequest(**task.params)
            return await self._do_prediction(request)

        elif task_type == "clear_cache":
            await self._clear_cache()
            return {"status": "cache_cleared"}

        elif task_type == "reload_models":
            await self._initialize_ml_components()
            return {"status": "models_reloaded"}

        else:
            logger.warning(f"Unknown task type: {task_type}")
            return None

    async def predict(
        self,
        symbol: str,
        candles_5m: List[Dict[str, Any]],
        candles_1h: Optional[List[Dict[str, Any]]] = None,
        current_price: Optional[float] = None,
        use_cache: bool = True
    ) -> MLPredictionResult:
        """
        ML 예측 수행 (직접 호출용)

        Args:
            symbol: 심볼 (예: ETHUSDT)
            candles_5m: 5분봉 캔들 데이터
            candles_1h: 1시간봉 캔들 데이터 (optional)
            current_price: 현재 가격 (optional)
            use_cache: 캐시 사용 여부

        Returns:
            MLPredictionResult
        """
        request_id = f"pred_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

        request = MLPredictionRequest(
            request_id=request_id,
            symbol=symbol,
            candles_5m=candles_5m,
            candles_1h=candles_1h,
            current_price=current_price,
        )

        # 캐시 확인
        if use_cache:
            cached = await self._get_cached(symbol)
            if cached:
                self._cache_hits += 1
                return cached

        return await self._do_prediction(request)

    async def _do_prediction(self, request: MLPredictionRequest) -> MLPredictionResult:
        """실제 예측 수행"""
        start_time = datetime.utcnow()
        self._total_predictions += 1

        async with self._prediction_semaphore:
            try:
                if ML_AVAILABLE and self.ensemble_predictor:
                    result = await self._ml_predict(request)
                else:
                    result = await self._fallback_predict(request)

                # 처리 시간 기록
                result.processing_time_ms = (
                    datetime.utcnow() - start_time
                ).total_seconds() * 1000

                # 캐시 저장
                await self._set_cache(request.symbol, result)

                return result

            except Exception as e:
                logger.error(f"Prediction failed: {e}", exc_info=True)

                if self.predictor_config.enable_fallback:
                    return await self._fallback_predict(request)
                else:
                    raise

    async def _ml_predict(self, request: MLPredictionRequest) -> MLPredictionResult:
        """ML 모델을 사용한 예측"""
        # 피처 추출
        features = self.feature_pipeline.extract_latest_features(
            candles_5m=request.candles_5m,
            candles_1h=request.candles_1h,
            symbol=request.symbol
        )

        if not features:
            logger.warning("Feature extraction failed, using fallback")
            return await self._fallback_predict(request)

        # 앙상블 예측
        ml_result = self.ensemble_predictor.predict(features)

        # 결과 변환
        result = MLPredictionResult(
            request_id=request.request_id,
            symbol=request.symbol,
            direction=self._map_direction(ml_result.direction.direction),
            direction_probabilities=ml_result.direction.probabilities,
            volatility=self._map_volatility(ml_result.volatility.level),
            volatility_probabilities={},
            timing=self._map_timing(ml_result.timing.timing),
            timing_probabilities=ml_result.timing.probabilities,
            stop_loss_percent=ml_result.stop_loss.stop_loss_percent,
            position_size_percent=ml_result.position_size.position_size_percent,
            confidence=PredictionConfidence(
                direction=ml_result.direction.confidence,
                volatility=ml_result.volatility.confidence,
                timing=ml_result.timing.confidence,
                stop_loss=ml_result.stop_loss.confidence,
                position_size=ml_result.position_size.confidence,
            ),
            models_used=ml_result.models_used,
            fallback_used=ml_result.fallback_used,
        )

        return result

    async def _fallback_predict(self, request: MLPredictionRequest) -> MLPredictionResult:
        """폴백 예측 (휴리스틱)"""
        self._fallback_count += 1

        # 간단한 기술적 분석 기반 예측
        candles = request.candles_5m
        if len(candles) < 20:
            return self._neutral_result(request)

        # 최근 가격 데이터
        closes = [float(c.get('close', c.get('c', 0))) for c in candles[-20:]]

        # EMA 계산
        ema_5 = sum(closes[-5:]) / 5
        ema_20 = sum(closes) / 20
        current = closes[-1]

        # 방향 결정
        if current > ema_5 > ema_20:
            direction = DirectionLabel.UP
            direction_conf = 0.6
        elif current < ema_5 < ema_20:
            direction = DirectionLabel.DOWN
            direction_conf = 0.6
        else:
            direction = DirectionLabel.NEUTRAL
            direction_conf = 0.5

        # 변동성 계산 (단순 표준편차)
        import statistics
        try:
            volatility_raw = statistics.stdev(closes) / statistics.mean(closes) * 100
        except:
            volatility_raw = 1.0

        if volatility_raw < 0.5:
            volatility = VolatilityLabel.LOW
        elif volatility_raw < 1.5:
            volatility = VolatilityLabel.NORMAL
        elif volatility_raw < 3.0:
            volatility = VolatilityLabel.HIGH
        else:
            volatility = VolatilityLabel.EXTREME

        result = MLPredictionResult(
            request_id=request.request_id,
            symbol=request.symbol,
            direction=direction,
            direction_probabilities={
                'down': 0.33 if direction == DirectionLabel.NEUTRAL else (0.6 if direction == DirectionLabel.DOWN else 0.2),
                'neutral': 0.34 if direction == DirectionLabel.NEUTRAL else 0.2,
                'up': 0.33 if direction == DirectionLabel.NEUTRAL else (0.6 if direction == DirectionLabel.UP else 0.2),
            },
            volatility=volatility,
            timing=TimingLabel.OK,
            stop_loss_percent=2.0,
            position_size_percent=10.0,
            confidence=PredictionConfidence(
                direction=direction_conf,
                volatility=0.5,
                timing=0.5,
                stop_loss=0.4,
                position_size=0.4,
            ),
            models_used=[],
            fallback_used=True,
        )

        return result

    def _neutral_result(self, request: MLPredictionRequest) -> MLPredictionResult:
        """중립 결과 반환"""
        return MLPredictionResult(
            request_id=request.request_id,
            symbol=request.symbol,
            direction=DirectionLabel.NEUTRAL,
            volatility=VolatilityLabel.NORMAL,
            timing=TimingLabel.OK,
            fallback_used=True,
        )

    def _map_direction(self, direction: int) -> DirectionLabel:
        """방향 값 → 라벨 변환"""
        mapping = {0: DirectionLabel.DOWN, 1: DirectionLabel.NEUTRAL, 2: DirectionLabel.UP}
        return mapping.get(direction, DirectionLabel.NEUTRAL)

    def _map_volatility(self, level: int) -> VolatilityLabel:
        """변동성 값 → 라벨 변환"""
        mapping = {
            0: VolatilityLabel.LOW,
            1: VolatilityLabel.NORMAL,
            2: VolatilityLabel.HIGH,
            3: VolatilityLabel.EXTREME,
        }
        return mapping.get(level, VolatilityLabel.NORMAL)

    def _map_timing(self, timing: int) -> TimingLabel:
        """타이밍 값 → 라벨 변환"""
        mapping = {0: TimingLabel.BAD, 1: TimingLabel.OK, 2: TimingLabel.GOOD}
        return mapping.get(timing, TimingLabel.OK)

    async def _get_cached(self, symbol: str) -> Optional[MLPredictionResult]:
        """캐시에서 결과 조회"""
        async with self._cache_lock:
            if symbol in self._prediction_cache:
                result, timestamp = self._prediction_cache[symbol]
                age = (datetime.utcnow() - timestamp).total_seconds()
                if age < self.predictor_config.cache_ttl:
                    return result
                else:
                    del self._prediction_cache[symbol]
        return None

    async def _set_cache(self, symbol: str, result: MLPredictionResult):
        """캐시에 결과 저장"""
        async with self._cache_lock:
            self._prediction_cache[symbol] = (result, datetime.utcnow())

            # 캐시 크기 제한
            if len(self._prediction_cache) > self.predictor_config.max_cache_size:
                oldest = min(
                    self._prediction_cache.keys(),
                    key=lambda k: self._prediction_cache[k][1]
                )
                del self._prediction_cache[oldest]

    async def _clear_cache(self):
        """캐시 초기화"""
        async with self._cache_lock:
            self._prediction_cache.clear()
        logger.info("Prediction cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """통계 반환"""
        cache_hit_rate = (
            self._cache_hits / self._total_predictions * 100
            if self._total_predictions > 0 else 0
        )

        return {
            'total_predictions': self._total_predictions,
            'cache_hits': self._cache_hits,
            'cache_hit_rate': round(cache_hit_rate, 2),
            'fallback_count': self._fallback_count,
            'cache_size': len(self._prediction_cache),
            'ml_available': ML_AVAILABLE,
            'models_loaded': self.ensemble_predictor is not None,
        }

    def get_status(self) -> Dict[str, Any]:
        """에이전트 상태 조회 (확장)"""
        base_status = super().get_status()
        base_status['ml_stats'] = self.get_stats()
        return base_status
