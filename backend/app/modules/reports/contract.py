"""The single contract every report implements.

A report declares its `filters` (which the frontend renders into the filter bar)
and `columns`, and provides a `run(db, org_id, params)` that returns a
`ReportResult`. Everything else — listing, running, PDF/Excel export, and the
generic runner UI — is written once against this contract.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.orm import Session

FilterType = Literal["date_range", "date", "select", "text"]
ColumnType = Literal["text", "money", "number", "date"]
Align = Literal["left", "right"]


@dataclass
class Filter:
    key: str
    type: FilterType
    label: str
    required: bool = False
    default: object = None
    options: list[dict] | None = None  # static [{"value": ..., "label": ...}]
    source: str | None = None  # dynamic, org-specific options (e.g. "accounts")


@dataclass
class Column:
    key: str
    label: str
    type: ColumnType = "text"
    align: Align = "left"


@dataclass
class Section:
    rows: list[dict]
    title: str | None = None
    subtotal: dict | None = None


@dataclass
class ReportResult:
    title: str
    columns: list[Column]
    sections: list[Section]
    subtitle: str | None = None
    grand_total: dict | None = None


@dataclass
class ReportDef:
    key: str
    name: str
    category: str
    columns: list[Column]
    run: Callable[[Session, int, dict], ReportResult]
    filters: list[Filter] = field(default_factory=list)
    description: str | None = None
