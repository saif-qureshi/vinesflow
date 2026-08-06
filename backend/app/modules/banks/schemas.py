from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BankOption(BaseModel):
    code: str
    name: str
    colour: str


class BankAccountCreate(BaseModel):
    bank_name: str = Field(min_length=1, max_length=150)
    bank_code: str | None = Field(default=None, max_length=20)
    account_title: str = Field(min_length=1, max_length=150)
    account_number: str = Field(min_length=1, max_length=50)
    iban: str | None = Field(default=None, max_length=34)
    branch: str | None = Field(default=None, max_length=150)
    currency: str = Field(default="PKR", min_length=3, max_length=3)
    colour: str | None = Field(default=None, max_length=9)
    logo_key: str | None = Field(default=None, max_length=512)


class BankAccountUpdate(BaseModel):
    bank_name: str | None = Field(default=None, min_length=1, max_length=150)
    bank_code: str | None = Field(default=None, max_length=20)
    account_title: str | None = Field(default=None, min_length=1, max_length=150)
    account_number: str | None = Field(default=None, min_length=1, max_length=50)
    iban: str | None = Field(default=None, max_length=34)
    branch: str | None = Field(default=None, max_length=150)
    colour: str | None = Field(default=None, max_length=9)
    logo_key: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None


class BankAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bank_name: str
    bank_code: str | None = None
    account_title: str
    account_number: str
    iban: str | None = None
    branch: str | None = None
    currency: str
    colour: str | None = None
    logo_key: str | None = None
    logo_url: str | None = None
    account_id: int
    account_code: str | None = None
    balance: Decimal = Decimal("0")
    is_active: bool
    created_at: datetime
