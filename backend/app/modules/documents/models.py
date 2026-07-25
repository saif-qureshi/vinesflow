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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import AuditMixin, Base, TimestampMixin
from app.modules.documents.enums import (
    DiscountType,
    DocumentPaymentStatus,
    DocumentStatus,
    DocumentType,
)
from app.modules.parties.models import Party

_MONEY = Numeric(18, 2)
_QTY = Numeric(14, 3)


class TaxRate(Base, TimestampMixin, AuditMixin):
    __tablename__ = "tax_rates"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_tax_rate_org_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Document(Base, TimestampMixin, AuditMixin):
    """Shared header for every sales/purchase document. Single-table polymorphic:
    the `type` column discriminates Invoice / SalesOrder / Bill / ... Per-type
    behaviour (numbering prefix, stock direction) lives on the subclass."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("org_id", "type", "number", name="uq_document_org_type_number"),
        Index("ix_documents_org_type", "org_id", "type"),
        Index("ix_documents_org_party", "org_id", "party_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.DRAFT, nullable=False)

    party_id: Mapped[int | None] = mapped_column(
        ForeignKey("parties.id", ondelete="SET NULL"), index=True, nullable=True
    )
    warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="PKR", nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    billing_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    shipping_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    fbr_sale_origin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fbr_sale_destination: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fbr_scenario_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fbr_invoice_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fbr_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fbr_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    tax_total: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    further_tax_total: Mapped[Decimal] = mapped_column(
        _MONEY, default=0, server_default="0", nullable=False
    )
    shipping: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    adjustment: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    payment_status: Mapped[str] = mapped_column(
        String(10), default=DocumentPaymentStatus.UNPAID, nullable=False
    )

    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    stock_posted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # How much this document credited against the document it came from.
    settled_amount: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)

    lines: Mapped[list[DocumentLine]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentLine.sort_order",
        lazy="selectin",
    )
    party: Mapped[Party | None] = relationship(lazy="selectin")

    __mapper_args__ = {"polymorphic_on": "type"}

    stock_direction: int = 0
    movement_type: str = "document"

    @property
    def balance_due(self) -> Decimal:
        return self.total - self.amount_paid


class Invoice(Document):
    __mapper_args__ = {"polymorphic_identity": DocumentType.INVOICE}

    stock_direction = -1
    movement_type = "sale"


class SalesOrder(Document):
    __mapper_args__ = {"polymorphic_identity": DocumentType.SALES_ORDER}

    stock_direction = 0
    movement_type = "sales_order"


class DeliveryChallan(Document):
    __mapper_args__ = {"polymorphic_identity": DocumentType.DELIVERY_CHALLAN}

    stock_direction = -1
    movement_type = "delivery"


class CreditNote(Document):
    __mapper_args__ = {"polymorphic_identity": DocumentType.CREDIT_NOTE}

    stock_direction = 1
    movement_type = "sales_return"


class PurchaseOrder(Document):
    __mapper_args__ = {"polymorphic_identity": DocumentType.PURCHASE_ORDER}

    stock_direction = 0
    movement_type = "purchase_order"


class GoodsReceipt(Document):
    __mapper_args__ = {"polymorphic_identity": DocumentType.GOODS_RECEIPT}

    stock_direction = 1
    movement_type = "goods_receipt"


class Bill(Document):
    __mapper_args__ = {"polymorphic_identity": DocumentType.BILL}

    stock_direction = 1
    movement_type = "purchase"


class DocumentLine(Base, TimestampMixin):
    __tablename__ = "document_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(_QTY, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    discount_type: Mapped[str] = mapped_column(String(10), default=DiscountType.AMOUNT, nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    discount: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    tax_rate_id: Mapped[int | None] = mapped_column(
        ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True
    )
    tax_amount: Mapped[Decimal] = mapped_column(_MONEY, default=0, nullable=False)
    further_tax: Mapped[Decimal] = mapped_column(
        _MONEY, default=0, server_default="0", nullable=False
    )
    line_total: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    document: Mapped[Document] = relationship(back_populates="lines")
