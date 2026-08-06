from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthError, ConflictError, ForbiddenError
from app.core.security import (
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.models import RefreshSession
from app.modules.users.models import User


def _now() -> datetime:
    return datetime.now(UTC)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Refresh sessions -------------------------------------------------

    def _expiry(self) -> datetime:
        return _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    def create_session(self, user_id: int, user_agent: str | None = None) -> str:
        """Start a new token family for a fresh login/registration."""
        raw = generate_refresh_token()
        self.db.add(
            RefreshSession(
                user_id=user_id,
                family_id=secrets.token_hex(16),
                token_hash=hash_token(raw),
                expires_at=self._expiry(),
                user_agent=user_agent,
            )
        )
        self.db.flush()
        return raw

    def get_session_by_raw(self, raw: str, *, lock: bool = False) -> RefreshSession | None:
        stmt = select(RefreshSession).where(RefreshSession.token_hash == hash_token(raw))
        if lock:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def rotate_session(self, session: RefreshSession, user_agent: str | None = None) -> str:
        """Revoke the presented session and issue a new one in the same family."""
        session.revoked_at = _now()
        raw = generate_refresh_token()
        self.db.add(
            RefreshSession(
                user_id=session.user_id,
                family_id=session.family_id,
                token_hash=hash_token(raw),
                expires_at=self._expiry(),
                user_agent=user_agent,
            )
        )
        self.db.flush()
        return raw

    def revoke_family(self, family_id: str) -> None:
        self.db.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == family_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=_now())
        )
        self.db.flush()

    def revoke_all_for_user(self, user_id: int) -> None:
        self.db.execute(
            update(RefreshSession)
            .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
            .values(revoked_at=_now())
        )
        self.db.flush()

    @staticmethod
    def is_expired(session: RefreshSession) -> bool:
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires < _now()

    # --- Orchestration ----------------------------------------------------

    def register_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
        org_name: str,
        user_agent: str | None,
    ) -> tuple[User, str]:
        from app.modules.orgs.service import OrgService

        if self.db.scalar(select(User.id).where(User.email == email.lower())) is not None:
            raise ConflictError("Email already registered", code="email_taken")

        user = User(
            email=email.lower(), full_name=full_name, hashed_password=hash_password(password)
        )
        self.db.add(user)
        self.db.flush()
        OrgService(self.db).create_org_with_owner(owner=user, name=org_name)
        raw = self.create_session(user.id, user_agent)
        self.db.commit()
        return user, raw

    def authenticate(
        self, *, email: str, password: str, user_agent: str | None
    ) -> tuple[User, str]:
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthError("Incorrect email or password")
        if not user.is_active:
            raise ForbiddenError("Account is disabled")
        raw = self.create_session(user.id, user_agent)
        self.db.commit()
        return user, raw

    def rotate_refresh_token(self, *, raw: str, user_agent: str | None) -> tuple[int, str]:
        # Locked so two concurrent refreshes of the same token serialise; the
        # loser then sees revoked_at set and is treated as a replay.
        session = self.get_session_by_raw(raw, lock=True)
        if session is None:
            raise AuthError("Invalid refresh token")
        if session.revoked_at is not None:
            # A revoked token replayed means the chain leaked: kill the family.
            self.revoke_family(session.family_id)
            self.db.commit()
            raise AuthError("Refresh token reuse detected")
        if self.is_expired(session):
            session.revoked_at = _now()
            self.db.commit()
            raise AuthError("Refresh token expired")
        new_raw = self.rotate_session(session, user_agent)
        self.db.commit()
        return session.user_id, new_raw

    def logout(self, *, raw: str | None) -> None:
        if not raw:
            return
        session = self.get_session_by_raw(raw)
        if session is not None:
            self.revoke_family(session.family_id)
            self.db.commit()

    def logout_all(self, *, user_id: int) -> None:
        self.revoke_all_for_user(user_id)
        self.db.commit()
