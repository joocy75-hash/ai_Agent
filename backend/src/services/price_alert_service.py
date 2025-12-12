"""
Price Alert Service

차트 어노테이션의 가격 알림(price_level)을 모니터링하고
가격이 설정된 레벨에 도달하면 알림을 전송하는 서비스
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import AsyncSessionLocal
from ..database.models import ChartAnnotation, AnnotationType
from ..websockets.ws_server import WebSocketManager

logger = logging.getLogger(__name__)


class PriceAlertService:
    """가격 알림 모니터링 서비스"""

    def __init__(self):
        self.running = False
        self.check_interval = 5  # 5초마다 가격 체크
        self.last_prices: Dict[str, float] = {}  # symbol -> last_price
        self.triggered_alerts: Set[int] = set()  # 이미 트리거된 알림 ID
        self._lock = asyncio.Lock()

    async def start(self):
        """서비스 시작"""
        if self.running:
            logger.warning("Price alert service is already running")
            return

        self.running = True
        asyncio.create_task(self._monitor_loop())
        logger.info("Price alert service started")

    async def stop(self):
        """서비스 중지"""
        self.running = False
        logger.info("Price alert service stopped")

    async def update_price(self, symbol: str, price: float):
        """
        가격 업데이트 (WebSocket 또는 다른 소스에서 호출)

        Args:
            symbol: 심볼 (예: BTCUSDT)
            price: 현재 가격
        """
        async with self._lock:
            previous_price = self.last_prices.get(symbol)
            self.last_prices[symbol] = price

            # 가격이 변경되었을 때만 알림 체크
            if previous_price is not None and previous_price != price:
                await self._check_price_alerts(symbol, previous_price, price)

    async def _check_price_alerts(
        self, symbol: str, previous_price: float, current_price: float
    ):
        """
        가격 알림 체크 및 트리거

        Args:
            symbol: 심볼
            previous_price: 이전 가격
            current_price: 현재 가격
        """
        try:
            async with AsyncSessionLocal() as session:
                # 해당 심볼의 활성화된 가격 알림 조회
                # annotation_type은 Python에서 필터링 (DB enum 대소문자 이슈 우회)
                result = await session.execute(
                    select(ChartAnnotation).where(
                        and_(
                            ChartAnnotation.symbol == symbol.upper(),
                            ChartAnnotation.is_active == True,
                            ChartAnnotation.alert_enabled == True,
                            ChartAnnotation.alert_triggered == False,
                        )
                    )
                )
                all_alerts = result.scalars().all()
                # Python에서 price_level 타입만 필터링
                alerts = [
                    a
                    for a in all_alerts
                    if str(a.annotation_type).lower() == "price_level"
                    or (
                        hasattr(a.annotation_type, "value")
                        and a.annotation_type.value == "price_level"
                    )
                ]

                for alert in alerts:
                    if alert.id in self.triggered_alerts:
                        continue

                    alert_price = float(alert.price)
                    direction = alert.alert_direction or "both"

                    # 가격 도달 체크
                    triggered = False
                    trigger_direction = None

                    if direction == "up" or direction == "both":
                        # 상향 돌파: 이전 가격 < 알림 가격 <= 현재 가격
                        if previous_price < alert_price <= current_price:
                            triggered = True
                            trigger_direction = "up"

                    if direction == "down" or direction == "both":
                        # 하향 돌파: 이전 가격 > 알림 가격 >= 현재 가격
                        if previous_price > alert_price >= current_price:
                            triggered = True
                            trigger_direction = "down"

                    if triggered:
                        await self._trigger_alert(
                            session, alert, current_price, trigger_direction
                        )

        except Exception as e:
            logger.error(f"Error checking price alerts for {symbol}: {e}")

    async def _trigger_alert(
        self,
        session: AsyncSession,
        alert: ChartAnnotation,
        current_price: float,
        direction: str,
    ):
        """
        알림 트리거 및 사용자에게 전송

        Args:
            session: DB 세션
            alert: 어노테이션
            current_price: 현재 가격
            direction: 트리거 방향 (up/down)
        """
        try:
            # 중복 트리거 방지
            self.triggered_alerts.add(alert.id)

            # DB 업데이트
            alert.alert_triggered = True
            alert.updated_at = datetime.utcnow()
            await session.commit()

            # 알림 메시지 생성
            direction_text = "상향 돌파" if direction == "up" else "하향 돌파"
            message = (
                f"🔔 가격 알림: {alert.symbol}\n"
                f"{direction_text} - 설정가: ${float(alert.price):,.2f}\n"
                f"현재가: ${current_price:,.2f}"
            )
            if alert.label:
                message = f"🔔 {alert.label}\n" + message.split("\n", 1)[1]

            # WebSocket으로 알림 전송
            await WebSocketManager.send_alert(alert.user_id, "INFO", message)

            # 가격 알림 전용 이벤트도 전송
            await WebSocketManager.broadcast_to_user(
                alert.user_id,
                {
                    "type": "price_alert_triggered",
                    "data": {
                        "id": alert.id,
                        "symbol": alert.symbol,
                        "alert_price": float(alert.price),
                        "current_price": current_price,
                        "direction": direction,
                        "label": alert.label,
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )

            logger.info(
                f"Price alert triggered for user {alert.user_id}: "
                f"{alert.symbol} {direction} ${float(alert.price)}"
            )

        except Exception as e:
            logger.error(f"Error triggering price alert {alert.id}: {e}")
            # 실패 시 다시 트리거 가능하도록 제거
            self.triggered_alerts.discard(alert.id)

    async def reset_alert(self, annotation_id: int):
        """
        알림 리셋 (다시 트리거 가능하도록)

        Args:
            annotation_id: 어노테이션 ID
        """
        self.triggered_alerts.discard(annotation_id)

        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ChartAnnotation).where(ChartAnnotation.id == annotation_id)
                )
                alert = result.scalar_one_or_none()

                if alert:
                    alert.alert_triggered = False
                    alert.updated_at = datetime.utcnow()
                    await session.commit()
                    logger.info(f"Price alert {annotation_id} reset")

        except Exception as e:
            logger.error(f"Error resetting price alert {annotation_id}: {e}")

    async def _monitor_loop(self):
        """모니터링 루프 (백그라운드에서 실행)"""
        while self.running:
            try:
                await asyncio.sleep(self.check_interval)
                # 여기서는 가격 업데이트가 update_price()를 통해 들어오므로
                # 별도의 가격 조회는 하지 않음
                # 필요시 여기서 직접 거래소 API 호출 가능

            except Exception as e:
                logger.error(f"Error in price alert monitor loop: {e}")
                await asyncio.sleep(10)

    def get_status(self) -> dict:
        """서비스 상태 조회"""
        return {
            "running": self.running,
            "tracked_symbols": list(self.last_prices.keys()),
            "triggered_count": len(self.triggered_alerts),
            "last_prices": self.last_prices.copy(),
        }


# 싱글톤 인스턴스
price_alert_service = PriceAlertService()
