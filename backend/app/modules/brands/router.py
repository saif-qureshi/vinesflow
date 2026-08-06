from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.brands.models import Brand
from app.modules.brands.schemas import BrandCreate, BrandRead, BrandUpdate
from app.modules.brands.service import BrandService
from app.modules.orgs.models import Membership

router = APIRouter(prefix="/brands", tags=["brands"], route_class=EnvelopeRoute)
Svc = Depends(Provide(BrandService))


@router.get("", response_model=list[BrandRead])
def list_brands(
    membership: Membership = Depends(require_permission("products:read")),
    svc: BrandService = Svc,
) -> list[Brand]:
    return svc.list(membership.org_id)


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
def create_brand(
    payload: BrandCreate,
    membership: Membership = Depends(require_permission("products:create")),
    svc: BrandService = Svc,
) -> Brand:
    return svc.create(membership.org_id, payload)


@router.patch("/{brand_id}", response_model=BrandRead)
def update_brand(
    brand_id: int,
    payload: BrandUpdate,
    membership: Membership = Depends(require_permission("products:update")),
    svc: BrandService = Svc,
) -> Brand:
    return svc.update(membership.org_id, brand_id, payload)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(
    brand_id: int,
    membership: Membership = Depends(require_permission("products:delete")),
    svc: BrandService = Svc,
) -> None:
    svc.delete(membership.org_id, brand_id)
