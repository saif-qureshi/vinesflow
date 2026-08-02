from fastapi import Response

from app.core.config import settings


def set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        key=settings.SUPER_ADMIN_REFRESH_COOKIE_NAME,
        value=raw,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.SUPER_ADMIN_REFRESH_COOKIE_PATH,
        domain=settings.REFRESH_COOKIE_DOMAIN,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.SUPER_ADMIN_REFRESH_COOKIE_NAME,
        path=settings.SUPER_ADMIN_REFRESH_COOKIE_PATH,
        domain=settings.REFRESH_COOKIE_DOMAIN,
    )
