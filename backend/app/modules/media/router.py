from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app.api.deps import CurrentMembership
from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.core.responses import EnvelopeRoute
from app.core.storage import get_storage
from app.modules.media.schemas import MediaUploadResult

router = APIRouter(prefix="/media", tags=["media"], route_class=EnvelopeRoute)

_ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "application/pdf",
}


@router.post("/upload", response_model=MediaUploadResult)
async def upload_media(membership: CurrentMembership, file: Annotated[UploadFile, File()]):
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise BadRequestError("Unsupported file type")

    fileobj = file.file
    fileobj.seek(0, os.SEEK_END)
    size = fileobj.tell()
    fileobj.seek(0)
    if size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise BadRequestError(f"File exceeds the {settings.MAX_UPLOAD_MB}MB limit")

    stored = get_storage().save_stream(
        org_id=membership.org_id,
        filename=file.filename or "file",
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
