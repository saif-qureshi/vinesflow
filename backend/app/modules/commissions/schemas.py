from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import ListQuery
from app.modules.salespeople.schemas import SalespersonSummary


class CommissionPayoutCreate(BaseModel):
    salesperson_id: int
    payout_date: date | None = None
    amount: Decimal = Field(gt=0)
    paid_through_account_id: int
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class CommissionPayoutUpdate(BaseModel):
    salesperson_id: int | None = None
    payout_date: date | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    paid_through_account_id: int | None = None
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class CommissionPayoutListQuery(ListQuery):
    salesperson_id: int | None = None
    status: str | None = None


class CommissionPayoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    status: str
    salesperson: SalespersonSummary
    payout_date: date
    amount: Decimal
    paid_through_account_id: int
    reference: str | None = None
    notes: str | None = None
    submitted_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime


class CommissionBalance(BaseModel):
    salesperson: SalespersonSummary
    earned: Decimal
    paid: Decimal
    outstanding: Decimal
