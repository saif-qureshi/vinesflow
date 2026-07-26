from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
from app.modules.accounting.enums import VoucherStatus, VoucherType
from app.modules.accounting.models import AccountingVoucher
from app.modules.accounting.service import JournalLine, PostingService
from app.modules.documents.enums import DocumentType, PaymentDirection, PaymentMethod
from app.modules.inventory.models import StockMovement
from app.modules.settings.service import SettingsService

_ZERO = Decimal("0")


class RealLedgerPoster:
    """Turns finalized documents and submitted payments into balanced GL vouchers.

    Occupies the same seam as NullLedgerPoster; B2 handles the sales side
    (invoices, credit notes, customer receipts) and no-ops on everything else
    until B3 extends it.
    """

    # --- helpers ----------------------------------------------------------

    def _account(self, db: Session, org_id: int, key: str) -> int:
        account_id = SettingsService(db).get(org_id, ACCOUNTING_SETTINGS_GROUP, key)
        if account_id is None:
            raise BadRequestError(f"Accounting account '{key}' is not configured")
        return int(account_id)

    def _already_posted(self, db: Session, org_id: int, source_type: str, source_id: int) -> bool:
        return (
            db.scalar(
                select(AccountingVoucher.id)
                .where(
                    AccountingVoucher.org_id == org_id,
                    AccountingVoucher.source_type == source_type,
                    AccountingVoucher.source_id == source_id,
                    AccountingVoucher.voucher_type != VoucherType.REVERSAL,
                )
                .limit(1)
            )
            is not None
        )

    def _stock_value(self, db: Session, document) -> Decimal:
        """Signed Σ(unit_cost · qty_delta) over this document's stock movements.

        Negative for outbound (a sale relieving stock), positive for a restock.
        """
        rows = db.execute(
            select(StockMovement.qty_delta, StockMovement.unit_cost).where(
                StockMovement.org_id == document.org_id,
                StockMovement.reference_type == document.type,
                StockMovement.reference_id == document.id,
            )
        ).all()
        total = _ZERO
        for qty_delta, unit_cost in rows:
            if unit_cost is not None:
                total += unit_cost * qty_delta
        return total

    def _post(
        self, db, org_id, *, voucher_type, posting_date, lines, description, source_type, source_id
    ):
        PostingService(db).post_voucher(
            org_id,
            voucher_type=voucher_type,
            posting_date=posting_date,
            lines=lines,
            description=description,
            source_type=source_type,
            source_id=source_id,
            allow_control_accounts=True,
        )

    def _reverse(
        self, db: Session, org_id: int, source_type: str, source_id: int, posting_date: date
    ) -> None:
        voucher = db.scalar(
            select(AccountingVoucher).where(
                AccountingVoucher.org_id == org_id,
                AccountingVoucher.source_type == source_type,
                AccountingVoucher.source_id == source_id,
                AccountingVoucher.status == VoucherStatus.POSTED,
                AccountingVoucher.voucher_type != VoucherType.REVERSAL,
            )
        )
        if voucher is not None:
            PostingService(db).reverse_voucher(voucher, posting_date=posting_date)

    # --- documents --------------------------------------------------------

    def post_document(self, db: Session, document) -> None:
        doc_type = DocumentType(document.type)
        if doc_type == DocumentType.INVOICE:
            builder, voucher_type = self._invoice_lines, VoucherType.SALES_INVOICE
        elif doc_type == DocumentType.CREDIT_NOTE:
            builder, voucher_type = self._credit_note_lines, VoucherType.CREDIT_NOTE
        else:
            return  # bills / vendor credits / stock docs land in B3
        if self._already_posted(db, document.org_id, document.type, document.id):
            return
        lines = builder(db, document)
        if lines:
            self._post(
                db,
                document.org_id,
                voucher_type=voucher_type,
                posting_date=document.issue_date,
                lines=lines,
                description=f"{doc_type.value.replace('_', ' ').title()} {document.number}",
                source_type=document.type,
                source_id=document.id,
            )

    def reverse_document(self, db: Session, document) -> None:
        self._reverse(db, document.org_id, document.type, document.id, document.issue_date)

    def _invoice_lines(self, db: Session, doc) -> list[JournalLine]:
        org_id = doc.org_id
        tax = doc.tax_total + doc.further_tax_total
        revenue = doc.total - tax
        lines = [
            JournalLine(
                account_id=self._account(db, org_id, "accounts_receivable"),
                debit=doc.total,
                party_id=doc.party_id,
            ),
        ]
        if revenue != _ZERO:
            lines.append(
                JournalLine(account_id=self._account(db, org_id, "sales_revenue"), credit=revenue)
            )
        if tax != _ZERO:
            lines.append(
                JournalLine(account_id=self._account(db, org_id, "sales_tax_payable"), credit=tax)
            )
        if doc.stock_posted:
            cost = -self._stock_value(db, doc)  # outbound value is negative → cost positive
            if cost != _ZERO:
                lines.append(JournalLine(account_id=self._account(db, org_id, "cogs"), debit=cost))
                lines.append(
                    JournalLine(account_id=self._account(db, org_id, "inventory"), credit=cost)
                )
        return lines

    def _credit_note_lines(self, db: Session, doc) -> list[JournalLine]:
        org_id = doc.org_id
        tax = doc.tax_total + doc.further_tax_total
        returns = doc.total - tax
        lines = [
            JournalLine(
                account_id=self._account(db, org_id, "accounts_receivable"),
                credit=doc.total,
                party_id=doc.party_id,
            ),
        ]
        if returns != _ZERO:
            lines.append(
                JournalLine(account_id=self._account(db, org_id, "sales_returns"), debit=returns)
            )
        if tax != _ZERO:
            lines.append(
                JournalLine(account_id=self._account(db, org_id, "sales_tax_payable"), debit=tax)
            )
        if doc.stock_posted:
            value = self._stock_value(db, doc)  # inbound restock → positive
            if value != _ZERO:
                lines.append(
                    JournalLine(account_id=self._account(db, org_id, "inventory"), debit=value)
                )
                lines.append(
                    JournalLine(account_id=self._account(db, org_id, "cogs"), credit=value)
                )
        return lines

    # --- payments ---------------------------------------------------------

    def post_payment(self, db: Session, payment) -> None:
        if payment.direction != PaymentDirection.RECEIVED:
            return  # payments made land in B3
        if payment.amount <= _ZERO:
            return
        source_type = f"payment_{payment.direction}"
        if self._already_posted(db, payment.org_id, source_type, payment.id):
            return
        deposit = "cash" if payment.method == PaymentMethod.CASH else "bank"
        lines = [
            JournalLine(
                account_id=self._account(db, payment.org_id, deposit), debit=payment.amount
            ),
            JournalLine(
                account_id=self._account(db, payment.org_id, "accounts_receivable"),
                credit=payment.amount,
                party_id=payment.party_id,
            ),
        ]
        self._post(
            db,
            payment.org_id,
            voucher_type=VoucherType.CUSTOMER_RECEIPT,
            posting_date=payment.posting_date,
            lines=lines,
            description=f"Receipt {payment.number}",
            source_type=source_type,
            source_id=payment.id,
        )

    def reverse_payment(self, db: Session, payment) -> None:
        if payment.direction != PaymentDirection.RECEIVED:
            return
        self._reverse(
            db, payment.org_id, f"payment_{payment.direction}", payment.id, payment.posting_date
        )
