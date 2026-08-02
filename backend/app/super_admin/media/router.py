from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.ratelimit import limiter
from app.core.responses import EnvelopeRoute
from app.core.storage import get_storage
from app.modules.media.schemas import MediaUploadResult
from app.modules.orgs.models import Organization
from app.super_admin.auth.deps import CurrentSuperAdmin, DbSession

router = APIRouter(
    prefix="/organizations/{org_id}/media",
    tags=["super-admin-media"],
    route_class=EnvelopeRoute,
)

_ALLOWED_LOGO_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}


@router.post("/upload", response_model=MediaUploadResult)
@limiter.limit("30/minute")
async def upload_organization_logo(
    request: Request,
    org_id: int,
    _admin: CurrentSuperAdmin,
    db: DbSession,
    file: Annotated[UploadFile, File()],
) -> MediaUploadResult:
    if db.get(Organization, org_id) is None:
        raise NotFoundError("Organization not found")
    if file.content_type not in _ALLOWED_LOGO_CONTENT_TYPES:
        raise BadRequestError("Only PNG, JPEG, WebP, or GIF images are allowed")

    fileobj = file.file
    fileobj.seek(0, os.SEEK_END)
    size = fileobj.tell()
    fileobj.seek(0)
    if size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise BadRequestError(f"File exceeds the {settings.MAX_UPLOAD_MB}MB limit")

    stored = get_storage().save_stream(
        org_id=org_id,
        filename=file.filename or "organization-logo",
        content_type=file.content_type,
        fileobj=fileobj,
        size=size,
    )
    return MediaUploadResult(
        url=stored.url,
        storage_key=stored.key,
        filename=stored.filename,
        content_type=stored.content_type,
        size=stored.size,
    )
