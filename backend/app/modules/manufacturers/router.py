from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.manufacturers.models import Manufacturer
from app.modules.manufacturers.schemas import (
    ManufacturerCreate,
    ManufacturerRead,
    ManufacturerUpdate,
)
from app.modules.manufacturers.service import ManufacturerService
from app.modules.orgs.models import Membership

router = APIRouter(prefix="/manufacturers", tags=["manufacturers"], route_class=EnvelopeRoute)
Svc = Depends(Provide(ManufacturerService))


@router.get("", response_model=list[ManufacturerRead])
def list_manufacturers(
    membership: Membership = Depends(require_permission("products:read")),
    svc: ManufacturerService = Svc,
) -> list[Manufacturer]:
    return svc.list(membership.org_id)


@router.post("", response_model=ManufacturerRead, status_code=status.HTTP_201_CREATED)
def create_manufacturer(
    payload: ManufacturerCreate,
    membership: Membership = Depends(require_permission("products:create")),
    svc: ManufacturerService = Svc,
) -> Manufacturer:
    return svc.create(membership.org_id, payload)


@router.patch("/{manufacturer_id}", response_model=ManufacturerRead)
def update_manufacturer(
    manufacturer_id: int,
    payload: ManufacturerUpdate,
    membership: Membership = Depends(require_permission("products:update")),
    svc: ManufacturerService = Svc,
) -> Manufacturer:
    return svc.update(membership.org_id, manufacturer_id, payload)


@router.delete("/{manufacturer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manufacturer(
    manufacturer_id: int,
    membership: Membership = Depends(require_permission("products:delete")),
    svc: ManufacturerService = Svc,
) -> None:
    svc.delete(membership.org_id, manufacturer_id)
