"""rename platform admin tables to super admin

Revision ID: e4b6c8d2f901
Revises: d3c9a1e7f402
Create Date: 2026-08-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e4b6c8d2f901"
down_revision: str | None = "d3c9a1e7f402"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("platform_admins", "super_admins")
    op.rename_table("platform_admin_sessions", "super_admin_sessions")

    op.execute(
        "ALTER TABLE super_admins "
        "RENAME CONSTRAINT platform_admins_pkey TO super_admins_pkey"
    )
    op.execute(
        "ALTER TABLE super_admin_sessions "
        "RENAME CONSTRAINT platform_admin_sessions_pkey TO super_admin_sessions_pkey"
    )
    op.execute(
        "ALTER TABLE super_admin_sessions "
        "RENAME CONSTRAINT platform_admin_sessions_admin_id_fkey "
        "TO super_admin_sessions_admin_id_fkey"
    )
    op.execute("ALTER INDEX ix_platform_admins_email RENAME TO ix_super_admins_email")
    op.execute(
        "ALTER INDEX ix_platform_admin_sessions_admin_id "
        "RENAME TO ix_super_admin_sessions_admin_id"
    )
    op.execute(
        "ALTER INDEX ix_platform_admin_sessions_family_id "
        "RENAME TO ix_super_admin_sessions_family_id"
    )
    op.execute(
        "ALTER INDEX ix_platform_admin_sessions_token_hash "
        "RENAME TO ix_super_admin_sessions_token_hash"
    )


def downgrade() -> None:
    op.execute("ALTER INDEX ix_super_admins_email RENAME TO ix_platform_admins_email")
    op.execute(
        "ALTER INDEX ix_super_admin_sessions_admin_id "
        "RENAME TO ix_platform_admin_sessions_admin_id"
    )
    op.execute(
        "ALTER INDEX ix_super_admin_sessions_family_id "
        "RENAME TO ix_platform_admin_sessions_family_id"
    )
    op.execute(
        "ALTER INDEX ix_super_admin_sessions_token_hash "
        "RENAME TO ix_platform_admin_sessions_token_hash"
    )
    op.execute(
        "ALTER TABLE super_admins "
        "RENAME CONSTRAINT super_admins_pkey TO platform_admins_pkey"
    )
    op.execute(
        "ALTER TABLE super_admin_sessions "
        "RENAME CONSTRAINT super_admin_sessions_pkey TO platform_admin_sessions_pkey"
    )
    op.execute(
        "ALTER TABLE super_admin_sessions "
        "RENAME CONSTRAINT super_admin_sessions_admin_id_fkey "
        "TO platform_admin_sessions_admin_id_fkey"
    )

    op.rename_table("super_admin_sessions", "platform_admin_sessions")
    op.rename_table("super_admins", "platform_admins")
