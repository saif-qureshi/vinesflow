from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SuperAdminOrganizationRead(BaseModel):
    id: int
    name: str
    slug: str
    currency: str
    country: str
    industry: str | None = None
    is_active: bool
    owner_name: str | None = None
    owner_email: str
    member_count: int
    fiscal_year_start_month: int
    created_at: datetime


class SuperAdminOrganizationPage(BaseModel):
    items: list[SuperAdminOrganizationRead]
    total: int
    page: int
    page_size: int


class SuperAdminOrganizationOnboard(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=128)
    owner_full_name: str | None = Field(default=None, max_length=255)
    currency: str = Field(default="PKR", min_length=3, max_length=3)
    country: str = Field(default="PK", min_length=2, max_length=2)
    industry: str | None = Field(default=None, max_length=100)
    fiscal_year_start_month: int = Field(default=7, ge=1, le=12)


class SuperAdminOrganizationStatusUpdate(BaseModel):
    is_active: bool


class SuperAdminOrganizationUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    currency: str = Field(min_length=3, max_length=3)
    country: str = Field(min_length=2, max_length=2)
    industry: str | None = Field(default=None, max_length=100)
    fiscal_year_start_month: int = Field(ge=1, le=12)
    is_active: bool
