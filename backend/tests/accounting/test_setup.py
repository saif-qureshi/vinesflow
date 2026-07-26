from __future__ import annotations

from sqlalchemy import func, select

from app.core.security import hash_password
from app.modules.accounting.constants import (
    ACCOUNT_MAPPING,
    ACCOUNTING_SETTINGS_GROUP,
    DEFAULT_ACCOUNTS,
)
from app.modules.accounting.enums import FiscalYearStatus
from app.modules.accounting.models import Account, AccountingPeriod, FiscalYear
from app.modules.accounting.setup import AccountingSetupService
from app.modules.orgs.service import OrgService
from app.modules.settings.service import SettingsService
from app.modules.users.models import User


def _owner(db, email="acct-owner@test.io"):
    user = User(email=email, hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    return user


def _count(db, model, org_id):
    return db.scalar(select(func.count()).select_from(model).where(model.org_id == org_id))


def test_new_org_gets_chart_mapping_and_calendar(db):
    org = OrgService(db).create_org_with_owner(owner=_owner(db), name="Acct Co")
    db.flush()

    accounts = db.scalars(select(Account).where(Account.org_id == org.id)).all()
    assert len(accounts) == len(DEFAULT_ACCOUNTS)
    by_code = {a.code: a for a in accounts}

    assert by_code["1130"].is_control_account
    assert not by_code["1110"].is_control_account
    assert not by_code["1000"].is_postable
    assert by_code["1110"].parent_id == by_code["1100"].id

    mapping = SettingsService(db).get_group(org.id, ACCOUNTING_SETTINGS_GROUP)
    assert set(mapping) == set(ACCOUNT_MAPPING)
    assert mapping["sales_revenue"] == by_code["4100"].id
    assert mapping["accounts_receivable"] == by_code["1130"].id

    fiscal_year = db.scalar(select(FiscalYear).where(FiscalYear.org_id == org.id))
    assert fiscal_year.status == FiscalYearStatus.ACTIVE
    assert _count(db, AccountingPeriod, org.id) == 12


def test_ensure_setup_is_idempotent(db):
    org = OrgService(db).create_org_with_owner(owner=_owner(db), name="Acct Co")
    db.flush()
    AccountingSetupService(db).ensure_setup(org.id, org.fiscal_year_start_month)
    db.flush()
    assert _count(db, Account, org.id) == len(DEFAULT_ACCOUNTS)
    assert _count(db, AccountingPeriod, org.id) == 12
    assert _count(db, FiscalYear, org.id) == 1


def test_fiscal_calendar_respects_start_month(db):
    org = OrgService(db).create_org_with_owner(
        owner=_owner(db), name="Jan Co", fiscal_year_start_month=1
    )
    db.flush()
    fiscal_year = db.scalar(select(FiscalYear).where(FiscalYear.org_id == org.id))
    assert fiscal_year.starts_on.month == 1
    first = db.scalar(
        select(AccountingPeriod).where(
            AccountingPeriod.org_id == org.id, AccountingPeriod.period_no == 1
        )
    )
    assert first.starts_on.month == 1
    assert first.ends_on.month == 1
