"""
그리드 봇 실행기 (Grid Bot Runner)

관련 문서: docs/MULTI_BOT_03_IMPLEMENTATION.md
관련 모델: GridBotConfig, GridOrder

그리드 봇 동작 원리:
1. 가격 범위(lower_price ~ upper_price)를 grid_count개로 분할
2. 각 그리드 가격에 매수 지정가 주문 설정
3. 매수 체결 시 → 한 단계 위 가격에 매도 주문 설정
4. 매도 체결 시 → 같은 가격에 매수 주문 재설정 (사이클 반복)

지원 모드:
- ARITHMETIC: 등차 그리드 (균등 가격 간격)
- GEOMETRIC: 등비 그리드 (균등 비율 간격)
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database.models import (
    ApiKey,
    BotInstance,
    GridBotConfig,
    GridMode,
    GridOrder,
    GridOrderStatus,
    Trade,
    TradeSource,
)
from ..services.bitget_rest import OrderSide, get_bitget_rest
from ..services.telegram import TradeResult, get_telegram_notifier
from ..services.trade_executor import InvalidApiKeyError
from ..utils.crypto_secrets import decrypt_secret

logger = logging.getLogger(__name__)


class GridBotRunner:
    """
    그리드 봇 실행 관리자

    역할:
    1. 그리드 가격 계산 (등차/등비)
    2. 초기 매수 주문 설정
    3. 체결 모니터링 및 주문 갱신
    4. 수익 계산 및 기록
    """

    def __init__(self, market_queue: asyncio.Queue):
        self.market_queue = market_queue
        self.tasks: Dict[int, asyncio.Task] = {}  # bot_instance_id -> Task
        self._stop_flags: Dict[int, bool] = {}  # Graceful shutdown flags

    def is_running(self, bot_instance_id: int) -> bool:
        """봇이 실행 중인지 확인"""
        return bot_instance_id in self.tasks and not self.tasks[bot_instance_id].done()

    async def start(self, session_factory, bot_instance_id: int, user_id: int):
        """그리드 봇 시작"""
        if self.is_running(bot_instance_id):
            logger.warning(f"Grid bot {bot_instance_id} is already running")
            return

        self._stop_flags[bot_instance_id] = False
        task = asyncio.create_task(
            self._run_grid_loop(session_factory, bot_instance_id, user_id)
        )
        self.tasks[bot_instance_id] = task
        logger.info(f"Started grid bot {bot_instance_id} for user {user_id}")

    def stop(self, bot_instance_id: int):
        """그리드 봇 정지"""
        if self.is_running(bot_instance_id):
            logger.info(f"Stopping grid bot {bot_instance_id}")
            self._stop_flags[bot_instance_id] = True
            self.tasks[bot_instance_id].cancel()
        else:
            logger.warning(f"Grid bot {bot_instance_id} is not running")

    # ============================================================
    # 그리드 계산 로직
    # ============================================================

    def calculate_grid_prices(
        self, lower_price: float, upper_price: float, grid_count: int, mode: GridMode
    ) -> List[float]:
        """
        그리드 가격 계산

        Args:
            lower_price: 하한가
            upper_price: 상한가
            grid_count: 그리드 수
            mode: ARITHMETIC(등차) 또는 GEOMETRIC(등비)

        Returns:
            그리드 가격 리스트 (낮은 가격 → 높은 가격 순)
        """
        if mode == GridMode.ARITHMETIC:
            # 등차 그리드: 가격 간격 균등
            step = (upper_price - lower_price) / (grid_count - 1)
            prices = [lower_price + i * step for i in range(grid_count)]
        else:
            # 등비 그리드: 비율 간격 균등
            ratio = (upper_price / lower_price) ** (1 / (grid_count - 1))
            prices = [lower_price * (ratio**i) for i in range(grid_count)]

        return [round(p, 8) for p in prices]

    def calculate_per_grid_amount(
        self, total_investment: float, grid_count: int, leverage: int = 1
    ) -> float:
        """
        그리드당 투자금 계산

        Args:
            total_investment: 총 투자금 (USDT)
            grid_count: 그리드 수
            leverage: 레버리지

        Returns:
            그리드당 투자금 (USDT)
        """
        # 그리드의 절반 정도에 초기 매수 주문이 설정된다고 가정
        effective_grids = grid_count // 2 + 1
        return (total_investment * leverage) / effective_grids

    def calculate_order_qty(
        self, investment_per_grid: float, price: float, min_qty: float = 0.001
    ) -> float:
        """
        주문 수량 계산

        Args:
            investment_per_grid: 그리드당 투자금
            price: 주문 가격
            min_qty: 최소 주문 수량

        Returns:
            주문 수량
        """
        qty = investment_per_grid / price
        return max(round(qty, 6), min_qty)

    # ============================================================
    # 메인 실행 루프
    # ============================================================

    async def _run_grid_loop(self, session_factory, bot_instance_id: int, user_id: int):
        """그리드 봇 메인 루프"""
        logger.info(
            f"Starting grid bot loop: bot_id={bot_instance_id}, user_id={user_id}"
        )

        try:
            async with session_factory() as session:
                # 1. 봇 인스턴스 및 그리드 설정 로드
                bot_instance, grid_config = await self._load_grid_config(
                    session, bot_instance_id, user_id
                )

                if not grid_config:
                    logger.error(f"Grid config not found for bot {bot_instance_id}")
                    await self._update_bot_error(
                        session, bot_instance_id, "GRID_CONFIG_NOT_FOUND"
                    )
                    return

                logger.info(
                    f"Loaded grid config: {grid_config.lower_price} ~ {grid_config.upper_price}, "
                    f"grids={grid_config.grid_count}, mode={grid_config.grid_mode.value}"
                )

                # 2. Bitget 클라이언트 초기화
                try:
                    bitget_client = await self._init_bitget_client(session, user_id)
                except InvalidApiKeyError as e:
                    logger.error(f"Invalid API key for user {user_id}: {e}")
                    await self._update_bot_error(
                        session, bot_instance_id, "INVALID_API_KEY"
                    )
                    return

                # 3. 그리드 가격 계산
                grid_prices = self.calculate_grid_prices(
                    float(grid_config.lower_price),
                    float(grid_config.upper_price),
                    grid_config.grid_count,
                    grid_config.grid_mode,
                )

                # 4. 그리드 주문 초기화 (DB에 없으면 생성)
                grid_orders = await self._initialize_grid_orders(
                    session, grid_config.id, grid_prices
                )

                # 5. 현재 가격 조회 및 초기 주문 설정
                symbol = bot_instance.symbol
                current_price = await self._get_current_price(bitget_client, symbol)

                if current_price:
                    await self._setup_initial_orders(
                        session,
                        bitget_client,
                        bot_instance,
                        grid_config,
                        grid_orders,
                        current_price,
                    )

                # 6. 체결 모니터링 루프
                # market_queue에서 가격 수신, 타임아웃 시 REST 폴백
                queue_timeout = 5.0  # 5초 타임아웃
                consecutive_errors = 0
                max_errors = 10
                last_check_time = datetime.utcnow()
                check_interval_seconds = 3  # 최소 체결 확인 간격

                logger.info(
                    f"Grid bot {bot_instance_id}: Starting price monitoring loop (queue + REST fallback)"
                )

                while not self._stop_flags.get(bot_instance_id, False):
                    try:
                        # market_queue에서 가격 데이터 수신 시도
                        try:
                            market_data = await asyncio.wait_for(
                                self.market_queue.get(), timeout=queue_timeout
                            )
                            # 심볼 매칭 확인
                            market_symbol = market_data.get("symbol", "")
                            if market_symbol == symbol or symbol in market_symbol:
                                current_price = float(market_data.get("price", 0))
                                logger.debug(
                                    f"Grid bot {bot_instance_id}: Price from queue: ${current_price:.2f}"
                                )
                            else:
                                # 다른 심볼 데이터는 다시 큐에 넣음 (다른 봇용)
                                # 단, 큐가 가득 차면 버림
                                try:
                                    self.market_queue.put_nowait(market_data)
                                except asyncio.QueueFull:
                                    pass
                                continue
                        except asyncio.TimeoutError:
                            # 타임아웃 시 REST API 폴백
                            current_price = await self._get_current_price(
                                bitget_client, symbol
                            )
                            if current_price:
                                logger.debug(
                                    f"Grid bot {bot_instance_id}: Price from REST: ${current_price:.2f}"
                                )

                        # 최소 간격 체크 (너무 자주 체결 확인하지 않도록)
                        now = datetime.utcnow()
                        elapsed = (now - last_check_time).total_seconds()
                        if elapsed < check_interval_seconds:
                            continue

                        if current_price and current_price > 0:
                            # 체결 확인 및 주문 갱신
                            await self._check_and_update_orders(
                                session,
                                bitget_client,
                                bot_instance,
                                grid_config,
                                grid_orders,
                                current_price,
                            )
                            last_check_time = now

                        consecutive_errors = 0

                    except Exception as e:
                        consecutive_errors += 1
                        logger.error(
                            f"Grid bot {bot_instance_id} error ({consecutive_errors}/{max_errors}): {e}",
                            exc_info=True,
                        )
                        if consecutive_errors >= max_errors:
                            await self._update_bot_error(
                                session, bot_instance_id, "TOO_MANY_ERRORS"
                            )
                            break
                        await asyncio.sleep(queue_timeout)

        except asyncio.CancelledError:
            logger.info(f"Grid bot {bot_instance_id} cancelled")
            # 열린 주문 취소 (옵션)
            try:
                async with session_factory() as cleanup_session:
                    await self._cleanup_on_stop(cleanup_session, bot_instance_id)
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            raise

        except Exception as exc:
            logger.error(
                f"Fatal error in grid bot {bot_instance_id}: {exc}", exc_info=True
            )

        finally:
            if bot_instance_id in self.tasks:
                del self.tasks[bot_instance_id]
            if bot_instance_id in self._stop_flags:
                del self._stop_flags[bot_instance_id]
            logger.info(f"Grid bot {bot_instance_id} loop ended")

    # ============================================================
    # 주문 관리
    # ============================================================

    async def _setup_initial_orders(
        self,
        session: AsyncSession,
        bitget_client,
        bot_instance: BotInstance,
        grid_config: GridBotConfig,
        grid_orders: List[GridOrder],
        current_price: float,
    ):
        """초기 매수 주문 설정 (현재 가격 이하의 그리드)"""
        symbol = bot_instance.symbol
        per_grid = self.calculate_per_grid_amount(
            float(grid_config.total_investment),
            grid_config.grid_count,
            bot_instance.max_leverage,
        )

        placed_count = 0

        for order in grid_orders:
            grid_price = float(order.grid_price)

            # 현재 가격보다 낮은 그리드에만 매수 주문
            if grid_price < current_price and order.status == GridOrderStatus.PENDING:
                qty = self.calculate_order_qty(per_grid, grid_price)

                try:
                    # 매수 지정가 주문
                    result = await bitget_client.place_limit_order(
                        symbol=symbol,
                        side=OrderSide.BUY,
                        price=grid_price,
                        size=qty,
                        margin_coin="USDT",
                    )

                    order_id = result.get("data", {}).get("orderId")
                    if order_id:
                        order.buy_order_id = order_id
                        order.status = GridOrderStatus.BUY_PLACED
                        placed_count += 1

                        logger.info(
                            f"Grid {order.grid_index}: Buy order placed at ${grid_price:.2f}, "
                            f"qty={qty:.6f}, order_id={order_id}"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to place buy order at grid {order.grid_index}: {e}"
                    )

        await session.commit()
        logger.info(
            f"Initial orders: {placed_count} buy orders placed out of {len(grid_orders)} grids"
        )

    async def _check_and_update_orders(
        self,
        session: AsyncSession,
        bitget_client,
        bot_instance: BotInstance,
        grid_config: GridBotConfig,
        grid_orders: List[GridOrder],
        current_price: float,
    ):
        """체결 확인 및 주문 갱신"""
        symbol = bot_instance.symbol
        per_grid = self.calculate_per_grid_amount(
            float(grid_config.total_investment),
            grid_config.grid_count,
            bot_instance.max_leverage,
        )

        for order in grid_orders:
            try:
                # 1. 매수 주문 체결 확인
                if order.status == GridOrderStatus.BUY_PLACED and order.buy_order_id:
                    filled = await self._check_order_filled(
                        bitget_client, order.buy_order_id, symbol
                    )

                    if filled:
                        filled_price, filled_qty = filled
                        order.buy_filled_price = Decimal(str(filled_price))
                        order.buy_filled_qty = Decimal(str(filled_qty))
                        order.buy_filled_at = datetime.utcnow()
                        order.status = GridOrderStatus.BUY_FILLED

                        logger.info(
                            f"Grid {order.grid_index}: Buy FILLED at ${filled_price:.2f}, qty={filled_qty:.6f}"
                        )

                        # WebSocket 알림 (NEW)
                        await self._notify_grid_order_update(
                            bot_instance.user_id,
                            bot_instance.id,
                            order.grid_index,
                            "buy_filled",
                            filled_price,
                            filled_qty,
                        )

                        # 매도 주문 설정 (한 단계 위 가격)
                        sell_price = self._get_next_sell_price(
                            grid_orders, order.grid_index
                        )
                        if sell_price:
                            await self._place_sell_order(
                                session,
                                bitget_client,
                                bot_instance,
                                order,
                                sell_price,
                                filled_qty,
                            )

                # 2. 매도 주문 체결 확인
                elif (
                    order.status == GridOrderStatus.SELL_PLACED and order.sell_order_id
                ):
                    filled = await self._check_order_filled(
                        bitget_client, order.sell_order_id, symbol
                    )

                    if filled:
                        filled_price, filled_qty = filled
                        order.sell_filled_price = Decimal(str(filled_price))
                        order.sell_filled_qty = Decimal(str(filled_qty))
                        order.sell_filled_at = datetime.utcnow()

                        # 수익 계산
                        buy_price = float(order.buy_filled_price or order.grid_price)
                        profit = (filled_price - buy_price) * filled_qty
                        order.profit = Decimal(str(profit))
                        order.status = GridOrderStatus.SELL_FILLED

                        logger.info(
                            f"Grid {order.grid_index}: Sell FILLED at ${filled_price:.2f}, "
                            f"profit=${profit:.4f}"
                        )

                        # WebSocket 알림 - 사이클 완료 (NEW)
                        await self._notify_grid_cycle_complete(
                            bot_instance.user_id,
                            bot_instance.id,
                            order.grid_index,
                            profit,
                            buy_price,
                            filled_price,
                            filled_qty,
                        )

                        # 거래 기록
                        await self._record_grid_trade(
                            session, bot_instance, order, profit
                        )

                        # 사이클 재시작: 같은 가격에 매수 주문 재설정
                        await self._restart_grid_cycle(
                            session, bitget_client, bot_instance, order, per_grid
                        )

                        # 텔레그램 알림
                        if bot_instance.telegram_notify:
                            await self._notify_grid_profit(bot_instance, order, profit)

            except Exception as e:
                logger.error(f"Error processing grid {order.grid_index}: {e}")

        await session.commit()

    async def _place_sell_order(
        self,
        session: AsyncSession,
        bitget_client,
        bot_instance: BotInstance,
        order: GridOrder,
        sell_price: float,
        qty: float,
    ):
        """매도 주문 설정"""
        try:
            result = await bitget_client.place_limit_order(
                symbol=bot_instance.symbol,
                side=OrderSide.SELL,
                price=sell_price,
                size=qty,
                margin_coin="USDT",
            )

            order_id = result.get("data", {}).get("orderId")
            if order_id:
                order.sell_order_id = order_id
                order.status = GridOrderStatus.SELL_PLACED

                logger.info(
                    f"Grid {order.grid_index}: Sell order placed at ${sell_price:.2f}, "
                    f"qty={qty:.6f}, order_id={order_id}"
                )

        except Exception as e:
            logger.error(f"Failed to place sell order for grid {order.grid_index}: {e}")

    async def _restart_grid_cycle(
        self,
        session: AsyncSession,
        bitget_client,
        bot_instance: BotInstance,
        order: GridOrder,
        per_grid: float,
    ):
        """그리드 사이클 재시작 (매수 주문 재설정)"""
        grid_price = float(order.grid_price)
        qty = self.calculate_order_qty(per_grid, grid_price)

        try:
            result = await bitget_client.place_limit_order(
                symbol=bot_instance.symbol,
                side=OrderSide.BUY,
                price=grid_price,
                size=qty,
                margin_coin="USDT",
            )

            order_id = result.get("data", {}).get("orderId")
            if order_id:
                # 상태 리셋
                order.buy_order_id = order_id
                order.sell_order_id = None
                order.buy_filled_price = None
                order.buy_filled_qty = None
                order.buy_filled_at = None
                order.sell_filled_price = None
                order.sell_filled_qty = None
                order.sell_filled_at = None
                order.status = GridOrderStatus.BUY_PLACED

                logger.info(
                    f"Grid {order.grid_index}: Cycle restarted with buy order at ${grid_price:.2f}"
                )

        except Exception as e:
            logger.error(f"Failed to restart grid cycle {order.grid_index}: {e}")

    # ============================================================
    # 헬퍼 메서드
    # ============================================================

    def _get_next_sell_price(
        self, grid_orders: List[GridOrder], current_index: int
    ) -> Optional[float]:
        """다음 그리드 가격 (매도 가격) 반환"""
        for order in grid_orders:
            if order.grid_index == current_index + 1:
                return float(order.grid_price)
        return None

    async def _check_order_filled(
        self, bitget_client, order_id: str, symbol: str
    ) -> Optional[Tuple[float, float]]:
        """주문 체결 확인 - 체결 시 (가격, 수량) 반환"""
        try:
            order_info = await bitget_client.get_order(symbol=symbol, order_id=order_id)

            if order_info and order_info.get("state") == "filled":
                filled_price = float(order_info.get("priceAvg", 0))
                filled_qty = float(order_info.get("filledQty", 0))
                return filled_price, filled_qty

        except Exception as e:
            logger.debug(f"Order {order_id} check error: {e}")

        return None

    async def _get_current_price(self, bitget_client, symbol: str) -> Optional[float]:
        """현재 가격 조회"""
        try:
            ticker = await bitget_client.get_ticker(symbol)

            # Bitget API v2는 리스트로 반환함
            if isinstance(ticker, list) and len(ticker) > 0:
                price = float(ticker[0].get("lastPr", 0))
            elif isinstance(ticker, dict):
                # 딕셔너리인 경우도 처리 (하위 호환성)
                price = float(ticker.get("lastPr", 0))
            else:
                logger.warning(f"Unexpected ticker format for {symbol}: {type(ticker)}")
                return None

            return price if price > 0 else None
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None

    async def _load_grid_config(
        self, session: AsyncSession, bot_instance_id: int, user_id: int
    ) -> Tuple[Optional[BotInstance], Optional[GridBotConfig]]:
        """봇 인스턴스 및 그리드 설정 로드"""
        result = await session.execute(
            select(BotInstance)
            .options(selectinload(BotInstance.grid_config))
            .where(
                and_(
                    BotInstance.id == bot_instance_id,
                    BotInstance.user_id == user_id,
                    BotInstance.is_active is True,
                )
            )
        )
        bot = result.scalar_one_or_none()

        # 그리드 봇인지 확인 (grid_config 존재 여부로 판별)
        if bot and bot.grid_config:
            return bot, bot.grid_config
        return None, None

    async def _initialize_grid_orders(
        self, session: AsyncSession, grid_config_id: int, grid_prices: List[float]
    ) -> List[GridOrder]:
        """그리드 주문 레코드 초기화"""
        # 기존 주문 조회
        result = await session.execute(
            select(GridOrder)
            .where(GridOrder.grid_config_id == grid_config_id)
            .order_by(GridOrder.grid_index)
        )
        existing = list(result.scalars())

        if existing:
            return existing

        # 새로 생성
        orders = []
        for i, price in enumerate(grid_prices):
            order = GridOrder(
                grid_config_id=grid_config_id,
                grid_index=i,
                grid_price=Decimal(str(price)),
                status=GridOrderStatus.PENDING,
            )
            session.add(order)
            orders.append(order)

        await session.commit()
        logger.info(f"Created {len(orders)} grid order records")
        return orders

    async def _init_bitget_client(self, session: AsyncSession, user_id: int):
        """Bitget 클라이언트 초기화"""
        result = await session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
        api_key_obj = result.scalars().first()

        if not api_key_obj:
            raise InvalidApiKeyError("API key not found")

        api_key = decrypt_secret(api_key_obj.encrypted_api_key)
        api_secret = decrypt_secret(api_key_obj.encrypted_secret_key)
        passphrase = (
            decrypt_secret(api_key_obj.encrypted_passphrase)
            if api_key_obj.encrypted_passphrase
            else ""
        )

        return get_bitget_rest(api_key, api_secret, passphrase)

    async def _update_bot_error(
        self, session: AsyncSession, bot_instance_id: int, error_msg: str
    ):
        """봇 에러 상태 업데이트"""
        await session.execute(
            update(BotInstance)
            .where(BotInstance.id == bot_instance_id)
            .values(last_error=error_msg, is_running=False)
        )
        await session.commit()

    async def _cleanup_on_stop(self, session: AsyncSession, bot_instance_id: int):
        """봇 정지 시 정리 작업"""
        await session.execute(
            update(BotInstance)
            .where(BotInstance.id == bot_instance_id)
            .values(is_running=False, last_stopped_at=datetime.utcnow())
        )
        await session.commit()
        logger.info(f"Grid bot {bot_instance_id} cleanup complete")

    async def _record_grid_trade(
        self,
        session: AsyncSession,
        bot_instance: BotInstance,
        order: GridOrder,
        profit: float,
    ):
        """그리드 거래 기록"""
        trade = Trade(
            user_id=bot_instance.user_id,
            bot_instance_id=bot_instance.id,
            trade_source=TradeSource.grid_bot,
            symbol=bot_instance.symbol,
            side="SELL",
            qty=order.sell_filled_qty,
            entry_price=order.buy_filled_price,
            exit_price=order.sell_filled_price,
            pnl=Decimal(str(profit)),
            pnl_percent=Decimal(
                str(
                    (profit / float(order.buy_filled_price * order.buy_filled_qty))
                    * 100
                )
            ),
            leverage=bot_instance.max_leverage,
            exit_reason=f"Grid {order.grid_index} cycle complete",
        )
        session.add(trade)
        await session.commit()

    async def _notify_grid_profit(
        self, bot_instance: BotInstance, order: GridOrder, profit: float
    ):
        """그리드 수익 알림 (텔레그램)"""
        try:
            notifier = get_telegram_notifier()
            if notifier.is_enabled():
                trade_result = TradeResult(
                    symbol=bot_instance.symbol,
                    direction="Grid",
                    entry_price=float(order.buy_filled_price),
                    exit_price=float(order.sell_filled_price),
                    quantity=float(order.sell_filled_qty),
                    pnl_percent=float(
                        (
                            profit
                            / (
                                float(order.buy_filled_price)
                                * float(order.buy_filled_qty)
                            )
                        )
                        * 100
                    ),
                    pnl_usdt=profit,
                    exit_reason=f"Grid #{order.grid_index} (Bot: {bot_instance.name})",
                    duration_minutes=0,
                )
                await notifier.notify_close_trade(trade_result)
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")

    async def _notify_grid_order_update(
        self,
        user_id: int,
        bot_id: int,
        grid_index: int,
        status: str,
        price: float,
        qty: float,
    ):
        """그리드 주문 상태 WebSocket 알림 (NEW)"""
        try:
            from ..websockets.ws_server import WebSocketManager

            await WebSocketManager.send_grid_order_update(
                user_id,
                {
                    "bot_id": bot_id,
                    "grid_index": grid_index,
                    "status": status,
                    "price": price,
                    "qty": qty,
                },
            )
        except Exception as e:
            logger.debug(f"WebSocket grid order update failed: {e}")

    async def _notify_grid_cycle_complete(
        self,
        user_id: int,
        bot_id: int,
        grid_index: int,
        profit: float,
        buy_price: float,
        sell_price: float,
        qty: float,
    ):
        """그리드 사이클 완료 WebSocket 알림 (NEW)"""
        try:
            from ..websockets.ws_server import WebSocketManager

            await WebSocketManager.send_grid_cycle_complete(
                user_id,
                {
                    "bot_id": bot_id,
                    "grid_index": grid_index,
                    "profit": profit,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "qty": qty,
                },
            )
        except Exception as e:
            logger.debug(f"WebSocket grid cycle complete failed: {e}")


# 싱글톤 인스턴스 (지연 초기화)
_grid_bot_runner_instance: Optional[GridBotRunner] = None


def get_grid_bot_runner(market_queue: asyncio.Queue) -> GridBotRunner:
    """GridBotRunner 싱글톤 인스턴스 반환 (지연 초기화)"""
    global _grid_bot_runner_instance
    if _grid_bot_runner_instance is None:
        _grid_bot_runner_instance = GridBotRunner(market_queue)
    return _grid_bot_runner_instance


# 편의를 위한 프록시 객체 (초기화 전에도 import 가능)
class GridBotRunnerProxy:
    """
    GridBotRunner 프록시

    BotRunner에서 import할 때 market_queue가 없어도 import 가능하도록 함.
    실제 사용 시점에 BotRunner의 market_queue로 초기화됨.
    """

    _instance: Optional[GridBotRunner] = None

    @classmethod
    def initialize(cls, market_queue: asyncio.Queue):
        """market_queue로 GridBotRunner 초기화"""
        if cls._instance is None:
            cls._instance = GridBotRunner(market_queue)
        return cls._instance

    @classmethod
    def get_instance(cls) -> Optional[GridBotRunner]:
        """초기화된 인스턴스 반환 (없으면 None)"""
        return cls._instance


# BotRunner에서 사용할 프록시
grid_bot_runner = GridBotRunnerProxy
