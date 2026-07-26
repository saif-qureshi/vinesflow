from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.container import Provide
from app.core.exceptions import AuthError
from app.core.ratelimit import limiter
from app.core.responses import EnvelopeRoute, error_body
from app.core.security import create_access_token
from app.modules.auth.cookies import clear_refresh_cookie, set_refresh_cookie
from app.modules.auth.schemas import (
    LoginRequest,
    MeResponse,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
)
from app.modules.auth.service import AuthService
from app.modules.orgs.service import OrgService

router = APIRouter(prefix="/auth", tags=["auth"], route_class=EnvelopeRoute)

AuthSvc = Depends(Provide(AuthService))
OrgSvc = Depends(Provide(OrgService))


def _refresh_error(message: str) -> JSONResponse:
    resp = JSONResponse(error_body("unauthorized", message), status_code=status.HTTP_401_UNAUTHORIZED)
    clear_refresh_cookie(resp)
    return resp


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(payload: RegisterRequest, request: Request, response: Response, auth: AuthService = AuthSvc):
    user, raw = auth.register_user(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        org_name=payload.org_name,
        user_agent=request.headers.get("user-agent"),
    )
    set_refresh_cookie(response, raw)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(payload: LoginRequest, request: Request, response: Response, auth: AuthService = AuthSvc):
    user, raw = auth.authenticate(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
    )
    set_refresh_cookie(response, raw)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("60/minute")
def refresh(request: Request, response: Response, auth: AuthService = AuthSvc):
    raw = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw:
        return _refresh_error("Missing refresh token")
    try:
        user_id, new_raw = auth.rotate_refresh_token(
            raw=raw, user_agent=request.headers.get("user-agent")
        )
    except AuthError as exc:
        return _refresh_error(exc.message)
    set_refresh_cookie(response, new_raw)
    return TokenResponse(access_token=create_access_token(user_id))


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, auth: AuthService = AuthSvc):
    auth.logout(raw=request.cookies.get(settings.REFRESH_COOKIE_NAME))
    clear_refresh_cookie(response)
    return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
def logout_all(current_user: CurrentUser, response: Response, auth: AuthService = AuthSvc):
    auth.logout_all(user_id=current_user.id)
    clear_refresh_cookie(response)
    return MessageResponse(message="All sessions revoked")


@router.get("/me", response_model=MeResponse)
def me(current_user: CurrentUser, orgs: OrgService = OrgSvc) -> MeResponse:
    return MeResponse(
        user=current_user, memberships=orgs.list_user_memberships(current_user.id)
    )
