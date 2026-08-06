from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.modules.dashboard.schemas import (
    AgingBucket,
    DashboardKpis,
    DashboardSummary,
    RecentInvoice,
    RevenuePoint,
    StatusCount,
)
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import Document
from app.modules.parties.models import Party

_ZERO = Decimal("0")
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _month_start(d: date) -> date:
    return d.replace(day=1)


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _sales(org_id: int):
        """Invoices and the credit notes that reduce them."""
        return and_(
            Document.org_id == org_id,
            Document.type.in_([DocumentType.INVOICE, DocumentType.CREDIT_NOTE]),
            Document.status == DocumentStatus.SENT,
        )

    @staticmethod
    def _net_revenue():
        """Revenue as the ledger sees it: excluding tax, net of returns."""
        sign = case((Document.type == DocumentType.CREDIT_NOTE, -1), else_=1)
        return sign * (Document.total - Document.tax_total - Document.further_tax_total)

    @staticmethod
    def _outstanding():
        return Document.total - Document.amount_paid - Document.amount_credited

    def _invoices(self, org_id: int):
        return and_(
            Document.org_id == org_id,
            Document.type == DocumentType.INVOICE,
            Document.status == DocumentStatus.SENT,
        )

    def summary(self, org_id: int, today: date) -> DashboardSummary:
        inv = self._invoices(org_id)
        outstanding = self._outstanding()
        unpaid = outstanding > _ZERO

        this_start = _month_start(today)
        last_start = _month_start(this_start - timedelta(days=1))
        sales = self._sales(org_id)
        revenue = self._net_revenue()
        rev_this = self.db.scalar(
            select(func.coalesce(func.sum(revenue), 0)).where(
                sales, Document.issue_date >= this_start
            )
        ) or _ZERO
        rev_last = self.db.scalar(
            select(func.coalesce(func.sum(revenue), 0)).where(
                sales, Document.issue_date >= last_start, Document.issue_date < this_start
            )
        ) or _ZERO
        delta = round(float((rev_this - rev_last) / rev_last * 100), 1) if rev_last else None

        receivables = self.db.scalar(
            select(func.coalesce(func.sum(outstanding), 0)).where(inv, unpaid)
        ) or _ZERO
        overdue = self.db.scalar(
            select(func.coalesce(func.sum(outstanding), 0)).where(
                inv, unpaid, Document.due_date.is_not(None), Document.due_date < today
            )
        ) or _ZERO
        customers = self.db.scalar(
            select(func.count(Party.id)).where(
                Party.org_id == org_id, Party.is_customer.is_(True), Party.is_active.is_(True)
            )
        ) or 0

        return DashboardSummary(
            kpis=DashboardKpis(
                revenue=rev_this,
                revenue_delta_pct=delta,
                receivables=receivables,
                overdue=overdue,
                active_customers=customers,
            ),
            revenue_series=self._revenue_series(org_id, today),
            aging=self._aging(org_id, today),
            invoice_status=self._status_counts(org_id, today),
            recent_invoices=self._recent(org_id, today),
        )

    def _revenue_series(self, org_id: int, today: date, months: int = 6) -> list[RevenuePoint]:
        sales = self._sales(org_id)
        revenue = self._net_revenue()
        starts: list[date] = []
        cursor = _month_start(today)
        for _ in range(months):
            starts.append(cursor)
            cursor = _month_start(cursor - timedelta(days=1))
        points: list[RevenuePoint] = []
        for start in reversed(starts):
            nxt = _month_start(start + timedelta(days=32))
            total = self.db.scalar(
                select(func.coalesce(func.sum(revenue), 0)).where(
                    sales, Document.issue_date >= start, Document.issue_date < nxt
                )
            ) or _ZERO
            points.append(RevenuePoint(month=_MONTHS[start.month - 1], revenue=total))
        return points

    def _aging(self, org_id: int, today: date) -> list[AgingBucket]:
        outstanding = self._outstanding()
        rows = self.db.execute(
            select(Document.due_date, outstanding).where(
                self._invoices(org_id), outstanding > _ZERO
            )
        ).all()
        buckets: dict[str, Decimal] = {"Current": _ZERO, "1-30": _ZERO, "31-60": _ZERO, "61-90": _ZERO, "90+": _ZERO}
        for due, amount in rows:
            amount = amount or _ZERO
            days = (today - due).days if due else 0
            if days <= 0:
                buckets["Current"] += amount
            elif days <= 30:
                buckets["1-30"] += amount
            elif days <= 60:
                buckets["31-60"] += amount
            elif days <= 90:
                buckets["61-90"] += amount
            else:
                buckets["90+"] += amount
        return [AgingBucket(bucket=name, amount=amount) for name, amount in buckets.items()]

    def _status_counts(self, org_id: int, today: date) -> list[StatusCount]:
        inv = self._invoices(org_id)
        unpaid = self._outstanding() > _ZERO

        def count(*where) -> int:
            return self.db.scalar(select(func.count(Document.id)).where(inv, *where)) or 0

        settled = count(self._outstanding() <= _ZERO)
        overdue = count(unpaid, Document.due_date.is_not(None), Document.due_date < today)
        pending = count(unpaid, or_(Document.due_date.is_(None), Document.due_date >= today))
        return [
            StatusCount(status="Settled", invoices=settled),
            StatusCount(status="Pending", invoices=pending),
            StatusCount(status="Overdue", invoices=overdue),
        ]

    def _recent(self, org_id: int, today: date, limit: int = 5) -> list[RecentInvoice]:
        rows = self.db.scalars(
            select(Document)
            .where(self._invoices(org_id))
            .order_by(Document.issue_date.desc(), Document.id.desc())
            .limit(limit)
        ).all()
        out: list[RecentInvoice] = []
        for d in rows:
            if d.balance_due <= _ZERO:
                status = "paid"
            elif d.due_date and d.due_date < today:
                status = "overdue"
            else:
                status = "pending"
            out.append(
                RecentInvoice(
                    id=d.id, number=d.number, party=d.party.name if d.party else None,
                    date=d.issue_date, amount=d.total, status=status,
                )
            )
        return out
