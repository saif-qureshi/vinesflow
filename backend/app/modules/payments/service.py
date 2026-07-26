from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestError, NotFoundError
from app.core import ledger as _ledger
from app.core.pagination import paginate_cursor
from app.modules.activities.service import ActivityService
from app.modules.documents.enums import (
    PAYMENT_PREFIXES,
    DocumentStatus,
    DocumentType,
    PaymentDirection,
    PaymentStatus,
)
from app.modules.documents.models import Document
from app.modules.documents.numbering import assign_number, numbering_format
from app.modules.documents.service import SALES_TYPES, DocumentService
from app.modules.parties.models import Party
from app.modules.payments.models import Payment, PaymentAllocation
from app.modules.payments.schemas import (
    OutstandingDocumentRead,
    PaymentCreate,
    PaymentListQuery,
    PaymentUpdate,
)

_ZERO = Decimal("0")
_CENTS = Decimal("0.01")

OUTSTANDING_TYPES = {
    PaymentDirection.RECEIVED: DocumentType.INVOICE,
    PaymentDirection.MADE: DocumentType.BILL,
}


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_CENTS)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PaymentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.activity = ActivityService(db)
        self.documents = DocumentService(db)
        self.ledger = _ledger.ledger_poster

    def _get_party(self, org_id: int, party_id: int, direction: PaymentDirection) -> Party:
        party = self.db.scalar(select(Party).where(Party.id == party_id, Party.org_id == org_id))
        if party is None:
            label = "Customer" if direction == PaymentDirection.RECEIVED else "Vendor"
            raise NotFoundError(f"{label} not found")
        return party

    def _build_allocations(self, org_id, direction, party_id, inputs, amount):
        if not inputs:
            return [], _ZERO
        doc_ids = [a.document_id for a in inputs]
        if len(set(doc_ids)) != len(doc_ids):
            raise BadRequestError("A document can only be allocated once per payment")
        docs = {
            d.id: d
            for d in self.db.scalars(
                select(Document).where(Document.org_id == org_id, Document.id.in_(doc_ids))
            )
        }
        is_sales = direction == PaymentDirection.RECEIVED
        allocated = _ZERO
        resolved = []
        for a in inputs:
            doc = docs.get(a.document_id)
            if doc is None:
                raise NotFoundError("A document to allocate was not found")
            if doc.party_id != party_id:
                raise BadRequestError(f"{doc.number} belongs to a different party")
            if (doc.type in SALES_TYPES) != is_sales:
                raise BadRequestError(f"{doc.number} does not match the payment direction")
            if doc.status != DocumentStatus.SENT:
                raise BadRequestError(f"Only finalized documents can be paid ({doc.number})")
            alloc = _q(a.amount)
            balance = doc.total - doc.amount_paid
            if alloc > balance:
                raise BadRequestError(f"Allocation exceeds the balance due on {doc.number}")
            allocated += alloc
            resolved.append((doc, alloc))
        if allocated > _q(amount):
            raise BadRequestError("Allocated amount exceeds the payment amount")
        return resolved, allocated

    def create(self, org_id: int, direction: PaymentDirection, payload: PaymentCreate) -> Payment:
        party = self._get_party(org_id, payload.party_id, direction)
        amount = _q(payload.amount)
        resolved, allocated = self._build_allocations(
            org_id, direction, party.id, payload.allocations, amount
        )
        document_date = payload.document_date or date.today()
        prefix, start, restart = numbering_format(
            self.db, org_id, f"payment_{direction}", PAYMENT_PREFIXES[direction]
        )
        payment = Payment(
            org_id=org_id,
            direction=direction,
            status=PaymentStatus.DRAFT,
            party_id=party.id,
            party_name=party.name,
            document_date=document_date,
            posting_date=payload.posting_date or document_date,
            method=payload.method,
            amount=amount,
            allocated_amount=allocated,
            unapplied_amount=amount - allocated,
            reference=payload.reference,
            notes=payload.notes,
        )
        payment.allocations = [
            PaymentAllocation(document_id=doc.id, document_number=doc.number, amount=alloc)
            for doc, alloc in resolved
        ]
        assign_number(
            self.db, payment, Payment.number, prefix, start, restart, document_date.year,
            Payment.org_id == org_id, Payment.direction == direction,
        )
        self.activity.record(
            org_id, "created", f"payment_{direction}", payment.number, entity_id=payment.id
        )
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def get(self, org_id: int, payment_id: int) -> Payment:
        payment = self.db.scalar(
            select(Payment)
            .where(Payment.id == payment_id, Payment.org_id == org_id)
            .options(joinedload(Payment.party))
        )
        if payment is None:
            raise NotFoundError("Payment not found")
        return payment

    def get_of_direction(self, org_id, payment_id, direction) -> Payment:
        payment = self.get(org_id, payment_id)
        if payment.direction != direction:
            raise NotFoundError("Payment not found")
        return payment

    def list(self, org_id, direction, query: PaymentListQuery):
        stmt = select(Payment).where(Payment.org_id == org_id, Payment.direction == direction)
        if query.status:
            stmt = stmt.where(Payment.status == query.status)
        if query.party_id is not None:
            stmt = stmt.where(Payment.party_id == query.party_id)
        if query.search:
            like = f"%{query.search.strip()}%"
            stmt = stmt.where(
                or_(
                    Payment.number.ilike(like),
                    Payment.party_name.ilike(like),
                    Payment.reference.ilike(like),
                )
            )
        return paginate_cursor(self.db, stmt, Payment.id, query)

    def update(self, org_id, direction, payment_id, payload: PaymentUpdate) -> Payment:
        payment = self.get_of_direction(org_id, payment_id, direction)
        if payment.status != PaymentStatus.DRAFT:
            raise BadRequestError("Only draft payments can be edited")
        fields = payload.model_fields_set
        if "party_id" in fields and payload.party_id is not None:
            party = self._get_party(org_id, payload.party_id, direction)
            payment.party_id = party.id
            payment.party_name = party.name
        for field in ("document_date", "posting_date", "method", "reference", "notes"):
            if field in fields and getattr(payload, field) is not None:
                setattr(payment, field, getattr(payload, field))
        if payload.amount is not None:
            payment.amount = _q(payload.amount)
        if payload.allocations is not None:
            resolved, allocated = self._build_allocations(
                org_id, direction, payment.party_id, payload.allocations, payment.amount
            )
            payment.allocations = [
                PaymentAllocation(document_id=doc.id, document_number=doc.number, amount=alloc)
                for doc, alloc in resolved
            ]
            payment.allocated_amount = allocated
        elif payment.allocated_amount > payment.amount:
            raise BadRequestError("Allocated amount exceeds the payment amount")
        payment.unapplied_amount = payment.amount - payment.allocated_amount
        self.activity.record(
            org_id, "updated", f"payment_{direction}", payment.number, entity_id=payment.id
        )
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def submit(self, org_id, direction, payment_id) -> Payment:
        payment = self.get_of_direction(org_id, payment_id, direction)
        if payment.status != PaymentStatus.DRAFT:
            raise BadRequestError("Only draft payments can be submitted")
        self._apply_allocations(payment, 1)
        self.ledger.post_payment(self.db, payment)
        payment.status = PaymentStatus.SUBMITTED
        payment.submitted_at = _now()
        payment.submitted_by_id = self.db.info.get("actor_id")
        self.activity.record(
            org_id, "submitted", f"payment_{direction}", payment.number, entity_id=payment.id
        )
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def cancel(self, org_id, direction, payment_id) -> Payment:
        payment = self.get_of_direction(org_id, payment_id, direction)
        if payment.status == PaymentStatus.CANCELLED:
            raise BadRequestError("Payment is already cancelled")
        if payment.status == PaymentStatus.SUBMITTED:
            self.ledger.reverse_payment(self.db, payment)
            self._apply_allocations(payment, -1)
        payment.status = PaymentStatus.CANCELLED
        payment.cancelled_at = _now()
        payment.cancelled_by_id = self.db.info.get("actor_id")
        self.activity.record(
            org_id, "cancelled", f"payment_{direction}", payment.number, entity_id=payment.id
        )
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def delete(self, org_id, direction, payment_id) -> None:
        payment = self.get_of_direction(org_id, payment_id, direction)
        if payment.status != PaymentStatus.DRAFT:
            raise BadRequestError("Only draft payments can be deleted")
        self.activity.record(
            org_id, "deleted", f"payment_{direction}", payment.number, entity_id=payment.id
        )
        self.db.delete(payment)
        self.db.commit()

    def _apply_allocations(self, payment: Payment, sign: int) -> None:
        doc_ids = [a.document_id for a in payment.allocations]
        if not doc_ids:
            return
        docs = {
            d.id: d for d in self.db.scalars(select(Document).where(Document.id.in_(doc_ids)))
        }
        for a in payment.allocations:
            doc = docs.get(a.document_id)
            if doc is None:
                continue
            if sign > 0 and a.amount > doc.total - doc.amount_paid:
                raise BadRequestError(f"Allocation exceeds the balance due on {doc.number}")
            self.documents.apply_settlement(doc, sign * a.amount)

    def outstanding_documents(self, org_id, direction, party_id) -> list[OutstandingDocumentRead]:
        doc_type = OUTSTANDING_TYPES[direction]
        docs = self.db.scalars(
            select(Document)
            .where(
                Document.org_id == org_id,
                Document.party_id == party_id,
                Document.type == doc_type,
                Document.status == DocumentStatus.SENT,
            )
            .order_by(Document.issue_date, Document.id)
        )
        result = []
        for d in docs:
            balance = d.total - d.amount_paid
            if balance > _ZERO:
                result.append(
                    OutstandingDocumentRead(
                        id=d.id,
                        number=d.number,
                        type=d.type,
                        issue_date=d.issue_date,
                        due_date=d.due_date,
                        total=d.total,
                        amount_paid=d.amount_paid,
                        balance_due=balance,
                    )
                )
        return result
