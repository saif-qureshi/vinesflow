"""store media and logo storage keys

Revision ID: 48607251a5a8
Revises: c7f4e9a2b601
Create Date: 2026-08-06 16:52:06.901662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48607251a5a8'
down_revision: Union[str, None] = 'c7f4e9a2b601'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('logo_key', sa.String(length=512), nullable=True))

    op.execute(
        """
        UPDATE media_assets
           SET storage_key = substring(url from position('org-' in url))
         WHERE storage_key IS NULL
           AND position('org-' in url) > 0
        """
    )
    op.execute(
        """
        UPDATE organizations
           SET logo_key = substring(logo_url from position('org-' in logo_url))
         WHERE logo_url IS NOT NULL
           AND position('org-' in logo_url) > 0
        """
    )
    op.execute("DELETE FROM media_assets WHERE storage_key IS NULL")

    op.alter_column('media_assets', 'storage_key',
               existing_type=sa.VARCHAR(length=512),
               nullable=False)
    op.drop_column('media_assets', 'url')
    op.drop_column('organizations', 'logo_url')


def downgrade() -> None:
    op.add_column('organizations', sa.Column('logo_url', sa.VARCHAR(length=1024), autoincrement=False, nullable=True))
    op.add_column('media_assets', sa.Column('url', sa.VARCHAR(length=1024), autoincrement=False, nullable=True))
    op.execute("UPDATE media_assets SET url = storage_key")
    op.alter_column('media_assets', 'url',
               existing_type=sa.VARCHAR(length=1024),
               nullable=False)
    op.execute("UPDATE organizations SET logo_url = logo_key")
    op.drop_column('organizations', 'logo_key')
    op.alter_column('media_assets', 'storage_key',
               existing_type=sa.VARCHAR(length=512),
               nullable=True)
