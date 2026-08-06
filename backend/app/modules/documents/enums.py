from __future__ import annotations

from enum import StrEnum


class DocumentType(StrEnum):
    SALES_ORDER = "sales_order"
    DELIVERY_CHALLAN = "delivery_challan"
    INVOICE = "invoice"
    SALES_RECEIPT = "sales_receipt"
    CREDIT_NOTE = "credit_note"
    PURCHASE_ORDER = "purchase_order"
    GOODS_RECEIPT = "goods_receipt"
    BILL = "bill"
    VENDOR_CREDIT = "vendor_credit"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    CLOSED = "closed"
    VOID = "void"


class DocumentPaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    # Settled by credit notes rather than by money changing hands.
    CREDITED = "credited"


class DiscountType(StrEnum):
    AMOUNT = "amount"
    PERCENT = "percent"


class PaymentDirection(StrEnum):
    RECEIVED = "received"
    MADE = "made"


class PaymentStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CANCELLED = "cancelled"


class PaymentMethod(StrEnum):
    CASH = "cash"
    BANK = "bank"
    CHEQUE = "cheque"
    CARD = "card"
    OTHER = "other"


PAYMENT_PREFIXES: dict[PaymentDirection, str] = {
    PaymentDirection.RECEIVED: "PAY-",
    PaymentDirection.MADE: "PMT-",
}


DEFAULT_PREFIXES: dict[DocumentType, str] = {
    DocumentType.SALES_ORDER: "SO-",
    DocumentType.DELIVERY_CHALLAN: "DC-",
    DocumentType.INVOICE: "INV-",
    DocumentType.SALES_RECEIPT: "SR-",
    DocumentType.CREDIT_NOTE: "CN-",
    DocumentType.PURCHASE_ORDER: "PO-",
    DocumentType.GOODS_RECEIPT: "GRN-",
    DocumentType.BILL: "BILL-",
    DocumentType.VENDOR_CREDIT: "VC-",
}
