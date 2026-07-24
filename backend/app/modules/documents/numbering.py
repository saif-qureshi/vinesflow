from __future__ import annotations

from sqlalchemy import ColumnElement, Integer, cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.core.exceptions import ConflictError
from app.modules.settings.service import SettingsService

_MAX_RETRIES = 6
_DEFAULT_START = "0001"


def numbering_format(db: Session, org_id: int, key: str, default_prefix: str) -> tuple[str, str, str]:
    fmt = SettingsService(db).get(org_id, "numbering", key)
    if isinstance(fmt, dict):
        return (
            str(fmt.get("prefix") or default_prefix),
            str(fmt.get("start") or _DEFAULT_START),
            str(fmt.get("restart") or "none"),
        )
    return default_prefix, _DEFAULT_START, "none"


def _peak(db: Session, number_col: InstrumentedAttribute, *where: ColumnElement) -> int:
    value = db.scalar(
        select(func.coalesce(func.max(cast(func.substring(number_col, "[0-9]+$"), Integer)), 0)).where(
            *where
        )
    )
    return int(value or 0)


def preview_number(
    db: Session,
    number_col: InstrumentedAttribute,
    prefix: str,
    start: str,
    restart: str,
    year: int,
    *where: ColumnElement,
) -> str:
    body = f"{prefix}{year}-" if restart == "yearly" else prefix
    scope = (number_col.like(f"{body}%"),) if restart == "yearly" else ()
    seq = max(_peak(db, number_col, *where, *scope), int(start) - 1) + 1
    return f"{body}{seq:0{len(start)}d}"


def assign_number(
    db: Session,
    entity,
    number_col: InstrumentedAttribute,
    prefix: str,
    start: str,
    restart: str,
    year: int,
    *where: ColumnElement,
) -> None:
    width = len(start)
    start_value = int(start)
    body = f"{prefix}{year}-" if restart == "yearly" else prefix
    scope = (number_col.like(f"{body}%"),) if restart == "yearly" else ()

    def _make() -> str:
        seq = max(_peak(db, number_col, *where, *scope), start_value - 1) + 1
        return f"{body}{seq:0{width}d}"

    entity.number = _make()
    for _ in range(_MAX_RETRIES):
        savepoint = db.begin_nested()
        try:
            db.add(entity)
            db.flush()
            savepoint.commit()
            return
        except IntegrityError:
            savepoint.rollback()
            entity.number = _make()
    raise ConflictError("Could not assign a document number")
