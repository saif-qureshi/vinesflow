from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
from app.modules.documents.enums import DocumentType
from app.modules.documents.models import TaxRate
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput
from app.modules.documents.service import DocumentService
from app.modules.expenses.schemas import ExpenseCreate, ExpenseLineInput
from app.modules.expenses.service import ExpenseService
from app.modules.inventory.models import StockLevel, StockMovement
from app.modules.locations.models import Location
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.reports.export import to_xlsx
from app.modules.reports.registry import REPORTS
from app.modules.reports.service import ReportService
from app.modules.settings.service import SettingsService
from app.modules.users.models import User


def _acct(db, org_id, key):
    return int(SettingsService(db).get(org_id, ACCOUNTING_SETTINGS_GROUP, key))


def _setup(db):
    user = User(email="rep@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    customer = Party(org_id=org.id, is_customer=True, name="Beta Corp")
    product = Product(
        org_id=org.id,
        name="Widget",
        type="single",
        track_inventory=True,
        sale_price=Decimal("100"),
        purchase_price=Decimal("60"),
    )
    db.add_all([customer, product])
    db.flush()
    warehouse = db.scalar(select(Location).where(Location.org_id == org.id))
    db.add_all(
        [
            StockMovement(
                org_id=org.id,
                product_id=product.id,
                location_id=warehouse.id,
                qty_delta=Decimal("20"),
                type="opening",
                unit_cost=Decimal("60"),
            ),
            StockLevel(
                org_id=org.id,
                product_id=product.id,
                location_id=warehouse.id,
                quantity=Decimal("20"),
            ),
        ]
    )
    db.flush()

    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "GST 18%"))
    docs = DocumentService(db)
    inv = docs.create(
        org.id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=customer.id,
            lines=[
                DocumentLineInput(
                    product_id=product.id,
                    description="Widget",
                    quantity=Decimal("2"),
                    unit_price=Decimal("100"),
                    tax_rate_id=tax.id,
                )
            ],
        ),
    )
    docs.finalize(org.id, inv.id)

    ExpenseService(db).submit(
        org.id,
        ExpenseService(db)
        .create(
            org.id,
            ExpenseCreate(
                paid_through_account_id=_acct(db, org.id, "cash"),
                lines=[
                    ExpenseLineInput(
                        account_id=_acct(db, org.id, "operating_expenses"), amount=Decimal("1000")
                    )
                ],
            ),
        )
        .id,
    )
    return org.id


def _grand(result, key):
    return result.grand_total[key]


def test_registry_covers_all_categories():
    categories = {r.category for r in REPORTS.values()}
    assert {"Financial", "Receivables", "Payables", "Sales"} <= categories


def test_trial_balance_ties(db):
    org_id = _setup(db)
    result = ReportService(db).run(org_id, "trial_balance", {})
    assert _grand(result, "debit") == _grand(result, "credit")
    assert to_xlsx(result)  # exports without error


def test_profit_and_loss_nets_income_less_cogs_and_expense(db):
    org_id = _setup(db)
    result = ReportService(db).run(org_id, "profit_and_loss", {})
    # revenue 200 - COGS 120 - operating 1000 = -920
    assert _grand(result, "amount") == Decimal("-920")


def test_sales_by_item_and_expenses_by_category(db):
    org_id = _setup(db)
    svc = ReportService(db)
    sales = svc.run(org_id, "sales_by_item", {})
    rows = sales.sections[0].rows
    assert any(r["item"] == "Widget" and r["amount"] == Decimal("200") for r in rows)

    expenses = svc.run(org_id, "expenses_by_category", {})
    assert _grand(expenses, "amount") == Decimal("1000")


def test_customer_balance_summary_shows_unpaid_invoice(db):
    org_id = _setup(db)
    result = ReportService(db).run(org_id, "customer_balance_summary", {})
    assert _grand(result, "balance") == Decimal("236.00")  # 200 + 18% tax


def test_metadata_resolves_account_options(db):
    org_id = _setup(db)
    meta = ReportService(db).metadata("general_ledger", org_id)
    account_filter = next(f for f in meta["filters"] if f["key"] == "account_id")
    assert account_filter["options"]  # populated from the org's chart


def test_column_filter_keeps_matching_rows_and_recomputes_total(db):
    import json

    org_id = _setup(db)  # one Widget line, amount 200
    svc = ReportService(db)

    kept = svc.run(
        org_id,
        "sales_by_item",
        {"filters": json.dumps([{"field": "amount", "op": "gt", "value": "100"}])},
    )
    assert sum(len(s.rows) for s in kept.sections) == 1
    assert kept.grand_total["amount"] == Decimal("200")

    dropped = svc.run(
        org_id,
        "sales_by_item",
        {"filters": json.dumps([{"field": "amount", "op": "gt", "value": "500"}])},
    )
    assert sum(len(s.rows) for s in dropped.sections) == 0
    assert dropped.grand_total["amount"] == Decimal("0")


def test_statements_opt_out_of_column_filters(db):
    org_id = _setup(db)
    meta = ReportService(db).metadata("profit_and_loss", org_id)
    assert meta["supports_filters"] is False
    assert ReportService(db).metadata("sales_by_item", org_id)["supports_filters"] is True


def test_sales_reports_net_off_credit_notes(db):
    from app.modules.documents.models import Document

    org_id = _setup(db)
    docs = DocumentService(db)
    invoice = db.scalar(
        select(Document).where(
            Document.org_id == org_id, Document.type == DocumentType.INVOICE
        )
    )
    # Sold 2 at 100; the whole lot comes back.
    note = docs.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    docs.finalize(org_id, note.id)

    svc = ReportService(db)
    by_customer = svc.run(org_id, "sales_by_customer", {})
    assert by_customer.grand_total["amount"] == Decimal("0")

    by_item = svc.run(org_id, "sales_by_item", {})
    assert by_item.grand_total["amount"] == Decimal("0")
    assert by_item.grand_total["quantity"] == Decimal("0")
