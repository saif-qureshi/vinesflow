"""Pluggable media storage. Local disk in dev, S3 in production.

The upload endpoint depends on the `Storage` protocol, so swapping backends is a
config change (STORAGE_BACKEND) — no code change at the call site.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import settings


@dataclass
class StoredFile:
    url: str
    key: str
    filename: str
    content_type: str | None
    size: int


def _object_key(org_id: int, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return f"org-{org_id}/{uuid.uuid4().hex}{ext}"


def _key_from_url(url: str) -> str | None:
    # Keys always start with the org partition, so recover them base-independently.
    idx = url.find("org-")
    return url[idx:] if idx != -1 else None


class Storage(Protocol):
    def save(self, *, org_id: int, filename: str, content_type: str | None, data: bytes) -> StoredFile: ...
    def delete(self, key: str) -> None: ...

    def key_from_url(self, url: str) -> str | None: ...


class LocalStorage:
    """Writes to a local directory served by the app at /media/files."""

    def __init__(self) -> None:
        self.root = Path(settings.MEDIA_LOCAL_DIR)

    def save(self, *, org_id: int, filename: str, content_type: str | None, data: bytes) -> StoredFile:
        key = _object_key(org_id, filename)
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        url = f"{settings.MEDIA_PUBLIC_URL.rstrip('/')}/media/files/{key}"
        return StoredFile(url=url, key=key, filename=filename, content_type=content_type, size=len(data))

    def delete(self, key: str) -> None:
        (self.root / key).unlink(missing_ok=True)

    def key_from_url(self, url: str) -> str | None:
        return _key_from_url(url)


class S3Storage:
    def __init__(self) -> None:
        import boto3  # imported lazily so dev doesn't need it

        self.client = boto3.client(
            "s3", region_name=settings.S3_REGION, endpoint_url=settings.S3_ENDPOINT_URL
        )
        self.bucket = settings.S3_BUCKET

    def save(self, *, org_id: int, filename: str, content_type: str | None, data: bytes) -> StoredFile:
        key = _object_key(org_id, filename)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type or "application/octet-stream",
        )
        base = settings.S3_PUBLIC_URL or f"https://{self.bucket}.s3.{settings.S3_REGION}.amazonaws.com"
        return StoredFile(
            url=f"{base.rstrip('/')}/{key}", key=key, filename=filename, content_type=content_type, size=len(data)
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def key_from_url(self, url: str) -> str | None:
        return _key_from_url(url)


def get_storage() -> Storage:
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalStorage()
