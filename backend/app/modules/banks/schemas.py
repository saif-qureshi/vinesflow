from __future__ import annotations

import re
import string
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ACCOUNT_NUMBER = re.compile(r"^[0-9][0-9-]{5,29}$")
_IBAN = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$")
_ALPHANUM = {c: str(10 + i) for i, c in enumerate(string.ascii_uppercase)}


def _normalize_account_number(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s", "", value)
    if not _ACCOUNT_NUMBER.fullmatch(cleaned):
        raise ValueError("An account number is 6-30 digits, optionally grouped with dashes")
    return cleaned


def _normalize_iban(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    cleaned = re.sub(r"\s", "", value).upper()
    if not _IBAN.fullmatch(cleaned):
        raise ValueError("An IBAN is two letters, two digits, then 11-30 letters or digits")
    # ISO 13616 check: rotate the first four characters to the end, turn letters
    # into numbers, and the whole thing must leave a remainder of 1 mod 97.
    rotated = cleaned[4:] + cleaned[:4]
    digits = "".join(_ALPHANUM.get(char, char) for char in rotated)
    if int(digits) % 97 != 1:
        raise ValueError("That IBAN's check digits are wrong — it may have a typo")
    return cleaned


class BankOption(BaseModel):
    code: str
    name: str
    colour: str
    logo_url: str


class BankAccountCreate(BaseModel):
    bank_name: str = Field(min_length=1, max_length=150)
    bank_code: str | None = Field(default=None, max_length=20)
    account_title: str = Field(min_length=2, max_length=150)
    account_number: str = Field(min_length=1, max_length=50)
    iban: str | None = Field(default=None, max_length=42)
    branch: str | None = Field(default=None, max_length=150)
    currency: str = Field(default="PKR", min_length=3, max_length=3)

    _clean_number = field_validator("account_number")(_normalize_account_number)
    _clean_iban = field_validator("iban")(_normalize_iban)


class BankAccountUpdate(BaseModel):
    bank_name: str | None = Field(default=None, min_length=1, max_length=150)
    bank_code: str | None = Field(default=None, max_length=20)
    account_title: str | None = Field(default=None, min_length=2, max_length=150)
    account_number: str | None = Field(default=None, min_length=1, max_length=50)
    iban: str | None = Field(default=None, max_length=42)
    branch: str | None = Field(default=None, max_length=150)
    is_active: bool | None = None

    _clean_number = field_validator("account_number")(_normalize_account_number)
    _clean_iban = field_validator("iban")(_normalize_iban)


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
    account_id: int
    account_code: str | None = None
    balance: Decimal = Decimal("0")
    is_active: bool
    created_at: datetime
