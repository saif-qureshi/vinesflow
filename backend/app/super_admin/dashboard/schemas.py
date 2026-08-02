from pydantic import BaseModel


class SuperAdminDashboardRead(BaseModel):
    organizations: int
    active_organizations: int
    inactive_organizations: int
    organization_users: int
