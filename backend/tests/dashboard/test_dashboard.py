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
    assert status == {"Paid": 2, "Pending": 1, "Overdue": 1}

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
