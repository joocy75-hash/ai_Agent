"""
봇 실행기 (Bot Runner)

다중 봇 시스템 지원 버전
- 기존: user_id 기반 (1 user = 1 bot)
- 신규: bot_instance_id 기반 (1 user = N bots)

관련 문서: docs/MULTI_BOT_03_IMPLEMENTATION.md
관련 서비스: allocation_manager.py
"""

import asyncio
import logging
import json
from collections import deque
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Set

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import (
    BotStatus,
    BotInstance,  # 다중 봇 시스템 (NEW)
    BotType,      # 다중 봇 시스템 (NEW)
    Position,
    Strategy,
    Trade,
    TradeSource,  # 다중 봇 시스템 (NEW)
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
from ..services.allocation_manager import allocation_manager  # 다중 봇 시스템 (NEW)
from ..services.bot_isolation_manager import bot_isolation_manager  # 다중 봇 시스템 (NEW)
from ..services.bot_recovery_manager import bot_recovery_manager  # 다중 봇 시스템 (NEW)
from ..utils.crypto_secrets import decrypt_secret
from ..websockets.ws_server import broadcast_to_user
from ..services.telegram import (
    get_telegram_notifier,
    TradeResult,
    OrderFilledInfo,
    StopLossInfo,
    TakeProfitInfo,
    RiskAlertInfo,
)
from ..agents.signal_validator import SignalValidatorAgent, ValidationResult
from ..agents.risk_monitor import RiskMonitorAgent, RiskLevel
from ..agents.market_regime import MarketRegimeAgent, MarketRegime, RegimeType
from ..agents.base import AgentTask, TaskPriority, AgentState

logger = logging.getLogger(__name__)


class BotRunner:
    """
    봇 실행 관리자

    다중 봇 시스템 지원:
    - tasks: bot_instance_id → Task (기존: user_id → Task)
    - user_bots: user_id → Set[bot_instance_id] (사용자별 실행 중인 봇 추적)

    하위 호환성:
    - 기존 user_id 기반 API도 유지 (legacy BotStatus 테이블 사용)
    """

    def __init__(self, market_queue: asyncio.Queue):
        self.market_queue = market_queue

        # 기존: user_id 기반 (하위 호환성)
        self.tasks: Dict[int, asyncio.Task] = {}
        self._daily_loss_exceeded: Dict[int, bool] = {}  # 사용자별 일일 손실 초과 여부 캐시

        # 다중 봇 시스템: bot_instance_id 기반 (NEW)
        self.instance_tasks: Dict[int, asyncio.Task] = {}  # bot_instance_id → Task
        self.user_bots: Dict[int, Set[int]] = {}  # user_id → Set[bot_instance_id]

        # Market Regime Agent (Day 2) - 시장 환경 분석
        self.market_regime = MarketRegimeAgent(
            agent_id="market_regime_main",
            name="Main Market Regime Analyzer",
            config={
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "candle_limit": 200
            },
            bitget_client=None,  # 실행 시점에 설정
            candle_cache=None,   # 실행 시점에 설정
            redis_client=None    # Redis 연동 시 설정 필요
        )

        # Signal Validator Agent (Day 3)
        self.signal_validator = SignalValidatorAgent(
            agent_id="signal_validator_main",
            name="Main Signal Validator",
            redis_client=None  # Redis 연동 시 설정 필요
        )

        # Risk Monitor Agent (Day 4)
        self.risk_monitor = RiskMonitorAgent(
            agent_id="risk_monitor_main",
            name="Main Risk Monitor",
            config={
                "max_position_loss_percent": 5.0,  # 포지션 손실 5% 초과 시 청산
                "max_daily_loss": 1000.0,  # 일일 손실 $1000 초과 시 거래 중지
                "max_drawdown_percent": 10.0,  # 최대 낙폭 10%
                "liquidation_warning_percent": 10.0  # 청산가 10% 이내 접근 시 경고
            }
        )

        # 최근 신호 기록 (bot_instance_id → deque of signals)
        self._recent_signals: Dict[int, deque] = {}  # 최근 10개 신호 저장

        # 5분 캔들 가격 기록 (symbol → deque of prices)
        self._price_history: Dict[str, deque] = {}  # 최근 6개 캔들 (30분치)

        # 주기적 에이전트 태스크
        self._periodic_tasks: Dict[str, asyncio.Task] = {}  # 백그라운드 태스크 추적

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

    # ============================================================
    # 다중 봇 시스템 메서드 (NEW)
    # ============================================================

    def is_instance_running(self, bot_instance_id: int) -> bool:
        """봇 인스턴스가 실행 중인지 확인 (AI봇 + 그리드봇 모두 체크)"""
        # AI 봇 체크
        if bot_instance_id in self.instance_tasks and not self.instance_tasks[bot_instance_id].done():
            return True

        # 그리드 봇 체크 (초기화되었을 경우만)
        try:
            from ..services.grid_bot_runner import get_grid_bot_runner
            grid_runner = get_grid_bot_runner(self.market_queue)
            if grid_runner.is_running(bot_instance_id):
                return True
        except Exception:
            pass  # GridBotRunner가 아직 초기화되지 않은 경우

        return False

    def get_user_running_bots(self, user_id: int) -> Set[int]:
        """사용자의 실행 중인 봇 인스턴스 ID 목록 반환"""
        return self.user_bots.get(user_id, set()).copy()

    def get_running_instance_count(self, user_id: int) -> int:
        """사용자의 실행 중인 봇 인스턴스 수 반환"""
        return len(self.user_bots.get(user_id, set()))

    async def start_instance(
        self,
        session_factory,
        bot_instance_id: int,
        user_id: int
    ):
        """
        봇 인스턴스 시작 (다중 봇 시스템)

        Args:
            session_factory: DB 세션 팩토리
            bot_instance_id: 봇 인스턴스 ID
            user_id: 사용자 ID (user_bots 추적용)
        """
        if self.is_instance_running(bot_instance_id):
            logger.warning(f"Bot instance {bot_instance_id} is already running")
            return

        # 태스크 생성
        task = asyncio.create_task(
            self._run_instance_loop(session_factory, bot_instance_id, user_id)
        )
        self.instance_tasks[bot_instance_id] = task

        # 사용자별 봇 추적
        if user_id not in self.user_bots:
            self.user_bots[user_id] = set()
        self.user_bots[user_id].add(bot_instance_id)

        logger.info(
            f"Started bot instance {bot_instance_id} for user {user_id}. "
            f"User now has {len(self.user_bots[user_id])} running bot(s)"
        )

    def stop_instance(self, bot_instance_id: int, user_id: int):
        """
        봇 인스턴스 정지 (다중 봇 시스템)

        Args:
            bot_instance_id: 봇 인스턴스 ID
            user_id: 사용자 ID (user_bots 추적용)
        """
        stopped = False

        # 1. AI 봇 체크 (BotRunner.instance_tasks)
        if self.is_instance_running(bot_instance_id):
            logger.info(f"Stopping AI bot instance {bot_instance_id}")
            self.instance_tasks[bot_instance_id].cancel()
            stopped = True

        # 2. 그리드 봇 체크 (GridBotRunner.tasks)
        from ..services.grid_bot_runner import get_grid_bot_runner
        grid_runner = get_grid_bot_runner(self.market_queue)
        if grid_runner.is_running(bot_instance_id):
            logger.info(f"Stopping Grid bot instance {bot_instance_id}")
            grid_runner.stop(bot_instance_id)
            stopped = True

        if stopped:
            # user_bots에서 제거
            if user_id in self.user_bots:
                self.user_bots[user_id].discard(bot_instance_id)
                if not self.user_bots[user_id]:
                    del self.user_bots[user_id]
        else:
            logger.warning(f"Bot instance {bot_instance_id} is not running")

    async def stop_all_user_instances(self, user_id: int):
        """사용자의 모든 봇 인스턴스 정지"""
        bot_ids = self.get_user_running_bots(user_id)
        for bot_id in bot_ids:
            self.stop_instance(bot_id, user_id)
        logger.info(f"Stopped all {len(bot_ids)} bot instances for user {user_id}")

    async def _run_instance_loop(
        self,
        session_factory,
        bot_instance_id: int,
        user_id: int
    ):
        """
        봇 인스턴스 실행 루프 (다중 봇 시스템)

        기존 _run_loop와 유사하지만:
        - BotInstance 테이블에서 설정 로드
        - allocation_manager로 할당된 잔고 계산
        - 봇 인스턴스별 격리된 포지션 관리
        - BotType에 따라 AI봇/그리드봇 분기
        """
        logger.info(f"Starting bot instance loop: bot_id={bot_instance_id}, user_id={user_id}")

        # Market Regime Agent 시작 (한 번만)
        if self.market_regime.state != AgentState.RUNNING:
            try:
                # TODO: Bitget 클라이언트 설정 (bot loop에서)
                await self.market_regime.start()
                logger.info("✅ MarketRegime Agent started")
            except Exception as e:
                logger.error(f"Failed to start MarketRegime Agent: {e}")

        # Signal Validator Agent 시작 (한 번만)
        if self.signal_validator.state != AgentState.RUNNING:
            try:
                await self.signal_validator.start()
                logger.info("✅ SignalValidator Agent started")
            except Exception as e:
                logger.error(f"Failed to start SignalValidator Agent: {e}")

        # Risk Monitor Agent 시작 (한 번만)
        if self.risk_monitor.state != AgentState.RUNNING:
            try:
                await self.risk_monitor.start()
                logger.info("✅ RiskMonitor Agent started")
            except Exception as e:
                logger.error(f"Failed to start RiskMonitor Agent: {e}")

        # 주기적 에이전트 태스크 시작 (한 번만)
        await self._start_periodic_agents(bot_instance_id, user_id)

        try:
            async with session_factory() as session:
                # 1. 봇 인스턴스 설정 로드
                try:
                    bot_instance = await self._get_bot_instance(session, bot_instance_id, user_id)
                    logger.info(
                        f"Loaded bot instance '{bot_instance.name}' (ID: {bot_instance_id}), "
                        f"type: {bot_instance.bot_type}, symbol: {bot_instance.symbol}, "
                        f"allocation: {bot_instance.allocation_percent}%"
                    )

                    # 2. 봇 타입에 따라 분기
                    if bot_instance.bot_type == BotType.GRID:
                        # 그리드 봇은 GridBotRunner로 위임
                        logger.info(f"Delegating to GridBotRunner for bot {bot_instance_id}")
                        from ..services.grid_bot_runner import get_grid_bot_runner
                        grid_runner = get_grid_bot_runner(self.market_queue)
                        await grid_runner.start(session_factory, bot_instance_id, user_id)
                        return  # GridBotRunner가 자체 루프 관리
                except Exception as e:
                    logger.error(f"Failed to load bot instance {bot_instance_id}: {e}", exc_info=True)
                    await self._update_bot_instance_error(session, bot_instance_id, str(e))
                    return

                # 2. 전략 로드 (AI 봇인 경우)
                strategy = None
                if bot_instance.strategy_id:
                    try:
                        strategy = await self._get_strategy_by_id(session, bot_instance.strategy_id)
                        logger.info(f"Loaded strategy '{strategy.name}' for bot instance {bot_instance_id}")
                    except Exception as e:
                        logger.error(f"Failed to load strategy for bot instance {bot_instance_id}: {e}")
                        await self._update_bot_instance_error(session, bot_instance_id, f"STRATEGY_LOAD_ERROR: {e}")
                        return

                # 3. Bitget API 클라이언트 초기화
                try:
                    bitget_client = await self._init_bitget_client(session, user_id)
                    logger.info(f"Bitget API client initialized for bot instance {bot_instance_id}")
                except InvalidApiKeyError as e:
                    logger.error(f"Invalid API key for user {user_id}: {e}")
                    await self._update_bot_instance_error(session, bot_instance_id, "INVALID_API_KEY")
                    return
                except Exception as e:
                    logger.error(f"Failed to initialize Bitget client: {e}", exc_info=True)
                    await self._update_bot_instance_error(session, bot_instance_id, f"CLIENT_INIT_ERROR: {e}")
                    return

                # 4. AllocationManager에서 포지션 동기화
                await allocation_manager.sync_used_amounts_from_positions(
                    user_id, bot_instance_id, bitget_client, session
                )

                # 5. 캔들 버퍼 초기화
                candle_buffer = deque(maxlen=200)
                symbol = bot_instance.symbol  # 예: "BTCUSDT"

                try:
                    # 전략 파라미터에서 타임프레임 가져오기
                    strategy_params = json.loads(strategy.params) if strategy and strategy.params else {}
                    timeframe = strategy_params.get("timeframe", "1h")

                    historical = await bitget_client.get_historical_candles(
                        symbol=symbol, interval=timeframe, limit=200
                    )
                    for candle in historical:
                        candle_buffer.append({
                            "open": float(candle.get("open", 0)),
                            "high": float(candle.get("high", 0)),
                            "low": float(candle.get("low", 0)),
                            "close": float(candle.get("close", 0)),
                            "volume": float(candle.get("volume", 0)),
                            "time": candle.get("timestamp", 0),
                        })
                    logger.info(f"✅ Loaded {len(candle_buffer)} historical candles for bot {bot_instance_id}")
                except Exception as e:
                    logger.warning(f"Failed to load historical candles for bot {bot_instance_id}: {e}")

                # 6. 메인 트레이딩 루프
                consecutive_errors = 0
                max_consecutive_errors = 10
                current_position = None

                while True:
                    try:
                        # 마켓 데이터 수신
                        try:
                            market = await asyncio.wait_for(self.market_queue.get(), timeout=60.0)
                        except asyncio.TimeoutError:
                            logger.warning(f"No market data for 60s (bot {bot_instance_id})")
                            continue

                        price = float(market.get("price", 0))
                        market_symbol = market.get("symbol", "BTCUSDT")

                        # 심볼 필터링
                        normalized_market = market_symbol.replace("/", "").replace("-", "").upper()
                        normalized_bot = symbol.replace("/", "").replace("-", "").upper()

                        if normalized_market != normalized_bot:
                            continue  # 다른 심볼은 무시

                        if price <= 0:
                            continue

                        # 캔들 버퍼 업데이트
                        new_candle = {
                            "open": market.get("open", price),
                            "high": market.get("high", price),
                            "low": market.get("low", price),
                            "close": market.get("close", price),
                            "volume": market.get("volume", 0),
                            "time": market.get("time", 0),
                        }
                        candle_buffer.append(new_candle)
                        candles = list(candle_buffer)

                        # === Risk Monitor (Day 4) - 포지션 보유 시 실시간 리스크 체크 ===
                        if current_position:
                            try:
                                # 현재 포지션 데이터 구성
                                entry_price = current_position.get("entry_price", price)
                                position_size = current_position.get("size", 0)
                                position_side = current_position.get("side", "long")

                                # PnL 계산
                                if position_side == "long":
                                    unrealized_pnl = (price - entry_price) * position_size
                                    unrealized_pnl_percent = ((price - entry_price) / entry_price) * 100
                                else:  # short
                                    unrealized_pnl = (entry_price - price) * position_size
                                    unrealized_pnl_percent = ((entry_price - price) / entry_price) * 100

                                # 청산가 계산 (간단한 추정)
                                leverage = bot_instance.max_leverage
                                if position_side == "long":
                                    liquidation_price = entry_price * (1 - 0.9 / leverage)
                                else:
                                    liquidation_price = entry_price * (1 + 0.9 / leverage)

                                distance_to_liquidation = abs((price - liquidation_price) / price) * 100

                                # RiskMonitor에 포지션 제출
                                risk_task = AgentTask(
                                    task_id=f"risk_{bot_instance_id}_{datetime.utcnow().timestamp()}",
                                    task_type="monitor_position",
                                    priority=TaskPriority.HIGH,
                                    params={
                                        "position": {
                                            "symbol": symbol,
                                            "side": position_side,
                                            "size": position_size,
                                            "entry_price": entry_price,
                                            "current_price": price,
                                            "unrealized_pnl": unrealized_pnl,
                                            "unrealized_pnl_percent": unrealized_pnl_percent,
                                            "leverage": leverage,
                                            "liquidation_price": liquidation_price,
                                            "distance_to_liquidation": distance_to_liquidation
                                        },
                                        "bitget_client": bitget_client,
                                        "auto_execute": True  # 자동 조치 활성화
                                    },
                                    timeout=1.0
                                )

                                await self.risk_monitor.submit_task(risk_task)
                                await asyncio.sleep(0.05)  # 처리 대기

                                # 리스크 알림 확인
                                risk_alerts = risk_task.result
                                if risk_alerts:
                                    for alert in risk_alerts:
                                        if alert.is_critical():
                                            logger.error(
                                                f"🚨 CRITICAL RISK: {alert.message}\n"
                                                f"  Position: {symbol} {position_side}\n"
                                                f"  Action: {alert.recommended_action.value}"
                                            )
                                            # 치명적 리스크 시 포지션 강제 청산
                                            if alert.recommended_action.value in {"close_position", "emergency_shutdown"}:
                                                logger.warning(f"🛑 Force closing position due to critical risk")
                                                await self._close_instance_position(
                                                    session, bitget_client, bot_instance, user_id,
                                                    current_position, price, f"Risk alert: {alert.message}"
                                                )
                                                current_position = None
                                                continue
                                        else:
                                            logger.warning(
                                                f"⚠️ Risk Alert: {alert.message} "
                                                f"(Action: {alert.recommended_action.value})"
                                            )

                            except Exception as e:
                                logger.error(f"Risk monitoring error: {e}")

                        # 전략 실행
                        if strategy:
                            try:
                                signal_result = generate_signal_with_strategy(
                                    strategy_code=strategy.code,
                                    current_price=price,
                                    candles=candles,
                                    params_json=strategy.params,
                                    current_position=current_position,
                                )
                                signal_action = signal_result.get("action", "hold")
                                signal_confidence = signal_result.get("confidence", 0)
                                signal_reason = signal_result.get("reason", "")
                            except Exception as e:
                                logger.error(f"Strategy error for bot {bot_instance_id}: {e}")
                                signal_action = "hold"
                                signal_confidence = 0
                                signal_reason = ""
                        else:
                            signal_action = "hold"
                            signal_confidence = 0
                            signal_reason = "No strategy"

                        # === Signal Validator (Day 3) ===
                        if signal_action in {"buy", "sell", "close"} and signal_action != "hold":
                            # 1. 가격 변동률 계산 (최근 5분)
                            price_change_5min = self._calculate_price_change(symbol, price)

                            # 2. 현재 포지션 방향
                            current_position_side = None
                            if current_position:
                                current_position_side = current_position.side  # "long" or "short"

                            # 3. 최근 신호 목록
                            recent_signals = self._get_recent_signals(bot_instance_id)

                            # 4. 주문 금액 계산
                            leverage = bot_instance.max_leverage
                            available = await allocation_manager.get_available_balance(
                                user_id, bot_instance_id, bitget_client, session
                            )
                            position_value = available * 0.95
                            order_size_usd = position_value

                            # 5. Market Regime 조회 (Day 2)
                            market_regime_type = None
                            market_volatility = None
                            try:
                                # MarketRegimeAgent에서 현재 시장 환경 조회
                                regime_task = AgentTask(
                                    task_id=f"regime_{bot_instance_id}_{datetime.utcnow().timestamp()}",
                                    task_type="get_current_regime",
                                    priority=TaskPriority.HIGH,
                                    params={},
                                    timeout=0.5
                                )
                                await self.market_regime.submit_task(regime_task)
                                await asyncio.sleep(0.05)  # 조회 대기

                                regime = regime_task.result
                                if regime:
                                    market_regime_type = regime.regime_type.value  # "trending", "ranging", etc.
                                    market_volatility = regime.volatility_level  # "low", "medium", "high"
                                    logger.debug(
                                        f"📊 Market Regime: {market_regime_type}, "
                                        f"Volatility: {market_volatility}"
                                    )
                            except Exception as e:
                                logger.warning(f"Failed to get market regime: {e}")
                                # 실패 시 None으로 유지 (validation은 계속 진행)

                            # 6. SignalValidator 호출
                            try:
                                validation_task = AgentTask(
                                    task_id=f"validate_{bot_instance_id}_{datetime.utcnow().timestamp()}",
                                    task_type="validate_signal",
                                    priority=TaskPriority.HIGH,
                                    params={
                                        "signal_id": f"{bot_instance_id}_{datetime.utcnow().timestamp()}",
                                        "symbol": symbol,
                                        "action": signal_action,
                                        "confidence": signal_confidence,
                                        "current_price": price,
                                        "price_change_5min": price_change_5min,
                                        "current_position_side": current_position_side,
                                        "recent_signals": recent_signals,
                                        "order_size_usd": order_size_usd,
                                        "available_balance": available,
                                        "market_regime": market_regime_type,  # 🆕 Market Regime 정보 추가
                                        "market_volatility": market_volatility,  # 🆕 변동성 정보 추가
                                        "support_level": None,  # TODO: 지지선 계산
                                        "resistance_level": None,  # TODO: 저항선 계산
                                        "recent_trades_count": 0,  # TODO: 거래 빈도 체크
                                        "current_drawdown": 0.0,  # TODO: 낙폭 계산
                                    },
                                    timeout=1.0
                                )

                                await self.signal_validator.submit_task(validation_task)
                                await asyncio.sleep(0.1)  # 검증 완료 대기 (최대 1초)

                                # 검증 결과 확인
                                validation = validation_task.result
                                if validation:
                                    if validation.is_rejected():
                                        logger.warning(
                                            f"🚫 Signal REJECTED by validator: {symbol} {signal_action} "
                                            f"(confidence: {signal_confidence:.2f})\n"
                                            f"  Reasons: {', '.join(validation.warnings)}"
                                        )
                                        # 최근 신호 기록 (거부된 신호도 기록)
                                        self._record_signal(bot_instance_id, "rejected")
                                        continue  # 신호 거부 - 주문 실행하지 않음

                                    # WARNING (조건부 승인) - 포지션 축소 적용
                                    position_adjustment = validation.metadata.get("position_adjustment", 1.0)
                                    order_size_adjustment = validation.metadata.get("order_size_adjustment", order_size_usd)

                                    if position_adjustment < 1.0 or order_size_adjustment < order_size_usd:
                                        logger.info(
                                            f"⚠️ Signal APPROVED with adjustments: {symbol} {signal_action}\n"
                                            f"  Position: {position_adjustment*100:.0f}%"
                                            f"  Order size: ${order_size_usd:.2f} → ${order_size_adjustment:.2f}"
                                        )
                                        # 주문 금액 조정
                                        position_value = order_size_adjustment

                                    else:
                                        logger.info(
                                            f"✅ Signal APPROVED: {symbol} {signal_action} "
                                            f"(confidence: {signal_confidence:.2f}, score: {validation.confidence_score:.2f})"
                                        )

                                    # 최근 신호 기록
                                    self._record_signal(bot_instance_id, signal_action)

                                else:
                                    logger.error("Validation result is None - rejecting signal for safety")
                                    continue

                            except Exception as e:
                                logger.error(f"Signal validation error: {e} - REJECTING signal for safety")
                                continue

                        # 포지션 청산
                        if signal_action == "close" and current_position:
                            await self._close_instance_position(
                                session, bitget_client, bot_instance, user_id,
                                current_position, price, signal_reason
                            )
                            current_position = None

                        # 신규 포지션 진입
                        elif signal_action in {"buy", "sell"} and not current_position:
                            # 1. 포지션 격리 체크 (같은 봇이 이미 포지션 보유 중인지)
                            position_side = "long" if signal_action == "buy" else "short"
                            can_open, isolation_msg = await bot_isolation_manager.can_open_position(
                                user_id, bot_instance_id, symbol, position_side, session
                            )
                            if not can_open:
                                logger.warning(f"Bot {bot_instance_id}: Position blocked - {isolation_msg}")
                                continue

                            # 2. 할당된 잔고 확인
                            available = await allocation_manager.get_available_balance(
                                user_id, bot_instance_id, bitget_client, session
                            )

                            if available < 10:  # 최소 $10 필요
                                logger.warning(f"Bot {bot_instance_id}: Insufficient allocated balance (${available:.2f})")
                                continue

                            # 주문 크기 계산 (할당된 잔고 기반)
                            leverage = bot_instance.max_leverage
                            position_value = available * 0.95  # 95% 사용 (여유분 5%)
                            signal_size = (position_value * leverage) / price

                            # 최소 주문량 체크
                            min_sizes = {"BTCUSDT": 0.001, "ETHUSDT": 0.01}
                            min_size = min_sizes.get(symbol, 0.001)
                            if signal_size < min_size:
                                signal_size = min_size

                            # 3. AllocationManager에서 금액 예약
                            can_order, msg = await allocation_manager.request_order_amount(
                                user_id, bot_instance_id, position_value, bitget_client, session
                            )
                            if not can_order:
                                logger.warning(f"Bot {bot_instance_id}: Order rejected - {msg}")
                                continue

                            try:
                                # 레버리지 설정
                                await bitget_client.set_leverage(
                                    symbol=symbol, leverage=leverage, margin_coin="USDT"
                                )

                                # 주문 실행
                                order_side = OrderSide.BUY if signal_action == "buy" else OrderSide.SELL
                                order_result = await bitget_client.place_market_order(
                                    symbol=symbol,
                                    side=order_side,
                                    size=signal_size,
                                    margin_coin="USDT",
                                    reduce_only=False,
                                )

                                # 4. 포지션 격리 매니저에 등록
                                exchange_order_id = order_result.get("data", {}).get("orderId")
                                await bot_isolation_manager.register_position(
                                    user_id, bot_instance_id, symbol, position_side,
                                    signal_size, price, exchange_order_id, session
                                )

                                # 거래 기록 (bot_instance_id 포함)
                                trade_id = await self._record_instance_entry_trade(
                                    session, user_id, bot_instance_id, symbol,
                                    signal_action, price, signal_size, leverage,
                                    bot_instance.strategy_id
                                )

                                current_position = {
                                    "side": "long" if signal_action == "buy" else "short",
                                    "entry_price": price,
                                    "size": signal_size,
                                    "symbol": symbol,
                                    "trade_id": trade_id,
                                    "leverage": leverage,
                                    "position_value": position_value,
                                }

                                logger.info(
                                    f"✅ Bot {bot_instance_id}: Opened {signal_action} position "
                                    f"@ ${price:.2f}, size={signal_size:.6f}, leverage={leverage}x"
                                )

                                # 텔레그램 알림 (봇 이름 포함)
                                if bot_instance.telegram_notify:
                                    await self._send_instance_trade_notification(
                                        bot_instance, signal_action, symbol, price,
                                        signal_size, leverage, order_result
                                    )

                            except Exception as e:
                                # 주문 실패 시 예약 금액 해제
                                allocation_manager.release_order_amount(bot_instance_id, position_value)
                                logger.error(f"Order error for bot {bot_instance_id}: {e}", exc_info=True)

                        # 연속 에러 리셋
                        consecutive_errors = 0
                        await asyncio.sleep(0.1)

                    except Exception as e:
                        consecutive_errors += 1

                        # 복구 매니저로 에러 기록 및 재시도 여부 결정
                        should_retry, error_msg = await bot_recovery_manager.record_error(
                            bot_instance_id, e, session, context="trading_loop"
                        )

                        logger.error(
                            f"Error in bot {bot_instance_id} loop (consecutive: {consecutive_errors}): {e}",
                            exc_info=True
                        )

                        if not should_retry or consecutive_errors >= max_consecutive_errors:
                            logger.critical(f"Bot {bot_instance_id} stopping: {error_msg}")
                            await self._update_bot_instance_error(session, bot_instance_id, error_msg)
                            break

                        # 에러 유형에 따른 대기 시간
                        error_type = bot_recovery_manager.classify_error(e)
                        retry_delay = bot_recovery_manager.get_retry_delay(bot_instance_id, error_type)
                        await asyncio.sleep(min(retry_delay, 10))  # 루프 내에서는 최대 10초

        except asyncio.CancelledError:
            logger.info(f"Bot instance {bot_instance_id} cancelled by user")
            # 복구 매니저 상태 정리
            bot_recovery_manager.cancel_recovery(bot_instance_id)
            try:
                async with session_factory() as cleanup_session:
                    await self._update_bot_instance_stopped(cleanup_session, bot_instance_id)
            except Exception as e:
                logger.error(f"Failed to update bot instance status: {e}")
            raise

        except Exception as exc:
            logger.error(f"Fatal error in bot instance {bot_instance_id}: {exc}", exc_info=True)
            # 치명적 에러 기록
            try:
                async with session_factory() as error_session:
                    await bot_recovery_manager.record_error(
                        bot_instance_id, exc, error_session, context="fatal_error"
                    )
            except Exception:
                pass

        finally:
            # 리소스 정리
            if bot_instance_id in self.instance_tasks:
                del self.instance_tasks[bot_instance_id]
            if user_id in self.user_bots:
                self.user_bots[user_id].discard(bot_instance_id)
                if not self.user_bots[user_id]:
                    del self.user_bots[user_id]

            # AllocationManager 사용량 리셋
            allocation_manager.reset_bot_usage(bot_instance_id)

            # BotIsolationManager 캐시 정리
            bot_isolation_manager.clear_bot_cache(bot_instance_id, user_id)

            # BotRecoveryManager 에러 카운터 리셋 (정상 종료 시)
            bot_recovery_manager.reset_error_count(bot_instance_id)

            logger.info(f"Bot instance {bot_instance_id} loop ended. Resources cleaned up.")

    async def _get_bot_instance(
        self,
        session: AsyncSession,
        bot_instance_id: int,
        user_id: int
    ) -> BotInstance:
        """봇 인스턴스 조회"""
        result = await session.execute(
            select(BotInstance).where(
                and_(
                    BotInstance.id == bot_instance_id,
                    BotInstance.user_id == user_id,
                    BotInstance.is_active == True
                )
            )
        )
        bot_instance = result.scalar_one_or_none()
        if not bot_instance:
            raise ValueError(f"Bot instance {bot_instance_id} not found for user {user_id}")
        return bot_instance

    async def _get_strategy_by_id(self, session: AsyncSession, strategy_id: int) -> Strategy:
        """전략 ID로 조회"""
        result = await session.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        strategy = result.scalar_one_or_none()
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
        return strategy

    async def _init_bitget_client(self, session: AsyncSession, user_id: int):
        """Bitget API 클라이언트 초기화"""
        result = await session.execute(
            select(ApiKey).where(ApiKey.user_id == user_id)
        )
        api_key_obj = result.scalars().first()

        if not api_key_obj:
            raise InvalidApiKeyError("API key not found in database")

        api_key = decrypt_secret(api_key_obj.encrypted_api_key)
        api_secret = decrypt_secret(api_key_obj.encrypted_secret_key)
        passphrase = (
            decrypt_secret(api_key_obj.encrypted_passphrase)
            if api_key_obj.encrypted_passphrase
            else ""
        )

        if not all([api_key, api_secret, passphrase]):
            raise InvalidApiKeyError("Invalid or incomplete API credentials")

        return get_bitget_rest(api_key, api_secret, passphrase)

    async def _update_bot_instance_error(
        self,
        session: AsyncSession,
        bot_instance_id: int,
        error_msg: str
    ):
        """봇 인스턴스 에러 상태 업데이트"""
        try:
            result = await session.execute(
                select(BotInstance).where(BotInstance.id == bot_instance_id)
            )
            bot = result.scalar_one_or_none()
            if bot:
                bot.last_error = error_msg[:500]  # 최대 500자
                bot.is_running = False
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to update bot instance error: {e}")

    async def _update_bot_instance_stopped(
        self,
        session: AsyncSession,
        bot_instance_id: int
    ):
        """봇 인스턴스 정지 상태 업데이트"""
        try:
            result = await session.execute(
                select(BotInstance).where(BotInstance.id == bot_instance_id)
            )
            bot = result.scalar_one_or_none()
            if bot:
                bot.is_running = False
                bot.last_stopped_at = datetime.utcnow()
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to update bot instance stopped status: {e}")

    async def _record_instance_entry_trade(
        self,
        session: AsyncSession,
        user_id: int,
        bot_instance_id: int,
        symbol: str,
        side: str,
        entry_price: float,
        qty: float,
        leverage: int,
        strategy_id: Optional[int] = None,
    ) -> int:
        """
        봇 인스턴스 진입 거래 기록 (다중 봇 시스템)

        Returns:
            trade_id: 생성된 거래 ID
        """
        trade = Trade(
            user_id=user_id,
            bot_instance_id=bot_instance_id,  # 다중 봇 시스템 (NEW)
            trade_source=TradeSource.BOT_INSTANCE,  # 다중 봇 시스템 (NEW)
            symbol=symbol,
            side=side.upper(),
            qty=Decimal(str(qty)),
            entry_price=Decimal(str(entry_price)),
            exit_price=None,
            pnl=None,
            pnl_percent=None,
            strategy_id=strategy_id,
            leverage=leverage,
            exit_reason=None,
        )
        session.add(trade)
        await session.commit()
        await session.refresh(trade)

        logger.info(
            f"📝 Bot {bot_instance_id} trade entry: ID={trade.id}, {symbol} {side.upper()} "
            f"@ ${entry_price:.2f}, qty={qty}, leverage={leverage}x"
        )
        return trade.id

    async def _close_instance_position(
        self,
        session: AsyncSession,
        bitget_client,
        bot_instance: BotInstance,
        user_id: int,
        position: dict,
        exit_price: float,
        reason: str
    ):
        """봇 인스턴스 포지션 청산"""
        try:
            close_side = OrderSide.SELL if position["side"] == "long" else OrderSide.BUY

            await bitget_client.place_market_order(
                symbol=position["symbol"],
                side=close_side,
                size=position["size"],
                margin_coin="USDT",
                reduce_only=True,
            )

            # PnL 계산
            entry_price = position["entry_price"]
            leverage = position.get("leverage", 10)
            position_size = position["size"]

            if position["side"] == "long":
                pnl_usdt = (exit_price - entry_price) * position_size * leverage
                pnl_percent = ((exit_price - entry_price) / entry_price) * 100 * leverage
            else:
                pnl_usdt = (entry_price - exit_price) * position_size * leverage
                pnl_percent = ((entry_price - exit_price) / entry_price) * 100 * leverage

            # Trade 레코드 업데이트
            if position.get("trade_id"):
                exit_tag = self._generate_exit_tag(reason, pnl_percent)
                await self._update_trade_exit(
                    session, position["trade_id"], exit_price, pnl_usdt, pnl_percent, reason,
                    exit_tag=exit_tag
                )

            # BotInstance 통계 업데이트
            await self._update_bot_instance_stats(
                session, bot_instance.id, pnl_usdt, pnl_usdt > 0
            )

            # AllocationManager 금액 해제
            if "position_value" in position:
                allocation_manager.release_order_amount(bot_instance.id, position["position_value"])

            # BotIsolationManager에서 포지션 정리
            await bot_isolation_manager.close_position(
                user_id, bot_instance.id, position["symbol"], exit_price, pnl_usdt, session
            )

            logger.info(
                f"✅ Bot {bot_instance.id}: Closed position. PnL: ${pnl_usdt:.2f} ({pnl_percent:.2f}%)"
            )

            # 텔레그램 알림
            if bot_instance.telegram_notify:
                await self._send_instance_close_notification(
                    bot_instance, position, exit_price, pnl_usdt, pnl_percent, reason
                )

        except Exception as e:
            logger.error(f"Failed to close position for bot {bot_instance.id}: {e}", exc_info=True)

    async def _update_bot_instance_stats(
        self,
        session: AsyncSession,
        bot_instance_id: int,
        pnl: float,
        is_win: bool
    ):
        """봇 인스턴스 통계 업데이트"""
        try:
            result = await session.execute(
                select(BotInstance).where(BotInstance.id == bot_instance_id)
            )
            bot = result.scalar_one_or_none()
            if bot:
                bot.total_trades += 1
                if is_win:
                    bot.winning_trades += 1
                bot.total_pnl = float(bot.total_pnl or 0) + pnl
                bot.last_trade_at = datetime.utcnow()
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to update bot instance stats: {e}")

    async def _send_instance_trade_notification(
        self,
        bot_instance: BotInstance,
        action: str,
        symbol: str,
        price: float,
        size: float,
        leverage: int,
        order_result: dict
    ):
        """봇 인스턴스 거래 체결 알림"""
        try:
            notifier = get_telegram_notifier()
            if notifier.is_enabled():
                total_value = price * size * leverage
                order_id = order_result.get("data", {}).get("orderId", "N/A")

                order_filled_info = OrderFilledInfo(
                    symbol=symbol,
                    direction="Long" if action == "buy" else "Short",
                    order_type="시장가",
                    order_price=price,
                    filled_price=price,
                    quantity=size,
                    filled_quantity=size,
                    leverage=leverage,
                    total_value=total_value,
                    order_id=order_id,
                    status=f"체결 (Bot: {bot_instance.name})",
                )
                await notifier.notify_order_filled(order_filled_info)
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")

    async def _send_instance_close_notification(
        self,
        bot_instance: BotInstance,
        position: dict,
        exit_price: float,
        pnl_usdt: float,
        pnl_percent: float,
        reason: str
    ):
        """봇 인스턴스 청산 알림"""
        try:
            notifier = get_telegram_notifier()
            if notifier.is_enabled():
                trade_result = TradeResult(
                    symbol=position["symbol"],
                    direction="Long" if position["side"] == "long" else "Short",
                    entry_price=position["entry_price"],
                    exit_price=exit_price,
                    quantity=position["size"],
                    pnl_percent=pnl_percent,
                    pnl_usdt=pnl_usdt,
                    exit_reason=f"{reason} (Bot: {bot_instance.name})",
                    duration_minutes=0.0,
                )
                await notifier.notify_close_trade(trade_result)
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")

    async def _run_loop(self, session_factory, user_id: int):
        """
        봇 실행 메인 루프 (개선된 에러 핸들링)

        개선사항:
        - 상세한 에러 로깅
        - DB 세션 에러 처리
        - 전략 실행 에러 격리
        - 주문 실행 에러 격리
        - Graceful shutdown
        - 에이전트 시스템 통합 (MarketRegime, SignalValidator, RiskMonitor)
        """
        logger.info(f"Starting bot loop for user {user_id}")
        logger.info(f"🔍 [DEBUG] Reached agent startup section")

        # ===== Agent System 시작 (한 번만) =====
        try:
            # Market Regime Agent 시작
            logger.info(f"🔍 [DEBUG] MarketRegime Agent state: {self.market_regime.state}")
            market_needs_start = self.market_regime.state != AgentState.RUNNING
            logger.info(f"🔍 [DEBUG] MarketRegime needs start: {market_needs_start}")

            if market_needs_start:
                try:
                    logger.info(f"🔍 [DEBUG] Calling market_regime.start()...")
                    await self.market_regime.start()
                    logger.info("✅ MarketRegime Agent started (legacy bot)")
                except Exception as e:
                    logger.error(f"❌ Failed to start MarketRegime Agent: {e}", exc_info=True)
            else:
                logger.info(f"⏭️  MarketRegime Agent already running, skipping")

            # Signal Validator Agent 시작
            logger.info(f"🔍 [DEBUG] SignalValidator Agent state: {self.signal_validator.state}")
            validator_needs_start = self.signal_validator.state != AgentState.RUNNING
            logger.info(f"🔍 [DEBUG] SignalValidator needs start: {validator_needs_start}")

            if validator_needs_start:
                try:
                    logger.info(f"🔍 [DEBUG] Calling signal_validator.start()...")
                    await self.signal_validator.start()
                    logger.info("✅ SignalValidator Agent started (legacy bot)")
                except Exception as e:
                    logger.error(f"❌ Failed to start SignalValidator Agent: {e}", exc_info=True)
            else:
                logger.info(f"⏭️  SignalValidator Agent already running, skipping")

            # Risk Monitor Agent 시작
            logger.info(f"🔍 [DEBUG] RiskMonitor Agent state: {self.risk_monitor.state}")
            risk_needs_start = self.risk_monitor.state != AgentState.RUNNING
            logger.info(f"🔍 [DEBUG] RiskMonitor needs start: {risk_needs_start}")

            if risk_needs_start:
                try:
                    logger.info(f"🔍 [DEBUG] Calling risk_monitor.start()...")
                    await self.risk_monitor.start()
                    logger.info("✅ RiskMonitor Agent started (legacy bot)")
                except Exception as e:
                    logger.error(f"❌ Failed to start RiskMonitor Agent: {e}", exc_info=True)
            else:
                logger.info(f"⏭️  RiskMonitor Agent already running, skipping")

            # 주기적 에이전트 태스크 시작 (한 번만)
            # Note: Legacy bot은 user_id를 bot_instance_id로 사용
            pseudo_bot_id = user_id * 1000  # user 1 -> 1000, user 2 -> 2000
            logger.info(f"🔍 [DEBUG] Calling _start_periodic_agents(bot_id={pseudo_bot_id}, user_id={user_id})...")
            try:
                await self._start_periodic_agents(pseudo_bot_id, user_id)
                logger.info(f"✅ Periodic agents started")
            except Exception as e:
                logger.error(f"❌ Failed to start periodic agents: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"❌ Critical error in agent startup section: {e}", exc_info=True)
            # Continue with bot loop even if agents fail to start

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
                            signal_enter_tag = signal_result.get("enter_tag", None)  # 시그널 태그

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

                                # PnL 계산 및 거래 기록 업데이트
                                entry_price = current_position["entry_price"]
                                exit_price = price
                                position_size = current_position["size"]
                                leverage = current_position.get("leverage", 10)
                                trade_id = current_position.get("trade_id")

                                # PnL 계산 (Long: 청산가 - 진입가, Short: 진입가 - 청산가)
                                if current_position["side"] == "long":
                                    pnl_usdt = (exit_price - entry_price) * position_size * leverage
                                    pnl_percent = ((exit_price - entry_price) / entry_price) * 100 * leverage
                                else:  # short
                                    pnl_usdt = (entry_price - exit_price) * position_size * leverage
                                    pnl_percent = ((entry_price - exit_price) / entry_price) * 100 * leverage

                                logger.info(
                                    f"💰 PnL calculated for user {user_id}: "
                                    f"Entry: ${entry_price:.2f}, Exit: ${exit_price:.2f}, "
                                    f"PnL: ${pnl_usdt:.2f} ({pnl_percent:.2f}%)"
                                )

                                # Trade 레코드 업데이트
                                if trade_id:
                                    # exit_tag 생성 (청산 사유 기반)
                                    exit_tag = self._generate_exit_tag(signal_reason, pnl_percent)
                                    await self._update_trade_exit(
                                        session,
                                        trade_id,
                                        exit_price,
                                        pnl_usdt,
                                        pnl_percent,
                                        signal_reason,
                                        exit_tag=exit_tag,
                                    )

                                # 📱 텔레그램 알림 전송 (청산 유형별 상세 알림) - 포지션 초기화 전에 전송!
                                position_side = current_position["side"]
                                try:
                                    notifier = get_telegram_notifier()
                                    if notifier.is_enabled():
                                        direction = "Long" if position_side == "long" else "Short"

                                        # 청산 사유에 따라 다른 알림 유형 사용
                                        if "stop_loss" in signal_reason.lower() or "손절" in signal_reason:
                                            # 손절 알림
                                            stop_loss_info = StopLossInfo(
                                                symbol=symbol,
                                                direction=direction,
                                                entry_price=entry_price,
                                                stop_price=exit_price,
                                                exit_price=exit_price,
                                                quantity=position_size,
                                                leverage=leverage,
                                                pnl_usdt=pnl_usdt,
                                                pnl_percent=pnl_percent,
                                            )
                                            await notifier.notify_stop_loss(stop_loss_info)
                                            logger.info(f"📱 Telegram: Stop loss notification sent for user {user_id}")

                                        elif "take_profit" in signal_reason.lower() or "익절" in signal_reason or pnl_percent >= 1.0:
                                            # 익절 알림 (수익률 1% 이상도 익절로 처리)
                                            take_profit_info = TakeProfitInfo(
                                                symbol=symbol,
                                                direction=direction,
                                                entry_price=entry_price,
                                                target_price=exit_price,
                                                exit_price=exit_price,
                                                quantity=position_size,
                                                leverage=leverage,
                                                pnl_usdt=pnl_usdt,
                                                pnl_percent=pnl_percent,
                                            )
                                            await notifier.notify_take_profit(take_profit_info)
                                            logger.info(f"📱 Telegram: Take profit notification sent for user {user_id}")

                                        else:
                                            # 일반 청산 알림 (TradeResult 사용)
                                            trade_result = TradeResult(
                                                symbol=symbol,
                                                direction=direction,
                                                entry_price=entry_price,
                                                exit_price=exit_price,
                                                quantity=position_size,
                                                pnl_percent=pnl_percent,
                                                pnl_usdt=pnl_usdt,
                                                exit_reason=signal_reason,
                                                duration_minutes=0.0,
                                            )
                                            await notifier.notify_close_trade(trade_result)
                                            logger.info(f"📱 Telegram: Position close notification sent for user {user_id}")

                                except Exception as e:
                                    logger.warning(f"텔레그램 청산 알림 전송 실패: {e}")

                                # 포지션 초기화 (텔레그램 알림 전송 후!)
                                current_position = None

                                await broadcast_to_user(
                                    user_id,
                                    {
                                        "event": "position_closed",
                                        "symbol": symbol,
                                        "reason": signal_reason,
                                        "pnl": round(pnl_usdt, 2),
                                        "pnl_percent": round(pnl_percent, 2),
                                        "orderId": order_result.get("data", {}).get(
                                            "orderId", ""
                                        ),
                                    },
                                )
                                logger.info(f"Position closed for user {user_id}")

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

                                # 📱 텔레그램 리스크 경고 알림
                                try:
                                    notifier = get_telegram_notifier()
                                    if notifier.is_enabled():
                                        risk_alert = RiskAlertInfo(
                                            alert_type="daily_loss_limit",
                                            message="일일 손실 한도 초과로 거래가 차단되었습니다.",
                                            current_value=abs(today_pnl),
                                            limit_value=daily_limit,
                                            blocked_action=signal_action.upper(),
                                            symbol=symbol,
                                        )
                                        await notifier.notify_risk_alert(risk_alert)
                                        logger.info(f"📱 Telegram: Daily loss limit alert sent for user {user_id}")
                                except Exception as e:
                                    logger.warning(f"텔레그램 리스크 알림 전송 실패: {e}")

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

                                # 📱 텔레그램 리스크 경고 알림
                                try:
                                    notifier = get_telegram_notifier()
                                    if notifier.is_enabled():
                                        risk_alert = RiskAlertInfo(
                                            alert_type="max_positions",
                                            message="최대 포지션 개수 도달로 거래가 차단되었습니다.",
                                            current_value=float(current_positions),
                                            limit_value=float(max_positions),
                                            blocked_action=signal_action.upper(),
                                            symbol=symbol,
                                        )
                                        await notifier.notify_risk_alert(risk_alert)
                                        logger.info(f"📱 Telegram: Max positions alert sent for user {user_id}")
                                except Exception as e:
                                    logger.warning(f"텔레그램 리스크 알림 전송 실패: {e}")

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

                                # 포지션 추적 시작 + 거래 기록 저장
                                trade_id = await self._record_entry_trade(
                                    session,
                                    user_id,
                                    symbol,
                                    signal_action,
                                    price,
                                    signal_size,
                                    allowed_leverage,
                                    strategy.id,
                                    enter_tag=signal_enter_tag,  # 시그널 태그 저장
                                )

                                current_position = {
                                    "side": "long"
                                    if signal_action == "buy"
                                    else "short",
                                    "entry_price": price,
                                    "size": signal_size,
                                    "symbol": symbol,
                                    "trade_id": trade_id,  # 청산 시 업데이트를 위해 저장
                                    "leverage": allowed_leverage,
                                }

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

                                # 📱 텔레그램 알림 전송 (체결)
                                try:
                                    notifier = get_telegram_notifier()
                                    if notifier.is_enabled():
                                        total_value = price * signal_size * allowed_leverage
                                        order_id = order_result.get("data", {}).get("orderId", "N/A")

                                        # OrderFilledInfo로 상세 체결 알림
                                        order_filled_info = OrderFilledInfo(
                                            symbol=symbol,
                                            direction="Long" if signal_action == "buy" else "Short",
                                            order_type="시장가",
                                            order_price=price,
                                            filled_price=price,
                                            quantity=signal_size,
                                            filled_quantity=signal_size,
                                            leverage=allowed_leverage,
                                            total_value=total_value,
                                            order_id=order_id,
                                            status="완전 체결",
                                        )
                                        await notifier.notify_order_filled(order_filled_info)
                                        logger.info(
                                            f"📱 Telegram: Order filled notification sent for user {user_id}"
                                        )
                                except Exception as e:
                                    logger.warning(f"텔레그램 체결 알림 전송 실패: {e}")

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

    async def _record_entry_trade(
        self,
        session: AsyncSession,
        user_id: int,
        symbol: str,
        side: str,
        entry_price: float,
        qty: float,
        leverage: int,
        strategy_id: int | None = None,
        enter_tag: str | None = None,
        order_tag: str | None = None,
    ) -> int:
        """
        진입 시 거래 기록 생성 (청산 전 상태)

        Args:
            enter_tag: 진입 시그널 태그 (예: "rsi_oversold", "ema_cross")
            order_tag: 주문 태그 (예: "main_entry", "dca_1")

        Returns:
            trade_id: 생성된 거래 ID (청산 시 업데이트용)
        """
        trade = Trade(
            user_id=user_id,
            symbol=symbol,
            side=side.upper(),
            qty=Decimal(str(qty)),
            entry_price=Decimal(str(entry_price)),
            exit_price=None,  # 아직 청산 안됨
            pnl=None,  # 아직 계산 안됨
            pnl_percent=None,
            strategy_id=strategy_id,
            leverage=leverage,
            exit_reason=None,  # 아직 청산 안됨
            enter_tag=enter_tag,  # 시그널 태그 (차트 마커용)
            order_tag=order_tag,  # 주문 태그
        )
        session.add(trade)
        await session.commit()
        await session.refresh(trade)

        logger.info(
            f"📝 Trade entry recorded: ID={trade.id}, {symbol} {side.upper()} "
            f"@ ${entry_price:.2f}, qty={qty}, leverage={leverage}x, tag={enter_tag}"
        )
        return trade.id

    async def _update_trade_exit(
        self,
        session: AsyncSession,
        trade_id: int,
        exit_price: float,
        pnl: float,
        pnl_percent: float,
        exit_reason: str,
        exit_tag: str | None = None,
    ):
        """
        청산 시 거래 기록 업데이트

        Args:
            exit_tag: 청산 시그널 태그 (예: "tp_hit", "sl_triggered", "signal_reverse")
        """
        try:
            result = await session.execute(
                select(Trade).where(Trade.id == trade_id)
            )
            trade = result.scalars().first()

            if trade:
                trade.exit_price = Decimal(str(exit_price))
                trade.pnl = Decimal(str(round(pnl, 8)))
                trade.pnl_percent = round(pnl_percent, 2)
                trade.exit_reason = exit_reason
                trade.exit_tag = exit_tag  # 청산 시그널 태그 (차트 마커용)
                await session.commit()

                logger.info(
                    f"📝 Trade exit updated: ID={trade_id}, "
                    f"Exit @ ${exit_price:.2f}, PnL: ${pnl:.2f} ({pnl_percent:.2f}%), tag={exit_tag}"
                )
            else:
                logger.warning(f"Trade {trade_id} not found for exit update")

        except Exception as e:
            logger.error(f"Failed to update trade exit: {e}", exc_info=True)

    def _generate_exit_tag(self, exit_reason: str, pnl_percent: float) -> str:
        """
        청산 사유와 PnL을 기반으로 exit_tag 생성

        Args:
            exit_reason: 청산 사유 문자열
            pnl_percent: 수익률 (%)

        Returns:
            exit_tag: 차트 마커용 청산 태그
        """
        reason_lower = exit_reason.lower() if exit_reason else ""

        # 손절 관련
        if "stop_loss" in reason_lower or "sl" in reason_lower or "손절" in reason_lower:
            return "sl_triggered"

        # 익절 관련
        if "take_profit" in reason_lower or "tp" in reason_lower or "익절" in reason_lower:
            return "tp_hit"

        # 청산가 관련
        if "liquidation" in reason_lower or "청산" in reason_lower:
            return "liquidation"

        # 시그널 반전
        if "signal" in reason_lower or "reverse" in reason_lower:
            return "signal_reverse"

        # PnL 기반 태그
        if pnl_percent >= 1.0:
            return "profit_exit"
        elif pnl_percent <= -1.0:
            return "loss_exit"

        # 기본값
        return "manual_close"

    # === Signal Validator Helper Methods (Day 3) ===

    def _calculate_price_change(self, symbol: str, current_price: float) -> float:
        """
        최근 5분간 가격 변동률 계산

        Args:
            symbol: 심볼
            current_price: 현재 가격

        Returns:
            가격 변동률 (%)
        """
        # 가격 히스토리 초기화
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=6)  # 5분 = 6개 캔들 (5분 간격)

        # 현재 가격 추가
        self._price_history[symbol].append(current_price)

        # 최소 2개 가격이 필요
        if len(self._price_history[symbol]) < 2:
            return 0.0

        # 5분 전 가격 (가장 오래된 가격)
        old_price = self._price_history[symbol][0]

        # 변동률 계산
        if old_price > 0:
            change_percent = (current_price - old_price) / old_price * 100
            return change_percent

        return 0.0

    def _get_recent_signals(self, bot_instance_id: int) -> list:
        """
        최근 신호 목록 조회

        Args:
            bot_instance_id: 봇 인스턴스 ID

        Returns:
            최근 신호 목록 (최신순, 최대 10개)
        """
        if bot_instance_id not in self._recent_signals:
            self._recent_signals[bot_instance_id] = deque(maxlen=10)

        return list(self._recent_signals[bot_instance_id])

    def _record_signal(self, bot_instance_id: int, signal_action: str):
        """
        신호 기록

        Args:
            bot_instance_id: 봇 인스턴스 ID
            signal_action: 신호 액션 (buy/sell/close/rejected)
        """
        if bot_instance_id not in self._recent_signals:
            self._recent_signals[bot_instance_id] = deque(maxlen=10)

        self._recent_signals[bot_instance_id].append(signal_action)

    # === Periodic Agent Tasks (주기적 에이전트 실행) ===

    async def _start_periodic_agents(self, bot_instance_id: int, user_id: int):
        """
        주기적 에이전트 태스크 시작

        - MarketRegimeAgent: 1분마다 시장 환경 분석
        - RiskMonitorAgent: 30초마다 리스크 체크

        각 태스크는 봇이 실행 중일 때만 동작하고, 봇 종료 시 자동으로 정지됩니다.
        """
        # 이미 실행 중이면 중복 시작 방지
        if "market_regime_periodic" in self._periodic_tasks:
            logger.debug("Periodic agents already running")
            return

        # MarketRegime 주기적 실행 (1분마다)
        market_task = asyncio.create_task(
            self._periodic_market_regime_analysis(bot_instance_id)
        )
        self._periodic_tasks["market_regime_periodic"] = market_task
        logger.info("🔄 Started periodic MarketRegime analysis (every 1min)")

        # RiskMonitor 주기적 실행 (30초마다)
        risk_task = asyncio.create_task(
            self._periodic_risk_monitoring(bot_instance_id, user_id)
        )
        self._periodic_tasks["risk_monitor_periodic"] = risk_task
        logger.info("🔄 Started periodic RiskMonitor checks (every 30sec)")

    async def _periodic_market_regime_analysis(self, bot_instance_id: int):
        """
        MarketRegimeAgent 주기적 실행 (1분마다)

        시장 환경을 분석하여 Redis에 저장합니다.
        다른 컴포넌트(SignalValidator 등)에서 참조 가능합니다.
        """
        while bot_instance_id in self.instance_tasks:
            try:
                # 시장 환경 분석 태스크 생성
                regime_task = AgentTask(
                    task_id=f"periodic_regime_{datetime.utcnow().timestamp()}",
                    task_type="analyze_market",
                    priority=TaskPriority.NORMAL,
                    params={
                        "symbol": "BTCUSDT",  # TODO: 봇별 심볼 가져오기
                        "timeframe": "1h"
                    },
                    timeout=5.0
                )

                # 에이전트에 태스크 제출
                await self.market_regime.submit_task(regime_task)
                await asyncio.sleep(0.1)  # 처리 대기

                # 결과 로깅
                if regime_task.result:
                    regime = regime_task.result
                    logger.debug(
                        f"📊 Periodic Market Analysis: "
                        f"regime={regime.regime_type.value}, "
                        f"volatility={regime.volatility_level}"
                    )

            except Exception as e:
                logger.error(f"Periodic market regime analysis error: {e}")

            # 1분 대기
            await asyncio.sleep(60)

        logger.info("Periodic MarketRegime analysis stopped (bot stopped)")

    async def _periodic_risk_monitoring(self, bot_instance_id: int, user_id: int):
        """
        RiskMonitorAgent 주기적 실행 (30초마다)

        계좌 리스크를 지속적으로 감시합니다:
        - 일일 손익 체크
        - 포지션 크기 체크
        - 연속 손실 체크
        - 청산가 접근 경고
        """
        while bot_instance_id in self.instance_tasks:
            try:
                # TODO: 실제 계좌 데이터 수집
                # 현재는 placeholder로 동작

                risk_task = AgentTask(
                    task_id=f"periodic_risk_{datetime.utcnow().timestamp()}",
                    task_type="check_risk",
                    priority=TaskPriority.HIGH,
                    params={
                        "user_id": user_id,
                        "bot_instance_id": bot_instance_id,
                        "daily_pnl": 0.0,  # TODO: DB에서 조회
                        "position_size": 0.0,  # TODO: 거래소에서 조회
                        "consecutive_losses": 0,  # TODO: DB에서 조회
                        "auto_execute": False  # 조회만 (조치 안 함)
                    },
                    timeout=2.0
                )

                # 에이전트에 태스크 제출
                await self.risk_monitor.submit_task(risk_task)
                await asyncio.sleep(0.1)  # 처리 대기

                # 결과 확인 (경고가 있으면 로깅)
                if risk_task.result:
                    alerts = risk_task.result
                    if alerts:
                        for alert in alerts:
                            logger.warning(
                                f"⚠️ Periodic Risk Alert: {alert.severity.value} - {alert.message}"
                            )

            except Exception as e:
                logger.error(f"Periodic risk monitoring error: {e}")

            # 30초 대기
            await asyncio.sleep(30)

        logger.info("Periodic RiskMonitor checks stopped (bot stopped)")
