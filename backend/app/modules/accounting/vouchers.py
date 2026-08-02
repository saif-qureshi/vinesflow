from __future__ import annotations

from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
from app.modules.accounting.enums import VoucherStatus, VoucherType
from app.modules.accounting.models import AccountingVoucher, VoucherLine
from app.modules.accounting.schemas import JournalVoucherCreate, OpeningBalanceInput
from app.modules.accounting.service import JournalLine, PostingService
from app.modules.settings.service import SettingsService

_ZERO = Decimal("0")


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

        inventory_account = int(
            SettingsService(self.db).get(org_id, ACCOUNTING_SETTINGS_GROUP, "inventory")
        )
        if any(line.account_id == inventory_account for line in lines):
            raise BadRequestError(
                "Enter inventory through item opening stock so quantity and accounting stay aligned"
            )

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
