from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.storage import get_storage
from app.db.base_class import AuditMixin, Base, TimestampMixin


class MediaAsset(Base, TimestampMixin, AuditMixin):
    """Polymorphic media table shared across entities (products now, more later).

    Rows are linked by (attachable_type, attachable_id) and identify the file by
    its storage key alone. The public URL is derived from the key on read, so
    changing bucket, CDN domain or storage backend never strands stored rows.
    """

    __tablename__ = "media_assets"
    __table_args__ = (Index("ix_media_attachable", "org_id", "attachable_type", "attachable_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    attachable_type: Mapped[str] = mapped_column(String(50), nullable=False)
    attachable_id: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    @property
    def url(self) -> str:
        return get_storage().url_for(self.storage_key)
