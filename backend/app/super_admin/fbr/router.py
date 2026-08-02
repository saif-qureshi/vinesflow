from fastapi import APIRouter, Depends, Request

from app.core.container import Provide
from app.core.ratelimit import limiter
from app.core.responses import EnvelopeRoute
from app.super_admin.auth.deps import CurrentSuperAdmin
from app.super_admin.fbr.schemas import (
    SuperAdminFbrSandboxTestRequest,
    SuperAdminFbrSandboxTestResult,
)
from app.super_admin.fbr.service import SuperAdminFbrService

router = APIRouter(
    prefix="/organizations/{org_id}/fbr",
    tags=["super-admin-fbr"],
    route_class=EnvelopeRoute,
)
FbrSvc = Depends(Provide(SuperAdminFbrService))


@router.post("/sandbox-tests", response_model=SuperAdminFbrSandboxTestResult)
@limiter.limit("10/minute")
def run_sandbox_tests(
    request: Request,
    org_id: int,
    payload: SuperAdminFbrSandboxTestRequest,
    _admin: CurrentSuperAdmin,
    fbr: SuperAdminFbrService = FbrSvc,
) -> SuperAdminFbrSandboxTestResult:
    return fbr.run_sandbox_tests(org_id, payload)
