from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from app.api.deps import CurrentMembership
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.dashboard.schemas import DashboardSummary
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"], route_class=EnvelopeRoute)

Svc = Depends(Provide(DashboardService))


@router.get("/summary", response_model=DashboardSummary)
def summary(membership: CurrentMembership, svc: DashboardService = Svc) -> DashboardSummary:
    return svc.summary(membership.org_id, date.today())
