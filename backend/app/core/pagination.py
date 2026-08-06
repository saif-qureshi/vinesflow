"""Cursor-based (keyset) pagination for list endpoints.

Keyset pagination is O(1) regardless of depth and stable under inserts. We page
on the primary key (newest-first): the opaque cursor encodes the last seen id,
and the next page is ``id < cursor``.
"""

from __future__ import annotations

import base64
import binascii
from typing import TypeVar

from pydantic import BaseModel, Field
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql import Select

T = TypeVar("T")


def encode_cursor(value: int) -> str:
    return base64.urlsafe_b64encode(str(value).encode()).decode()


def decode_cursor(cursor: str) -> int | None:
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, binascii.Error):
        return None


class CursorParams(BaseModel):
    """Base cursor pagination. Endpoint query objects inherit from this."""

    cursor: str | None = None
    limit: int = Field(default=25, ge=1, le=100)


class ListQuery(CursorParams):
    """Base list query = pagination + free-text search. Modules extend this
    with their own filters (mirrors accountings' ListQueryDto)."""

    search: str | None = None


class CursorPage[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False


def paginate_cursor(
    db: Session,
    stmt: Select,
    id_col: InstrumentedAttribute,
    params: CursorParams,
) -> tuple[list, str | None, bool]:
    """Return (rows, next_cursor, has_more) for a newest-first keyset page."""
    if params.cursor:
        last_id = decode_cursor(params.cursor)
        if last_id is not None:
            stmt = stmt.where(id_col < last_id)

    rows = list(db.scalars(stmt.order_by(id_col.desc()).limit(params.limit + 1)).all())
    has_more = len(rows) > params.limit
    rows = rows[: params.limit]
    next_cursor = encode_cursor(rows[-1].id) if has_more and rows else None
    return rows, next_cursor, has_more
