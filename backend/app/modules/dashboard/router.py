from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.orgs.models import Membership
from app.modules.dashboard.schemas import DashboardSummary
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"], route_class=EnvelopeRoute)

Svc = Depends(Provide(DashboardService))


@router.get("/summary", response_model=DashboardSummary)
def summary(
    membership: Membership = Depends(require_permission("reports:read")),
    svc: DashboardService = Svc,
) -> DashboardSummary:
    return svc.summary(membership.org_id, date.today())
