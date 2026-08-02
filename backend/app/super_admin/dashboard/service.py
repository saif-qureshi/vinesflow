from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.orgs.models import Organization
from app.modules.users.models import User
from app.super_admin.dashboard.schemas import SuperAdminDashboardRead


class SuperAdminDashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def read(self) -> SuperAdminDashboardRead:
        organizations = self.db.scalar(select(func.count()).select_from(Organization)) or 0
        active = (
            self.db.scalar(
                select(func.count())
                .select_from(Organization)
                .where(Organization.is_active.is_(True))
            )
            or 0
        )
        users = self.db.scalar(select(func.count()).select_from(User)) or 0
        return SuperAdminDashboardRead(
            organizations=organizations,
            active_organizations=active,
            inactive_organizations=organizations - active,
            organization_users=users,
        )
