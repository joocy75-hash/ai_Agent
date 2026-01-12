"""
간단한 모니터링 시스템

실사용자 20명 규모에 맞는 기본 모니터링.
메모리 기반으로 간단하게 구현.
"""
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict

import psutil


class SimpleMonitor:
    """
    간단한 메모리 기반 모니터링 시스템.

    추적 항목:
    - API 요청 수 (endpoint별)
    - 응답 시간
    - 에러 발생 수
    - 시스템 리소스 (CPU, 메모리)
    - 활성 사용자 수
    """

    def __init__(self):
        self.requests_count = defaultdict(int)
        self.response_times = defaultdict(lambda: deque(maxlen=100))
        self.errors_count = defaultdict(int)
        self.active_users = set()
        self.backtest_stats = {
            "queued": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
        }

    def track_request(self, endpoint: str):
        """API 요청 추적"""
        self.requests_count[endpoint] += 1

    def track_response_time(self, endpoint: str, response_time: float):
        """응답 시간 추적"""
        self.response_times[endpoint].append(response_time)

    def track_error(self, endpoint: str):
        """에러 추적"""
        self.errors_count[endpoint] += 1

    def track_user(self, user_id: int):
        """사용자 활동 추적"""
        self.active_users.add(user_id)

    def update_backtest_status(self, status: str, increment: int = 1):
        """백테스트 상태 업데이트"""
        if status in self.backtest_stats:
            self.backtest_stats[status] += increment

    def record_request(self, endpoint: str, duration: float, success: bool = True):
        """API 요청 기록 (레거시 호환)"""
        self.track_request(endpoint)
        self.track_response_time(endpoint, duration)

        if not success:
            self.track_error(endpoint)

    def record_user_activity(self, user_id: int):
        """사용자 활동 기록 (레거시 호환)"""
        self.track_user(user_id)

    def update_backtest_stats(self, status: str, increment: int = 1):
        """백테스트 통계 업데이트 (레거시 호환)"""
        self.update_backtest_status(status, increment)

    def get_stats(self) -> Dict:
        """현재 통계 반환"""
        system_info = self._get_system_info()

        # Compute total dynamically
        backtest_data = dict(self.backtest_stats)
        backtest_data["total"] = sum(self.backtest_stats.values())

        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_info,
            "api": {
                "total_requests": sum(self.requests_count.values()),
                "requests_by_endpoint": dict(self.requests_count),
                "total_errors": sum(self.errors_count.values()),
                "errors_by_endpoint": dict(self.errors_count),
                "avg_response_times": self._calculate_avg_response_times(),
            },
            "users": {
                "active_users": len(self.active_users),
                "users_list": list(self.active_users),
            },
            "backtest": backtest_data,
        }

        return stats

    def _calculate_avg_response_times(self) -> Dict[str, float]:
        """endpoint별 평균 응답 시간 계산"""
        avg_times = {}
        for endpoint, times in self.response_times.items():
            if times:
                avg_times[endpoint] = sum(times) / len(times)
        return avg_times

    def _get_system_info(self) -> Dict:
        """시스템 리소스 정보"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / 1024 / 1024,
                "memory_total_mb": memory.total / 1024 / 1024,
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / 1024 / 1024 / 1024,
                "disk_total_gb": disk.total / 1024 / 1024 / 1024,
            }
        except Exception:
            return {}

    def reset_stats(self):
        """통계 초기화 (일일 리셋용)"""
        self.requests_count.clear()
        self.response_times.clear()
        self.errors_count.clear()
        self.active_users.clear()
        self.backtest_stats = {
            "queued": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
        }


# 전역 모니터 인스턴스
monitor = SimpleMonitor()


# 데코레이터로 사용
def track_endpoint(endpoint_name: str):
    """
    엔드포인트 성능 추적 데코레이터.

    Usage:
        @track_endpoint("backtest_start")
        async def start_backtest(...):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                monitor.record_request(endpoint_name, duration, success)

        return wrapper
    return decorator
