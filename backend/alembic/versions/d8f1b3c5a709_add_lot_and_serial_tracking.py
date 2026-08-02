"""add lot and serial tracking

Revision ID: d8f1b3c5a709
Revises: c4d9e7a1b205
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d8f1b3c5a709"
down_revision: str | None = "c4d9e7a1b205"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
    ]


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("tracking_mode", sa.String(length=20), server_default="none", nullable=False),
    )

    op.create_table(
        "stock_lots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("lot_number", sa.String(length=100), nullable=False),
        sa.Column("manufactured_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "product_id", "lot_number", name="uq_stock_lot_product_number"
        ),
    )
    op.create_index("ix_stock_lots_org_id", "stock_lots", ["org_id"])
    op.create_index("ix_stock_lots_org_product", "stock_lots", ["org_id", "product_id"])

    op.create_table(
        "serial_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("serial_number", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="in_stock", nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("bin_id", sa.Integer(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["bin_id"], ["bins.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "product_id", "serial_number", name="uq_serial_unit_product_number"
        ),
    )
    op.create_index("ix_serial_units_org_id", "serial_units", ["org_id"])
    op.create_index(
        "ix_serial_units_org_product_status",
        "serial_units",
        ["org_id", "product_id", "status"],
    )

    op.add_column("stock_movements", sa.Column("lot_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_stock_movements_lot_id",
        "stock_movements",
        "stock_lots",
        ["lot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_stock_movements_lot_id", "stock_movements", ["lot_id"])

    op.add_column("stock_levels", sa.Column("lot_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_stock_levels_lot_id",
        "stock_levels",
        "stock_lots",
        ["lot_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_stock_levels_lot_id", "stock_levels", ["lot_id"])
    op.drop_index("uq_stock_level_unbinned", table_name="stock_levels")
    op.drop_index("uq_stock_level_binned", table_name="stock_levels")
    op.create_index(
        "uq_stock_level_unbinned_unlotted",
        "stock_levels",
        ["org_id", "product_id", "location_id"],
        unique=True,
        postgresql_where=sa.text("bin_id IS NULL AND lot_id IS NULL"),
    )
    op.create_index(
        "uq_stock_level_binned_unlotted",
        "stock_levels",
        ["org_id", "product_id", "location_id", "bin_id"],
        unique=True,
        postgresql_where=sa.text("bin_id IS NOT NULL AND lot_id IS NULL"),
    )
    op.create_index(
        "uq_stock_level_unbinned_lotted",
        "stock_levels",
        ["org_id", "product_id", "location_id", "lot_id"],
        unique=True,
        postgresql_where=sa.text("bin_id IS NULL AND lot_id IS NOT NULL"),
    )
    op.create_index(
        "uq_stock_level_binned_lotted",
        "stock_levels",
        ["org_id", "product_id", "location_id", "bin_id", "lot_id"],
        unique=True,
        postgresql_where=sa.text("bin_id IS NOT NULL AND lot_id IS NOT NULL"),
    )

    op.create_table(
        "stock_movement_serials",
        sa.Column("movement_id", sa.Integer(), nullable=False),
        sa.Column("serial_unit_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["movement_id"], ["stock_movements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["serial_unit_id"], ["serial_units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("movement_id", "serial_unit_id"),
    )

    op.create_table(
        "document_line_lot_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_line_id", sa.Integer(), nullable=False),
        sa.Column("lot_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 3), nullable=False),
        sa.ForeignKeyConstraint(["document_line_id"], ["document_lines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lot_id"], ["stock_lots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_line_id", "lot_id", name="uq_document_line_lot"),
    )
    op.create_index(
        "ix_document_line_lot_allocations_document_line_id",
        "document_line_lot_allocations",
        ["document_line_id"],
    )

    op.create_table(
        "document_line_serials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_line_id", sa.Integer(), nullable=False),
        sa.Column("serial_number", sa.String(length=150), nullable=False),
        sa.Column("serial_unit_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["document_line_id"], ["document_lines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["serial_unit_id"], ["serial_units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_line_id", "serial_number", name="uq_document_line_serial"
        ),
    )
    op.create_index(
        "ix_document_line_serials_document_line_id",
        "document_line_serials",
        ["document_line_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_line_serials_document_line_id", table_name="document_line_serials")
    op.drop_table("document_line_serials")
    op.drop_index(
        "ix_document_line_lot_allocations_document_line_id",
        table_name="document_line_lot_allocations",
    )
    op.drop_table("document_line_lot_allocations")
    op.drop_table("stock_movement_serials")

    op.drop_index("uq_stock_level_binned_lotted", table_name="stock_levels")
    op.drop_index("uq_stock_level_unbinned_lotted", table_name="stock_levels")
    op.drop_index("uq_stock_level_binned_unlotted", table_name="stock_levels")
    op.drop_index("uq_stock_level_unbinned_unlotted", table_name="stock_levels")
    op.create_index(
        "uq_stock_level_unbinned",
        "stock_levels",
        ["org_id", "product_id", "location_id"],
        unique=True,
        postgresql_where=sa.text("bin_id IS NULL"),
    )
    op.create_index(
        "uq_stock_level_binned",
        "stock_levels",
        ["org_id", "product_id", "location_id", "bin_id"],
        unique=True,
        postgresql_where=sa.text("bin_id IS NOT NULL"),
    )
    op.drop_index("ix_stock_levels_lot_id", table_name="stock_levels")
    op.drop_constraint("fk_stock_levels_lot_id", "stock_levels", type_="foreignkey")
    op.drop_column("stock_levels", "lot_id")

    op.drop_index("ix_stock_movements_lot_id", table_name="stock_movements")
    op.drop_constraint("fk_stock_movements_lot_id", "stock_movements", type_="foreignkey")
    op.drop_column("stock_movements", "lot_id")

    op.drop_index("ix_serial_units_org_product_status", table_name="serial_units")
    op.drop_index("ix_serial_units_org_id", table_name="serial_units")
    op.drop_table("serial_units")
    op.drop_index("ix_stock_lots_org_product", table_name="stock_lots")
    op.drop_index("ix_stock_lots_org_id", table_name="stock_lots")
    op.drop_table("stock_lots")
    op.drop_column("products", "tracking_mode")
