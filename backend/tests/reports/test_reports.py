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
