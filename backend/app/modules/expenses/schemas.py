from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import ListQuery


class ExpenseLineInput(BaseModel):
    account_id: int
    description: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(gt=0)


class ExpenseCreate(BaseModel):
    expense_date: date | None = None
    paid_through_account_id: int
    vendor_id: int | None = None
    customer_id: int | None = None
    is_tax_inclusive: bool = False
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    reference_no: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    lines: list[ExpenseLineInput] = Field(min_length=1)


class ExpenseUpdate(BaseModel):
    expense_date: date | None = None
    paid_through_account_id: int | None = None
    vendor_id: int | None = None
    customer_id: int | None = None
    is_tax_inclusive: bool | None = None
    tax_amount: Decimal | None = Field(default=None, ge=0)
    reference_no: str | None = None
    notes: str | None = Field(default=None, max_length=500)
    lines: list[ExpenseLineInput] | None = Field(default=None, min_length=1)


class PartySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ExpenseLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    line_no: int
    description: str | None = None
    amount: Decimal


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    status: str
    expense_date: date
    paid_through_account_id: int
    vendor_id: int | None = None
    vendor_name: str | None = None
    vendor: PartySummary | None = None
    customer_id: int | None = None
    is_tax_inclusive: bool
    reference_no: str | None = None
    notes: str | None = None
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    submitted_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime
    lines: list[ExpenseLineRead]


class ExpenseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    status: str
    expense_date: date
    vendor_name: str | None = None
    reference_no: str | None = None
    total: Decimal


class ExpenseListQuery(ListQuery):
    status: str | None = None
    vendor_id: int | None = None
