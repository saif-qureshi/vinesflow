from fastapi import APIRouter, Depends

from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.super_admin.auth.deps import CurrentSuperAdmin
from app.super_admin.dashboard.schemas import SuperAdminDashboardRead
from app.super_admin.dashboard.service import SuperAdminDashboardService

router = APIRouter(tags=["super-admin-dashboard"], route_class=EnvelopeRoute)
DashboardSvc = Depends(Provide(SuperAdminDashboardService))


@router.get("/dashboard", response_model=SuperAdminDashboardRead)
def dashboard(
    _admin: CurrentSuperAdmin,
    service: SuperAdminDashboardService = DashboardSvc,
) -> SuperAdminDashboardRead:
    return service.read()
