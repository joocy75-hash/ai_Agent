"""
봇 격리 관리자 (Bot Isolation Manager)

관련 문서: docs/MULTI_BOT_03_IMPLEMENTATION.md

역할:
- 동일 심볼에 대한 봇 간 포지션 충돌 방지
- 봇별 포지션 추적 및 관리
- 거래소 주문 ID와 봇 인스턴스 매핑

사용 예시:
    from services.bot_isolation_manager import bot_isolation_manager

    # 포지션 진입 전 충돌 체크
    can_enter, msg = await bot_isolation_manager.can_open_position(
        user_id, bot_instance_id, symbol, side, session
    )

    # 포지션 등록
    await bot_isolation_manager.register_position(
        user_id, bot_instance_id, symbol, side, size, entry_price, order_id, session
    )
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Set, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Position

logger = logging.getLogger(__name__)


class BotIsolationManager:
    """
    봇 인스턴스별 포지션 격리 관리

    주요 기능:
    1. 동일 심볼 포지션 충돌 방지 (같은 사용자의 여러 봇이 같은 심볼 거래 시)
    2. 봇별 포지션/주문 추적
    3. 메모리 캐시 + DB 동기화
    """

    def __init__(self):
        # 메모리 캐시: 빠른 조회를 위해
        # user_id -> symbol -> Set[bot_instance_id]
        self._active_positions: Dict[int, Dict[str, Set[int]]] = {}

        # bot_instance_id -> position_info
        self._bot_positions: Dict[int, dict] = {}

        # 락: 동시 포지션 진입 방지
        self._locks: Dict[str, asyncio.Lock] = {}  # "user_id:symbol" -> Lock

    async def _get_lock(self, user_id: int, symbol: str) -> asyncio.Lock:
        """사용자-심볼 조합별 락 반환"""
        key = f"{user_id}:{symbol}"
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def can_open_position(
        self,
        user_id: int,
        bot_instance_id: int,
        symbol: str,
        side: str,
        session: AsyncSession,
        allow_same_symbol_different_bot: bool = True
    ) -> Tuple[bool, str]:
        """
        포지션 진입 가능 여부 확인

        Args:
            user_id: 사용자 ID
            bot_instance_id: 봇 인스턴스 ID
            symbol: 거래 심볼 (예: BTCUSDT)
            side: 포지션 방향 (long/short)
            session: DB 세션
            allow_same_symbol_different_bot: 같은 심볼에 다른 봇이 포지션 가능 여부

        Returns:
            (가능 여부, 메시지)
        """
        lock = await self._get_lock(user_id, symbol)

        async with lock:
            # 1. 해당 봇이 이미 같은 심볼에 포지션 보유 중인지 확인
            if bot_instance_id in self._bot_positions:
                pos = self._bot_positions[bot_instance_id]
                if pos.get("symbol") == symbol and pos.get("is_open", False):
                    return False, f"봇 {bot_instance_id}이(가) 이미 {symbol} 포지션 보유 중"

            # 2. 같은 심볼에 다른 봇이 포지션 보유 중인지 확인 (선택적)
            if not allow_same_symbol_different_bot:
                if user_id in self._active_positions:
                    if symbol in self._active_positions[user_id]:
                        other_bots = self._active_positions[user_id][symbol]
                        if other_bots and bot_instance_id not in other_bots:
                            return False, f"다른 봇이 이미 {symbol} 포지션 보유 중: {other_bots}"

            # 3. DB 확인 (캐시 미스 대비)
            result = await session.execute(
                select(Position).where(
                    and_(
                        Position.user_id == user_id,
                        Position.symbol == symbol,
                        Position.bot_instance_id == bot_instance_id,
                        Position.size > 0
                    )
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return False, f"DB에 {symbol} 포지션 존재 (ID: {existing.id})"

            return True, "OK"

    async def register_position(
        self,
        user_id: int,
        bot_instance_id: int,
        symbol: str,
        side: str,
        size: float,
        entry_price: float,
        exchange_order_id: Optional[str],
        session: AsyncSession
    ) -> int:
        """
        포지션 등록 (진입 시)

        Args:
            user_id: 사용자 ID
            bot_instance_id: 봇 인스턴스 ID
            symbol: 거래 심볼
            side: 포지션 방향
            size: 포지션 크기
            entry_price: 진입 가격
            exchange_order_id: 거래소 주문 ID
            session: DB 세션

        Returns:
            position_id: 생성된 포지션 ID
        """
        lock = await self._get_lock(user_id, symbol)

        async with lock:
            # 1. 메모리 캐시 업데이트
            if user_id not in self._active_positions:
                self._active_positions[user_id] = {}
            if symbol not in self._active_positions[user_id]:
                self._active_positions[user_id][symbol] = set()
            self._active_positions[user_id][symbol].add(bot_instance_id)

            self._bot_positions[bot_instance_id] = {
                "symbol": symbol,
                "side": side,
                "size": size,
                "entry_price": entry_price,
                "exchange_order_id": exchange_order_id,
                "is_open": True,
                "opened_at": datetime.utcnow(),
            }

            # 2. DB에 포지션 저장
            position = Position(
                user_id=user_id,
                bot_instance_id=bot_instance_id,
                symbol=symbol,
                side=side,
                size=size,
                entry_price=Decimal(str(entry_price)),
                exchange_order_id=exchange_order_id,
            )
            session.add(position)
            await session.commit()
            await session.refresh(position)

            logger.info(
                f"Position registered: bot={bot_instance_id}, symbol={symbol}, "
                f"side={side}, size={size}, price={entry_price}"
            )
            return position.id

    async def update_position(
        self,
        user_id: int,
        bot_instance_id: int,
        symbol: str,
        size: float,
        entry_price: float,
        session: AsyncSession
    ):
        """
        포지션 업데이트 (추매 시)

        Args:
            user_id: 사용자 ID
            bot_instance_id: 봇 인스턴스 ID
            symbol: 거래 심볼
            size: 업데이트된 포지션 크기
            entry_price: 업데이트된 평균 진입가
            session: DB 세션
        """
        lock = await self._get_lock(user_id, symbol)

        async with lock:
            if bot_instance_id in self._bot_positions:
                self._bot_positions[bot_instance_id]["size"] = size
                self._bot_positions[bot_instance_id]["entry_price"] = entry_price

            result = await session.execute(
                select(Position).where(
                    and_(
                        Position.user_id == user_id,
                        Position.bot_instance_id == bot_instance_id,
                        Position.symbol == symbol
                    )
                )
            )
            position = result.scalar_one_or_none()
            if position:
                position.size = size
                position.entry_price = Decimal(str(entry_price))
                await session.commit()

    async def close_position(
        self,
        user_id: int,
        bot_instance_id: int,
        symbol: str,
        exit_price: float,
        pnl: float,
        session: AsyncSession
    ):
        """
        포지션 청산 (메모리 캐시 + DB 업데이트)

        Args:
            user_id: 사용자 ID
            bot_instance_id: 봇 인스턴스 ID
            symbol: 거래 심볼
            exit_price: 청산 가격
            pnl: 손익
            session: DB 세션
        """
        lock = await self._get_lock(user_id, symbol)

        async with lock:
            # 1. 메모리 캐시에서 제거
            if user_id in self._active_positions:
                if symbol in self._active_positions[user_id]:
                    self._active_positions[user_id][symbol].discard(bot_instance_id)
                    if not self._active_positions[user_id][symbol]:
                        del self._active_positions[user_id][symbol]

            if bot_instance_id in self._bot_positions:
                del self._bot_positions[bot_instance_id]

            # 2. DB에서 포지션 업데이트 (size=0 또는 삭제)
            result = await session.execute(
                select(Position).where(
                    and_(
                        Position.user_id == user_id,
                        Position.bot_instance_id == bot_instance_id,
                        Position.symbol == symbol
                    )
                )
            )
            position = result.scalar_one_or_none()
            if position:
                position.size = 0
                position.pnl = Decimal(str(pnl))
                await session.commit()

            logger.info(
                f"Position closed: bot={bot_instance_id}, symbol={symbol}, "
                f"exit_price={exit_price}, pnl={pnl}"
            )

    def get_bot_position(self, bot_instance_id: int) -> Optional[dict]:
        """봇의 현재 포지션 정보 반환 (메모리 캐시)"""
        return self._bot_positions.get(bot_instance_id)

    def get_user_active_symbols(self, user_id: int) -> Dict[str, Set[int]]:
        """사용자의 활성 심볼별 봇 목록 반환"""
        return self._active_positions.get(user_id, {}).copy()

    def is_bot_in_position(self, bot_instance_id: int) -> bool:
        """봇이 현재 포지션 보유 중인지 확인"""
        pos = self._bot_positions.get(bot_instance_id)
        return pos is not None and pos.get("is_open", False)

    async def sync_from_db(self, session: AsyncSession, user_id: Optional[int] = None):
        """
        DB에서 포지션 정보 동기화 (서버 시작 시 또는 불일치 발생 시)

        Args:
            session: DB 세션
            user_id: 특정 사용자만 동기화 (None이면 전체)
        """
        query = select(Position).where(Position.size > 0)
        if user_id is not None:
            query = query.where(Position.user_id == user_id)

        result = await session.execute(query)
        positions = result.scalars().all()

        for pos in positions:
            if pos.bot_instance_id is None:
                continue  # 기존 시스템 포지션 (봇 인스턴스 없음)

            # 메모리 캐시 업데이트
            if pos.user_id not in self._active_positions:
                self._active_positions[pos.user_id] = {}
            if pos.symbol not in self._active_positions[pos.user_id]:
                self._active_positions[pos.user_id][pos.symbol] = set()
            self._active_positions[pos.user_id][pos.symbol].add(pos.bot_instance_id)

            self._bot_positions[pos.bot_instance_id] = {
                "symbol": pos.symbol,
                "side": pos.side,
                "size": float(pos.size),
                "entry_price": float(pos.entry_price),
                "exchange_order_id": pos.exchange_order_id,
                "is_open": True,
            }

        logger.info(f"Synced {len(positions)} positions from DB")

    def clear_bot_cache(self, bot_instance_id: int, user_id: int = None):
        """봇 캐시 정리 (봇 정지 시)"""
        if bot_instance_id in self._bot_positions:
            pos = self._bot_positions[bot_instance_id]
            symbol = pos.get("symbol")

            # active_positions에서 제거
            if user_id and user_id in self._active_positions:
                if symbol and symbol in self._active_positions[user_id]:
                    self._active_positions[user_id][symbol].discard(bot_instance_id)

            del self._bot_positions[bot_instance_id]
            logger.debug(f"Cleared cache for bot {bot_instance_id}")


# 싱글톤 인스턴스
bot_isolation_manager = BotIsolationManager()
