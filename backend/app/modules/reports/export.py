from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.core.pdf import PdfService, page_footer_html
from app.modules.documents.print.mapper import branding_for
from app.modules.orgs.models import Organization
from app.modules.reports.contract import Column, ReportResult
from app.modules.reports.print import render_report_html

_MONEY_FMT = "#,##0.00"


def _cell_value(column: Column, row: dict):
    value = row.get(column.key)
    if value is None:
        return "" if column.type != "money" else None
    if column.type in ("money", "number") and isinstance(value, (Decimal, int, float)):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


# --- Excel ---------------------------------------------------------------


def to_xlsx(result: ReportResult) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = result.title[:31]
    bold = Font(bold=True)
    header_fill = PatternFill("solid", fgColor="F1F5F9")

    ws.append([result.title])
    ws.cell(row=1, column=1).font = Font(bold=True, size=14)
    if result.subtitle:
        ws.append([result.subtitle])
    ws.append([])

    header_row = ws.max_row + 1
    ws.append([c.label for c in result.columns])
    for idx, col in enumerate(result.columns, start=1):
        cell = ws.cell(row=header_row, column=idx)
        cell.font = bold
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="right" if col.align == "right" else "left")

    def write_row(row: dict, *, strong: bool = False):
        r = ws.max_row + 1
        for idx, col in enumerate(result.columns, start=1):
            cell = ws.cell(row=r, column=idx, value=_cell_value(col, row))
            if col.type == "money":
                cell.number_format = _MONEY_FMT
            if col.align == "right":
                cell.alignment = Alignment(horizontal="right")
            if strong:
                cell.font = bold

    for section in result.sections:
        if section.title:
            r = ws.max_row + 1
            ws.cell(row=r, column=1, value=section.title).font = bold
        for row in section.rows:
            write_row(row)
        if section.subtotal:
            write_row(section.subtotal, strong=True)

    if result.grand_total:
        write_row(result.grand_total, strong=True)

    for idx, col in enumerate(result.columns, start=1):
        width = max(len(col.label) + 2, 16 if col.type == "money" else 20)
        ws.column_dimensions[get_column_letter(idx)].width = width

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


# --- PDF -----------------------------------------------------------------


def to_pdf(result: ReportResult, org: Organization) -> bytes:
    branding = branding_for(org)
    footer = page_footer_html(branding.footer_text) if branding.footer_text else None
    return PdfService().html_to_pdf(render_report_html(result, org), paper="a4", footer_html=footer)
