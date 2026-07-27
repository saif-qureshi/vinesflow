"""Branded HTML for report PDFs.

Shares the document branding — org logo, accent colour and footer via
``branding_for`` — so an exported report looks like it belongs to the same
product as the invoices, without reusing the line-item document skin.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from jinja2 import Environment, StrictUndefined

from app.modules.documents.print.mapper import _logo_data_url, branding_for
from app.modules.orgs.models import Organization
from app.modules.reports.contract import Column, ReportResult

_env = Environment(autoescape=True, undefined=StrictUndefined)

_CSS = """
*{box-sizing:border-box}
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#0f172a;margin:0;font-size:12px}
.head{display:flex;align-items:center;gap:12px;border-bottom:2px solid var(--accent);padding-bottom:10px}
.logo{height:40px;max-width:170px;object-fit:contain}
.org{font-size:15px;font-weight:700;color:var(--accent)}
.titleblock{margin:14px 0 10px}
.title{font-size:18px;font-weight:700;margin:0}
.sub{color:#475569;font-size:12px;margin-top:2px}
.meta{color:#94a3b8;font-size:10px;margin-top:4px}
table{width:100%;border-collapse:collapse}
th{font-size:10px;text-transform:uppercase;letter-spacing:.03em;color:#64748b;
   border-bottom:1.5px solid #e2e8f0;padding:6px 8px}
td{padding:5px 8px;border-bottom:1px solid #f1f5f9}
.left{text-align:left}.right{text-align:right;font-variant-numeric:tabular-nums}
.section td{font-weight:700;color:var(--accent);padding-top:12px;border-bottom:none}
.subtotal td{font-weight:600;border-top:1px solid #e2e8f0}
.grand td{font-weight:700;border-top:2px solid var(--accent)}
tr{page-break-inside:avoid}
"""

_TEMPLATE = _env.from_string(
    """<!doctype html><html><head><meta charset="utf-8">
<style>:root{--accent:{{accent}}}{{css}}</style></head><body>
<div class="head">
  {% if logo %}<img class="logo" src="{{logo}}">{% endif %}
  <div class="org">{{company}}</div>
</div>
<div class="titleblock">
  <div class="title">{{title}}</div>
  {% if subtitle %}<div class="sub">{{subtitle}}</div>{% endif %}
  <div class="meta">Generated on {{generated}}{% if currency %} · Amounts in {{currency}}{% endif %}</div>
</div>
<table>
  <thead><tr>{% for c in columns %}<th class="{{c.align}}">{{c.label}}</th>{% endfor %}</tr></thead>
  <tbody>
    {% for s in sections %}
      {% if s.title %}<tr class="section"><td colspan="{{ncols}}">{{s.title}}</td></tr>{% endif %}
      {% for row in s.rows %}<tr>{% for cell in row %}<td class="{{cell.align}}">{{cell.value}}</td>{% endfor %}</tr>{% endfor %}
      {% if s.subtotal %}<tr class="subtotal">{% for cell in s.subtotal %}<td class="{{cell.align}}">{{cell.value}}</td>{% endfor %}</tr>{% endif %}
    {% endfor %}
    {% if grand_total %}<tr class="grand">{% for cell in grand_total %}<td class="{{cell.align}}">{{cell.value}}</td>{% endfor %}</tr>{% endif %}
  </tbody>
</table>
</body></html>"""
)


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
    columns = result.columns
    sections = [
        {
            "title": s.title,
            "rows": [_cells(columns, r) for r in s.rows],
            "subtotal": _cells(columns, s.subtotal) if s.subtotal else None,
        }
        for s in result.sections
    ]
    return _TEMPLATE.render(
        css=_CSS,
        accent=branding.accent_color or "#0f766e",
        logo=_logo_data_url(org),
        company=org.name,
        currency=getattr(org, "currency", None),
        title=result.title,
        subtitle=result.subtitle,
        generated=date.today().strftime("%d %b %Y"),
        columns=[{"label": c.label, "align": c.align} for c in columns],
        ncols=len(columns),
        sections=sections,
        grand_total=_cells(columns, result.grand_total) if result.grand_total else None,
    )
