from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.pagination import paginate_cursor
from app.core.storage import belongs_to_org
from app.modules.activities.service import ActivityService
from app.modules.parties.models import Party
from app.modules.parties.schemas import PartyCreate, PartyListQuery, PartyUpdate

_ADDRESS_FIELDS = {"billing_address", "shipping_address"}
_ZERO = Decimal("0")


def _entity_type(party: Party) -> str:
    return "customer" if party.is_customer else "vendor"


class PartyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.activity = ActivityService(db)

    def _require_role(self, is_customer: bool, is_vendor: bool) -> None:
        if not is_customer and not is_vendor:
            raise BadRequestError("A party must be a customer, a vendor, or both")

    @staticmethod
    def _avatar_key(org_id: int, key: str | None) -> str | None:
        if not key:
            return None
        if not belongs_to_org(key, org_id):
            raise BadRequestError("Invalid avatar reference")
        return key

    def list(self, org_id: int, query: PartyListQuery) -> tuple[list[Party], str | None, bool]:
        stmt = select(Party).where(Party.org_id == org_id)
        if query.role == "customer":
            stmt = stmt.where(Party.is_customer.is_(True))
        elif query.role == "vendor":
            stmt = stmt.where(Party.is_vendor.is_(True))
        if query.search:
            like = f"%{query.search.strip()}%"
            stmt = stmt.where(
                or_(
                    Party.name.ilike(like),
                    Party.company_name.ilike(like),
                    Party.email.ilike(like),
                    Party.work_phone.ilike(like),
                    Party.mobile.ilike(like),
                )
            )
        if query.type:
            stmt = stmt.where(Party.type == query.type)
        if query.is_active is not None:
            stmt = stmt.where(Party.is_active == query.is_active)
        rows, cursor, has_more = paginate_cursor(self.db, stmt, Party.id, query)
        self._attach_balances(org_id, rows)
        return rows, cursor, has_more

    def _attach_balances(self, org_id: int, parties: list[Party]) -> None:
        """What each party owes, straight off the ledger. Only the receivable and
        payable legs of a voucher carry a party, so this is their account with the
        business: positive when they owe us, negative when we owe them."""
        from app.modules.accounting.models import LedgerEntry

        if not parties:
            return
        balances = dict(
            self.db.execute(
                select(
                    LedgerEntry.party_id,
                    func.coalesce(func.sum(LedgerEntry.debit - LedgerEntry.credit), 0),
                )
                .where(
                    LedgerEntry.org_id == org_id,
                    LedgerEntry.party_id.in_([p.id for p in parties]),
                )
                .group_by(LedgerEntry.party_id)
            ).all()
        )
        for party in parties:
            party.balance = balances.get(party.id, _ZERO)

    def get(self, org_id: int, party_id: int) -> Party:
        party = self.db.scalar(
            select(Party).where(Party.id == party_id, Party.org_id == org_id)
        )
        if party is None:
            raise NotFoundError("Party not found")
        self._attach_balances(org_id, [party])
        return party

    def create(self, org_id: int, payload: PartyCreate) -> Party:
        self._require_role(payload.is_customer, payload.is_vendor)
        data = payload.model_dump(exclude=_ADDRESS_FIELDS)
        data["avatar_key"] = self._avatar_key(org_id, data.get("avatar_key"))
        party = Party(
            org_id=org_id,
            billing_address=payload.billing_address.model_dump() if payload.billing_address else None,
            shipping_address=payload.shipping_address.model_dump() if payload.shipping_address else None,
            **data,
        )
        self.db.add(party)
        self.db.flush()
        self.activity.record(org_id, "created", _entity_type(party), party.name, entity_id=party.id)
        self.db.commit()
        self.db.refresh(party)
        return party

    def update(self, org_id: int, party_id: int, payload: PartyUpdate) -> Party:
        party = self.get(org_id, party_id)
        fields = payload.model_fields_set
        for key, value in payload.model_dump(exclude=_ADDRESS_FIELDS, exclude_unset=True).items():
            setattr(party, key, self._avatar_key(org_id, value) if key == "avatar_key" else value)
        self._require_role(party.is_customer, party.is_vendor)
        if "billing_address" in fields:
            party.billing_address = (
                payload.billing_address.model_dump() if payload.billing_address else None
            )
        if "shipping_address" in fields:
            party.shipping_address = (
                payload.shipping_address.model_dump() if payload.shipping_address else None
            )
        self.activity.record(org_id, "updated", _entity_type(party), party.name, entity_id=party.id)
        self.db.commit()
        self.db.refresh(party)
        return party

    def delete(self, org_id: int, party_id: int) -> None:
        from app.modules.accounting.models import LedgerEntry
        from app.modules.documents.models import Document
        from app.modules.expenses.models import Expense
        from app.modules.payments.models import Payment

        party = self.get(org_id, party_id)
        references = [
            (Document, Document.party_id),
            (Payment, Payment.party_id),
            (LedgerEntry, LedgerEntry.party_id),
            (Expense, Expense.vendor_id),
            (Expense, Expense.customer_id),
        ]
        for model, column in references:
            if self.db.scalar(
                select(model.id).where(model.org_id == org_id, column == party_id).limit(1)
            ):
                raise ConflictError("Party has transaction history; deactivate it instead")
        self.activity.record(org_id, "deleted", _entity_type(party), party.name, entity_id=party_id)
        self.db.delete(party)
        self.db.commit()
