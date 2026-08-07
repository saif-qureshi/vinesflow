from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
from app.modules.accounting.models import Account, LedgerEntry
from app.modules.accounting.schemas import AccountCreate, AccountUpdate


def cash_account_ids(db: Session, org_id: int) -> list[int]:
    """The Cash and Bank accounts, plus every account beneath them —
    each bank account the org adds lives under Bank."""
    from app.modules.settings.service import SettingsService

    settings = SettingsService(db)
    roots = [
        int(account_id)
        for key in ("cash", "bank")
        if (account_id := settings.get(org_id, ACCOUNTING_SETTINGS_GROUP, key)) is not None
    ]
    if not roots:
        return []
    children: dict[int | None, list[int]] = {}
    for account_id, parent_id in db.execute(
        select(Account.id, Account.parent_id).where(Account.org_id == org_id)
    ).all():
        children.setdefault(parent_id, []).append(account_id)
    found, queue = set(roots), list(roots)
    while queue:
        for child in children.get(queue.pop(), []):
            if child not in found:
                found.add(child)
                queue.append(child)
    return list(found)


class AccountsService:
    def __init__(self, db: Session) -> None:
        self.db = db

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

    def _validate_parent(
        self, org_id: int, parent_id: int | None, *, exclude_id: int | None = None
    ) -> None:
        if parent_id is None:
            return
        if parent_id == exclude_id:
            raise BadRequestError("An account cannot be its own parent")
        self.get_account(org_id, parent_id)

    def _has_ledger_entries(self, org_id: int, account_id: int) -> bool:
        return (
            self.db.scalar(
                select(LedgerEntry.id)
                .where(LedgerEntry.org_id == org_id, LedgerEntry.account_id == account_id)
                .limit(1)
            )
            is not None
        )
