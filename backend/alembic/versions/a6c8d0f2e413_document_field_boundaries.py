"""enforce document type field boundaries

Revision ID: a6c8d0f2e413
Revises: f5a7c9e1d302
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a6c8d0f2e413"
down_revision: str | None = "f5a7c9e1d302"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("expected_shipment_date", sa.Date(), nullable=True))

    # Preserve the former sales-order date under its correct business meaning.
    op.execute(
        """
        UPDATE documents
        SET expected_shipment_date = due_date
        WHERE type = 'sales_order'
        """
    )
    op.execute("UPDATE documents SET due_date = NULL WHERE type NOT IN ('invoice', 'bill')")
    op.execute(
        """
        UPDATE documents
        SET fbr_sale_origin = NULL,
            fbr_sale_destination = NULL,
            fbr_scenario_id = NULL,
            fbr_invoice_number = NULL,
            fbr_submitted_at = NULL,
            fbr_response = NULL
        WHERE type NOT IN ('invoice', 'credit_note')
        """
    )
    op.execute(
        """
        UPDATE documents
        SET fbr_reason = NULL, fbr_reason_remarks = NULL
        WHERE type != 'credit_note'
        """
    )
    op.execute(
        """
        UPDATE documents
        SET amount_paid = 0, payment_status = 'unpaid'
        WHERE type NOT IN ('invoice', 'bill')
        """
    )
    op.execute("UPDATE documents SET settled_amount = 0 WHERE type != 'credit_note'")

    op.create_check_constraint(
        "ck_documents_due_date_type",
        "documents",
        "type IN ('invoice', 'bill') OR due_date IS NULL",
    )
    op.create_check_constraint(
        "ck_documents_expected_shipment_type",
        "documents",
        "type = 'sales_order' OR expected_shipment_date IS NULL",
    )
    op.create_check_constraint(
        "ck_documents_fbr_fields_type",
        "documents",
        "type IN ('invoice', 'credit_note') OR "
        "(fbr_sale_origin IS NULL AND fbr_sale_destination IS NULL AND "
        "fbr_scenario_id IS NULL AND fbr_invoice_number IS NULL AND "
        "fbr_submitted_at IS NULL AND fbr_response IS NULL)",
    )
    op.create_check_constraint(
        "ck_documents_fbr_reason_type",
        "documents",
        "type = 'credit_note' OR (fbr_reason IS NULL AND fbr_reason_remarks IS NULL)",
    )
    op.create_check_constraint(
        "ck_documents_payment_fields_type",
        "documents",
        "type IN ('invoice', 'bill') OR (amount_paid = 0 AND payment_status = 'unpaid')",
    )
    op.create_check_constraint(
        "ck_documents_settlement_type",
        "documents",
        "type = 'credit_note' OR settled_amount = 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_documents_settlement_type", "documents", type_="check")
    op.drop_constraint("ck_documents_payment_fields_type", "documents", type_="check")
    op.drop_constraint("ck_documents_fbr_reason_type", "documents", type_="check")
    op.drop_constraint("ck_documents_fbr_fields_type", "documents", type_="check")
    op.drop_constraint("ck_documents_expected_shipment_type", "documents", type_="check")
    op.drop_constraint("ck_documents_due_date_type", "documents", type_="check")
    op.drop_column("documents", "expected_shipment_date")
