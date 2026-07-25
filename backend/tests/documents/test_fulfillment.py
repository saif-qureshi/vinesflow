from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError
from app.core.security import hash_password
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import TaxRate
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput
from app.modules.documents.service import DocumentService
from app.modules.inventory.schemas import StockAdjustInput
from app.modules.inventory.service import InventoryService
from app.modules.locations.models import Location
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.users.models import User


def _setup(db):
    user = User(email="f@test.io", hashed_password=hash_password("password123"))
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


def _create(svc, org_id, doc_type, party_id, pid, tax_id, qty=5, warehouse_id=None):
    return svc.create(
        org_id,
        doc_type,
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


def test_sales_order_commits_stock_without_moving_it(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    inv = InventoryService(db)
    order = _create(svc, org_id, DocumentType.SALES_ORDER, party_id, pid, tax_id, qty=5)
    assert order.number.startswith("SO-")

    svc.finalize(org_id, order.id)
    stock = inv.item_stock(org_id, pid)
    assert stock.on_hand == Decimal(20)          # nothing shipped yet
    assert stock.committed == Decimal(5)         # but promised
    assert stock.available == Decimal(15)
    assert order.stock_posted is False


def test_delivery_challan_ships_stock(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    challan = _create(
        svc, org_id, DocumentType.DELIVERY_CHALLAN, party_id, pid, tax_id, qty=5, warehouse_id=loc_id
    )
    assert challan.number.startswith("DC-")
    svc.finalize(org_id, challan.id)
    assert challan.stock_posted is True
    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(15)


def test_order_to_challan_to_invoice_moves_stock_once(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    inv = InventoryService(db)

    order = _create(svc, org_id, DocumentType.SALES_ORDER, party_id, pid, tax_id, qty=5)
    svc.finalize(org_id, order.id)
    assert inv.item_stock(org_id, pid).committed == Decimal(5)

    challan = svc.convert(org_id, order.id, DocumentType.SALES_ORDER, DocumentType.DELIVERY_CHALLAN)
    assert challan.source_document_id == order.id
    assert order.status == DocumentStatus.CLOSED
    # a closed order no longer commits stock
    assert inv.item_stock(org_id, pid).committed == Decimal(0)

    svc.finalize(org_id, challan.id)
    assert inv.item_stock(org_id, pid).on_hand == Decimal(15)

    invoice = svc.convert(
        org_id, challan.id, DocumentType.DELIVERY_CHALLAN, DocumentType.INVOICE
    )
    svc.finalize(org_id, invoice.id)
    # the invoice bills only: stock must not move a second time
    assert invoice.stock_posted is False
    assert inv.item_stock(org_id, pid).on_hand == Decimal(15)
    assert invoice.total == challan.total


def test_order_straight_to_invoice_still_ships(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    order = _create(svc, org_id, DocumentType.SALES_ORDER, party_id, pid, tax_id, qty=4)
    svc.finalize(org_id, order.id)
    invoice = svc.convert(org_id, order.id, DocumentType.SALES_ORDER, DocumentType.INVOICE)
    svc.finalize(org_id, invoice.id)
    # the order never moved stock, so the invoice must
    assert invoice.stock_posted is True
    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(16)


def test_void_only_reverses_what_it_posted(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    inv = InventoryService(db)
    challan = _create(
        svc, org_id, DocumentType.DELIVERY_CHALLAN, party_id, pid, tax_id, qty=5, warehouse_id=loc_id
    )
    svc.finalize(org_id, challan.id)
    invoice = svc.convert(org_id, challan.id, DocumentType.DELIVERY_CHALLAN, DocumentType.INVOICE)
    svc.finalize(org_id, invoice.id)
    assert inv.item_stock(org_id, pid).on_hand == Decimal(15)

    svc.void(org_id, invoice.id)   # billed only -> no stock effect
    assert inv.item_stock(org_id, pid).on_hand == Decimal(15)

    svc.void(org_id, challan.id)   # shipped -> reverses
    assert inv.item_stock(org_id, pid).on_hand == Decimal(20)


def test_cannot_convert_a_draft(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    order = _create(svc, org_id, DocumentType.SALES_ORDER, party_id, pid, tax_id)
    with pytest.raises(BadRequestError):
        svc.convert(org_id, order.id, DocumentType.SALES_ORDER, DocumentType.INVOICE)


def test_invalid_conversion_target(db):
    org_id, loc_id, party_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    challan = _create(
        svc, org_id, DocumentType.DELIVERY_CHALLAN, party_id, pid, tax_id, warehouse_id=loc_id
    )
    svc.finalize(org_id, challan.id)
    with pytest.raises(BadRequestError):
        svc.convert(
            org_id, challan.id, DocumentType.DELIVERY_CHALLAN, DocumentType.DELIVERY_CHALLAN
        )
