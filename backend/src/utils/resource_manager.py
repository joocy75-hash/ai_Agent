"""
사용자별 리소스 관리

실사용자 20명 규모에 맞춘 리소스 제한 및 격리.
"""
from collections import defaultdict
from typing import Dict, Optional
import asyncio


class UserResourceManager:
    """
    사용자별 리소스 사용 제한 관리.

    제한 항목:
    - 동시 실행 백테스트 수
    - 동시 실행 봇 수
    - 사용한 총 백테스트 수 (일일)
    """

    def __init__(self):
        # 사용자별 활성 백테스트 추적
        self.active_backtests: Dict[int, set] = defaultdict(set)

        # 사용자별 활성 봇 추적
        self.active_bots: Dict[int, set] = defaultdict(set)

        # 사용자별 일일 백테스트 카운트
        self.daily_backtest_count: Dict[int, int] = defaultdict(int)

        # 제한 설정 (실사용자 20명 기준)
        self.limits = {
            "max_concurrent_backtests_per_user": 2,  # 사용자당 동시 2개
            "max_concurrent_bots_per_user": 3,        # 사용자당 봇 3개
            "max_daily_backtests_per_user": 50,      # 일일 50회
            "max_total_concurrent_backtests": 20,    # 전체 20개 (20명 × 평균 1개)
        }

    def can_start_backtest(self, user_id: int) -> tuple[bool, Optional[str]]:
        """
        백테스트 시작 가능 여부 확인.

        Returns:
            (가능여부, 에러 메시지)
        """
        # 사용자별 동시 백테스트 제한
        if len(self.active_backtests[user_id]) >= self.limits["max_concurrent_backtests_per_user"]:
            return False, f"Max concurrent backtests per user: {self.limits['max_concurrent_backtests_per_user']}"

        # 전체 동시 백테스트 제한
        total_active = sum(len(backtests) for backtests in self.active_backtests.values())
        if total_active >= self.limits["max_total_concurrent_backtests"]:
            return False, f"System at capacity. Max concurrent backtests: {self.limits['max_total_concurrent_backtests']}"

        # 일일 백테스트 제한
        if self.daily_backtest_count[user_id] >= self.limits["max_daily_backtests_per_user"]:
            return False, f"Daily backtest limit reached: {self.limits['max_daily_backtests_per_user']}"

        return True, None

    def start_backtest(self, user_id: int, backtest_id: int):
        """백테스트 시작 기록"""
        self.active_backtests[user_id].add(backtest_id)
        self.daily_backtest_count[user_id] += 1

    def finish_backtest(self, user_id: int, backtest_id: int):
        """백테스트 완료 기록"""
        self.active_backtests[user_id].discard(backtest_id)

    def can_start_bot(self, user_id: int) -> tuple[bool, Optional[str]]:
        """
        봇 시작 가능 여부 확인.

        Returns:
            (가능여부, 에러 메시지)
        """
        if len(self.active_bots[user_id]) >= self.limits["max_concurrent_bots_per_user"]:
            return False, f"Max concurrent bots per user: {self.limits['max_concurrent_bots_per_user']}"

        return True, None

    def start_bot(self, user_id: int, bot_id: str):
        """봇 시작 기록"""
        self.active_bots[user_id].add(bot_id)

    def stop_bot(self, user_id: int, bot_id: str):
        """봇 중지 기록"""
        self.active_bots[user_id].discard(bot_id)

    def get_user_stats(self, user_id: int) -> Dict:
        """사용자별 리소스 사용 현황"""
        return {
            "user_id": user_id,
            "active_backtests": len(self.active_backtests[user_id]),
            "active_bots": len(self.active_bots[user_id]),
            "daily_backtest_count": self.daily_backtest_count[user_id],
            "limits": self.limits,
        }

    def get_global_stats(self) -> Dict:
        """전체 리소스 사용 현황"""
        total_backtests = sum(len(backtests) for backtests in self.active_backtests.values())
        total_bots = sum(len(bots) for bots in self.active_bots.values())

        return {
            "total_active_backtests": total_backtests,
            "total_active_bots": total_bots,
            "active_users": len([uid for uid, backtests in self.active_backtests.items() if backtests]),
            "limits": self.limits,
        }

    def reset_daily_counts(self):
        """일일 카운트 초기화 (크론잡으로 매일 실행)"""
        self.daily_backtest_count.clear()


# 전역 리소스 관리자
resource_manager = UserResourceManager()
