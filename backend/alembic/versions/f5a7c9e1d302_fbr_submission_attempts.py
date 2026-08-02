"""add FBR submission attempt history

Revision ID: f5a7c9e1d302
Revises: e4b6c8d2f901
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f5a7c9e1d302"
down_revision: str | None = "e4b6c8d2f901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fbr_submission_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_fbr_submission_attempts_document_id",
        "fbr_submission_attempts",
        ["document_id"],
    )
    op.create_index(
        "ix_fbr_submission_attempts_org_created",
        "fbr_submission_attempts",
        ["org_id", "created_at"],
    )
    op.create_index("ix_fbr_submission_attempts_org_id", "fbr_submission_attempts", ["org_id"])
    op.create_index("ix_fbr_submission_attempts_status", "fbr_submission_attempts", ["status"])
    op.execute(
        """
        INSERT INTO fbr_submission_attempts
            (org_id, document_id, status, error, created_at, updated_at)
        SELECT org_id, id, 'submitted', NULL, fbr_submitted_at, fbr_submitted_at
        FROM documents
        WHERE fbr_submitted_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_fbr_submission_attempts_status", table_name="fbr_submission_attempts")
    op.drop_index("ix_fbr_submission_attempts_org_id", table_name="fbr_submission_attempts")
    op.drop_index("ix_fbr_submission_attempts_org_created", table_name="fbr_submission_attempts")
    op.drop_index("ix_fbr_submission_attempts_document_id", table_name="fbr_submission_attempts")
    op.drop_table("fbr_submission_attempts")
