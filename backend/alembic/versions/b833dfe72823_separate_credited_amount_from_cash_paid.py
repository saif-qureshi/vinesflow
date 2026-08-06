"""separate credited amount from cash paid

Revision ID: b833dfe72823
Revises: cd193a795714
Create Date: 2026-08-06 19:27:43.011058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b833dfe72823'
down_revision: Union[str, None] = 'cd193a795714'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CHECK = "ck_documents_payment_fields_type"


def upgrade() -> None:
    op.add_column(
        'documents',
        sa.Column(
            'amount_credited', sa.Numeric(precision=18, scale=2),
            server_default='0', nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE documents d
           SET amount_credited = c.credited,
               amount_paid = GREATEST(d.amount_paid - c.credited, 0)
          FROM (
                SELECT source_document_id AS id, SUM(settled_amount) AS credited
                  FROM documents
                 WHERE type = 'credit_note'
                   AND status <> 'void'
                   AND settled_amount > 0
                   AND source_document_id IS NOT NULL
                 GROUP BY source_document_id
               ) c
         WHERE d.id = c.id
        """
    )
    op.execute(
        """
        UPDATE documents
           SET payment_status = CASE
                 WHEN amount_paid + amount_credited <= 0 THEN 'unpaid'
                 WHEN amount_paid + amount_credited < total THEN 'partial'
                 WHEN amount_paid >= total THEN 'paid'
                 ELSE 'credited'
               END
         WHERE type IN ('invoice', 'bill')
        """
    )
    op.drop_constraint(_CHECK, 'documents', type_='check')
    op.create_check_constraint(
        _CHECK,
        'documents',
        "type IN ('invoice', 'bill') OR "
        "(amount_paid = 0 AND amount_credited = 0 AND payment_status = 'unpaid')",
    )


def downgrade() -> None:
    op.drop_constraint(_CHECK, 'documents', type_='check')
    op.execute(
        """
        UPDATE documents
           SET amount_paid = amount_paid + amount_credited,
               payment_status = CASE
                 WHEN amount_paid + amount_credited <= 0 THEN 'unpaid'
                 WHEN amount_paid + amount_credited < total THEN 'partial'
                 ELSE 'paid'
               END
         WHERE amount_credited > 0
        """
    )
    op.drop_column('documents', 'amount_credited')
    op.create_check_constraint(
        _CHECK,
        'documents',
        "type IN ('invoice', 'bill') OR (amount_paid = 0 AND payment_status = 'unpaid')",
    )
