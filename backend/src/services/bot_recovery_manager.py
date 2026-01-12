"""
봇 복구 관리자 (Bot Recovery Manager)

관련 문서: docs/MULTI_BOT_03_IMPLEMENTATION.md

역할:
- 봇 에러 상태 추적 및 관리
- 자동 재시작 로직 (지수 백오프)
- 치명적 에러 감지 및 알림
- 복구 불가능한 상태 처리

사용 예시:
    from services.bot_recovery_manager import bot_recovery_manager

    # 에러 발생 시 기록
    should_retry = await bot_recovery_manager.record_error(
        bot_instance_id, error_type, error_message, session
    )

    # 복구 시도
    if should_retry:
        await bot_recovery_manager.schedule_recovery(bot_instance_id)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import BotInstance

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """에러 유형"""
    API_KEY_INVALID = "api_key_invalid"        # 복구 불가
    API_KEY_EXPIRED = "api_key_expired"        # 복구 불가
    INSUFFICIENT_BALANCE = "insufficient_balance"  # 일시적
    RATE_LIMIT = "rate_limit"                  # 일시적, 대기 후 재시도
    NETWORK_ERROR = "network_error"            # 일시적
    EXCHANGE_ERROR = "exchange_error"          # 일시적
    STRATEGY_ERROR = "strategy_error"          # 코드 문제, 복구 불가
    POSITION_ERROR = "position_error"          # 상태 확인 필요
    UNKNOWN = "unknown"                        # 분류 불가


class ErrorSeverity(str, Enum):
    """에러 심각도"""
    LOW = "low"          # 무시 가능
    MEDIUM = "medium"    # 재시도 가능
    HIGH = "high"        # 즉시 대응 필요
    CRITICAL = "critical"  # 봇 중지 필요


# 에러 유형별 설정
ERROR_CONFIG = {
    ErrorType.API_KEY_INVALID: {
        "severity": ErrorSeverity.CRITICAL,
        "recoverable": False,
        "max_retries": 0,
        "message": "API 키가 유효하지 않습니다. 설정을 확인하세요.",
    },
    ErrorType.API_KEY_EXPIRED: {
        "severity": ErrorSeverity.CRITICAL,
        "recoverable": False,
        "max_retries": 0,
        "message": "API 키가 만료되었습니다. 새 키를 등록하세요.",
    },
    ErrorType.INSUFFICIENT_BALANCE: {
        "severity": ErrorSeverity.MEDIUM,
        "recoverable": True,
        "max_retries": 3,
        "base_delay": 300,  # 5분
        "message": "잔고가 부족합니다.",
    },
    ErrorType.RATE_LIMIT: {
        "severity": ErrorSeverity.LOW,
        "recoverable": True,
        "max_retries": 10,
        "base_delay": 60,  # 1분
        "message": "API 요청 제한에 도달했습니다. 잠시 후 재시도합니다.",
    },
    ErrorType.NETWORK_ERROR: {
        "severity": ErrorSeverity.MEDIUM,
        "recoverable": True,
        "max_retries": 5,
        "base_delay": 30,  # 30초
        "message": "네트워크 오류가 발생했습니다.",
    },
    ErrorType.EXCHANGE_ERROR: {
        "severity": ErrorSeverity.MEDIUM,
        "recoverable": True,
        "max_retries": 3,
        "base_delay": 60,
        "message": "거래소 오류가 발생했습니다.",
    },
    ErrorType.STRATEGY_ERROR: {
        "severity": ErrorSeverity.HIGH,
        "recoverable": False,
        "max_retries": 0,
        "message": "전략 실행 중 오류가 발생했습니다.",
    },
    ErrorType.POSITION_ERROR: {
        "severity": ErrorSeverity.HIGH,
        "recoverable": True,
        "max_retries": 2,
        "base_delay": 10,
        "message": "포지션 처리 중 오류가 발생했습니다.",
    },
    ErrorType.UNKNOWN: {
        "severity": ErrorSeverity.MEDIUM,
        "recoverable": True,
        "max_retries": 3,
        "base_delay": 60,
        "message": "알 수 없는 오류가 발생했습니다.",
    },
}


class BotRecoveryManager:
    """
    봇 에러 복구 관리자

    주요 기능:
    1. 에러 유형 분류 및 기록
    2. 지수 백오프를 사용한 재시도
    3. 최대 재시도 횟수 관리
    4. 치명적 에러 시 봇 중지 및 알림
    """

    def __init__(self):
        # 봇별 에러 카운터: bot_instance_id -> {error_type: count}
        self._error_counts: Dict[int, Dict[str, int]] = {}

        # 봇별 마지막 에러 시간: bot_instance_id -> datetime
        self._last_error_time: Dict[int, datetime] = {}

        # 복구 예약된 봇: bot_instance_id -> Task
        self._recovery_tasks: Dict[int, asyncio.Task] = {}

        # 에러 카운터 리셋 시간 (이 시간 동안 에러 없으면 카운터 리셋)
        self.ERROR_RESET_PERIOD = timedelta(hours=1)

    def classify_error(self, error: Exception) -> ErrorType:
        """
        예외를 분류하여 에러 유형 반환

        Args:
            error: 발생한 예외

        Returns:
            ErrorType
        """
        error_str = str(error).lower()

        # API 키 관련
        if any(kw in error_str for kw in ["invalid api", "api key", "authentication", "unauthorized"]):
            if "expired" in error_str:
                return ErrorType.API_KEY_EXPIRED
            return ErrorType.API_KEY_INVALID

        # 잔고 관련
        if any(kw in error_str for kw in ["insufficient", "balance", "margin"]):
            return ErrorType.INSUFFICIENT_BALANCE

        # Rate Limit
        if any(kw in error_str for kw in ["rate limit", "too many", "429"]):
            return ErrorType.RATE_LIMIT

        # 네트워크
        if any(kw in error_str for kw in ["connection", "timeout", "network", "dns"]):
            return ErrorType.NETWORK_ERROR

        # 거래소
        if any(kw in error_str for kw in ["exchange", "bitget", "order"]):
            return ErrorType.EXCHANGE_ERROR

        # 전략
        if any(kw in error_str for kw in ["strategy", "signal", "indicator"]):
            return ErrorType.STRATEGY_ERROR

        # 포지션
        if any(kw in error_str for kw in ["position", "close", "open"]):
            return ErrorType.POSITION_ERROR

        return ErrorType.UNKNOWN

    async def record_error(
        self,
        bot_instance_id: int,
        error: Exception,
        session: AsyncSession,
        context: str = ""
    ) -> Tuple[bool, str]:
        """
        에러 기록 및 재시도 여부 결정

        Args:
            bot_instance_id: 봇 인스턴스 ID
            error: 발생한 예외
            session: DB 세션
            context: 에러 발생 컨텍스트

        Returns:
            (should_retry, message)
        """
        error_type = self.classify_error(error)
        config = ERROR_CONFIG[error_type]

        # 에러 카운터 업데이트
        if bot_instance_id not in self._error_counts:
            self._error_counts[bot_instance_id] = {}

        # 에러 리셋 체크 (오래된 에러 카운터 리셋)
        last_error = self._last_error_time.get(bot_instance_id)
        if last_error and datetime.utcnow() - last_error > self.ERROR_RESET_PERIOD:
            self._error_counts[bot_instance_id] = {}

        self._last_error_time[bot_instance_id] = datetime.utcnow()

        # 에러 카운트 증가
        current_count = self._error_counts[bot_instance_id].get(error_type.value, 0) + 1
        self._error_counts[bot_instance_id][error_type.value] = current_count

        # DB에 에러 기록
        await self._update_bot_error(session, bot_instance_id, error_type, str(error), context)

        # 재시도 가능 여부 판단
        if not config["recoverable"]:
            logger.error(
                f"Bot {bot_instance_id}: Non-recoverable error - {error_type.value}: {error}"
            )
            return False, config["message"]

        max_retries = config["max_retries"]
        if current_count > max_retries:
            logger.error(
                f"Bot {bot_instance_id}: Max retries ({max_retries}) exceeded for {error_type.value}"
            )
            return False, f"{config['message']} (최대 재시도 횟수 초과)"

        logger.warning(
            f"Bot {bot_instance_id}: Recoverable error ({current_count}/{max_retries}) - "
            f"{error_type.value}: {error}"
        )
        return True, config["message"]

    def get_retry_delay(self, bot_instance_id: int, error_type: ErrorType) -> int:
        """
        지수 백오프를 사용한 재시도 대기 시간 계산

        Args:
            bot_instance_id: 봇 인스턴스 ID
            error_type: 에러 유형

        Returns:
            대기 시간 (초)
        """
        config = ERROR_CONFIG[error_type]
        base_delay = config.get("base_delay", 60)

        # 에러 횟수에 따른 지수 백오프
        error_count = self._error_counts.get(bot_instance_id, {}).get(error_type.value, 1)
        delay = base_delay * (2 ** (error_count - 1))

        # 최대 대기 시간 제한 (30분)
        return min(delay, 1800)

    async def schedule_recovery(
        self,
        bot_instance_id: int,
        error_type: ErrorType,
        recovery_callback,
        *args,
        **kwargs
    ):
        """
        복구 예약 (지연 후 재시작)

        Args:
            bot_instance_id: 봇 인스턴스 ID
            error_type: 에러 유형
            recovery_callback: 복구 시 호출할 함수
            *args, **kwargs: 콜백 인자
        """
        # 기존 복구 태스크 취소
        if bot_instance_id in self._recovery_tasks:
            self._recovery_tasks[bot_instance_id].cancel()

        delay = self.get_retry_delay(bot_instance_id, error_type)
        logger.info(f"Bot {bot_instance_id}: Scheduling recovery in {delay}s")

        async def recovery_task():
            await asyncio.sleep(delay)
            try:
                await recovery_callback(*args, **kwargs)
                # 성공 시 에러 카운터 리셋
                self.reset_error_count(bot_instance_id, error_type)
            except Exception as e:
                logger.error(f"Bot {bot_instance_id}: Recovery failed: {e}")

        task = asyncio.create_task(recovery_task())
        self._recovery_tasks[bot_instance_id] = task

    def cancel_recovery(self, bot_instance_id: int):
        """복구 예약 취소"""
        if bot_instance_id in self._recovery_tasks:
            self._recovery_tasks[bot_instance_id].cancel()
            del self._recovery_tasks[bot_instance_id]
            logger.info(f"Bot {bot_instance_id}: Recovery cancelled")

    def reset_error_count(self, bot_instance_id: int, error_type: Optional[ErrorType] = None):
        """
        에러 카운터 리셋

        Args:
            bot_instance_id: 봇 인스턴스 ID
            error_type: 특정 에러 유형만 리셋 (None이면 전체)
        """
        if bot_instance_id in self._error_counts:
            if error_type:
                self._error_counts[bot_instance_id].pop(error_type.value, None)
            else:
                del self._error_counts[bot_instance_id]

    def get_error_status(self, bot_instance_id: int) -> dict:
        """봇의 에러 상태 반환"""
        return {
            "error_counts": self._error_counts.get(bot_instance_id, {}),
            "last_error_time": self._last_error_time.get(bot_instance_id),
            "has_recovery_scheduled": bot_instance_id in self._recovery_tasks,
        }

    async def _update_bot_error(
        self,
        session: AsyncSession,
        bot_instance_id: int,
        error_type: ErrorType,
        error_message: str,
        context: str
    ):
        """DB에 봇 에러 상태 업데이트"""
        try:
            result = await session.execute(
                select(BotInstance).where(BotInstance.id == bot_instance_id)
            )
            bot = result.scalar_one_or_none()
            if bot:
                error_info = f"[{error_type.value}] {error_message}"
                if context:
                    error_info = f"{context}: {error_info}"
                bot.last_error = error_info[:500]  # 최대 500자
                bot.updated_at = datetime.utcnow()
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to update bot error in DB: {e}")

    async def check_and_recover_bots(self, session_factory, bot_manager):
        """
        에러 상태의 봇들 점검 및 복구 시도 (주기적 실행)

        서버 시작 시 또는 주기적으로 호출하여 복구 가능한 봇들을 재시작
        """
        async with session_factory() as session:
            # is_running=True이지만 실제로 실행 중이지 않은 봇 찾기
            result = await session.execute(
                select(BotInstance).where(
                    BotInstance.is_running is True,
                    BotInstance.is_active is True
                )
            )
            bots = result.scalars().all()

            for bot in bots:
                if not bot_manager.is_instance_running(bot.id):
                    # 마지막 에러 확인
                    error_type = ErrorType.UNKNOWN
                    if bot.last_error:
                        # 에러 메시지에서 유형 추출
                        for et in ErrorType:
                            if et.value in bot.last_error.lower():
                                error_type = et
                                break

                    config = ERROR_CONFIG[error_type]
                    if config["recoverable"]:
                        logger.info(f"Bot {bot.id}: Attempting automatic recovery")
                        try:
                            await bot_manager.start_bot_instance(bot.id, bot.user_id)
                            self.reset_error_count(bot.id)
                            logger.info(f"Bot {bot.id}: Recovery successful")
                        except Exception as e:
                            logger.error(f"Bot {bot.id}: Recovery failed: {e}")
                    else:
                        # 복구 불가능한 에러면 is_running=False로 변경
                        logger.warning(
                            f"Bot {bot.id}: Non-recoverable error, marking as stopped"
                        )
                        bot.is_running = False
                        await session.commit()

    def clear_bot_state(self, bot_instance_id: int):
        """봇 관련 모든 상태 정리 (봇 삭제 시)"""
        self._error_counts.pop(bot_instance_id, None)
        self._last_error_time.pop(bot_instance_id, None)
        self.cancel_recovery(bot_instance_id)


# 싱글톤 인스턴스
bot_recovery_manager = BotRecoveryManager()
