from decimal import Decimal

import pytest

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.modules.accounting.models import Account
from app.modules.banks.schemas import BankAccountCreate, BankAccountUpdate
from app.modules.banks.service import BankAccountService
from app.modules.orgs.service import OrgService
from app.modules.users.models import User


def _org(db) -> int:
    user = User(email="bank@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    return org.id


def _payload(**overrides) -> BankAccountCreate:
    data = dict(
        bank_name="Meezan Bank",
        bank_code="MEZN",
        account_title="Acme Trading",
        account_number="0102030405",
        iban="PK36MEZN0000001234567890",
        branch="Gulberg",
        colour="#00694E",
    )
    data.update(overrides)
    return BankAccountCreate(**data)


def test_a_bank_account_gets_its_own_ledger_account(db):
    org_id = _org(db)
    bank = BankAccountService(db).create(org_id, _payload())

    account = db.get(Account, bank.account_id)
    assert account.name == "Meezan Bank — Acme Trading"
    assert account.is_postable is True
    # Numbered under Bank (1120), so it rolls up with the rest of the cash.
    parent = db.get(Account, account.parent_id)
    assert parent.code == "1120"
    assert account.code == "1121"
    assert bank.balance == Decimal("0")


def test_each_account_gets_a_distinct_code(db):
    org_id = _org(db)
    svc = BankAccountService(db)
    first = svc.create(org_id, _payload())
    second = svc.create(org_id, _payload(account_number="0999", account_title="Payroll"))

    codes = {db.get(Account, first.account_id).code, db.get(Account, second.account_id).code}
    assert codes == {"1121", "1122"}


def test_duplicate_account_numbers_are_refused(db):
    org_id = _org(db)
    svc = BankAccountService(db)
    svc.create(org_id, _payload())
    with pytest.raises(ConflictError):
        svc.create(org_id, _payload(account_title="Another"))


def test_renaming_updates_the_ledger_account_too(db):
    org_id = _org(db)
    svc = BankAccountService(db)
    bank = svc.create(org_id, _payload())
    svc.update(org_id, bank.id, BankAccountUpdate(account_title="Operations"))
    assert db.get(Account, bank.account_id).name == "Meezan Bank — Operations"


def test_an_account_with_history_cannot_be_deleted(db):
    from datetime import date

    from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
    from app.modules.accounting.enums import VoucherType
    from app.modules.accounting.service import JournalLine, PostingService
    from app.modules.settings.service import SettingsService

    org_id = _org(db)
    svc = BankAccountService(db)
    bank = svc.create(org_id, _payload())
    cash = int(SettingsService(db).get(org_id, ACCOUNTING_SETTINGS_GROUP, "cash"))

    PostingService(db).post_voucher(
        org_id,
        voucher_type=VoucherType.JOURNAL,
        posting_date=date.today(),
        lines=[
            JournalLine(account_id=bank.account_id, debit=Decimal("100")),
            JournalLine(account_id=cash, credit=Decimal("100")),
        ],
        description="Cash deposited",
    )
    db.flush()

    assert svc.get(org_id, bank.id).balance == Decimal("100.0000")
    with pytest.raises(ConflictError):
        svc.delete(org_id, bank.id)


def test_an_unused_account_is_removed_with_its_ledger_account(db):
    org_id = _org(db)
    svc = BankAccountService(db)
    bank = svc.create(org_id, _payload())
    account_id = bank.account_id
    svc.delete(org_id, bank.id)
    assert db.get(Account, account_id) is None
    assert svc.list(org_id) == []


def test_the_catalog_lists_pakistani_banks(db):
    from app.modules.banks.catalog import PAKISTANI_BANKS

    names = {b["name"] for b in PAKISTANI_BANKS}
    assert "Habib Bank Limited" in names
    assert "Meezan Bank" in names
    assert all(b["colour"].startswith("#") for b in PAKISTANI_BANKS)
