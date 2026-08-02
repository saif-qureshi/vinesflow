from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError
from app.core.security import hash_password
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import TaxRate
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput, DocumentUpdate
from app.modules.documents.service import DocumentService
from app.modules.inventory.schemas import BinCreate, StockAdjustInput
from app.modules.inventory.service import InventoryService
from app.modules.locations.models import Location
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.users.models import User


def _setup(db):
    user = User(email="pf@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    loc = db.scalar(select(Location).where(Location.org_id == org.id))
    vendor = Party(org_id=org.id, is_vendor=True, name="Supplier")
    product = Product(
        org_id=org.id, name="Widget", type="single", track_inventory=True,
        sale_price=Decimal("100"), purchase_price=Decimal("60"),
    )
    db.add_all([vendor, product])
    db.flush()
    InventoryService(db).adjust(
        org.id, StockAdjustInput(product_id=product.id, location_id=loc.id, qty_delta=Decimal(10), reason="Opening balance")
    )
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "Exempt"))
    return org.id, loc.id, vendor.id, product.id, tax.id


def _create(svc, org_id, doc_type, party_id, pid, tax_id, qty=6, warehouse_id=None):
    return svc.create(
        org_id,
        doc_type,
        DocumentCreate(
            party_id=party_id,
            warehouse_id=warehouse_id,
            lines=[
                DocumentLineInput(
                    product_id=pid, description="Widget", quantity=Decimal(qty),
                    unit_price=Decimal("60"), tax_rate_id=tax_id,
                )
            ],
        ),
    )


def test_purchase_order_is_incoming_without_moving_stock(db):
    org_id, loc_id, vendor_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    inv = InventoryService(db)
    order = _create(svc, org_id, DocumentType.PURCHASE_ORDER, vendor_id, pid, tax_id, qty=6)
    assert order.number.startswith("PO-")

    svc.finalize(org_id, order.id)
    stock = inv.item_stock(org_id, pid)
    assert stock.on_hand == Decimal(10)          # nothing received yet
    assert stock.to_be_received == Decimal(6)    # but expected
    assert stock.committed == Decimal(0)         # purchases never commit
    assert order.stock_posted is False


def test_goods_receipt_receives_stock(db):
    org_id, loc_id, vendor_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    grn = _create(
        svc, org_id, DocumentType.GOODS_RECEIPT, vendor_id, pid, tax_id, qty=6, warehouse_id=loc_id
    )
    assert grn.number.startswith("GRN-")
    svc.finalize(org_id, grn.id)
    assert grn.stock_posted is True
    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(16)


def test_purchase_order_does_not_accept_bin_and_receipt_selects_it(db):
    org_id, loc_id, vendor_id, pid, tax_id = _setup(db)
    inventory = InventoryService(db)
    bin_ = inventory.bins.create(
        org_id, BinCreate(location_id=loc_id, code="A-01", name="Rack A")
    )
    svc = DocumentService(db)

    with pytest.raises(BadRequestError, match="not on orders"):
        svc.create(
            org_id,
            DocumentType.PURCHASE_ORDER,
            DocumentCreate(
                party_id=vendor_id,
                warehouse_id=loc_id,
                lines=[
                    DocumentLineInput(
                        product_id=pid,
                        bin_id=bin_.id,
                        description="Widget",
                        quantity=Decimal(6),
                        unit_price=Decimal(60),
                        tax_rate_id=tax_id,
                    )
                ],
            ),
        )

    order = _create(
        svc,
        org_id,
        DocumentType.PURCHASE_ORDER,
        vendor_id,
        pid,
        tax_id,
        warehouse_id=loc_id,
    )
    svc.finalize(org_id, order.id)
    receipt = svc.convert(
        org_id, order.id, DocumentType.PURCHASE_ORDER, DocumentType.GOODS_RECEIPT
    )
    assert receipt.lines[0].bin_id is None

    svc.update(
        org_id,
        receipt.id,
        DocumentType.GOODS_RECEIPT,
        DocumentUpdate(
            lines=[
                DocumentLineInput(
                    product_id=pid,
                    bin_id=bin_.id,
                    description="Widget",
                    quantity=Decimal(6),
                    unit_price=Decimal(60),
                    tax_rate_id=tax_id,
                )
            ]
        ),
    )
    svc.finalize(org_id, receipt.id)
    assert inventory.on_hand(org_id, pid, loc_id, bin_.id) == Decimal(6)


def test_po_to_grn_to_bill_receives_once(db):
    org_id, loc_id, vendor_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    inv = InventoryService(db)

    order = _create(svc, org_id, DocumentType.PURCHASE_ORDER, vendor_id, pid, tax_id, qty=6)
    svc.finalize(org_id, order.id)
    assert inv.item_stock(org_id, pid).to_be_received == Decimal(6)

    grn = svc.convert(org_id, order.id, DocumentType.PURCHASE_ORDER, DocumentType.GOODS_RECEIPT)
    assert order.status == DocumentStatus.SENT
    assert inv.item_stock(org_id, pid).to_be_received == Decimal(6)

    svc.finalize(org_id, grn.id)
    assert order.status == DocumentStatus.CLOSED
    assert inv.item_stock(org_id, pid).to_be_received == Decimal(0)
    assert inv.item_stock(org_id, pid).on_hand == Decimal(16)

    bill = svc.convert(org_id, grn.id, DocumentType.GOODS_RECEIPT, DocumentType.BILL)
    svc.finalize(org_id, bill.id)
    # the bill bills only: stock must not be received twice
    assert bill.stock_posted is False
    assert inv.item_stock(org_id, pid).on_hand == Decimal(16)


def test_po_straight_to_bill_still_receives(db):
    org_id, loc_id, vendor_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    order = _create(svc, org_id, DocumentType.PURCHASE_ORDER, vendor_id, pid, tax_id, qty=3)
    svc.finalize(org_id, order.id)
    bill = svc.convert(org_id, order.id, DocumentType.PURCHASE_ORDER, DocumentType.BILL)
    assert order.status == DocumentStatus.SENT
    svc.finalize(org_id, bill.id)
    assert order.status == DocumentStatus.CLOSED
    assert bill.stock_posted is True
    assert InventoryService(db).item_stock(org_id, pid).on_hand == Decimal(13)


def test_bill_from_grn_is_still_payable(db):
    org_id, loc_id, vendor_id, pid, tax_id = _setup(db)
    svc = DocumentService(db)
    grn = _create(
        svc, org_id, DocumentType.GOODS_RECEIPT, vendor_id, pid, tax_id, qty=2, warehouse_id=loc_id
    )
    svc.finalize(org_id, grn.id)
    bill = svc.convert(org_id, grn.id, DocumentType.GOODS_RECEIPT, DocumentType.BILL)
    svc.finalize(org_id, bill.id)
    assert bill.total == Decimal("120")
    assert bill.payment_status == "unpaid"
