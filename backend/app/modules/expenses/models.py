from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import AuditMixin, Base, TimestampMixin
from app.modules.expenses.enums import ExpenseStatus
from app.modules.parties.models import Party

_MONEY = Numeric(18, 2)


class Expense(Base, TimestampMixin, AuditMixin):
    __tablename__ = "expenses"
    __table_args__ = (
        UniqueConstraint("org_id", "number", name="uq_expense_org_number"),
        Index("ix_expenses_org_status", "org_id", "status"),
        Index("ix_expenses_org_date", "org_id", "expense_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(12), default=ExpenseStatus.DRAFT, nullable=False)

    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_through_account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )

    vendor_id: Mapped[int | None] = mapped_column(
        ForeignKey("parties.id", ondelete="SET NULL"), index=True, nullable=True
    )
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("parties.id", ondelete="SET NULL"), nullable=True
    )

    is_tax_inclusive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reference_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    lines: Mapped[list[ExpenseLine]] = relationship(
        back_populates="expense",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ExpenseLine.line_no",
    )
    vendor: Mapped[Party | None] = relationship(foreign_keys=[vendor_id], lazy="selectin")


class ExpenseLine(Base, TimestampMixin):
    __tablename__ = "expense_lines"
    __table_args__ = (Index("ix_expense_lines_account", "account_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)

    expense: Mapped[Expense] = relationship(back_populates="lines")
