from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.orgs.models import Membership
from app.modules.salespeople.models import Salesperson
from app.modules.salespeople.schemas import (
    SalespersonCreate,
    SalespersonRead,
    SalespersonUpdate,
)
from app.modules.salespeople.service import SalespersonService

router = APIRouter(prefix="/salespeople", tags=["salespeople"], route_class=EnvelopeRoute)
Svc = Depends(Provide(SalespersonService))


@router.get("", response_model=list[SalespersonRead])
def list_salespeople(
    membership: Membership = Depends(require_permission("invoices:read")),
    svc: SalespersonService = Svc,
) -> list[Salesperson]:
    return svc.list(membership.org_id)


@router.post("", response_model=SalespersonRead, status_code=status.HTTP_201_CREATED)
def create_salesperson(
    payload: SalespersonCreate,
    membership: Membership = Depends(require_permission("orgs:update")),
    svc: SalespersonService = Svc,
) -> Salesperson:
    return svc.create(membership.org_id, payload)


@router.patch("/{salesperson_id}", response_model=SalespersonRead)
def update_salesperson(
    salesperson_id: int,
    payload: SalespersonUpdate,
    membership: Membership = Depends(require_permission("orgs:update")),
    svc: SalespersonService = Svc,
) -> Salesperson:
    return svc.update(membership.org_id, salesperson_id, payload)


@router.delete("/{salesperson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salesperson(
    salesperson_id: int,
    membership: Membership = Depends(require_permission("orgs:update")),
    svc: SalespersonService = Svc,
) -> None:
    svc.delete(membership.org_id, salesperson_id)
