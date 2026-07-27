from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounting.poster import RealLedgerPoster
from app.modules.accounting.setup import AccountingSetupService
from app.modules.documents.enums import DocumentStatus, PaymentStatus
from app.modules.documents.models import Document
from app.modules.inventory.models import StockMovement
from app.modules.orgs.models import Organization
from app.modules.payments.models import Payment

_ZERO = Decimal("0")


class BackfillService:
    """Replays finalized documents, submitted payments, and stock adjustments
    into the ledger for orgs that traded before Books existed. Idempotent —
    the poster skips anything already posted (by source_type + source_id)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.poster = RealLedgerPoster()
        self.setup = AccountingSetupService(db)

    def backfill(self, org_id: int) -> dict[str, int]:
        org = self.db.get(Organization, org_id)
        start_month = org.fiscal_year_start_month

        documents = list(
            self.db.scalars(
                select(Document)
                .where(Document.org_id == org_id, Document.status == DocumentStatus.SENT)
                .order_by(Document.issue_date, Document.id)
            )
        )
        payments = list(
            self.db.scalars(
                select(Payment)
                .where(Payment.org_id == org_id, Payment.status == PaymentStatus.SUBMITTED)
                .order_by(Payment.posting_date, Payment.id)
            )
        )
        adjustments = list(
            self.db.scalars(
                select(StockMovement)
                .where(
                    StockMovement.org_id == org_id,
                    StockMovement.type.in_(["adjustment", "revaluation"]),
                )
                .order_by(StockMovement.id)
            )
        )

        # A pre-Books document can predate the seeded fiscal year — make sure a
        # covering fiscal year + periods exist before anything tries to post.
        for doc in documents:
            self.setup.ensure_fiscal_year_for(org_id, doc.issue_date, start_month)
        for pay in payments:
            self.setup.ensure_fiscal_year_for(org_id, pay.posting_date, start_month)
        for adj in adjustments:
            self.setup.ensure_fiscal_year_for(org_id, adj.created_at.date(), start_month)

        counts = {"documents": 0, "payments": 0, "adjustments": 0}
        for doc in documents:
            self.poster.post_document(self.db, doc)
            counts["documents"] += 1
        for pay in payments:
            self.poster.post_payment(self.db, pay)
            counts["payments"] += 1
        for adj in adjustments:
            value = self._adjustment_value(adj)
            if value == _ZERO:
                continue
            self.poster.post_inventory_adjustment(
                self.db,
                org_id=org_id,
                value=value,
                account_id=None,
                posting_date=adj.created_at.date(),
                source_id=adj.id,
            )
            counts["adjustments"] += 1

        self.db.commit()
        return counts

    @staticmethod
    def _adjustment_value(movement: StockMovement) -> Decimal:
        if movement.value_delta is not None:
            return movement.value_delta
        if movement.unit_cost is not None:
            return movement.unit_cost * movement.qty_delta
        return _ZERO
