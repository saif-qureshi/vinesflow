from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthError
from app.core.security import generate_refresh_token, hash_token, verify_password
from app.super_admin.auth.models import SuperAdmin, SuperAdminSession


def _now() -> datetime:
    return datetime.now(UTC)


class SuperAdminAuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _expiry(self) -> datetime:
        return _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    def _new_session(
        self,
        admin_id: int,
        user_agent: str | None,
        family_id: str | None = None,
    ) -> str:
        raw = generate_refresh_token()
        self.db.add(
            SuperAdminSession(
                admin_id=admin_id,
                family_id=family_id or secrets.token_hex(16),
                token_hash=hash_token(raw),
                expires_at=self._expiry(),
                user_agent=user_agent,
            )
        )
        self.db.flush()
        return raw

    def authenticate(
        self, *, email: str, password: str, user_agent: str | None
    ) -> tuple[SuperAdmin, str]:
        admin = self.db.scalar(select(SuperAdmin).where(SuperAdmin.email == email.lower()))
        if (
            admin is None
            or not verify_password(password, admin.hashed_password)
            or not admin.is_active
        ):
            raise AuthError("Incorrect email or password")
        raw = self._new_session(admin.id, user_agent)
        admin.last_login_at = _now()
        self.db.commit()
        return admin, raw

    def rotate(self, *, raw: str, user_agent: str | None) -> tuple[SuperAdmin, str]:
        # Locked so concurrent refreshes serialise and the loser is seen as a replay.
        session = self.db.scalar(
            select(SuperAdminSession)
            .where(SuperAdminSession.token_hash == hash_token(raw))
            .with_for_update()
        )
        if session is None:
            raise AuthError("Invalid refresh token")
        if session.revoked_at is not None:
            self._revoke_family(session.family_id)
            self.db.commit()
            raise AuthError("Refresh token reuse detected")
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < _now():
            session.revoked_at = _now()
            self.db.commit()
            raise AuthError("Refresh token expired")
        admin = self.db.get(SuperAdmin, session.admin_id)
        if admin is None or not admin.is_active:
            session.revoked_at = _now()
            self.db.commit()
            raise AuthError("Super admin account is disabled")
        session.revoked_at = _now()
        new_raw = self._new_session(admin.id, user_agent, session.family_id)
        self.db.commit()
        return admin, new_raw

    def logout(self, raw: str | None) -> None:
        if not raw:
            return
        session = self.db.scalar(
            select(SuperAdminSession).where(SuperAdminSession.token_hash == hash_token(raw))
        )
        if session is None:
            return
        self._revoke_family(session.family_id)
        self.db.commit()

    def revoke_all_for_admin(self, admin_id: int) -> None:
        self.db.execute(
            update(SuperAdminSession)
            .where(
                SuperAdminSession.admin_id == admin_id,
                SuperAdminSession.revoked_at.is_(None),
            )
            .values(revoked_at=_now())
        )
        self.db.flush()

    def _revoke_family(self, family_id: str) -> None:
        self.db.execute(
            update(SuperAdminSession)
            .where(
                SuperAdminSession.family_id == family_id,
                SuperAdminSession.revoked_at.is_(None),
            )
            .values(revoked_at=_now())
        )
