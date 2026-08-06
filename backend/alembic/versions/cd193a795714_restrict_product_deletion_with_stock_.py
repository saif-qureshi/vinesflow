"""restrict product deletion with stock history

Revision ID: cd193a795714
Revises: 9850595e9788
Create Date: 2026-08-06 17:48:45.215368

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd193a795714'
down_revision: Union[str, None] = '9850595e9788'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = ('stock_levels', 'stock_movements')


def _rebuild(on_delete: str) -> None:
    for table in _TABLES:
        name = f'{table}_product_id_fkey'
        op.drop_constraint(name, table, type_='foreignkey')
        op.create_foreign_key(
            name, table, 'products', ['product_id'], ['id'], ondelete=on_delete
        )


def upgrade() -> None:
    _rebuild('RESTRICT')


def downgrade() -> None:
    _rebuild('CASCADE')
