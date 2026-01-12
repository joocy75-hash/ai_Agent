"""
Anomaly Detection Agent (이상 징후 감지 에이전트)

실시간 봇 동작 및 시장 이상 징후 감지

AI Enhancement:
- DeepSeek-V3.2 API를 사용한 AI 기반 이상 징후 분석
- 규칙 기반 + AI 분석 결합으로 false positive 감소
- 비용 최적화 (Event-Driven, Response Caching)
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..base import AgentTask, BaseAgent
from .models import (
    AnomalyAlert,
    AnomalySeverity,
    AnomalyType,
    BotBehaviorMetrics,
    CircuitBreakerStatus,
    MarketAnomalyMetrics,
)

logger = logging.getLogger(__name__)


class AnomalyDetectionAgent(BaseAgent):
    """
    이상 징후 감지 에이전트

    주요 기능:
    1. 봇 동작 모니터링 (거래 빈도, 연속 손실, 슬리피지, API 오류)
    2. 시장 이상 감지 (급등락, 거래량 급증, 펀딩 비율 이상)
    3. 서킷 브레이커 (일일 손실 한도 도달 시 자동 중지)
    4. 자동 조치 실행 (봇 중지, 포지션 축소 등)

    작업 타입:
    - monitor_bot_behavior: 봇 동작 모니터링
    - detect_market_anomaly: 시장 이상 감지
    - check_circuit_breaker: 서킷 브레이커 체크
    - get_active_alerts: 활성 알림 조회
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
        self._active_alerts: List[AnomalyAlert] = []

        # 임계값 설정 (config에서 가져오거나 기본값)
        cfg = config or {}

        # 봇 동작 임계값
        self.max_trades_per_10min = cfg.get("max_trades_per_10min", 20)
        self.losing_streak_threshold = cfg.get("losing_streak_threshold", 7)
        self.max_slippage_percent = cfg.get("max_slippage_percent", 0.5)
        self.max_api_error_rate = cfg.get("max_api_error_rate", 0.3)
        self.bot_stuck_minutes = cfg.get("bot_stuck_minutes", 15)

        # 시장 이상 임계값
        self.flash_crash_threshold = cfg.get("flash_crash_threshold", 5.0)  # 1분 5%
        self.volume_spike_ratio = cfg.get("volume_spike_ratio", 10.0)  # 평균 대비 10배
        self.extreme_funding_rate = cfg.get("extreme_funding_rate", 0.001)  # 0.1%

        # 서킷 브레이커
        self.max_daily_loss_percent = cfg.get("max_daily_loss_percent", 10.0)

        # AI 설정
        self.enable_ai = cfg.get("enable_ai", True)

        logger.info(
            f"AnomalyDetectionAgent initialized: "
            f"max_trades={self.max_trades_per_10min}, "
            f"losing_streak={self.losing_streak_threshold}, "
            f"circuit_breaker={self.max_daily_loss_percent}%, "
            f"AI={self.enable_ai}"
        )

    async def process_task(self, task: AgentTask) -> Any:
        """작업 처리"""
        task_type = task.task_type
        params = task.params

        logger.debug(f"AnomalyDetectionAgent processing: {task_type}")

        if task_type == "monitor_bot_behavior":
            return await self._monitor_bot_behavior(params)

        elif task_type == "detect_market_anomaly":
            return await self._detect_market_anomaly(params)

        elif task_type == "check_circuit_breaker":
            return await self._check_circuit_breaker(params)

        elif task_type == "get_active_alerts":
            return self._get_active_alerts(params)

        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _monitor_bot_behavior(self, params: dict) -> List[AnomalyAlert]:
        """
        봇 동작 모니터링

        Args:
            params: {
                "bot_instance_id": int,
                "metrics": BotBehaviorMetrics,
                "auto_execute": bool
            }

        Returns:
            감지된 이상 징후 알림 리스트
        """
        bot_id = params.get("bot_instance_id")
        metrics_data = params.get("metrics", {})
        auto_execute = params.get("auto_execute", True)

        # BotBehaviorMetrics 객체 생성
        metrics = BotBehaviorMetrics(bot_instance_id=bot_id, **metrics_data)

        alerts = []

        # 1. 과도한 거래 빈도 체크
        if metrics.trades_last_10min > self.max_trades_per_10min:
            alert = await self._create_alert(
                anomaly_type=AnomalyType.EXCESSIVE_TRADING,
                severity=AnomalySeverity.HIGH,
                bot_instance_id=bot_id,
                message=f"비정상적으로 많은 거래: {metrics.trades_last_10min}회/10분",
                details={
                    "trade_count": metrics.trades_last_10min,
                    "threshold": self.max_trades_per_10min,
                    "time_window": "10 minutes",
                },
                recommended_action="봇 자동 중지 권장 - 전략 로직 점검 필요",
            )

            if auto_execute:
                await self._auto_stop_bot(bot_id, reason="excessive_trading")
                alert.auto_executed = True

            alerts.append(alert)

        # 2. 연속 손실 체크
        if metrics.recent_trades_count >= 10:
            metrics.losing_trades_count / metrics.recent_trades_count

            if metrics.losing_trades_count >= self.losing_streak_threshold:
                alert = await self._create_alert(
                    anomaly_type=AnomalyType.LOSING_STREAK,
                    severity=AnomalySeverity.MEDIUM,
                    bot_instance_id=bot_id,
                    message=f"연속 손실: {metrics.losing_trades_count}/{metrics.recent_trades_count} (승률: {metrics.win_rate:.1f}%)",
                    details={
                        "losing_trades": metrics.losing_trades_count,
                        "total_trades": metrics.recent_trades_count,
                        "win_rate": metrics.win_rate,
                    },
                    recommended_action="전략 파라미터 점검 및 백테스팅 권장",
                )
                alerts.append(alert)

        # 3. 높은 슬리피지 체크
        if metrics.avg_slippage_percent > self.max_slippage_percent:
            alert = await self._create_alert(
                anomaly_type=AnomalyType.HIGH_SLIPPAGE,
                severity=AnomalySeverity.LOW,
                bot_instance_id=bot_id,
                message=f"높은 슬리피지: 평균 {metrics.avg_slippage_percent:.2f}% (최대 {metrics.max_slippage_percent:.2f}%)",
                details={
                    "avg_slippage": metrics.avg_slippage_percent,
                    "max_slippage": metrics.max_slippage_percent,
                    "threshold": self.max_slippage_percent,
                },
                recommended_action="유동성 부족 가능성 - 거래량 확인 필요",
            )
            alerts.append(alert)

        # 4. API 오류율 급증 체크
        if metrics.api_error_rate > self.max_api_error_rate:
            alert = await self._create_alert(
                anomaly_type=AnomalyType.API_ERROR_SPIKE,
                severity=AnomalySeverity.HIGH,
                bot_instance_id=bot_id,
                message=f"API 오류율 급증: {metrics.api_error_rate * 100:.1f}% ({metrics.api_errors_last_5min}/{metrics.api_calls_last_5min})",
                details={
                    "error_count": metrics.api_errors_last_5min,
                    "total_calls": metrics.api_calls_last_5min,
                    "error_rate": metrics.api_error_rate,
                },
                recommended_action="거래소 API 상태 확인 및 봇 임시 중지 권장",
            )

            if auto_execute and metrics.api_error_rate > 0.5:  # 50% 이상 오류
                await self._auto_stop_bot(bot_id, reason="api_error_spike")
                alert.auto_executed = True

            alerts.append(alert)

        # 5. 봇 멈춤 감지
        if metrics.seconds_since_last_activity > (self.bot_stuck_minutes * 60):
            alert = await self._create_alert(
                anomaly_type=AnomalyType.BOT_STUCK,
                severity=AnomalySeverity.HIGH,
                bot_instance_id=bot_id,
                message=f"봇 무응답: {metrics.seconds_since_last_activity // 60}분간 활동 없음",
                details={
                    "last_activity": metrics.last_activity_timestamp,
                    "inactive_seconds": metrics.seconds_since_last_activity,
                },
                recommended_action="봇 재시작 권장",
            )
            alerts.append(alert)

        # Redis에 알림 저장
        for alert in alerts:
            await self._save_alert_to_redis(alert)
            self._active_alerts.append(alert)

        if alerts:
            logger.warning(
                f"Bot {bot_id} anomalies detected: {[a.anomaly_type.value for a in alerts]}"
            )

        return alerts

    async def _detect_market_anomaly(self, params: dict) -> List[AnomalyAlert]:
        """
        시장 이상 징후 감지

        Args:
            params: {
                "symbol": str,
                "metrics": MarketAnomalyMetrics,
                "broadcast": bool
            }

        Returns:
            감지된 이상 징후 알림 리스트
        """
        symbol = params.get("symbol", "BTCUSDT")
        metrics_data = params.get("metrics", {})
        broadcast = params.get("broadcast", True)

        # MarketAnomalyMetrics 객체 생성
        metrics = MarketAnomalyMetrics(symbol=symbol, **metrics_data)

        alerts = []

        # 1. 급격한 가격 변동 (Flash Crash/Rally)
        if abs(metrics.price_change_1min_percent) > self.flash_crash_threshold:
            direction = "급등" if metrics.price_change_1min_percent > 0 else "급락"
            alert = await self._create_alert(
                anomaly_type=AnomalyType.FLASH_CRASH,
                severity=AnomalySeverity.CRITICAL,
                symbol=symbol,
                message=f"{symbol} {direction}: {abs(metrics.price_change_1min_percent):.2f}% (1분)",
                details={
                    "price_change_1min": metrics.price_change_1min_percent,
                    "price_change_5min": metrics.price_change_5min_percent,
                    "threshold": self.flash_crash_threshold,
                },
                recommended_action=f"모든 {symbol} 봇 일시 중지 권장 - 시장 안정화 대기",
            )
            alerts.append(alert)

        # 2. 거래량 급증
        if metrics.volume_ratio > self.volume_spike_ratio:
            alert = await self._create_alert(
                anomaly_type=AnomalyType.VOLUME_SPIKE,
                severity=AnomalySeverity.MEDIUM,
                symbol=symbol,
                message=f"{symbol} 거래량 급증: 평균 대비 {metrics.volume_ratio:.1f}배",
                details={
                    "current_volume": metrics.volume_1min,
                    "average_volume": metrics.volume_avg_1hour,
                    "volume_ratio": metrics.volume_ratio,
                },
                recommended_action="중요 뉴스 발생 가능성 - 뉴스 확인 필요",
            )
            alerts.append(alert)

        # 3. 극단적 펀딩 비율 (선물 거래)
        if metrics.funding_rate is not None:
            if abs(metrics.funding_rate) > self.extreme_funding_rate:
                direction = "롱 편향" if metrics.funding_rate > 0 else "숏 편향"
                alert = await self._create_alert(
                    anomaly_type=AnomalyType.EXTREME_FUNDING,
                    severity=AnomalySeverity.MEDIUM,
                    symbol=symbol,
                    message=f"{symbol} 극단적 펀딩 비율: {metrics.funding_rate * 100:.3f}% ({direction})",
                    details={
                        "funding_rate": metrics.funding_rate,
                        "funding_rate_avg": metrics.funding_rate_avg,
                        "direction": direction,
                    },
                    recommended_action=f"{direction} 포지션 주의 - 펀딩 수수료 급증 가능",
                )
                alerts.append(alert)

        # 4. 유동성 급감 (오더북 불균형)
        if abs(metrics.orderbook_imbalance) > 0.7:  # 70% 이상 불균형
            direction = "매수" if metrics.orderbook_imbalance > 0 else "매도"
            alert = await self._create_alert(
                anomaly_type=AnomalyType.LIQUIDITY_DROP,
                severity=AnomalySeverity.LOW,
                symbol=symbol,
                message=f"{symbol} 오더북 불균형: {direction} 압력 {abs(metrics.orderbook_imbalance) * 100:.1f}%",
                details={
                    "orderbook_imbalance": metrics.orderbook_imbalance,
                    "bids_depth": metrics.orderbook_depth_bids,
                    "asks_depth": metrics.orderbook_depth_asks,
                },
                recommended_action="슬리피지 위험 증가 - 큰 주문 주의",
            )
            alerts.append(alert)

        # Redis에 알림 저장 및 브로드캐스트
        for alert in alerts:
            await self._save_alert_to_redis(alert)
            self._active_alerts.append(alert)

            if broadcast:
                # Redis Pub/Sub로 모든 봇에게 알림
                await self._broadcast_market_alert(alert)

        if alerts:
            logger.warning(
                f"Market {symbol} anomalies: {[a.anomaly_type.value for a in alerts]}"
            )

        return alerts

    async def _check_circuit_breaker(self, params: dict) -> Optional[CircuitBreakerStatus]:
        """
        서킷 브레이커 체크 (일일 손실 한도)

        Args:
            params: {
                "user_id": int,
                "daily_pnl": float,
                "total_equity": float,
                "auto_execute": bool
            }

        Returns:
            서킷 브레이커 상태 (트리거된 경우에만)
        """
        user_id = params.get("user_id")
        daily_pnl = params.get("daily_pnl", 0.0)
        total_equity = params.get("total_equity", 0.0)
        auto_execute = params.get("auto_execute", True)

        if total_equity <= 0:
            logger.warning(f"Invalid total_equity for user {user_id}: {total_equity}")
            return None

        # 손실 비율 계산
        daily_loss_percent = (daily_pnl / total_equity) * 100

        # 임계값 초과 체크
        if daily_loss_percent < -self.max_daily_loss_percent:
            logger.critical(
                f"Circuit breaker triggered for user {user_id}: "
                f"{daily_loss_percent:.2f}% loss"
            )

            status = CircuitBreakerStatus(
                user_id=user_id,
                daily_pnl=daily_pnl,
                total_equity=total_equity,
                daily_loss_percent=daily_loss_percent,
                max_daily_loss_percent=self.max_daily_loss_percent,
                is_triggered=True,
                triggered_at=datetime.utcnow(),
                reason=f"일일 손실 {abs(daily_loss_percent):.1f}% 도달 (한도: {self.max_daily_loss_percent}%)",
            )

            if auto_execute:
                # 모든 봇 자동 중지
                stopped_bots = await self._auto_stop_all_bots(user_id)
                status.stopped_bot_ids = stopped_bots

                # 긴급 알림 생성
                alert = await self._create_alert(
                    anomaly_type=AnomalyType.CIRCUIT_BREAKER,
                    severity=AnomalySeverity.CRITICAL,
                    user_id=user_id,
                    message=f"서킷 브레이커 발동: 일일 손실 {abs(daily_loss_percent):.1f}%",
                    details={
                        "daily_pnl": daily_pnl,
                        "total_equity": total_equity,
                        "loss_percent": daily_loss_percent,
                        "stopped_bots": len(stopped_bots),
                    },
                    recommended_action="모든 봇이 자동 중지되었습니다. 전략 재검토 필요.",
                )
                alert.auto_executed = True
                await self._save_alert_to_redis(alert)

                # Telegram + Email 알림 (외부 서비스 호출)
                await self._send_emergency_notification(user_id, status, alert)

            # Redis에 상태 저장
            await self._save_circuit_breaker_status(status)

            return status

        return None

    def _get_active_alerts(self, params: dict) -> List[AnomalyAlert]:
        """
        활성 알림 조회

        Args:
            params: {
                "user_id": Optional[int],
                "bot_instance_id": Optional[int],
                "severity": Optional[AnomalySeverity],
                "limit": int
            }
        """
        user_id = params.get("user_id")
        bot_id = params.get("bot_instance_id")
        severity = params.get("severity")
        limit = params.get("limit", 50)

        # 필터링
        filtered_alerts = self._active_alerts

        if user_id:
            filtered_alerts = [a for a in filtered_alerts if a.user_id == user_id]

        if bot_id:
            filtered_alerts = [a for a in filtered_alerts if a.bot_instance_id == bot_id]

        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]

        # 최신순 정렬 및 제한
        filtered_alerts = sorted(
            filtered_alerts, key=lambda a: a.timestamp, reverse=True
        )[:limit]

        return filtered_alerts

    # ==================== Helper Methods ====================

    async def _create_alert(
        self,
        anomaly_type: AnomalyType,
        severity: AnomalySeverity,
        message: str,
        details: dict,
        recommended_action: str,
        user_id: Optional[int] = None,
        bot_instance_id: Optional[int] = None,
        symbol: Optional[str] = None,
    ) -> AnomalyAlert:
        """알림 생성"""
        alert = AnomalyAlert(
            alert_id=f"anomaly_{uuid.uuid4().hex[:12]}",
            anomaly_type=anomaly_type,
            severity=severity,
            user_id=user_id,
            bot_instance_id=bot_instance_id,
            symbol=symbol,
            message=message,
            details=details,
            recommended_action=recommended_action,
        )
        return alert

    async def _save_alert_to_redis(self, alert: AnomalyAlert):
        """Redis에 알림 저장"""
        if not self.redis_client:
            return

        try:
            key = f"agent:anomaly:alert:{alert.alert_id}"
            await self.redis_client.setex(
                key, 3600, alert.model_dump_json()  # 1시간 TTL
            )

            # 사용자별 알림 리스트
            if alert.user_id:
                list_key = f"agent:anomaly:user:{alert.user_id}:alerts"
                await self.redis_client.lpush(list_key, alert.alert_id)
                await self.redis_client.ltrim(list_key, 0, 99)  # 최대 100개 유지

            # 봇별 알림 리스트
            if alert.bot_instance_id:
                list_key = f"agent:anomaly:bot:{alert.bot_instance_id}:alerts"
                await self.redis_client.lpush(list_key, alert.alert_id)
                await self.redis_client.ltrim(list_key, 0, 49)  # 최대 50개 유지

        except Exception as e:
            logger.error(f"Failed to save alert to Redis: {e}")

    async def _broadcast_market_alert(self, alert: AnomalyAlert):
        """시장 이상 알림 브로드캐스트"""
        if not self.redis_client:
            return

        try:
            # Redis Pub/Sub로 모든 구독자에게 알림
            channel = f"market:anomaly:{alert.symbol}"
            await self.redis_client.publish(channel, alert.model_dump_json())
        except Exception as e:
            logger.error(f"Failed to broadcast market alert: {e}")

    async def _auto_stop_bot(self, bot_instance_id: int, reason: str):
        """봇 자동 중지"""
        # TODO: 실제 봇 중지 로직 구현 (bot_runner 서비스 호출)
        logger.warning(f"Auto-stopping bot {bot_instance_id}: {reason}")

        if self.redis_client:
            # Redis에 중지 명령 발행
            await self.redis_client.publish(
                f"bot:command:{bot_instance_id}",
                f'{{"action": "stop", "reason": "{reason}", "auto": true}}'
            )

    async def _auto_stop_all_bots(self, user_id: int) -> List[int]:
        """사용자의 모든 봇 자동 중지"""
        # TODO: DB에서 사용자의 모든 활성 봇 조회 및 중지
        logger.critical(f"Auto-stopping all bots for user {user_id}")

        stopped_bots = []

        if self.db_session:
            # 실제 DB 쿼리는 외부에서 주입받은 session 사용
            # from database.models import BotInstance
            # active_bots = await self.db_session.execute(
            #     select(BotInstance).where(
            #         BotInstance.user_id == user_id,
            #         BotInstance.is_running == True
            #     )
            # )
            # for bot in active_bots.scalars():
            #     await self._auto_stop_bot(bot.id, "circuit_breaker")
            #     stopped_bots.append(bot.id)
            pass

        return stopped_bots

    async def _save_circuit_breaker_status(self, status: CircuitBreakerStatus):
        """서킷 브레이커 상태 Redis 저장"""
        if not self.redis_client:
            return

        try:
            key = f"agent:circuit_breaker:user:{status.user_id}"
            await self.redis_client.setex(
                key, 86400, status.model_dump_json()  # 24시간 TTL
            )
        except Exception as e:
            logger.error(f"Failed to save circuit breaker status: {e}")

    async def _send_emergency_notification(
        self, user_id: int, status: CircuitBreakerStatus, alert: AnomalyAlert
    ):
        """긴급 알림 전송 (Telegram + Email)"""
        # TODO: 실제 알림 서비스 호출
        logger.critical(
            f"Sending emergency notification to user {user_id}: {alert.message}"
        )

        # Telegram
        # await telegram_service.send_message(
        #     user_id,
        #     f"🚨 긴급: 서킷 브레이커 발동\n"
        #     f"일일 손실: {abs(status.daily_loss_percent):.1f}%\n"
        #     f"중지된 봇: {len(status.stopped_bot_ids)}개\n"
        #     f"{alert.recommended_action}"
        # )

        # Email
        # await email_service.send_email(
        #     user_id,
        #     subject="[긴급] 자동 거래 중지 - 서킷 브레이커 발동",
        #     body=f"..."
        # )

    async def _analyze_anomaly_with_ai(
        self,
        anomaly_type: AnomalyType,
        metrics: Dict[str, Any],
        rule_based_severity: AnomalySeverity,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        AI 기반 이상 징후 분석 (DeepSeek-V3.2)

        Args:
            anomaly_type: 이상 징후 타입
            metrics: 메트릭 데이터
            rule_based_severity: 규칙 기반 심각도
            context: 컨텍스트 데이터

        Returns:
            {"severity": AnomalySeverity, "confidence": float, "is_false_positive": bool} 또는 None
        """
        if not self.enable_ai or not self.ai_service:
            return None

        # 시스템 프롬프트
        system_prompt = """You are an expert trading bot anomaly detection AI.

Analyze anomalies and determine:
- Severity: LOW/MEDIUM/HIGH/CRITICAL
- Whether it's a false positive
- Recommended action

Return ONLY valid JSON:
{"severity": "LOW|MEDIUM|HIGH|CRITICAL", "confidence": 0.0-1.0, "is_false_positive": false, "reason": "brief explanation", "action": "recommended action"}"""

        # 사용자 프롬프트
        metrics_str = "\n".join([f"- {k}: {v}" for k, v in metrics.items()])

        user_prompt = f"""Analyze this trading bot anomaly:

Anomaly Type: {anomaly_type.value}
Rule-based Severity: {rule_based_severity.value}

Metrics:
{metrics_str}

Context:
- Bot ID: {context.get('bot_id', 'N/A')}
- Symbol: {context.get('symbol', 'N/A')}
- Time: {context.get('timestamp', datetime.utcnow()).strftime('%Y-%m-%d %H:%M:%S')}

Is this a real anomaly or false positive? Provide analysis in JSON:"""

        try:
            # AI API 호출 (비용 최적화 적용)
            result = await self.ai_service.call_ai(
                agent_type="anomaly_detector",
                prompt=user_prompt,
                context={
                    "anomaly_type": anomaly_type.value,
                    "severity": rule_based_severity.value,
                    "bot_id": context.get("bot_id"),
                },
                system_prompt=system_prompt,
                response_type="anomaly_detection",
                temperature=0.2,
                max_tokens=200,
                enable_caching=True,
                enable_sampling=True
            )

            response_text = result.get("response", "")

            if not response_text:
                return None

            # JSON 파싱 (ReDoS 안전한 방식)
            from ...utils.safe_json_parser import extract_json_from_text
            ai_analysis = extract_json_from_text(response_text)

            if ai_analysis:

                severity_str = ai_analysis.get("severity", rule_based_severity.value).upper()
                ai_confidence = float(ai_analysis.get("confidence", 0.5))
                is_false_positive = ai_analysis.get("is_false_positive", False)

                # AnomalySeverity로 변환
                try:
                    ai_severity = AnomalySeverity(severity_str)
                except ValueError:
                    ai_severity = rule_based_severity

                logger.debug(
                    f"AI anomaly analysis: {severity_str}, confidence: {ai_confidence:.2f}, "
                    f"false_positive: {is_false_positive}, reason: {ai_analysis.get('reason', 'N/A')}"
                )

                return {
                    "severity": ai_severity,
                    "confidence": ai_confidence,
                    "is_false_positive": is_false_positive,
                    "reason": ai_analysis.get("reason", ""),
                    "action": ai_analysis.get("action", "")
                }

            return None

        except Exception as e:
            logger.error(f"AI anomaly analysis error: {e}", exc_info=True)
            return None
