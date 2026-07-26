from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.accounting.enums import PeriodStatus
from app.modules.accounting.models import (
    Account,
    AccountingPeriod,
    AccountingVoucher,
    FiscalYear,
    LedgerEntry,
)
from app.modules.accounting.schemas import AccountCreate, AccountUpdate


class AccountingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Accounts ---------------------------------------------------------

    def list_accounts(self, org_id: int) -> list[Account]:
        return list(
            self.db.scalars(select(Account).where(Account.org_id == org_id).order_by(Account.code))
        )

    def get_account(self, org_id: int, account_id: int) -> Account:
        account = self.db.scalar(
            select(Account).where(Account.id == account_id, Account.org_id == org_id)
        )
        if account is None:
            raise NotFoundError("Account not found")
        return account

    def _validate_parent(
        self, org_id: int, parent_id: int | None, *, exclude_id: int | None = None
    ) -> None:
        if parent_id is None:
            return
        if parent_id == exclude_id:
            raise BadRequestError("An account cannot be its own parent")
        self.get_account(org_id, parent_id)

    def create_account(self, org_id: int, payload: AccountCreate) -> Account:
        if self.db.scalar(
            select(Account.id).where(Account.org_id == org_id, Account.code == payload.code)
        ):
            raise ConflictError("An account with that code already exists")
        self._validate_parent(org_id, payload.parent_id)
        account = Account(
            org_id=org_id,
            parent_id=payload.parent_id,
            code=payload.code,
            name=payload.name,
            account_type=payload.account_type,
            normal_balance=payload.normal_balance,
            is_control_account=False,
            is_postable=payload.is_postable,
            description=payload.description,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update_account(self, org_id: int, account_id: int, payload: AccountUpdate) -> Account:
        account = self.get_account(org_id, account_id)
        if payload.name is not None:
            account.name = payload.name
        if "parent_id" in payload.model_fields_set:
            self._validate_parent(org_id, payload.parent_id, exclude_id=account_id)
            account.parent_id = payload.parent_id
        if payload.description is not None:
            account.description = payload.description
        if payload.is_active is not None:
            if not payload.is_active and self._has_ledger_entries(org_id, account_id):
                raise ConflictError("Cannot deactivate an account that has ledger entries")
            account.is_active = payload.is_active
        self.db.commit()
        self.db.refresh(account)
        return account

    def _has_ledger_entries(self, org_id: int, account_id: int) -> bool:
        return (
            self.db.scalar(
                select(LedgerEntry.id)
                .where(LedgerEntry.org_id == org_id, LedgerEntry.account_id == account_id)
                .limit(1)
            )
            is not None
        )

    # --- Fiscal years & periods ------------------------------------------

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
        if self._fiscal_year_has_postings(fiscal_year_id):
            raise ConflictError("Cannot delete a fiscal year that has postings")
        self.db.delete(fiscal_year)
        self.db.commit()

    def _fiscal_year_has_postings(self, fiscal_year_id: int) -> bool:
        has_entries = self.db.scalar(
            select(LedgerEntry.id).where(LedgerEntry.fiscal_year_id == fiscal_year_id).limit(1)
        )
        has_vouchers = self.db.scalar(
            select(AccountingVoucher.id)
            .where(AccountingVoucher.fiscal_year_id == fiscal_year_id)
            .limit(1)
        )
        return has_entries is not None or has_vouchers is not None

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
