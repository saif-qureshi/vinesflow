from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.reports.contract import ReportDef, ReportResult
from app.modules.reports.dates import resolve_range
from app.modules.reports.filters import apply_filters, operators_for
from app.modules.reports.registry import REPORTS


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_reports(self) -> list[dict]:
        return [
            {
                "key": r.key,
                "name": r.name,
                "category": r.category,
                "description": r.description,
            }
            for r in sorted(REPORTS.values(), key=lambda r: (r.category, r.name))
        ]

    def get(self, key: str) -> ReportDef:
        report = REPORTS.get(key)
        if report is None:
            raise NotFoundError("Report not found")
        return report

    def metadata(self, key: str, org_id: int) -> dict:
        report = self.get(key)
        filters = []
        for f in report.filters:
            data = asdict(f)
            if f.source:
                data["options"] = self._filter_options(org_id, f.source)
            filters.append(data)
        columns = []
        for c in report.columns:
            data = asdict(c)
            if report.supports_filters and c.filterable:
                data["operators"] = operators_for(c)
            columns.append(data)
        return {
            "key": report.key,
            "name": report.name,
            "category": report.category,
            "description": report.description,
            "supports_filters": report.supports_filters,
            "filters": filters,
            "columns": columns,
        }

    def _filter_options(self, org_id: int, source: str) -> list[dict]:
        from app.modules.accounting.models import Account
        from app.modules.parties.models import Party

        if source == "accounts":
            rows = self.db.execute(
                select(Account.id, Account.code, Account.name)
                .where(Account.org_id == org_id, Account.is_postable.is_(True))
                .order_by(Account.code)
            ).all()
            return [{"value": i, "label": f"{code} — {name}"} for i, code, name in rows]
        if source in ("locations", "brands", "manufacturers"):
            from app.modules.brands.models import Brand
            from app.modules.locations.models import Location
            from app.modules.manufacturers.models import Manufacturer

            model = {"locations": Location, "brands": Brand, "manufacturers": Manufacturer}[source]
            rows = self.db.execute(
                select(model.id, model.name).where(model.org_id == org_id).order_by(model.name)
            ).all()
            # A sentinel, because the runner's select cannot be cleared once set.
            label = {"locations": "All branches", "brands": "All brands",
                     "manufacturers": "All manufacturers"}[source]
            return [{"value": "", "label": label}] + [
                {"value": i, "label": name} for i, name in rows
            ]
        if source == "salespeople":
            from app.modules.salespeople.models import Salesperson

            rows = self.db.execute(
                select(Salesperson.id, Salesperson.name)
                .where(Salesperson.org_id == org_id)
                .order_by(Salesperson.name)
            ).all()
            return [{"value": "", "label": "All salespeople"}] + [
                {"value": i, "label": name} for i, name in rows
            ]
        if source in ("customers", "vendors", "parties"):
            stmt = select(Party.id, Party.name).where(Party.org_id == org_id)
            if source != "parties":
                column = Party.is_customer if source == "customers" else Party.is_vendor
                stmt = stmt.where(column.is_(True))
            rows = self.db.execute(stmt.order_by(Party.name)).all()
            return [{"value": i, "label": name} for i, name in rows]
        return []

    def resolve_params(self, report: ReportDef, org_id: int, raw: dict) -> dict:
        params: dict = {}
        for f in report.filters:
            if f.type == "date_range":
                preset = raw.get(f.key) or f.default or "this_month"
                start, end = resolve_range(
                    self.db,
                    org_id,
                    preset,
                    _parse_date(raw.get("from")),
                    _parse_date(raw.get("to")),
                )
                params["start"], params["end"] = start, end
                params["range_preset"] = preset
            elif f.type == "date":
                params[f.key] = _parse_date(raw.get(f.key)) or date.today()
            else:
                value = raw.get(f.key, f.default)
                params[f.key] = value
        return params

    def run(self, org_id: int, key: str, raw: dict) -> ReportResult:
        report = self.get(key)
        params = self.resolve_params(report, org_id, raw)
        result = report.run(self.db, org_id, params)
        if report.supports_filters:
            result = apply_filters(result, self._parse_filters(raw))
        return result

    @staticmethod
    def _parse_filters(raw: dict) -> list[dict]:
        try:
            parsed = json.loads(raw.get("filters") or "[]")
        except (ValueError, TypeError):
            return []
        return [f for f in parsed if isinstance(f, dict) and f.get("field") and f.get("op")]

    def run_json(self, org_id: int, key: str, raw: dict) -> dict:
        result = self.run(org_id, key, raw)
        return _jsonable(
            {
                "key": key,
                "title": result.title,
                "subtitle": result.subtitle,
                "columns": [asdict(c) for c in result.columns],
                "sections": [asdict(s) for s in result.sections],
                "grand_total": result.grand_total,
            }
        )
