from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentMembership
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.fbr.schemas import FbrOption, FbrReferenceRead, FbrSyncSummary
from app.modules.fbr.service import FbrService

router = APIRouter(prefix="/fbr", tags=["fbr"], route_class=EnvelopeRoute)
Svc = Depends(Provide(FbrService))


@router.get("/provinces", response_model=list[FbrOption])
def provinces(membership: CurrentMembership, svc: FbrService = Svc):
    return svc.provinces()


@router.get("/hs-uom", response_model=list[FbrReferenceRead])
def hs_uom(hs_code: str, membership: CurrentMembership, svc: FbrService = Svc):
    return svc.hs_uom(membership.org_id, hs_code)


@router.get("/sro-items", response_model=list[FbrReferenceRead])
def sro_items(sro_id: str, membership: CurrentMembership, svc: FbrService = Svc):
    return svc.sro_items(membership.org_id, sro_id)


@router.get("/reference/{ref_type}", response_model=list[FbrReferenceRead])
def reference(
    ref_type: str,
    membership: CurrentMembership,
    parent: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    svc: FbrService = Svc,
):
    return svc.reference(ref_type, parent, search, limit)


@router.get("/summary", response_model=FbrSyncSummary)
def summary(membership: CurrentMembership, svc: FbrService = Svc):
    return FbrSyncSummary(counts=svc.summary())


@router.post("/invoices/{doc_id}/validate")
def validate_invoice(
    doc_id: int,
    membership: CurrentMembership,
    scenario_id: str | None = None,
    svc: FbrService = Svc,
):
    return svc.validate_document(membership.org_id, doc_id, scenario_id)
