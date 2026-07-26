from __future__ import annotations

from enum import StrEnum


class AccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class NormalBalance(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class FiscalYearStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class PeriodStatus(StrEnum):
    OPEN = "open"
    LOCKED = "locked"
    CLOSED = "closed"


class VoucherStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    REVERSED = "reversed"
    CANCELLED = "cancelled"


class VoucherType(StrEnum):
    JOURNAL = "journal"
    OPENING = "opening"
    REVERSAL = "reversal"
    ADJUSTMENT = "adjustment"
    PERIOD_CLOSING = "period_closing"
    SALES_INVOICE = "sales_invoice"
    DELIVERY_CHALLAN = "delivery_challan"
    CUSTOMER_RECEIPT = "customer_receipt"
    CREDIT_NOTE = "credit_note"
    BILL = "bill"
    VENDOR_PAYMENT = "vendor_payment"
    VENDOR_CREDIT = "vendor_credit"
    GOODS_RECEIPT = "goods_receipt"
    EXPENSE = "expense"
    STOCK_ADJUSTMENT = "stock_adjustment"
