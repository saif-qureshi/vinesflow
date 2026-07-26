from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.exceptions import BadRequestError
from app.modules.accounting.enums import (
    AccountType,
    FiscalYearStatus,
    NormalBalance,
    PeriodStatus,
    VoucherStatus,
    VoucherType,
)
from app.modules.accounting.models import (
    Account,
    AccountingPeriod,
    FiscalYear,
    LedgerEntry,
)
from app.modules.accounting.service import JournalLine, PostingService
from app.modules.orgs.models import Organization

POST_DATE = date(2026, 6, 15)


@pytest.fixture()
def org(db):
    org = Organization(name="Books Co", slug="books-co")
    db.add(org)
    db.flush()
    return org


@pytest.fixture()
def accounts(db, org):
    rows = {
        "cash": Account(
            org_id=org.id,
            code="1110",
            name="Cash",
            account_type=AccountType.ASSET,
            normal_balance=NormalBalance.DEBIT,
        ),
        "revenue": Account(
            org_id=org.id,
            code="4100",
            name="Sales Revenue",
            account_type=AccountType.INCOME,
            normal_balance=NormalBalance.CREDIT,
        ),
        "ar": Account(
            org_id=org.id,
            code="1130",
            name="Accounts Receivable",
            account_type=AccountType.ASSET,
            normal_balance=NormalBalance.DEBIT,
            is_control_account=True,
        ),
    }
    db.add_all(rows.values())
    db.flush()
    return rows


@pytest.fixture()
def period(db, org):
    fy = FiscalYear(
        org_id=org.id,
        name="FY2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
        status=FiscalYearStatus.ACTIVE,
    )
    db.add(fy)
    db.flush()
    period = AccountingPeriod(
        org_id=org.id,
        fiscal_year_id=fy.id,
        name="Jun 2026",
        period_no=6,
        starts_on=date(2026, 6, 1),
        ends_on=date(2026, 6, 30),
        status=PeriodStatus.OPEN,
    )
    db.add(period)
    db.flush()
    return period


def _jv(accounts, amount="100"):
    return [
        JournalLine(account_id=accounts["cash"].id, debit=Decimal(amount)),
        JournalLine(account_id=accounts["revenue"].id, credit=Decimal(amount)),
    ]


def _net(db, org_id, voucher_id=None):
    stmt = select(
        func.coalesce(func.sum(LedgerEntry.debit), 0)
        - func.coalesce(func.sum(LedgerEntry.credit), 0)
    ).where(LedgerEntry.org_id == org_id)
    if voucher_id is not None:
        stmt = stmt.where(LedgerEntry.voucher_id == voucher_id)
    return db.scalar(stmt)


def test_balanced_voucher_posts_and_writes_ledger(db, org, accounts, period):
    voucher = PostingService(db).post_voucher(
        org.id, voucher_type=VoucherType.JOURNAL, posting_date=POST_DATE, lines=_jv(accounts)
    )
    assert voucher.status == VoucherStatus.POSTED
    assert voucher.number == "JV0001"
    assert voucher.total_debit == Decimal("100.0000")
    assert voucher.period_id == period.id
    entries = db.scalars(select(LedgerEntry).where(LedgerEntry.voucher_id == voucher.id)).all()
    assert len(entries) == 2
    assert _net(db, org.id, voucher.id) == 0


def test_unbalanced_voucher_fails(db, org, accounts, period):
    lines = [
        JournalLine(account_id=accounts["cash"].id, debit=Decimal("100")),
        JournalLine(account_id=accounts["revenue"].id, credit=Decimal("90")),
    ]
    with pytest.raises(BadRequestError, match="equal"):
        PostingService(db).post_voucher(
            org.id, voucher_type=VoucherType.JOURNAL, posting_date=POST_DATE, lines=lines
        )


def test_single_line_fails(db, org, accounts, period):
    with pytest.raises(BadRequestError, match="at least two"):
        PostingService(db).post_voucher(
            org.id,
            voucher_type=VoucherType.JOURNAL,
            posting_date=POST_DATE,
            lines=[JournalLine(account_id=accounts["cash"].id, debit=Decimal("100"))],
        )


def test_line_cannot_have_both_debit_and_credit(db, org, accounts, period):
    lines = [
        JournalLine(account_id=accounts["cash"].id, debit=Decimal("100"), credit=Decimal("100")),
        JournalLine(account_id=accounts["revenue"].id, credit=Decimal("100")),
    ]
    with pytest.raises(BadRequestError, match="both"):
        PostingService(db).post_voucher(
            org.id, voucher_type=VoucherType.JOURNAL, posting_date=POST_DATE, lines=lines
        )


def test_no_period_covering_date_rejects(db, org, accounts, period):
    with pytest.raises(BadRequestError, match="No accounting period"):
        PostingService(db).post_voucher(
            org.id,
            voucher_type=VoucherType.JOURNAL,
            posting_date=date(2030, 1, 1),
            lines=_jv(accounts),
        )


def test_locked_period_rejects(db, org, accounts, period):
    period.status = PeriodStatus.LOCKED
    db.flush()
    with pytest.raises(BadRequestError, match="locked or closed"):
        PostingService(db).post_voucher(
            org.id, voucher_type=VoucherType.JOURNAL, posting_date=POST_DATE, lines=_jv(accounts)
        )


def test_closed_fiscal_year_rejects(db, org, accounts, period):
    period.fiscal_year.status = FiscalYearStatus.CLOSED
    db.flush()
    with pytest.raises(BadRequestError, match="closed fiscal year"):
        PostingService(db).post_voucher(
            org.id, voucher_type=VoucherType.JOURNAL, posting_date=POST_DATE, lines=_jv(accounts)
        )


def test_control_account_blocked_for_manual_jv_allowed_for_documents(db, org, accounts, period):
    svc = PostingService(db)
    control_lines = [
        JournalLine(account_id=accounts["ar"].id, debit=Decimal("100")),
        JournalLine(account_id=accounts["revenue"].id, credit=Decimal("100")),
    ]
    with pytest.raises(BadRequestError, match="control account"):
        svc.post_voucher(
            org.id, voucher_type=VoucherType.JOURNAL, posting_date=POST_DATE, lines=control_lines
        )
    voucher = svc.post_voucher(
        org.id,
        voucher_type=VoucherType.SALES_INVOICE,
        posting_date=POST_DATE,
        lines=control_lines,
        allow_control_accounts=True,
    )
    assert voucher.status == VoucherStatus.POSTED
    assert voucher.number == "SV0001"


def test_reversal_mirrors_and_nets_to_zero(db, org, accounts, period):
    svc = PostingService(db)
    voucher = svc.post_voucher(
        org.id,
        voucher_type=VoucherType.SALES_INVOICE,
        posting_date=POST_DATE,
        lines=[
            JournalLine(account_id=accounts["ar"].id, debit=Decimal("100")),
            JournalLine(account_id=accounts["revenue"].id, credit=Decimal("100")),
        ],
        allow_control_accounts=True,
    )
    reversal = svc.reverse_voucher(voucher)
    assert reversal.reversed_from_id == voucher.id
    assert reversal.number == "RV0001"
    assert voucher.status == VoucherStatus.REVERSED
    assert _net(db, org.id) == 0
    with pytest.raises(BadRequestError, match="Only posted"):
        svc.reverse_voucher(voucher)


def test_voucher_numbering_increments_per_type(db, org, accounts, period):
    svc = PostingService(db)
    first = svc.post_voucher(
        org.id, voucher_type=VoucherType.JOURNAL, posting_date=POST_DATE, lines=_jv(accounts)
    )
    second = svc.post_voucher(
        org.id, voucher_type=VoucherType.JOURNAL, posting_date=POST_DATE, lines=_jv(accounts)
    )
    assert (first.number, second.number) == ("JV0001", "JV0002")
