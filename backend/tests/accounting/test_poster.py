from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app.core.security import hash_password
from app.modules.accounting.constants import ACCOUNTING_SETTINGS_GROUP
from app.modules.accounting.enums import VoucherStatus, VoucherType
from app.modules.accounting.models import AccountingVoucher, LedgerEntry
from app.modules.documents.enums import DocumentType, PaymentDirection
from app.modules.documents.models import TaxRate
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput
from app.modules.documents.service import DocumentService
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.payments.schemas import PaymentAllocationInput, PaymentCreate
from app.modules.payments.service import PaymentService
from app.modules.products.models import Product
from app.modules.settings.service import SettingsService
from app.modules.users.models import User


def _setup(db):
    user = User(email="ledger@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme")
    db.flush()
    customer = Party(org_id=org.id, is_customer=True, name="Beta Corp")
    product = Product(
        org_id=org.id,
        name="Widget",
        type="single",
        track_inventory=True,
        sale_price=Decimal("100"),
        purchase_price=Decimal("60"),
    )
    db.add_all([customer, product])
    db.flush()
    return org.id, customer.id, product.id


def _acct(db, org_id, key):
    return int(SettingsService(db).get(org_id, ACCOUNTING_SETTINGS_GROUP, key))


def _bal(db, org_id, key):
    account_id = _acct(db, org_id, key)
    debit = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.debit), 0)).where(
            LedgerEntry.org_id == org_id, LedgerEntry.account_id == account_id
        )
    )
    credit = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.credit), 0)).where(
            LedgerEntry.org_id == org_id, LedgerEntry.account_id == account_id
        )
    )
    return debit - credit


def _tb_balances(db, org_id) -> bool:
    debit = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.debit), 0)).where(LedgerEntry.org_id == org_id)
    )
    credit = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.credit), 0)).where(LedgerEntry.org_id == org_id)
    )
    return debit == credit


def _invoice(db, org_id, cust_id, pid):
    svc = DocumentService(db)
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org_id, TaxRate.name == "GST 18%"))
    doc = svc.create(
        org_id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=cust_id,
            lines=[
                DocumentLineInput(
                    product_id=pid,
                    description="Widget",
                    quantity=Decimal("2"),
                    unit_price=Decimal("100"),
                    tax_rate_id=tax.id,
                )
            ],
        ),
    )
    return svc.finalize(org_id, doc.id)


def test_invoice_finalize_posts_balanced_double_entry(db):
    org_id, cust_id, pid = _setup(db)
    doc = _invoice(db, org_id, cust_id, pid)

    voucher = db.scalar(
        select(AccountingVoucher).where(
            AccountingVoucher.source_type == "invoice", AccountingVoucher.source_id == doc.id
        )
    )
    assert voucher is not None
    assert voucher.voucher_type == VoucherType.SALES_INVOICE
    assert voucher.total_debit == voucher.total_credit

    tax = doc.tax_total + doc.further_tax_total
    assert _bal(db, org_id, "accounts_receivable") == doc.total
    assert _bal(db, org_id, "sales_revenue") == -(doc.total - tax)
    assert _bal(db, org_id, "sales_tax_payable") == -tax
    assert _bal(db, org_id, "cogs") == Decimal("120")  # 2 units * cost 60
    assert _bal(db, org_id, "inventory") == Decimal("-120")
    assert _tb_balances(db, org_id)


def test_void_invoice_reverses_to_zero(db):
    org_id, cust_id, pid = _setup(db)
    doc = _invoice(db, org_id, cust_id, pid)
    DocumentService(db).void(org_id, doc.id)

    for key in ("accounts_receivable", "sales_revenue", "sales_tax_payable", "cogs", "inventory"):
        assert _bal(db, org_id, key) == 0
    original = db.scalar(
        select(AccountingVoucher).where(
            AccountingVoucher.source_type == "invoice",
            AccountingVoucher.source_id == doc.id,
            AccountingVoucher.voucher_type == VoucherType.SALES_INVOICE,
        )
    )
    assert original.status == VoucherStatus.REVERSED
    assert _tb_balances(db, org_id)


def test_payment_received_posts_cash_and_clears_ar(db):
    org_id, cust_id, pid = _setup(db)
    doc = _invoice(db, org_id, cust_id, pid)

    pay_svc = PaymentService(db)
    pay = pay_svc.create(
        org_id,
        PaymentDirection.RECEIVED,
        PaymentCreate(
            party_id=cust_id,
            amount=doc.total,
            allocations=[PaymentAllocationInput(document_id=doc.id, amount=doc.total)],
        ),
    )
    pay_svc.submit(org_id, PaymentDirection.RECEIVED, pay.id)

    voucher = db.scalar(
        select(AccountingVoucher).where(
            AccountingVoucher.source_type == "payment_received",
            AccountingVoucher.source_id == pay.id,
        )
    )
    assert voucher is not None
    assert voucher.voucher_type == VoucherType.CUSTOMER_RECEIPT
    assert _bal(db, org_id, "cash") == doc.total
    assert _bal(db, org_id, "accounts_receivable") == 0  # invoice raised it, receipt cleared it
    assert _tb_balances(db, org_id)
