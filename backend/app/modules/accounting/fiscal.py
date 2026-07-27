from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.accounting.enums import PeriodStatus
from app.modules.accounting.models import (
    AccountingPeriod,
    AccountingVoucher,
    FiscalYear,
    LedgerEntry,
)


class FiscalYearService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Fiscal years -----------------------------------------------------

    def list_fiscal_years(self, org_id: int) -> list[FiscalYear]:
        return list(
            self.db.scalars(
                select(FiscalYear).where(FiscalYear.org_id == org_id).order_by(FiscalYear.starts_on)
            )
        )

    def create_next_fiscal_year(self, org_id: int) -> FiscalYear:
        from app.modules.accounting.setup import AccountingSetupService

        fiscal_year = AccountingSetupService(self.db).create_next_fiscal_year(org_id)
        self.db.commit()
        self.db.refresh(fiscal_year)
        return fiscal_year

    def delete_fiscal_year(self, org_id: int, fiscal_year_id: int) -> None:
        fiscal_year = self.db.scalar(
            select(FiscalYear).where(FiscalYear.id == fiscal_year_id, FiscalYear.org_id == org_id)
        )
        if fiscal_year is None:
            raise NotFoundError("Fiscal year not found")
        count = self.db.scalar(
            select(func.count()).select_from(FiscalYear).where(FiscalYear.org_id == org_id)
        )
        if count <= 1:
            raise ConflictError("Cannot delete the only fiscal year")
        if self._has_postings(fiscal_year_id):
            raise ConflictError("Cannot delete a fiscal year that has postings")
        self.db.delete(fiscal_year)
        self.db.commit()

    def _has_postings(self, fiscal_year_id: int) -> bool:
        has_entries = self.db.scalar(
            select(LedgerEntry.id).where(LedgerEntry.fiscal_year_id == fiscal_year_id).limit(1)
        )
        has_vouchers = self.db.scalar(
            select(AccountingVoucher.id)
            .where(AccountingVoucher.fiscal_year_id == fiscal_year_id)
            .limit(1)
        )
        return has_entries is not None or has_vouchers is not None

    # --- Periods ----------------------------------------------------------

    def list_periods(
        self, org_id: int, fiscal_year_id: int | None = None
    ) -> list[AccountingPeriod]:
        stmt = select(AccountingPeriod).where(AccountingPeriod.org_id == org_id)
        if fiscal_year_id is not None:
            stmt = stmt.where(AccountingPeriod.fiscal_year_id == fiscal_year_id)
        return list(self.db.scalars(stmt.order_by(AccountingPeriod.starts_on)))

    def set_period_status(
        self, org_id: int, period_id: int, status: PeriodStatus
    ) -> AccountingPeriod:
        if status not in (PeriodStatus.OPEN, PeriodStatus.LOCKED):
            raise BadRequestError("A period can only be set open or locked")
        period = self.db.scalar(
            select(AccountingPeriod).where(
                AccountingPeriod.id == period_id, AccountingPeriod.org_id == org_id
            )
        )
        if period is None:
            raise NotFoundError("Period not found")
        if period.status == PeriodStatus.CLOSED:
            raise ConflictError("A closed period cannot be reopened")
        period.status = status
        self.db.commit()
        self.db.refresh(period)
        return period
