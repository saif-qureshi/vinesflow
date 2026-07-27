"""Branded HTML for report PDFs.

Shares the document branding — org logo, accent colour and footer via
``branding_for`` — so an exported report looks like it belongs to the same
product as the invoices, without reusing the line-item document skin. Template
and stylesheet are read per render (like the document skins) so edits hot-reload.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, StrictUndefined

from app.modules.documents.print.mapper import _logo_data_url, branding_for
from app.modules.orgs.models import Organization
from app.modules.reports.contract import Column, ReportResult

_ASSETS = Path(__file__).parent / "print_assets"
_env = Environment(autoescape=True, undefined=StrictUndefined)


def _value(column: Column, row: dict) -> str:
    raw = row.get(column.key)
    if raw is None or raw == "":
        return ""
    if column.type == "money" and isinstance(raw, (Decimal, int, float)):
        return f"{float(raw):,.2f}"
    if column.type == "number" and isinstance(raw, (Decimal, int, float)):
        return f"{float(raw):,g}"
    if isinstance(raw, date):
        return raw.strftime("%d %b %Y")
    return str(raw)


def _cells(columns: list[Column], row: dict) -> list[dict]:
    return [{"value": _value(c, row), "align": c.align} for c in columns]


def render_report_html(result: ReportResult, org: Organization) -> str:
    branding = branding_for(org)
    accent = branding.accent_color or "#0f766e"
    columns = result.columns
    template = _env.from_string((_ASSETS / "report.jinja").read_text(encoding="utf-8"))
    body = template.render(
        logo=_logo_data_url(org),
        company=org.name,
        currency=getattr(org, "currency", None),
        title=result.title,
        subtitle=result.subtitle,
        generated=date.today().strftime("%d %b %Y"),
        columns=[{"label": c.label, "align": c.align} for c in columns],
        ncols=len(columns),
        sections=[
            {
                "title": s.title,
                "rows": [_cells(columns, r) for r in s.rows],
                "subtotal": _cells(columns, s.subtotal) if s.subtotal else None,
            }
            for s in result.sections
        ],
        grand_total=_cells(columns, result.grand_total) if result.grand_total else None,
    )
    css = (_ASSETS / "report.css").read_text(encoding="utf-8")
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<style>{css}:root{{--accent:{accent}}}</style></head><body>{body}</body></html>"
    )
