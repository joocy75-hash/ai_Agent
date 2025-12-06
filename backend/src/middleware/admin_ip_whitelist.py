"""
관리자 IP 화이트리스트 미들웨어

환경변수 ADMIN_IP_WHITELIST에 설정된 IP만 /admin 경로 접근 허용
비어있으면 모든 IP 허용 (개발 환경용)

사용법:
    # .env
    ADMIN_IP_WHITELIST=123.45.67.89,111.222.333.444

    # main.py
    from .middleware.admin_ip_whitelist import AdminIPWhitelistMiddleware
    if os.getenv("ENVIRONMENT") == "production":
        app.add_middleware(AdminIPWhitelistMiddleware)
"""

import os
import logging
from typing import Set, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class AdminIPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    관리자 API (/admin/*) 접근을 특정 IP로 제한하는 미들웨어
    """

    def __init__(self, app, whitelist: Optional[Set[str]] = None):
        """
        Args:
            app: ASGI 애플리케이션
            whitelist: 허용할 IP 집합 (None이면 환경변수에서 로드)
        """
        super().__init__(app)

        # 환경변수에서 화이트리스트 로드
        if whitelist is None:
            whitelist_env = os.getenv("ADMIN_IP_WHITELIST", "")
            self.whitelist = {
                ip.strip() for ip in whitelist_env.split(",") if ip.strip()
            }
        else:
            self.whitelist = whitelist

        # 로컬 개발용 기본 허용 IP
        self.local_ips = {"127.0.0.1", "localhost", "::1"}

        # 개발 환경 여부
        self.is_development = os.getenv("ENVIRONMENT", "development") == "development"

        if self.whitelist:
            logger.info(f"Admin IP whitelist enabled: {self.whitelist}")
        else:
            logger.warning("Admin IP whitelist is empty - all IPs allowed for /admin")

    def _get_client_ip(self, request: Request) -> str:
        """
        클라이언트 실제 IP 추출

        프록시/로드밸런서 뒤에 있는 경우 X-Forwarded-For 헤더 확인
        """
        # X-Forwarded-For 헤더 (프록시 뒤에 있는 경우)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # 첫 번째 IP가 원본 클라이언트 IP
            return forwarded.split(",")[0].strip()

        # X-Real-IP 헤더 (Nginx 등에서 설정)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # 직접 연결된 클라이언트 IP
        if request.client:
            return request.client.host

        return "unknown"

    def _is_admin_path(self, path: str) -> bool:
        """관리자 경로인지 확인"""
        return path.startswith("/admin")

    def _is_ip_allowed(self, client_ip: str) -> bool:
        """IP가 허용되는지 확인"""
        # 개발 환경에서 화이트리스트가 비어있으면 모든 IP 허용
        if not self.whitelist:
            return True

        # 로컬 IP는 항상 허용 (개발 편의)
        if client_ip in self.local_ips:
            return True

        # 화이트리스트에 있는 IP만 허용
        return client_ip in self.whitelist

    async def dispatch(self, request: Request, call_next):
        """요청 처리"""
        path = request.url.path

        # 관리자 경로가 아니면 그냥 통과
        if not self._is_admin_path(path):
            return await call_next(request)

        # 클라이언트 IP 추출
        client_ip = self._get_client_ip(request)

        # IP 검증
        if not self._is_ip_allowed(client_ip):
            logger.warning(
                f"Admin access denied - IP: {client_ip}, Path: {path}, "
                f"Whitelist: {self.whitelist}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied: Your IP is not authorized to access admin endpoints",
                    "ip": client_ip,
                    "code": "ADMIN_IP_NOT_WHITELISTED",
                },
            )

        # 허용된 IP - 로그 기록 후 통과
        logger.debug(f"Admin access allowed - IP: {client_ip}, Path: {path}")
        return await call_next(request)


def check_admin_ip(request: Request) -> str:
    """
    FastAPI Dependency로 사용할 수 있는 IP 체크 함수

    사용법:
        @router.get("/admin/users")
        async def get_users(client_ip: str = Depends(check_admin_ip)):
            ...
    """
    whitelist_env = os.getenv("ADMIN_IP_WHITELIST", "")
    whitelist = {ip.strip() for ip in whitelist_env.split(",") if ip.strip()}
    local_ips = {"127.0.0.1", "localhost", "::1"}

    # 클라이언트 IP 추출
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.headers.get("X-Real-IP"):
        client_ip = request.headers.get("X-Real-IP").strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = "unknown"

    # 화이트리스트가 비어있으면 모든 IP 허용
    if not whitelist:
        return client_ip

    # 로컬 IP 허용
    if client_ip in local_ips:
        return client_ip

    # 화이트리스트 체크
    if client_ip not in whitelist:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=403,
            detail={
                "message": "Access denied: Your IP is not authorized",
                "ip": client_ip,
                "code": "ADMIN_IP_NOT_WHITELISTED",
            },
        )

    return client_ip
