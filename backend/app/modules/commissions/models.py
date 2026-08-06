from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import AuditMixin, Base, TimestampMixin
from app.modules.salespeople.models import Salesperson

_MONEY = Numeric(18, 2)


class CommissionPayout(Base, TimestampMixin, AuditMixin):
    """Money paid to a salesperson against the commission they have earned."""

    __tablename__ = "commission_payouts"
    __table_args__ = (UniqueConstraint("org_id", "number", name="uq_commission_payout_org_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    salesperson_id: Mapped[int] = mapped_column(
        ForeignKey("salespeople.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    payout_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    paid_through_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    salesperson: Mapped[Salesperson] = relationship(lazy="selectin")
