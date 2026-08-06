"""Pluggable media storage. Local disk in dev, S3 in production.

The upload endpoint depends on the `Storage` protocol, so swapping backends is a
config change (STORAGE_BACKEND) — no code change at the call site.
"""

from __future__ import annotations

import re
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from app.core.config import settings

_MEDIA_CACHE_CONTROL = "public, max-age=31536000, immutable"
_KEY_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# Objects shared by every org rather than owned by one, e.g. bank logos.
CATALOG_ROOT = "catalog"


@dataclass
class StoredFile:
    url: str
    key: str
    filename: str
    content_type: str | None
    size: int


_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "application/pdf": ".pdf",
}


def _object_key(org_id: int, content_type: str | None) -> str:
    ext = _EXTENSIONS.get((content_type or "").lower(), "")
    return f"{settings.MEDIA_KEY_PREFIX}org-{org_id}/{uuid.uuid4().hex}{ext}"


def org_key_prefix(org_id: int) -> str:
    return f"{settings.MEDIA_KEY_PREFIX}org-{org_id}/"


def is_safe_key(key: str) -> bool:
    if not key or key.startswith("/") or "\\" in key:
        return False
    prefix = settings.MEDIA_KEY_PREFIX
    if prefix:
        if not key.startswith(prefix):
            return False
        key = key[len(prefix) :]
    segments = key.split("/")
    root = segments[0]
    if len(segments) < 2 or not (root == CATALOG_ROOT or root.startswith("org-")):
        return False
    return all(_KEY_SEGMENT.fullmatch(segment) for segment in segments)


def belongs_to_org(key: str, org_id: int) -> bool:
    """Deliberately excludes catalog keys: a client may reference its own
    objects only, never the shared ones."""
    return is_safe_key(key) and key.startswith(org_key_prefix(org_id))


def catalog_key(*parts: str) -> str:
    return f"{settings.MEDIA_KEY_PREFIX}{CATALOG_ROOT}/" + "/".join(parts)


class Storage(Protocol):
    def save_stream(
        self, *, org_id: int, filename: str, content_type: str | None, fileobj: BinaryIO, size: int
    ) -> StoredFile: ...
    def delete(self, key: str) -> None: ...

    def url_for(self, key: str) -> str: ...

    def get_bytes(self, key: str) -> bytes | None: ...
    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None: ...


class LocalStorage:
    """Writes to a local directory served by the app at /media/files."""

    def __init__(self) -> None:
        self.root = Path(settings.MEDIA_LOCAL_DIR)

    def save_stream(
        self, *, org_id: int, filename: str, content_type: str | None, fileobj: BinaryIO, size: int
    ) -> StoredFile:
        key = _object_key(org_id, content_type)
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as dest:
            shutil.copyfileobj(fileobj, dest)
        return StoredFile(
            url=self.url_for(key),
            key=key,
            filename=filename,
            content_type=content_type,
            size=size,
        )

    def url_for(self, key: str) -> str:
        return f"{settings.MEDIA_PUBLIC_URL.rstrip('/')}/media/files/{key}"

    def _path_for(self, key: str) -> Path | None:
        if not is_safe_key(key):
            return None
        root = self.root.resolve()
        path = (root / key).resolve()
        return path if path.is_relative_to(root) else None

    def delete(self, key: str) -> None:
        path = self._path_for(key)
        if path is not None:
            path.unlink(missing_ok=True)

    def get_bytes(self, key: str) -> bytes | None:
        path = self._path_for(key)
        return path.read_bytes() if path is not None and path.exists() else None

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        path = self._path_for(key)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


class S3Storage:
    def __init__(self) -> None:
        import boto3  # imported lazily so dev doesn't need it

        self.client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        self.bucket = settings.S3_BUCKET

    def save_stream(
        self, *, org_id: int, filename: str, content_type: str | None, fileobj: BinaryIO, size: int
    ) -> StoredFile:
        key = _object_key(org_id, content_type)
        self.client.upload_fileobj(
            fileobj,
            self.bucket,
            key,
            ExtraArgs={
                "ContentType": content_type or "application/octet-stream",
                "CacheControl": _MEDIA_CACHE_CONTROL,
            },
        )
        return StoredFile(
            url=self.url_for(key),
            key=key,
            filename=filename,
            content_type=content_type,
            size=size,
        )

    def url_for(self, key: str) -> str:
        base = (
            settings.S3_PUBLIC_URL
            or f"https://{self.bucket}.s3.{settings.S3_REGION}.amazonaws.com"
        )
        return f"{base.rstrip('/')}/{key}"

    def delete(self, key: str) -> None:
        if not is_safe_key(key):
            return
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def get_bytes(self, key: str) -> bytes | None:
        if not is_safe_key(key):
            return None
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except self.client.exceptions.NoSuchKey:
            return None
        return response["Body"].read()

    def put_bytes(self, key: str, data: bytes, *, content_type: str) -> None:
        if not is_safe_key(key):
            return
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)


def get_storage() -> Storage:
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalStorage()
