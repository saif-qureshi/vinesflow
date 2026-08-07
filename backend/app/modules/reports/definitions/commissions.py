from __future__ import annotations

from decimal import Decimal

from app.modules.reports.contract import Column, Filter, ReportDef, ReportResult, Section
from app.modules.reports.registry import register

_ZERO = Decimal("0")

_COLUMNS = [
    Column("salesperson", "Salesperson"),
    Column("opening", "Opening", "money", "right"),
    Column("earned", "Earned", "money", "right"),
    Column("paid", "Paid", "money", "right"),
    Column("outstanding", "Outstanding", "money", "right"),
]

_DETAIL_COLUMNS = [
    Column("date", "Date", "date"),
    Column("number", "Document"),
    Column("customer", "Customer"),
    Column("salesperson", "Salesperson"),
    Column("amount", "Document Total", "money", "right"),
    Column("rate", "Rate %", "number", "right"),
    Column("commission", "Commission", "money", "right"),
]


def _period(params: dict) -> str:
    return f"From {params['start'].isoformat()} to {params['end'].isoformat()}"


def _commission_summary(db, org_id, params):
    from app.modules.commissions.service import CommissionService

    rows = CommissionService(db).balances(org_id, params["start"], params["end"])
    section_rows = [
        {
            "salesperson": row["salesperson"].name,
            "opening": row["opening"],
            "earned": row["earned"],
            "paid": row["paid"],
            "outstanding": row["outstanding"],
        }
        for row in rows
    ]
    totals = {
        key: sum((row[key] for row in section_rows), _ZERO)
        for key in ("opening", "earned", "paid", "outstanding")
    }
    return ReportResult(
        title="Commission Summary",
        subtitle=_period(params),
        columns=_COLUMNS,
        sections=[Section(rows=section_rows)],
        grand_total={"salesperson": "Total", **totals},
    )


register(
    ReportDef(
        key="commission_summary",
        name="Commission Summary",
        category="Sales",
        description="Commission owed at the start, earned, paid and still owed per salesperson.",
        columns=_COLUMNS,
        filters=[Filter("range", "date_range", "Date range", default="this_month")],
        run=_commission_summary,
    )
)


def _commission_detail(db, org_id, params):
    from app.modules.commissions.service import CommissionService

    salesperson_id = params.get("salesperson_id")
    docs = CommissionService(db).earnings(
        org_id,
        params["start"],
        params["end"],
        int(salesperson_id) if salesperson_id else None,
    )
    # A credit note gives back the commission its invoice paid out.
    sign = {"credit_note": -1}
    rows = [
        {
            "date": doc.issue_date,
            "number": doc.number,
            "customer": doc.party.name if doc.party else "—",
            "salesperson": doc.salesperson.name if doc.salesperson else "—",
            "amount": doc.total * sign.get(doc.type, 1),
            "rate": doc.commission_rate,
            "commission": doc.commission_amount * sign.get(doc.type, 1),
        }
        for doc in docs
    ]
    return ReportResult(
        title="Commission Detail",
        subtitle=_period(params),
        columns=_DETAIL_COLUMNS,
        sections=[Section(rows=rows)],
        grand_total={
            "date": None,
            "number": "Total",
            "amount": sum((r["amount"] for r in rows), _ZERO),
            "commission": sum((r["commission"] for r in rows), _ZERO),
        },
    )


register(
    ReportDef(
        key="commission_detail",
        name="Commission Detail",
        category="Sales",
        description="Every document that earned commission, and what it paid.",
        columns=_DETAIL_COLUMNS,
        filters=[
            Filter("salesperson_id", "select", "Salesperson", source="salespeople"),
            Filter("range", "date_range", "Date range", default="this_month"),
        ],
        run=_commission_detail,
    )
)
