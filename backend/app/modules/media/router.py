from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.api.deps import CurrentMembership
from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.core.responses import EnvelopeRoute
from app.core.storage import get_storage
from app.modules.media.schemas import MediaUploadResult

router = APIRouter(prefix="/media", tags=["media"], route_class=EnvelopeRoute)


@router.post("/upload", response_model=MediaUploadResult)
async def upload_media(membership: CurrentMembership, file: UploadFile = File(...)):
    data = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise BadRequestError(f"File exceeds the {settings.MAX_UPLOAD_MB}MB limit")

    stored = get_storage().save(
        org_id=membership.org_id,
        filename=file.filename or "file",
        content_type=file.content_type,
        data=data,
    )
    return MediaUploadResult(
        url=stored.url,
        storage_key=stored.key,
        filename=stored.filename,
        content_type=stored.content_type,
        size=stored.size,
    )
