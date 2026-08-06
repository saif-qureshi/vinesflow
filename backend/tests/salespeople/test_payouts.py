from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.exceptions import BadRequestError
from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
from app.modules.accounting.models import LedgerEntry
from app.modules.commissions.enums import CommissionPayoutStatus
from app.modules.commissions.schemas import CommissionPayoutCreate
from app.modules.commissions.service import CommissionService
from app.modules.documents.service import DocumentService
from app.modules.settings.service import SettingsService

from .test_commission import _invoice, _setup


def _acct(db, org_id, key):
    return int(SettingsService(db).get(org_id, ACCOUNTING_SETTINGS_GROUP, key))


def _bal(db, org_id, key):
    account_id = _acct(db, org_id, key)
    debit, credit = db.execute(
        select(
            func.coalesce(func.sum(LedgerEntry.debit), 0),
            func.coalesce(func.sum(LedgerEntry.credit), 0),
        ).where(LedgerEntry.org_id == org_id, LedgerEntry.account_id == account_id)
    ).first()
    return debit - credit


def _earned_invoice(db, org_id, party_id, pid, tax_id, rep_id):
    return _invoice(DocumentService(db), org_id, party_id, pid, tax_id, rep_id)


def test_balances_show_earned_paid_and_outstanding(db):
    org_id, party_id, pid, tax_id, rep_id = _setup(db)
    _earned_invoice(db, org_id, party_id, pid, tax_id, rep_id)
    svc = CommissionService(db)

    rows = svc.balances(org_id)
    assert [(r["earned"], r["paid"], r["outstanding"]) for r in rows] == [
        (Decimal("10.00"), Decimal("0"), Decimal("10.00"))
    ]

    payout = svc.create(
        org_id,
        CommissionPayoutCreate(
            salesperson_id=rep_id,
            amount=Decimal("4"),
            paid_through_account_id=_acct(db, org_id, "cash"),
        ),
    )
    assert payout.number.startswith("CP-")
    assert payout.status == CommissionPayoutStatus.DRAFT

    svc.submit(org_id, payout.id)
    rows = svc.balances(org_id)
    assert [(r["earned"], r["paid"], r["outstanding"]) for r in rows] == [
        (Decimal("10.00"), Decimal("4.00"), Decimal("6.00"))
    ]


def test_submitting_a_payout_posts_the_expense(db):
    org_id, party_id, pid, tax_id, rep_id = _setup(db)
    _earned_invoice(db, org_id, party_id, pid, tax_id, rep_id)
    svc = CommissionService(db)
    payout = svc.create(
        org_id,
        CommissionPayoutCreate(
            salesperson_id=rep_id,
            amount=Decimal("10"),
            paid_through_account_id=_acct(db, org_id, "cash"),
        ),
    )
    cash_before = _bal(db, org_id, "cash")

    svc.submit(org_id, payout.id)
    assert _bal(db, org_id, "sales_commission") == Decimal("10.00")
    assert _bal(db, org_id, "cash") - cash_before == Decimal("-10.00")

    svc.cancel(org_id, payout.id)
    assert _bal(db, org_id, "sales_commission") == Decimal("0")
    assert _bal(db, org_id, "cash") == cash_before


def test_cannot_pay_out_more_than_is_outstanding(db):
    org_id, party_id, pid, tax_id, rep_id = _setup(db)
    _earned_invoice(db, org_id, party_id, pid, tax_id, rep_id)
    svc = CommissionService(db)
    payout = svc.create(
        org_id,
        CommissionPayoutCreate(
            salesperson_id=rep_id,
            amount=Decimal("25"),
            paid_through_account_id=_acct(db, org_id, "cash"),
        ),
    )
    with pytest.raises(BadRequestError):
        svc.submit(org_id, payout.id)


def test_a_return_reduces_what_is_owed(db):
    from app.modules.documents.enums import DocumentType

    org_id, party_id, pid, tax_id, rep_id = _setup(db)
    docs = DocumentService(db)
    invoice = _earned_invoice(db, org_id, party_id, pid, tax_id, rep_id)
    note = docs.convert(org_id, invoice.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    docs.finalize(org_id, note.id)

    assert CommissionService(db).balance_for(org_id, rep_id) == Decimal("0.00")
