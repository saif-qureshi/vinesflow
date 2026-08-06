from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.exceptions import BadRequestError
from app.core.security import hash_password
from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
from app.modules.accounting.enums import VoucherStatus, VoucherType
from app.modules.accounting.models import AccountingVoucher, LedgerEntry
from app.modules.expenses.enums import ExpenseStatus
from app.modules.expenses.schemas import ExpenseCreate, ExpenseLineInput, ExpenseUpdate
from app.modules.expenses.service import ExpenseService
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.settings.service import SettingsService
from app.modules.users.models import User


def _setup(db):
    user = User(email="expense@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    vendor = Party(org_id=org.id, is_vendor=True, name="Utility Co")
    db.add(vendor)
    db.flush()
    return org.id, vendor.id


def _acct(db, org_id, key):
    return int(SettingsService(db).get(org_id, ACCOUNTING_SETTINGS_GROUP, key))


def _bal(db, org_id, key):
    account_id = _acct(db, org_id, key)
    debit = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.debit), 0)).where(
            LedgerEntry.org_id == org_id, LedgerEntry.account_id == account_id
        )
    )
    credit = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.credit), 0)).where(
            LedgerEntry.org_id == org_id, LedgerEntry.account_id == account_id
        )
    )
    return debit - credit


def _tb_balances(db, org_id) -> bool:
    debit = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.debit), 0)).where(LedgerEntry.org_id == org_id)
    )
    credit = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.credit), 0)).where(LedgerEntry.org_id == org_id)
    )
    return debit == credit


def _create(db, org_id, vendor_id, **overrides):
    payload = dict(
        paid_through_account_id=_acct(db, org_id, "cash"),
        vendor_id=vendor_id,
        tax_amount=Decimal("180"),
        lines=[
            ExpenseLineInput(
                account_id=_acct(db, org_id, "operating_expenses"), amount=Decimal("1000")
            )
        ],
    )
    payload.update(overrides)
    return ExpenseService(db).create(org_id, ExpenseCreate(**payload))


def test_submit_expense_posts_balanced_double_entry(db):
    org_id, vendor_id = _setup(db)
    svc = ExpenseService(db)
    expense = _create(db, org_id, vendor_id)
    assert expense.status == ExpenseStatus.DRAFT
    assert expense.total == Decimal("1180")

    svc.submit(org_id, expense.id)

    voucher = db.scalar(
        select(AccountingVoucher).where(
            AccountingVoucher.source_type == "expense", AccountingVoucher.source_id == expense.id
        )
    )
    assert voucher is not None
    assert voucher.voucher_type == VoucherType.EXPENSE
    assert voucher.status == VoucherStatus.POSTED
    assert voucher.total_debit == voucher.total_credit

    assert _bal(db, org_id, "operating_expenses") == Decimal("1000")
    assert _bal(db, org_id, "input_tax") == Decimal("180")
    assert _bal(db, org_id, "cash") == Decimal("-1180")
    assert _tb_balances(db, org_id)


def test_itemized_expense_posts_each_category(db):
    org_id, vendor_id = _setup(db)
    svc = ExpenseService(db)
    expense = _create(
        db,
        org_id,
        vendor_id,
        tax_amount=Decimal("0"),
        lines=[
            ExpenseLineInput(
                account_id=_acct(db, org_id, "operating_expenses"), amount=Decimal("600")
            ),
            ExpenseLineInput(
                account_id=_acct(db, org_id, "inventory_adjustment"), amount=Decimal("400")
            ),
        ],
    )
    svc.submit(org_id, expense.id)

    assert _bal(db, org_id, "operating_expenses") == Decimal("600")
    assert _bal(db, org_id, "inventory_adjustment") == Decimal("400")
    assert _bal(db, org_id, "cash") == Decimal("-1000")
    assert _tb_balances(db, org_id)


def test_cancel_submitted_expense_reverses_to_zero(db):
    org_id, vendor_id = _setup(db)
    svc = ExpenseService(db)
    expense = _create(db, org_id, vendor_id)
    svc.submit(org_id, expense.id)
    svc.cancel(org_id, expense.id)

    assert svc.get(org_id, expense.id).status == ExpenseStatus.CANCELLED
    assert _bal(db, org_id, "operating_expenses") == Decimal("0")
    assert _bal(db, org_id, "cash") == Decimal("0")
    assert _tb_balances(db, org_id)


def test_submitted_expense_cannot_be_edited(db):
    org_id, vendor_id = _setup(db)
    svc = ExpenseService(db)
    expense = _create(db, org_id, vendor_id)
    svc.submit(org_id, expense.id)
    with pytest.raises(BadRequestError):
        svc.update(org_id, expense.id, ExpenseUpdate(reference_no="X"))


def test_tax_inclusive_expense_extracts_the_tax_instead_of_adding_it(db):
    org_id, vendor_id = _setup(db)
    svc = ExpenseService(db)
    # A 1,180 receipt whose price already contains 180 of sales tax.
    expense = _create(
        db,
        org_id,
        vendor_id,
        is_tax_inclusive=True,
        tax_amount=Decimal("180"),
        lines=[
            ExpenseLineInput(
                account_id=_acct(db, org_id, "operating_expenses"), amount=Decimal("1180")
            )
        ],
    )
    assert expense.total == Decimal("1180")
    assert expense.subtotal == Decimal("1000")
    assert expense.tax_amount == Decimal("180")

    svc.submit(org_id, expense.id)

    assert _bal(db, org_id, "operating_expenses") == Decimal("1000")
    assert _bal(db, org_id, "input_tax") == Decimal("180")
    assert _bal(db, org_id, "cash") == Decimal("-1180")
    assert _tb_balances(db, org_id)


def test_tax_inclusive_split_across_lines_still_balances(db):
    org_id, vendor_id = _setup(db)
    svc = ExpenseService(db)
    ops = _acct(db, org_id, "operating_expenses")
    expense = _create(
        db,
        org_id,
        vendor_id,
        is_tax_inclusive=True,
        tax_amount=Decimal("30"),
        lines=[
            ExpenseLineInput(account_id=ops, amount=Decimal("100")),
            ExpenseLineInput(account_id=ops, amount=Decimal("33.33")),
            ExpenseLineInput(account_id=ops, amount=Decimal("66.67")),
        ],
    )
    assert expense.total == Decimal("200")
    assert expense.subtotal == Decimal("170")

    svc.submit(org_id, expense.id)

    assert _bal(db, org_id, "operating_expenses") == Decimal("170")
    assert _bal(db, org_id, "cash") == Decimal("-200")
    assert _tb_balances(db, org_id)


def test_tax_cannot_exceed_a_tax_inclusive_amount(db):
    org_id, vendor_id = _setup(db)
    with pytest.raises(BadRequestError):
        _create(
            db,
            org_id,
            vendor_id,
            is_tax_inclusive=True,
            tax_amount=Decimal("500"),
            lines=[
                ExpenseLineInput(
                    account_id=_acct(db, org_id, "operating_expenses"), amount=Decimal("100")
                )
            ],
        )
