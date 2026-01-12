"""
API 성능 모니터링 미들웨어

- API 응답 시간 측정 및 로깅
- 느린 요청 경고 (500ms 이상)
- X-Response-Time 헤더 추가
"""
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("performance")

# 느린 요청 임계값 (밀리초)
SLOW_REQUEST_THRESHOLD_MS = 500


class PerformanceMiddleware(BaseHTTPMiddleware):
    """API 성능 모니터링 미들웨어"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 시작 시간 기록
        start_time = time.perf_counter()

        # 요청 처리
        response = await call_next(request)

        # 응답 시간 계산 (밀리초)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # 경로 정보
        path = request.url.path
        method = request.method

        # 헬스체크는 로깅 제외
        if path == "/health":
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            return response

        # 느린 요청 경고
        if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                f"🐌 SLOW API: {method} {path} took {duration_ms:.2f}ms "
                f"(threshold: {SLOW_REQUEST_THRESHOLD_MS}ms)"
            )
        else:
            # 일반 요청 로깅 (DEBUG 레벨)
            logger.debug(f"⚡ API: {method} {path} - {duration_ms:.2f}ms")

        # 응답 헤더에 응답 시간 추가
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        return response


# 통계 수집용 (선택적)
class PerformanceStats:
    """API 성능 통계 수집"""

    def __init__(self):
        self.request_times: dict = {}  # path -> [times]
        self.slow_requests: list = []

    def record(self, path: str, duration_ms: float):
        """요청 시간 기록"""
        if path not in self.request_times:
            self.request_times[path] = []

        # 최근 100개만 유지
        times = self.request_times[path]
        times.append(duration_ms)
        if len(times) > 100:
            times.pop(0)

        # 느린 요청 기록
        if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            self.slow_requests.append({
                "path": path,
                "duration_ms": duration_ms,
                "timestamp": time.time()
            })
            # 최근 50개만 유지
            if len(self.slow_requests) > 50:
                self.slow_requests.pop(0)

    def get_stats(self, path: str = None) -> dict:
        """통계 조회"""
        if path:
            times = self.request_times.get(path, [])
            if not times:
                return {"error": "No data for path"}
            return {
                "path": path,
                "count": len(times),
                "avg_ms": sum(times) / len(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "p95_ms": sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times),
            }

        # 전체 통계
        all_stats = {}
        for p, times in self.request_times.items():
            if times:
                all_stats[p] = {
                    "count": len(times),
                    "avg_ms": round(sum(times) / len(times), 2),
                    "max_ms": round(max(times), 2),
                }
        return {
            "endpoints": all_stats,
            "slow_requests_count": len(self.slow_requests),
            "recent_slow_requests": self.slow_requests[-10:],
        }


# 전역 통계 인스턴스
performance_stats = PerformanceStats()
