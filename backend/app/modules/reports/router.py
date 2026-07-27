from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import require_permission
from app.core.container import Provide
from app.core.responses import EnvelopeRoute
from app.modules.orgs.models import Membership, Organization
from app.modules.reports import definitions  # noqa: F401  (populates the registry)
from app.modules.reports.export import to_pdf, to_xlsx
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"], route_class=EnvelopeRoute)
Svc = Depends(Provide(ReportService))
read = Depends(require_permission("reports:read"))

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("")
def list_reports(membership: Membership = read, svc: ReportService = Svc):
    return svc.list_reports()


@router.get("/{key}")
def report_metadata(key: str, membership: Membership = read, svc: ReportService = Svc):
    return svc.metadata(key, membership.org_id)


@router.get("/{key}/run")
def run_report(key: str, request: Request, membership: Membership = read, svc: ReportService = Svc):
    return svc.run_json(membership.org_id, key, dict(request.query_params))


@router.get("/{key}/export")
def export_report(
    key: str,
    request: Request,
    format: str = "pdf",
    membership: Membership = read,
    svc: ReportService = Svc,
):
    result = svc.run(membership.org_id, key, dict(request.query_params))
    if format == "xlsx":
        content = to_xlsx(result)
        media, ext = _XLSX, "xlsx"
    else:
        org = svc.db.get(Organization, membership.org_id)
        content = to_pdf(result, org.name if org else None)
        media, ext = "application/pdf", "pdf"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{key}.{ext}"'},
    )
