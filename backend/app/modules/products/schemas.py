from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import ListQuery
from app.modules.attributes.schemas import AttributeValueSummary
from app.modules.brands.schemas import BrandSummary
from app.modules.categories.schemas import CategorySummary
from app.modules.manufacturers.schemas import ManufacturerSummary
from app.modules.media.schemas import MediaCreate, MediaRead
from app.modules.uoms.schemas import UomSummary


class ItemSalesPoint(BaseModel):
    label: str
    sales: Decimal


Nature = Literal["good", "service"]
ProductType = Literal["single", "variable"]
TrackingMode = Literal["none", "lot", "serial"]


class ProductListQuery(ListQuery):
    """Pagination + search + product filters, injected as one query object."""

    category_id: int | None = None
    brand_id: int | None = None
    manufacturer_id: int | None = None
    nature: Nature | None = None
    type: ProductType | None = None
    is_active: bool | None = None


# Attribute definitions are supplied inline with the product (by name); the
# service upserts the org-level attribute/value rows and links them.
class VariantAttributeInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    options: list[str] = Field(default_factory=list)


class VariantAttributeRead(BaseModel):
    name: str
    options: list[str]


class VariantInput(BaseModel):
    id: int | None = None
    options: dict[str, str]
    name: str | None = None
    sku: str | None = Field(default=None, max_length=100)
    barcode: str | None = Field(default=None, max_length=64)
    sale_price: float | None = Field(default=None, ge=0)
    purchase_price: float | None = Field(default=None, ge=0)
    is_active: bool = True


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    values: list[AttributeValueSummary] = Field(default_factory=list)
    sku: str | None = None
    barcode: str | None = None
    sale_price: float | None = None
    purchase_price: float | None = None
    is_active: bool


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    nature: Nature = "good"
    type: ProductType = "single"
    sku: str | None = Field(default=None, max_length=100)
    barcode: str | None = Field(default=None, max_length=64)
    category_id: int | None = None
    brand_id: int | None = None
    manufacturer_id: int | None = None
    uom_id: int | None = None
    sale_price: float | None = Field(default=None, ge=0)
    purchase_price: float | None = Field(default=None, ge=0)
    track_inventory: bool = False
    tracking_mode: TrackingMode = "none"
    reorder_point: int | None = Field(default=None, ge=0)
    is_active: bool = True
    hs_code: str | None = Field(default=None, max_length=20)
    uom_code: str | None = Field(default=None, max_length=20)
    sale_type_code: str | None = Field(default=None, max_length=20)
    tax_rate_code: str | None = Field(default=None, max_length=20)
    sro_schedule_code: str | None = Field(default=None, max_length=20)
    sro_item_serial: str | None = Field(default=None, max_length=30)


class ProductCreate(ProductBase):
    media: list[MediaCreate] = Field(default_factory=list)
    variant_attributes: list[VariantAttributeInput] = Field(default_factory=list)
    variants: list[VariantInput] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    nature: Nature | None = None
    type: ProductType | None = None
    sku: str | None = Field(default=None, max_length=100)
    barcode: str | None = Field(default=None, max_length=64)
    category_id: int | None = None
    brand_id: int | None = None
    manufacturer_id: int | None = None
    uom_id: int | None = None
    sale_price: float | None = Field(default=None, ge=0)
    purchase_price: float | None = Field(default=None, ge=0)
    track_inventory: bool | None = None
    tracking_mode: TrackingMode | None = None
    reorder_point: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    hs_code: str | None = Field(default=None, max_length=20)
    uom_code: str | None = Field(default=None, max_length=20)
    sale_type_code: str | None = Field(default=None, max_length=20)
    tax_rate_code: str | None = Field(default=None, max_length=20)
    sro_schedule_code: str | None = Field(default=None, max_length=20)
    sro_item_serial: str | None = Field(default=None, max_length=30)
    media: list[MediaCreate] | None = None
    variant_attributes: list[VariantAttributeInput] | None = None
    variants: list[VariantInput] | None = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    nature: str
    type: str
    sku: str | None = None
    barcode: str | None = None
    sale_price: float | None = None
    purchase_price: float | None = None
    track_inventory: bool
    tracking_mode: str
    reorder_point: int | None = None
    is_active: bool
    hs_code: str | None = None
    uom_code: str | None = None
    sale_type_code: str | None = None
    tax_rate_code: str | None = None
    sro_schedule_code: str | None = None
    sro_item_serial: str | None = None
    category: CategorySummary | None = None
    brand: BrandSummary | None = None
    manufacturer: ManufacturerSummary | None = None
    uom: UomSummary | None = None
    media: list[MediaRead] = Field(default_factory=list)
    variant_attributes: list[VariantAttributeRead] = Field(default_factory=list)
    variants: list[VariantRead] = Field(default_factory=list)
    created_at: datetime
