from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError
from app.core.security import hash_password
from app.modules.documents.enums import DocumentType
from app.modules.documents.models import TaxRate
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput, LotAllocationInput
from app.modules.documents.service import DocumentService
from app.modules.inventory.models import SerialUnit, StockLot
from app.modules.inventory.schemas import (
    OpeningStockInput,
    OpeningStockLineInput,
    StockAdjustInput,
    StockTransferInput,
)
from app.modules.inventory.service import InventoryService
from app.modules.inventory.tracking_service import TrackingService
from app.modules.locations.models import Location
from app.modules.locations.schemas import LocationCreate
from app.modules.locations.service import LocationService
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.users.models import User


def _setup(db, tracking_mode: str):
    user = User(
        email=f"{tracking_mode}@test.io", hashed_password=hash_password("password123")
    )
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Tracked Co")
    db.flush()
    location = db.scalar(select(Location).where(Location.org_id == org.id))
    vendor = Party(org_id=org.id, is_vendor=True, name="Supplier")
    customer = Party(org_id=org.id, is_customer=True, name="Customer")
    product = Product(
        org_id=org.id,
        name=f"{tracking_mode.title()} Item",
        type="single",
        nature="good",
        track_inventory=True,
        tracking_mode=tracking_mode,
        purchase_price=Decimal("10"),
        sale_price=Decimal("20"),
    )
    db.add_all([vendor, customer, product])
    db.flush()
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "Exempt"))
    return org.id, location.id, vendor.id, customer.id, product.id, tax.id


def _document(
    service,
    org_id,
    doc_type,
    party_id,
    location_id,
    product_id,
    tax_id,
    quantity,
    *,
    lots=None,
    serials=None,
):
    return service.create(
        org_id,
        doc_type,
        DocumentCreate(
            party_id=party_id,
            warehouse_id=location_id,
            lines=[
                DocumentLineInput(
                    product_id=product_id,
                    description="Tracked item",
                    quantity=Decimal(quantity),
                    unit_price=Decimal("10"),
                    tax_rate_id=tax_id,
                    lot_allocations=lots or [],
                    serial_numbers=serials or [],
                )
            ],
        ),
    )


def test_lot_receipt_and_dispatch_update_exact_lot(db):
    org_id, location_id, vendor_id, customer_id, product_id, tax_id = _setup(db, "lot")
    documents = DocumentService(db)
    receipt = _document(
        documents,
        org_id,
        DocumentType.GOODS_RECEIPT,
        vendor_id,
        location_id,
        product_id,
        tax_id,
        10,
        lots=[
            LotAllocationInput(
                lot_number="batch-001",
                expiry_date=date.today() + timedelta(days=90),
                quantity=Decimal(10),
            )
        ],
    )
    documents.finalize(org_id, receipt.id)
    lot = db.scalar(select(StockLot).where(StockLot.product_id == product_id))
    assert lot.lot_number == "BATCH-001"
    assert InventoryService(db).on_hand_in_lot(
        org_id, product_id, location_id, None, lot.id
    ) == Decimal(10)

    challan = _document(
        documents,
        org_id,
        DocumentType.DELIVERY_CHALLAN,
        customer_id,
        location_id,
        product_id,
        tax_id,
        3,
        lots=[LotAllocationInput(lot_id=lot.id, quantity=Decimal(3))],
    )
    documents.finalize(org_id, challan.id)
    assert InventoryService(db).on_hand_in_lot(
        org_id, product_id, location_id, None, lot.id
    ) == Decimal(7)
    listed = TrackingService(db).list_lots(org_id, product_id, location_id=location_id)
    assert listed[0].quantity == Decimal(7)


def test_expired_lot_cannot_be_dispatched(db):
    org_id, location_id, vendor_id, customer_id, product_id, tax_id = _setup(db, "lot")
    documents = DocumentService(db)
    receipt = _document(
        documents,
        org_id,
        DocumentType.GOODS_RECEIPT,
        vendor_id,
        location_id,
        product_id,
        tax_id,
        2,
        lots=[
            LotAllocationInput(
                lot_number="expired",
                expiry_date=date.today() - timedelta(days=1),
                quantity=Decimal(2),
            )
        ],
    )
    documents.finalize(org_id, receipt.id)
    lot_id = receipt.lines[0].lot_allocations[0].lot_id
    challan = _document(
        documents,
        org_id,
        DocumentType.DELIVERY_CHALLAN,
        customer_id,
        location_id,
        product_id,
        tax_id,
        1,
        lots=[LotAllocationInput(lot_id=lot_id, quantity=Decimal(1))],
    )
    with pytest.raises(BadRequestError, match="expired"):
        documents.finalize(org_id, challan.id)


def test_serial_receipt_dispatch_and_void_restore_unit(db):
    org_id, location_id, vendor_id, customer_id, product_id, tax_id = _setup(db, "serial")
    documents = DocumentService(db)
    receipt = _document(
        documents,
        org_id,
        DocumentType.GOODS_RECEIPT,
        vendor_id,
        location_id,
        product_id,
        tax_id,
        2,
        serials=[" sn-001 ", "SN-002"],
    )
    documents.finalize(org_id, receipt.id)
    units = list(db.scalars(select(SerialUnit).order_by(SerialUnit.serial_number)))
    assert [(unit.serial_number, unit.status) for unit in units] == [
        ("SN-001", "in_stock"),
        ("SN-002", "in_stock"),
    ]

    challan = _document(
        documents,
        org_id,
        DocumentType.DELIVERY_CHALLAN,
        customer_id,
        location_id,
        product_id,
        tax_id,
        1,
        serials=["SN-001"],
    )
    documents.finalize(org_id, challan.id)
    first = db.scalar(select(SerialUnit).where(SerialUnit.serial_number == "SN-001"))
    assert first.status == "sold"
    assert first.location_id is None

    documents.void(org_id, challan.id)
    assert first.status == "in_stock"
    assert first.location_id == location_id


def test_lot_opening_stock_and_transfer_keep_lot_identity(db):
    org_id, location_id, _, _, product_id, _ = _setup(db, "lot")
    service = InventoryService(db)
    destination = LocationService(db).create(org_id, LocationCreate(name="Secondary"))

    service.set_opening_stock(
        org_id,
        OpeningStockInput(
            product_id=product_id,
            entries=[
                OpeningStockLineInput(
                    location_id=location_id,
                    lot_number="opening-001",
                    expiry_date=date.today() + timedelta(days=180),
                    quantity=Decimal(5),
                )
            ],
        ),
    )
    lot = db.scalar(select(StockLot).where(StockLot.product_id == product_id))
    service.transfer(
        org_id,
        StockTransferInput(
            product_id=product_id,
            from_location_id=location_id,
            to_location_id=destination.id,
            lot_id=lot.id,
            quantity=Decimal(2),
        ),
    )

    assert service.on_hand_in_lot(
        org_id, product_id, location_id, None, lot.id
    ) == Decimal(3)
    assert service.on_hand_in_lot(
        org_id, product_id, destination.id, None, lot.id
    ) == Decimal(2)


def test_serial_adjustment_and_transfer_move_selected_units(db):
    org_id, location_id, _, _, product_id, _ = _setup(db, "serial")
    service = InventoryService(db)
    destination = LocationService(db).create(org_id, LocationCreate(name="Secondary"))
    service.adjust(
        org_id,
        StockAdjustInput(
            product_id=product_id,
            location_id=location_id,
            qty_delta=Decimal(2),
            serial_numbers=["SER-1", "SER-2"],
        ),
    )
    service.transfer(
        org_id,
        StockTransferInput(
            product_id=product_id,
            from_location_id=location_id,
            to_location_id=destination.id,
            quantity=Decimal(1),
            serial_numbers=["SER-2"],
        ),
    )

    first = db.scalar(select(SerialUnit).where(SerialUnit.serial_number == "SER-1"))
    second = db.scalar(select(SerialUnit).where(SerialUnit.serial_number == "SER-2"))
    assert first.location_id == location_id
    assert second.location_id == destination.id
