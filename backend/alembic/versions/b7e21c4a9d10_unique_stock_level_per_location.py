"""unique stock level per product and location

Revision ID: b7e21c4a9d10
Revises: 25902cd534c5
Create Date: 2026-08-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b7e21c4a9d10"
down_revision: str | None = "25902cd534c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        WITH totals AS (
            SELECT
                MIN(id) AS keep_id,
                SUM(quantity) AS quantity
            FROM stock_levels
            GROUP BY org_id, product_id, location_id
        )
        UPDATE stock_levels AS level
        SET quantity = totals.quantity
        FROM totals
        WHERE level.id = totals.keep_id
        """
    )
    op.execute(
        """
        DELETE FROM stock_levels AS duplicate
        USING stock_levels AS keeper
        WHERE duplicate.org_id = keeper.org_id
          AND duplicate.product_id = keeper.product_id
          AND duplicate.location_id = keeper.location_id
          AND duplicate.id > keeper.id
        """
    )
    op.create_unique_constraint(
        "uq_stock_level_org_product_location",
        "stock_levels",
        ["org_id", "product_id", "location_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_stock_level_org_product_location",
        "stock_levels",
        type_="unique",
    )
