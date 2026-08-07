from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import TaxRate
from app.modules.documents.schemas import (
    DocumentCreate,
    DocumentLineInput,
    DocumentListQuery,
    DocumentUpdate,
)
from app.modules.documents.service import DocumentService
from app.modules.inventory.models import StockMovement
from app.modules.inventory.schemas import StockAdjustInput
from app.modules.inventory.service import InventoryService
from app.modules.locations.models import Location
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.settings.service import SettingsService
from app.modules.users.models import User


def _setup(db, *, track=True):
    user = User(email="d@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    loc = db.scalar(select(Location).where(Location.org_id == org.id))
    customer = Party(org_id=org.id, is_customer=True, name="Beta Corp", payment_term_days=15)
    product = Product(
        org_id=org.id,
        name="Widget",
        type="single",
        track_inventory=track,
        sale_price=Decimal("100"),
        purchase_price=Decimal("60"),
    )
    db.add_all([customer, product])
    db.flush()
    return org.id, loc.id, customer.id, product.id


def _vendor(db, org_id):
    vendor = Party(org_id=org_id, is_vendor=True, name="Supplier")
    db.add(vendor)
    db.flush()
    return vendor.id


def _tax(db, org_id, name="GST 18%"):
    return db.scalar(select(TaxRate).where(TaxRate.org_id == org_id, TaxRate.name == name))


def _line(pid, tax_id, qty=2, price=Decimal("100"), discount=Decimal("0"), discount_type="amount"):
    return DocumentLineInput(
        product_id=pid, description="Widget", quantity=Decimal(qty),
        unit_price=price, discount_type=discount_type, discount_value=discount, tax_rate_id=tax_id,
    )


def _invoice(svc, org_id, party_id, pid, tax_id, **kw):
    return svc.create(
        org_id, DocumentType.INVOICE, DocumentCreate(party_id=party_id, lines=[_line(pid, tax_id)], **kw)
    )


def test_org_creation_seeds_tax_rates(db):
    org_id, *_ = _setup(db)
    names = set(db.scalars(select(TaxRate.name).where(TaxRate.org_id == org_id)))
    assert names == {"GST 18%", "Exempt"}


def test_create_invoice_numbers_and_totals(db):
    org_id, loc_id, party_id, pid = _setup(db)
    svc = DocumentService(db)
    inv = _invoice(svc, org_id, party_id, pid, _tax(db, org_id).id)
    assert inv.number.startswith("INV-")
    assert inv.status == DocumentStatus.DRAFT
    assert inv.subtotal == Decimal("200")
    assert inv.tax_total == Decimal("36")
    assert inv.total == Decimal("236")
    assert inv.balance_due == Decimal("236")
    assert inv.due_date == inv.issue_date + timedelta(days=15)


def test_document_type_specific_dates_and_fields(db):
    org_id, _loc_id, party_id, pid = _setup(db, track=False)
    tax = _tax(db, org_id)
    svc = DocumentService(db)
    shipment_date = date.today() + timedelta(days=5)

    order = svc.create(
        org_id,
        DocumentType.SALES_ORDER,
        DocumentCreate(
            party_id=party_id,
            expected_shipment_date=shipment_date,
            lines=[_line(pid, tax.id)],
        ),
    )
    assert order.expected_shipment_date == shipment_date
    assert order.due_date is None

    challan = svc.create(
        org_id,
        DocumentType.DELIVERY_CHALLAN,
        DocumentCreate(party_id=party_id, lines=[_line(pid, tax.id)]),
    )
    assert challan.due_date is None
    assert challan.expected_shipment_date is None

    with pytest.raises(BadRequestError, match="Due date is only available"):
        svc.create(
            org_id,
            DocumentType.DELIVERY_CHALLAN,
            DocumentCreate(
                party_id=party_id,
                due_date=shipment_date,
                lines=[_line(pid, tax.id)],
            ),
        )
    with pytest.raises(BadRequestError, match="Expected shipment date is only available"):
        svc.create(
            org_id,
            DocumentType.INVOICE,
            DocumentCreate(
                party_id=party_id,
                expected_shipment_date=shipment_date,
                lines=[_line(pid, tax.id)],
            ),
        )
    with pytest.raises(BadRequestError, match="FBR filing fields are only available"):
        svc.create(
            org_id,
            DocumentType.SALES_ORDER,
            DocumentCreate(
                party_id=party_id,
                fbr_sale_origin="SINDH",
                lines=[_line(pid, tax.id)],
            ),
        )


def test_invoice_numbers_increment(db):
    org_id, loc_id, party_id, pid = _setup(db)
    svc = DocumentService(db)
    tax = _tax(db, org_id)
    a = _invoice(svc, org_id, party_id, pid, tax.id)
    b = _invoice(svc, org_id, party_id, pid, tax.id)
    assert a.number == "INV-0001"
    assert b.number == "INV-0002"


def test_sequences_are_per_type(db):
    org_id, loc_id, party_id, pid = _setup(db, track=False)
    vendor_id = _vendor(db, org_id)
    svc = DocumentService(db)
    tax = _tax(db, org_id)
    inv = _invoice(svc, org_id, party_id, pid, tax.id)
    bill = svc.create(
        org_id, DocumentType.BILL, DocumentCreate(party_id=vendor_id, lines=[_line(pid, tax.id)])
    )
    assert inv.number == "INV-0001"
    assert bill.number == "BILL-0001"


def test_explicit_number_and_duplicate_rejected(db):
    org_id, loc_id, party_id, pid = _setup(db)
    tax = _tax(db, org_id)
    svc = DocumentService(db)
    a = _invoice(svc, org_id, party_id, pid, tax.id, number="INV-CUSTOM-1")
    assert a.number == "INV-CUSTOM-1"
    with pytest.raises(ConflictError):
        _invoice(svc, org_id, party_id, pid, tax.id, number="INV-CUSTOM-1")


def test_next_number_preview(db):
    org_id, loc_id, party_id, pid = _setup(db)
    tax = _tax(db, org_id)
    svc = DocumentService(db)
    assert svc.next_number(org_id, DocumentType.INVOICE) == "INV-0001"
    _invoice(svc, org_id, party_id, pid, tax.id)
    assert svc.next_number(org_id, DocumentType.INVOICE) == "INV-0002"


def test_numbering_format_from_settings(db):
    org_id, loc_id, party_id, pid = _setup(db)
    tax = _tax(db, org_id)
    SettingsService(db).set(
        org_id, "numbering", str(DocumentType.INVOICE), {"prefix": "SALE/", "start": "000100"}
    )
    svc = DocumentService(db)
    a = _invoice(svc, org_id, party_id, pid, tax.id)
    b = _invoice(svc, org_id, party_id, pid, tax.id)
    assert a.number == "SALE/000100"
    assert b.number == "SALE/000101"


def test_numbering_yearly_restart(db):
    org_id, loc_id, party_id, pid = _setup(db)
    tax = _tax(db, org_id)
    SettingsService(db).set(
        org_id,
        "numbering",
        str(DocumentType.INVOICE),
        {"prefix": "INV-", "start": "0001", "restart": "yearly"},
    )
    svc = DocumentService(db)

    def make(issue):
        return svc.create(
            org_id,
            DocumentType.INVOICE,
            DocumentCreate(party_id=party_id, issue_date=issue, lines=[_line(pid, tax.id)]),
        )

    a = make(date(2026, 5, 1))
    b = make(date(2026, 9, 1))
    c = make(date(2027, 1, 3))
    assert a.number == "INV-2026-0001"
    assert b.number == "INV-2026-0002"
    assert c.number == "INV-2027-0001"


def test_discount_and_exempt_rate(db):
    org_id, loc_id, party_id, pid = _setup(db)
    svc = DocumentService(db)
    exempt = _tax(db, org_id, "Exempt")
    inv = svc.create(
        org_id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            lines=[_line(pid, exempt.id, qty=2, price=Decimal("100"), discount=Decimal("25"))],
        ),
    )
    assert inv.subtotal == Decimal("200")
    assert inv.discount_total == Decimal("25")
    assert inv.tax_total == Decimal("0")
    assert inv.total == Decimal("175")


def test_percent_discount(db):
    org_id, loc_id, party_id, pid = _setup(db, track=False)
    svc = DocumentService(db)
    tax = _tax(db, org_id)
    inv = svc.create(
        org_id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            lines=[_line(pid, tax.id, qty=2, price=Decimal("100"), discount=Decimal("10"), discount_type="percent")],
        ),
    )
    line = inv.lines[0]
    assert line.discount_type == "percent"
    assert line.discount_value == Decimal("10")
    assert line.discount == Decimal("20")
    assert inv.discount_total == Decimal("20")
    assert inv.tax_total == Decimal("32.40")
    assert inv.total == Decimal("212.40")


def test_amount_discount_capped_at_base(db):
    org_id, loc_id, party_id, pid = _setup(db, track=False)
    svc = DocumentService(db)
    exempt = _tax(db, org_id, "Exempt")
    inv = svc.create(
        org_id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            lines=[_line(pid, exempt.id, qty=1, price=Decimal("100"), discount=Decimal("150"))],
        ),
    )
    assert inv.discount_total == Decimal("100")
    assert inv.total == Decimal("0")


def test_percent_over_100_rejected():
    with pytest.raises(ValidationError):
        DocumentLineInput(
            product_id=1, description="x", quantity=Decimal(1), unit_price=Decimal(1),
            discount_type="percent", discount_value=Decimal("150"),
        )


def test_create_invoice_unknown_party_raises(db):
    org_id, loc_id, party_id, pid = _setup(db)
    svc = DocumentService(db)
    with pytest.raises(NotFoundError):
        _invoice(svc, org_id, 999999, pid, _tax(db, org_id).id)


def test_finalize_ships_stock(db):
    org_id, loc_id, party_id, pid = _setup(db)
    InventoryService(db).adjust(
        org_id, StockAdjustInput(product_id=pid, location_id=loc_id, qty_delta=Decimal(10), reason="Opening balance")
    )
    svc = DocumentService(db)
    inv = _invoice(svc, org_id, party_id, pid, _tax(db, org_id).id, warehouse_id=loc_id)
    svc.finalize(org_id, inv.id)
    assert inv.status == DocumentStatus.SENT
    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(8)
    movement = db.scalar(
        select(StockMovement).where(
            StockMovement.reference_type == "invoice", StockMovement.reference_id == inv.id
        )
    )
    assert movement.qty_delta == Decimal(-2)
    assert movement.unit_cost == Decimal("60")


def test_finalize_rejects_insufficient_stock_without_partial_posting(db):
    org_id, loc_id, party_id, pid = _setup(db)
    svc = DocumentService(db)
    inv = _invoice(
        svc,
        org_id,
        party_id,
        pid,
        _tax(db, org_id).id,
        warehouse_id=loc_id,
    )

    with pytest.raises(BadRequestError, match="Not enough stock"):
        svc.finalize(org_id, inv.id)

    assert inv.status == DocumentStatus.DRAFT
    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(0)
    movement = db.scalar(
        select(StockMovement).where(
            StockMovement.reference_type == "invoice",
            StockMovement.reference_id == inv.id,
        )
    )
    assert movement is None


def test_document_rejects_inactive_or_cross_org_warehouse(db):
    org_id, loc_id, party_id, pid = _setup(db)
    tax_id = _tax(db, org_id).id
    location = db.get(Location, loc_id)
    location.is_active = False
    db.commit()

    with pytest.raises(NotFoundError, match="Warehouse not found"):
        _invoice(
            DocumentService(db),
            org_id,
            party_id,
            pid,
            tax_id,
            warehouse_id=loc_id,
        )

    other_user = User(
        email="other-warehouse@test.io",
        hashed_password=hash_password("password123"),
    )
    db.add(other_user)
    db.flush()
    other_org = OrgService(db).create_org_with_owner(owner=other_user, name="Other Org")
    other_location_id = db.scalar(select(Location.id).where(Location.org_id == other_org.id))

    with pytest.raises(NotFoundError, match="Warehouse not found"):
        _invoice(
            DocumentService(db),
            org_id,
            party_id,
            pid,
            tax_id,
            warehouse_id=other_location_id,
        )


def test_bill_receives_stock(db):
    org_id, loc_id, _, pid = _setup(db)
    vendor_id = _vendor(db, org_id)
    svc = DocumentService(db)
    tax = _tax(db, org_id)
    bill = svc.create(
        org_id,
        DocumentType.BILL,
        DocumentCreate(
            party_id=vendor_id,
            warehouse_id=loc_id,
            lines=[
                DocumentLineInput(
                    product_id=pid, description="Widget", quantity=Decimal(5),
                    unit_price=Decimal("40"), tax_rate_id=tax.id,
                )
            ],
        ),
    )
    assert bill.number == "BILL-0001"
    svc.finalize(org_id, bill.id)
    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(5)
    movement = db.scalar(
        select(StockMovement).where(
            StockMovement.reference_type == "bill", StockMovement.reference_id == bill.id
        )
    )
    assert movement.qty_delta == Decimal(5)
    assert movement.unit_cost == Decimal("40")


def test_get_of_type_guards(db):
    org_id, loc_id, party_id, pid = _setup(db, track=False)
    svc = DocumentService(db)
    inv = _invoice(svc, org_id, party_id, pid, _tax(db, org_id).id)
    with pytest.raises(NotFoundError):
        svc.get_of_type(org_id, inv.id, DocumentType.BILL)


def test_finalize_only_from_draft(db):
    org_id, loc_id, party_id, pid = _setup(db, track=False)
    svc = DocumentService(db)
    inv = _invoice(svc, org_id, party_id, pid, _tax(db, org_id).id)
    svc.finalize(org_id, inv.id)
    with pytest.raises(BadRequestError):
        svc.finalize(org_id, inv.id)


def test_void_reverses_stock(db):
    org_id, loc_id, party_id, pid = _setup(db)
    InventoryService(db).adjust(
        org_id, StockAdjustInput(product_id=pid, location_id=loc_id, qty_delta=Decimal(10), reason="Opening balance")
    )
    svc = DocumentService(db)
    inv = _invoice(svc, org_id, party_id, pid, _tax(db, org_id).id, warehouse_id=loc_id)
    svc.finalize(org_id, inv.id)
    svc.void(org_id, inv.id)
    assert inv.status == DocumentStatus.VOID
    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(10)


def test_update_only_draft(db):
    org_id, loc_id, party_id, pid = _setup(db, track=False)
    svc = DocumentService(db)
    tax = _tax(db, org_id)
    inv = _invoice(svc, org_id, party_id, pid, tax.id)
    svc.update(org_id, inv.id, DocumentType.INVOICE, DocumentUpdate(lines=[_line(pid, tax.id, qty=5)]))
    assert inv.subtotal == Decimal("500")
    svc.finalize(org_id, inv.id)
    with pytest.raises(BadRequestError):
        svc.update(org_id, inv.id, DocumentType.INVOICE, DocumentUpdate(reference="X"))


def test_delete_only_draft(db):
    org_id, loc_id, party_id, pid = _setup(db, track=False)
    svc = DocumentService(db)
    tax = _tax(db, org_id)
    inv = _invoice(svc, org_id, party_id, pid, tax.id)
    svc.delete(org_id, inv.id)
    other = _invoice(svc, org_id, party_id, pid, tax.id)
    svc.finalize(org_id, other.id)
    with pytest.raises(BadRequestError):
        svc.delete(org_id, other.id)


def test_list_and_filter(db):
    org_id, loc_id, party_id, pid = _setup(db, track=False)
    svc = DocumentService(db)
    tax = _tax(db, org_id)
    a = _invoice(svc, org_id, party_id, pid, tax.id)
    _invoice(svc, org_id, party_id, pid, tax.id)
    svc.finalize(org_id, a.id)
    items, _, _ = svc.list_documents(org_id, DocumentType.INVOICE, DocumentListQuery())
    assert len(items) == 2
    drafts, _, _ = svc.list_documents(org_id, DocumentType.INVOICE, DocumentListQuery(status="draft"))
    assert len(drafts) == 1


def test_counter_sale_is_found_by_phone_however_it_was_typed(db):
    org_id, _loc_id, _party_id, pid = _setup(db, track=False)
    svc = DocumentService(db)
    tax = _tax(db, org_id)
    sale = svc.create(
        org_id,
        DocumentType.SALES_RECEIPT,
        DocumentCreate(
            contact_name="Bilal",
            contact_phone="0300-1234567",
            lines=[
                DocumentLineInput(
                    product_id=pid,
                    description="Widget",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100"),
                    tax_rate_id=tax.id,
                )
            ],
        ),
    )

    def found(term: str) -> list[int]:
        rows, _, _ = svc.list_documents(
            org_id, DocumentType.SALES_RECEIPT, DocumentListQuery(search=term)
        )
        return [r.id for r in rows]

    assert found("03001234567") == [sale.id]
    assert found("0300-1234567") == [sale.id]
    assert found("+92 300 1234567") == [sale.id]
    assert found("1234567") == [sale.id]
    assert found("Bilal") == [sale.id]
    assert found("0999") == []


def test_sellable_items(db):
    org_id, loc_id, party_id, pid = _setup(db, track=False)
    svc = DocumentService(db)
    items = svc.sellable_items(org_id, None, 20)
    assert [i.id for i in items] == [pid]
    assert items[0].sale_price == Decimal("100")
