from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.pagination import ListQuery
from app.modules.inventory.schemas import StockLotRead
from app.modules.salespeople.schemas import SalespersonSummary


class LotAllocationInput(BaseModel):
    lot_id: int | None = None
    lot_number: str | None = Field(default=None, max_length=100)
    manufactured_date: date | None = None
    expiry_date: date | None = None
    quantity: Decimal = Field(gt=0)


class LotAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lot_id: int
    quantity: Decimal
    lot: StockLotRead


class DocumentLineSerialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    serial_number: str
    serial_unit_id: int | None = None


class DocumentLineInput(BaseModel):
    product_id: int | None = None
    tracking_mode: Literal["none", "lot", "serial"] = "none"
    bin_id: int | None = None
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    discount_type: Literal["amount", "percent"] = "amount"
    discount_value: Decimal = Field(default=Decimal("0"), ge=0)
    tax_rate_id: int | None = None
    lot_allocations: list[LotAllocationInput] = Field(default_factory=list)
    serial_numbers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cap_percentage(self) -> DocumentLineInput:
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValueError("A percentage discount cannot exceed 100%")
        return self


class DocumentCreate(BaseModel):
    salesperson_id: int | None = None
    party_id: int | None = None
    contact_name: str | None = Field(default=None, max_length=150)
    contact_phone: str | None = Field(default=None, max_length=40)
    paid_through_account_id: int | None = None
    number: str | None = Field(default=None, max_length=40)
    issue_date: date | None = None
    due_date: date | None = None
    expected_shipment_date: date | None = None
    reference: str | None = Field(default=None, max_length=100)
    warehouse_id: int | None = None
    notes: str | None = None
    terms: str | None = None
    shipping: Decimal = Field(default=Decimal("0"), ge=0)
    adjustment: Decimal = Field(default=Decimal("0"))
    fbr_sale_origin: str | None = Field(default=None, max_length=50)
    fbr_sale_destination: str | None = Field(default=None, max_length=50)
    fbr_scenario_id: str | None = Field(default=None, max_length=20)
    fbr_reason: str | None = Field(default=None, max_length=100)
    fbr_reason_remarks: str | None = Field(default=None, max_length=255)
    lines: list[DocumentLineInput] = Field(min_length=1)


class DocumentUpdate(BaseModel):
    salesperson_id: int | None = None
    party_id: int | None = None
    number: str | None = Field(default=None, max_length=40)
    issue_date: date | None = None
    due_date: date | None = None
    expected_shipment_date: date | None = None
    reference: str | None = None
    warehouse_id: int | None = None
    notes: str | None = None
    terms: str | None = None
    shipping: Decimal | None = None
    adjustment: Decimal | None = None
    fbr_sale_origin: str | None = Field(default=None, max_length=50)
    fbr_sale_destination: str | None = Field(default=None, max_length=50)
    fbr_scenario_id: str | None = Field(default=None, max_length=20)
    fbr_reason: str | None = Field(default=None, max_length=100)
    fbr_reason_remarks: str | None = Field(default=None, max_length=255)
    lines: list[DocumentLineInput] | None = None


class PartySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None


class RelatedDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    number: str
    status: str


class DocumentLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None = None
    bin_id: int | None = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_type: str
    discount_value: Decimal
    discount: Decimal
    tax_rate_id: int | None = None
    tax_amount: Decimal
    further_tax: Decimal = Decimal("0")
    line_total: Decimal
    sort_order: int
    lot_allocations: list[LotAllocationRead] = Field(default_factory=list)
    serials: list[DocumentLineSerialRead] = Field(default_factory=list)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    number: str
    status: str
    payment_status: str
    stock_posted: bool = False
    party_id: int | None = None
    party: PartySummary | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    paid_through_account_id: int | None = None
    buyer_registered: bool = False
    credit_notes: list[RelatedDocument] = []
    warehouse_id: int | None = None
    issue_date: date
    due_date: date | None = None
    expected_shipment_date: date | None = None
    reference: str | None = None
    currency: str
    notes: str | None = None
    terms: str | None = None
    billing_address: dict | None = None
    shipping_address: dict | None = None
    fbr_sale_origin: str | None = None
    fbr_sale_destination: str | None = None
    fbr_scenario_id: str | None = None
    fbr_reason: str | None = None
    fbr_reason_remarks: str | None = None
    fbr_invoice_number: str | None = None
    fbr_submitted_at: datetime | None = None
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    further_tax_total: Decimal = Decimal("0")
    shipping: Decimal
    adjustment: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_credited: Decimal
    balance_due: Decimal
    salesperson: SalespersonSummary | None = None
    commission_rate: Decimal
    commission_amount: Decimal
    source_document_id: int | None = None
    created_at: datetime
    updated_at: datetime
    lines: list[DocumentLineRead]

    @computed_field
    @property
    def fbr_qr(self) -> str | None:
        if not self.fbr_invoice_number:
            return None
        from app.modules.fbr.qr import qr_data_uri

        return qr_data_uri(self.fbr_invoice_number)


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    status: str
    payment_status: str
    issue_date: date
    due_date: date | None = None
    expected_shipment_date: date | None = None
    currency: str
    total: Decimal
    amount_paid: Decimal
    amount_credited: Decimal
    balance_due: Decimal
    party: PartySummary | None = None
    salesperson: SalespersonSummary | None = None


class DocumentConvertInput(BaseModel):
    target: Literal["delivery_challan", "invoice", "credit_note", "goods_receipt", "bill"]


class DocumentListQuery(ListQuery):
    status: str | None = None
    payment_status: str | None = None
    party_id: int | None = None


class TaxRateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    rate: Decimal = Field(ge=0, le=100)
    is_active: bool = True


class TaxRateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    rate: Decimal | None = Field(default=None, ge=0, le=100)
    is_active: bool | None = None


class TaxRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    rate: Decimal
    is_active: bool
    is_system: bool


class SellableItemRead(BaseModel):
    id: int
    name: str
    sku: str | None = None
    description: str | None = None
    image_url: str | None = None
    uom_symbol: str | None = None
    sale_price: Decimal | None = None
    purchase_price: Decimal | None = None
    fbr_rate: str | None = None
    track_inventory: bool = False
    tracking_mode: str = "none"
    stock: Decimal | None = None
