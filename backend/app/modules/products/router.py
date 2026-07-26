from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.pagination import CursorPage
from app.core.responses import EnvelopeRoute
from app.modules.orgs.models import Membership
from app.modules.products.models import Product
from app.modules.products.schemas import (
    ItemSalesPoint,
    ProductCreate,
    ProductListQuery,
    ProductRead,
    ProductUpdate,
)
from app.modules.products.service import ProductService

router = APIRouter(prefix="/products", tags=["products"], route_class=EnvelopeRoute)
Svc = Depends(Provide(ProductService))


@router.get("", response_model=CursorPage[ProductRead])
def list_products(
    query: Annotated[ProductListQuery, Query()],
    membership: Membership = Depends(require_permission("products:read")),
    svc: ProductService = Svc,
):
    items, next_cursor, has_more = svc.list(membership.org_id, query)
    return {"items": items, "next_cursor": next_cursor, "has_more": has_more}


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    membership: Membership = Depends(require_permission("products:create")),
    svc: ProductService = Svc,
) -> Product:
    return svc.create(membership.org_id, payload)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    membership: Membership = Depends(require_permission("products:read")),
    svc: ProductService = Svc,
) -> Product:
    return svc.get(membership.org_id, product_id)


@router.get("/{product_id}/sales", response_model=list[ItemSalesPoint])
def item_sales(
    product_id: int,
    period: Literal["month", "quarter", "year"] = "year",
    membership: Membership = Depends(require_permission("products:read")),
    svc: ProductService = Svc,
):
    return svc.item_sales(membership.org_id, product_id, period)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    membership: Membership = Depends(require_permission("products:update")),
    svc: ProductService = Svc,
) -> Product:
    return svc.update(membership.org_id, product_id, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    membership: Membership = Depends(require_permission("products:delete")),
    svc: ProductService = Svc,
) -> None:
    svc.delete(membership.org_id, product_id)
