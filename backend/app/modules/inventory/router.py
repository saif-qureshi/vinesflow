from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.pagination import CursorPage, CursorParams
from app.core.responses import EnvelopeRoute
from app.modules.inventory.schemas import (
    InventoryItemRead,
    InventoryListQuery,
    ItemStockRead,
    OnHandRead,
    OpeningStockInput,
    ReasonCreate,
    ReasonRead,
    StockAdjustInput,
    StockMovementRead,
    StockTransferInput,
)
from app.modules.inventory.service import InventoryService
from app.modules.orgs.models import Membership

router = APIRouter(prefix="/inventory", tags=["inventory"], route_class=EnvelopeRoute)
Svc = Depends(Provide(InventoryService))


@router.get("/reasons", response_model=list[ReasonRead])
def list_reasons(
    membership: Membership = Depends(require_permission("inventory:read")),
    svc: InventoryService = Svc,
):
    return svc.list_reasons(membership.org_id)


@router.post("/reasons", response_model=ReasonRead, status_code=status.HTTP_201_CREATED)
def create_reason(
    payload: ReasonCreate,
    membership: Membership = Depends(require_permission("inventory:update")),
    svc: InventoryService = Svc,
):
    return svc.create_reason(membership.org_id, payload)


@router.delete("/reasons/{reason_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reason(
    reason_id: int,
    membership: Membership = Depends(require_permission("inventory:update")),
    svc: InventoryService = Svc,
) -> None:
    svc.delete_reason(membership.org_id, reason_id)


@router.get("", response_model=CursorPage[InventoryItemRead])
def list_inventory(
    query: Annotated[InventoryListQuery, Query()],
    membership: Membership = Depends(require_permission("inventory:read")),
    svc: InventoryService = Svc,
):
    items, next_cursor, has_more = svc.list(membership.org_id, query)
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}


@router.post("/adjust", status_code=status.HTTP_204_NO_CONTENT)
def adjust_stock(
    payload: StockAdjustInput,
    membership: Membership = Depends(require_permission("inventory:update")),
    svc: InventoryService = Svc,
) -> None:
    svc.adjust(membership.org_id, payload)


@router.post("/opening", status_code=status.HTTP_204_NO_CONTENT)
def set_opening_stock(
    payload: OpeningStockInput,
    membership: Membership = Depends(require_permission("inventory:create")),
    svc: InventoryService = Svc,
) -> None:
    svc.set_opening(membership.org_id, payload)


@router.post("/transfer", status_code=status.HTTP_204_NO_CONTENT)
def transfer_stock(
    payload: StockTransferInput,
    membership: Membership = Depends(require_permission("inventory:update")),
    svc: InventoryService = Svc,
) -> None:
    svc.transfer(membership.org_id, payload)


@router.get("/{product_id}/stock", response_model=ItemStockRead)
def item_stock(
    product_id: int,
    membership: Membership = Depends(require_permission("inventory:read")),
    svc: InventoryService = Svc,
) -> ItemStockRead:
    return svc.item_stock(membership.org_id, product_id)


@router.get("/{product_id}/on-hand", response_model=OnHandRead)
def item_on_hand(
    product_id: int,
    location_id: int,
    membership: Membership = Depends(require_permission("inventory:read")),
    svc: InventoryService = Svc,
) -> OnHandRead:
    return OnHandRead(quantity=svc.on_hand(membership.org_id, product_id, location_id))


@router.get("/{product_id}/movements", response_model=CursorPage[StockMovementRead])
def item_movements(
    product_id: int,
    query: Annotated[CursorParams, Query()],
    membership: Membership = Depends(require_permission("inventory:read")),
    svc: InventoryService = Svc,
):
    items, next_cursor, has_more = svc.movements(membership.org_id, product_id, query)
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}
