from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.accounting.constants import (
    ACCOUNTING_SETTINGS_GROUP,
    SUBSIDIARY_OPENING_ACCOUNTS,
)
from app.modules.accounting.enums import VoucherStatus, VoucherType
from app.modules.accounting.models import AccountingVoucher, LedgerEntry, VoucherLine
from app.modules.accounting.schemas import JournalVoucherCreate, OpeningBalanceInput
from app.modules.accounting.service import JournalLine, PostingService
from app.modules.parties.models import Party
from app.modules.settings.service import SettingsService

_ZERO = Decimal("0")
_PARTY_OPENING = "party_opening"


class VoucherService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.posting = PostingService(db)

    def list_vouchers(self, org_id: int) -> list[AccountingVoucher]:
        return list(
            self.db.scalars(
                select(AccountingVoucher)
                .where(AccountingVoucher.org_id == org_id)
                .order_by(AccountingVoucher.posting_date.desc(), AccountingVoucher.id.desc())
            )
        )

    def get_voucher(self, org_id: int, voucher_id: int) -> AccountingVoucher:
        voucher = self.db.scalar(
            select(AccountingVoucher).where(
                AccountingVoucher.id == voucher_id, AccountingVoucher.org_id == org_id
            )
        )
        if voucher is None:
            raise NotFoundError("Voucher not found")
        return voucher

    def create_journal_voucher(
        self, org_id: int, payload: JournalVoucherCreate
    ) -> AccountingVoucher:
        voucher = self.posting.create_voucher(
            org_id,
            voucher_type=VoucherType.JOURNAL,
            posting_date=payload.date,
            reference_no=payload.reference_no,
            description=payload.description,
            lines=self._journal_lines(payload),
        )
        self.db.commit()
        self.db.refresh(voucher)
        return voucher

    def update_journal_voucher(
        self, org_id: int, voucher_id: int, payload: JournalVoucherCreate
    ) -> AccountingVoucher:
        voucher = self.get_voucher(org_id, voucher_id)
        if voucher.status != VoucherStatus.DRAFT:
            raise ConflictError("Only draft vouchers can be edited")
        total_debit, total_credit = self.posting.validate_lines(
            org_id, self._journal_lines(payload)
        )
        voucher.reference_no = payload.reference_no
        voucher.description = payload.description
        voucher.document_date = payload.date
        voucher.posting_date = payload.date
        voucher.total_debit = total_debit
        voucher.total_credit = total_credit
        voucher.lines.clear()
        for index, line in enumerate(payload.lines, start=1):
            voucher.lines.append(
                VoucherLine(
                    account_id=line.account_id,
                    party_id=line.party_id,
                    line_no=index,
                    debit=line.debit,
                    credit=line.credit,
                    description=line.description,
                )
            )
        self.db.commit()
        self.db.refresh(voucher)
        return voucher

    def post_journal_voucher(self, org_id: int, voucher_id: int) -> AccountingVoucher:
        voucher = self.get_voucher(org_id, voucher_id)
        self.posting.post_draft(voucher)
        self.db.commit()
        self.db.refresh(voucher)
        return voucher

    def cancel_journal_voucher(self, org_id: int, voucher_id: int) -> AccountingVoucher:
        voucher = self.get_voucher(org_id, voucher_id)
        if voucher.status != VoucherStatus.DRAFT:
            raise ConflictError("Only draft vouchers can be cancelled")
        voucher.status = VoucherStatus.CANCELLED
        self.db.commit()
        self.db.refresh(voucher)
        return voucher

    def reverse_voucher(self, org_id: int, voucher_id: int) -> AccountingVoucher:
        voucher = self.get_voucher(org_id, voucher_id)
        reversal = self.posting.reverse_voucher(voucher)
        self.db.commit()
        self.db.refresh(reversal)
        return reversal

    def create_opening_balances(
        self, org_id: int, payload: OpeningBalanceInput
    ) -> AccountingVoucher:
        if self.db.scalar(
            select(AccountingVoucher.id)
            .where(
                AccountingVoucher.org_id == org_id,
                AccountingVoucher.voucher_type == VoucherType.OPENING,
                AccountingVoucher.status == VoucherStatus.POSTED,
                or_(
                    AccountingVoucher.source_type.is_(None),
                    AccountingVoucher.source_type == "opening_balances",
                ),
            )
            .limit(1)
        ):
            raise ConflictError("Opening balances have already been set")

        lines = [
            JournalLine(account_id=e.account_id, debit=e.debit, credit=e.credit)
            for e in payload.entries
            if e.debit or e.credit
        ]
        if not lines:
            raise BadRequestError("Enter at least one opening balance")

        settings = SettingsService(self.db)
        for key, message in SUBSIDIARY_OPENING_ACCOUNTS.items():
            account_id = settings.get(org_id, ACCOUNTING_SETTINGS_GROUP, key)
            if account_id and any(line.account_id == int(account_id) for line in lines):
                raise BadRequestError(message)

        net = sum((line.debit - line.credit for line in lines), _ZERO)
        if net != _ZERO:
            offset = int(
                SettingsService(self.db).get(
                    org_id, ACCOUNTING_SETTINGS_GROUP, "opening_balance_equity"
                )
            )
            if net > _ZERO:
                lines.append(JournalLine(account_id=offset, credit=net))
            else:
                lines.append(JournalLine(account_id=offset, debit=-net))

        voucher = self.posting.post_voucher(
            org_id,
            voucher_type=VoucherType.OPENING,
            posting_date=payload.date,
            lines=lines,
            description="Opening balances",
            source_type="opening_balances",
            source_id=org_id,
            allow_control_accounts=True,
        )
        self.db.commit()
        self.db.refresh(voucher)
        return voucher

    def party_opening_balance(self, org_id: int, party_id: int) -> Decimal:
        """Read back from the ledger rather than a stored copy, so the figure on
        the party can never disagree with the entries behind it."""
        total = self.db.scalar(
            select(
                func.coalesce(func.sum(LedgerEntry.debit - LedgerEntry.credit), 0)
            ).where(
                LedgerEntry.org_id == org_id,
                LedgerEntry.party_id == party_id,
                LedgerEntry.voucher_type == VoucherType.OPENING,
            )
        ) or _ZERO
        return total

    def set_party_opening_balance(
        self, org_id: int, party_id: int, amount: Decimal, as_of: date
    ) -> Decimal:
        """What the party already owed on the day the books started. Posted with
        the party on the line, so it reaches their ledger, statement and aging —
        which a lump figure on the opening balances screen never could."""
        party = self.db.scalar(
            select(Party).where(Party.id == party_id, Party.org_id == org_id)
        )
        if party is None:
            raise NotFoundError("Party not found")
        if amount < _ZERO:
            raise BadRequestError("An opening balance cannot be negative")

        settings = SettingsService(self.db)

        def account(key: str) -> int:
            value = settings.get(org_id, ACCOUNTING_SETTINGS_GROUP, key)
            if value is None:
                raise BadRequestError(f"The {key.replace('_', ' ')} account is not configured")
            return int(value)

        existing = self.db.scalar(
            select(AccountingVoucher).where(
                AccountingVoucher.org_id == org_id,
                AccountingVoucher.source_type == _PARTY_OPENING,
                AccountingVoucher.source_id == party_id,
                AccountingVoucher.status == VoucherStatus.POSTED,
                AccountingVoucher.voucher_type != VoucherType.REVERSAL,
            )
        )
        if existing is not None:
            self.posting.reverse_voucher(existing, posting_date=as_of)

        if amount != _ZERO:
            equity = account("opening_balance_equity")
            if party.is_vendor and not party.is_customer:
                lines = [
                    JournalLine(account_id=equity, debit=amount),
                    JournalLine(
                        account_id=account("accounts_payable"), credit=amount, party_id=party_id
                    ),
                ]
            else:
                lines = [
                    JournalLine(
                        account_id=account("accounts_receivable"), debit=amount, party_id=party_id
                    ),
                    JournalLine(account_id=equity, credit=amount),
                ]
            self.posting.post_voucher(
                org_id,
                voucher_type=VoucherType.OPENING,
                posting_date=as_of,
                lines=lines,
                description=f"Opening balance — {party.name}",
                source_type=_PARTY_OPENING,
                source_id=party_id,
                allow_control_accounts=True,
            )
        self.db.commit()
        return self.party_opening_balance(org_id, party_id)

    @staticmethod
    def _journal_lines(payload: JournalVoucherCreate) -> list[JournalLine]:
        return [
            JournalLine(
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                party_id=line.party_id,
                description=line.description,
            )
            for line in payload.lines
        ]
