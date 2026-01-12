import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.db import get_session
from ..database.models import BotStatus
from ..schemas.bot_schema import BotStartRequest, BotStatusResponse
from ..services.telegram import get_telegram_notifier
from ..services.telegram.types import BotConfig, PositionInfo
from ..services.trade_executor import InvalidApiKeyError, ensure_client
from ..utils.jwt_auth import get_current_user_id
from ..utils.resource_manager import resource_manager
from ..utils.structured_logging import get_logger
from ..workers.manager import BotManager

logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

router = APIRouter(prefix="/bot", tags=["bot"])


@router.post("/start", response_model=BotStatusResponse)
async def start_bot(
    payload: BotStartRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """봇 시작 (JWT 인증 필요, 사용자별 리소스 제한 적용)"""

    structured_logger.info(
        "bot_start_requested",
        f"Bot start requested for user {user_id}",
        user_id=user_id,
        strategy_id=payload.strategy_id,
    )

    # 리소스 제한 확인
    can_start, error_msg = resource_manager.can_start_bot(user_id)
    if not can_start:
        structured_logger.warning(
            "bot_start_rejected",
            "Bot start rejected due to resource limits",
            user_id=user_id,
            reason=error_msg,
        )
        raise HTTPException(status_code=429, detail=error_msg)

    try:
        await ensure_client(user_id, session)
    except InvalidApiKeyError as e:
        structured_logger.warning(
            "bot_start_invalid_api_key",
            "Bot start failed - invalid API key",
            user_id=user_id,
        )
        raise HTTPException(
            status_code=400,
            detail="API key not found. Please save your API keys in the settings first.",
        ) from e

    # app.state에서 bot_manager 가져오기
    manager: BotManager = request.app.state.bot_manager
    await manager.start_bot(user_id)
    await upsert_status(session, user_id, payload.strategy_id, True)

    # 리소스 매니저에 봇 시작 기록
    resource_manager.start_bot(user_id, f"bot_{user_id}")

    # 캐시 무효화 (봇 상태가 변경됨)
    from ..utils.cache_manager import cache_manager, make_cache_key

    cache_key = make_cache_key("bot_status", user_id)
    await cache_manager.delete(cache_key)
    logger.debug(f"Invalidated bot_status cache for user {user_id}")

    structured_logger.info(
        "bot_started",
        "Bot started successfully",
        user_id=user_id,
        strategy_id=payload.strategy_id,
    )

    # 텔레그램 알림 전송
    try:
        import json

        from sqlalchemy import select as sql_select

        from ..database.models import Strategy

        # 전략 정보 조회
        strategy_result = await session.execute(
            sql_select(Strategy).where(Strategy.id == payload.strategy_id)
        )
        strategy = strategy_result.scalars().first()

        # 전략 파라미터 파싱
        strategy_params = {}
        strategy_description = "전략 설명 없음"
        if strategy:
            strategy_description = strategy.description or strategy.name
            if strategy.params:
                try:
                    strategy_params = json.loads(strategy.params)
                except (json.JSONDecodeError, ValueError):
                    pass

        notifier = get_telegram_notifier()
        if notifier.is_enabled():
            config = BotConfig(
                exchange="BITGET",
                trade_amount=strategy_params.get("position_size_percent", 35.0),
                stop_loss_percent=strategy_params.get("stop_loss", 5.0),
                timeframe=strategy_params.get("timeframe", "1h"),
                strategy=f"{strategy.name if strategy else f'Strategy #{payload.strategy_id}'}",
                leverage=strategy_params.get("leverage", 10),
                margin_mode="isolated",
            )

            # 상세 메시지 생성 (마크다운 제거 - 텔레그램 API 에러 방지)
            detail_message = "\n\n📊 전략 상세정보\n"
            detail_message += "━━━━━━━━━━━━━━━━\n"
            detail_message += (
                f"{strategy_description[:200]}...\n\n"
                if len(strategy_description) > 200
                else f"{strategy_description}\n\n"
            )

            if strategy_params:
                detail_message += "⚙️ 설정값\n"
                detail_message += (
                    f"• 심볼: {strategy_params.get('symbol', 'BTCUSDT')}\n"
                )
                detail_message += (
                    f"• 타임프레임: {strategy_params.get('timeframe', '1h')}\n"
                )
                detail_message += (
                    f"• 레버리지: {strategy_params.get('leverage', 10)}x\n"
                )
                detail_message += f"• 포지션 크기: {strategy_params.get('position_size_percent', 35)}%\n"
                detail_message += f"• 손절: -{strategy_params.get('stop_loss_percent', strategy_params.get('stop_loss', 2.0))}%\n"
                detail_message += f"• 익절: +{strategy_params.get('take_profit_percent', strategy_params.get('take_profit', 4.0))}%\n"

                # RSI 설정 (있는 경우)
                if "rsi_period" in strategy_params:
                    detail_message += "\n📈 RSI 설정\n"
                    detail_message += (
                        f"• RSI 기간: {strategy_params.get('rsi_period', 14)}\n"
                    )
                    detail_message += (
                        f"• 과매도: {strategy_params.get('rsi_oversold', 30)} 이하\n"
                    )
                    detail_message += (
                        f"• 과매수: {strategy_params.get('rsi_overbought', 70)} 이상\n"
                    )

                # MACD 설정 (있는 경우)
                if "macd_fast" in strategy_params:
                    detail_message += "\n📉 MACD 설정\n"
                    detail_message += (
                        f"• Fast: {strategy_params.get('macd_fast', 12)}\n"
                    )
                    detail_message += (
                        f"• Slow: {strategy_params.get('macd_slow', 26)}\n"
                    )
                    detail_message += (
                        f"• Signal: {strategy_params.get('macd_signal', 9)}\n"
                    )

                # EMA 설정 (있는 경우)
                if "ema_fast" in strategy_params or "ema_short" in strategy_params:
                    detail_message += "\n🎯 EMA 설정\n"
                    detail_message += f"• 단기: {strategy_params.get('ema_short', strategy_params.get('ema_fast', 9))}\n"
                    detail_message += f"• 장기: {strategy_params.get('ema_long', strategy_params.get('ema_slow', 50))}\n"

                # 볼린저밴드 설정 (있는 경우)
                if "bb_period" in strategy_params:
                    detail_message += "\n📊 볼린저밴드 설정\n"
                    detail_message += (
                        f"• 기간: {strategy_params.get('bb_period', 20)}\n"
                    )
                    detail_message += (
                        f"• 표준편차: {strategy_params.get('bb_std_dev', 2.0)}\n"
                    )

            await notifier.notify_bot_start(config, additional_message=detail_message)
            logger.info(f"📱 Telegram: Bot start notification sent for user {user_id}")
    except Exception as e:
        logger.warning(f"텔레그램 알림 전송 실패: {e}")

    return BotStatusResponse(
        user_id=user_id, strategy_id=payload.strategy_id, is_running=True
    )


@router.post("/stop", response_model=BotStatusResponse)
async def stop_bot(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """봇 중지 및 전체 포지션 청산 (JWT 인증 필요)"""

    structured_logger.info(
        "bot_stop_requested", f"Bot stop requested for user {user_id}", user_id=user_id
    )

    # 현재 봇 상태 조회
    result = await session.execute(
        select(BotStatus).where(BotStatus.user_id == user_id)
    )
    status = result.scalars().first()
    strategy_id = status.strategy_id if status else None

    # 포지션 청산 로직 (CRITICAL: 금융 리스크 방지)
    closed_positions = []
    try:
        from ..database.models import ApiKey
        from ..services.bitget_rest import get_bitget_rest
        from ..utils.crypto_secrets import decrypt_secret

        # 사용자 API 키 조회
        api_key_result = await session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id)
        )
        api_key_obj = api_key_result.scalars().first()

        if api_key_obj:
            # API 키 복호화
            api_key = decrypt_secret(api_key_obj.encrypted_api_key)
            api_secret = decrypt_secret(api_key_obj.encrypted_secret_key)
            passphrase = (
                decrypt_secret(api_key_obj.encrypted_passphrase)
                if api_key_obj.encrypted_passphrase
                else ""
            )

            # Bitget REST 클라이언트 초기화
            bitget_client = get_bitget_rest(api_key, api_secret, passphrase)

            # 모든 열린 포지션 가져오기
            positions = await bitget_client.get_positions(product_type="USDT-FUTURES")

            # 각 포지션 청산
            from ..services.bitget_rest import OrderSide

            for position in positions:
                total_size = float(position.get("total", 0))
                if total_size > 0:  # 포지션이 열려 있는 경우
                    symbol = position["symbol"]
                    hold_side = position.get("holdSide", "long")  # 'long' or 'short'

                    logger.info(
                        f"📋 Attempting to close {hold_side} position for {symbol}: size={total_size}"
                    )

                    try:
                        # 포지션 반대 방향으로 시장가 주문 (reduce_only=True)
                        # Long 포지션 -> Sell로 청산
                        # Short 포지션 -> Buy로 청산
                        close_side = (
                            OrderSide.SELL if hold_side == "long" else OrderSide.BUY
                        )

                        close_result = await bitget_client.place_market_order(
                            symbol=symbol,
                            side=close_side,
                            size=total_size,
                            margin_coin="USDT",
                            reduce_only=True,  # 청산 전용
                        )

                        closed_positions.append(
                            {
                                "symbol": symbol,
                                "side": hold_side,
                                "size": total_size,
                                "result": close_result,
                            }
                        )

                        structured_logger.info(
                            "position_closed",
                            f"Closed {hold_side} position for {symbol}",
                            user_id=user_id,
                            symbol=symbol,
                            side=hold_side,
                            size=total_size,
                        )

                    except Exception as e:
                        structured_logger.error(
                            "position_close_failed",
                            f"Failed to close {hold_side} position for {symbol}",
                            user_id=user_id,
                            symbol=symbol,
                            side=hold_side,
                            size=total_size,
                            error=str(e),
                        )
                        # 개별 포지션 청산 실패해도 계속 진행
                        closed_positions.append(
                            {
                                "symbol": symbol,
                                "side": hold_side,
                                "size": total_size,
                                "error": str(e),
                            }
                        )

            structured_logger.info(
                "positions_closed",
                f"Force closed {len(closed_positions)} positions",
                user_id=user_id,
                positions_closed=len(closed_positions),
            )

    except Exception as e:
        structured_logger.error(
            "positions_close_failed",
            "Failed to close positions during bot stop",
            user_id=user_id,
            error=str(e),
        )
        # 포지션 청산 실패해도 봇은 중지 (사용자가 수동으로 청산 가능)

    # app.state에서 bot_manager 가져오기
    manager: BotManager = request.app.state.bot_manager
    await manager.stop_bot(user_id)
    await upsert_status(session, user_id, strategy_id or 0, False)

    # 리소스 매니저에 봇 중지 기록
    resource_manager.stop_bot(user_id, f"bot_{user_id}")

    # 캐시 무효화 (봇 상태, 잔고, 포지션이 변경됨)
    from ..utils.cache_manager import cache_manager, make_cache_key

    await cache_manager.delete(make_cache_key("bot_status", user_id))
    await cache_manager.delete(make_cache_key("balance", user_id))
    await cache_manager.delete(make_cache_key("positions", user_id))
    logger.debug(f"Invalidated caches for user {user_id} after bot stop")

    # 응답에 청산된 포지션 정보 포함
    message = (
        f"Bot stopped. Closed {len(closed_positions)} positions."
        if closed_positions
        else "Bot stopped."
    )

    structured_logger.info(
        "bot_stopped",
        "Bot stopped successfully",
        user_id=user_id,
        strategy_id=strategy_id,
        positions_closed=len(closed_positions),
    )

    # 텔레그램 알림 전송
    try:
        notifier = get_telegram_notifier()
        if notifier.is_enabled():
            # 미청산 포지션이 있으면 경고 알림
            if closed_positions:
                positions = [
                    PositionInfo(
                        symbol=p.get("symbol", "Unknown"),
                        direction="Long" if p.get("side") == "long" else "Short",
                        pnl_percent=0.0,
                        entry_price=0.0,
                        quantity=p.get("size", 0),
                    )
                    for p in closed_positions
                ]
                await notifier.notify_open_positions_warning(positions)

            await notifier.notify_bot_stop(reason="정상 종료")
            logger.info(f"📱 Telegram: Bot stop notification sent for user {user_id}")
    except Exception as e:
        logger.warning(f"텔레그램 알림 전송 실패: {e}")

    return BotStatusResponse(
        user_id=user_id, strategy_id=strategy_id, is_running=False, message=message
    )


async def _attempt_bot_restart(user_id, status, session, manager, cache_manager):
    """
    Helper function to attempt bot restart with tracking (Issue #5)

    Updates restart attempt counter and timestamp.
    Resets counter on success.
    """
    from datetime import datetime

    # Update restart tracking
    status.restart_attempts += 1
    status.last_restart_attempt = datetime.utcnow()
    await session.commit()

    logger.info(
        f"🔄 Attempting bot restart for user {user_id} "
        f"(attempt {status.restart_attempts}/3)"
    )

    try:
        # API 키 유효성 확인
        from ..services.trade_executor import InvalidApiKeyError, ensure_client
        try:
            await ensure_client(user_id, session)
        except InvalidApiKeyError:
            logger.warning(f"Cannot auto-restart bot for user {user_id}: Invalid API key")
            # API 키 없으면 DB를 False로 업데이트
            status.is_running = False
            await session.commit()
            await cache_manager.delete(f"bot_status:{user_id}")
            return False

        # 봇 재시작
        await manager.start_bot(user_id)
        logger.info(f"✅ Bot auto-restarted for user {user_id}")

        # 성공 시 카운터 리셋
        status.restart_attempts = 0
        await session.commit()

        # 캐시 무효화
        await cache_manager.delete(f"bot_status:{user_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to auto-restart bot for user {user_id}: {e}")
        return False


@router.get("/status")
async def bot_status(
    request: Request,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """봇 상태 조회 (강화 버전 - JWT 인증 필요) - 자동 복구 지원"""
    from datetime import datetime

    from ..services.exchange_service import ExchangeService
    from ..utils.cache_manager import cache_manager, make_cache_key
    from ..workers.manager import BotManager

    # 캐시 확인 (10초 TTL - 빠른 응답 위해)
    cache_key = make_cache_key("bot_status", user_id)
    cached_status = await cache_manager.get(cache_key)
    if cached_status is not None:
        logger.debug(f"Cache hit for bot_status user {user_id}")
        return cached_status

    try:
        # 기본 봇 상태 조회
        result = await session.execute(
            select(BotStatus).where(BotStatus.user_id == user_id)
        )
        status = result.scalars().first()

        # 실제 BotManager의 상태 확인 (중요!)
        manager: BotManager = request.app.state.bot_manager
        is_actually_running = manager.runner.is_running(user_id)

        # 데이터베이스와 실제 상태가 다른 경우 처리
        # 핵심 로직: DB=True but Memory=False → 봇 자동 재시작 (페이지 새로고침 대응)
        if status and status.is_running and not is_actually_running:
            logger.warning(
                f"🔄 Bot status mismatch for user {user_id}: DB=True, Actual=False. "
                f"Auto-restarting bot (strategy_id={status.strategy_id})..."
            )

            # 전략이 선택되어 있는 경우에만 자동 재시작
            if status.strategy_id:
                # Issue #5: Check restart limits to prevent infinite loops
                from datetime import datetime, timedelta

                # Check if too many restart attempts
                if status.restart_attempts >= 3:
                    logger.error(
                        f"❌ Max restart attempts (3) reached for user {user_id}. "
                        f"Stopping bot. User must manually restart or reset counter."
                    )
                    status.is_running = False
                    status.restart_attempts = 0  # Reset for next manual start
                    await session.commit()
                    await cache_manager.delete(cache_key)
                    is_actually_running = False

                # Check if restarted too recently (5 minute cooldown)
                elif status.last_restart_attempt:
                    time_since_last = datetime.utcnow() - status.last_restart_attempt
                    if time_since_last < timedelta(minutes=5):
                        logger.warning(
                            f"⏳ Skipping restart for user {user_id}: "
                            f"Last attempt was {time_since_last.seconds}s ago (cooldown: 5min)"
                        )
                        is_actually_running = False
                    else:
                        # Cooldown passed, try restart
                        await _attempt_bot_restart(user_id, status, session, manager, cache_manager)
                        is_actually_running = manager.is_bot_running(user_id)
                else:
                    # First restart attempt
                    await _attempt_bot_restart(user_id, status, session, manager, cache_manager)
                    is_actually_running = manager.is_bot_running(user_id)
            else:
                # 전략이 없으면 DB를 False로 업데이트
                logger.warning(f"No strategy selected for user {user_id}, marking bot as stopped")
                status.is_running = False
                await session.commit()
                await cache_manager.delete(cache_key)
                is_actually_running = False

        # DB=False but Memory=True (비정상 상태) → DB를 True로 동기화
        elif status and not status.is_running and is_actually_running:
            logger.warning(
                f"Bot status mismatch for user {user_id}: DB=False, Actual=True. Syncing DB to True."
            )
            status.is_running = True
            await session.commit()
            await cache_manager.delete(cache_key)

        # 실제 상태를 기준으로 반환
        is_running = is_actually_running
        strategy_id = status.strategy_id if status else None

        # 전략 정보 조회 (DB 조회만, 빠름)
        strategy_info = None
        if strategy_id:
            from ..database.models import Strategy

            strategy_result = await session.execute(
                select(Strategy).where(Strategy.id == strategy_id)
            )
            strategy = strategy_result.scalars().first()
            if strategy:
                # 최근 시그널 조회는 스킵 (성능 개선)
                latest_signal = None

                strategy_info = {
                    "name": strategy.name,
                    "status": "ACTIVE" if is_running else "INACTIVE",
                    "lastSignal": (
                        latest_signal.signal_type if latest_signal else None
                    ),
                    "lastSignalTime": (
                        latest_signal.timestamp.isoformat() if latest_signal else None
                    ),
                }

        # 거래소 연결 상태 및 잔고 조회 (캐싱 적용)
        connection_status = "DISCONNECTED"
        balance_info = None
        last_data_received = None

        # 잔고 캐시 확인 (별도 캐시, 60초 TTL)
        balance_cache_key = make_cache_key("balance", user_id)
        cached_balance = await cache_manager.get(balance_cache_key)

        if cached_balance is not None:
            # 캐시된 잔고 사용
            logger.debug(f"Cache hit for balance user {user_id}")
            connection_status = "CONNECTED"
            balance_info = cached_balance
            last_data_received = datetime.fromisoformat(cached_balance["updatedAt"].replace("Z", ""))
        else:
            # 캐시 미스: API 호출
            try:
                client, exchange_name = await ExchangeService.get_user_exchange_client(
                    session, user_id
                )

                # 잔고 조회로 연결 상태 확인
                balance = await client.fetch_balance()
                connection_status = "CONNECTED"
                last_data_received = datetime.utcnow()

                # USDT 잔고 정보
                usdt_balance = balance.get("USDT", {})
                total = float(usdt_balance.get("total", 0))
                free = float(usdt_balance.get("free", 0))
                used = float(usdt_balance.get("used", 0))

                balance_info = {
                    "total": total,
                    "free": free,
                    "used": used,
                    "updatedAt": last_data_received.isoformat() + "Z",
                }

                # 잔고 캐시 저장 (60초 TTL)
                await cache_manager.set(balance_cache_key, balance_info, ttl=60)
                logger.debug(f"Cached balance for user {user_id}")

            except Exception as e:
                logger.warning(f"[bot_status] Failed to fetch balance: {e}")
                connection_status = "DISCONNECTED"

        # 응답 구성 (하위 호환성을 위해 is_running, strategy_id 필드 추가)
        response = {
            "status": "RUNNING" if is_running else "STOPPED",
            "is_running": is_running,  # 프론트엔드 호환성
            "strategy_id": strategy_id,  # 프론트엔드 호환성
            "strategy": strategy_info,
            "connection": {
                "exchange": connection_status,
                "lastDataReceived": last_data_received.isoformat() + "Z"
                if last_data_received
                else None,
                "timeSinceLastUpdate": 0 if last_data_received else None,
            },
            "balance": balance_info,
        }

        # 캐시에 저장 (30초 TTL)
        await cache_manager.set(cache_key, response, ttl=30)
        logger.debug(f"Cached bot_status for user {user_id}")

        return response

    except Exception as e:
        logger.error(f"[bot_status] Error: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "is_running": False,  # 에러 시에는 중지 상태로 표시
            "strategy_id": None,
            "strategy": None,
            "connection": {
                "exchange": "DISCONNECTED",
                "lastDataReceived": None,
                "timeSinceLastUpdate": None,
            },
            "balance": None,
        }


async def upsert_status(
    session: AsyncSession, user_id: int, strategy_id: int, is_running: bool
):
    result = await session.execute(
        select(BotStatus).where(BotStatus.user_id == user_id)
    )
    status = result.scalars().first()
    if not status:
        status = BotStatus(
            user_id=user_id, strategy_id=strategy_id, is_running=is_running
        )
        session.add(status)
    else:
        status.is_running = is_running
        status.strategy_id = strategy_id
    await session.commit()


@router.post("/reset-restart-counter")
async def reset_restart_counter(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
):
    """
    봇 재시작 카운터 초기화 (Issue #5)

    문제 해결 후 사용자가 수동으로 재시작 카운터를 리셋할 수 있습니다.
    3회 재시도 제한에 도달한 후 문제를 해결했을 때 사용합니다.
    """
    result = await session.execute(
        select(BotStatus).where(BotStatus.user_id == user_id)
    )
    status = result.scalars().first()

    if not status:
        raise HTTPException(status_code=404, detail="봇 상태를 찾을 수 없습니다.")

    # 카운터 리셋
    old_attempts = status.restart_attempts
    status.restart_attempts = 0
    status.last_restart_attempt = None
    await session.commit()

    logger.info(
        f"Restart counter reset for user {user_id} "
        f"(was {old_attempts} attempts)"
    )

    return {
        "success": True,
        "message": "재시작 카운터가 초기화되었습니다.",
        "previous_attempts": old_attempts,
    }
