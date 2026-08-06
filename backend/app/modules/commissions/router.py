from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.pagination import CursorPage
from app.core.responses import EnvelopeRoute
from app.modules.commissions.schemas import (
    CommissionBalance,
    CommissionPayoutCreate,
    CommissionPayoutListQuery,
    CommissionPayoutRead,
    CommissionPayoutUpdate,
)
from app.modules.commissions.service import CommissionService
from app.modules.orgs.models import Membership

router = APIRouter(prefix="/commissions", tags=["commissions"], route_class=EnvelopeRoute)
Svc = Depends(Provide(CommissionService))


@router.get("/balances", response_model=list[CommissionBalance])
def commission_balances(
    membership: Membership = Depends(require_permission("reports:read")),
    svc: CommissionService = Svc,
):
    return svc.balances(membership.org_id)


@router.get("/payouts", response_model=CursorPage[CommissionPayoutRead])
def list_payouts(
    query: Annotated[CommissionPayoutListQuery, Query()],
    membership: Membership = Depends(require_permission("payments:read")),
    svc: CommissionService = Svc,
):
    items, next_cursor, has_more = svc.list(membership.org_id, query)
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}


@router.post("/payouts", response_model=CommissionPayoutRead, status_code=status.HTTP_201_CREATED)
def create_payout(
    payload: CommissionPayoutCreate,
    membership: Membership = Depends(require_permission("payments:create")),
    svc: CommissionService = Svc,
):
    return svc.create(membership.org_id, payload)


@router.get("/payouts/{payout_id}", response_model=CommissionPayoutRead)
def get_payout(
    payout_id: int,
    membership: Membership = Depends(require_permission("payments:read")),
    svc: CommissionService = Svc,
):
    return svc.get(membership.org_id, payout_id)


@router.patch("/payouts/{payout_id}", response_model=CommissionPayoutRead)
def update_payout(
    payout_id: int,
    payload: CommissionPayoutUpdate,
    membership: Membership = Depends(require_permission("payments:update")),
    svc: CommissionService = Svc,
):
    return svc.update(membership.org_id, payout_id, payload)


@router.post("/payouts/{payout_id}/submit", response_model=CommissionPayoutRead)
def submit_payout(
    payout_id: int,
    membership: Membership = Depends(require_permission("payments:update")),
    svc: CommissionService = Svc,
):
    return svc.submit(membership.org_id, payout_id)


@router.post("/payouts/{payout_id}/cancel", response_model=CommissionPayoutRead)
def cancel_payout(
    payout_id: int,
    membership: Membership = Depends(require_permission("payments:update")),
    svc: CommissionService = Svc,
):
    return svc.cancel(membership.org_id, payout_id)


@router.delete("/payouts/{payout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payout(
    payout_id: int,
    membership: Membership = Depends(require_permission("payments:delete")),
    svc: CommissionService = Svc,
) -> None:
    svc.delete(membership.org_id, payout_id)
