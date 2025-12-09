import asyncio
import logging
import json
from collections import deque
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import (
    BotStatus,
    Position,
    Strategy,
    Trade,
    User,
    ApiKey,
    RiskSettings,
)
from ..services.strategy_engine import run as run_strategy
from ..services.strategy_loader import generate_signal_with_strategy
from ..services.equity_service import record_equity
from ..services.trade_executor import (
    InvalidApiKeyError,
    ensure_client,
    place_market_order,
)
from ..services.exchanges import exchange_manager
from ..services.bitget_rest import get_bitget_rest, OrderSide
from ..utils.crypto_secrets import decrypt_secret
from ..websockets.ws_server import broadcast_to_user
from ..services.telegram import get_telegram_notifier, TradeInfo, TradeResult

logger = logging.getLogger(__name__)


class BotRunner:
    def __init__(self, market_queue: asyncio.Queue):
        self.market_queue = market_queue
        self.tasks: Dict[int, asyncio.Task] = {}
        self._daily_loss_exceeded: Dict[
            int, bool
        ] = {}  # 사용자별 일일 손실 초과 여부 캐시

    async def check_daily_loss_limit(
        self, session: AsyncSession, user_id: int
    ) -> tuple[bool, Optional[float], Optional[float]]:
        """
        일일 손실 한도 체크

        Returns:
            tuple: (거래 가능 여부, 오늘 손익, 일일 손실 한도)
            - True: 거래 가능
            - False: 일일 손실 한도 초과
        """
        try:
            # 1. 리스크 설정 조회
            result = await session.execute(
                select(RiskSettings).where(RiskSettings.user_id == user_id)
            )
            risk_settings = result.scalar_one_or_none()

            if not risk_settings or not risk_settings.daily_loss_limit:
                # 설정 없으면 제한 없음
                return True, None, None

            daily_limit = risk_settings.daily_loss_limit

            # 2. 오늘 날짜 (UTC 기준)
            today_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # 3. 오늘 거래의 총 손익 계산
            pnl_result = await session.execute(
                select(func.sum(Trade.pnl))
                .where(Trade.user_id == user_id)
                .where(Trade.created_at >= today_start)
                .where(Trade.pnl.isnot(None))
            )
            today_pnl = pnl_result.scalar() or 0.0

            # 4. 손실이 한도를 초과했는지 확인 (손실은 음수)
            if today_pnl < 0 and abs(today_pnl) >= daily_limit:
                logger.warning(
                    f"🚫 User {user_id}: Daily loss limit EXCEEDED! "
                    f"Today's PnL: ${today_pnl:.2f}, Limit: -${daily_limit:.2f}"
                )
                self._daily_loss_exceeded[user_id] = True
                return False, today_pnl, daily_limit

            # 5. 한도 내에 있으면 거래 가능
            self._daily_loss_exceeded[user_id] = False
            logger.debug(
                f"User {user_id}: Daily loss check passed. "
                f"Today's PnL: ${today_pnl:.2f}, Limit: -${daily_limit:.2f}"
            )
            return True, today_pnl, daily_limit

        except Exception as e:
            logger.error(f"Error checking daily loss limit for user {user_id}: {e}")
            # 에러 발생 시 안전하게 거래 허용
            return True, None, None

    async def check_max_positions(
        self, session: AsyncSession, user_id: int, bitget_client
    ) -> tuple[bool, int, Optional[int]]:
        """
        최대 포지션 개수 체크

        Returns:
            tuple: (거래 가능 여부, 현재 포지션 수, 최대 허용 수)
            - True: 신규 포지션 진입 가능
            - False: 최대 포지션 개수 초과
        """
        try:
            # 1. 리스크 설정 조회
            result = await session.execute(
                select(RiskSettings).where(RiskSettings.user_id == user_id)
            )
            risk_settings = result.scalar_one_or_none()

            if not risk_settings or not risk_settings.max_positions:
                # 설정 없으면 제한 없음
                return True, 0, None

            max_positions = risk_settings.max_positions

            # 2. Bitget에서 현재 오픈 포지션 수 조회
            try:
                positions = await bitget_client.get_positions()
                # 실제 사이즈가 있는 포지션만 카운트
                current_positions = len(
                    [
                        p
                        for p in positions
                        if float(p.get("total", 0)) > 0
                        or float(p.get("available", 0)) > 0
                    ]
                )
            except Exception as e:
                logger.warning(f"Failed to get positions from Bitget: {e}")
                current_positions = 0

            # 3. 포지션 개수 체크
            if current_positions >= max_positions:
                logger.warning(
                    f"🚫 User {user_id}: Max positions limit reached! "
                    f"Current: {current_positions}, Max: {max_positions}"
                )
                return False, current_positions, max_positions

            logger.debug(
                f"User {user_id}: Position check passed. "
                f"Current: {current_positions}, Max: {max_positions}"
            )
            return True, current_positions, max_positions

        except Exception as e:
            logger.error(f"Error checking max positions for user {user_id}: {e}")
            return True, 0, None

    async def check_leverage_limit(
        self, session: AsyncSession, user_id: int, requested_leverage: int = 10
    ) -> tuple[bool, int, Optional[int]]:
        """
        최대 레버리지 체크

        Args:
            requested_leverage: 사용하려는 레버리지 (기본 10x)

        Returns:
            tuple: (사용 가능 여부, 허용된 레버리지, 최대 허용 레버리지)
            - True: 요청한 레버리지 사용 가능
            - False: 최대 레버리지 초과 (허용된 레버리지로 제한됨)
        """
        try:
            # 1. 리스크 설정 조회
            result = await session.execute(
                select(RiskSettings).where(RiskSettings.user_id == user_id)
            )
            risk_settings = result.scalar_one_or_none()

            if not risk_settings or not risk_settings.max_leverage:
                # 설정 없으면 요청한 레버리지 그대로 사용
                return True, requested_leverage, None

            max_leverage = risk_settings.max_leverage

            # 2. 레버리지 체크
            if requested_leverage > max_leverage:
                logger.warning(
                    f"⚠️ User {user_id}: Leverage limited! "
                    f"Requested: {requested_leverage}x, Max allowed: {max_leverage}x"
                )
                # 최대 허용 레버리지로 제한 (거래는 진행)
                return False, max_leverage, max_leverage

            logger.debug(
                f"User {user_id}: Leverage check passed. "
                f"Using: {requested_leverage}x, Max: {max_leverage}x"
            )
            return True, requested_leverage, max_leverage

        except Exception as e:
            logger.error(f"Error checking leverage limit for user {user_id}: {e}")
            return True, requested_leverage, None

    async def get_all_risk_checks(
        self,
        session: AsyncSession,
        user_id: int,
        bitget_client,
        requested_leverage: int = 10,
    ) -> dict:
        """
        모든 리스크 체크를 한 번에 수행

        Returns:
            dict: {
                "can_trade": bool,          # 거래 가능 여부
                "blocked_reasons": list,    # 차단 사유 목록
                "daily_loss": {...},        # 일일 손실 정보
                "positions": {...},         # 포지션 정보
                "leverage": {...}           # 레버리지 정보
            }
        """
        result = {
            "can_trade": True,
            "blocked_reasons": [],
            "daily_loss": {},
            "positions": {},
            "leverage": {},
        }

        # 1. 일일 손실 체크
        can_trade_loss, today_pnl, daily_limit = await self.check_daily_loss_limit(
            session, user_id
        )
        result["daily_loss"] = {
            "passed": can_trade_loss,
            "today_pnl": today_pnl,
            "limit": daily_limit,
        }
        if not can_trade_loss:
            result["can_trade"] = False
            result["blocked_reasons"].append(
                f"일일 손실 한도 초과 (${today_pnl:.2f} / -${daily_limit:.2f})"
            )

        # 2. 포지션 개수 체크
        can_trade_pos, current_pos, max_pos = await self.check_max_positions(
            session, user_id, bitget_client
        )
        result["positions"] = {
            "passed": can_trade_pos,
            "current": current_pos,
            "max": max_pos,
        }
        if not can_trade_pos:
            result["can_trade"] = False
            result["blocked_reasons"].append(
                f"최대 포지션 개수 도달 ({current_pos}/{max_pos})"
            )

        # 3. 레버리지 체크 (이건 제한만 하고 차단하지 않음)
        leverage_ok, allowed_leverage, max_leverage = await self.check_leverage_limit(
            session, user_id, requested_leverage
        )
        result["leverage"] = {
            "passed": leverage_ok,
            "requested": requested_leverage,
            "allowed": allowed_leverage,
            "max": max_leverage,
        }
        if not leverage_ok:
            result["blocked_reasons"].append(
                f"레버리지 제한됨 ({requested_leverage}x → {allowed_leverage}x)"
            )

        return result

    def is_running(self, user_id: int) -> bool:
        return user_id in self.tasks and not self.tasks[user_id].done()

    def stop(self, user_id: int):
        """봇 정지 (Graceful shutdown)"""
        if self.is_running(user_id):
            logger.info(f"Stopping bot for user {user_id}")
            self.tasks[user_id].cancel()
        else:
            logger.warning(f"Bot for user {user_id} is not running")

    async def start(self, session_factory, user_id: int):
        if self.is_running(user_id):
            return

        task = asyncio.create_task(self._run_loop(session_factory, user_id))
        self.tasks[user_id] = task

    async def _run_loop(self, session_factory, user_id: int):
        """
        봇 실행 메인 루프 (개선된 에러 핸들링)

        개선사항:
        - 상세한 에러 로깅
        - DB 세션 에러 처리
        - 전략 실행 에러 격리
        - 주문 실행 에러 격리
        - Graceful shutdown
        """
        logger.info(f"Starting bot loop for user {user_id}")

        try:
            async with session_factory() as session:
                # 1. 전략 로드
                try:
                    strategy = await self._get_user_strategy(session, user_id)
                    code_preview = strategy.code[:100] if strategy.code else "None"
                    logger.info(
                        f"Loaded strategy '{strategy.name}' for user {user_id}, code length: {len(strategy.code) if strategy.code else 0}, preview: {code_preview}..."
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to load strategy for user {user_id}: {e}",
                        exc_info=True,
                    )
                    await broadcast_to_user(
                        user_id,
                        {
                            "event": "bot_status",
                            "status": "error",
                            "message": f"STRATEGY_LOAD_ERROR: {str(e)}",
                        },
                    )
                    return

                # 2. Bitget API 클라이언트 초기화
                try:
                    # API 키 조회
                    result = await session.execute(
                        select(ApiKey).where(ApiKey.user_id == user_id)
                    )
                    api_key_obj = result.scalars().first()

                    if not api_key_obj:
                        raise InvalidApiKeyError("API key not found in database")

                    # API 키 복호화
                    api_key = decrypt_secret(api_key_obj.encrypted_api_key)
                    api_secret = decrypt_secret(api_key_obj.encrypted_secret_key)
                    passphrase = (
                        decrypt_secret(api_key_obj.encrypted_passphrase)
                        if api_key_obj.encrypted_passphrase
                        else ""
                    )

                    if not all([api_key, api_secret, passphrase]):
                        raise InvalidApiKeyError(
                            "Invalid or incomplete API credentials"
                        )

                    # Bitget REST 클라이언트 생성
                    bitget_client = get_bitget_rest(api_key, api_secret, passphrase)
                    logger.info(f"Bitget API client initialized for user {user_id}")

                except InvalidApiKeyError as e:
                    logger.error(f"Invalid API key for user {user_id}: {e}")
                    await broadcast_to_user(
                        user_id,
                        {
                            "event": "bot_status",
                            "status": "error",
                            "message": "INVALID_API_KEY",
                        },
                    )
                    return
                except Exception as e:
                    logger.error(
                        f"Failed to initialize Bitget client for user {user_id}: {e}",
                        exc_info=True,
                    )
                    await broadcast_to_user(
                        user_id,
                        {
                            "event": "bot_status",
                            "status": "error",
                            "message": f"CLIENT_INIT_ERROR: {str(e)}",
                        },
                    )
                    return

                # 3. 과거 캔들 데이터 로드 (CRITICAL: 전략 정확도 향상)
                candle_buffer = deque(maxlen=200)

                # 전략 파라미터에서 심볼과 타임프레임 미리 가져오기 (try 블록 밖에서 정의)
                strategy_params = json.loads(strategy.params) if strategy.params else {}
                symbol = strategy_params.get("symbol", "BTC/USDT").replace(
                    "/", ""
                )  # "BTCUSDT"
                timeframe = strategy_params.get("timeframe", "1h")

                try:
                    # Bitget API에서 과거 200개 캔들 가져오기
                    historical = await bitget_client.get_historical_candles(
                        symbol=symbol, interval=timeframe, limit=200
                    )

                    # 캔들 버퍼에 추가
                    for candle in historical:
                        candle_buffer.append(
                            {
                                "open": float(candle.get("open", 0)),
                                "high": float(candle.get("high", 0)),
                                "low": float(candle.get("low", 0)),
                                "close": float(candle.get("close", 0)),
                                "volume": float(candle.get("volume", 0)),
                                "time": candle.get("timestamp", 0),
                            }
                        )

                    logger.info(
                        f"✅ Loaded {len(candle_buffer)} historical candles for {symbol} {timeframe} (user {user_id})"
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to load historical candles for user {user_id}: {e}"
                    )
                    logger.info(
                        f"Continuing with empty candle buffer (strategies may have reduced accuracy)"
                    )

                # 4. 메인 트레이딩 루프
                consecutive_errors = 0
                max_consecutive_errors = 10
                current_position = None  # 현재 포지션 추적

                while True:
                    try:
                        # 마켓 데이터 수신 (타임아웃 추가)
                        try:
                            market = await asyncio.wait_for(
                                self.market_queue.get(), timeout=60.0
                            )
                        except asyncio.TimeoutError:
                            logger.warning(
                                f"No market data received for 60s (user {user_id})"
                            )
                            await broadcast_to_user(
                                user_id,
                                {
                                    "event": "bot_status",
                                    "status": "warning",
                                    "message": "NO_MARKET_DATA",
                                },
                            )
                            continue

                        price = float(market.get("price", 0))
                        market_symbol = market.get("symbol", "BTCUSDT")

                        # 심볼 정규화: BTC/USDT, BTCUSDT, BTC-USDT 모두 BTCUSDT로 변환
                        normalized_market = (
                            market_symbol.replace("/", "").replace("-", "").upper()
                        )
                        normalized_strategy = (
                            symbol.replace("/", "").replace("-", "").upper()
                        )

                        # Filter: Only process market data matching strategy symbol
                        if normalized_market != normalized_strategy:
                            # 10번에 한 번만 로그 (너무 많은 로그 방지)
                            if hasattr(self, "_skip_log_count"):
                                self._skip_log_count = (
                                    getattr(self, "_skip_log_count", 0) + 1
                                )
                                if self._skip_log_count % 100 == 0:
                                    logger.debug(
                                        f"Skipped {self._skip_log_count} market data (got {normalized_market}, need {normalized_strategy})"
                                    )
                            else:
                                self._skip_log_count = 1
                            continue  # Skip this market data

                        logger.info(
                            f"🔄 Processing market data: {market_symbol} @ ${price:,.2f} (user {user_id})"
                        )

                        if price <= 0:
                            logger.warning(f"Invalid price received: {price}")
                            continue

                        # 캔들 데이터 준비 - market 데이터를 캔들 형식으로 변환
                        new_candle = {
                            "open": market.get("open", price),
                            "high": market.get("high", price),
                            "low": market.get("low", price),
                            "close": market.get("close", price),
                            "volume": market.get("volume", 0),
                            "time": market.get("time", 0),
                        }

                        # 새 캔들을 버퍼에 추가 (롤링 윈도우)
                        candle_buffer.append(new_candle)

                        # 전체 캔들 버퍼를 전략에 전달 (1개가 아닌 전체!)
                        candles = list(candle_buffer)

                        # 새로운 전략 로더 사용 (포지션 정보 포함)
                        try:
                            # 실제 모드: 현재 포지션 상태를 전략에 전달
                            signal_result = generate_signal_with_strategy(
                                strategy_code=strategy.code,
                                current_price=price,
                                candles=candles,
                                params_json=strategy.params,
                                current_position=current_position,  # 실제 포지션 상태 전달
                            )

                            signal_action = signal_result.get("action", "hold")
                            signal_confidence = signal_result.get("confidence", 0)
                            signal_reason = signal_result.get("reason", "")
                            signal_size_from_strategy = signal_result.get("size", None)
                            size_metadata = signal_result.get("size_metadata", None)

                            # 실제 잔고 기반으로 주문 크기 계산
                            # ⚠️ 중요: buy/sell 시그널일 때만 잔고 조회 (API Rate Limit 방지)
                            logger.info(
                                f"🔍 Signal check - action:{signal_action}, size_from_strategy:{signal_size_from_strategy}, size_metadata:{size_metadata}"
                            )
                            if (
                                signal_action in {"buy", "sell"}
                                and signal_size_from_strategy is None
                                and size_metadata
                            ):
                                logger.info(
                                    f"💰 Starting balance query for user {user_id}"
                                )
                                try:
                                    # Bitget 계정 잔고 조회 (bitget_client는 이미 초기화된 ccxt 객체)
                                    balance = await bitget_client.fetch_balance(
                                        {"type": "swap"}
                                    )
                                    usdt_balance = balance.get("USDT", {})
                                    available_balance = float(
                                        usdt_balance.get("free", 0)
                                    )

                                    if available_balance > 0:
                                        # 전략 파라미터에서 비율 가져오기
                                        position_size_percent = size_metadata.get(
                                            "position_size_percent", 0.4
                                        )
                                        leverage = size_metadata.get("leverage", 10)

                                        # 주문 크기 계산 (USDT → BTC)
                                        position_value_usdt = (
                                            available_balance
                                            * position_size_percent
                                            * leverage
                                        )
                                        signal_size = (
                                            position_value_usdt / price
                                        )  # BTC 수량

                                        # 최소 주문 크기 확인 (Bitget: 0.001 BTC)
                                        if signal_size < 0.001:
                                            signal_size = 0.001
                                            logger.warning(
                                                f"⚠️ Calculated size {signal_size:.6f} too small, using minimum 0.001 BTC"
                                            )

                                        logger.info(
                                            f"✅ Calculated order size for user {user_id}: {signal_size:.6f} BTC "
                                            f"(balance: ${available_balance:.2f}, position: {position_size_percent * 100:.1f}%, leverage: {leverage}x)"
                                        )
                                    else:
                                        logger.warning(
                                            f"⚠️ No available balance for user {user_id}, using minimum size"
                                        )
                                        signal_size = 0.001  # 최소 크기
                                except Exception as e:
                                    logger.error(
                                        f"❌ Failed to calculate order size for user {user_id}: {e}"
                                    )
                                    signal_size = 0.001  # 에러 시 최소 크기
                            elif signal_size_from_strategy is not None:
                                signal_size = signal_size_from_strategy
                            else:
                                signal_size = 0.001  # 기본 최소 크기

                            logger.info(
                                f"Strategy signal for user {user_id}: {signal_action} (confidence: {signal_confidence:.2f}, reason: {signal_reason})"
                            )

                        except Exception as e:
                            logger.error(
                                f"Strategy execution error for user {user_id}: {e}",
                                exc_info=True,
                            )
                            await broadcast_to_user(
                                user_id,
                                {
                                    "event": "bot_status",
                                    "status": "warning",
                                    "message": f"STRATEGY_ERROR: {str(e)}",
                                },
                            )
                            signal_action = "hold"
                            signal_size = 0.01  # Bitget minimum: 0.01 BTC

                        # 포지션 청산 처리
                        if signal_action == "close" and current_position:
                            try:
                                # 포지션 반대 주문으로 청산
                                close_side = (
                                    OrderSide.SELL
                                    if current_position["side"] == "long"
                                    else OrderSide.BUY
                                )
                                logger.info(
                                    f"Closing position for user {user_id}: {current_position['side']}"
                                )

                                order_result = await bitget_client.place_market_order(
                                    symbol=symbol,
                                    side=close_side,
                                    size=current_position["size"],
                                    margin_coin="USDT",
                                    reduce_only=True,
                                )

                                # 포지션 초기화
                                current_position = None

                                await broadcast_to_user(
                                    user_id,
                                    {
                                        "event": "position_closed",
                                        "symbol": symbol,
                                        "reason": signal_reason,
                                        "orderId": order_result.get("data", {}).get(
                                            "orderId", ""
                                        ),
                                    },
                                )
                                logger.info(f"Position closed for user {user_id}")

                                # 📱 텔레그램 알림 전송 (청산)
                                try:
                                    notifier = get_telegram_notifier()
                                    if notifier.is_enabled():
                                        # 간단한 청산 알림 메시지 전송
                                        close_message = f"""🔔 <b>포지션 청산</b>

📈 심볼: {symbol}
📍 청산가: ${price:,.2f}
📝 사유: {signal_reason}

⏰ 시간: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC"""
                                        await notifier.send_message(close_message)
                                        logger.info(
                                            f"📱 Telegram: Position close notification sent for user {user_id}"
                                        )
                                except Exception as e:
                                    logger.warning(f"텔레그램 청산 알림 전송 실패: {e}")

                            except Exception as e:
                                logger.error(
                                    f"Position close error for user {user_id}: {e}",
                                    exc_info=True,
                                )
                                await broadcast_to_user(
                                    user_id,
                                    {
                                        "event": "bot_status",
                                        "status": "error",
                                        "message": f"CLOSE_ERROR: {str(e)}",
                                    },
                                )

                        # 새로운 포지션 진입
                        elif signal_action in {"buy", "sell"} and not current_position:
                            # 🚫 일일 손실 제한 체크
                            (
                                can_trade,
                                today_pnl,
                                daily_limit,
                            ) = await self.check_daily_loss_limit(session, user_id)

                            if not can_trade:
                                logger.warning(
                                    f"🚫 Trade BLOCKED for user {user_id}: Daily loss limit exceeded! "
                                    f"Today's PnL: ${today_pnl:.2f}, Limit: -${daily_limit:.2f}"
                                )
                                await broadcast_to_user(
                                    user_id,
                                    {
                                        "event": "risk_alert",
                                        "type": "daily_loss_limit",
                                        "message": f"일일 손실 한도 초과! 오늘 손익: ${today_pnl:.2f}, 한도: -${daily_limit:.2f}",
                                        "today_pnl": today_pnl,
                                        "daily_limit": daily_limit,
                                        "blocked_action": signal_action,
                                    },
                                )
                                # 거래를 건너뛰고 다음 시그널 대기
                                continue

                            # 🚫 최대 포지션 개수 체크
                            (
                                can_open_position,
                                current_positions,
                                max_positions,
                            ) = await self.check_max_positions(
                                session, user_id, bitget_client
                            )

                            if not can_open_position:
                                logger.warning(
                                    f"🚫 Trade BLOCKED for user {user_id}: Max positions reached! "
                                    f"Current: {current_positions}, Max: {max_positions}"
                                )
                                await broadcast_to_user(
                                    user_id,
                                    {
                                        "event": "risk_alert",
                                        "type": "max_positions",
                                        "message": f"최대 포지션 개수 도달! 현재: {current_positions}개, 한도: {max_positions}개",
                                        "current_positions": current_positions,
                                        "max_positions": max_positions,
                                        "blocked_action": signal_action,
                                    },
                                )
                                # 거래를 건너뛰고 다음 시그널 대기
                                continue

                            try:
                                # ⚠️ 레버리지 제한 체크 (거래는 진행하되 레버리지만 제한)
                                strategy_params = (
                                    json.loads(strategy.params)
                                    if strategy.params
                                    else {}
                                )
                                requested_leverage = strategy_params.get("leverage", 10)

                                (
                                    leverage_ok,
                                    allowed_leverage,
                                    max_leverage,
                                ) = await self.check_leverage_limit(
                                    session, user_id, requested_leverage
                                )

                                if not leverage_ok:
                                    logger.info(
                                        f"⚠️ User {user_id}: Leverage limited from {requested_leverage}x to {allowed_leverage}x"
                                    )
                                    # 레버리지는 거래소에서 설정하므로 로그만 남김

                                order_side = (
                                    OrderSide.BUY
                                    if signal_action == "buy"
                                    else OrderSide.SELL
                                )

                                # 최소 주문량 강제 적용 (심볼별) - 테스트 모드: 항상 최소 주문량 사용
                                min_order_sizes = {
                                    "BTCUSDT": 0.001,
                                    "ETHUSDT": 0.01,
                                }
                                min_order_size = min_order_sizes.get(symbol, 0.001)
                                # 테스트 모드: 계산된 크기와 관계없이 최소 주문량 사용
                                if signal_size != min_order_size:
                                    logger.warning(
                                        f"⚠️ TEST MODE: Using minimum order size {min_order_size} instead of {signal_size}"
                                    )
                                    signal_size = min_order_size

                                logger.info(
                                    f"Executing {signal_action} order for user {user_id} at {price} (size: {signal_size}, confidence: {signal_confidence:.2f})"
                                )

                                # 주문 전에 레버리지 설정 (Bitget 요구사항)
                                try:
                                    await bitget_client.set_leverage(
                                        symbol=symbol,
                                        leverage=allowed_leverage,
                                        margin_coin="USDT",
                                    )
                                    logger.info(
                                        f"Leverage set to {allowed_leverage}x for {symbol}"
                                    )
                                except Exception as lev_err:
                                    logger.warning(f"Failed to set leverage: {lev_err}")

                                # Bitget 시장가 주문 실행
                                order_result = await bitget_client.place_market_order(
                                    symbol=symbol,
                                    side=order_side,
                                    size=signal_size,  # 전략에서 제공한 수량 사용
                                    margin_coin="USDT",
                                    reduce_only=False,
                                )

                                # 포지션 추적 시작
                                current_position = {
                                    "side": "long"
                                    if signal_action == "buy"
                                    else "short",
                                    "entry_price": price,
                                    "size": signal_size,
                                    "symbol": symbol,
                                }

                                # 거래 기록 저장
                                await self._record_trade(
                                    session,
                                    user_id,
                                    symbol,
                                    signal_action,
                                    price,
                                    order_result,
                                    strategy.id,
                                )

                                # WebSocket으로 프론트엔드에 알림
                                await broadcast_to_user(
                                    user_id,
                                    {
                                        "event": "trade_filled",
                                        "symbol": symbol,
                                        "side": signal_action,
                                        "price": price,
                                        "size": signal_size,
                                        "confidence": signal_confidence,
                                        "reason": signal_reason,
                                        "orderId": order_result.get("data", {}).get(
                                            "orderId", ""
                                        ),
                                    },
                                )
                                logger.info(
                                    f"Bitget order executed successfully for user {user_id}: {order_result}"
                                )

                                # 📱 텔레그램 알림 전송 (진입)
                                try:
                                    notifier = get_telegram_notifier()
                                    if notifier.is_enabled():
                                        trade_info = TradeInfo(
                                            symbol=symbol,
                                            side="Long"
                                            if signal_action == "buy"
                                            else "Short",
                                            entry_price=price,
                                            quantity=signal_size,
                                            leverage=allowed_leverage,
                                            stop_loss=signal_result.get("stop_loss"),
                                            take_profit=signal_result.get(
                                                "take_profit"
                                            ),
                                        )
                                        await notifier.notify_new_trade(trade_info)
                                        logger.info(
                                            f"📱 Telegram: Trade entry notification sent for user {user_id}"
                                        )
                                except Exception as e:
                                    logger.warning(f"텔레그램 진입 알림 전송 실패: {e}")

                            except Exception as e:
                                logger.error(
                                    f"Order execution error for user {user_id}: {e}",
                                    exc_info=True,
                                )
                                await broadcast_to_user(
                                    user_id,
                                    {
                                        "event": "bot_status",
                                        "status": "warning",
                                        "message": f"ORDER_ERROR: {str(e)}",
                                    },
                                )
                                # 주문 실패해도 계속 진행

                        # 자산 기록 (에러 격리)
                        try:
                            await record_equity(session, user_id, value=price)
                        except Exception as e:
                            logger.error(
                                f"Failed to record equity for user {user_id}: {e}"
                            )
                            # 자산 기록 실패는 치명적이지 않으므로 계속 진행

                        # 가격 업데이트 브로드캐스트
                        try:
                            await broadcast_to_user(
                                user_id,
                                {
                                    "event": "price_update",
                                    "symbol": symbol,
                                    "price": price,
                                },
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to broadcast price update for user {user_id}: {e}"
                            )

                        # 연속 에러 카운터 리셋
                        consecutive_errors = 0

                        await asyncio.sleep(0.1)

                    except Exception as e:
                        consecutive_errors += 1
                        logger.error(
                            f"Error in bot loop for user {user_id} (consecutive: {consecutive_errors}/{max_consecutive_errors}): {e}",
                            exc_info=True,
                        )

                        if consecutive_errors >= max_consecutive_errors:
                            logger.critical(
                                f"Too many consecutive errors for user {user_id}. Stopping bot."
                            )
                            await broadcast_to_user(
                                user_id,
                                {
                                    "event": "bot_status",
                                    "status": "error",
                                    "message": "TOO_MANY_ERRORS",
                                },
                            )
                            break

                        await asyncio.sleep(1.0)  # 에러 발생 시 잠시 대기

        except asyncio.CancelledError:
            # 사용자가 의도적으로 봇을 중지한 경우에만 DB 상태를 False로 업데이트
            logger.info(f"Bot cancelled by user for user {user_id}")
            await broadcast_to_user(
                user_id, {"event": "bot_status", "status": "stopped"}
            )

            # CancelledError일 때만 DB를 False로 업데이트 (사용자 의도적 중지)
            try:
                async with session_factory() as cleanup_session:
                    result = await cleanup_session.execute(
                        select(BotStatus).where(BotStatus.user_id == user_id)
                    )
                    bot_status = result.scalars().first()
                    if bot_status and bot_status.is_running:
                        bot_status.is_running = False
                        await cleanup_session.commit()
                        logger.info(
                            f"Updated BotStatus to stopped for user {user_id} (user initiated)"
                        )
            except Exception as e:
                logger.error(f"Failed to update BotStatus for user {user_id}: {e}")

            raise  # CancelledError는 재발생시켜야 함

        except Exception as exc:
            # 에러로 인한 종료 - DB는 is_running=True 유지 (자동 재시작 가능하도록)
            logger.error(
                f"Fatal error in bot loop for user {user_id}: {exc}. "
                f"DB status will remain is_running=True for auto-restart on next status check.",
                exc_info=True,
            )
            await broadcast_to_user(
                user_id, {"event": "bot_status", "status": "error", "message": str(exc)}
            )

        finally:
            # 리소스 정리 (메모리의 tasks 딕셔너리만 정리, DB는 건드리지 않음)
            logger.info(
                f"Bot loop ended for user {user_id}. Cleaning up memory resources..."
            )
            if user_id in self.tasks:
                del self.tasks[user_id]
            # 주의: DB 상태는 여기서 업데이트하지 않음!
            # - 사용자가 stop_bot 호출 시: CancelledError 핸들러에서 DB 업데이트
            # - 에러로 종료 시: DB는 is_running=True 유지하여 새로고침 시 자동 재시작

    async def _get_user_strategy(self, session: AsyncSession, user_id: int) -> Strategy:
        """사용자의 bot_status에서 선택된 전략 가져오기"""
        from ..database.models import BotStatus

        # 1. bot_status에서 선택된 strategy_id 가져오기
        result = await session.execute(
            select(BotStatus).where(BotStatus.user_id == user_id)
        )
        bot_status = result.scalars().first()

        if not bot_status or not bot_status.strategy_id:
            raise ValueError(f"No strategy selected for user {user_id}")

        # 2. 선택된 전략 가져오기
        result = await session.execute(
            select(Strategy).where(Strategy.id == bot_status.strategy_id)
        )
        strategy = result.scalars().first()

        if not strategy:
            raise ValueError(f"Strategy {bot_status.strategy_id} not found")

        return strategy

    async def _record_trade(
        self,
        session: AsyncSession,
        user_id: int,
        symbol: str,
        side: str,
        price: float,
        res: dict,
        strategy_id: int | None = None,
    ):
        trade = Trade(
            user_id=user_id,
            symbol=symbol,
            side=side.upper(),
            qty=0.001,
            entry_price=Decimal(str(price)),
            exit_price=Decimal(str(price)),
            pnl=Decimal("0"),
            pnl_percent=0.0,
            strategy_id=strategy_id,
            leverage=5,
            exit_reason="signal_reverse",
        )
        session.add(trade)
        await session.commit()
        await session.refresh(trade)
