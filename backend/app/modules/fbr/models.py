from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin

NONE_MARK = "__NONE__"


class FbrReferenceData(Base, TimestampMixin):
    __tablename__ = "fbr_reference_data"
    __table_args__ = (
        UniqueConstraint("type", "code", "parent_code", name="uq_fbr_reference_type_code_parent"),
        Index("ix_fbr_reference_type", "type"),
        Index("ix_fbr_reference_parent", "parent_type", "parent_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    parent_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    parent_code: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
