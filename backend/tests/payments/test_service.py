from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import hash_password
from app.modules.documents.enums import (
    DocumentPaymentStatus,
    DocumentStatus,
    DocumentType,
    PaymentDirection,
    PaymentStatus,
)
from app.modules.documents.models import TaxRate
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput
from app.modules.documents.service import DocumentService
from app.modules.locations.models import Location
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.payments.schemas import PaymentAllocationInput, PaymentCreate, PaymentUpdate
from app.modules.payments.service import PaymentService
from app.modules.products.models import Product
from app.modules.users.models import User


def _setup(db):
    user = User(email="p@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    loc = db.scalar(select(Location).where(Location.org_id == org.id))
    customer = Party(org_id=org.id, is_customer=True, name="Beta Corp")
    vendor = Party(org_id=org.id, is_vendor=True, name="Supplier")
    product = Product(
        org_id=org.id,
        name="Widget",
        type="single",
        track_inventory=False,
        sale_price=Decimal("100"),
        purchase_price=Decimal("60"),
    )
    db.add_all([customer, vendor, product])
    db.flush()
    return org.id, loc.id, customer.id, vendor.id, product.id


def _exempt(db, org_id):
    return db.scalar(select(TaxRate).where(TaxRate.org_id == org_id, TaxRate.name == "Exempt"))


def _finalized(db, org_id, doc_type, party_id, pid, tax_id, qty=2, price=Decimal("100")):
    svc = DocumentService(db)
    doc = svc.create(
        org_id,
        doc_type,
        DocumentCreate(
            party_id=party_id,
            lines=[
                DocumentLineInput(
                    product_id=pid,
                    description="Widget",
                    quantity=Decimal(qty),
                    unit_price=price,
                    tax_rate_id=tax_id,
                )
            ],
        ),
    )
    svc.finalize(org_id, doc.id)
    return doc


def _received(svc, org_id, party_id, amount, allocations):
    return svc.create(
        org_id,
        PaymentDirection.RECEIVED,
        PaymentCreate(
            party_id=party_id,
            amount=Decimal(amount),
            allocations=[
                PaymentAllocationInput(document_id=d, amount=Decimal(a)) for d, a in allocations
            ],
        ),
    )


def test_create_is_draft_and_does_not_apply(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    assert pay.number == "PAY-0001"
    assert pay.status == PaymentStatus.DRAFT
    assert pay.allocated_amount == Decimal("200")
    assert pay.unapplied_amount == Decimal("0")
    # invoice untouched while draft
    assert DocumentService(db).get(org_id, inv.id).amount_paid == Decimal("0")
    assert DocumentService(db).get(org_id, inv.id).payment_status == DocumentPaymentStatus.UNPAID


def test_submit_marks_invoice_paid(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    svc.submit(org_id, PaymentDirection.RECEIVED, pay.id)
    assert pay.status == PaymentStatus.SUBMITTED
    doc = DocumentService(db).get(org_id, inv.id)
    assert doc.amount_paid == Decimal("200")
    assert doc.payment_status == DocumentPaymentStatus.PAID


def test_partial_payment(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 50, [(inv.id, 50)])
    svc.submit(org_id, PaymentDirection.RECEIVED, pay.id)
    doc = DocumentService(db).get(org_id, inv.id)
    assert doc.amount_paid == Decimal("50")
    assert doc.payment_status == DocumentPaymentStatus.PARTIAL


def test_cancel_reverses_settlement(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    svc.submit(org_id, PaymentDirection.RECEIVED, pay.id)
    svc.cancel(org_id, PaymentDirection.RECEIVED, pay.id)
    assert pay.status == PaymentStatus.CANCELLED
    doc = DocumentService(db).get(org_id, inv.id)
    assert doc.amount_paid == Decimal("0")
    assert doc.payment_status == DocumentPaymentStatus.UNPAID


def test_unapplied_advance(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 300, [(inv.id, 200)])
    assert pay.allocated_amount == Decimal("200")
    assert pay.unapplied_amount == Decimal("100")


def test_allocation_exceeds_balance(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    with pytest.raises(BadRequestError):
        _received(svc, org_id, cust_id, 500, [(inv.id, 500)])


def test_over_allocated_vs_amount(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    with pytest.raises(BadRequestError):
        _received(svc, org_id, cust_id, 100, [(inv.id, 200)])


def test_wrong_party(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    other = Party(org_id=org_id, is_customer=True, name="Gamma")
    db.add(other)
    db.flush()
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    with pytest.raises(BadRequestError):
        _received(svc, org_id, other.id, 200, [(inv.id, 200)])


def test_direction_mismatch(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    bill = _finalized(db, org_id, DocumentType.BILL, vend_id, pid, tax.id)
    svc = PaymentService(db)
    with pytest.raises(BadRequestError):
        _received(svc, org_id, vend_id, 200, [(bill.id, 200)])


@pytest.mark.parametrize(
    "doc_type",
    [
        DocumentType.SALES_ORDER,
        DocumentType.DELIVERY_CHALLAN,
        DocumentType.CREDIT_NOTE,
    ],
)
def test_received_payment_only_accepts_sales_invoices(db, doc_type):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    doc = _finalized(db, org_id, doc_type, cust_id, pid, tax.id)

    with pytest.raises(BadRequestError, match="finalized sales invoices"):
        _received(PaymentService(db), org_id, cust_id, 200, [(doc.id, 200)])


@pytest.mark.parametrize(
    "doc_type",
    [DocumentType.PURCHASE_ORDER, DocumentType.GOODS_RECEIPT],
)
def test_made_payment_only_accepts_purchase_bills(db, doc_type):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    doc = _finalized(db, org_id, doc_type, vend_id, pid, tax.id)

    with pytest.raises(BadRequestError, match="finalized purchase bills"):
        PaymentService(db).create(
            org_id,
            PaymentDirection.MADE,
            PaymentCreate(
                party_id=vend_id,
                amount=Decimal("200"),
                allocations=[PaymentAllocationInput(document_id=doc.id, amount=Decimal("200"))],
            ),
        )


def test_payment_party_must_have_the_required_active_role(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    svc = PaymentService(db)

    with pytest.raises(BadRequestError, match="not a customer"):
        _received(svc, org_id, vend_id, 100, [])

    customer = db.get(Party, cust_id)
    customer.is_active = False
    db.commit()
    with pytest.raises(BadRequestError, match="customer is inactive"):
        _received(svc, org_id, cust_id, 100, [])


def test_only_finalized_can_be_paid(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    draft = DocumentService(db).create(
        org_id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=cust_id,
            lines=[
                DocumentLineInput(
                    product_id=pid,
                    description="W",
                    quantity=Decimal(1),
                    unit_price=Decimal(100),
                    tax_rate_id=tax.id,
                )
            ],
        ),
    )
    svc = PaymentService(db)
    with pytest.raises(BadRequestError):
        _received(svc, org_id, cust_id, 100, [(draft.id, 100)])


def test_changing_payment_party_clears_existing_allocations(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    other = Party(org_id=org_id, is_customer=True, name="Gamma")
    db.add(other)
    db.flush()
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])

    updated = svc.update(
        org_id,
        PaymentDirection.RECEIVED,
        pay.id,
        PaymentUpdate(party_id=other.id),
    )

    assert updated.party_id == other.id
    assert updated.allocations == []
    assert updated.allocated_amount == Decimal("0")
    assert updated.unapplied_amount == Decimal("200")


def test_changing_payment_party_revalidates_replacement_allocations(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    other = Party(org_id=org_id, is_customer=True, name="Gamma")
    db.add(other)
    db.flush()
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])

    with pytest.raises(BadRequestError, match="different party"):
        svc.update(
            org_id,
            PaymentDirection.RECEIVED,
            pay.id,
            PaymentUpdate(
                party_id=other.id,
                allocations=[PaymentAllocationInput(document_id=inv.id, amount=Decimal("200"))],
            ),
        )

    assert pay.party_id == cust_id
    assert pay.allocated_amount == Decimal("200")


def test_submit_revalidates_document_status(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    inv.status = DocumentStatus.VOID
    db.commit()

    with pytest.raises(BadRequestError, match="Only finalized documents"):
        svc.submit(org_id, PaymentDirection.RECEIVED, pay.id)

    assert pay.status == PaymentStatus.DRAFT


def test_submit_revalidates_document_currency(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    inv.currency = "USD"
    db.commit()

    with pytest.raises(BadRequestError, match="uses USD, but payments use PKR"):
        svc.submit(org_id, PaymentDirection.RECEIVED, pay.id)

    assert pay.status == PaymentStatus.DRAFT


def test_submit_revalidates_current_outstanding_balance(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    first = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    second = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    svc.submit(org_id, PaymentDirection.RECEIVED, first.id)

    with pytest.raises(BadRequestError, match="exceeds the balance due"):
        svc.submit(org_id, PaymentDirection.RECEIVED, second.id)

    assert second.status == PaymentStatus.DRAFT


def test_vendor_payment_pays_bill(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    bill = _finalized(db, org_id, DocumentType.BILL, vend_id, pid, tax.id)
    svc = PaymentService(db)
    pay = svc.create(
        org_id,
        PaymentDirection.MADE,
        PaymentCreate(
            party_id=vend_id,
            amount=Decimal("200"),
            allocations=[PaymentAllocationInput(document_id=bill.id, amount=Decimal("200"))],
        ),
    )
    assert pay.number == "PMT-0001"
    svc.submit(org_id, PaymentDirection.MADE, pay.id)
    doc = DocumentService(db).get(org_id, bill.id)
    assert doc.payment_status == DocumentPaymentStatus.PAID


def test_paid_invoice_cannot_be_voided(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    psvc = PaymentService(db)
    pay = _received(psvc, org_id, cust_id, 200, [(inv.id, 200)])
    psvc.submit(org_id, PaymentDirection.RECEIVED, pay.id)
    with pytest.raises(BadRequestError):
        DocumentService(db).void(org_id, inv.id)


def test_outstanding_documents(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    outstanding = svc.outstanding_documents(org_id, PaymentDirection.RECEIVED, cust_id)
    assert [o.id for o in outstanding] == [inv.id]
    assert outstanding[0].balance_due == Decimal("200")
    # once paid, it drops off
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    svc.submit(org_id, PaymentDirection.RECEIVED, pay.id)
    assert svc.outstanding_documents(org_id, PaymentDirection.RECEIVED, cust_id) == []


def test_only_draft_editable_and_submittable(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    svc.submit(org_id, PaymentDirection.RECEIVED, pay.id)
    with pytest.raises(BadRequestError):
        svc.update(org_id, PaymentDirection.RECEIVED, pay.id, PaymentUpdate(reference="X"))
    with pytest.raises(BadRequestError):
        svc.submit(org_id, PaymentDirection.RECEIVED, pay.id)


def test_get_of_direction_guards(db):
    org_id, loc_id, cust_id, vend_id, pid = _setup(db)
    tax = _exempt(db, org_id)
    inv = _finalized(db, org_id, DocumentType.INVOICE, cust_id, pid, tax.id)
    svc = PaymentService(db)
    pay = _received(svc, org_id, cust_id, 200, [(inv.id, 200)])
    with pytest.raises(NotFoundError):
        svc.get_of_direction(org_id, pay.id, PaymentDirection.MADE)
