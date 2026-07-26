from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounting.constants import (
    ACCOUNT_MAPPING,
    ACCOUNTING_SETTINGS_GROUP,
    DEFAULT_ACCOUNTS,
)
from app.modules.accounting.enums import FiscalYearStatus, PeriodStatus
from app.modules.accounting.models import Account, AccountingPeriod, FiscalYear
from app.modules.settings.service import SettingsService


def _add_months(anchor: date, months: int) -> date:
    total = anchor.month - 1 + months
    return date(anchor.year + total // 12, total % 12 + 1, 1)


def _month_end(day: date) -> date:
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])


class AccountingSetupService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_setup(
        self, org_id: int, fiscal_year_start_month: int = 7, *, today: date | None = None
    ) -> None:
        self.seed_chart(org_id)
        self.seed_fiscal_calendar(org_id, fiscal_year_start_month, today=today or date.today())

    def seed_chart(self, org_id: int) -> None:
        by_code = {
            acc.code: acc
            for acc in self.db.scalars(select(Account).where(Account.org_id == org_id))
        }
        for seed in DEFAULT_ACCOUNTS:
            if seed["code"] in by_code:
                continue
            parent = by_code.get(seed["parent"]) if seed.get("parent") else None
            account = Account(
                org_id=org_id,
                parent_id=parent.id if parent else None,
                code=seed["code"],
                name=seed["name"],
                account_type=seed["type"],
                normal_balance=seed["normal"],
                is_control_account=seed.get("control", False),
                is_postable=seed.get("postable", True),
            )
            self.db.add(account)
            self.db.flush()
            by_code[seed["code"]] = account

        settings = SettingsService(self.db)
        stored = settings.get_group(org_id, ACCOUNTING_SETTINGS_GROUP)
        for key, code in ACCOUNT_MAPPING.items():
            account = by_code.get(code)
            if account is not None and key not in stored:
                settings.set(org_id, ACCOUNTING_SETTINGS_GROUP, key, account.id)

    def seed_fiscal_calendar(
        self, org_id: int, fiscal_year_start_month: int = 7, *, today: date | None = None
    ) -> FiscalYear | None:
        existing = self.db.scalar(select(FiscalYear).where(FiscalYear.org_id == org_id).limit(1))
        if existing is not None:
            return existing

        day = today or date.today()
        start_year = day.year if day.month >= fiscal_year_start_month else day.year - 1
        starts_on = date(start_year, fiscal_year_start_month, 1)
        ends_on = _month_end(_add_months(starts_on, 11))
        name = (
            f"FY {start_year}-{str(ends_on.year)[-2:]}"
            if starts_on.year != ends_on.year
            else f"FY {start_year}"
        )

        fiscal_year = FiscalYear(
            org_id=org_id,
            name=name,
            starts_on=starts_on,
            ends_on=ends_on,
            status=FiscalYearStatus.ACTIVE,
        )
        self.db.add(fiscal_year)
        self.db.flush()

        for index in range(12):
            month_start = _add_months(starts_on, index)
            self.db.add(
                AccountingPeriod(
                    org_id=org_id,
                    fiscal_year_id=fiscal_year.id,
                    name=month_start.strftime("%b %Y"),
                    period_no=index + 1,
                    starts_on=month_start,
                    ends_on=_month_end(month_start),
                    status=PeriodStatus.OPEN,
                )
            )
        self.db.flush()
        return fiscal_year
