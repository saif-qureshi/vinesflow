from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.accounting.accounts import AccountsService
from app.modules.accounting.fiscal import FiscalYearService
from app.modules.accounting.schemas import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    FiscalYearRead,
    JournalVoucherCreate,
    OpeningBalanceInput,
    PeriodRead,
    PeriodStatusUpdate,
    VoucherRead,
    VoucherSummary,
)
from app.modules.accounting.vouchers import VoucherService
from app.modules.orgs.models import Membership

router = APIRouter(prefix="/accounting", tags=["accounting"], route_class=EnvelopeRoute)
Accounts = Depends(Provide(AccountsService))
Fiscal = Depends(Provide(FiscalYearService))
Vouchers = Depends(Provide(VoucherService))


# --- Accounts ------------------------------------------------------------


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    membership: Membership = Depends(require_permission("accounting:read")),
    svc: AccountsService = Accounts,
):
    return svc.list_accounts(membership.org_id)


@router.post("/accounts", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    membership: Membership = Depends(require_permission("accounting:create")),
    svc: AccountsService = Accounts,
):
    return svc.create_account(membership.org_id, payload)


@router.patch("/accounts/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    membership: Membership = Depends(require_permission("accounting:update")),
    svc: AccountsService = Accounts,
):
    return svc.update_account(membership.org_id, account_id, payload)


# --- Journal vouchers ----------------------------------------------------


@router.get("/vouchers", response_model=list[VoucherSummary])
def list_vouchers(
    membership: Membership = Depends(require_permission("accounting:read")),
    svc: VoucherService = Vouchers,
):
    return svc.list_vouchers(membership.org_id)


@router.post("/vouchers", response_model=VoucherRead, status_code=status.HTTP_201_CREATED)
def create_voucher(
    payload: JournalVoucherCreate,
    membership: Membership = Depends(require_permission("accounting:create")),
    svc: VoucherService = Vouchers,
):
    return svc.create_journal_voucher(membership.org_id, payload)


@router.get("/vouchers/{voucher_id}", response_model=VoucherRead)
def get_voucher(
    voucher_id: int,
    membership: Membership = Depends(require_permission("accounting:read")),
    svc: VoucherService = Vouchers,
):
    return svc.get_voucher(membership.org_id, voucher_id)


@router.patch("/vouchers/{voucher_id}", response_model=VoucherRead)
def update_voucher(
    voucher_id: int,
    payload: JournalVoucherCreate,
    membership: Membership = Depends(require_permission("accounting:update")),
    svc: VoucherService = Vouchers,
):
    return svc.update_journal_voucher(membership.org_id, voucher_id, payload)


@router.post("/vouchers/{voucher_id}/post", response_model=VoucherRead)
def post_voucher(
    voucher_id: int,
    membership: Membership = Depends(require_permission("accounting:update")),
    svc: VoucherService = Vouchers,
):
    return svc.post_journal_voucher(membership.org_id, voucher_id)


@router.post("/vouchers/{voucher_id}/cancel", response_model=VoucherRead)
def cancel_voucher(
    voucher_id: int,
    membership: Membership = Depends(require_permission("accounting:update")),
    svc: VoucherService = Vouchers,
):
    return svc.cancel_journal_voucher(membership.org_id, voucher_id)


@router.post("/vouchers/{voucher_id}/reverse", response_model=VoucherRead)
def reverse_voucher(
    voucher_id: int,
    membership: Membership = Depends(require_permission("accounting:update")),
    svc: VoucherService = Vouchers,
):
    return svc.reverse_voucher(membership.org_id, voucher_id)


@router.post("/opening-balances", response_model=VoucherRead, status_code=status.HTTP_201_CREATED)
def create_opening_balances(
    payload: OpeningBalanceInput,
    membership: Membership = Depends(require_permission("accounting:create")),
    svc: VoucherService = Vouchers,
):
    return svc.create_opening_balances(membership.org_id, payload)


# --- Fiscal years & periods ----------------------------------------------


@router.get("/fiscal-years", response_model=list[FiscalYearRead])
def list_fiscal_years(
    membership: Membership = Depends(require_permission("accounting:read")),
    svc: FiscalYearService = Fiscal,
):
    return svc.list_fiscal_years(membership.org_id)


@router.post("/fiscal-years", response_model=FiscalYearRead, status_code=status.HTTP_201_CREATED)
def create_fiscal_year(
    membership: Membership = Depends(require_permission("accounting:create")),
    svc: FiscalYearService = Fiscal,
):
    return svc.create_next_fiscal_year(membership.org_id)


@router.delete("/fiscal-years/{fiscal_year_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fiscal_year(
    fiscal_year_id: int,
    membership: Membership = Depends(require_permission("accounting:delete")),
    svc: FiscalYearService = Fiscal,
):
    svc.delete_fiscal_year(membership.org_id, fiscal_year_id)


@router.get("/periods", response_model=list[PeriodRead])
def list_periods(
    fiscal_year_id: int | None = None,
    membership: Membership = Depends(require_permission("accounting:read")),
    svc: FiscalYearService = Fiscal,
):
    return svc.list_periods(membership.org_id, fiscal_year_id)


@router.patch("/periods/{period_id}/status", response_model=PeriodRead)
def set_period_status(
    period_id: int,
    payload: PeriodStatusUpdate,
    membership: Membership = Depends(require_permission("accounting:update")),
    svc: FiscalYearService = Fiscal,
):
    return svc.set_period_status(membership.org_id, period_id, payload.status)
