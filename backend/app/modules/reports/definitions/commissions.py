from __future__ import annotations

from decimal import Decimal

from app.modules.reports.contract import Column, ReportDef, ReportResult, Section
from app.modules.reports.registry import register

_ZERO = Decimal("0")

_COLUMNS = [
    Column("salesperson", "Salesperson"),
    Column("earned", "Earned", "money", "right"),
    Column("paid", "Paid", "money", "right"),
    Column("outstanding", "Outstanding", "money", "right"),
]


def _commission_summary(db, org_id, params):
    from app.modules.commissions.service import CommissionService

    rows = CommissionService(db).balances(org_id)
    section_rows = [
        {
            "salesperson": row["salesperson"].name,
            "earned": row["earned"],
            "paid": row["paid"],
            "outstanding": row["outstanding"],
        }
        for row in rows
    ]
    totals = {
        key: sum((row[key] for row in section_rows), _ZERO)
        for key in ("earned", "paid", "outstanding")
    }
    return ReportResult(
        title="Commission Summary",
        columns=_COLUMNS,
        sections=[Section(rows=section_rows)],
        grand_total={"salesperson": "Total", **totals},
    )


register(
    ReportDef(
        key="commission_summary",
        name="Commission Summary",
        category="Sales",
        description="Commission earned, paid and still owed per salesperson.",
        columns=_COLUMNS,
        run=_commission_summary,
    )
)
