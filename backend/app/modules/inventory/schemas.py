from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import ListQuery


class StockAdjustInput(BaseModel):
    product_id: int
    location_id: int
    qty_delta: Decimal
    reason: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=255)


class OpeningStockInput(BaseModel):
    product_id: int
    location_id: int
    quantity: Decimal = Field(ge=0)
    note: str | None = Field(default=None, max_length=255)


class StockTransferInput(BaseModel):
    product_id: int
    from_location_id: int
    to_location_id: int
    quantity: Decimal = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)


class OnHandRead(BaseModel):
    quantity: Decimal


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    location_id: int
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
    uom_symbol: str | None = None
    reorder_point: int | None = None
    on_hand: Decimal
    is_low: bool


class StockByLocation(BaseModel):
    location_id: int
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
