from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.banks.catalog import PAKISTANI_BANKS, logo_key
from app.modules.banks.schemas import (
    BankAccountCreate,
    BankAccountRead,
    BankAccountUpdate,
    BankOption,
)
from app.modules.banks.service import BankAccountService
from app.modules.orgs.models import Membership

router = APIRouter(prefix="/banks", tags=["banks"], route_class=EnvelopeRoute)
Svc = Depends(Provide(BankAccountService))


@router.get("/catalog", response_model=list[BankOption])
def bank_catalog(
    membership: Membership = Depends(require_permission("accounting:read")),
) -> list[dict]:
    from app.core.storage import get_storage

    storage = get_storage()
    return [
        {**bank, "logo_url": storage.url_for(logo_key(bank["logo"]))}
        for bank in PAKISTANI_BANKS
    ]


@router.get("/accounts", response_model=list[BankAccountRead])
def list_bank_accounts(
    membership: Membership = Depends(require_permission("accounting:read")),
    svc: BankAccountService = Svc,
):
    return svc.list(membership.org_id)


@router.post("/accounts", response_model=BankAccountRead, status_code=status.HTTP_201_CREATED)
def create_bank_account(
    payload: BankAccountCreate,
    membership: Membership = Depends(require_permission("accounting:create")),
    svc: BankAccountService = Svc,
):
    return svc.create(membership.org_id, payload)


@router.patch("/accounts/{bank_id}", response_model=BankAccountRead)
def update_bank_account(
    bank_id: int,
    payload: BankAccountUpdate,
    membership: Membership = Depends(require_permission("accounting:update")),
    svc: BankAccountService = Svc,
):
    return svc.update(membership.org_id, bank_id, payload)


@router.delete("/accounts/{bank_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bank_account(
    bank_id: int,
    membership: Membership = Depends(require_permission("accounting:delete")),
    svc: BankAccountService = Svc,
) -> None:
    svc.delete(membership.org_id, bank_id)
