"""
잔고 컨트롤러 서비스

잔고 초과만 체크하는 단순한 로직 (40% 한도 제거됨)
사용자당 최대 5개 봇 제한

관련 문서: docs/MULTI_BOT_IMPLEMENTATION_PLAN.md
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import BotInstance, TrendBotTemplate
from ..services.exchange_service import ExchangeService

logger = logging.getLogger(__name__)


@dataclass
class BalanceInfo:
    """잔고 정보 데이터클래스"""
    total_balance: float
    used_amount: float
    available_amount: float
    active_bot_count: int
    active_bots: List[BotInstance]


@dataclass
class BotPnLInfo:
    """봇 PnL 정보"""
    bot_id: int
    name: str
    allocated_amount: float
    current_pnl: float
    current_pnl_percent: float


class BalanceController:
    """
    잔고 컨트롤러

    - 잔고 초과만 체크 (40% 한도 제거됨)
    - 사용자당 최대 5개 봇 제한
    """

    MAX_BOTS_PER_USER = 5  # 최대 5개 봇
    MIN_INVESTMENT = 10.0  # 최소 투자금 $10

    def __init__(self, db: AsyncSession):
        """
        Args:
            db: SQLAlchemy AsyncSession
        """
        self.db = db

    async def check_can_start(
        self,
        user_id: int,
        amount: float
    ) -> Tuple[bool, str]:
        """
        봇 시작 가능 여부 확인

        Args:
            user_id: 사용자 ID
            amount: 투자 금액 (USDT)

        Returns:
            (가능 여부, 메시지) 튜플
        """
        # 최소 투자금 체크
        if amount < self.MIN_INVESTMENT:
            return (False, f"최소 투자금은 ${self.MIN_INVESTMENT}입니다")

        try:
            balance_info = await self.get_user_balance(user_id)
        except Exception as e:
            logger.error(f"Failed to get balance for user {user_id}: {e}")
            return (False, f"잔고 조회 실패: {str(e)}")

        # 봇 개수 체크
        if balance_info.active_bot_count >= self.MAX_BOTS_PER_USER:
            return (
                False,
                f"최대 {self.MAX_BOTS_PER_USER}개의 봇만 운용할 수 있습니다"
            )

        # 잔고 초과 체크
        if balance_info.used_amount + amount > balance_info.total_balance:
            available = balance_info.total_balance - balance_info.used_amount
            return (
                False,
                f"잔고가 부족합니다 (가용: ${available:.2f})"
            )

        return (True, "OK")

    async def get_user_balance(self, user_id: int) -> BalanceInfo:
        """
        사용자 잔고 정보 조회

        Args:
            user_id: 사용자 ID

        Returns:
            BalanceInfo 객체
        """
        # 1. 거래소에서 총 잔고 조회
        total_balance = await self._get_exchange_balance(user_id)

        # 2. 활성 봇들의 할당 금액 합계
        result = await self.db.execute(
            select(BotInstance).where(
                and_(
                    BotInstance.user_id == user_id,
                    BotInstance.is_running is True,
                    BotInstance.is_active is True
                )
            )
        )
        active_bots = list(result.scalars().all())
        used_amount = sum(float(b.allocated_amount or 0) for b in active_bots)

        return BalanceInfo(
            total_balance=total_balance,
            used_amount=used_amount,
            available_amount=max(0, total_balance - used_amount),
            active_bot_count=len(active_bots),
            active_bots=active_bots
        )

    async def get_balance_summary(self, user_id: int) -> dict:
        """
        잔고 요약 정보 조회 (API 응답용)

        Args:
            user_id: 사용자 ID

        Returns:
            잔고 요약 딕셔너리
        """
        balance_info = await self.get_user_balance(user_id)

        # 전체 PnL 계산
        total_pnl = 0.0
        total_allocated = 0.0

        bots_data = []
        for bot in balance_info.active_bots:
            allocated = float(bot.allocated_amount or 0)
            pnl = float(bot.total_pnl or 0)
            total_pnl += pnl
            total_allocated += allocated

            # 개별 봇 수익률 계산
            pnl_percent = (pnl / allocated * 100) if allocated > 0 else 0

            # 승률 계산
            total_trades = bot.total_trades or 0
            winning_trades = bot.winning_trades or 0
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # 템플릿 정보 조회
            template_name = None
            strategy_type = None
            if bot.trend_template_id:
                template_result = await self.db.execute(
                    select(TrendBotTemplate).where(
                        TrendBotTemplate.id == bot.trend_template_id
                    )
                )
                template = template_result.scalars().first()
                if template:
                    template_name = template.name
                    strategy_type = template.strategy_type

            bots_data.append({
                "id": bot.id,
                "name": bot.name,
                "symbol": bot.symbol,
                "template_id": bot.trend_template_id,
                "template_name": template_name,
                "strategy_type": strategy_type,
                "allocated_amount": allocated,
                "leverage": bot.max_leverage,
                "current_pnl": pnl,
                "current_pnl_percent": round(pnl_percent, 2),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "win_rate": round(win_rate, 2),
                "is_running": bot.is_running,
                "last_error": bot.last_error,
                "last_signal_at": bot.last_signal_at,
                "created_at": bot.created_at,
                "last_started_at": bot.last_started_at
            })

        # 전체 수익률 계산
        total_pnl_percent = (
            (total_pnl / total_allocated * 100)
            if total_allocated > 0 else 0
        )

        return {
            "total_balance": round(balance_info.total_balance, 2),
            "used_amount": round(balance_info.used_amount, 2),
            "available_amount": round(balance_info.available_amount, 2),
            "active_bot_count": balance_info.active_bot_count,
            "max_bot_count": self.MAX_BOTS_PER_USER,
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_percent, 2),
            "bots": bots_data
        }

    async def check_balance_for_amount(
        self,
        user_id: int,
        amount: float
    ) -> dict:
        """
        특정 금액에 대한 잔고 확인 (프리뷰용)

        Args:
            user_id: 사용자 ID
            amount: 확인할 금액

        Returns:
            잔고 확인 결과 딕셔너리
        """
        can_start, message = await self.check_can_start(user_id, amount)
        balance_info = await self.get_user_balance(user_id)

        return {
            "requested_amount": round(amount, 2),
            "available": can_start,
            "current_used": round(balance_info.used_amount, 2),
            "total_balance": round(balance_info.total_balance, 2),
            "after_used": round(balance_info.used_amount + amount, 2),
            "message": message
        }

    async def _get_exchange_balance(self, user_id: int) -> float:
        """
        거래소에서 실제 잔고 조회

        Args:
            user_id: 사용자 ID

        Returns:
            총 잔고 (USDT)
        """
        try:
            client, exchange_name = await ExchangeService.get_user_exchange_client(
                self.db,
                user_id
            )

            # 선물 잔고 조회
            balance = await client.get_futures_balance()

            if balance and 'total' in balance:
                return float(balance.get('total', 0))
            elif balance and 'available' in balance:
                return float(balance.get('available', 0))
            else:
                logger.warning(
                    f"Unexpected balance format from {exchange_name} "
                    f"for user {user_id}: {balance}"
                )
                return 0.0

        except Exception as e:
            logger.error(f"Failed to get exchange balance for user {user_id}: {e}")
            raise

    async def update_bot_pnl(
        self,
        bot_id: int,
        pnl: float,
        pnl_percent: float
    ) -> None:
        """
        봇 PnL 업데이트

        Args:
            bot_id: 봇 인스턴스 ID
            pnl: 수익금 (USDT)
            pnl_percent: 수익률 (%)
        """
        result = await self.db.execute(
            select(BotInstance).where(BotInstance.id == bot_id)
        )
        bot = result.scalars().first()

        if bot:
            bot.total_pnl = pnl
            bot.current_pnl_percent = pnl_percent
            await self.db.commit()
            logger.debug(f"Updated PnL for bot {bot_id}: {pnl:.2f} ({pnl_percent:.2f}%)")

    async def increment_trade_count(
        self,
        bot_id: int,
        is_winning: bool
    ) -> None:
        """
        봇 거래 횟수 증가

        Args:
            bot_id: 봇 인스턴스 ID
            is_winning: 수익 거래 여부
        """
        result = await self.db.execute(
            select(BotInstance).where(BotInstance.id == bot_id)
        )
        bot = result.scalars().first()

        if bot:
            bot.total_trades = (bot.total_trades or 0) + 1
            if is_winning:
                bot.winning_trades = (bot.winning_trades or 0) + 1
            await self.db.commit()
            logger.debug(
                f"Updated trade count for bot {bot_id}: "
                f"{bot.total_trades} total, {bot.winning_trades} winning"
            )
