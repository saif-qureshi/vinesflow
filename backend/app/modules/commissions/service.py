from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core import ledger as _ledger
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import paginate_cursor
from app.modules.accounting.models import Account
from app.modules.activities.service import ActivityService
from app.modules.commissions.enums import COMMISSION_PAYOUT_PREFIX, CommissionPayoutStatus
from app.modules.commissions.models import CommissionPayout
from app.modules.commissions.schemas import (
    CommissionPayoutCreate,
    CommissionPayoutListQuery,
    CommissionPayoutUpdate,
)
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import Document
from app.modules.documents.numbering import assign_number, numbering_format
from app.modules.salespeople.models import Salesperson

_ZERO = Decimal("0")
# A credit note takes back what its invoice paid out.
_EARNED_SIGN = case((Document.type == DocumentType.CREDIT_NOTE, -1), else_=1)


def _now() -> datetime:
    return datetime.now(UTC)


class CommissionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.activity = ActivityService(db)
        self.ledger = _ledger.ledger_poster

    # --- payouts ----------------------------------------------------------

    def _get_salesperson(self, org_id: int, salesperson_id: int) -> Salesperson:
        row = self.db.scalar(
            select(Salesperson).where(
                Salesperson.id == salesperson_id, Salesperson.org_id == org_id
            )
        )
        if row is None:
            raise NotFoundError("Salesperson not found")
        return row

    def _get_account(self, org_id: int, account_id: int) -> Account:
        account = self.db.scalar(
            select(Account).where(Account.id == account_id, Account.org_id == org_id)
        )
        if account is None:
            raise NotFoundError("Account not found")
        if not account.is_postable:
            raise BadRequestError(f"{account.code} {account.name} is not a postable account")
        return account

    def get(self, org_id: int, payout_id: int, *, lock: bool = False) -> CommissionPayout:
        stmt = select(CommissionPayout).where(
            CommissionPayout.id == payout_id, CommissionPayout.org_id == org_id
        )
        payout = self.db.scalar(stmt.with_for_update() if lock else stmt)
        if payout is None:
            raise NotFoundError("Commission payout not found")
        return payout

    def list(self, org_id: int, query: CommissionPayoutListQuery):
        stmt = select(CommissionPayout).where(CommissionPayout.org_id == org_id)
        if query.salesperson_id is not None:
            stmt = stmt.where(CommissionPayout.salesperson_id == query.salesperson_id)
        if query.status:
            stmt = stmt.where(CommissionPayout.status == query.status)
        if query.search:
            stmt = stmt.where(CommissionPayout.number.ilike(f"%{query.search.strip()}%"))
        return paginate_cursor(self.db, stmt, CommissionPayout.id, query)

    def create(self, org_id: int, payload: CommissionPayoutCreate) -> CommissionPayout:
        salesperson = self._get_salesperson(org_id, payload.salesperson_id)
        account = self._get_account(org_id, payload.paid_through_account_id)
        prefix, start, restart = numbering_format(
            self.db, org_id, "commission_payout", COMMISSION_PAYOUT_PREFIX
        )
        payout = CommissionPayout(
            org_id=org_id,
            status=CommissionPayoutStatus.DRAFT,
            salesperson_id=salesperson.id,
            payout_date=payload.payout_date or date.today(),
            amount=payload.amount,
            paid_through_account_id=account.id,
            reference=payload.reference,
            notes=payload.notes,
        )
        assign_number(
            self.db,
            payout,
            CommissionPayout.number,
            prefix,
            start,
            restart,
            payout.payout_date.year,
            CommissionPayout.org_id == org_id,
        )
        self.activity.record(
            org_id, "created", "commission_payout", payout.number, entity_id=payout.id
        )
        self.db.commit()
        self.db.refresh(payout)
        return payout

    def update(
        self, org_id: int, payout_id: int, payload: CommissionPayoutUpdate
    ) -> CommissionPayout:
        payout = self.get(org_id, payout_id)
        if payout.status != CommissionPayoutStatus.DRAFT:
            raise BadRequestError("Only draft payouts can be edited")
        fields = payload.model_fields_set
        if "salesperson_id" in fields and payload.salesperson_id is not None:
            payout.salesperson_id = self._get_salesperson(org_id, payload.salesperson_id).id
        if "paid_through_account_id" in fields and payload.paid_through_account_id is not None:
            payout.paid_through_account_id = self._get_account(
                org_id, payload.paid_through_account_id
            ).id
        for field in ("payout_date", "amount", "reference", "notes"):
            if field in fields and getattr(payload, field) is not None:
                setattr(payout, field, getattr(payload, field))
        self.activity.record(
            org_id, "updated", "commission_payout", payout.number, entity_id=payout.id
        )
        self.db.commit()
        self.db.refresh(payout)
        return payout

    def submit(self, org_id: int, payout_id: int) -> CommissionPayout:
        payout = self.get(org_id, payout_id, lock=True)
        if payout.status != CommissionPayoutStatus.DRAFT:
            raise BadRequestError("Only draft payouts can be submitted")
        outstanding = self.balance_for(org_id, payout.salesperson_id)
        if payout.amount > outstanding:
            raise BadRequestError(
                f"Only {outstanding} of commission is outstanding for this salesperson"
            )
        self.ledger.post_commission_payout(self.db, payout)
        payout.status = CommissionPayoutStatus.SUBMITTED
        payout.submitted_at = _now()
        self.activity.record(
            org_id, "submitted", "commission_payout", payout.number, entity_id=payout.id
        )
        self.db.commit()
        self.db.refresh(payout)
        return payout

    def cancel(self, org_id: int, payout_id: int) -> CommissionPayout:
        payout = self.get(org_id, payout_id, lock=True)
        if payout.status == CommissionPayoutStatus.CANCELLED:
            raise BadRequestError("Payout is already cancelled")
        if payout.status == CommissionPayoutStatus.SUBMITTED:
            self.ledger.reverse_commission_payout(self.db, payout)
        payout.status = CommissionPayoutStatus.CANCELLED
        payout.cancelled_at = _now()
        self.activity.record(
            org_id, "cancelled", "commission_payout", payout.number, entity_id=payout.id
        )
        self.db.commit()
        self.db.refresh(payout)
        return payout

    def delete(self, org_id: int, payout_id: int) -> None:
        payout = self.get(org_id, payout_id)
        if payout.status != CommissionPayoutStatus.DRAFT:
            raise BadRequestError("Only draft payouts can be deleted")
        self.activity.record(
            org_id, "deleted", "commission_payout", payout.number, entity_id=payout.id
        )
        self.db.delete(payout)
        self.db.commit()

    # --- balances ---------------------------------------------------------

    def _earned(self, org_id: int, salesperson_id: int | None = None):
        stmt = select(
            Document.salesperson_id,
            func.coalesce(func.sum(_EARNED_SIGN * Document.commission_amount), 0),
        ).where(
            Document.org_id == org_id,
            Document.status == DocumentStatus.SENT,
            Document.salesperson_id.is_not(None),
        )
        if salesperson_id is not None:
            stmt = stmt.where(Document.salesperson_id == salesperson_id)
        return stmt.group_by(Document.salesperson_id)

    def _paid(self, org_id: int, salesperson_id: int | None = None):
        stmt = select(
            CommissionPayout.salesperson_id,
            func.coalesce(func.sum(CommissionPayout.amount), 0),
        ).where(
            CommissionPayout.org_id == org_id,
            CommissionPayout.status == CommissionPayoutStatus.SUBMITTED,
        )
        if salesperson_id is not None:
            stmt = stmt.where(CommissionPayout.salesperson_id == salesperson_id)
        return stmt.group_by(CommissionPayout.salesperson_id)

    def balance_for(self, org_id: int, salesperson_id: int) -> Decimal:
        earned = self.db.execute(self._earned(org_id, salesperson_id)).first()
        paid = self.db.execute(self._paid(org_id, salesperson_id)).first()
        return (earned[1] if earned else _ZERO) - (paid[1] if paid else _ZERO)

    def balances(self, org_id: int) -> list[dict]:
        earned = dict(self.db.execute(self._earned(org_id)).all())
        paid = dict(self.db.execute(self._paid(org_id)).all())
        people = {
            row.id: row
            for row in self.db.scalars(
                select(Salesperson).where(Salesperson.org_id == org_id).order_by(Salesperson.name)
            )
        }
        rows = []
        for sid, person in people.items():
            got, gave = earned.get(sid, _ZERO), paid.get(sid, _ZERO)
            if got == _ZERO and gave == _ZERO and not person.is_active:
                continue
            rows.append(
                {
                    "salesperson": person,
                    "earned": got,
                    "paid": gave,
                    "outstanding": got - gave,
                }
            )
        return rows
