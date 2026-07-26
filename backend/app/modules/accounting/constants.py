from __future__ import annotations

from app.modules.accounting.enums import VoucherType

VOUCHER_PREFIXES: dict[VoucherType, str] = {
    VoucherType.JOURNAL: "JV",
    VoucherType.OPENING: "OPN",
    VoucherType.REVERSAL: "RV",
    VoucherType.ADJUSTMENT: "ADJ",
    VoucherType.PERIOD_CLOSING: "PCV",
    VoucherType.SALES_INVOICE: "SV",
    VoucherType.CUSTOMER_RECEIPT: "RCP",
    VoucherType.CREDIT_NOTE: "CN",
    VoucherType.BILL: "PV",
    VoucherType.VENDOR_PAYMENT: "PPV",
    VoucherType.VENDOR_CREDIT: "DNV",
    VoucherType.GOODS_RECEIPT: "GRV",
    VoucherType.EXPENSE: "EXV",
    VoucherType.STOCK_ADJUSTMENT: "SAV",
}
