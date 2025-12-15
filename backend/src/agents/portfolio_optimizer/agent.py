"""
Portfolio Optimization Agent (포트폴리오 최적화 에이전트)

마코위츠 포트폴리오 이론 적용한 자동 리밸런싱

AI Enhancement:
- DeepSeek-V3.2 API를 사용한 AI 기반 포트폴리오 분석
- 규칙 기반 최적화 + AI 인사이트 결합
- 비용 최적화 (PERIODIC 샘플링, Response Caching)
"""

import logging
import uuid
import json
import numpy as np
from typing import Any, List, Dict, Optional
from datetime import datetime, timedelta

from ..base import BaseAgent, AgentTask
from .models import (
    RiskLevel,
    BotPerformanceMetrics,
    CorrelationMatrix,
    RiskContribution,
    PortfolioAnalysis,
    AllocationSuggestion,
    RebalancingSuggestion,
    RebalancingHistory,
)

logger = logging.getLogger(__name__)


class PortfolioOptimizationAgent(BaseAgent):
    """
    포트폴리오 최적화 에이전트

    주요 기능:
    1. 포트폴리오 분석 (각 봇 성과, 상관관계, 리스크 기여도)
    2. 최적 할당 제안 (마코위츠 모델)
    3. 자동 리밸런싱 (주간/월간)
    4. 분산 효과 측정

    작업 타입:
    - analyze_portfolio: 포트폴리오 분석
    - suggest_rebalancing: 리밸런싱 제안
    - apply_rebalancing: 리밸런싱 적용
    - calculate_correlation: 상관관계 계산
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        config: dict = None,
        redis_client=None,
        db_session=None,
        ai_service=None
    ):
        super().__init__(agent_id, name, config)
        self.redis_client = redis_client
        self.db_session = db_session
        self.ai_service = ai_service  # IntegratedAIService

        # 최적화 제약 조건
        cfg = config or {}
        self.min_allocation_percent = cfg.get("min_allocation_percent", 5.0)
        self.max_allocation_percent = cfg.get("max_allocation_percent", 40.0)
        self.rebalancing_threshold = cfg.get("rebalancing_threshold", 5.0)  # 5% 이상 차이나면 리밸런싱
        self.enable_ai = cfg.get("enable_ai", True)

        logger.info(
            f"PortfolioOptimizationAgent initialized: "
            f"allocation_range=[{self.min_allocation_percent}%, {self.max_allocation_percent}%], "
            f"AI={self.enable_ai}"
        )

    async def process_task(self, task: AgentTask) -> Any:
        """작업 처리"""
        task_type = task.task_type
        params = task.params

        logger.debug(f"PortfolioOptimizationAgent processing: {task_type}")

        if task_type == "analyze_portfolio":
            return await self._analyze_portfolio(params)

        elif task_type == "suggest_rebalancing":
            return await self._suggest_rebalancing(params)

        elif task_type == "apply_rebalancing":
            return await self._apply_rebalancing(params)

        elif task_type == "calculate_correlation":
            return await self._calculate_correlation(params)

        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _analyze_portfolio(self, params: dict) -> PortfolioAnalysis:
        """
        포트폴리오 분석

        Args:
            params: {
                "user_id": int,
                "bot_performance": List[BotPerformanceMetrics],
                "analysis_period_days": int
            }

        Returns:
            포트폴리오 분석 결과
        """
        user_id = params.get("user_id")
        bot_performance_data = params.get("bot_performance", [])
        period_days = params.get("analysis_period_days", 30)

        # BotPerformanceMetrics 객체 리스트 생성
        bot_performance = [
            BotPerformanceMetrics(**bot) for bot in bot_performance_data
        ]

        if not bot_performance:
            logger.warning(f"No bots found for user {user_id}")
            return PortfolioAnalysis(
                user_id=user_id,
                total_bots=0,
                total_equity=0.0,
            )

        # 1. 상관관계 계산
        correlation_matrix = await self._calculate_correlation_internal(bot_performance)

        # 2. 리스크 기여도 계산
        risk_contributions = await self._calculate_risk_contributions(
            bot_performance, correlation_matrix
        )

        # 3. 포트폴리오 전체 메트릭 계산
        total_equity = sum(bot.current_allocation_amount for bot in bot_performance)

        portfolio_metrics = self._calculate_portfolio_metrics(
            bot_performance, correlation_matrix
        )

        # 4. 분산 효과 측정
        diversification_ratio = self._calculate_diversification_ratio(
            bot_performance, correlation_matrix
        )

        analysis = PortfolioAnalysis(
            user_id=user_id,
            total_bots=len(bot_performance),
            total_equity=total_equity,
            bot_performance=bot_performance,
            correlation_matrix=correlation_matrix,
            risk_contributions=risk_contributions,
            portfolio_roi=portfolio_metrics["roi"],
            portfolio_sharpe=portfolio_metrics["sharpe"],
            portfolio_volatility=portfolio_metrics["volatility"],
            portfolio_max_drawdown=portfolio_metrics["max_drawdown"],
            diversification_ratio=diversification_ratio,
        )

        # Redis에 저장
        await self._save_analysis_to_redis(analysis)

        logger.info(
            f"Portfolio analysis for user {user_id}: "
            f"Sharpe={portfolio_metrics['sharpe']:.2f}, "
            f"Diversification={diversification_ratio:.2f}"
        )

        return analysis

    async def _suggest_rebalancing(self, params: dict) -> RebalancingSuggestion:
        """
        리밸런싱 제안

        Args:
            params: {
                "user_id": int,
                "risk_level": RiskLevel,
                "portfolio_analysis": PortfolioAnalysis
            }

        Returns:
            리밸런싱 제안
        """
        user_id = params.get("user_id")
        risk_level_str = params.get("risk_level", "moderate")
        risk_level = RiskLevel(risk_level_str)
        analysis_data = params.get("portfolio_analysis")

        # PortfolioAnalysis 객체 생성
        if isinstance(analysis_data, dict):
            analysis = PortfolioAnalysis(**analysis_data)
        else:
            analysis = analysis_data

        if not analysis.bot_performance:
            logger.warning(f"No bots to rebalance for user {user_id}")
            return RebalancingSuggestion(
                user_id=user_id,
                risk_level=risk_level,
                current_portfolio_sharpe=0.0,
                expected_portfolio_sharpe=0.0,
                sharpe_improvement_percent=0.0,
                current_portfolio_return=0.0,
                expected_portfolio_return=0.0,
                return_improvement_percent=0.0,
                current_portfolio_risk=0.0,
                expected_portfolio_risk=0.0,
                risk_reduction_percent=0.0,
            )

        # 1. 기대 수익률 및 공분산 행렬 준비
        expected_returns = np.array([bot.roi / 100 for bot in analysis.bot_performance])
        volatilities = np.array([bot.volatility / 100 for bot in analysis.bot_performance])

        # 상관관계 행렬 → 공분산 행렬
        if analysis.correlation_matrix:
            corr_matrix = np.array(analysis.correlation_matrix.matrix)
        else:
            # 상관관계 없으면 단위 행렬 (독립)
            n = len(expected_returns)
            corr_matrix = np.eye(n)

        # Cov = Corr × σ × σ'
        cov_matrix = corr_matrix * np.outer(volatilities, volatilities)

        # 2. 최적 가중치 계산 (마코위츠)
        optimal_weights = self._optimize_weights(
            expected_returns, cov_matrix, risk_level
        )

        # 3. 제안 생성
        suggestions = []
        for i, bot in enumerate(analysis.bot_performance):
            current_alloc = bot.current_allocation_percent
            suggested_alloc = optimal_weights[i] * 100

            change = suggested_alloc - current_alloc

            # 변경폭이 임계값 이상일 때만 제안
            if abs(change) >= self.rebalancing_threshold:
                reason = self._explain_allocation_change(
                    bot, suggested_alloc, current_alloc, analysis
                )

                suggestion = AllocationSuggestion(
                    bot_instance_id=bot.bot_instance_id,
                    bot_name=bot.bot_name,
                    current_allocation_percent=current_alloc,
                    suggested_allocation_percent=suggested_alloc,
                    change_percent=change,
                    reason=reason,
                    expected_contribution={
                        "roi": bot.roi,
                        "sharpe": bot.sharpe_ratio,
                        "weight": optimal_weights[i],
                    },
                )
                suggestions.append(suggestion)

        # 4. 예상 개선 효과 계산
        current_metrics = {
            "sharpe": analysis.portfolio_sharpe,
            "return": analysis.portfolio_roi,
            "risk": analysis.portfolio_volatility,
        }

        expected_metrics = self._calculate_expected_portfolio_metrics(
            expected_returns, cov_matrix, optimal_weights
        )

        sharpe_improvement = (
            (expected_metrics["sharpe"] - current_metrics["sharpe"])
            / max(abs(current_metrics["sharpe"]), 0.01)
            * 100
        )

        return_improvement = (
            (expected_metrics["return"] - current_metrics["return"])
            / max(abs(current_metrics["return"]), 0.01)
            * 100
        )

        risk_reduction = (
            (current_metrics["risk"] - expected_metrics["risk"])
            / max(current_metrics["risk"], 0.01)
            * 100
        )

        rebalancing = RebalancingSuggestion(
            user_id=user_id,
            risk_level=risk_level,
            suggestions=suggestions,
            current_portfolio_sharpe=current_metrics["sharpe"],
            expected_portfolio_sharpe=expected_metrics["sharpe"],
            sharpe_improvement_percent=sharpe_improvement,
            current_portfolio_return=current_metrics["return"],
            expected_portfolio_return=expected_metrics["return"],
            return_improvement_percent=return_improvement,
            current_portfolio_risk=current_metrics["risk"],
            expected_portfolio_risk=expected_metrics["risk"],
            risk_reduction_percent=risk_reduction,
            constraints={
                "min_allocation": self.min_allocation_percent,
                "max_allocation": self.max_allocation_percent,
                "risk_level": risk_level.value,
            },
        )

        # Redis에 저장
        await self._save_suggestion_to_redis(rebalancing)

        logger.info(
            f"Rebalancing suggestion for user {user_id}: "
            f"{len(suggestions)} changes, "
            f"expected Sharpe improvement: {sharpe_improvement:+.1f}%"
        )

        return rebalancing

    async def _apply_rebalancing(self, params: dict) -> RebalancingHistory:
        """
        리밸런싱 적용

        Args:
            params: {
                "user_id": int,
                "suggestion": RebalancingSuggestion,
                "auto_execute": bool
            }

        Returns:
            리밸런싱 이력
        """
        user_id = params.get("user_id")
        suggestion_data = params.get("suggestion")
        auto_execute = params.get("auto_execute", False)

        # RebalancingSuggestion 객체 생성
        if isinstance(suggestion_data, dict):
            suggestion = RebalancingSuggestion(**suggestion_data)
        else:
            suggestion = suggestion_data

        # 적용 전 스냅샷
        before_snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "allocations": {
                s.bot_instance_id: s.current_allocation_percent
                for s in suggestion.suggestions
            },
        }

        # 리밸런싱 적용 (DB 업데이트)
        if auto_execute and self.db_session:
            # TODO: 실제 DB 업데이트 로직
            # for sug in suggestion.suggestions:
            #     await self.db_session.execute(
            #         update(BotInstance)
            #         .where(BotInstance.id == sug.bot_instance_id)
            #         .values(allocation_percent=sug.suggested_allocation_percent)
            #     )
            # await self.db_session.commit()
            logger.info(f"Applied rebalancing for user {user_id}")

        # 적용 후 스냅샷
        after_snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "allocations": {
                s.bot_instance_id: s.suggested_allocation_percent
                for s in suggestion.suggestions
            },
        }

        # 이력 저장
        history = RebalancingHistory(
            rebalancing_id=f"rebal_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            executed_at=datetime.utcnow(),
            suggestions_applied=suggestion.suggestions,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
        )

        # Redis에 저장
        await self._save_history_to_redis(history)

        return history

    async def _calculate_correlation(self, params: dict) -> CorrelationMatrix:
        """상관관계 계산 (외부 호출용)"""
        bot_performance_data = params.get("bot_performance", [])
        bot_performance = [
            BotPerformanceMetrics(**bot) for bot in bot_performance_data
        ]

        return await self._calculate_correlation_internal(bot_performance)

    # ==================== Helper Methods ====================

    async def _calculate_correlation_internal(
        self, bot_performance: List[BotPerformanceMetrics]
    ) -> Optional[CorrelationMatrix]:
        """상관관계 계산 (내부 로직)"""
        if len(bot_performance) < 2:
            return None

        # TODO: 실제로는 각 봇의 일일 수익률 시계열 데이터 필요
        # 여기서는 간소화하여 랜덤 상관관계 생성 (예시)
        n = len(bot_performance)
        bot_ids = [bot.bot_instance_id for bot in bot_performance]

        # 실제 구현 시: 각 봇의 거래 내역에서 일일 수익률 계산 후
        # np.corrcoef() 사용
        # 예시: 대각선 1.0, 나머지는 0.3~0.7 사이
        matrix = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                # 같은 심볼이면 상관관계 높음
                if bot_performance[i].symbol == bot_performance[j].symbol:
                    corr = 0.7
                else:
                    corr = 0.3
                matrix[i][j] = corr
                matrix[j][i] = corr

        return CorrelationMatrix(bot_ids=bot_ids, matrix=matrix.tolist())

    async def _calculate_risk_contributions(
        self,
        bot_performance: List[BotPerformanceMetrics],
        correlation_matrix: Optional[CorrelationMatrix],
    ) -> List[RiskContribution]:
        """리스크 기여도 계산"""
        if not correlation_matrix:
            return []

        # 현재 가중치
        weights = np.array([bot.current_allocation_percent / 100 for bot in bot_performance])
        volatilities = np.array([bot.volatility / 100 for bot in bot_performance])

        corr_matrix = np.array(correlation_matrix.matrix)
        cov_matrix = corr_matrix * np.outer(volatilities, volatilities)

        # 포트폴리오 분산
        port_variance = weights @ cov_matrix @ weights
        port_vol = np.sqrt(port_variance)

        # 한계 VaR (marginal contribution to risk)
        marginal_var = (cov_matrix @ weights) / port_vol

        # 구성 VaR (component contribution)
        component_var = weights * marginal_var

        # 기여 비율
        contributions = []
        for i, bot in enumerate(bot_performance):
            contrib_percent = (component_var[i] / port_vol) * 100 if port_vol > 0 else 0

            contributions.append(
                RiskContribution(
                    bot_instance_id=bot.bot_instance_id,
                    bot_name=bot.bot_name,
                    marginal_var=marginal_var[i],
                    component_var=component_var[i],
                    contribution_percent=contrib_percent,
                )
            )

        return contributions

    def _calculate_portfolio_metrics(
        self,
        bot_performance: List[BotPerformanceMetrics],
        correlation_matrix: Optional[CorrelationMatrix],
    ) -> Dict[str, float]:
        """포트폴리오 전체 메트릭 계산"""
        weights = np.array([bot.current_allocation_percent / 100 for bot in bot_performance])

        # ROI: 가중 평균
        portfolio_roi = sum(bot.roi * w for bot, w in zip(bot_performance, weights))

        # 샤프 비율: 가중 평균 (간소화)
        portfolio_sharpe = sum(bot.sharpe_ratio * w for bot, w in zip(bot_performance, weights))

        # 변동성: 공분산 고려
        volatilities = np.array([bot.volatility for bot in bot_performance])

        if correlation_matrix:
            corr_matrix = np.array(correlation_matrix.matrix)
            cov_matrix = corr_matrix * np.outer(volatilities, volatilities)
            portfolio_variance = weights @ cov_matrix @ weights
            portfolio_volatility = np.sqrt(portfolio_variance)
        else:
            # 상관관계 없으면 단순 가중 평균
            portfolio_volatility = sum(vol * w for vol, w in zip(volatilities, weights))

        # MDD: 가중 평균
        portfolio_mdd = sum(bot.max_drawdown * w for bot, w in zip(bot_performance, weights))

        return {
            "roi": portfolio_roi,
            "sharpe": portfolio_sharpe,
            "volatility": portfolio_volatility,
            "max_drawdown": portfolio_mdd,
        }

    def _calculate_diversification_ratio(
        self,
        bot_performance: List[BotPerformanceMetrics],
        correlation_matrix: Optional[CorrelationMatrix],
    ) -> float:
        """
        분산 비율 계산

        Diversification Ratio = (가중 평균 변동성) / (포트폴리오 변동성)
        1.0 = 분산 효과 없음
        >1.0 = 분산 효과 있음
        """
        if not correlation_matrix or len(bot_performance) < 2:
            return 1.0

        weights = np.array([bot.current_allocation_percent / 100 for bot in bot_performance])
        volatilities = np.array([bot.volatility for bot in bot_performance])

        # 가중 평균 변동성
        weighted_avg_vol = sum(vol * w for vol, w in zip(volatilities, weights))

        # 포트폴리오 변동성 (상관관계 고려)
        corr_matrix = np.array(correlation_matrix.matrix)
        cov_matrix = corr_matrix * np.outer(volatilities, volatilities)
        port_variance = weights @ cov_matrix @ weights
        port_vol = np.sqrt(port_variance)

        if port_vol == 0:
            return 1.0

        return weighted_avg_vol / port_vol

    def _optimize_weights(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        risk_level: RiskLevel,
    ) -> np.ndarray:
        """
        최적 가중치 계산 (마코위츠 최적화)

        Args:
            expected_returns: 기대 수익률 벡터
            cov_matrix: 공분산 행렬
            risk_level: 리스크 수준

        Returns:
            최적 가중치 벡터
        """
        try:
            from scipy.optimize import minimize

            n_assets = len(expected_returns)

            def portfolio_variance(weights):
                return weights @ cov_matrix @ weights

            def portfolio_return(weights):
                return np.dot(weights, expected_returns)

            def sharpe_ratio(weights):
                ret = portfolio_return(weights)
                vol = np.sqrt(portfolio_variance(weights))
                return -ret / vol if vol > 0 else 0  # negative for minimization

            # 제약 조건
            constraints = [
                {"type": "eq", "fun": lambda w: np.sum(w) - 1},  # 합 = 1
            ]

            # 경계: 각 봇 최소~최대 할당
            bounds = tuple(
                (self.min_allocation_percent / 100, self.max_allocation_percent / 100)
                for _ in range(n_assets)
            )

            # 목적 함수 선택
            if risk_level == RiskLevel.CONSERVATIVE:
                objective = portfolio_variance  # 최소 분산
            elif risk_level == RiskLevel.MODERATE:
                objective = sharpe_ratio  # 최대 샤프
            else:  # AGGRESSIVE
                objective = lambda w: -portfolio_return(w)  # 최대 수익

            # 초기값: 균등 배분
            initial_weights = np.array([1.0 / n_assets] * n_assets)

            # 최적화 실행
            result = minimize(
                objective,
                initial_weights,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 1000},
            )

            if result.success:
                return result.x
            else:
                logger.warning(f"Optimization failed: {result.message}")
                return initial_weights

        except ImportError:
            logger.warning("scipy not installed, using equal weights")
            return np.array([1.0 / len(expected_returns)] * len(expected_returns))

    def _calculate_expected_portfolio_metrics(
        self, expected_returns: np.ndarray, cov_matrix: np.ndarray, weights: np.ndarray
    ) -> Dict[str, float]:
        """예상 포트폴리오 메트릭 계산"""
        port_return = np.dot(weights, expected_returns)
        port_variance = weights @ cov_matrix @ weights
        port_vol = np.sqrt(port_variance)
        port_sharpe = port_return / port_vol if port_vol > 0 else 0

        return {
            "return": port_return * 100,  # percentage
            "risk": port_vol * 100,  # percentage
            "sharpe": port_sharpe,
        }

    def _explain_allocation_change(
        self,
        bot: BotPerformanceMetrics,
        suggested_alloc: float,
        current_alloc: float,
        analysis: PortfolioAnalysis,
    ) -> str:
        """할당 변경 이유 설명"""
        change = suggested_alloc - current_alloc

        if change > 0:
            # 증가
            reasons = []
            if bot.sharpe_ratio > 1.5:
                reasons.append(f"높은 샤프 비율 ({bot.sharpe_ratio:.2f})")
            if bot.win_rate > 60:
                reasons.append(f"높은 승률 ({bot.win_rate:.1f}%)")
            if bot.volatility < 10:
                reasons.append("낮은 변동성")

            return "비중 증가: " + ", ".join(reasons) if reasons else "성과 개선"

        else:
            # 감소
            reasons = []
            if bot.sharpe_ratio < 0.5:
                reasons.append(f"낮은 샤프 비율 ({bot.sharpe_ratio:.2f})")
            if bot.max_drawdown < -15:
                reasons.append(f"큰 낙폭 ({bot.max_drawdown:.1f}%)")
            if bot.volatility > 20:
                reasons.append("높은 변동성")

            return "비중 감소: " + ", ".join(reasons) if reasons else "성과 저조"

    async def _save_analysis_to_redis(self, analysis: PortfolioAnalysis):
        """Redis에 분석 결과 저장"""
        if not self.redis_client:
            return

        try:
            key = f"agent:portfolio:analysis:user:{analysis.user_id}"
            await self.redis_client.setex(key, 3600, analysis.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to save analysis to Redis: {e}")

    async def _save_suggestion_to_redis(self, suggestion: RebalancingSuggestion):
        """Redis에 제안 저장"""
        if not self.redis_client:
            return

        try:
            key = f"agent:portfolio:suggestion:user:{suggestion.user_id}"
            await self.redis_client.setex(key, 7200, suggestion.model_dump_json())  # 2시간
        except Exception as e:
            logger.error(f"Failed to save suggestion to Redis: {e}")

    async def _save_history_to_redis(self, history: RebalancingHistory):
        """Redis에 이력 저장"""
        if not self.redis_client:
            return

        try:
            key = f"agent:portfolio:history:{history.rebalancing_id}"
            await self.redis_client.setex(key, 2592000, history.model_dump_json())  # 30일

            # 사용자별 이력 리스트
            list_key = f"agent:portfolio:user:{history.user_id}:history"
            await self.redis_client.lpush(list_key, history.rebalancing_id)
            await self.redis_client.ltrim(list_key, 0, 19)  # 최대 20개 유지
        except Exception as e:
            logger.error(f"Failed to save history to Redis: {e}")

    async def _analyze_portfolio_with_ai(
        self,
        user_id: int,
        analysis: PortfolioAnalysis,
        bot_performance: List[BotPerformanceMetrics],
        risk_level: RiskLevel
    ) -> Optional[Dict[str, Any]]:
        """
        AI 기반 포트폴리오 분석 (DeepSeek-V3.2)

        Args:
            user_id: 사용자 ID
            analysis: 규칙 기반 분석 결과
            bot_performance: 봇 성과 목록
            risk_level: 리스크 레벨

        Returns:
            {"insights": List[str], "warnings": List[str], "recommendations": List[str]} 또는 None
        """
        if not self.enable_ai or not self.ai_service:
            return None

        # 시스템 프롬프트
        system_prompt = """You are an expert portfolio management AI specializing in cryptocurrency trading.

Analyze portfolio composition and provide:
- Key insights about performance
- Warnings about risks
- Specific recommendations for improvement

Return ONLY valid JSON:
{"insights": ["insight1", "insight2"], "warnings": ["warning1"], "recommendations": ["rec1", "rec2"]}"""

        # 봇 성과 요약
        bots_summary = "\n".join([
            f"- Bot {bot.bot_id}: ROI={bot.roi_percent:.1f}%, Sharpe={bot.sharpe_ratio:.2f}, "
            f"Win Rate={bot.win_rate:.1f}%, Volatility={bot.volatility:.1f}%"
            for bot in bot_performance[:10]  # 최대 10개만
        ])

        # 사용자 프롬프트
        user_prompt = f"""Analyze this cryptocurrency trading portfolio:

Total Bots: {len(bot_performance)}
Risk Level: {risk_level.value}

Portfolio Metrics:
- Total Return: {analysis.total_return_percent:.1f}%
- Total Risk: {analysis.total_risk_percent:.1f}%
- Portfolio Sharpe: {analysis.portfolio_sharpe:.2f}
- Diversification Ratio: {analysis.diversification_ratio:.2f}

Top Bots Performance:
{bots_summary}

Correlation Analysis:
- Average Correlation: {analysis.correlation_matrix.average_correlation:.2f}
- Max Correlation: {analysis.correlation_matrix.max_correlation:.2f}

Risk Contributions:
{', '.join([f'{rc.bot_id}={rc.contribution_percent:.1f}%' for rc in analysis.risk_contributions[:5]])}

Provide insights, warnings, and recommendations in JSON:"""

        try:
            # AI API 호출 (비용 최적화 적용)
            result = await self.ai_service.call_ai(
                agent_type="portfolio_optimizer",
                prompt=user_prompt,
                context={
                    "user_id": user_id,
                    "bot_count": len(bot_performance),
                    "risk_level": risk_level.value,
                    "portfolio_sharpe": analysis.portfolio_sharpe,
                },
                system_prompt=system_prompt,
                response_type="portfolio_optimization",
                temperature=0.3,
                max_tokens=400,
                enable_caching=True,
                enable_sampling=True
            )

            response_text = result.get("response", "")

            if not response_text:
                return None

            # JSON 파싱
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text)

            if json_match:
                ai_analysis = json.loads(json_match.group())

                insights = ai_analysis.get("insights", [])
                warnings = ai_analysis.get("warnings", [])
                recommendations = ai_analysis.get("recommendations", [])

                logger.info(
                    f"🤖 AI Portfolio Analysis: {len(insights)} insights, "
                    f"{len(warnings)} warnings, {len(recommendations)} recommendations"
                )

                return {
                    "insights": insights,
                    "warnings": warnings,
                    "recommendations": recommendations
                }

            return None

        except Exception as e:
            logger.error(f"AI portfolio analysis error: {e}", exc_info=True)
            return None
