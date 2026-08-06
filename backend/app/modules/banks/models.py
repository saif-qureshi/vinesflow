from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import AuditMixin, Base, TimestampMixin
from app.modules.accounting.models import Account


class BankAccount(Base, TimestampMixin, AuditMixin):
    """A bank account the org holds, backed by its own ledger account."""

    __tablename__ = "bank_accounts"
    __table_args__ = (
        UniqueConstraint("org_id", "account_number", name="uq_bank_account_org_number"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    bank_name: Mapped[str] = mapped_column(String(150), nullable=False)
    bank_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    account_title: Mapped[str] = mapped_column(String(150), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(150), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="PKR", nullable=False)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    account: Mapped[Account] = relationship(lazy="selectin")
