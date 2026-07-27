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
from app.modules.accounting.enums import (
    FiscalYearStatus,
    PeriodStatus,
    VoucherStatus,
)

_MONEY = Numeric(18, 4)


class Account(Base, TimestampMixin, AuditMixin):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_account_org_code"),
        Index("ix_accounts_org_type", "org_id", "account_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_type: Mapped[str] = mapped_column(String(12), nullable=False)
    normal_balance: Mapped[str] = mapped_column(String(6), nullable=False)
    is_control_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_postable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class FiscalYear(Base, TimestampMixin, AuditMixin):
    __tablename__ = "fiscal_years"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_fiscal_year_org_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(8), default=FiscalYearStatus.ACTIVE, nullable=False)

    periods: Mapped[list[AccountingPeriod]] = relationship(
        back_populates="fiscal_year", cascade="all, delete-orphan"
    )


class AccountingPeriod(Base, TimestampMixin, AuditMixin):
    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint("org_id", "fiscal_year_id", "period_no", name="uq_period_org_fy_no"),
        Index("ix_periods_org_dates", "org_id", "starts_on", "ends_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    fiscal_year_id: Mapped[int] = mapped_column(
        ForeignKey("fiscal_years.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    period_no: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(8), default=PeriodStatus.OPEN, nullable=False)

    fiscal_year: Mapped[FiscalYear] = relationship(back_populates="periods", lazy="joined")


class AccountingVoucher(Base, TimestampMixin, AuditMixin):
    __tablename__ = "accounting_vouchers"
    __table_args__ = (
        UniqueConstraint("org_id", "voucher_type", "number", name="uq_voucher_org_type_number"),
        Index("ix_vouchers_org_source", "org_id", "source_type", "source_id"),
        Index("ix_vouchers_org_posting_date", "org_id", "posting_date"),
        Index("ix_vouchers_org_status", "org_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    fiscal_year_id: Mapped[int] = mapped_column(
        ForeignKey("fiscal_years.id", ondelete="RESTRICT"), nullable=False
    )
    period_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_periods.id", ondelete="RESTRICT"), nullable=False
    )
    voucher_type: Mapped[str] = mapped_column(String(20), nullable=False)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    reference_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    document_date: Mapped[date] = mapped_column(Date, nullable=False)
    posting_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_debit: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    total_credit: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(12), default=VoucherStatus.DRAFT, nullable=False)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reversed_from_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounting_vouchers.id", ondelete="RESTRICT"), nullable=True
    )

    # The document/payment that produced this voucher, for backfill idempotency.
    source_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    source_id: Mapped[int | None] = mapped_column(nullable=True)

    lines: Mapped[list[VoucherLine]] = relationship(
        back_populates="voucher",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="VoucherLine.line_no",
    )


class VoucherLine(Base, TimestampMixin):
    __tablename__ = "voucher_lines"
    __table_args__ = (Index("ix_voucher_lines_account", "account_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    voucher_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_vouchers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("parties.id", ondelete="SET NULL"), nullable=True
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    debit: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    credit: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    voucher: Mapped[AccountingVoucher] = relationship(back_populates="lines")


class LedgerEntry(Base, TimestampMixin, AuditMixin):
    """The posted general ledger — one immutable row per voucher line."""

    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("ix_ledger_org_posting", "org_id", "posting_date"),
        Index("ix_ledger_org_account_posting", "org_id", "account_id", "posting_date"),
        Index("ix_ledger_org_party_posting", "org_id", "party_id", "posting_date"),
        Index("ix_ledger_org_voucher", "org_id", "voucher_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("parties.id", ondelete="SET NULL"), nullable=True
    )
    voucher_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_vouchers.id", ondelete="RESTRICT"), nullable=False
    )
    voucher_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("voucher_lines.id", ondelete="SET NULL"), nullable=True
    )
    fiscal_year_id: Mapped[int] = mapped_column(
        ForeignKey("fiscal_years.id", ondelete="RESTRICT"), nullable=False
    )
    period_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_periods.id", ondelete="RESTRICT"), nullable=False
    )
    voucher_type: Mapped[str] = mapped_column(String(20), nullable=False)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    posting_date: Mapped[date] = mapped_column(Date, nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    debit: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    credit: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="posted", nullable=False)
