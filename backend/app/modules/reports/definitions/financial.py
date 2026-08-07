from __future__ import annotations

from app.modules.accounting.reports import ReportsService
from app.modules.reports.contract import Column, Filter, ReportDef, ReportResult, Section
from app.modules.reports.registry import register

AMOUNT_COLS = [Column("account", "Account"), Column("amount", "Amount", "money", "right")]
TB_COLS = [
    Column("account", "Account"),
    Column("debit", "Debit", "money", "right"),
    Column("credit", "Credit", "money", "right"),
]
GL_COLS = [
    Column("date", "Date", "date"),
    Column("voucher", "Voucher"),
    Column("number", "Number"),
    Column("description", "Description"),
    Column("debit", "Debit", "money", "right"),
    Column("credit", "Credit", "money", "right"),
    Column("balance", "Balance", "money", "right"),
]


def _label(item: dict) -> str:
    return f"{item['code']} — {item['name']}" if item.get("code") else item["name"]


def _period(params: dict) -> str:
    return f"From {params['start'].isoformat()} to {params['end'].isoformat()}"


def _rows(items: list[dict]) -> list[dict]:
    return [{"account": _label(i), "amount": i["amount"]} for i in items]


# --- Trial Balance -------------------------------------------------------


def _trial_balance(db, org_id, params) -> ReportResult:
    data = ReportsService(db).trial_balance(org_id, params["as_of"])
    rows = [
        {"account": _label(line), "debit": line["debit"], "credit": line["credit"]}
        for line in data["lines"]
    ]
    return ReportResult(
        title="Trial Balance",
        subtitle=f"As of {params['as_of'].isoformat()}",
        columns=TB_COLS,
        sections=[Section(rows=rows)],
        grand_total={
            "account": "Total",
            "debit": data["total_debit"],
            "credit": data["total_credit"],
        },
    )


register(
    ReportDef(
        key="trial_balance",
        name="Trial Balance",
        category="Financial",
        description="Debit and credit balance of every account.",
        columns=TB_COLS,
        filters=[Filter("as_of", "date", "As of date")],
        run=_trial_balance,
    )
)


# --- Profit and Loss -----------------------------------------------------


def _profit_and_loss(db, org_id, params) -> ReportResult:
    d = ReportsService(db).profit_and_loss(org_id, params["start"], params["end"])
    sections = [
        Section(
            title="Income",
            rows=_rows(d["income"]),
            subtotal={"account": "Total Income", "amount": d["total_income"]},
        ),
        Section(
            title="Cost of Goods Sold",
            rows=_rows(d["cost_of_sales"]),
            subtotal={"account": "Total Cost of Goods Sold", "amount": d["total_cost_of_sales"]},
        ),
        Section(rows=[], subtotal={"account": "Gross Profit", "amount": d["gross_profit"]}),
        Section(
            title="Operating Expenses",
            rows=_rows(d["operating_expenses"]),
            subtotal={
                "account": "Total Operating Expenses",
                "amount": d["total_operating_expenses"],
            },
        ),
    ]
    return ReportResult(
        title="Profit and Loss",
        subtitle=_period(params),
        columns=AMOUNT_COLS,
        sections=sections,
        grand_total={"account": "Net Profit / (Loss)", "amount": d["net_profit"]},
    )


register(
    ReportDef(
        key="profit_and_loss",
        name="Profit and Loss",
        category="Financial",
        description="Income, cost of sales and expenses over a period.",
        columns=AMOUNT_COLS,
        filters=[Filter("range", "date_range", "Date range", default="this_month")],
        run=_profit_and_loss,
        supports_filters=False,
    )
)


# --- Balance Sheet -------------------------------------------------------


def _balance_sheet(db, org_id, params) -> ReportResult:
    d = ReportsService(db).balance_sheet(org_id, params["as_of"])
    sections = [
        Section(
            title="Assets",
            rows=_rows(d["assets"]),
            subtotal={"account": "Total Assets", "amount": d["total_assets"]},
        ),
        Section(
            title="Liabilities",
            rows=_rows(d["liabilities"]),
            subtotal={"account": "Total Liabilities", "amount": d["total_liabilities"]},
        ),
        Section(
            title="Equity",
            rows=_rows(d["equity"]),
            subtotal={"account": "Total Equity", "amount": d["total_equity"]},
        ),
    ]
    return ReportResult(
        title="Balance Sheet",
        subtitle=f"As of {params['as_of'].isoformat()}",
        columns=AMOUNT_COLS,
        sections=sections,
        grand_total={
            "account": "Total Liabilities & Equity",
            "amount": d["total_liabilities_and_equity"],
        },
    )


register(
    ReportDef(
        key="balance_sheet",
        name="Balance Sheet",
        category="Financial",
        description="Assets, liabilities and equity as of a date.",
        columns=AMOUNT_COLS,
        filters=[Filter("as_of", "date", "As of date")],
        run=_balance_sheet,
        supports_filters=False,
    )
)


# --- Cash Flow -----------------------------------------------------------


def _cash_flow(db, org_id, params) -> ReportResult:
    d = ReportsService(db).cash_flow(org_id, params["start"], params["end"])
    sections = [
        Section(
            rows=[{"account": "Cash at the start of the period", "amount": d["opening_cash"]}],
        ),
        Section(
            title="Operating Activities",
            rows=_rows(d["operating"]),
            subtotal={"account": "Net Cash from Operating", "amount": d["total_operating"]},
        ),
        Section(
            title="Investing Activities",
            rows=_rows(d["investing"]),
            subtotal={"account": "Net Cash from Investing", "amount": d["total_investing"]},
        ),
        Section(
            title="Financing Activities",
            rows=_rows(d["financing"]),
            subtotal={"account": "Net Cash from Financing", "amount": d["total_financing"]},
        ),
        Section(
            rows=[{"account": "Net change in cash", "amount": d["net_change"]}],
        ),
    ]
    return ReportResult(
        title="Cash Flow Statement",
        subtitle=_period(params),
        columns=AMOUNT_COLS,
        sections=sections,
        grand_total={"account": "Cash at the end of the period", "amount": d["closing_cash"]},
    )


register(
    ReportDef(
        key="cash_flow",
        name="Cash Flow Statement",
        category="Financial",
        description="Where cash came from and where it went, from opening to closing balance.",
        columns=AMOUNT_COLS,
        filters=[Filter("range", "date_range", "Date range", default="this_month")],
        run=_cash_flow,
        supports_filters=False,
    )
)


# --- General Ledger ------------------------------------------------------


def _opening_row(balance) -> dict:
    return {
        "date": None,
        "voucher": "",
        "number": "",
        "description": "Opening balance",
        "debit": None,
        "credit": None,
        "balance": balance,
    }


def _closing_row(balance, label="Closing balance") -> dict:
    return {
        "date": None,
        "description": label,
        "debit": None,
        "credit": None,
        "balance": balance,
    }


def _entry_rows(entries: list[dict]) -> list[dict]:
    return [
        {
            "date": e["posting_date"],
            "voucher": e["voucher_type"],
            "number": e["number"],
            "description": e["description"],
            "debit": e["debit"],
            "credit": e["credit"],
            "balance": e["balance"],
        }
        for e in entries
    ]


def _statement_section(d: dict, title: str | None = None) -> Section:
    return Section(
        title=title,
        rows=[_opening_row(d["opening_balance"]), *_entry_rows(d["rows"])],
        subtotal=_closing_row(d["closing_balance"]),
    )


def _general_ledger(db, org_id, params) -> ReportResult:
    d = ReportsService(db).general_ledger(org_id, params["start"], params["end"])
    return ReportResult(
        title="General Ledger",
        subtitle=_period(params),
        columns=GL_COLS,
        sections=[
            _statement_section(account, f"{account['account_code']} — {account['account_name']}")
            for account in d["accounts"]
        ]
        or [Section(rows=[])],
        grand_total={
            "description": "Total",
            "debit": d["total_debit"],
            "credit": d["total_credit"],
            "balance": None,
        },
    )


register(
    ReportDef(
        key="general_ledger",
        name="General Ledger",
        category="Financial",
        description="Every posting in the period, grouped by account head.",
        columns=GL_COLS,
        filters=[Filter("range", "date_range", "Date range", default="this_month")],
        run=_general_ledger,
        supports_filters=False,
    )
)


# --- Account Statement ---------------------------------------------------


def _account_statement(db, org_id, params) -> ReportResult:
    account_id = params.get("account_id")
    if not account_id:
        return ReportResult(
            title="Account Statement",
            subtitle="Select an account to run this report",
            columns=GL_COLS,
            sections=[Section(rows=[])],
        )
    d = ReportsService(db).account_statement(
        org_id, int(account_id), params["start"], params["end"]
    )
    return ReportResult(
        title=f"Account Statement — {d['account_code']} {d['account_name']}",
        subtitle=_period(params),
        columns=GL_COLS,
        sections=[_statement_section(d)],
    )


register(
    ReportDef(
        key="account_statement",
        name="Account Statement",
        category="Financial",
        description="Every transaction posted to one account, with running balance.",
        columns=GL_COLS,
        filters=[
            Filter("account_id", "select", "Account", required=True, source="accounts"),
            Filter("range", "date_range", "Date range", default="this_fiscal_year"),
        ],
        run=_account_statement,
        supports_filters=False,
    )
)


# --- Party Ledger --------------------------------------------------------


def _party_ledger(db, org_id, params) -> ReportResult:
    party_id = params.get("party_id")
    if not party_id:
        return ReportResult(
            title="Party Ledger",
            subtitle="Select a customer or supplier to run this report",
            columns=GL_COLS,
            sections=[Section(rows=[])],
        )
    d = ReportsService(db).party_statement(org_id, int(party_id), params["start"], params["end"])
    return ReportResult(
        title=f"Party Ledger — {d['party_name']}",
        subtitle=_period(params),
        columns=GL_COLS,
        sections=[_statement_section(d)],
    )


register(
    ReportDef(
        key="party_ledger",
        name="Party Ledger",
        category="Financial",
        description="What one customer or supplier owes, and every document behind it.",
        columns=GL_COLS,
        filters=[
            Filter("party_id", "select", "Customer / Supplier", required=True, source="parties"),
            Filter("range", "date_range", "Date range", default="this_fiscal_year"),
        ],
        run=_party_ledger,
        supports_filters=False,
    )
)
