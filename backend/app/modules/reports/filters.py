from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from app.modules.reports.contract import Column, ReportResult, Section

_ZERO = Decimal("0")

TEXT_OPS = [
    {"value": "contains", "label": "Contains"},
    {"value": "not_contains", "label": "Does not contain"},
    {"value": "is", "label": "Is"},
    {"value": "is_not", "label": "Is not"},
    {"value": "starts_with", "label": "Starts with"},
]
NUMBER_OPS = [
    {"value": "eq", "label": "Equals"},
    {"value": "ne", "label": "Not equal"},
    {"value": "gt", "label": "Greater than"},
    {"value": "gte", "label": "Greater or equal"},
    {"value": "lt", "label": "Less than"},
    {"value": "lte", "label": "Less or equal"},
    {"value": "between", "label": "Between"},
]
DATE_OPS = [
    {"value": "on", "label": "On"},
    {"value": "before", "label": "Before"},
    {"value": "after", "label": "After"},
    {"value": "between", "label": "Between"},
]


def filter_type(column: Column) -> str:
    if column.type in ("money", "number"):
        return "number"
    if column.type == "date":
        return "date"
    return "text"


def operators_for(column: Column) -> list[dict]:
    kind = filter_type(column)
    return NUMBER_OPS if kind == "number" else DATE_OPS if kind == "date" else TEXT_OPS


def is_sum(column: Column) -> bool:
    if column.aggregate == "sum":
        return True
    if column.aggregate == "none":
        return False
    return column.type in ("money", "number")


def _num(value) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_date(value) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _pair(value):
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return value[0], value[1]
    return None, None


def _match(column: Column, raw, op: str, value) -> bool:
    kind = filter_type(column)
    if kind == "number":
        a = _num(raw)
        if a is None:
            return False
        if op == "between":
            lo, hi = _pair(value)
            lo, hi = _num(lo), _num(hi)
            return lo is not None and hi is not None and lo <= a <= hi
        b = _num(value)
        if b is None:
            return False
        return {
            "eq": a == b,
            "ne": a != b,
            "gt": a > b,
            "gte": a >= b,
            "lt": a < b,
            "lte": a <= b,
        }.get(op, False)
    if kind == "date":
        a = _to_date(raw)
        if a is None:
            return False
        if op == "between":
            lo, hi = _pair(value)
            lo, hi = _to_date(lo), _to_date(hi)
            return lo is not None and hi is not None and lo <= a <= hi
        b = _to_date(value)
        if b is None:
            return False
        return {"on": a == b, "before": a < b, "after": a > b}.get(op, False)
    text = ("" if raw is None else str(raw)).lower()
    needle = ("" if value is None else str(value)).lower()
    return {
        "contains": needle in text,
        "not_contains": needle not in text,
        "is": text == needle,
        "is_not": text != needle,
        "starts_with": text.startswith(needle),
    }.get(op, False)


def _recompute(base: dict, sum_cols: list[Column], rows: list[dict]) -> dict:
    out = dict(base)
    for col in sum_cols:
        out[col.key] = sum((_num(r.get(col.key)) or _ZERO for r in rows), _ZERO)
    return out


def apply_filters(result: ReportResult, filters: list[dict]) -> ReportResult:
    if not filters:
        return result
    columns = {c.key: c for c in result.columns}
    sum_cols = [c for c in result.columns if is_sum(c)]

    def keep(row: dict) -> bool:
        for f in filters:
            col = columns.get(f.get("field"))
            if col is None:
                continue
            if not _match(col, row.get(col.key), f.get("op"), f.get("value")):
                return False
        return True

    sections = []
    all_rows: list[dict] = []
    for section in result.sections:
        rows = [r for r in section.rows if keep(r)]
        all_rows.extend(rows)
        subtotal = _recompute(section.subtotal, sum_cols, rows) if section.subtotal else None
        sections.append(Section(rows=rows, title=section.title, subtotal=subtotal))

    grand = _recompute(result.grand_total, sum_cols, all_rows) if result.grand_total else None
    return ReportResult(
        title=result.title,
        columns=result.columns,
        sections=sections,
        subtitle=result.subtitle,
        grand_total=grand,
    )
