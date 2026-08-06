from datetime import date, timedelta
from decimal import Decimal

from app.core.security import hash_password
from app.modules.dashboard.service import DashboardService
from app.modules.documents.models import Invoice
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.users.models import User


def _setup(db):
    user = User(email="dash@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Dash Co")
    cust = Party(org_id=org.id, is_customer=True, name="ACME")
    db.add(cust)
    db.flush()
    return org, cust


def _inv(org, cust, n, total, paid, due, issue, ps):
    return Invoice(
        org_id=org.id, party_id=cust.id, status="sent", number=f"INV-{n:04d}",
        issue_date=issue, due_date=due, total=Decimal(total), amount_paid=Decimal(paid),
        payment_status=ps, subtotal=Decimal(total), discount_total=Decimal(0),
        tax_total=Decimal(0), shipping=Decimal(0), adjustment=Decimal(0),
    )


def test_dashboard_summary_aggregates(db):
    org, cust = _setup(db)
    today = date(2026, 7, 25)
    db.add_all([
        _inv(org, cust, 1, 1000, 1000, today, today, "paid"),
        _inv(org, cust, 2, 500, 0, today - timedelta(days=45), today, "unpaid"),
        _inv(org, cust, 3, 300, 100, today + timedelta(days=5), today, "partial"),
        _inv(org, cust, 4, 800, 800, date(2026, 6, 10), date(2026, 6, 10), "paid"),
    ])
    db.flush()

    s = DashboardService(db).summary(org.id, today)
    assert s.kpis.revenue == Decimal("1800")       # inv 1 + 2 + 3 (all issued in July)
    assert s.kpis.receivables == Decimal("700")    # inv 2 (500) + inv 3 outstanding (200)
    assert s.kpis.overdue == Decimal("500")        # inv 2, past due
    assert s.kpis.active_customers == 1

    status = {x.status: x.invoices for x in s.invoice_status}
    assert status == {"Settled": 2, "Pending": 1, "Overdue": 1}

    aging = {x.bucket: x.amount for x in s.aging}
    assert aging["Current"] == Decimal("200")      # inv 3, not yet due
    assert aging["31-60"] == Decimal("500")        # inv 2, 45 days overdue

    assert len(s.revenue_series) == 6
    assert s.recent_invoices[0].number == "INV-0003"


def test_dashboard_summary_empty_org(db):
    org, _ = _setup(db)
    s = DashboardService(db).summary(org.id, date(2026, 7, 25))
    assert s.kpis.revenue == Decimal("0")
    assert s.kpis.revenue_delta_pct is None
    assert len(s.revenue_series) == 6
    assert s.recent_invoices == []


def test_revenue_excludes_tax_and_nets_off_credit_notes(db):
    from app.modules.documents.models import CreditNote

    org, cust = _setup(db)
    today = date(2026, 7, 25)
    invoice = Invoice(
        org_id=org.id, party_id=cust.id, status="sent", number="INV-0001",
        issue_date=today, due_date=today, total=Decimal("1180"), amount_paid=Decimal(0),
        payment_status="unpaid", subtotal=Decimal("1000"), discount_total=Decimal(0),
        tax_total=Decimal("180"), shipping=Decimal(0), adjustment=Decimal(0),
    )
    note = CreditNote(
        org_id=org.id, party_id=cust.id, status="sent", number="CN-0001",
        issue_date=today, total=Decimal("236"), subtotal=Decimal("200"),
        discount_total=Decimal(0), tax_total=Decimal("36"),
        shipping=Decimal(0), adjustment=Decimal(0),
    )
    db.add_all([invoice, note])
    db.flush()

    s = DashboardService(db).summary(org.id, today)
    # 1000 sold less 200 returned; the 216 of sales tax is not revenue.
    assert s.kpis.revenue == Decimal("800")
    assert s.revenue_series[-1].revenue == Decimal("800")


def test_cash_flow_reads_cash_and_every_bank_account_under_it(db):
    from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
    from app.modules.accounting.enums import VoucherType
    from app.modules.accounting.service import JournalLine, PostingService
    from app.modules.banks.schemas import BankAccountCreate
    from app.modules.banks.service import BankAccountService
    from app.modules.settings.service import SettingsService

    org, _ = _setup(db)
    today = date(2026, 7, 25)
    cash = int(SettingsService(db).get(org.id, ACCOUNTING_SETTINGS_GROUP, "cash"))
    bank = BankAccountService(db).create(
        org.id,
        BankAccountCreate(
            bank_name="Meezan Bank", account_title="Acme", account_number="0102030405"
        ),
    )

    posting = PostingService(db)
    # Money in through the new bank account, money out through cash.
    posting.post_voucher(
        org.id,
        voucher_type=VoucherType.JOURNAL,
        posting_date=today,
        lines=[
            JournalLine(account_id=bank.account_id, debit=Decimal("1000")),
            JournalLine(account_id=cash, credit=Decimal("400")),
            JournalLine(
                account_id=int(
                    SettingsService(db).get(
                        org.id, ACCOUNTING_SETTINGS_GROUP, "operating_expenses"
                    )
                ),
                debit=Decimal("0"),
                credit=Decimal("600"),
            ),
        ],
        description="Mixed movement",
    )
    db.flush()

    s = DashboardService(db).summary(org.id, today)
    assert s.kpis.cash_on_hand == Decimal("600")  # 1000 into the bank less 400 out of cash
    this_month = s.cash_flow[-1]
    assert this_month.inflow == Decimal("1000")
    assert this_month.outflow == Decimal("400")
    assert this_month.net == Decimal("600")


def test_cash_flow_is_empty_when_nothing_has_moved(db):
    org, _ = _setup(db)
    s = DashboardService(db).summary(org.id, date(2026, 7, 25))
    assert s.kpis.cash_on_hand == Decimal("0")
    assert len(s.cash_flow) == 6
    assert all(p.inflow == Decimal("0") and p.outflow == Decimal("0") for p in s.cash_flow)
