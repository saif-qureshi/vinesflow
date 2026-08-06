from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.schemas import UserRead


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


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    currency: str = Field(default="PKR", min_length=3, max_length=3)
    industry: str | None = Field(default=None, max_length=100)
    fiscal_year_start_month: int = Field(default=7, ge=1, le=12)


class OrgUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    industry: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    ntn: str | None = Field(default=None, max_length=20)
    strn: str | None = Field(default=None, max_length=20)
    cnic: str | None = Field(default=None, max_length=20)
    address: Address | None = None
    fiscal_year_start_month: int | None = Field(default=None, ge=1, le=12)
    logo_key: str | None = Field(default=None, max_length=512)
    theme: str | None = Field(default=None, pattern="^(light|dark)$")
    accent_color: str | None = Field(default=None, min_length=4, max_length=9)
    keep_branding: bool | None = None
    fbr_enabled: bool | None = None
    fbr_environment: str | None = Field(default=None, pattern="^(sandbox|production)$")
    fbr_province: str | None = Field(default=None, max_length=50)
    fbr_sandbox_token: str | None = Field(default=None, max_length=512)
    fbr_production_token: str | None = Field(default=None, max_length=512)


class OrgRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    currency: str
    industry: str | None = None
    country: str
    ntn: str | None = None
    strn: str | None = None
    cnic: str | None = None
    address: Address | None = None
    fiscal_year_start_month: int
    logo_key: str | None = None
    logo_url: str | None = None
    theme: str
    accent_color: str
    keep_branding: bool
    fbr_enabled: bool
    fbr_environment: str
    fbr_province: str | None = None
    fbr_sandbox_configured: bool = False
    fbr_production_configured: bool = False
    created_at: datetime


class RoleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class OrgMembership(BaseModel):
    """An org the current user belongs to, plus their role and owner flag."""

    model_config = ConfigDict(from_attributes=True)

    org_id: int
    is_owner: bool
    organization: OrgRead
    role: RoleSummary


class MemberRead(BaseModel):
    """A member of an org, from the org's perspective."""

    model_config = ConfigDict(from_attributes=True)

    id: int  # membership id
    is_owner: bool
    user: UserRead
    role: RoleSummary


class MemberAdd(BaseModel):
    email: str
    role_id: int


class MemberUpdate(BaseModel):
    role_id: int
