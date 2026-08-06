"""store avatar storage keys

Revision ID: 9850595e9788
Revises: 48607251a5a8
Create Date: 2026-08-06 17:11:41.279917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9850595e9788'
down_revision: Union[str, None] = '48607251a5a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('parties', sa.Column('avatar_key', sa.String(length=512), nullable=True))
    op.add_column('users', sa.Column('avatar_key', sa.String(length=512), nullable=True))
    for table in ('parties', 'users'):
        op.execute(
            f"""
            UPDATE {table}
               SET avatar_key = substring(avatar_url from position('org-' in avatar_url))
             WHERE avatar_url IS NOT NULL
               AND position('org-' in avatar_url) > 0
            """
        )
    op.drop_column('parties', 'avatar_url')
    op.drop_column('users', 'avatar_url')


def downgrade() -> None:
    op.add_column('users', sa.Column('avatar_url', sa.VARCHAR(length=1024), autoincrement=False, nullable=True))
    op.add_column('parties', sa.Column('avatar_url', sa.VARCHAR(length=1024), autoincrement=False, nullable=True))
    for table in ('parties', 'users'):
        op.execute(f"UPDATE {table} SET avatar_url = avatar_key")
    op.drop_column('users', 'avatar_key')
    op.drop_column('parties', 'avatar_key')
