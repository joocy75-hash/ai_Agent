"""
Signal Validator Models (시그널 검증 데이터 모델)

시그널 검증 결과를 저장하는 데이터 모델
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List


class ValidationResult(str, Enum):
    """검증 결과"""
    APPROVED = "approved"  # 승인
    REJECTED = "rejected"  # 거부
    WARNING = "warning"  # 경고 (조건부 승인)
    PENDING = "pending"  # 검증 대기


@dataclass
class SignalValidation:
    """
    시그널 검증 결과

    Attributes:
        signal_id: 시그널 ID
        symbol: 심볼
        action: 시그널 액션 (buy/sell/close)
        validation_result: 검증 결과
        confidence_score: 신뢰도 점수 (0.0 ~ 1.0)
        passed_rules: 통과한 규칙 목록
        failed_rules: 실패한 규칙 목록
        warnings: 경고 메시지 목록
        timestamp: 검증 시각
    """
    signal_id: str
    symbol: str
    action: str
    validation_result: ValidationResult
    confidence_score: float
    passed_rules: List[str] = field(default_factory=list)
    failed_rules: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "action": self.action,
            "validation_result": self.validation_result.value,
            "confidence_score": self.confidence_score,
            "passed_rules": self.passed_rules,
            "failed_rules": self.failed_rules,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    def is_approved(self) -> bool:
        """승인되었는지 확인"""
        return self.validation_result == ValidationResult.APPROVED

    def is_rejected(self) -> bool:
        """거부되었는지 확인"""
        return self.validation_result == ValidationResult.REJECTED

    def has_warnings(self) -> bool:
        """경고가 있는지 확인"""
        return len(self.warnings) > 0 or self.validation_result == ValidationResult.WARNING


@dataclass
class ValidationRule:
    """
    검증 규칙

    Attributes:
        rule_id: 규칙 ID
        name: 규칙 이름
        description: 규칙 설명
        weight: 규칙 가중치 (중요도)
        is_critical: 필수 규칙 여부 (실패 시 자동 거부)
    """
    rule_id: str
    name: str
    description: str
    weight: float = 1.0
    is_critical: bool = False

    def __repr__(self) -> str:
        critical_flag = " [CRITICAL]" if self.is_critical else ""
        return f"<ValidationRule {self.rule_id}: {self.name}{critical_flag}>"
