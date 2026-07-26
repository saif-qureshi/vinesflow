from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.modules.accounting.enums import (
    AccountType,
    FiscalYearStatus,
    NormalBalance,
    PeriodStatus,
)


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
