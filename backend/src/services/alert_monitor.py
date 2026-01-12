import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import AsyncSessionLocal
from ..database.models import SystemAlert, Trade
from ..services.exchange_service import ExchangeService
from ..websockets.ws_server import ws_manager

logger = logging.getLogger(__name__)


class AlertLevel:
    """알림 레벨 상수"""

    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class AlertMonitor:
    """시스템 알림 자동 생성 및 모니터링"""

    def __init__(self):
        self.last_check = {}  # user_id -> last_check_time
        self.alert_cooldown = 300  # 5분 (같은 알림 중복 방지)

    async def create_alert(
        self,
        session: AsyncSession,
        user_id: int,
        level: str,
        message: str,
        alert_type: str = None,
    ) -> Optional[SystemAlert]:
        """
        알림 생성 및 WebSocket 전송

        Args:
            session: DB 세션
            user_id: 사용자 ID
            level: 알림 레벨 (ERROR, WARNING, INFO)
            message: 알림 메시지
            alert_type: 알림 타입 (중복 방지용)
        """
        try:
            # 중복 알림 체크 (5분 이내 같은 타입)
            if alert_type:
                recent_time = datetime.utcnow() - timedelta(seconds=self.alert_cooldown)
                result = await session.execute(
                    select(SystemAlert).where(
                        and_(
                            SystemAlert.user_id == user_id,
                            SystemAlert.message.like(f"%{alert_type}%"),
                            SystemAlert.created_at >= recent_time,
                            SystemAlert.is_resolved is False,
                        )
                    )
                )
                if result.scalars().first():
                    logger.debug(
                        f"Skipping duplicate alert: {alert_type} for user {user_id}"
                    )
                    return None

            # 알림 생성
            alert = SystemAlert(
                user_id=user_id,
                level=level,
                message=message,
                is_resolved=False,
                created_at=datetime.utcnow(),
            )
            session.add(alert)
            await session.commit()

            # WebSocket으로 즉시 전송
            await ws_manager.send_alert(user_id, level, message)

            logger.info(f"Alert created: {level} - {message} for user {user_id}")
            return alert

        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None

    async def check_low_balance(self, session: AsyncSession, user_id: int):
        """잔고 부족 감지 (10% 미만)"""
        try:
            client, exchange_name = await ExchangeService.get_user_exchange_client(
                session, user_id
            )
            balance = await client.fetch_balance()

            usdt_balance = balance.get("USDT", {})
            total = float(usdt_balance.get("total", 0))
            free = float(usdt_balance.get("free", 0))

            if total > 0:
                free_percent = (free / total) * 100

                if free_percent < 10:
                    await self.create_alert(
                        session,
                        user_id,
                        AlertLevel.WARNING,
                        f"사용 가능한 잔고가 {free_percent:.1f}%로 낮습니다. "
                        f"현재: ${free:.2f} USDT / 총: ${total:.2f} USDT",
                        alert_type="low_balance",
                    )
                elif free_percent < 5:
                    await self.create_alert(
                        session,
                        user_id,
                        AlertLevel.ERROR,
                        f"⚠️ 긴급: 사용 가능한 잔고가 {free_percent:.1f}%로 매우 낮습니다! "
                        f"현재: ${free:.2f} USDT / 총: ${total:.2f} USDT",
                        alert_type="critical_low_balance",
                    )

        except Exception as e:
            logger.error(f"Failed to check low balance for user {user_id}: {e}")

    async def check_high_margin_usage(self, session: AsyncSession, user_id: int):
        """높은 증거금 사용률 감지 (80% 이상)"""
        try:
            client, exchange_name = await ExchangeService.get_user_exchange_client(
                session, user_id
            )
            balance = await client.fetch_balance()

            usdt_balance = balance.get("USDT", {})
            total = float(usdt_balance.get("total", 0))
            free = float(usdt_balance.get("free", 0))

            if total > 0:
                used = total - free
                usage_percent = (used / total) * 100

                if usage_percent >= 90:
                    await self.create_alert(
                        session,
                        user_id,
                        AlertLevel.ERROR,
                        f"⚠️ 위험: 증거금 사용률이 {usage_percent:.1f}%로 매우 높습니다! "
                        f"청산 위험이 있습니다. 사용 중: ${used:.2f} USDT",
                        alert_type="critical_margin",
                    )
                elif usage_percent >= 80:
                    await self.create_alert(
                        session,
                        user_id,
                        AlertLevel.WARNING,
                        f"증거금 사용률이 {usage_percent:.1f}%로 높습니다. "
                        f"사용 중: ${used:.2f} USDT / 총: ${total:.2f} USDT",
                        alert_type="high_margin",
                    )

        except Exception as e:
            logger.error(f"Failed to check margin usage for user {user_id}: {e}")

    async def check_api_connection(self, session: AsyncSession, user_id: int):
        """API 연결 실패 감지"""
        try:
            client, exchange_name = await ExchangeService.get_user_exchange_client(
                session, user_id
            )
            # 간단한 API 호출로 연결 테스트
            await client.fetch_balance()

        except Exception as e:
            # API 연결 실패
            await self.create_alert(
                session,
                user_id,
                AlertLevel.ERROR,
                f"거래소 API 연결에 실패했습니다: {str(e)[:100]}",
                alert_type="api_connection_failed",
            )

    async def check_abnormal_loss(self, session: AsyncSession, user_id: int):
        """비정상적인 손실 감지 (일일 -5% 이상)"""
        try:
            # 오늘의 거래 조회
            today_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            result = await session.execute(
                select(Trade).where(
                    and_(
                        Trade.user_id == user_id,
                        Trade.created_at >= today_start,
                        Trade.pnl.isnot(None),
                    )
                )
            )
            trades = result.scalars().all()

            if not trades:
                return

            # 총 손익 계산
            total_pnl = sum(float(trade.pnl or 0) for trade in trades)

            # 초기 잔고 추정 (현재 잔고 - 총 손익)
            client, exchange_name = await ExchangeService.get_user_exchange_client(
                session, user_id
            )
            balance = await client.fetch_balance()
            current_balance = float(balance.get("USDT", {}).get("total", 0))

            if current_balance > 0:
                initial_balance = current_balance - total_pnl
                if initial_balance > 0:
                    loss_percent = (total_pnl / initial_balance) * 100

                    if loss_percent <= -10:
                        await self.create_alert(
                            session,
                            user_id,
                            AlertLevel.ERROR,
                            f"⚠️ 긴급: 오늘 {loss_percent:.1f}%의 큰 손실이 발생했습니다! "
                            f"손실: ${total_pnl:.2f} USDT (거래 {len(trades)}건)",
                            alert_type="critical_daily_loss",
                        )
                    elif loss_percent <= -5:
                        await self.create_alert(
                            session,
                            user_id,
                            AlertLevel.WARNING,
                            f"오늘 {loss_percent:.1f}%의 손실이 발생했습니다. "
                            f"손실: ${total_pnl:.2f} USDT (거래 {len(trades)}건)",
                            alert_type="abnormal_daily_loss",
                        )

        except Exception as e:
            logger.error(f"Failed to check abnormal loss for user {user_id}: {e}")

    async def check_position_risk(self, session: AsyncSession, user_id: int):
        """포지션 리스크 감지 (미실현 손실 -10% 이상)"""
        try:
            client, exchange_name = await ExchangeService.get_user_exchange_client(
                session, user_id
            )
            positions = await client.fetch_positions()

            for pos in positions:
                if pos.get("contracts", 0) == 0:
                    continue

                symbol = pos.get("symbol", "")
                unrealized_pnl = float(pos.get("unrealizedPnl", 0))
                position_value = float(pos.get("contracts", 0)) * float(
                    pos.get("markPrice", 1)
                )

                if position_value > 0:
                    pnl_percent = (unrealized_pnl / position_value) * 100

                    if pnl_percent <= -15:
                        await self.create_alert(
                            session,
                            user_id,
                            AlertLevel.ERROR,
                            f"⚠️ {symbol} 포지션에서 {pnl_percent:.1f}%의 큰 손실이 발생 중입니다! "
                            f"미실현 손실: ${unrealized_pnl:.2f} USDT",
                            alert_type=f"critical_position_loss_{symbol}",
                        )
                    elif pnl_percent <= -10:
                        await self.create_alert(
                            session,
                            user_id,
                            AlertLevel.WARNING,
                            f"{symbol} 포지션에서 {pnl_percent:.1f}%의 손실이 발생 중입니다. "
                            f"미실현 손실: ${unrealized_pnl:.2f} USDT",
                            alert_type=f"position_loss_{symbol}",
                        )

        except Exception as e:
            logger.error(f"Failed to check position risk for user {user_id}: {e}")

    async def run_all_checks(self, user_id: int):
        """모든 체크 실행 - API 호출 최적화 (Rate Limit 방지)"""
        async with AsyncSessionLocal() as session:
            try:
                # ⚠️ Rate Limit 방지: 잔고와 포지션을 한 번만 조회
                client, exchange_name = await ExchangeService.get_user_exchange_client(
                    session, user_id
                )

                # 1회 API 호출로 잔고 조회
                balance = None
                positions = None
                try:
                    balance = await client.fetch_balance()
                except Exception as e:
                    logger.error(f"Failed to fetch balance for user {user_id}: {e}")
                    # API 연결 실패 알림
                    await self.create_alert(
                        session,
                        user_id,
                        AlertLevel.ERROR,
                        f"거래소 API 연결에 실패했습니다: {str(e)[:100]}",
                        alert_type="api_connection_failed",
                    )
                    return

                # 1회 API 호출로 포지션 조회
                try:
                    positions = await client.fetch_positions()
                except Exception as e:
                    logger.error(f"Failed to fetch positions for user {user_id}: {e}")
                    positions = []

                # 조회한 데이터로 모든 체크 실행 (추가 API 호출 없음)
                if balance:
                    await self._check_balance_with_data(session, user_id, balance)

                if positions:
                    await self._check_positions_with_data(session, user_id, positions)

                if balance:
                    await self._check_abnormal_loss_with_data(session, user_id, balance)

                self.last_check[user_id] = datetime.utcnow()
                logger.debug(f"✅ Alert checks completed for user {user_id} (optimized API calls)")

            except Exception as e:
                logger.error(f"Failed to run checks for user {user_id}: {e}")

    async def _check_balance_with_data(self, session: AsyncSession, user_id: int, balance: dict):
        """잔고 데이터로 잔고 부족 및 증거금 체크 (API 호출 없음)"""
        try:
            usdt_balance = balance.get("USDT", {})
            total = float(usdt_balance.get("total", 0))
            free = float(usdt_balance.get("free", 0))

            if total > 0:
                free_percent = (free / total) * 100
                used = total - free
                usage_percent = (used / total) * 100

                # 잔고 부족 체크
                if free_percent < 5:
                    await self.create_alert(
                        session,
                        user_id,
                        AlertLevel.ERROR,
                        f"⚠️ 긴급: 사용 가능한 잔고가 {free_percent:.1f}%로 매우 낮습니다! "
                        f"현재: ${free:.2f} USDT / 총: ${total:.2f} USDT",
                        alert_type="critical_low_balance",
                    )
                elif free_percent < 10:
                    await self.create_alert(
                        session,
                        user_id,
                        AlertLevel.WARNING,
                        f"사용 가능한 잔고가 {free_percent:.1f}%로 낮습니다. "
                        f"현재: ${free:.2f} USDT / 총: ${total:.2f} USDT",
                        alert_type="low_balance",
                    )

                # 증거금 사용률 체크
                if usage_percent >= 90:
                    await self.create_alert(
                        session,
                        user_id,
                        AlertLevel.ERROR,
                        f"⚠️ 위험: 증거금 사용률이 {usage_percent:.1f}%로 매우 높습니다! "
                        f"청산 위험이 있습니다. 사용 중: ${used:.2f} USDT",
                        alert_type="critical_margin",
                    )
                elif usage_percent >= 80:
                    await self.create_alert(
                        session,
                        user_id,
                        AlertLevel.WARNING,
                        f"증거금 사용률이 {usage_percent:.1f}%로 높습니다. "
                        f"사용 중: ${used:.2f} USDT / 총: ${total:.2f} USDT",
                        alert_type="high_margin",
                    )
        except Exception as e:
            logger.error(f"Failed to check balance data for user {user_id}: {e}")

    async def _check_positions_with_data(self, session: AsyncSession, user_id: int, positions: list):
        """포지션 데이터로 리스크 체크 (API 호출 없음)"""
        try:
            for pos in positions:
                if pos.get("contracts", 0) == 0:
                    continue

                symbol = pos.get("symbol", "")
                unrealized_pnl = float(pos.get("unrealizedPnl", 0))
                position_value = float(pos.get("contracts", 0)) * float(
                    pos.get("markPrice", 1)
                )

                if position_value > 0:
                    pnl_percent = (unrealized_pnl / position_value) * 100

                    if pnl_percent <= -15:
                        await self.create_alert(
                            session,
                            user_id,
                            AlertLevel.ERROR,
                            f"⚠️ {symbol} 포지션에서 {pnl_percent:.1f}%의 큰 손실이 발생 중입니다! "
                            f"미실현 손실: ${unrealized_pnl:.2f} USDT",
                            alert_type=f"critical_position_loss_{symbol}",
                        )
                    elif pnl_percent <= -10:
                        await self.create_alert(
                            session,
                            user_id,
                            AlertLevel.WARNING,
                            f"{symbol} 포지션에서 {pnl_percent:.1f}%의 손실이 발생 중입니다. "
                            f"미실현 손실: ${unrealized_pnl:.2f} USDT",
                            alert_type=f"position_loss_{symbol}",
                        )
        except Exception as e:
            logger.error(f"Failed to check positions data for user {user_id}: {e}")

    async def _check_abnormal_loss_with_data(self, session: AsyncSession, user_id: int, balance: dict):
        """잔고 데이터로 비정상 손실 체크 (API 호출 없음)"""
        try:
            # 오늘의 거래 조회
            today_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            result = await session.execute(
                select(Trade).where(
                    and_(
                        Trade.user_id == user_id,
                        Trade.created_at >= today_start,
                        Trade.pnl.isnot(None),
                    )
                )
            )
            trades = result.scalars().all()

            if not trades:
                return

            # 총 손익 계산
            total_pnl = sum(float(trade.pnl or 0) for trade in trades)

            # 현재 잔고
            current_balance = float(balance.get("USDT", {}).get("total", 0))

            if current_balance > 0:
                initial_balance = current_balance - total_pnl
                if initial_balance > 0:
                    loss_percent = (total_pnl / initial_balance) * 100

                    if loss_percent <= -10:
                        await self.create_alert(
                            session,
                            user_id,
                            AlertLevel.ERROR,
                            f"⚠️ 긴급: 오늘 {loss_percent:.1f}%의 큰 손실이 발생했습니다! "
                            f"손실: ${total_pnl:.2f} USDT (거래 {len(trades)}건)",
                            alert_type="critical_daily_loss",
                        )
                    elif loss_percent <= -5:
                        await self.create_alert(
                            session,
                            user_id,
                            AlertLevel.WARNING,
                            f"오늘 {loss_percent:.1f}%의 손실이 발생했습니다. "
                            f"손실: ${total_pnl:.2f} USDT (거래 {len(trades)}건)",
                            alert_type="abnormal_daily_loss",
                        )
        except Exception as e:
            logger.error(f"Failed to check abnormal loss data for user {user_id}: {e}")


# 싱글톤 인스턴스
alert_monitor = AlertMonitor()
