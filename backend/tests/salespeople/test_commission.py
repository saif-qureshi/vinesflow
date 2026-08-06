from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.documents.enums import DocumentType
from app.modules.documents.models import TaxRate
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput, DocumentUpdate
from app.modules.documents.service import DocumentService
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.salespeople.schemas import SalespersonCreate
from app.modules.salespeople.service import SalespersonService
from app.modules.users.models import User


def _setup(db):
    user = User(email="sp@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    customer = Party(org_id=org.id, is_customer=True, name="Beta Corp")
    product = Product(
        org_id=org.id, name="Widget", type="single",
        sale_price=Decimal("100"), purchase_price=Decimal("60"),
    )
    db.add_all([customer, product])
    db.flush()
    rate = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "GST 18%"))
    rep = SalespersonService(db).create(
        org.id, SalespersonCreate(name="Ali", commission_rate=Decimal("5"))
    )
    return org.id, customer.id, product.id, rate.id, rep.id


def _invoice(svc, org_id, party_id, pid, tax_id, rep_id, qty=2):
    doc = svc.create(
        org_id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            salesperson_id=rep_id,
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


def test_commission_is_earned_on_the_net_value_of_the_sale(db):
    org_id, party_id, pid, tax_id, rep_id = _setup(db)
    invoice = _invoice(DocumentService(db), org_id, party_id, pid, tax_id, rep_id)

    # 2 x 100 = 200 net, plus 18% tax. Commission is 5% of the 200.
    assert invoice.total == Decimal("236.00")
    assert invoice.commission_rate == Decimal("5.000")
    assert invoice.commission_amount == Decimal("10.00")


def test_a_later_rate_change_does_not_restate_earned_commission(db):
    org_id, party_id, pid, tax_id, rep_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, rep_id)

    from app.modules.salespeople.schemas import SalespersonUpdate

    SalespersonService(db).update(org_id, rep_id, SalespersonUpdate(commission_rate=Decimal("20")))
    db.refresh(invoice)
    assert invoice.commission_amount == Decimal("10.00")


def test_a_credit_note_claws_the_commission_back(db):
    org_id, party_id, pid, tax_id, rep_id = _setup(db)
    svc = DocumentService(db)
    invoice = _invoice(svc, org_id, party_id, pid, tax_id, rep_id)

    note = svc.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    assert note.salesperson_id == rep_id
    svc.finalize(org_id, note.id)
    assert note.commission_amount == Decimal("10.00")  # netted off in reporting


def test_an_invoice_without_a_salesperson_earns_nothing(db):
    org_id, party_id, pid, tax_id, _ = _setup(db)
    svc = DocumentService(db)
    doc = svc.create(
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
    svc.finalize(org_id, doc.id)
    assert doc.commission_amount == Decimal("0.00")


def test_an_unknown_salesperson_is_rejected(db):
    org_id, party_id, pid, tax_id, _ = _setup(db)
    with pytest.raises(NotFoundError):
        DocumentService(db).create(
            org_id,
            DocumentType.INVOICE,
            DocumentCreate(
                party_id=party_id,
                salesperson_id=999999,
                lines=[
                    DocumentLineInput(
                        product_id=pid, description="Widget", quantity=Decimal(1),
                        unit_price=Decimal("100"), tax_rate_id=tax_id,
                    )
                ],
            ),
        )


def test_a_credited_salesperson_cannot_be_deleted(db):
    org_id, party_id, pid, tax_id, rep_id = _setup(db)
    _invoice(DocumentService(db), org_id, party_id, pid, tax_id, rep_id)
    with pytest.raises(ConflictError):
        SalespersonService(db).delete(org_id, rep_id)


def test_the_salesperson_can_be_changed_while_still_a_draft(db):
    org_id, party_id, pid, tax_id, rep_id = _setup(db)
    svc = DocumentService(db)
    other = SalespersonService(db).create(
        org_id, SalespersonCreate(name="Sara", commission_rate=Decimal("10"))
    )
    doc = svc.create(
        org_id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            salesperson_id=rep_id,
            lines=[
                DocumentLineInput(
                    product_id=pid, description="Widget", quantity=Decimal(2),
                    unit_price=Decimal("100"), tax_rate_id=tax_id,
                )
            ],
        ),
    )
    svc.update(org_id, doc.id, DocumentType.INVOICE, DocumentUpdate(salesperson_id=other.id))
    svc.finalize(org_id, doc.id)
    assert doc.commission_amount == Decimal("20.00")
