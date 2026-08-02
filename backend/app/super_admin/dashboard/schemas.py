from datetime import datetime

from pydantic import BaseModel


class SuperAdminDashboardOrganization(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    owner_email: str
    member_count: int
    tax_identity_configured: bool
    fbr_enabled: bool
    fbr_ready: bool
    created_at: datetime


class SuperAdminDashboardActivityPoint(BaseModel):
    date: str
    customer_logins: int
    organizations_created: int


class SuperAdminDashboardFbrInvoicePoint(BaseModel):
    date: str
    submitted: int
    draft: int
    failed: int


class SuperAdminDashboardRead(BaseModel):
    organizations: int
    active_organizations: int
    inactive_organizations: int
    organization_users: int
    new_organizations_30d: int
    fbr_enabled_organizations: int
    tax_identity_organizations: int
    fbr_configuration_issues: int
    recent_organizations: list[SuperAdminDashboardOrganization]
    activity_14d: list[SuperAdminDashboardActivityPoint]
    fbr_invoice_activity_14d: list[SuperAdminDashboardFbrInvoicePoint]
