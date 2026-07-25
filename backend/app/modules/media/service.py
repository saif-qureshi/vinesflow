from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.storage import get_storage
from app.modules.media.models import MediaAsset
from app.modules.media.schemas import MediaCreate


class MediaService:
    """Manages the polymorphic media table for any attachable entity."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for(self, attachable_type: str, attachable_id: int) -> list[MediaAsset]:
        return list(
            self.db.scalars(
                select(MediaAsset)
                .where(
                    MediaAsset.attachable_type == attachable_type,
                    MediaAsset.attachable_id == attachable_id,
                )
                .order_by(MediaAsset.sort_order)
            ).all()
        )

    @staticmethod
    def _key_of(item: MediaCreate) -> str | None:
        return item.storage_key or get_storage().key_from_url(item.url)

    @staticmethod
    def _remove_object(key: str | None) -> None:
        if not key:
            return
        try:
            get_storage().delete(key)
        except Exception:
            pass  # object cleanup is best-effort; never fail the request over it

    def delete_for(self, attachable_type: str, attachable_id: int) -> None:
        for asset in self.list_for(attachable_type, attachable_id):
            self._remove_object(asset.storage_key)
        self.db.execute(
            delete(MediaAsset).where(
                MediaAsset.attachable_type == attachable_type,
                MediaAsset.attachable_id == attachable_id,
            )
        )

    def replace_for(
        self,
        *,
        org_id: int,
        attachable_type: str,
        attachable_id: int,
        media: list[MediaCreate],
    ) -> None:
        existing = self.list_for(attachable_type, attachable_id)
        kept = {self._key_of(m) for m in media}
        self.db.execute(
            delete(MediaAsset).where(
                MediaAsset.attachable_type == attachable_type,
                MediaAsset.attachable_id == attachable_id,
            )
        )
        for asset in existing:
            if asset.storage_key and asset.storage_key not in kept:
                self._remove_object(asset.storage_key)
        for i, item in enumerate(media):
            self.db.add(
                MediaAsset(
                    org_id=org_id,
                    attachable_type=attachable_type,
                    attachable_id=attachable_id,
                    url=item.url,
                    storage_key=self._key_of(item),
                    filename=item.filename,
                    content_type=item.content_type,
                    size=item.size,
                    sort_order=item.sort_order or i,
                )
            )
