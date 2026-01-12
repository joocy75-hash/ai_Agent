"""
A/B Tester - ML 모델 A/B 테스트 프레임워크

두 모델(또는 전략)을 동시에 실행하여 성능 비교
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class TestGroup(str, Enum):
    """테스트 그룹"""
    CONTROL = "control"  # 기존 모델/전략
    TREATMENT = "treatment"  # 새 모델/전략


@dataclass
class ABTestResult:
    """A/B 테스트 결과"""
    test_id: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # 샘플 수
    control_samples: int = 0
    treatment_samples: int = 0

    # 성과 지표
    control_win_rate: float = 0.0
    treatment_win_rate: float = 0.0

    control_avg_pnl: float = 0.0
    treatment_avg_pnl: float = 0.0

    control_sharpe: float = 0.0
    treatment_sharpe: float = 0.0

    # 통계적 유의성
    p_value: float = 1.0
    is_significant: bool = False  # p < 0.05
    confidence_level: float = 0.0

    # 승자
    winner: Optional[TestGroup] = None
    improvement: float = 0.0  # treatment vs control 개선율 (%)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_id': self.test_id,
            'duration': str(self.end_time - self.start_time) if self.start_time and self.end_time else None,
            'control_samples': self.control_samples,
            'treatment_samples': self.treatment_samples,
            'control_win_rate': round(self.control_win_rate, 2),
            'treatment_win_rate': round(self.treatment_win_rate, 2),
            'control_avg_pnl': round(self.control_avg_pnl, 4),
            'treatment_avg_pnl': round(self.treatment_avg_pnl, 4),
            'p_value': round(self.p_value, 4),
            'is_significant': self.is_significant,
            'winner': self.winner.value if self.winner else None,
            'improvement': round(self.improvement, 2),
        }


@dataclass
class ABTestConfig:
    """A/B 테스트 설정"""
    test_id: str = ""
    control_ratio: float = 0.5  # Control 그룹 비율
    min_samples: int = 100  # 최소 샘플 수
    significance_level: float = 0.05  # 유의수준
    metric: str = "pnl"  # 비교 지표 (pnl, win_rate, sharpe)


class ABTester:
    """
    A/B 테스트 프레임워크

    Usage:
    ```python
    tester = ABTester(config=ABTestConfig(test_id="ml_v2_test"))

    # 각 거래에서 그룹 할당
    group = tester.assign_group()

    # 결과 기록
    if group == TestGroup.CONTROL:
        tester.record_control(pnl=profit, won=True)
    else:
        tester.record_treatment(pnl=profit, won=True)

    # 결과 분석
    result = tester.analyze()
    ```
    """

    def __init__(self, config: Optional[ABTestConfig] = None):
        self.config = config or ABTestConfig()
        if not self.config.test_id:
            self.config.test_id = f"ab_test_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # 결과 저장
        self.control_results: List[Dict[str, Any]] = []
        self.treatment_results: List[Dict[str, Any]] = []

        self.start_time = datetime.utcnow()
        self._is_running = True

        logger.info(f"A/B Test '{self.config.test_id}' started")

    def assign_group(self) -> TestGroup:
        """
        그룹 할당 (랜덤)

        Returns:
            할당된 그룹
        """
        if random.random() < self.config.control_ratio:
            return TestGroup.CONTROL
        return TestGroup.TREATMENT

    def record_control(self, pnl: float, won: bool, metadata: Optional[Dict] = None):
        """Control 그룹 결과 기록"""
        self.control_results.append({
            'pnl': pnl,
            'won': won,
            'timestamp': datetime.utcnow(),
            'metadata': metadata or {},
        })

    def record_treatment(self, pnl: float, won: bool, metadata: Optional[Dict] = None):
        """Treatment 그룹 결과 기록"""
        self.treatment_results.append({
            'pnl': pnl,
            'won': won,
            'timestamp': datetime.utcnow(),
            'metadata': metadata or {},
        })

    def analyze(self) -> ABTestResult:
        """
        A/B 테스트 결과 분석

        Returns:
            ABTestResult
        """
        result = ABTestResult(
            test_id=self.config.test_id,
            start_time=self.start_time,
            end_time=datetime.utcnow(),
            control_samples=len(self.control_results),
            treatment_samples=len(self.treatment_results),
        )

        if not self.control_results or not self.treatment_results:
            logger.warning("Insufficient samples for analysis")
            return result

        # Control 그룹 통계
        control_pnls = [r['pnl'] for r in self.control_results]
        control_wins = [r['won'] for r in self.control_results]

        result.control_win_rate = sum(control_wins) / len(control_wins) * 100
        result.control_avg_pnl = np.mean(control_pnls)
        if len(control_pnls) > 1 and np.std(control_pnls) > 0:
            result.control_sharpe = np.mean(control_pnls) / np.std(control_pnls) * np.sqrt(252)

        # Treatment 그룹 통계
        treatment_pnls = [r['pnl'] for r in self.treatment_results]
        treatment_wins = [r['won'] for r in self.treatment_results]

        result.treatment_win_rate = sum(treatment_wins) / len(treatment_wins) * 100
        result.treatment_avg_pnl = np.mean(treatment_pnls)
        if len(treatment_pnls) > 1 and np.std(treatment_pnls) > 0:
            result.treatment_sharpe = np.mean(treatment_pnls) / np.std(treatment_pnls) * np.sqrt(252)

        # 통계적 유의성 검정 (Welch's t-test)
        result.p_value = self._welch_ttest(control_pnls, treatment_pnls)
        result.is_significant = result.p_value < self.config.significance_level
        result.confidence_level = (1 - result.p_value) * 100

        # 승자 결정
        if result.is_significant:
            if result.treatment_avg_pnl > result.control_avg_pnl:
                result.winner = TestGroup.TREATMENT
                if result.control_avg_pnl != 0:
                    result.improvement = (result.treatment_avg_pnl - result.control_avg_pnl) / abs(result.control_avg_pnl) * 100
            else:
                result.winner = TestGroup.CONTROL
                if result.treatment_avg_pnl != 0:
                    result.improvement = (result.control_avg_pnl - result.treatment_avg_pnl) / abs(result.treatment_avg_pnl) * 100

        logger.info(
            f"A/B Test '{self.config.test_id}' analysis: "
            f"Control={result.control_avg_pnl:.4f}, "
            f"Treatment={result.treatment_avg_pnl:.4f}, "
            f"p={result.p_value:.4f}, "
            f"Winner={result.winner}"
        )

        return result

    def _welch_ttest(self, group1: List[float], group2: List[float]) -> float:
        """
        Welch's t-test (unequal variance t-test)

        두 그룹의 평균이 통계적으로 다른지 검정
        """
        n1, n2 = len(group1), len(group2)

        if n1 < 2 or n2 < 2:
            return 1.0

        mean1, mean2 = np.mean(group1), np.mean(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)

        # t-statistic
        se = np.sqrt(var1/n1 + var2/n2)
        if se == 0:
            return 1.0

        t_stat = (mean1 - mean2) / se

        # Welch-Satterthwaite degrees of freedom
        num = (var1/n1 + var2/n2) ** 2
        denom = (var1/n1)**2/(n1-1) + (var2/n2)**2/(n2-1)
        num / denom if denom > 0 else 1

        # p-value (two-tailed) using t-distribution approximation
        # 간단한 근사: 정규분포 사용
        from math import erf, sqrt
        p_value = 2 * (1 - 0.5 * (1 + erf(abs(t_stat) / sqrt(2))))

        return p_value

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        total_samples = len(self.control_results) + len(self.treatment_results)
        progress = min(total_samples / self.config.min_samples * 100, 100)

        return {
            'test_id': self.config.test_id,
            'is_running': self._is_running,
            'control_samples': len(self.control_results),
            'treatment_samples': len(self.treatment_results),
            'total_samples': total_samples,
            'min_samples': self.config.min_samples,
            'progress': round(progress, 1),
            'can_analyze': total_samples >= self.config.min_samples,
        }

    def stop(self):
        """테스트 종료"""
        self._is_running = False
        logger.info(f"A/B Test '{self.config.test_id}' stopped")

    def reset(self):
        """테스트 리셋"""
        self.control_results.clear()
        self.treatment_results.clear()
        self.start_time = datetime.utcnow()
        self._is_running = True
        logger.info(f"A/B Test '{self.config.test_id}' reset")
