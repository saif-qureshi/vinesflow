from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.pagination import CursorPage
from app.core.responses import EnvelopeRoute
from app.modules.expenses.schemas import (
    ExpenseCreate,
    ExpenseListItem,
    ExpenseListQuery,
    ExpenseRead,
    ExpenseUpdate,
)
from app.modules.expenses.service import ExpenseService
from app.modules.orgs.models import Membership

router = APIRouter(prefix="/expenses", tags=["expenses"], route_class=EnvelopeRoute)
Svc = Depends(Provide(ExpenseService))

read = Depends(require_permission("expenses:read"))
make = Depends(require_permission("expenses:create"))
edit = Depends(require_permission("expenses:update"))
drop = Depends(require_permission("expenses:delete"))


@router.get("", response_model=CursorPage[ExpenseListItem])
def list_expenses(
    query: Annotated[ExpenseListQuery, Query()],
    membership: Membership = read,
    svc: ExpenseService = Svc,
):
    items, next_cursor, has_more = svc.list(membership.org_id, query)
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate, membership: Membership = make, svc: ExpenseService = Svc
):
    return svc.create(membership.org_id, payload)


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(expense_id: int, membership: Membership = read, svc: ExpenseService = Svc):
    return svc.get(membership.org_id, expense_id)


@router.patch("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    membership: Membership = edit,
    svc: ExpenseService = Svc,
):
    return svc.update(membership.org_id, expense_id, payload)


@router.post("/{expense_id}/submit", response_model=ExpenseRead)
def submit_expense(expense_id: int, membership: Membership = edit, svc: ExpenseService = Svc):
    return svc.submit(membership.org_id, expense_id)


@router.post("/{expense_id}/cancel", response_model=ExpenseRead)
def cancel_expense(expense_id: int, membership: Membership = edit, svc: ExpenseService = Svc):
    return svc.cancel(membership.org_id, expense_id)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(
    expense_id: int, membership: Membership = drop, svc: ExpenseService = Svc
) -> None:
    svc.delete(membership.org_id, expense_id)
