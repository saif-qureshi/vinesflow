from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SalespersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    commission_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    is_active: bool = True


class SalespersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    commission_rate: Decimal | None = Field(default=None, ge=0, le=100)
    is_active: bool | None = None


class SalespersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    commission_rate: Decimal
    is_active: bool
    created_at: datetime


class SalespersonSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
