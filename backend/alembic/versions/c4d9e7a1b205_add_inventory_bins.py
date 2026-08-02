"""add inventory bins

Revision ID: c4d9e7a1b205
Revises: a6c8d0f2e413
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4d9e7a1b205"
down_revision: str | None = "a6c8d0f2e413"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "location_id", "code", name="uq_bin_location_code"),
    )
    op.create_index("ix_bins_org_id", "bins", ["org_id"])
    op.create_index("ix_bins_org_location", "bins", ["org_id", "location_id"])

    op.add_column("stock_movements", sa.Column("bin_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_stock_movements_bin_id",
        "stock_movements",
        "bins",
        ["bin_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_stock_movements_bin_id", "stock_movements", ["bin_id"])

    op.drop_constraint("uq_stock_level_org_product_location", "stock_levels", type_="unique")
    op.add_column("stock_levels", sa.Column("bin_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_stock_levels_bin_id", "stock_levels", "bins", ["bin_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_index("ix_stock_levels_bin_id", "stock_levels", ["bin_id"])
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

    op.add_column("document_lines", sa.Column("bin_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_document_lines_bin_id",
        "document_lines",
        "bins",
        ["bin_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_document_lines_bin_id", "document_lines", type_="foreignkey")
    op.drop_column("document_lines", "bin_id")

    op.drop_index("uq_stock_level_binned", table_name="stock_levels")
    op.drop_index("uq_stock_level_unbinned", table_name="stock_levels")
    op.drop_index("ix_stock_levels_bin_id", table_name="stock_levels")
    op.drop_constraint("fk_stock_levels_bin_id", "stock_levels", type_="foreignkey")
    op.drop_column("stock_levels", "bin_id")
    op.create_unique_constraint(
        "uq_stock_level_org_product_location",
        "stock_levels",
        ["org_id", "product_id", "location_id"],
    )

    op.drop_index("ix_stock_movements_bin_id", table_name="stock_movements")
    op.drop_constraint("fk_stock_movements_bin_id", "stock_movements", type_="foreignkey")
    op.drop_column("stock_movements", "bin_id")

    op.drop_index("ix_bins_org_location", table_name="bins")
    op.drop_index("ix_bins_org_id", table_name="bins")
    op.drop_table("bins")
