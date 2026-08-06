from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import AuditMixin, Base, TimestampMixin


class Salesperson(Base, TimestampMixin, AuditMixin):
    """Someone who earns commission on the sales they are credited with."""

    __tablename__ = "salespeople"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_salesperson_org_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Percent of net sales value, applied when a document is finalized.
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 3), default=0, server_default="0", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
