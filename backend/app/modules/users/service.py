from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.core.security import hash_password
from app.core.storage import belongs_to_org
from app.modules.users.models import User
from app.modules.users.schemas import UserUpdate


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _avatar_key(user: User, key: str) -> str | None:
        if not key:
            return None
        if not any(belongs_to_org(key, m.org_id) for m in user.memberships):
            raise BadRequestError("Invalid avatar reference")
        return key

    def update_profile(self, user: User, payload: UserUpdate) -> User:
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.avatar_key is not None:
            user.avatar_key = self._avatar_key(user, payload.avatar_key)
        if payload.password is not None:
            user.hashed_password = hash_password(payload.password)
        self.db.commit()
        self.db.refresh(user)
        return user
