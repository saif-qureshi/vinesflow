from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.storage import get_storage
from app.db.base_class import AuditMixin, Base, TimestampMixin

CUSTOMER = "customer"
VENDOR = "vendor"


class Party(Base, TimestampMixin, AuditMixin):
    """A customer and/or vendor. One shared record; the is_customer / is_vendor
    flags let a single party be both. Surfaced to the UI as Customers (Sales)
    and Vendors (Purchases) — filtered views over this table."""

    __tablename__ = "parties"
    __table_args__ = (
        Index("ix_parties_org_customer", "org_id", "is_customer"),
        Index("ix_parties_org_vendor", "org_id", "is_vendor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    is_customer: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_vendor: Mapped[bool] = mapped_column(nullable=False, default=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="business")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salutation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(40), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    ntn: Mapped[str | None] = mapped_column(String(50), nullable=True)
    strn: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cnic: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_term_days: Mapped[int | None] = mapped_column(nullable=True)
    billing_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    shipping_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    @property
    def avatar_url(self) -> str | None:
        return get_storage().url_for(self.avatar_key) if self.avatar_key else None
