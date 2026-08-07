from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import ListQuery

PartyType = Literal["business", "individual"]
PartyRole = Literal["customer", "vendor"]


class PartyListQuery(ListQuery):
    role: PartyRole | None = None
    type: PartyType | None = None
    is_active: bool | None = None


class Address(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attention: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    phone: str | None = None


class PartyBase(BaseModel):
    type: PartyType = "business"
    is_customer: bool = False
    is_vendor: bool = False
    name: str = Field(min_length=1, max_length=255)
    avatar_key: str | None = Field(default=None, max_length=512)
    company_name: str | None = Field(default=None, max_length=255)
    salutation: str | None = Field(default=None, max_length=20)
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    work_phone: str | None = Field(default=None, max_length=40)
    mobile: str | None = Field(default=None, max_length=40)
    currency: str | None = Field(default=None, max_length=3)
    ntn: str | None = Field(default=None, max_length=50)
    strn: str | None = Field(default=None, max_length=50)
    cnic: str | None = Field(default=None, max_length=20)
    payment_term_days: int | None = Field(default=None, ge=0)
    billing_address: Address | None = None
    shipping_address: Address | None = None
    notes: str | None = None
    is_active: bool = True


class PartyCreate(PartyBase):
    pass


class PartyUpdate(BaseModel):
    type: PartyType | None = None
    is_customer: bool | None = None
    is_vendor: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    avatar_key: str | None = Field(default=None, max_length=512)
    company_name: str | None = Field(default=None, max_length=255)
    salutation: str | None = Field(default=None, max_length=20)
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=255)
    work_phone: str | None = Field(default=None, max_length=40)
    mobile: str | None = Field(default=None, max_length=40)
    currency: str | None = Field(default=None, max_length=3)
    ntn: str | None = Field(default=None, max_length=50)
    strn: str | None = Field(default=None, max_length=50)
    cnic: str | None = Field(default=None, max_length=20)
    payment_term_days: int | None = Field(default=None, ge=0)
    billing_address: Address | None = None
    shipping_address: Address | None = None
    notes: str | None = None
    is_active: bool | None = None


class PartyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_customer: bool
    is_vendor: bool
    type: str
    name: str
    avatar_key: str | None = None
    avatar_url: str | None = None
    company_name: str | None = None
    salutation: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    work_phone: str | None = None
    mobile: str | None = None
    currency: str | None = None
    ntn: str | None = None
    strn: str | None = None
    cnic: str | None = None
    payment_term_days: int | None = None
    billing_address: Address | None = None
    shipping_address: Address | None = None
    notes: str | None = None
    is_active: bool
    balance: Decimal = Decimal("0")
    opening_balance: Decimal = Decimal("0")
    created_at: datetime


class PartySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str | None = None
