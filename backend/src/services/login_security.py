"""
로그인 보안 서비스 - Brute Force 공격 방지

기능:
- 로그인 실패 횟수 추적
- 일정 횟수 초과 시 계정 일시 잠금
- 잠금 시간 경과 후 자동 해제
- Redis 또는 In-Memory 캐시 지원 (Graceful Degradation)
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

from ..config import RateLimitConfig
from ..utils.cache_manager import cache_manager, make_cache_key

logger = logging.getLogger(__name__)


class LoginSecurityConfig:
    """로그인 보안 설정"""

    # 환경에 따른 설정 (개발 환경에서는 더 관대하게)
    IS_DEVELOPMENT = RateLimitConfig.IS_DEVELOPMENT

    # 최대 로그인 실패 허용 횟수
    MAX_FAILED_ATTEMPTS = 10 if IS_DEVELOPMENT else 5

    # 계정 잠금 시간 (초)
    LOCKOUT_DURATION_SECONDS = (
        60 if IS_DEVELOPMENT else 15 * 60
    )  # 개발: 1분, 프로덕션: 15분

    # 실패 기록 유지 시간 (초) - 이 시간이 지나면 실패 카운트 리셋
    FAILED_ATTEMPT_TTL_SECONDS = 60 * 60  # 1시간


class LoginSecurityService:
    """로그인 보안 서비스"""

    # 캐시 키 접두사
    KEY_PREFIX_FAILED = "login_fail"  # 실패 횟수: login_fail:{email}
    KEY_PREFIX_LOCKOUT = "login_lockout"  # 잠금 상태: login_lockout:{email}

    async def check_login_allowed(
        self, email: str
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        로그인 허용 여부 확인

        Args:
            email: 사용자 이메일

        Returns:
            Tuple[bool, Optional[str], Optional[int]]:
                - 로그인 허용 여부
                - 에러 메시지 (잠금된 경우)
                - 남은 잠금 시간 (초)
        """
        lockout_key = make_cache_key(self.KEY_PREFIX_LOCKOUT, email.lower())

        # 잠금 상태 확인
        lockout_data = await cache_manager.get(lockout_key)

        if lockout_data:
            remaining_seconds = lockout_data.get("remaining", 0)

            # 잠금 시간 계산
            if remaining_seconds > 0:
                remaining_minutes = remaining_seconds // 60
                if remaining_minutes > 0:
                    message = f"계정이 잠금되었습니다. {remaining_minutes}분 후에 다시 시도해주세요."
                else:
                    message = f"계정이 잠금되었습니다. {remaining_seconds}초 후에 다시 시도해주세요."

                logger.warning(
                    f"[LoginSecurity] Account locked: {email}, remaining: {remaining_seconds}s"
                )
                return False, message, remaining_seconds

        return True, None, None

    async def record_failed_attempt(self, email: str) -> Tuple[int, bool]:
        """
        로그인 실패 기록

        Args:
            email: 사용자 이메일

        Returns:
            Tuple[int, bool]: (현재 실패 횟수, 잠금 여부)
        """
        email_lower = email.lower()
        fail_key = make_cache_key(self.KEY_PREFIX_FAILED, email_lower)
        lockout_key = make_cache_key(self.KEY_PREFIX_LOCKOUT, email_lower)

        # 현재 실패 횟수 조회
        current_failures = await cache_manager.get(fail_key)
        failed_count = (current_failures or 0) + 1

        # 실패 횟수 저장
        await cache_manager.set(
            fail_key, failed_count, LoginSecurityConfig.FAILED_ATTEMPT_TTL_SECONDS
        )

        logger.info(
            f"[LoginSecurity] Failed attempt recorded: {email}, count: {failed_count}"
        )

        # 최대 실패 횟수 초과 시 잠금
        if failed_count >= LoginSecurityConfig.MAX_FAILED_ATTEMPTS:
            lockout_duration = LoginSecurityConfig.LOCKOUT_DURATION_SECONDS
            lockout_until = datetime.utcnow().timestamp() + lockout_duration

            await cache_manager.set(
                lockout_key,
                {
                    "remaining": lockout_duration,
                    "until": lockout_until,
                    "attempts": failed_count,
                },
                lockout_duration,
            )

            # 실패 카운트 리셋
            await cache_manager.delete(fail_key)

            logger.warning(
                f"[LoginSecurity] Account locked: {email}, "
                f"attempts: {failed_count}, duration: {lockout_duration}s"
            )

            return failed_count, True

        return failed_count, False

    async def record_successful_login(self, email: str) -> None:
        """
        로그인 성공 시 실패 기록 초기화

        Args:
            email: 사용자 이메일
        """
        email_lower = email.lower()
        fail_key = make_cache_key(self.KEY_PREFIX_FAILED, email_lower)
        lockout_key = make_cache_key(self.KEY_PREFIX_LOCKOUT, email_lower)

        # 실패 기록 삭제
        await cache_manager.delete(fail_key)
        # 잠금 해제 (있다면)
        await cache_manager.delete(lockout_key)

        logger.info(f"[LoginSecurity] Successful login, cleared records: {email}")

    async def get_failed_attempts(self, email: str) -> int:
        """
        현재 실패 횟수 조회

        Args:
            email: 사용자 이메일

        Returns:
            실패 횟수
        """
        fail_key = make_cache_key(self.KEY_PREFIX_FAILED, email.lower())
        count = await cache_manager.get(fail_key)
        return count or 0

    async def unlock_account(self, email: str) -> bool:
        """
        계정 잠금 해제 (관리자용)

        Args:
            email: 사용자 이메일

        Returns:
            성공 여부
        """
        email_lower = email.lower()
        fail_key = make_cache_key(self.KEY_PREFIX_FAILED, email_lower)
        lockout_key = make_cache_key(self.KEY_PREFIX_LOCKOUT, email_lower)

        await cache_manager.delete(fail_key)
        await cache_manager.delete(lockout_key)

        logger.info(f"[LoginSecurity] Account unlocked by admin: {email}")
        return True


# 전역 인스턴스
login_security = LoginSecurityService()
