from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DashboardKpis(BaseModel):
    revenue: Decimal
    revenue_delta_pct: float | None = None
    receivables: Decimal
    overdue: Decimal
    active_customers: int
    cash_on_hand: Decimal = Decimal("0")


class RevenuePoint(BaseModel):
    month: str
    revenue: Decimal


class CashFlowPoint(BaseModel):
    month: str
    inflow: Decimal
    outflow: Decimal
    net: Decimal


class AgingBucket(BaseModel):
    bucket: str
    amount: Decimal


class StatusCount(BaseModel):
    status: str
    invoices: int


class RecentInvoice(BaseModel):
    id: int
    number: str
    party: str | None
    date: date
    amount: Decimal
    status: str


class DashboardSummary(BaseModel):
    kpis: DashboardKpis
    revenue_series: list[RevenuePoint]
    cash_flow: list[CashFlowPoint]
    aging: list[AgingBucket]
    invoice_status: list[StatusCount]
    recent_invoices: list[RecentInvoice]
