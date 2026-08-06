from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.pagination import CursorPage
from app.core.responses import EnvelopeRoute
from app.modules.documents.enums import DocumentType
from app.modules.documents.print.service import DocumentPrintService
from app.modules.documents.schemas import (
    DocumentConvertInput,
    DocumentCreate,
    DocumentListItem,
    DocumentListQuery,
    DocumentRead,
    DocumentUpdate,
    SellableItemRead,
    TaxRateCreate,
    TaxRateRead,
    TaxRateUpdate,
)
from app.modules.documents.service import DocumentService
from app.modules.orgs.models import Membership

router = APIRouter(tags=["documents"], route_class=EnvelopeRoute)
Svc = Depends(Provide(DocumentService))
PrintSvc = Depends(Provide(DocumentPrintService))


@router.get("/tax-rates", response_model=list[TaxRateRead])
def list_tax_rates(
    membership: Membership = Depends(require_permission("products:read")),
    svc: DocumentService = Svc,
):
    return svc.list_tax_rates(membership.org_id)


@router.post("/tax-rates", response_model=TaxRateRead, status_code=status.HTTP_201_CREATED)
def create_tax_rate(
    payload: TaxRateCreate,
    membership: Membership = Depends(require_permission("orgs:update")),
    svc: DocumentService = Svc,
):
    return svc.create_tax_rate(membership.org_id, payload)


@router.patch("/tax-rates/{rate_id}", response_model=TaxRateRead)
def update_tax_rate(
    rate_id: int,
    payload: TaxRateUpdate,
    membership: Membership = Depends(require_permission("orgs:update")),
    svc: DocumentService = Svc,
):
    return svc.update_tax_rate(membership.org_id, rate_id, payload)


@router.get("/sellable-items", response_model=list[SellableItemRead])
def sellable_items(
    search: str | None = None,
    warehouse_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    membership: Membership = Depends(require_permission("products:read")),
    svc: DocumentService = Svc,
):
    return svc.sellable_items(membership.org_id, search, limit, warehouse_id)


@router.get("/stock-on-hand", response_model=dict[int, Decimal])
def stock_on_hand(
    product_ids: list[int] = Query(default=[]),
    warehouse_id: int | None = None,
    membership: Membership = Depends(require_permission("inventory:read")),
    svc: DocumentService = Svc,
):
    return svc.stock_on_hand(membership.org_id, product_ids, warehouse_id)


def register_document_routes(path: str, doc_type: DocumentType, module: str) -> None:
    read = Depends(require_permission(f"{module}:read"))
    make = Depends(require_permission(f"{module}:create"))
    edit = Depends(require_permission(f"{module}:update"))
    drop = Depends(require_permission(f"{module}:delete"))

    @router.get(f"/{path}", response_model=CursorPage[DocumentListItem], name=f"list_{path}")
    def _list(
        query: Annotated[DocumentListQuery, Query()],
        membership: Membership = read,
        svc: DocumentService = Svc,
    ):
        items, next_cursor, has_more = svc.list_documents(membership.org_id, doc_type, query)
        return {"items": items, "next_cursor": next_cursor, "has_more": has_more}

    @router.post(
        f"/{path}",
        response_model=DocumentRead,
        status_code=status.HTTP_201_CREATED,
        name=f"create_{path}",
    )
    def _create(
        payload: DocumentCreate, membership: Membership = make, svc: DocumentService = Svc
    ):
        return svc.create(membership.org_id, doc_type, payload)

    @router.get(f"/{path}/next-number", name=f"next_number_{path}")
    def _next_number(membership: Membership = read, svc: DocumentService = Svc):
        return {"number": svc.next_number(membership.org_id, doc_type)}

    @router.get(f"/{path}/{{doc_id}}", response_model=DocumentRead, name=f"get_{path}")
    def _get(doc_id: int, membership: Membership = read, svc: DocumentService = Svc):
        return svc.get_of_type(membership.org_id, doc_id, doc_type)

    @router.patch(f"/{path}/{{doc_id}}", response_model=DocumentRead, name=f"update_{path}")
    def _update(
        doc_id: int,
        payload: DocumentUpdate,
        membership: Membership = edit,
        svc: DocumentService = Svc,
    ):
        return svc.update(membership.org_id, doc_id, doc_type, payload)

    @router.post(
        f"/{path}/{{doc_id}}/finalize", response_model=DocumentRead, name=f"finalize_{path}"
    )
    def _finalize(doc_id: int, membership: Membership = edit, svc: DocumentService = Svc):
        return svc.finalize(membership.org_id, doc_id, doc_type)

    @router.post(f"/{path}/{{doc_id}}/void", response_model=DocumentRead, name=f"void_{path}")
    def _void(doc_id: int, membership: Membership = edit, svc: DocumentService = Svc):
        return svc.void(membership.org_id, doc_id, doc_type)

    @router.delete(
        f"/{path}/{{doc_id}}", status_code=status.HTTP_204_NO_CONTENT, name=f"delete_{path}"
    )
    def _delete(doc_id: int, membership: Membership = drop, svc: DocumentService = Svc) -> None:
        svc.delete(membership.org_id, doc_id, doc_type)

    @router.post(f"/{path}/{{doc_id}}/convert", response_model=DocumentRead, name=f"convert_{path}")
    def _convert(
        doc_id: int,
        payload: DocumentConvertInput,
        membership: Membership = edit,
        svc: DocumentService = Svc,
    ):
        return svc.convert(membership.org_id, doc_id, doc_type, DocumentType(payload.target))

    @router.get(f"/{path}/{{doc_id}}/preview", name=f"preview_{path}")
    def _preview(
        doc_id: int,
        skin: str = "corporate",
        membership: Membership = read,
        svc: DocumentPrintService = PrintSvc,
    ):
        html = svc.render_html(membership.org_id, doc_id, doc_type, skin)
        return Response(content=html, media_type="text/html")

    @router.get(f"/{path}/{{doc_id}}/pdf", name=f"pdf_{path}")
    def _pdf(
        doc_id: int,
        skin: str = "corporate",
        paper: str = "a4",
        download: bool = False,
        membership: Membership = read,
        svc: DocumentPrintService = PrintSvc,
    ):
        content, filename = svc.render_pdf(membership.org_id, doc_id, doc_type, skin, paper)
        disposition = "attachment" if download else "inline"
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
        )


register_document_routes("sales-orders", DocumentType.SALES_ORDER, "sales_orders")
register_document_routes("delivery-challans", DocumentType.DELIVERY_CHALLAN, "delivery_challans")
register_document_routes("invoices", DocumentType.INVOICE, "invoices")
register_document_routes("credit-notes", DocumentType.CREDIT_NOTE, "credit_notes")
register_document_routes("purchase-orders", DocumentType.PURCHASE_ORDER, "purchase_orders")
register_document_routes("goods-receipts", DocumentType.GOODS_RECEIPT, "goods_receipts")
register_document_routes("bills", DocumentType.BILL, "bills")
