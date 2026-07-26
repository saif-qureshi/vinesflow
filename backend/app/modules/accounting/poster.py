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
from app.modules.documents.models import Document
from app.modules.inventory.models import StockMovement
from app.modules.settings.service import SettingsService

_ZERO = Decimal("0")


class RealLedgerPoster:
    """Turns finalized documents and submitted payments into balanced GL vouchers.

    Sales: invoices, delivery-challan COGS, credit notes, customer receipts.
    Purchases: goods receipts (GRNI), bills, payments made. Vendor credits and
    stock adjustments are a later pass.
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
        handlers = {
            DocumentType.INVOICE: (self._invoice_lines, VoucherType.SALES_INVOICE),
            DocumentType.DELIVERY_CHALLAN: (
                self._delivery_challan_lines,
                VoucherType.DELIVERY_CHALLAN,
            ),
            DocumentType.CREDIT_NOTE: (self._credit_note_lines, VoucherType.CREDIT_NOTE),
            DocumentType.BILL: (self._bill_lines, VoucherType.BILL),
            DocumentType.GOODS_RECEIPT: (self._goods_receipt_lines, VoucherType.GOODS_RECEIPT),
        }
        handler = handlers.get(doc_type)
        if handler is None:
            return  # vendor credits / stock adjustments land in a later pass
        builder, voucher_type = handler
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

    def _delivery_challan_lines(self, db: Session, doc) -> list[JournalLine]:
        # Relieving stock on delivery is where COGS belongs; the challan-sourced
        # invoice then books only revenue + tax (it skips COGS, no double count).
        if not doc.stock_posted:
            return []
        cost = -self._stock_value(db, doc)  # outbound value is negative → cost positive
        if cost == _ZERO:
            return []
        return [
            JournalLine(account_id=self._account(db, doc.org_id, "cogs"), debit=cost),
            JournalLine(account_id=self._account(db, doc.org_id, "inventory"), credit=cost),
        ]

    def _goods_receipt_lines(self, db: Session, doc) -> list[JournalLine]:
        if not doc.stock_posted:
            return []
        value = self._stock_value(db, doc)  # inbound → positive
        if value == _ZERO:
            return []
        return [
            JournalLine(account_id=self._account(db, doc.org_id, "inventory"), debit=value),
            JournalLine(account_id=self._account(db, doc.org_id, "grni"), credit=value),
        ]

    def _bill_lines(self, db: Session, doc) -> list[JournalLine]:
        org_id = doc.org_id
        tax = doc.tax_total + doc.further_tax_total
        net = doc.total - tax
        lines: list[JournalLine] = []
        if net != _ZERO:
            lines.append(
                JournalLine(
                    account_id=self._account(db, org_id, self._purchase_target(db, doc)), debit=net
                )
            )
        if tax != _ZERO:
            lines.append(JournalLine(account_id=self._account(db, org_id, "input_tax"), debit=tax))
        lines.append(
            JournalLine(
                account_id=self._account(db, org_id, "accounts_payable"),
                credit=doc.total,
                party_id=doc.party_id,
            )
        )
        return lines

    def _purchase_target(self, db: Session, doc) -> str:
        # Test actual movement, not stock_posted (a service bill sets the flag but moves nothing).
        if self._stock_value(db, doc) != _ZERO:
            return "inventory"
        if self._source_moved_stock(db, doc):
            return "grni"
        return "operating_expenses"

    def _source_moved_stock(self, db: Session, doc) -> bool:
        if doc.source_document_id is None:
            return False
        source = db.get(Document, doc.source_document_id)
        return (
            source is not None
            and source.stock_posted
            and source.stock_direction == doc.stock_direction
        )

    # --- payments ---------------------------------------------------------

    def post_payment(self, db: Session, payment) -> None:
        if payment.amount <= _ZERO:
            return
        source_type = f"payment_{payment.direction}"
        if self._already_posted(db, payment.org_id, source_type, payment.id):
            return
        deposit = "cash" if payment.method == PaymentMethod.CASH else "bank"
        if payment.direction == PaymentDirection.RECEIVED:
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
            voucher_type = VoucherType.CUSTOMER_RECEIPT
            description = f"Receipt {payment.number}"
        else:
            lines = [
                JournalLine(
                    account_id=self._account(db, payment.org_id, "accounts_payable"),
                    debit=payment.amount,
                    party_id=payment.party_id,
                ),
                JournalLine(
                    account_id=self._account(db, payment.org_id, deposit), credit=payment.amount
                ),
            ]
            voucher_type = VoucherType.VENDOR_PAYMENT
            description = f"Payment {payment.number}"
        self._post(
            db,
            payment.org_id,
            voucher_type=voucher_type,
            posting_date=payment.posting_date,
            lines=lines,
            description=description,
            source_type=source_type,
            source_id=payment.id,
        )

    def reverse_payment(self, db: Session, payment) -> None:
        self._reverse(
            db, payment.org_id, f"payment_{payment.direction}", payment.id, payment.posting_date
        )
