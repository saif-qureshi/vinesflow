import pytest

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import hash_password
from app.modules.orgs.service import OrgService
from app.modules.parties.schemas import PartyCreate, PartyListQuery, PartyUpdate
from app.modules.parties.service import PartyService
from app.modules.users.models import User


def _org(db) -> int:
    user = User(email="p@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    return org.id


def _names(rows):
    return [p.name for p in rows]


def _list(db, org_id, role=None):
    rows, _, _ = PartyService(db).list(org_id, PartyListQuery(role=role))
    return _names(rows)


def test_create_requires_a_role(db):
    org_id = _org(db)
    with pytest.raises(BadRequestError):
        PartyService(db).create(org_id, PartyCreate(name="Nobody"))


def test_create_customer(db):
    org_id = _org(db)
    party = PartyService(db).create(org_id, PartyCreate(name="Alice", is_customer=True))
    assert party.is_customer is True and party.is_vendor is False


def test_single_party_both_roles(db):
    org_id = _org(db)
    PartyService(db).create(org_id, PartyCreate(name="Acme", is_customer=True, is_vendor=True))
    assert "Acme" in _list(db, org_id, "customer")
    assert "Acme" in _list(db, org_id, "vendor")


def test_list_role_filter(db):
    org_id = _org(db)
    svc = PartyService(db)
    svc.create(org_id, PartyCreate(name="OnlyCustomer", is_customer=True))
    svc.create(org_id, PartyCreate(name="OnlyVendor", is_vendor=True))
    assert _list(db, org_id, "customer") == ["OnlyCustomer"]
    assert _list(db, org_id, "vendor") == ["OnlyVendor"]
    assert set(_list(db, org_id)) == {"OnlyCustomer", "OnlyVendor"}


def test_get_ignores_role(db):
    org_id = _org(db)
    party = PartyService(db).create(org_id, PartyCreate(name="Alice", is_customer=True))
    assert PartyService(db).get(org_id, party.id).name == "Alice"


def test_update_can_add_role(db):
    org_id = _org(db)
    svc = PartyService(db)
    party = svc.create(org_id, PartyCreate(name="Acme", is_customer=True))
    updated = svc.update(org_id, party.id, PartyUpdate(is_vendor=True, work_phone="123"))
    assert updated.is_customer and updated.is_vendor
    assert updated.work_phone == "123"


def test_update_cannot_remove_all_roles(db):
    org_id = _org(db)
    svc = PartyService(db)
    party = svc.create(org_id, PartyCreate(name="Acme", is_customer=True))
    with pytest.raises(BadRequestError):
        svc.update(org_id, party.id, PartyUpdate(is_customer=False))


def test_update_remove_one_role_keeps_record(db):
    org_id = _org(db)
    svc = PartyService(db)
    party = svc.create(org_id, PartyCreate(name="Acme", is_customer=True, is_vendor=True))
    svc.update(org_id, party.id, PartyUpdate(is_customer=False))
    assert "Acme" not in _list(db, org_id, "customer")
    assert "Acme" in _list(db, org_id, "vendor")


def test_delete_is_blocked_once_the_party_has_history(db):
    from datetime import date
    from decimal import Decimal

    from app.core.exceptions import ConflictError
    from app.modules.documents.enums import DocumentType
    from app.modules.documents.models import Document

    org_id = _org(db)
    svc = PartyService(db)
    party = svc.create(org_id, PartyCreate(name="Acme", is_customer=True))
    db.add(
        Document(
            org_id=org_id,
            type=DocumentType.INVOICE,
            number="INV-0001",
            party_id=party.id,
            issue_date=date.today(),
            subtotal=Decimal(0),
            total=Decimal(0),
        )
    )
    db.flush()

    with pytest.raises(ConflictError):
        svc.delete(org_id, party.id)
    assert svc.get(org_id, party.id).id == party.id


def test_delete_hard_removes(db):
    org_id = _org(db)
    svc = PartyService(db)
    party = svc.create(org_id, PartyCreate(name="Solo", is_customer=True))
    pid = party.id
    svc.delete(org_id, pid)
    with pytest.raises(NotFoundError):
        svc.get(org_id, pid)


def test_addresses_roundtrip(db):
    org_id = _org(db)
    party = PartyService(db).create(
        org_id,
        PartyCreate(
            name="Acme",
            is_customer=True,
            billing_address={"line1": "1 Main St", "city": "Lahore", "country": "PK"},
        ),
    )
    assert party.billing_address["city"] == "Lahore"
    assert party.shipping_address is None


def test_balance_reflects_what_the_party_owes(db):
    from decimal import Decimal

    from sqlalchemy import select

    from app.modules.documents.enums import DocumentType
    from app.modules.documents.models import TaxRate
    from app.modules.documents.schemas import DocumentCreate, DocumentLineInput
    from app.modules.documents.service import DocumentService

    org_id = _org(db)
    svc = PartyService(db)
    customer = svc.create(org_id, PartyCreate(name="Beta Corp", is_customer=True))
    assert svc.get(org_id, customer.id).balance == Decimal("0")

    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org_id, TaxRate.name == "GST 18%"))
    docs = DocumentService(db)
    invoice = docs.create(
        org_id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=customer.id,
            lines=[
                DocumentLineInput(
                    description="Widget",
                    quantity=Decimal("2"),
                    unit_price=Decimal("100"),
                    tax_rate_id=tax.id,
                )
            ],
        ),
    )
    docs.finalize(org_id, invoice.id)

    assert svc.get(org_id, customer.id).balance == Decimal("236.00")
    rows, _, _ = svc.list(org_id, PartyListQuery())
    assert next(p for p in rows if p.id == customer.id).balance == Decimal("236.00")
