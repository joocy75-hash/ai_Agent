import secrets

from fastapi import Response

from ..config import settings
from .jwt_auth import JWTAuth

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    csrf_token = secrets.token_urlsafe(32)

    cookie_params = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    if settings.cookie_domain:
        cookie_params["domain"] = settings.cookie_domain

    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        max_age=settings.jwt_expires_seconds,
        **cookie_params,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=JWTAuth.REFRESH_TOKEN_EXPIRES_DAYS * 24 * 60 * 60,
        **cookie_params,
    )

    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
        domain=settings.cookie_domain or None,
        max_age=JWTAuth.REFRESH_TOKEN_EXPIRES_DAYS * 24 * 60 * 60,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/", domain=settings.cookie_domain or None)
    response.delete_cookie(REFRESH_COOKIE, path="/", domain=settings.cookie_domain or None)
    response.delete_cookie(CSRF_COOKIE, path="/", domain=settings.cookie_domain or None)
