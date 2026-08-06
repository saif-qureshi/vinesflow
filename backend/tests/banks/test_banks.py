import pathlib
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
        iban="PK36SCBL0000001123456702",
        branch="Gulberg",
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
    second = svc.create(org_id, _payload(account_number="0999888777", account_title="Payroll"))

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


def test_every_catalog_bank_ships_its_artwork(db):

    from app.modules.banks.catalog import LOGO_DIR, PAKISTANI_BANKS, logo_key

    codes = {bank["code"] for bank in PAKISTANI_BANKS}
    assert len(codes) == len(PAKISTANI_BANKS)  # codes are unique

    import app.modules.banks.catalog as catalog_module

    source = pathlib.Path(catalog_module.__file__).parent / LOGO_DIR
    for bank in PAKISTANI_BANKS:
        assert bank["logo"] == f"{bank['code'].lower()}.png"
        assert logo_key(bank["logo"]) == f"catalog/banks/{bank['logo']}"
    # Only U Microfinance is still without artwork.
    missing = [b["code"] for b in PAKISTANI_BANKS if not (source / b["logo"]).is_file()]
    assert missing == ["UMBL"]


def test_the_catalog_is_served_with_resolvable_urls(db):
    from app.core.storage import get_storage
    from app.modules.banks.catalog import PAKISTANI_BANKS, logo_key
    from app.modules.banks.schemas import BankOption

    storage = get_storage()
    options = [
        BankOption(**bank, logo_url=storage.url_for(logo_key(bank["logo"])))
        for bank in PAKISTANI_BANKS
    ]
    # Absolute, so any origin — and the PDF renderer — can use it.
    assert all(o.logo_url.startswith(("http://", "https://")) for o in options)
    assert options[0].logo_url.endswith("/catalog/banks/hbl.png")


@pytest.mark.parametrize(
    "number",
    ["445889652215236322das23132123123sad32as1d32as", "123", "abcdef", ""],
)
def test_junk_account_numbers_are_refused(db, number):
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        _payload(account_number=number)


def test_account_numbers_are_normalised(db):
    assert _payload(account_number="0102 0304 05").account_number == "0102030405"
    assert _payload(account_number="0102-0304-05").account_number == "0102-0304-05"


@pytest.mark.parametrize(
    "iban",
    [
        "1as23d123as1d23as1d32as1d2as",  # not an IBAN at all
        "PK99SCBL0000001123456702",  # right shape, wrong check digits
        "PK36SCBL",  # too short
    ],
)
def test_bad_ibans_are_refused(db, iban):
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        _payload(iban=iban)


def test_valid_ibans_are_normalised_and_optional(db):
    assert _payload(iban="pk36 scbl 0000 0011 2345 6702").iban == "PK36SCBL0000001123456702"
    assert _payload(iban="").iban is None
    assert _payload(iban=None).iban is None
