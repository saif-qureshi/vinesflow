from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.modules.accounting.constants import VOUCHER_PREFIXES
from app.modules.accounting.enums import (
    FiscalYearStatus,
    PeriodStatus,
    VoucherStatus,
    VoucherType,
)
from app.modules.accounting.models import (
    Account,
    AccountingPeriod,
    AccountingVoucher,
    LedgerEntry,
    VoucherLine,
)
from app.modules.documents.numbering import assign_number
from app.modules.parties.models import Party

_ZERO = Decimal("0")
_Q = Decimal("0.0001")


def _money(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(_Q, rounding=ROUND_HALF_UP)


@dataclass
class JournalLine:
    account_id: int
    debit: Decimal = field(default=_ZERO)
    credit: Decimal = field(default=_ZERO)
    party_id: int | None = None
    description: str | None = None


class PostingService:
    """The single double-entry engine. Every ledger write goes through here."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Periods ----------------------------------------------------------

    def resolve_open_period(self, org_id: int, posting_date: date) -> AccountingPeriod:
        period = self.db.scalar(
            select(AccountingPeriod).where(
                AccountingPeriod.org_id == org_id,
                AccountingPeriod.starts_on <= posting_date,
                AccountingPeriod.ends_on >= posting_date,
            )
        )
        if period is None:
            raise BadRequestError("No accounting period covers this posting date")
        if period.fiscal_year.status != FiscalYearStatus.ACTIVE:
            raise BadRequestError("Posting date belongs to a closed fiscal year")
        if period.status != PeriodStatus.OPEN:
            raise BadRequestError("Accounting period is locked or closed")
        return period

    # --- Validation -------------------------------------------------------

    def validate_lines(
        self, org_id: int, lines: list[JournalLine], *, allow_control_accounts: bool = False
    ) -> tuple[Decimal, Decimal]:
        if len(lines) < 2:
            raise BadRequestError("A voucher must have at least two lines")

        account_ids = {line.account_id for line in lines}
        accounts = {
            acc.id: acc
            for acc in self.db.scalars(
                select(Account).where(Account.org_id == org_id, Account.id.in_(account_ids))
            )
        }
        for account_id in account_ids:
            account = accounts.get(account_id)
            if account is None:
                raise BadRequestError("Select a valid account")
            if not account.is_active:
                raise BadRequestError(f"Account {account.code} {account.name} is inactive")
            if not account.is_postable:
                raise BadRequestError(f"Account {account.code} {account.name} is not postable")
            if not allow_control_accounts and account.is_control_account:
                raise BadRequestError(
                    f"{account.code} {account.name} is a control account and can only be "
                    "posted by the documents it controls"
                )

        party_ids = {line.party_id for line in lines if line.party_id is not None}
        if party_ids:
            found = set(
                self.db.scalars(
                    select(Party.id).where(Party.org_id == org_id, Party.id.in_(party_ids))
                )
            )
            if found != party_ids:
                raise BadRequestError("Select a valid party")

        total_debit = _ZERO
        total_credit = _ZERO
        for index, line in enumerate(lines, start=1):
            debit = _money(line.debit)
            credit = _money(line.credit)
            if debit < _ZERO or credit < _ZERO:
                raise BadRequestError(f"Line {index} amounts cannot be negative")
            if debit > _ZERO and credit > _ZERO:
                raise BadRequestError(f"Line {index} cannot have both a debit and a credit amount")
            if debit == _ZERO and credit == _ZERO:
                raise BadRequestError(f"Line {index} must have a debit or credit amount")
            total_debit += debit
            total_credit += credit

        if total_debit <= _ZERO or total_credit <= _ZERO:
            raise BadRequestError("Voucher must contain debit and credit amounts")
        if total_debit != total_credit:
            raise BadRequestError("Voucher debit and credit totals must be equal")

        return total_debit, total_credit

    # --- Posting ----------------------------------------------------------

    def create_voucher(
        self,
        org_id: int,
        *,
        voucher_type: VoucherType,
        posting_date: date,
        lines: list[JournalLine],
        document_date: date | None = None,
        reference_no: str | None = None,
        description: str | None = None,
        source_type: str | None = None,
        source_id: int | None = None,
        allow_control_accounts: bool = False,
    ) -> AccountingVoucher:
        """Build a balanced voucher in draft (no ledger entries yet)."""
        period = self.resolve_open_period(org_id, posting_date)
        total_debit, total_credit = self.validate_lines(
            org_id, lines, allow_control_accounts=allow_control_accounts
        )
        voucher = AccountingVoucher(
            org_id=org_id,
            fiscal_year_id=period.fiscal_year_id,
            period_id=period.id,
            voucher_type=voucher_type,
            reference_no=reference_no,
            document_date=document_date or posting_date,
            posting_date=posting_date,
            description=description,
            total_debit=total_debit,
            total_credit=total_credit,
            status=VoucherStatus.DRAFT,
            source_type=source_type,
            source_id=source_id,
        )
        assign_number(
            self.db,
            voucher,
            AccountingVoucher.number,
            VOUCHER_PREFIXES[VoucherType(voucher_type)],
            "0001",
            "none",
            posting_date.year,
            AccountingVoucher.org_id == org_id,
            AccountingVoucher.voucher_type == voucher_type,
        )
        for index, line in enumerate(lines, start=1):
            self.db.add(
                VoucherLine(
                    voucher_id=voucher.id,
                    account_id=line.account_id,
                    party_id=line.party_id,
                    line_no=index,
                    debit=_money(line.debit),
                    credit=_money(line.credit),
                    description=line.description,
                )
            )
        self.db.flush()
        return voucher

    def post_draft(
        self, voucher: AccountingVoucher, *, allow_control_accounts: bool = False
    ) -> AccountingVoucher:
        """Post a draft voucher to the ledger."""
        if voucher.status != VoucherStatus.DRAFT:
            raise BadRequestError("Only draft vouchers can be posted")
        period = self.resolve_open_period(voucher.org_id, voucher.posting_date)
        self.validate_lines(
            voucher.org_id,
            [
                JournalLine(
                    account_id=line.account_id,
                    debit=line.debit,
                    credit=line.credit,
                    party_id=line.party_id,
                )
                for line in voucher.lines
            ],
            allow_control_accounts=allow_control_accounts,
        )
        for line in voucher.lines:
            self.db.add(
                LedgerEntry(
                    org_id=voucher.org_id,
                    account_id=line.account_id,
                    party_id=line.party_id,
                    voucher_id=voucher.id,
                    voucher_line_id=line.id,
                    fiscal_year_id=period.fiscal_year_id,
                    period_id=period.id,
                    voucher_type=voucher.voucher_type,
                    number=voucher.number,
                    posting_date=voucher.posting_date,
                    line_no=line.line_no,
                    debit=line.debit,
                    credit=line.credit,
                    description=line.description or voucher.description,
                )
            )
        voucher.fiscal_year_id = period.fiscal_year_id
        voucher.period_id = period.id
        voucher.status = VoucherStatus.POSTED
        voucher.posted_at = datetime.now(UTC)
        self.db.flush()
        return voucher

    def post_voucher(
        self,
        org_id: int,
        *,
        voucher_type: VoucherType,
        posting_date: date,
        lines: list[JournalLine],
        document_date: date | None = None,
        reference_no: str | None = None,
        description: str | None = None,
        source_type: str | None = None,
        source_id: int | None = None,
        allow_control_accounts: bool = False,
    ) -> AccountingVoucher:
        """Create and immediately post a voucher (used by automatic document postings)."""
        voucher = self.create_voucher(
            org_id,
            voucher_type=voucher_type,
            posting_date=posting_date,
            lines=lines,
            document_date=document_date,
            reference_no=reference_no,
            description=description,
            source_type=source_type,
            source_id=source_id,
            allow_control_accounts=allow_control_accounts,
        )
        return self.post_draft(voucher, allow_control_accounts=allow_control_accounts)

    def reverse_voucher(
        self,
        voucher: AccountingVoucher,
        *,
        posting_date: date | None = None,
        description: str | None = None,
    ) -> AccountingVoucher:
        if voucher.status != VoucherStatus.POSTED:
            raise BadRequestError("Only posted vouchers can be reversed")
        desc = description or f"Reversal of {voucher.number}"
        mirror = [
            JournalLine(
                account_id=line.account_id,
                debit=line.credit,
                credit=line.debit,
                party_id=line.party_id,
                description=desc,
            )
            for line in voucher.lines
        ]
        reversal = self.post_voucher(
            voucher.org_id,
            voucher_type=VoucherType.REVERSAL,
            posting_date=posting_date or voucher.posting_date,
            lines=mirror,
            description=desc,
            source_type=voucher.source_type,
            source_id=voucher.source_id,
            allow_control_accounts=True,
        )
        reversal.reversed_from_id = voucher.id
        voucher.status = VoucherStatus.REVERSED
        self.db.flush()
        return reversal

    def get_voucher(self, org_id: int, voucher_id: int) -> AccountingVoucher:
        voucher = self.db.scalar(
            select(AccountingVoucher).where(
                AccountingVoucher.id == voucher_id, AccountingVoucher.org_id == org_id
            )
        )
        if voucher is None:
            raise NotFoundError("Voucher not found")
        return voucher
