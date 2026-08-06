from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.storage import get_storage
from app.db.base_class import Base, TimestampMixin

if TYPE_CHECKING:
    from app.modules.rbac.models import Role
    from app.modules.users.models import User


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), default="PKR", server_default="PKR", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(2), default="PK", server_default="PK", nullable=False)
    ntn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    strn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cnic: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Month the fiscal year starts (1=January … 7=July). PKR default is July–June.
    fiscal_year_start_month: Mapped[int] = mapped_column(
        default=7, server_default="7", nullable=False
    )
    logo_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Branding / appearance
    theme: Mapped[str] = mapped_column(String(10), default="light", server_default="light", nullable=False)
    accent_color: Mapped[str] = mapped_column(
        String(9), default="#2563eb", server_default="#2563eb", nullable=False
    )
    keep_branding: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    fbr_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    fbr_environment: Mapped[str] = mapped_column(
        String(12), default="sandbox", server_default="sandbox", nullable=False
    )
    fbr_sandbox_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    fbr_production_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    fbr_province: Mapped[str | None] = mapped_column(String(50), nullable=True)

    memberships: Mapped[list[Membership]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    roles: Mapped[list[Role]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )

    @property
    def logo_url(self) -> str | None:
        return get_storage().url_for(self.logo_key) if self.logo_key else None

    @property
    def fbr_sandbox_configured(self) -> bool:
        return bool(self.fbr_sandbox_token)

    @property
    def fbr_production_configured(self) -> bool:
        return bool(self.fbr_production_token)


class Membership(Base, TimestampMixin):
    """Links a user to an organization with exactly one role in that org."""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    # The org creator/owner. Cannot be removed or demoted by others.
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")
    role: Mapped[Role] = relationship(back_populates="memberships")
