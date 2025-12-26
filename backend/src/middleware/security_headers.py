"""
보안 헤더 미들웨어

OWASP 권장 보안 헤더를 응답에 추가합니다.
- X-Content-Type-Options: MIME 타입 스니핑 방지
- X-Frame-Options: 클릭재킹 방지
- X-XSS-Protection: XSS 필터 활성화
- Referrer-Policy: 리퍼러 정보 제한
- Permissions-Policy: 브라우저 기능 제한
- Content-Security-Policy: 콘텐츠 소스 제한
"""

import os
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    보안 헤더를 모든 응답에 추가하는 미들웨어
    """

    def __init__(self, app):
        super().__init__(app)
        self.is_production = os.getenv("ENVIRONMENT", "development") == "production"

        if self.is_production:
            logger.info("SecurityHeadersMiddleware enabled (production mode)")
        else:
            logger.info("SecurityHeadersMiddleware enabled (development mode - relaxed CSP)")

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 기본 보안 헤더 (모든 환경)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (HTTP Strict Transport Security) - 프로덕션에서만
        # HTTPS 사용 강제, 중간자 공격 방지
        if self.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # 브라우저 기능 제한 (카메라, 마이크, 위치 등)
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )

        # Content-Security-Policy (프로덕션에서 더 엄격)
        if self.is_production:
            # 프로덕션: 엄격한 CSP
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://s3.tradingview.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' wss: https:; "
                "frame-src 'self' https://s.tradingview.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
        else:
            # 개발: 완화된 CSP (디버깅 용이)
            csp = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "img-src 'self' data: https: http:; "
                "connect-src 'self' ws: wss: http: https:; "
                "frame-src *;"
            )

        response.headers["Content-Security-Policy"] = csp

        # Cache-Control (API 응답은 캐시하지 않음)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response
