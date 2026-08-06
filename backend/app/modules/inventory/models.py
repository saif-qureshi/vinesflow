from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import AuditMixin, Base, TimestampMixin


class Reason(Base, TimestampMixin, AuditMixin):
    __tablename__ = "reasons"
    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_reason_org_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_system: Mapped[bool] = mapped_column(nullable=False, default=False)


class Bin(Base, TimestampMixin, AuditMixin):
    __tablename__ = "bins"
    __table_args__ = (
        UniqueConstraint("org_id", "location_id", "code", name="uq_bin_location_code"),
        Index("ix_bins_org_location", "org_id", "location_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class StockLot(Base, TimestampMixin, AuditMixin):
    __tablename__ = "stock_lots"
    __table_args__ = (
        UniqueConstraint("org_id", "product_id", "lot_number", name="uq_stock_lot_product_number"),
        Index("ix_stock_lots_org_product", "org_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    lot_number: Mapped[str] = mapped_column(String(100), nullable=False)
    manufactured_date: Mapped[date | None] = mapped_column(nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class SerialUnit(Base, TimestampMixin, AuditMixin):
    __tablename__ = "serial_units"
    __table_args__ = (
        UniqueConstraint(
            "org_id", "product_id", "serial_number", name="uq_serial_unit_product_number"
        ),
        Index("ix_serial_units_org_product_status", "org_id", "product_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    serial_number: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_stock")
    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True
    )
    bin_id: Mapped[int | None] = mapped_column(
        ForeignKey("bins.id", ondelete="RESTRICT"), nullable=True
    )


class StockMovement(Base, TimestampMixin, AuditMixin):
    """Immutable stock ledger. Source of truth; corrections are new rows."""

    __tablename__ = "stock_movements"
    __table_args__ = (Index("ix_stock_movements_org_product", "org_id", "product_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    bin_id: Mapped[int | None] = mapped_column(
        ForeignKey("bins.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    lot_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_lots.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    qty_delta: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    value_delta: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)


class StockMovementSerial(Base):
    __tablename__ = "stock_movement_serials"

    movement_id: Mapped[int] = mapped_column(
        ForeignKey("stock_movements.id", ondelete="CASCADE"), primary_key=True
    )
    serial_unit_id: Mapped[int] = mapped_column(
        ForeignKey("serial_units.id", ondelete="RESTRICT"), primary_key=True
    )


class StockLevel(Base, TimestampMixin):
    """Cached on-hand per (item, variant, location). Derived from the ledger."""

    __tablename__ = "stock_levels"
    __table_args__ = (
        Index(
            "uq_stock_level_unbinned_unlotted",
            "org_id",
            "product_id",
            "location_id",
            unique=True,
            postgresql_where=text("bin_id IS NULL AND lot_id IS NULL"),
        ),
        Index(
            "uq_stock_level_binned_unlotted",
            "org_id",
            "product_id",
            "location_id",
            "bin_id",
            unique=True,
            postgresql_where=text("bin_id IS NOT NULL AND lot_id IS NULL"),
        ),
        Index(
            "uq_stock_level_unbinned_lotted",
            "org_id",
            "product_id",
            "location_id",
            "lot_id",
            unique=True,
            postgresql_where=text("bin_id IS NULL AND lot_id IS NOT NULL"),
        ),
        Index(
            "uq_stock_level_binned_lotted",
            "org_id",
            "product_id",
            "location_id",
            "bin_id",
            "lot_id",
            unique=True,
            postgresql_where=text("bin_id IS NOT NULL AND lot_id IS NOT NULL"),
        ),
        Index("ix_stock_levels_org_product", "org_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    bin_id: Mapped[int | None] = mapped_column(
        ForeignKey("bins.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    lot_id: Mapped[int | None] = mapped_column(
        ForeignKey("stock_lots.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False, default=0)
