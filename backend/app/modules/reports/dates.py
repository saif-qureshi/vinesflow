from __future__ import annotations

import calendar
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounting.models import FiscalYear

DATE_RANGE_OPTIONS = [
    {"value": "today", "label": "Today"},
    {"value": "this_month", "label": "This Month"},
    {"value": "last_month", "label": "Last Month"},
    {"value": "this_quarter", "label": "This Quarter"},
    {"value": "last_quarter", "label": "Last Quarter"},
    {"value": "this_year", "label": "This Year"},
    {"value": "last_year", "label": "Last Year"},
    {"value": "this_fiscal_year", "label": "This Fiscal Year"},
    {"value": "last_fiscal_year", "label": "Last Fiscal Year"},
    {"value": "custom", "label": "Custom"},
]


def _month_end(day: date) -> date:
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])


def _fiscal_year(db: Session, org_id: int, target: date) -> FiscalYear | None:
    return db.scalar(
        select(FiscalYear).where(
            FiscalYear.org_id == org_id,
            FiscalYear.starts_on <= target,
            FiscalYear.ends_on >= target,
        )
    )


def resolve_range(
    db: Session,
    org_id: int,
    preset: str,
    from_date: date | None,
    to_date: date | None,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    today = today or date.today()
    if preset == "custom" and from_date and to_date:
        return from_date, to_date
    if preset == "today":
        return today, today
    if preset == "this_month":
        return date(today.year, today.month, 1), _month_end(today)
    if preset == "last_month":
        prev_end = date(today.year, today.month, 1) - timedelta(days=1)
        return date(prev_end.year, prev_end.month, 1), prev_end
    if preset in ("this_quarter", "last_quarter"):
        q = (today.month - 1) // 3
        if preset == "last_quarter":
            q -= 1
        year = today.year + (q // 4)
        q %= 4
        start_month = q * 3 + 1
        start = date(year, start_month, 1)
        end = _month_end(date(year, start_month + 2, 1))
        return start, end
    if preset == "this_year":
        return date(today.year, 1, 1), date(today.year, 12, 31)
    if preset == "last_year":
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    if preset in ("this_fiscal_year", "last_fiscal_year"):
        fy = _fiscal_year(db, org_id, today)
        if fy is not None:
            if preset == "this_fiscal_year":
                return fy.starts_on, fy.ends_on
            prev = _fiscal_year(db, org_id, fy.starts_on - timedelta(days=1))
            if prev is not None:
                return prev.starts_on, prev.ends_on
        return date(today.year, 1, 1), date(today.year, 12, 31)
    return date(today.year, today.month, 1), _month_end(today)
