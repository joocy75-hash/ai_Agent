"""
잔고 할당 관리자 (Allocation Manager)

관련 문서: docs/MULTI_BOT_03_IMPLEMENTATION.md

역할:
- 봇별 할당 잔고 계산
- 동시 주문 시 잔고 충돌 방지 (락 사용)
- 사용 가능 잔고 조회
- 봇별 주문 가능 금액 검증

사용 예시:
    from services.allocation_manager import allocation_manager

    # 봇에 할당된 잔고 조회
    allocated = await allocation_manager.get_allocated_balance(user_id, bot_id, bitget_client)

    # 주문 전 잔고 확인
    can_order = await allocation_manager.request_order_amount(user_id, bot_id, amount, bitget_client)
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import BotInstance

logger = logging.getLogger(__name__)


class AllocationManager:
    """
    사용자별 잔고 할당 관리

    주요 기능:
    1. 봇별 할당 잔고 계산 (총잔고 * allocation_percent / 100)
    2. 캐싱으로 API Rate Limit 방지
    3. 락으로 동시 주문 충돌 방지
    """

    def __init__(self):
        # 사용자별 락 (동시 주문 방지)
        self._locks: Dict[int, asyncio.Lock] = {}  # user_id -> Lock

        # 잔고 캐시
        self._balance_cache: Dict[int, float] = {}  # user_id -> total_balance
        self._cache_time: Dict[int, float] = {}  # user_id -> timestamp

        # 봇별 사용 중인 금액 추적 (열린 포지션)
        self._used_amounts: Dict[int, float] = {}  # bot_instance_id -> used_amount

        # 캐시 TTL (초)
        self.CACHE_TTL = 10  # 10초 캐시

    async def get_user_lock(self, user_id: int) -> asyncio.Lock:
        """사용자별 락 반환 (없으면 생성)"""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def get_total_balance(
        self,
        user_id: int,
        bitget_client,
        force_refresh: bool = False
    ) -> float:
        """
        사용자 총 잔고 조회 (캐싱 적용)

        Args:
            user_id: 사용자 ID
            bitget_client: Bitget REST 클라이언트
            force_refresh: 캐시 무시하고 강제 조회

        Returns:
            총 USDT 잔고
        """
        now = time.time()

        # 캐시 확인 (force_refresh가 아닌 경우)
        if not force_refresh:
            if user_id in self._balance_cache:
                cache_age = now - self._cache_time.get(user_id, 0)
                if cache_age < self.CACHE_TTL:
                    logger.debug(f"Balance cache hit for user {user_id}")
                    return self._balance_cache[user_id]

        # API 호출
        try:
            balance = await bitget_client.fetch_balance()
            usdt_balance = balance.get("USDT", {})
            total = float(usdt_balance.get("total", 0))

            # 캐시 업데이트
            self._balance_cache[user_id] = total
            self._cache_time[user_id] = now

            logger.debug(f"Fetched balance for user {user_id}: {total} USDT")
            return total

        except Exception as e:
            logger.error(f"Failed to fetch balance for user {user_id}: {e}")
            # 캐시가 있으면 캐시 반환 (stale data)
            if user_id in self._balance_cache:
                logger.warning(f"Returning stale balance for user {user_id}")
                return self._balance_cache[user_id]
            raise

    async def get_allocated_balance(
        self,
        user_id: int,
        bot_instance_id: int,
        bitget_client,
        session: AsyncSession
    ) -> float:
        """
        특정 봇에 할당된 잔고 계산

        Formula: 총잔고 * (allocation_percent / 100)

        Args:
            user_id: 사용자 ID
            bot_instance_id: 봇 인스턴스 ID
            bitget_client: Bitget REST 클라이언트
            session: DB 세션

        Returns:
            봇에 할당된 USDT 잔고
        """
        # 총 잔고 조회
        total = await self.get_total_balance(user_id, bitget_client)

        # 봇의 할당 비율 조회
        result = await session.execute(
            select(BotInstance.allocation_percent).where(
                and_(
                    BotInstance.id == bot_instance_id,
                    BotInstance.user_id == user_id,
                    BotInstance.is_active is True
                )
            )
        )
        allocation_percent = result.scalar()

        if allocation_percent is None:
            logger.warning(f"Bot instance {bot_instance_id} not found for user {user_id}")
            return 0

        allocated = total * (float(allocation_percent) / 100)
        logger.debug(
            f"Bot {bot_instance_id} allocated balance: {allocated:.2f} USDT "
            f"({allocation_percent}% of {total:.2f})"
        )
        return allocated

    async def get_available_balance(
        self,
        user_id: int,
        bot_instance_id: int,
        bitget_client,
        session: AsyncSession
    ) -> float:
        """
        봇의 사용 가능한 잔고 계산 (할당 - 사용 중)

        Args:
            user_id: 사용자 ID
            bot_instance_id: 봇 인스턴스 ID
            bitget_client: Bitget REST 클라이언트
            session: DB 세션

        Returns:
            사용 가능한 USDT 잔고
        """
        allocated = await self.get_allocated_balance(
            user_id, bot_instance_id, bitget_client, session
        )

        # 현재 사용 중인 금액 (열린 포지션)
        used = self._used_amounts.get(bot_instance_id, 0)

        available = max(0, allocated - used)
        logger.debug(
            f"Bot {bot_instance_id} available: {available:.2f} USDT "
            f"(allocated: {allocated:.2f}, used: {used:.2f})"
        )
        return available

    async def validate_allocation(
        self,
        user_id: int,
        new_allocation: float,
        session: AsyncSession,
        exclude_bot_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        새 할당이 가능한지 검증

        Args:
            user_id: 사용자 ID
            new_allocation: 새로 할당하려는 비율 (%)
            session: DB 세션
            exclude_bot_id: 제외할 봇 ID (수정 시 자신 제외)

        Returns:
            (가능 여부, 메시지)
        """
        # 현재 총 할당률 조회
        query = select(func.coalesce(func.sum(BotInstance.allocation_percent), 0)).where(
            and_(
                BotInstance.user_id == user_id,
                BotInstance.is_active is True
            )
        )
        if exclude_bot_id:
            query = query.where(BotInstance.id != exclude_bot_id)

        result = await session.execute(query)
        current_total = float(result.scalar() or 0)

        if current_total + new_allocation > 100:
            available = 100 - current_total
            return False, f"할당 초과: 현재 {current_total:.1f}% 사용 중, 최대 {available:.1f}% 가능"

        return True, "OK"

    async def request_order_amount(
        self,
        user_id: int,
        bot_instance_id: int,
        amount: float,
        bitget_client,
        session: AsyncSession
    ) -> Tuple[bool, str]:
        """
        주문 금액 요청 (락 사용으로 동시 주문 충돌 방지)

        여러 봇이 동시에 주문할 때 잔고 충돌을 방지합니다.

        Args:
            user_id: 사용자 ID
            bot_instance_id: 봇 인스턴스 ID
            amount: 요청 금액 (USDT)
            bitget_client: Bitget REST 클라이언트
            session: DB 세션

        Returns:
            (성공 여부, 메시지)
        """
        lock = await self.get_user_lock(user_id)

        async with lock:
            available = await self.get_available_balance(
                user_id, bot_instance_id, bitget_client, session
            )

            if amount > available:
                logger.warning(
                    f"Bot {bot_instance_id}: Insufficient balance. "
                    f"Requested: {amount:.2f}, Available: {available:.2f}"
                )
                return False, f"잔고 부족: 요청 {amount:.2f} USDT, 사용 가능 {available:.2f} USDT"

            # 사용 금액 예약
            self._used_amounts[bot_instance_id] = self._used_amounts.get(bot_instance_id, 0) + amount
            logger.info(
                f"Bot {bot_instance_id}: Reserved {amount:.2f} USDT. "
                f"Total used: {self._used_amounts[bot_instance_id]:.2f}"
            )
            return True, "OK"

    def release_order_amount(self, bot_instance_id: int, amount: float):
        """
        주문 금액 해제 (주문 취소/체결 후)

        Args:
            bot_instance_id: 봇 인스턴스 ID
            amount: 해제할 금액 (USDT)
        """
        if bot_instance_id in self._used_amounts:
            self._used_amounts[bot_instance_id] = max(
                0, self._used_amounts[bot_instance_id] - amount
            )
            logger.debug(
                f"Bot {bot_instance_id}: Released {amount:.2f} USDT. "
                f"Total used: {self._used_amounts[bot_instance_id]:.2f}"
            )

    def reset_bot_usage(self, bot_instance_id: int):
        """
        봇의 사용 금액 초기화 (봇 중지 시)

        Args:
            bot_instance_id: 봇 인스턴스 ID
        """
        if bot_instance_id in self._used_amounts:
            del self._used_amounts[bot_instance_id]
            logger.debug(f"Bot {bot_instance_id}: Usage reset")

    def invalidate_cache(self, user_id: int):
        """
        사용자의 잔고 캐시 무효화

        Args:
            user_id: 사용자 ID
        """
        if user_id in self._balance_cache:
            del self._balance_cache[user_id]
        if user_id in self._cache_time:
            del self._cache_time[user_id]
        logger.debug(f"Balance cache invalidated for user {user_id}")

    async def sync_used_amounts_from_positions(
        self,
        user_id: int,
        bot_instance_id: int,
        bitget_client,
        session: AsyncSession
    ):
        """
        실제 포지션에서 사용 금액 동기화

        봇 시작 시 또는 불일치 발생 시 호출

        Args:
            user_id: 사용자 ID
            bot_instance_id: 봇 인스턴스 ID
            bitget_client: Bitget REST 클라이언트
            session: DB 세션
        """
        try:
            # Bitget에서 포지션 조회
            positions = await bitget_client.get_positions(product_type="USDT-FUTURES")

            # 봇의 심볼 조회
            result = await session.execute(
                select(BotInstance.symbol).where(BotInstance.id == bot_instance_id)
            )
            bot_symbol = result.scalar()

            # 해당 봇의 심볼에 해당하는 포지션의 사용 금액 계산
            used = 0
            for pos in positions:
                if pos.get("symbol") == bot_symbol:
                    # 포지션 가치 = 사이즈 * 진입가 / 레버리지
                    size = float(pos.get("total", 0))
                    avg_price = float(pos.get("averageOpenPrice", 0))
                    leverage = float(pos.get("leverage", 1))
                    if size > 0 and avg_price > 0:
                        used += (size * avg_price) / leverage

            self._used_amounts[bot_instance_id] = used
            logger.info(
                f"Bot {bot_instance_id}: Synced used amount from positions: {used:.2f} USDT"
            )

        except Exception as e:
            logger.error(f"Failed to sync used amounts for bot {bot_instance_id}: {e}")


# 싱글톤 인스턴스
allocation_manager = AllocationManager()
