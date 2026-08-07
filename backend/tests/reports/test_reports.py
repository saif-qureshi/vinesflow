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
    meta = ReportService(db).metadata("account_statement", org_id)
    account_filter = next(f for f in meta["filters"] if f["key"] == "account_id")
    assert account_filter["options"]  # populated from the org's chart


def test_cash_flow_classifies_movements_and_ties_to_the_cash_balance(db):
    from datetime import date

    from app.modules.accounting.models import Account
    from app.modules.accounting.schemas import JournalLineInput, JournalVoucherCreate
    from app.modules.accounting.vouchers import VoucherService

    org_id = _setup(db)  # the only cash movement so far is the 1000 expense
    result = ReportService(db).run(org_id, "cash_flow", {})
    operating = next(s for s in result.sections if s.title == "Operating Activities")
    assert operating.subtotal["amount"] == Decimal("-1000")
    assert _grand(result, "amount") == Decimal("-1000")

    owner_equity = db.scalar(
        select(Account.id).where(Account.org_id == org_id, Account.code == "3100")
    )
    vouchers = VoucherService(db)
    voucher = vouchers.create_journal_voucher(
        org_id,
        JournalVoucherCreate(
            date=date.today(),
            description="Owner puts money in",
            lines=[
                JournalLineInput(account_id=_acct(db, org_id, "bank"), debit=Decimal("5000")),
                JournalLineInput(account_id=owner_equity, credit=Decimal("5000")),
            ],
        ),
    )
    vouchers.post_journal_voucher(org_id, voucher.id)

    result = ReportService(db).run(org_id, "cash_flow", {})
    financing = next(s for s in result.sections if s.title == "Financing Activities")
    assert financing.subtotal["amount"] == Decimal("5000")  # equity, not operating
    assert _grand(result, "amount") == Decimal("4000")  # 5000 in, 1000 out


def test_general_ledger_groups_every_account_and_ties(db):
    org_id = _setup(db)
    result = ReportService(db).run(org_id, "general_ledger", {})
    titles = [s.title for s in result.sections]
    assert len(titles) > 1 and all(titles)  # one section per account head
    assert _grand(result, "debit") == _grand(result, "credit")
    for section in result.sections:
        assert section.rows[0]["description"] == "Opening balance"
        assert section.subtotal["description"] == "Closing balance"


def test_credit_normal_account_reads_positive(db):
    org_id = _setup(db)
    result = ReportService(db).run(
        org_id, "account_statement", {"account_id": _acct(db, org_id, "sales_revenue")}
    )
    # Revenue is credit-normal: 200 earned reads +200, matching the P&L.
    assert result.sections[0].subtotal["balance"] == Decimal("200")


def test_party_ledger_shows_what_the_customer_owes(db):
    org_id = _setup(db)
    customer = db.scalar(select(Party).where(Party.org_id == org_id, Party.is_customer.is_(True)))
    result = ReportService(db).run(org_id, "party_ledger", {"party_id": customer.id})
    section = result.sections[0]
    assert section.subtotal["balance"] == Decimal("236.00")  # 200 + 18% tax
    assert [r["description"] for r in section.rows][0] == "Opening balance"
    assert any(r["voucher"] == "sales_invoice" for r in section.rows[1:])


def test_party_ledger_flips_sign_for_a_supplier(db):
    org_id = _setup(db)
    vendor = Party(org_id=org_id, is_vendor=True, name="Supplier Ltd")
    db.add(vendor)
    db.flush()
    docs = DocumentService(db)
    bill = docs.create(
        org_id,
        DocumentType.BILL,
        DocumentCreate(
            party_id=vendor.id,
            lines=[
                DocumentLineInput(
                    description="Parts", quantity=Decimal("1"), unit_price=Decimal("500")
                )
            ],
        ),
    )
    docs.finalize(org_id, bill.id)

    result = ReportService(db).run(org_id, "party_ledger", {"party_id": vendor.id})
    # Payable is credit-normal: what the business owes reads positive, as on the Balance Sheet.
    assert result.sections[0].subtotal["balance"] == Decimal("500")


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


def test_inventory_summary_filters_and_totals_units(db):
    from app.modules.brands.models import Brand
    from app.modules.manufacturers.models import Manufacturer
    from app.modules.products.models import Product

    org_id = _setup(db)
    brand = Brand(org_id=org_id, name="Dove")
    maker = Manufacturer(org_id=org_id, name="Unilever")
    db.add_all([brand, maker])
    db.flush()
    product = db.scalar(select(Product).where(Product.org_id == org_id))
    product.brand_id = brand.id
    product.manufacturer_id = maker.id
    db.flush()

    svc = ReportService(db)
    summary = svc.run(org_id, "inventory_summary", {})
    assert summary.grand_total["quantity"] == Decimal("18")  # 20 opening less 2 invoiced
    assert summary.sections[0].rows[0]["brand"] == "Dove"
    assert summary.sections[0].rows[0]["manufacturer"] == "Unilever"

    # Filtering to another brand empties it.
    other = Brand(org_id=org_id, name="Lux")
    db.add(other)
    db.flush()
    filtered = svc.run(org_id, "inventory_summary", {"brand_id": str(other.id)})
    assert filtered.sections[0].rows == []
    assert filtered.grand_total["quantity"] == Decimal("0")


def test_inventory_summary_branch_filter_uses_stock_location(db):
    from app.modules.locations.models import Location

    org_id = _setup(db)
    svc = ReportService(db)
    warehouse = db.scalar(select(Location).where(Location.org_id == org_id))

    here = svc.run(org_id, "inventory_summary", {"location_id": str(warehouse.id)})
    assert here.grand_total["quantity"] == Decimal("18")

    elsewhere = Location(org_id=org_id, name="Store B")
    db.add(elsewhere)
    db.flush()
    away = svc.run(org_id, "inventory_summary", {"location_id": str(elsewhere.id)})
    assert away.grand_total["quantity"] == Decimal("0")
