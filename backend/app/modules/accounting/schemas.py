from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.accounting.enums import (
    AccountType,
    FiscalYearStatus,
    NormalBalance,
    PeriodStatus,
    VoucherStatus,
    VoucherType,
)


class JournalLineInput(BaseModel):
    account_id: int
    party_id: int | None = None
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    description: str | None = None


class JournalVoucherCreate(BaseModel):
    date: date
    reference_no: str | None = Field(default=None, max_length=50)
    description: str | None = None
    lines: list[JournalLineInput] = Field(min_length=2)


class VoucherLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    party_id: int | None
    line_no: int
    debit: Decimal
    credit: Decimal
    description: str | None


class VoucherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voucher_type: VoucherType
    number: str
    reference_no: str | None
    document_date: date
    posting_date: date
    description: str | None
    total_debit: Decimal
    total_credit: Decimal
    status: VoucherStatus
    reversed_from_id: int | None
    source_type: str | None
    source_id: int | None
    created_at: datetime
    lines: list[VoucherLineRead] = Field(default_factory=list)


class VoucherSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voucher_type: VoucherType
    number: str
    reference_no: str | None
    posting_date: date
    description: str | None
    total_debit: Decimal
    status: VoucherStatus


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    code: str
    name: str
    account_type: AccountType
    normal_balance: NormalBalance
    is_control_account: bool
    is_postable: bool
    is_active: bool
    description: str | None


class AccountCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=150)
    account_type: AccountType
    normal_balance: NormalBalance
    parent_id: int | None = None
    is_postable: bool = True
    description: str | None = None


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    parent_id: int | None = None
    is_active: bool | None = None
    description: str | None = None


class FiscalYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    starts_on: date
    ends_on: date
    status: FiscalYearStatus


class PeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fiscal_year_id: int
    name: str
    period_no: int
    starts_on: date
    ends_on: date
    status: PeriodStatus


class PeriodStatusUpdate(BaseModel):
    status: PeriodStatus
