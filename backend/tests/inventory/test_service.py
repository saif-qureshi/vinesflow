from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestError, ConflictError
from app.core.security import hash_password
from app.modules.inventory.models import StockMovement
from app.modules.inventory.schemas import (
    BinCreate,
    InventoryListQuery,
    ReasonCreate,
    StockAdjustInput,
    StockTransferInput,
)
from app.modules.inventory.service import InventoryService
from app.modules.locations.models import Location
from app.modules.locations.schemas import LocationCreate
from app.modules.locations.service import LocationService
from app.modules.orgs.service import OrgService
from app.modules.products.models import Product
from app.modules.users.models import User


def _setup(db, *, variable=False, reorder=5):
    user = User(email="i@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    loc = db.scalar(select(Location).where(Location.org_id == org.id))
    product = Product(
        org_id=org.id,
        name="Widget",
        type="variable" if variable else "single",
        track_inventory=True,
        reorder_point=reorder,
    )
    db.add(product)
    db.flush()
    return org.id, loc.id, product.id


def test_adjust_updates_on_hand(db):
    org_id, loc_id, pid = _setup(db)
    svc = InventoryService(db)
    svc.adjust(org_id, StockAdjustInput(product_id=pid, location_id=loc_id, qty_delta=Decimal(10)))
    assert svc.item_stock(org_id, pid).on_hand == Decimal(10)
    svc.adjust(org_id, StockAdjustInput(product_id=pid, location_id=loc_id, qty_delta=Decimal(-3)))
    assert svc.item_stock(org_id, pid).on_hand == Decimal(7)


def test_transfer_moves_between_locations(db):
    org_id, loc_id, pid = _setup(db)
    svc = InventoryService(db)
    loc_b = LocationService(db).create(org_id, LocationCreate(name="Store B"))
    svc.adjust(org_id, StockAdjustInput(product_id=pid, location_id=loc_id, qty_delta=Decimal(10), reason="Opening balance"))
    svc.transfer(
        org_id,
        StockTransferInput(product_id=pid, from_location_id=loc_id, to_location_id=loc_b.id, quantity=Decimal(4)),
    )
    stock = svc.item_stock(org_id, pid)
    by_loc = {b.location_id: b.quantity for b in stock.by_location}
    assert stock.on_hand == Decimal(10)
    assert by_loc[loc_id] == Decimal(6)
    assert by_loc[loc_b.id] == Decimal(4)


def test_transfer_insufficient_stock_raises(db):
    org_id, loc_id, pid = _setup(db)
    svc = InventoryService(db)
    loc_b = LocationService(db).create(org_id, LocationCreate(name="Store B"))
    with pytest.raises(BadRequestError):
        svc.transfer(
            org_id,
            StockTransferInput(product_id=pid, from_location_id=loc_id, to_location_id=loc_b.id, quantity=Decimal(1)),
        )


def test_document_movement_cannot_create_negative_stock(db):
    org_id, loc_id, pid = _setup(db)
    svc = InventoryService(db)

    with pytest.raises(BadRequestError, match="Not enough stock"):
        svc.post_document_movement(
            org_id=org_id,
            product_id=pid,
            location_id=loc_id,
            qty_delta=Decimal("-1"),
            type_="sale",
            reference_type="invoice",
            reference_id=1,
        )

    assert svc.on_hand(org_id, pid, loc_id) == Decimal(0)
    assert db.scalar(select(StockMovement.id)) is None


def test_variable_product_requires_variant(db):
    org_id, loc_id, pid = _setup(db, variable=True)
    with pytest.raises(BadRequestError):
        InventoryService(db).adjust(
            org_id, StockAdjustInput(product_id=pid, location_id=loc_id, qty_delta=Decimal(1))
        )


def test_low_stock_filter(db):
    org_id, loc_id, pid = _setup(db, reorder=5)
    svc = InventoryService(db)
    svc.adjust(org_id, StockAdjustInput(product_id=pid, location_id=loc_id, qty_delta=Decimal(3)))
    items, _, _ = svc.list(org_id, InventoryListQuery(low_stock=True))
    assert any(i.id == pid and i.is_low for i in items)


def test_reasons_seeded_and_custom(db):
    org_id, _, _ = _setup(db)
    svc = InventoryService(db)
    names = [r.name for r in svc.list_reasons(org_id)]
    assert "Damaged goods" in names
    svc.create_reason(org_id, ReasonCreate(name="Custom reason"))
    assert "Custom reason" in [r.name for r in svc.list_reasons(org_id)]


def test_cannot_delete_system_reason(db):
    org_id, _, _ = _setup(db)
    svc = InventoryService(db)
    system = next(r for r in svc.list_reasons(org_id) if r.is_system)
    with pytest.raises(ConflictError):
        svc.delete_reason(org_id, system.id)


def test_on_hand_lookup(db):
    org_id, loc_id, pid = _setup(db)
    svc = InventoryService(db)
    svc.adjust(
        org_id,
        StockAdjustInput(product_id=pid, location_id=loc_id, qty_delta=Decimal(5), reason="Damaged goods"),
    )
    assert svc.on_hand(org_id, pid, loc_id) == Decimal(5)


def test_stock_is_tracked_by_bin_and_aggregated_by_warehouse(db):
    org_id, loc_id, pid = _setup(db)
    svc = InventoryService(db)
    bin_a = svc.bins.create(org_id, BinCreate(location_id=loc_id, code="A-01", name="Rack A"))
    bin_b = svc.bins.create(org_id, BinCreate(location_id=loc_id, code="B-01", name="Rack B"))

    svc.adjust(
        org_id,
        StockAdjustInput(
            product_id=pid, location_id=loc_id, bin_id=bin_a.id, qty_delta=Decimal(10)
        ),
    )
    svc.adjust(
        org_id,
        StockAdjustInput(product_id=pid, location_id=loc_id, bin_id=bin_b.id, qty_delta=Decimal(4)),
    )

    assert svc.on_hand(org_id, pid, loc_id) == Decimal(14)
    assert svc.on_hand(org_id, pid, loc_id, bin_a.id) == Decimal(10)

    svc.transfer(
        org_id,
        StockTransferInput(
            product_id=pid,
            from_location_id=loc_id,
            to_location_id=loc_id,
            from_bin_id=bin_a.id,
            to_bin_id=bin_b.id,
            quantity=Decimal(3),
        ),
    )

    stock = svc.item_stock(org_id, pid)
    by_bin = {row.bin_id: row.quantity for row in stock.by_bin}
    assert stock.on_hand == Decimal(14)
    assert stock.by_location[0].quantity == Decimal(14)
    assert by_bin == {bin_a.id: Decimal(7), bin_b.id: Decimal(7)}

    with pytest.raises(BadRequestError, match="Not enough stock"):
        svc.transfer(
            org_id,
            StockTransferInput(
                product_id=pid,
                from_location_id=loc_id,
                to_location_id=loc_id,
                from_bin_id=bin_a.id,
                to_bin_id=bin_b.id,
                quantity=Decimal(8),
            ),
        )
