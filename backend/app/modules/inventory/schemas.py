from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import ListQuery


class StockAdjustInput(BaseModel):
    product_id: int
    location_id: int
    bin_id: int | None = None
    lot_id: int | None = None
    serial_numbers: list[str] = Field(default_factory=list)
    mode: Literal["quantity", "value"] = "quantity"
    qty_delta: Decimal = Decimal("0")
    value_delta: Decimal | None = None
    unit_cost: Decimal | None = None
    account_id: int | None = None
    date: date_cls | None = None
    reason: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=255)


class StockTransferInput(BaseModel):
    product_id: int
    from_location_id: int
    to_location_id: int
    from_bin_id: int | None = None
    to_bin_id: int | None = None
    lot_id: int | None = None
    serial_numbers: list[str] = Field(default_factory=list)
    quantity: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)


class OpeningStockLineInput(BaseModel):
    location_id: int
    bin_id: int | None = None
    lot_id: int | None = None
    lot_number: str | None = Field(default=None, max_length=100)
    manufactured_date: date_cls | None = None
    expiry_date: date_cls | None = None
    serial_numbers: list[str] = Field(default_factory=list)
    quantity: Decimal = Field(ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)


class OpeningStockInput(BaseModel):
    product_id: int
    date: date_cls | None = None
    entries: list[OpeningStockLineInput] = Field(default_factory=list)


class OpeningStockLocationRead(BaseModel):
    location_id: int
    bin_id: int | None = None
    lot_id: int | None = None
    serial_numbers: list[str] = Field(default_factory=list)
    quantity: Decimal
    unit_cost: Decimal | None = None
    value: Decimal


class OpeningStockRead(BaseModel):
    product_id: int
    editable: bool
    entries: list[OpeningStockLocationRead] = Field(default_factory=list)


class OnHandRead(BaseModel):
    quantity: Decimal


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    location_id: int
    bin_id: int | None = None
    lot_id: int | None = None
    qty_delta: Decimal
    type: str
    reason: str | None = None
    note: str | None = None
    created_at: datetime


class ReasonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ReasonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_system: bool


class InventoryListQuery(ListQuery):
    location_id: int | None = None
    low_stock: bool | None = None


class InventoryItemRead(BaseModel):
    id: int
    name: str
    sku: str | None = None
    is_variant: bool = False
    tracking_mode: Literal["none", "lot", "serial"] = "none"
    uom_symbol: str | None = None
    reorder_point: int | None = None
    on_hand: Decimal
    is_low: bool


class StockByLocation(BaseModel):
    location_id: int
    quantity: Decimal


class StockByBin(BaseModel):
    location_id: int
    bin_id: int | None = None
    quantity: Decimal


class StockByLot(BaseModel):
    location_id: int
    bin_id: int | None = None
    lot_id: int
    quantity: Decimal


class ItemStockRead(BaseModel):
    on_hand: Decimal
    opening_stock: Decimal = Decimal("0")
    committed: Decimal = Decimal("0")
    available: Decimal = Decimal("0")
    to_be_shipped: Decimal = Decimal("0")
    to_be_received: Decimal = Decimal("0")
    to_be_invoiced: Decimal = Decimal("0")
    to_be_billed: Decimal = Decimal("0")
    by_location: list[StockByLocation] = Field(default_factory=list)
    by_bin: list[StockByBin] = Field(default_factory=list)
    by_lot: list[StockByLot] = Field(default_factory=list)


class BinCreate(BaseModel):
    location_id: int
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True


class BinUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class BinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    code: str
    name: str
    is_active: bool
    created_at: datetime


class StockLotCreate(BaseModel):
    product_id: int
    lot_number: str = Field(min_length=1, max_length=100)
    manufactured_date: date_cls | None = None
    expiry_date: date_cls | None = None
    note: str | None = Field(default=None, max_length=255)


class StockLotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    lot_number: str
    manufactured_date: date_cls | None = None
    expiry_date: date_cls | None = None
    note: str | None = None
    is_active: bool


class LotStockRead(StockLotRead):
    quantity: Decimal = Decimal("0")


class SerialUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    serial_number: str
    status: str
    location_id: int | None = None
    bin_id: int | None = None
