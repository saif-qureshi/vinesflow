from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.modules.documents.enums import DocumentStatus, DocumentType, PaymentStatus
from app.modules.documents.models import Document
from app.modules.parties.models import Party
from app.modules.payments.models import Payment, PaymentAllocation
from app.modules.reports.contract import Column, Filter, ReportDef, ReportResult, Section
from app.modules.reports.registry import register

_ZERO = Decimal("0")

# The credit note type that writes value back against each kind of document.
_CREDIT_TYPE = {
    DocumentType.INVOICE: DocumentType.CREDIT_NOTE,
    DocumentType.BILL: DocumentType.VENDOR_CREDIT,
}

AGING = [
    ("current", "Current"),
    ("d1_30", "1 – 30"),
    ("d31_60", "31 – 60"),
    ("d61_90", "61 – 90"),
    ("d90", "91+"),
]


def _bucket(age_days: int) -> str:
    if age_days <= 0:
        return "current"
    if age_days <= 30:
        return "d1_30"
    if age_days <= 60:
        return "d31_60"
    if age_days <= 90:
        return "d61_90"
    return "d90"


# --- Outstanding as of a date --------------------------------------------


def _settled_by_document(db, org_id, doc_type, as_of) -> dict[int, Decimal]:
    """What had been taken off each document by `as_of` — payments applied and
    credit notes raised. Today's counters on the document cannot answer this,
    because they carry settlements made after the reporting date."""
    settled: dict[int, Decimal] = {}
    paid = db.execute(
        select(
            PaymentAllocation.document_id,
            func.coalesce(func.sum(PaymentAllocation.amount), 0),
        )
        .join(Payment, Payment.id == PaymentAllocation.payment_id)
        .where(
            Payment.org_id == org_id,
            Payment.status == PaymentStatus.SUBMITTED,
            Payment.posting_date <= as_of,
        )
        .group_by(PaymentAllocation.document_id)
    ).all()
    for document_id, amount in paid:
        settled[document_id] = settled.get(document_id, _ZERO) + amount

    credited = db.execute(
        select(
            Document.source_document_id,
            func.coalesce(func.sum(Document.settled_amount), 0),
        )
        .where(
            Document.org_id == org_id,
            Document.type == _CREDIT_TYPE[doc_type],
            Document.status == DocumentStatus.SENT,
            Document.source_document_id.is_not(None),
            Document.issue_date <= as_of,
        )
        .group_by(Document.source_document_id)
    ).all()
    for document_id, amount in credited:
        settled[document_id] = settled.get(document_id, _ZERO) + amount
    return settled


@dataclass
class Outstanding:
    """One thing still owed, whether it came from a document or from the balance
    the party carried in when the books started."""

    party_id: int | None
    aged_from: date
    balance: Decimal


def _party_openings(db, org_id, doc_type, as_of) -> list[Outstanding]:
    from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
    from app.modules.accounting.enums import VoucherType
    from app.modules.accounting.models import LedgerEntry
    from app.modules.settings.service import SettingsService

    key = "accounts_receivable" if doc_type == DocumentType.INVOICE else "accounts_payable"
    account_id = SettingsService(db).get(org_id, ACCOUNTING_SETTINGS_GROUP, key)
    if account_id is None:
        return []
    sign = 1 if doc_type == DocumentType.INVOICE else -1
    rows = db.execute(
        select(
            LedgerEntry.party_id,
            func.min(LedgerEntry.posting_date),
            func.coalesce(func.sum(LedgerEntry.debit - LedgerEntry.credit), 0),
        )
        .where(
            LedgerEntry.org_id == org_id,
            LedgerEntry.account_id == int(account_id),
            LedgerEntry.voucher_type == VoucherType.OPENING,
            LedgerEntry.party_id.is_not(None),
            LedgerEntry.posting_date <= as_of,
        )
        .group_by(LedgerEntry.party_id)
    ).all()
    return [
        Outstanding(party_id=party_id, aged_from=first, balance=total * sign)
        for party_id, first, total in rows
        if total * sign > _ZERO
    ]


def _open_documents(db, org_id, doc_type, as_of) -> list[Outstanding]:
    settled = _settled_by_document(db, org_id, doc_type, as_of)
    docs = db.scalars(
        select(Document).where(
            Document.org_id == org_id,
            Document.type == doc_type,
            Document.status == DocumentStatus.SENT,
            Document.issue_date <= as_of,
        )
    )
    open_items = []
    for doc in docs:
        balance = doc.total - settled.get(doc.id, _ZERO)
        if balance > _ZERO:
            open_items.append(
                Outstanding(
                    party_id=doc.party_id,
                    aged_from=doc.due_date or doc.issue_date,
                    balance=balance,
                )
            )
    return open_items + _party_openings(db, org_id, doc_type, as_of)


# --- Balance summaries ---------------------------------------------------


def _balance_summary(db, org_id, doc_type, party_label, as_of):
    names = dict(db.execute(select(Party.id, Party.name).where(Party.org_id == org_id)).all())
    balances: dict[int, Decimal] = {}
    for item in _open_documents(db, org_id, doc_type, as_of):
        balances[item.party_id] = balances.get(item.party_id, _ZERO) + item.balance

    section_rows = sorted(
        ({"party": names.get(pid, "—"), "balance": bal} for pid, bal in balances.items()),
        key=lambda r: r["party"],
    )
    total = sum((r["balance"] for r in section_rows), _ZERO)
    columns = [Column("party", party_label), Column("balance", "Balance Due", "money", "right")]
    return ReportResult(
        title=f"{party_label} Balance Summary",
        subtitle=f"As of {as_of.isoformat()}",
        columns=columns,
        sections=[Section(rows=section_rows)],
        grand_total={"party": "Total", "balance": total},
    )


def _customer_balance(db, org_id, params):
    return _balance_summary(db, org_id, DocumentType.INVOICE, "Customer", params["as_of"])


def _vendor_balance(db, org_id, params):
    return _balance_summary(db, org_id, DocumentType.BILL, "Vendor", params["as_of"])


# --- Aging ---------------------------------------------------------------


def _aging(db, org_id, doc_type, as_of, party_label):
    names = dict(db.execute(select(Party.id, Party.name).where(Party.org_id == org_id)).all())
    acc: dict[int, dict] = {}
    for item in _open_documents(db, org_id, doc_type, as_of):
        bucket = _bucket((as_of - item.aged_from).days)
        row = acc.setdefault(
            item.party_id,
            {
                "party": names.get(item.party_id, "—"),
                **{k: _ZERO for k, _ in AGING},
                "total": _ZERO,
            },
        )
        row[bucket] += item.balance
        row["total"] += item.balance

    rows = sorted(acc.values(), key=lambda r: r["party"])
    totals = {"party": "Total", "total": sum((r["total"] for r in rows), _ZERO)}
    for key, _ in AGING:
        totals[key] = sum((r[key] for r in rows), _ZERO)
    columns = [Column("party", party_label)]
    columns += [Column(key, label, "money", "right", filterable=False) for key, label in AGING]
    columns.append(Column("total", "Total", "money", "right"))
    return ReportResult(
        title=f"{party_label} Aging Summary",
        subtitle=f"As of {as_of.isoformat()}",
        columns=columns,
        sections=[Section(rows=rows)],
        grand_total=totals,
    )


def _ar_aging(db, org_id, params):
    return _aging(db, org_id, DocumentType.INVOICE, params["as_of"], "Customer")


def _ap_aging(db, org_id, params):
    return _aging(db, org_id, DocumentType.BILL, params["as_of"], "Vendor")


register(
    ReportDef(
        key="customer_balance_summary",
        name="Customer Balance Summary",
        category="Receivables",
        description="Outstanding balance owed by each customer.",
        columns=[Column("party", "Customer"), Column("balance", "Balance Due", "money", "right")],
        filters=[Filter("as_of", "date", "As of date")],
        run=_customer_balance,
    )
)
register(
    ReportDef(
        key="ar_aging_summary",
        name="AR Aging Summary",
        category="Receivables",
        description="Receivables bucketed by how overdue they are.",
        columns=[Column("party", "Customer")]
        + [Column(k, label, "money", "right", filterable=False) for k, label in AGING]
        + [Column("total", "Total", "money", "right")],
        filters=[Filter("as_of", "date", "As of date")],
        run=_ar_aging,
    )
)
register(
    ReportDef(
        key="vendor_balance_summary",
        name="Vendor Balance Summary",
        category="Payables",
        description="Outstanding balance owed to each vendor.",
        columns=[Column("party", "Vendor"), Column("balance", "Balance Due", "money", "right")],
        filters=[Filter("as_of", "date", "As of date")],
        run=_vendor_balance,
    )
)
register(
    ReportDef(
        key="ap_aging_summary",
        name="AP Aging Summary",
        category="Payables",
        description="Payables bucketed by how overdue they are.",
        columns=[Column("party", "Vendor")]
        + [Column(k, label, "money", "right", filterable=False) for k, label in AGING]
        + [Column("total", "Total", "money", "right")],
        filters=[Filter("as_of", "date", "As of date")],
        run=_ap_aging,
    )
)
