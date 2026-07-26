from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.accounting.manage import AccountingService
from app.modules.accounting.schemas import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    FiscalYearRead,
    PeriodRead,
    PeriodStatusUpdate,
)
from app.modules.orgs.models import Membership

router = APIRouter(prefix="/accounting", tags=["accounting"], route_class=EnvelopeRoute)
Svc = Depends(Provide(AccountingService))


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    membership: Membership = Depends(require_permission("accounting:read")),
    svc: AccountingService = Svc,
):
    return svc.list_accounts(membership.org_id)


@router.post("/accounts", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    membership: Membership = Depends(require_permission("accounting:create")),
    svc: AccountingService = Svc,
):
    return svc.create_account(membership.org_id, payload)


@router.patch("/accounts/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    membership: Membership = Depends(require_permission("accounting:update")),
    svc: AccountingService = Svc,
):
    return svc.update_account(membership.org_id, account_id, payload)


@router.get("/fiscal-years", response_model=list[FiscalYearRead])
def list_fiscal_years(
    membership: Membership = Depends(require_permission("accounting:read")),
    svc: AccountingService = Svc,
):
    return svc.list_fiscal_years(membership.org_id)


@router.get("/periods", response_model=list[PeriodRead])
def list_periods(
    fiscal_year_id: int | None = None,
    membership: Membership = Depends(require_permission("accounting:read")),
    svc: AccountingService = Svc,
):
    return svc.list_periods(membership.org_id, fiscal_year_id)


@router.patch("/periods/{period_id}/status", response_model=PeriodRead)
def set_period_status(
    period_id: int,
    payload: PeriodStatusUpdate,
    membership: Membership = Depends(require_permission("accounting:update")),
    svc: AccountingService = Svc,
):
    return svc.set_period_status(membership.org_id, period_id, payload.status)
