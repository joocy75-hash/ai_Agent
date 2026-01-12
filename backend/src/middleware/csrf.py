import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Double-submit CSRF protection for cookie-based auth.
    Requires matching X-CSRF-Token header and csrf_token cookie for mutating requests.
    """

    def __init__(self, app, exempt_paths: set[str] | None = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or set()
        # CORS origins from environment
        cors_origins_env = os.environ.get("CORS_ORIGINS", "")
        self.allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

    def _get_cors_headers(self, request: Request) -> dict:
        """CORS 헤더 생성 (에러 응답용)"""
        origin = request.headers.get("origin", "")
        headers = {
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-CSRF-Token",
        }
        # Origin이 허용 목록에 있으면 해당 origin 반환
        if origin in self.allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
        elif self.allowed_origins:
            # 허용된 origin이 있으면 첫 번째 것 사용
            headers["Access-Control-Allow-Origin"] = self.allowed_origins[0]
        return headers

    async def dispatch(self, request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            path = request.url.path
            if path not in self.exempt_paths:
                auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
                if not (auth_header and auth_header.startswith("Bearer ")):
                    csrf_cookie = request.cookies.get("csrf_token")
                    csrf_header = request.headers.get("X-CSRF-Token")
                    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                        # CORS 헤더를 포함하여 403 반환
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "CSRF token missing or invalid"},
                            headers=self._get_cors_headers(request),
                        )

        return await call_next(request)
