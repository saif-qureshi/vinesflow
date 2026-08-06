from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import AuditMixin, Base, TimestampMixin


class Manufacturer(Base, TimestampMixin, AuditMixin):
    """Org-scoped manufacturer that makes an item."""

    __tablename__ = "manufacturers"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_manufacturer_org_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
