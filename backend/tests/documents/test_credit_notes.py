from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError
from app.core.security import hash_password
from app.modules.documents.enums import DocumentPaymentStatus, DocumentStatus, DocumentType
from app.modules.documents.models import TaxRate
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput, DocumentUpdate
from app.modules.documents.service import DocumentService
from app.modules.inventory.schemas import StockAdjustInput
from app.modules.inventory.service import InventoryService
from app.modules.locations.models import Location
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.users.models import User


def _setup(db):
    user = User(email="cn@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    loc = db.scalar(select(Location).where(Location.org_id == org.id))
    customer = Party(org_id=org.id, is_customer=True, name="Beta Corp")
    product = Product(
        org_id=org.id, name="Widget", type="single", track_inventory=True,
        sale_price=Decimal("100"), purchase_price=Decimal("60"),
    )
    db.add_all([customer, product])
    db.flush()
    InventoryService(db).adjust(
        org.id, StockAdjustInput(product_id=product.id, location_id=loc.id, qty_delta=Decimal(20), reason="Opening balance")
    )
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "Exempt"))
    return org.id, loc.id, customer.id, product.id, tax.id


def _invoice(svc, org_id, party_id, pid, tax_id, qty=5, warehouse_id=None):
    doc = svc.create(
        org_id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            warehouse_id=warehouse_id,
            lines=[
                DocumentLineInput(
                    product_id=pid, description="Widget", quantity=Decimal(qty),
                    unit_price=Decimal("100"), tax_rate_id=tax_id,
                )
            ],
        ),
    )
    svc.finalize(org_id, doc.id)
    return doc


def test_credit_note_returns_stock_and_clears_the_balance(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    inv = InventoryService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, qty=5, warehouse_id=loc_id)
    assert inv.item_stock(org_id, pid).on_hand == Decimal(15)
    assert invoice.total == Decimal("500")

    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    assert note.number.startswith("CN-")
    svc.finalize(org_id, note.id)

    # goods come back in, even though the source invoice already shipped them
    assert note.stock_posted is True
    assert inv.item_stock(org_id, pid).on_hand == Decimal(20)
    # and the customer no longer owes for them, without pretending they paid
    assert invoice.amount_paid == Decimal(0)
    assert invoice.amount_credited == Decimal("500")
    assert invoice.balance_due == Decimal(0)
    assert invoice.payment_status == DocumentPaymentStatus.CREDITED
    assert note.settled_amount == Decimal("500")


def test_partial_credit_note_leaves_a_balance(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, qty=5, warehouse_id=loc_id)

    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    # return only 2 of the 5
    svc.update(
        org_id, note.id, DocumentType.CREDIT_NOTE,
        DocumentUpdate(
            lines=[
                DocumentLineInput(
                    product_id=pid, description="Widget", quantity=Decimal(2),
                    unit_price=Decimal("100"), tax_rate_id=tax_id,
                )
            ]
        ),
    )
    svc.finalize(org_id, note.id)

    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(17)
    assert invoice.amount_paid == Decimal(0)
    assert invoice.amount_credited == Decimal("200")
    assert invoice.payment_status == DocumentPaymentStatus.PARTIAL
    assert invoice.balance_due == Decimal("300")


def test_credit_cannot_exceed_the_invoice_balance(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, qty=2, warehouse_id=loc_id)

    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    svc.update(
        org_id, note.id, DocumentType.CREDIT_NOTE,
        DocumentUpdate(
            lines=[
                DocumentLineInput(
                    product_id=pid, description="Widget", quantity=Decimal(9),
                    unit_price=Decimal("100"), tax_rate_id=tax_id,
                )
            ]
        ),
    )
    with pytest.raises(BadRequestError):
        svc.finalize(org_id, note.id)


def test_credit_note_cannot_return_an_unrelated_product(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, qty=2, warehouse_id=loc_id)
    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    other = Product(
        org_id=org_id,
        name="Other Widget",
        type="single",
        track_inventory=True,
        sale_price=Decimal("100"),
        purchase_price=Decimal("60"),
    )
    db.add(other)
    db.flush()
    svc.update(
        org_id,
        note.id,
        DocumentType.CREDIT_NOTE,
        DocumentUpdate(
            lines=[
                DocumentLineInput(
                    product_id=other.id,
                    description="Widget",
                    quantity=Decimal(1),
                    unit_price=Decimal("100"),
                    tax_rate_id=tax_id,
                )
            ]
        ),
    )

    with pytest.raises(BadRequestError, match="must match quantities and prices"):
        svc.finalize(org_id, note.id)


def test_active_credit_note_blocks_voiding_its_invoice(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, warehouse_id=loc_id)
    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)

    with pytest.raises(BadRequestError, match=f"{note.number} is active"):
        svc.void(org_id, invoice.id)

    svc.delete(org_id, note.id)
    svc.void(org_id, invoice.id)
    assert invoice.status == DocumentStatus.VOID


def test_voiding_a_credit_note_restores_the_debt_and_stock(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    inv = InventoryService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, qty=5, warehouse_id=loc_id)
    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    svc.finalize(org_id, note.id)
    assert invoice.payment_status == DocumentPaymentStatus.CREDITED

    svc.void(org_id, note.id)
    assert inv.item_stock(org_id, pid).on_hand == Decimal(15)
    assert invoice.amount_paid == Decimal(0)
    assert invoice.amount_credited == Decimal(0)
    assert invoice.payment_status == DocumentPaymentStatus.UNPAID
    assert note.settled_amount == Decimal(0)


def test_standalone_credit_note_still_returns_stock(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    note = svc.create(
        org_id,
        DocumentType.CREDIT_NOTE,
        DocumentCreate(
            party_id=party_id,
            warehouse_id=loc_id,
            lines=[
                DocumentLineInput(
                    product_id=pid, description="Widget", quantity=Decimal(3),
                    unit_price=Decimal("100"), tax_rate_id=tax_id,
                )
            ],
        ),
    )
    svc.finalize(org_id, note.id)
    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(23)
    assert note.settled_amount == Decimal(0)


def _value(movements):
    return sum((m.unit_cost or Decimal(0)) * m.qty_delta for m in movements)


def _movements(db, org_id, doc_type, doc_id):
    from app.modules.inventory.models import StockMovement

    return list(
        db.scalars(
            select(StockMovement).where(
                StockMovement.org_id == org_id,
                StockMovement.reference_type == doc_type,
                StockMovement.reference_id == doc_id,
            )
        )
    )


def test_credit_note_restocks_at_cost_not_at_the_sale_price(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, qty=5, warehouse_id=loc_id)
    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    svc.finalize(org_id, note.id)

    out = _movements(db, org_id, DocumentType.INVOICE, invoice.id)
    back = _movements(db, org_id, DocumentType.CREDIT_NOTE, note.id)
    # Sold at 100, costed at 60 — the return must come back in at 60.
    assert [m.unit_cost for m in out] == [Decimal("60.0000")]
    assert [m.unit_cost for m in back] == [Decimal("60.0000")]
    # so selling and returning leaves inventory value unchanged
    assert _value(out) + _value(back) == Decimal(0)


def test_voiding_reverses_at_the_original_cost(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, qty=5, warehouse_id=loc_id)

    # The item is repriced after the invoice shipped.
    product = db.get(Product, pid)
    product.purchase_price = Decimal("80")
    db.flush()

    svc.void(org_id, invoice.id)

    movements = _movements(db, org_id, DocumentType.INVOICE, invoice.id)
    assert {m.unit_cost for m in movements} == {Decimal("60.0000")}
    assert sum(m.qty_delta for m in movements) == Decimal(0)
    assert _value(movements) == Decimal(0)


def test_a_credit_note_is_not_reported_as_money_received(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, qty=5, warehouse_id=loc_id)
    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    svc.finalize(org_id, note.id)

    # Nothing was collected, so the invoice must not read as paid.
    assert invoice.amount_paid == Decimal(0)
    assert invoice.payment_status != DocumentPaymentStatus.PAID
    # but it is settled, so it drops out of receivables
    assert invoice.balance_due == Decimal(0)


def test_payment_and_credit_are_tracked_separately(db):
    from app.modules.documents.enums import PaymentDirection
    from app.modules.payments.schemas import PaymentAllocationInput, PaymentCreate
    from app.modules.payments.service import PaymentService

    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, qty=5, warehouse_id=loc_id)

    pay = PaymentService(db)
    payment = pay.create(
        org_id,
        PaymentDirection.RECEIVED,
        PaymentCreate(
            party_id=party_id,
            amount=Decimal("200"),
            allocations=[PaymentAllocationInput(document_id=invoice.id, amount=Decimal("200"))],
        ),
    )
    pay.submit(org_id, PaymentDirection.RECEIVED, payment.id)

    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    svc.update(
        org_id, note.id, DocumentType.CREDIT_NOTE,
        DocumentUpdate(
            lines=[
                DocumentLineInput(
                    product_id=pid, description="Widget", quantity=Decimal(1),
                    unit_price=Decimal("100"), tax_rate_id=tax_id,
                )
            ]
        ),
    )
    svc.finalize(org_id, note.id)

    assert invoice.amount_paid == Decimal("200")
    assert invoice.amount_credited == Decimal("100")
    assert invoice.balance_due == Decimal("200")
    assert invoice.payment_status == DocumentPaymentStatus.PARTIAL


def test_a_deactivated_tax_rate_cannot_be_used_on_new_documents(db):
    from app.core.exceptions import NotFoundError

    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    rate = db.get(TaxRate, tax_id)
    rate.is_active = False
    db.flush()

    with pytest.raises(NotFoundError):
        DocumentService(db).create(
            org_id,
            DocumentType.INVOICE,
            DocumentCreate(
                party_id=party_id,
                lines=[
                    DocumentLineInput(
                        product_id=pid, description="Widget", quantity=Decimal(1),
                        unit_price=Decimal("100"), tax_rate_id=tax_id,
                    )
                ],
            ),
        )
