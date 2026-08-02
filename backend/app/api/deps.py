from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.modules.orgs.models import Membership
from app.modules.users.models import User

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_membership(
    db: DbSession,
    current_user: CurrentUser,
    x_org_id: Annotated[int | None, Header(alias="X-Org-Id")] = None,
) -> Membership:
    """Resolve the caller's membership in the org given by the X-Org-Id header."""
    if x_org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Org-Id header",
        )
    membership = db.scalar(
        select(Membership)
        .where(Membership.user_id == current_user.id, Membership.org_id == x_org_id)
        .options(joinedload(Membership.role), joinedload(Membership.organization))
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )
    if not membership.organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This organization is disabled",
        )
    db.info["actor_id"] = current_user.id
    return membership


CurrentMembership = Annotated[Membership, Depends(get_current_membership)]


def membership_has_permission(membership: Membership, code: str) -> bool:
    if membership.user.is_superuser:
        return True
    if membership.is_owner:
        return True
    return any(p.code == code for p in membership.role.permissions)


def require_permission(code: str):
    """Dependency factory: ensures the caller has `code` in the current org."""

    def _checker(membership: CurrentMembership) -> Membership:
        if not membership_has_permission(membership, code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {code}",
            )
        return membership

    return _checker
