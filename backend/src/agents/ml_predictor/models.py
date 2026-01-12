"""
ML Predictor Models - 데이터 모델 정의

Request/Response 타입 및 설정 클래스
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DirectionLabel(str, Enum):
    """방향 라벨"""
    DOWN = "down"
    NEUTRAL = "neutral"
    UP = "up"


class VolatilityLabel(str, Enum):
    """변동성 라벨"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


class TimingLabel(str, Enum):
    """타이밍 라벨"""
    BAD = "bad"
    OK = "ok"
    GOOD = "good"


@dataclass
class PredictionConfidence:
    """예측 신뢰도"""
    direction: float = 0.0
    volatility: float = 0.0
    timing: float = 0.0
    stop_loss: float = 0.0
    position_size: float = 0.0

    @property
    def overall(self) -> float:
        """전체 신뢰도 (가중 평균)"""
        weights = {
            'direction': 0.35,
            'volatility': 0.15,
            'timing': 0.25,
            'stop_loss': 0.10,
            'position_size': 0.15,
        }
        return (
            self.direction * weights['direction'] +
            self.volatility * weights['volatility'] +
            self.timing * weights['timing'] +
            self.stop_loss * weights['stop_loss'] +
            self.position_size * weights['position_size']
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            'direction': round(self.direction, 4),
            'volatility': round(self.volatility, 4),
            'timing': round(self.timing, 4),
            'stop_loss': round(self.stop_loss, 4),
            'position_size': round(self.position_size, 4),
            'overall': round(self.overall, 4),
        }


@dataclass
class MLPredictionRequest:
    """ML 예측 요청"""
    request_id: str
    symbol: str
    candles_5m: List[Dict[str, Any]]  # 5분봉 캔들
    candles_1h: Optional[List[Dict[str, Any]]] = None  # 1시간봉 (optional)
    current_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not self.request_id:
            raise ValueError("request_id is required")
        if not self.symbol:
            raise ValueError("symbol is required")
        if not self.candles_5m or len(self.candles_5m) < 50:
            raise ValueError("At least 50 candles are required")


@dataclass
class MLPredictionResult:
    """ML 예측 결과"""
    request_id: str
    symbol: str

    # 예측 결과
    direction: DirectionLabel = DirectionLabel.NEUTRAL
    direction_probabilities: Dict[str, float] = field(default_factory=dict)

    volatility: VolatilityLabel = VolatilityLabel.NORMAL
    volatility_probabilities: Dict[str, float] = field(default_factory=dict)

    timing: TimingLabel = TimingLabel.OK
    timing_probabilities: Dict[str, float] = field(default_factory=dict)

    stop_loss_percent: float = 2.0
    position_size_percent: float = 10.0

    # 신뢰도
    confidence: PredictionConfidence = field(default_factory=PredictionConfidence)

    # 메타데이터
    models_used: List[str] = field(default_factory=list)
    fallback_used: bool = False
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_confident(self) -> bool:
        """충분히 신뢰할 수 있는 예측인지"""
        return self.confidence.overall >= 0.6

    @property
    def should_trade(self) -> bool:
        """거래 신호로 사용할 수 있는지"""
        return (
            self.direction != DirectionLabel.NEUTRAL and
            self.timing != TimingLabel.BAD and
            self.confidence.direction >= 0.5
        )

    @property
    def recommended_action(self) -> str:
        """권장 행동"""
        if not self.should_trade:
            return "hold"

        if self.direction == DirectionLabel.UP:
            return "buy"
        elif self.direction == DirectionLabel.DOWN:
            return "sell"
        else:
            return "hold"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'request_id': self.request_id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'direction_probabilities': self.direction_probabilities,
            'volatility': self.volatility.value,
            'volatility_probabilities': self.volatility_probabilities,
            'timing': self.timing.value,
            'timing_probabilities': self.timing_probabilities,
            'stop_loss_percent': round(self.stop_loss_percent, 2),
            'position_size_percent': round(self.position_size_percent, 2),
            'confidence': self.confidence.to_dict(),
            'is_confident': self.is_confident,
            'should_trade': self.should_trade,
            'recommended_action': self.recommended_action,
            'models_used': self.models_used,
            'fallback_used': self.fallback_used,
            'processing_time_ms': round(self.processing_time_ms, 2),
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class MLPredictorConfig:
    """ML Predictor Agent 설정"""
    # 모델 설정
    models_dir: str = ""
    load_models_on_start: bool = True

    # 예측 설정
    direction_threshold: float = 0.5  # 방향 예측 최소 신뢰도
    timing_threshold: float = 0.5  # 타이밍 예측 최소 신뢰도

    # 캐시 설정
    cache_ttl: float = 5.0  # 초
    max_cache_size: int = 100

    # 폴백 설정
    enable_fallback: bool = True  # 모델 로드 실패 시 휴리스틱 사용

    # 성능 설정
    max_concurrent_predictions: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            'models_dir': self.models_dir,
            'load_models_on_start': self.load_models_on_start,
            'direction_threshold': self.direction_threshold,
            'timing_threshold': self.timing_threshold,
            'cache_ttl': self.cache_ttl,
            'max_cache_size': self.max_cache_size,
            'enable_fallback': self.enable_fallback,
            'max_concurrent_predictions': self.max_concurrent_predictions,
        }
