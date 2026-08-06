from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.modules.orgs.schemas import Address


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


class SuperAdminOrganizationMember(BaseModel):
    membership_id: int
    user_id: int
    full_name: str | None = None
    email: str
    role_name: str
    role_slug: str
    is_owner: bool
    is_active: bool


class SuperAdminOrganizationDetail(SuperAdminOrganizationRead):
    ntn: str | None = None
    strn: str | None = None
    cnic: str | None = None
    address: Address | None = None
    logo_key: str | None = None
    logo_url: str | None = None
    fbr_enabled: bool
    fbr_environment: str
    fbr_province: str | None = None
    fbr_sandbox_configured: bool
    fbr_production_configured: bool
    members: list[SuperAdminOrganizationMember]


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


class SuperAdminOrganizationOwnerPasswordUpdate(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class SuperAdminOrganizationOwnerPasswordResult(BaseModel):
    owner_email: str
    message: str


class SuperAdminOrganizationUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    currency: str = Field(min_length=3, max_length=3)
    country: str = Field(min_length=2, max_length=2)
    industry: str | None = Field(default=None, max_length=100)
    ntn: str | None = Field(default=None, max_length=20)
    strn: str | None = Field(default=None, max_length=20)
    cnic: str | None = Field(default=None, max_length=20)
    address: Address | None = None
    logo_key: str | None = Field(default=None, max_length=512)
    fbr_enabled: bool | None = None
    fbr_environment: str | None = Field(default=None, pattern="^(sandbox|production)$")
    fbr_province: str | None = Field(default=None, max_length=50)
    fbr_sandbox_token: str | None = Field(default=None, max_length=512)
    fbr_production_token: str | None = Field(default=None, max_length=512)
    fiscal_year_start_month: int = Field(ge=1, le=12)
    is_active: bool
