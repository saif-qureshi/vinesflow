from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
from app.modules.accounting.enums import AccountType, NormalBalance
from app.modules.accounting.models import Account, LedgerEntry
from app.modules.activities.service import ActivityService
from app.modules.banks.models import BankAccount
from app.modules.banks.schemas import BankAccountCreate, BankAccountUpdate
from app.modules.settings.service import SettingsService

_ZERO = Decimal("0")


class BankAccountService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.activity = ActivityService(db)

    def _bank_parent(self, org_id: int) -> Account:
        account_id = SettingsService(self.db).get(org_id, ACCOUNTING_SETTINGS_GROUP, "bank")
        account = self.db.get(Account, int(account_id)) if account_id else None
        if account is None:
            raise BadRequestError("The Bank account is not configured for this organization")
        return account

    def _next_code(self, org_id: int, parent: Account) -> str:
        """Number children off the Bank account: 1120 -> 1121, 1122, ..."""
        base = int(parent.code)
        taken = {
            code
            for (code,) in self.db.execute(
                select(Account.code).where(Account.org_id == org_id)
            ).all()
        }
        for offset in range(1, 100):
            candidate = str(base + offset)
            if candidate not in taken:
                return candidate
        raise ConflictError("No account code is available under Bank")

    def _balances(self, org_id: int) -> dict[int, Decimal]:
        rows = self.db.execute(
            select(
                LedgerEntry.account_id,
                func.coalesce(func.sum(LedgerEntry.debit - LedgerEntry.credit), 0),
            )
            .where(LedgerEntry.org_id == org_id)
            .group_by(LedgerEntry.account_id)
        ).all()
        return dict(rows)

    def list(self, org_id: int) -> list[BankAccount]:
        rows = list(
            self.db.scalars(
                select(BankAccount)
                .where(BankAccount.org_id == org_id)
                .order_by(BankAccount.bank_name, BankAccount.account_title)
            ).all()
        )
        balances = self._balances(org_id)
        for row in rows:
            row.balance = balances.get(row.account_id, _ZERO)
            row.account_code = row.account.code
        return rows

    def get(self, org_id: int, bank_id: int) -> BankAccount:
        row = self.db.scalar(
            select(BankAccount).where(BankAccount.id == bank_id, BankAccount.org_id == org_id)
        )
        if row is None:
            raise NotFoundError("Bank account not found")
        row.balance = self._balances(org_id).get(row.account_id, _ZERO)
        row.account_code = row.account.code
        return row

    def _ensure_unique_number(
        self, org_id: int, number: str, exclude_id: int | None = None
    ) -> None:
        q = select(BankAccount.id).where(
            BankAccount.org_id == org_id, BankAccount.account_number == number
        )
        if exclude_id is not None:
            q = q.where(BankAccount.id != exclude_id)
        if self.db.scalar(q) is not None:
            raise ConflictError("That account number is already recorded")

    def create(self, org_id: int, payload: BankAccountCreate) -> BankAccount:
        self._ensure_unique_number(org_id, payload.account_number)
        parent = self._bank_parent(org_id)
        # Each bank account gets its own ledger account so its balance and its
        # cash flow can be told apart from every other one.
        account = Account(
            org_id=org_id,
            parent_id=parent.id,
            code=self._next_code(org_id, parent),
            name=f"{payload.bank_name} — {payload.account_title}",
            account_type=AccountType.ASSET,
            normal_balance=NormalBalance.DEBIT,
            is_control_account=False,
            is_postable=True,
        )
        self.db.add(account)
        self.db.flush()

        bank = BankAccount(org_id=org_id, account_id=account.id, **payload.model_dump())
        self.db.add(bank)
        self.db.flush()
        self.activity.record(
            org_id, "created", "bank_account", bank.account_title, entity_id=bank.id
        )
        self.db.commit()
        self.db.refresh(bank)
        return self.get(org_id, bank.id)

    def update(self, org_id: int, bank_id: int, payload: BankAccountUpdate) -> BankAccount:
        bank = self.get(org_id, bank_id)
        fields = payload.model_fields_set
        if "account_number" in fields and payload.account_number:
            self._ensure_unique_number(org_id, payload.account_number, exclude_id=bank_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(bank, field, value)
        if {"bank_name", "account_title"} & fields:
            bank.account.name = f"{bank.bank_name} — {bank.account_title}"
        self.activity.record(
            org_id, "updated", "bank_account", bank.account_title, entity_id=bank.id
        )
        self.db.commit()
        self.db.refresh(bank)
        return self.get(org_id, bank_id)

    def delete(self, org_id: int, bank_id: int) -> None:
        bank = self.get(org_id, bank_id)
        if self.db.scalar(
            select(LedgerEntry.id).where(LedgerEntry.account_id == bank.account_id).limit(1)
        ):
            raise ConflictError("This account has ledger history; deactivate it instead")
        account = bank.account
        self.activity.record(
            org_id, "deleted", "bank_account", bank.account_title, entity_id=bank.id
        )
        self.db.delete(bank)
        self.db.flush()
        self.db.delete(account)
        self.db.commit()
