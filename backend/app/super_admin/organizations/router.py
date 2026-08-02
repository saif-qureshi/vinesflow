from fastapi import APIRouter, Depends, Query, status

from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.super_admin.auth.deps import CurrentSuperAdmin
from app.super_admin.organizations.schemas import (
    SuperAdminOrganizationOnboard,
    SuperAdminOrganizationPage,
    SuperAdminOrganizationRead,
    SuperAdminOrganizationStatusUpdate,
    SuperAdminOrganizationUpdate,
)
from app.super_admin.organizations.service import SuperAdminOrganizationService

router = APIRouter(
    prefix="/organizations",
    tags=["super-admin-organizations"],
    route_class=EnvelopeRoute,
)
OrgSvc = Depends(Provide(SuperAdminOrganizationService))


@router.get("/{org_id}", response_model=SuperAdminOrganizationRead)
def get_organization(
    org_id: int,
    _admin: CurrentSuperAdmin,
    organizations: SuperAdminOrganizationService = OrgSvc,
) -> SuperAdminOrganizationRead:
    return organizations.get(org_id)


@router.get("", response_model=SuperAdminOrganizationPage)
def list_organizations(
    _admin: CurrentSuperAdmin,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    organizations: SuperAdminOrganizationService = OrgSvc,
) -> SuperAdminOrganizationPage:
    return organizations.list(search=search, page=page, page_size=page_size)


@router.post("", response_model=SuperAdminOrganizationRead, status_code=status.HTTP_201_CREATED)
def onboard_organization(
    payload: SuperAdminOrganizationOnboard,
    _admin: CurrentSuperAdmin,
    organizations: SuperAdminOrganizationService = OrgSvc,
) -> SuperAdminOrganizationRead:
    return organizations.onboard(payload)


@router.patch("/{org_id}/status", response_model=SuperAdminOrganizationRead)
def update_organization_status(
    org_id: int,
    payload: SuperAdminOrganizationStatusUpdate,
    _admin: CurrentSuperAdmin,
    organizations: SuperAdminOrganizationService = OrgSvc,
) -> SuperAdminOrganizationRead:
    return organizations.set_status(org_id, payload.is_active)


@router.put("/{org_id}", response_model=SuperAdminOrganizationRead)
def update_organization(
    org_id: int,
    payload: SuperAdminOrganizationUpdate,
    _admin: CurrentSuperAdmin,
    organizations: SuperAdminOrganizationService = OrgSvc,
) -> SuperAdminOrganizationRead:
    return organizations.update(org_id, payload)
