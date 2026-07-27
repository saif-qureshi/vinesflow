from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app.modules.accounting.models import Account
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import Document, DocumentLine
from app.modules.expenses.enums import ExpenseStatus
from app.modules.expenses.models import Expense, ExpenseLine
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.reports.contract import Column, Filter, ReportDef, ReportResult, Section
from app.modules.reports.registry import register

_ZERO = Decimal("0")


def _period(params: dict) -> str:
    return f"From {params['start'].isoformat()} to {params['end'].isoformat()}"


def _date_range_filter():
    return Filter("range", "date_range", "Date range", default="this_month")


# --- By item -------------------------------------------------------------


def _by_item(db, org_id, params, doc_type, title):
    rows = db.execute(
        select(
            DocumentLine.product_id,
            func.sum(DocumentLine.quantity),
            func.sum(DocumentLine.line_total - DocumentLine.tax_amount - DocumentLine.further_tax),
        )
        .join(Document, Document.id == DocumentLine.document_id)
        .where(
            Document.org_id == org_id,
            Document.type == doc_type,
            Document.status == DocumentStatus.SENT,
            Document.issue_date >= params["start"],
            Document.issue_date <= params["end"],
        )
        .group_by(DocumentLine.product_id)
    ).all()
    names: dict[int, str] = {}
    skus: dict[int, str | None] = {}
    for pid, name, sku in db.execute(
        select(Product.id, Product.name, Product.sku).where(Product.org_id == org_id)
    ).all():
        names[pid], skus[pid] = name, sku

    section_rows = []
    total_qty = total_amount = _ZERO
    for pid, qty, amount in rows:
        qty = qty or _ZERO
        amount = amount or _ZERO
        total_qty += qty
        total_amount += amount
        section_rows.append(
            {
                "item": names.get(pid, "Non-inventory / service"),
                "sku": skus.get(pid) or "",
                "quantity": qty,
                "amount": amount,
                "avg_price": (amount / qty) if qty else _ZERO,
            }
        )
    section_rows.sort(key=lambda r: r["amount"], reverse=True)
    columns = [
        Column("item", "Item"),
        Column("sku", "SKU"),
        Column("quantity", "Quantity", "number", "right"),
        Column("amount", "Amount", "money", "right"),
        Column("avg_price", "Avg Price", "money", "right"),
    ]
    return ReportResult(
        title=title,
        subtitle=_period(params),
        columns=columns,
        sections=[Section(rows=section_rows)],
        grand_total={"item": "Total", "quantity": total_qty, "amount": total_amount},
    )


def _sales_by_item(db, org_id, params):
    return _by_item(db, org_id, params, DocumentType.INVOICE, "Sales by Item")


def _purchases_by_item(db, org_id, params):
    return _by_item(db, org_id, params, DocumentType.BILL, "Purchases by Item")


# --- Sales by customer ---------------------------------------------------


def _sales_by_customer(db, org_id, params):
    rows = db.execute(
        select(Party.name, func.count(Document.id), func.coalesce(func.sum(Document.total), 0))
        .join(Document, Document.party_id == Party.id)
        .where(
            Document.org_id == org_id,
            Document.type == DocumentType.INVOICE,
            Document.status == DocumentStatus.SENT,
            Document.issue_date >= params["start"],
            Document.issue_date <= params["end"],
        )
        .group_by(Party.id)
        .order_by(func.coalesce(func.sum(Document.total), 0).desc())
    ).all()
    section_rows = [
        {"customer": name, "count": count, "amount": amount} for name, count, amount in rows
    ]
    total = sum((r["amount"] for r in section_rows), _ZERO)
    return ReportResult(
        title="Sales by Customer",
        subtitle=_period(params),
        columns=[
            Column("customer", "Customer"),
            Column("count", "Invoices", "number", "right"),
            Column("amount", "Amount", "money", "right"),
        ],
        sections=[Section(rows=section_rows)],
        grand_total={"customer": "Total", "amount": total},
    )


# --- Expenses by category ------------------------------------------------


def _expenses_by_category(db, org_id, params):
    rows = db.execute(
        select(Account.code, Account.name, func.coalesce(func.sum(ExpenseLine.amount), 0))
        .join(ExpenseLine, ExpenseLine.account_id == Account.id)
        .join(Expense, Expense.id == ExpenseLine.expense_id)
        .where(
            Expense.org_id == org_id,
            Expense.status == ExpenseStatus.SUBMITTED,
            Expense.expense_date >= params["start"],
            Expense.expense_date <= params["end"],
        )
        .group_by(Account.id)
        .order_by(func.coalesce(func.sum(ExpenseLine.amount), 0).desc())
    ).all()
    section_rows = [
        {"category": f"{code} — {name}", "amount": amount} for code, name, amount in rows
    ]
    total = sum((r["amount"] for r in section_rows), _ZERO)
    return ReportResult(
        title="Expenses by Category",
        subtitle=_period(params),
        columns=[Column("category", "Category"), Column("amount", "Amount", "money", "right")],
        sections=[Section(rows=section_rows)],
        grand_total={"category": "Total", "amount": total},
    )


register(
    ReportDef(
        key="sales_by_item",
        name="Sales by Item",
        category="Sales",
        description="Quantity and revenue sold per item.",
        columns=[
            Column("item", "Item"),
            Column("sku", "SKU"),
            Column("quantity", "Quantity", "number", "right"),
            Column("amount", "Amount", "money", "right"),
            Column("avg_price", "Avg Price", "money", "right"),
        ],
        filters=[_date_range_filter()],
        run=_sales_by_item,
    )
)
register(
    ReportDef(
        key="sales_by_customer",
        name="Sales by Customer",
        category="Sales",
        description="Invoiced revenue per customer.",
        columns=[
            Column("customer", "Customer"),
            Column("count", "Invoices", "number", "right"),
            Column("amount", "Amount", "money", "right"),
        ],
        filters=[_date_range_filter()],
        run=_sales_by_customer,
    )
)
register(
    ReportDef(
        key="purchases_by_item",
        name="Purchases by Item",
        category="Purchases and Expenses",
        description="Quantity and cost purchased per item.",
        columns=[
            Column("item", "Item"),
            Column("sku", "SKU"),
            Column("quantity", "Quantity", "number", "right"),
            Column("amount", "Amount", "money", "right"),
            Column("avg_price", "Avg Price", "money", "right"),
        ],
        filters=[_date_range_filter()],
        run=_purchases_by_item,
    )
)
register(
    ReportDef(
        key="expenses_by_category",
        name="Expenses by Category",
        category="Purchases and Expenses",
        description="Submitted expenses grouped by category account.",
        columns=[Column("category", "Category"), Column("amount", "Amount", "money", "right")],
        filters=[_date_range_filter()],
        run=_expenses_by_category,
    )
)
