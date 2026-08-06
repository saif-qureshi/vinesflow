from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.storage import get_storage
from app.db.base_class import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.orgs.models import Membership


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Customer-app permission bypass retained for compatibility; not a super admin.
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def avatar_url(self) -> str | None:
        return get_storage().url_for(self.avatar_key) if self.avatar_key else None
