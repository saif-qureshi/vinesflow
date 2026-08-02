from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.container import Provide
from app.core.exceptions import AuthError
from app.core.ratelimit import limiter
from app.core.responses import EnvelopeRoute, error_body
from app.super_admin.auth.cookies import clear_refresh_cookie, set_refresh_cookie
from app.super_admin.auth.deps import CurrentSuperAdmin
from app.super_admin.auth.models import SuperAdmin
from app.super_admin.auth.schemas import (
    SuperAdminLogin,
    SuperAdminMessage,
    SuperAdminRead,
    SuperAdminToken,
)
from app.super_admin.auth.security import create_access_token
from app.super_admin.auth.service import SuperAdminAuthService

router = APIRouter(prefix="/auth", tags=["super-admin-auth"], route_class=EnvelopeRoute)
AuthSvc = Depends(Provide(SuperAdminAuthService))


def _refresh_error(message: str) -> JSONResponse:
    response = JSONResponse(
        error_body("unauthorized", message),
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
    clear_refresh_cookie(response)
    return response


@router.post("/login", response_model=SuperAdminToken)
@limiter.limit("10/minute")
def login(
    payload: SuperAdminLogin,
    request: Request,
    response: Response,
    auth: SuperAdminAuthService = AuthSvc,
) -> SuperAdminToken:
    admin, raw = auth.authenticate(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
    )
    set_refresh_cookie(response, raw)
    return SuperAdminToken(access_token=create_access_token(admin.id))


@router.post("/refresh", response_model=SuperAdminToken)
@limiter.limit("60/minute")
def refresh(
    request: Request,
    response: Response,
    auth: SuperAdminAuthService = AuthSvc,
):
    raw = request.cookies.get(settings.SUPER_ADMIN_REFRESH_COOKIE_NAME)
    if not raw:
        return _refresh_error("Missing refresh token")
    try:
        admin, new_raw = auth.rotate(
            raw=raw,
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as exc:
        return _refresh_error(exc.message)
    set_refresh_cookie(response, new_raw)
    return SuperAdminToken(access_token=create_access_token(admin.id))


@router.post("/logout", response_model=SuperAdminMessage)
def logout(
    request: Request,
    response: Response,
    auth: SuperAdminAuthService = AuthSvc,
) -> SuperAdminMessage:
    auth.logout(request.cookies.get(settings.SUPER_ADMIN_REFRESH_COOKIE_NAME))
    clear_refresh_cookie(response)
    return SuperAdminMessage(message="Logged out")


@router.get("/me", response_model=SuperAdminRead)
def me(admin: CurrentSuperAdmin) -> SuperAdmin:
    return admin
