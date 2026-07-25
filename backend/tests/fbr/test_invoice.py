from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.core import crypto
from app.core.config import settings as app_settings
from app.core.crypto import encrypt_secret
from app.core.exceptions import BadRequestError
from app.core.security import hash_password
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import Document, TaxRate
from app.modules.fbr.client import FbrClient
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput
from app.modules.documents.service import DocumentService
from app.modules.fbr.invoice import FbrInvoiceBuilder
from app.modules.fbr.models import FbrReferenceData
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.users.models import User


def _seed_refs(db):
    db.add_all([
        FbrReferenceData(type="sale_type", code="75", description="Goods at standard rate (default)"),
        FbrReferenceData(type="tax_rate", code="728", description="18%", value=Decimal("18"), parent_type="sale_type", parent_code="75"),
        FbrReferenceData(type="uom", code="69", description="Numbers, pieces, units"),
    ])
    db.flush()


def _setup(db):
    user = User(email="inv@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Seller Co")
    org.ntn = "1234567-8"
    org.fbr_enabled = True
    org.fbr_province = "SINDH"
    org.address = {"line1": "1 Mill Road", "city": "Karachi", "state": "SINDH"}
    customer = Party(
        org_id=org.id,
        is_customer=True,
        name="Buyer Ltd",
        ntn="7654321",
        strn="3277876500000",
        billing_address={"line1": "9 Mall Road", "city": "Lahore", "state": "PUNJAB"},
    )
    product = Product(
        org_id=org.id,
        name="Widget",
        type="single",
        sale_price=Decimal("100"),
        hs_code="8432.1010",
        uom_code="69",
        sale_type_code="75",
        tax_rate_code="728",
    )
    db.add_all([customer, product])
    db.flush()
    return org, customer.id, product.id


def test_build_invoice_payload(db):
    _seed_refs(db)
    org, party_id, pid = _setup(db)
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "GST 18%"))
    invoice = DocumentService(db).create(
        org.id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            lines=[DocumentLineInput(product_id=pid, description="Widget", quantity=Decimal("2"),
                                     unit_price=Decimal("100"), tax_rate_id=tax.id)],
        ),
    )

    payload = FbrInvoiceBuilder(db).build(invoice, org)

    assert payload["sellerNTNCNIC"] == "12345678"
    assert payload["sellerProvince"] == "SINDH"
    assert payload["buyerNTNCNIC"] == "7654321"
    assert payload["buyerProvince"] == "PUNJAB"
    assert payload["buyerRegistrationType"] == "Registered"
    assert payload["invoiceType"] == "Sale Invoice"

    item = payload["items"][0]
    assert item["hsCode"] == "8432.1010"
    assert item["rate"] == "18%"
    assert item["uoM"] == "Numbers, pieces, units"
    assert item["saleType"] == "Goods at standard rate (default)"
    assert item["quantity"] == 2.0
    assert item["valueSalesExcludingST"] == 200.0
    assert item["salesTaxApplicable"] == 36.0


def test_fbr_tax_from_product_rate_and_further_tax(db):
    _seed_refs(db)
    org, party_id, pid = _setup(db)
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "GST 18%"))
    svc = DocumentService(db)

    def make():
        return svc.create(
            org.id,
            DocumentType.INVOICE,
            DocumentCreate(
                party_id=party_id,
                lines=[DocumentLineInput(product_id=pid, description="Widget", quantity=Decimal("2"),
                                         unit_price=Decimal("100"), tax_rate_id=tax.id)],
            ),
        )

    registered = make()
    assert registered.tax_total == Decimal("36")
    assert registered.further_tax_total == Decimal("0")
    assert registered.lines[0].tax_amount == Decimal("36")
    assert registered.total == Decimal("236")

    buyer = db.get(Party, party_id)
    buyer.strn = None
    db.flush()
    unregistered = make()
    assert unregistered.tax_total == Decimal("36")
    assert unregistered.further_tax_total == Decimal("6")
    assert unregistered.lines[0].further_tax == Decimal("6")
    assert unregistered.total == Decimal("242")
    payload = FbrInvoiceBuilder(db).build(unregistered, org)
    assert payload["items"][0]["furtherTax"] == 6.0


def test_fbr_fixed_rate_per_unit(db):
    _seed_refs(db)
    db.add(FbrReferenceData(type="tax_rate", code="1023", description="Rs.200",
                            value=Decimal("200"), parent_type="sale_type", parent_code="75"))
    db.flush()
    org, party_id, _ = _setup(db)
    fixed = Product(org_id=org.id, name="Cement", type="single", tax_rate_code="1023")
    db.add(fixed)
    db.flush()
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "GST 18%"))
    invoice = DocumentService(db).create(
        org.id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            lines=[DocumentLineInput(product_id=fixed.id, description="Cement", quantity=Decimal("3"),
                                     unit_price=Decimal("500"), tax_rate_id=tax.id)],
        ),
    )
    assert invoice.lines[0].tax_amount == Decimal("600")
    assert invoice.tax_total == Decimal("600")


def test_unregistered_buyer_without_strn(db):
    _seed_refs(db)
    org, party_id, pid = _setup(db)
    buyer = db.get(Party, party_id)
    buyer.strn = None
    db.flush()
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "GST 18%"))
    invoice = DocumentService(db).create(
        org.id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            lines=[DocumentLineInput(product_id=pid, description="Widget", quantity=Decimal("1"),
                                     unit_price=Decimal("100"), tax_rate_id=tax.id)],
        ),
    )
    payload = FbrInvoiceBuilder(db).build(invoice, org)
    assert payload["buyerRegistrationType"] == "Unregistered"


def _fbr_org(db, monkeypatch):
    monkeypatch.setattr(app_settings, "FBR_ENCRYPTION_KEY", Fernet.generate_key().decode())
    crypto._cipher.cache_clear()
    _seed_refs(db)
    org, party_id, pid = _setup(db)
    org.fbr_environment = "sandbox"
    org.fbr_sandbox_token = encrypt_secret("tok-abc")
    db.flush()
    return org, party_id, pid


def _make_invoice(db, org, party_id, pid):
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "GST 18%"))
    return DocumentService(db).create(
        org.id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            lines=[DocumentLineInput(product_id=pid, description="Widget", quantity=Decimal("1"),
                                     unit_price=Decimal("100"), tax_rate_id=tax.id)],
        ),
    )


def test_finalize_submits_to_fbr(db, monkeypatch):
    org, party_id, pid = _fbr_org(db, monkeypatch)
    valid = {"validationResponse": {"statusCode": "00", "status": "Valid"}}
    monkeypatch.setattr(FbrClient, "validate_invoice", lambda self, p: valid)
    monkeypatch.setattr(
        FbrClient, "post_invoice",
        lambda self, p: {"invoiceNumber": "7000007DI123", **valid},
    )
    svc = DocumentService(db)
    inv = _make_invoice(db, org, party_id, pid)
    finalized = svc.finalize(org.id, inv.id)
    assert finalized.status == DocumentStatus.SENT
    assert finalized.fbr_invoice_number == "7000007DI123"
    assert finalized.fbr_submitted_at is not None
    crypto._cipher.cache_clear()


def test_finalize_blocked_when_fbr_rejects(db, monkeypatch):
    org, party_id, pid = _fbr_org(db, monkeypatch)
    monkeypatch.setattr(
        FbrClient, "validate_invoice",
        lambda self, p: {"validationResponse": {"statusCode": "01", "status": "Invalid", "error": "bad HS code"}},
    )
    svc = DocumentService(db)
    inv = _make_invoice(db, org, party_id, pid)
    with pytest.raises(BadRequestError):
        svc.finalize(org.id, inv.id)
    assert db.get(Document, inv.id).status == DocumentStatus.DRAFT
    crypto._cipher.cache_clear()


def test_print_includes_fbr_qr(db):
    _seed_refs(db)
    org, party_id, pid = _setup(db)
    inv = _make_invoice(db, org, party_id, pid)
    inv.fbr_invoice_number = "7000007DI999"
    db.flush()
    from app.modules.documents.print.mapper import document_to_print

    printable = document_to_print(inv, org)
    assert printable.stamp_image_data_url
    assert printable.stamp_image_data_url.startswith("data:image/png")
    assert any(m.label == "FBR IRN" and m.value == "7000007DI999" for m in printable.meta)

    inv.fbr_invoice_number = None
    db.flush()
    assert document_to_print(inv, org).stamp_image_data_url is None


def _submit_ok(monkeypatch, irn):
    valid = {"validationResponse": {"statusCode": "00", "status": "Valid"}}
    monkeypatch.setattr(FbrClient, "validate_invoice", lambda self, p: valid)
    monkeypatch.setattr(FbrClient, "post_invoice", lambda self, p: {"invoiceNumber": irn, **valid})


def test_credit_note_references_invoice_and_one_per_invoice(db, monkeypatch):
    org, party_id, pid = _fbr_org(db, monkeypatch)
    _submit_ok(monkeypatch, "7000007DI111")
    svc = DocumentService(db)
    inv = _make_invoice(db, org, party_id, pid)
    svc.finalize(org.id, inv.id)

    cn = svc.convert(org.id, inv.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    payload = FbrInvoiceBuilder(db).build(cn, org)
    assert payload["invoiceType"] == "Debit Note"
    assert payload["invoiceRefNo"] == "7000007DI111"

    with pytest.raises(BadRequestError):
        svc.convert(org.id, inv.id, DocumentType.INVOICE, DocumentType.CREDIT_NOTE)
    crypto._cipher.cache_clear()


def test_cannot_void_filed_fbr_invoice(db, monkeypatch):
    org, party_id, pid = _fbr_org(db, monkeypatch)
    _submit_ok(monkeypatch, "7000007DI222")
    svc = DocumentService(db)
    inv = _make_invoice(db, org, party_id, pid)
    svc.finalize(org.id, inv.id)
    with pytest.raises(BadRequestError):
        svc.void(org.id, inv.id)
    crypto._cipher.cache_clear()


def test_variant_inherits_parent_fbr_fields(db):
    from app.modules.products.schemas import ProductCreate, VariantAttributeInput, VariantInput
    from app.modules.products.service import ProductService
    from app.modules.uoms.models import Uom

    _seed_refs(db)
    org, party_id, _pid = _setup(db)
    uom_id = db.scalar(select(Uom.id).where(Uom.org_id == org.id).order_by(Uom.id))
    parent = ProductService(db).create(
        org.id,
        ProductCreate(
            name="Shirt", nature="good", type="variable", uom_id=uom_id,
            hs_code="6109.1000", uom_code="69", sale_type_code="75", tax_rate_code="728",
            variant_attributes=[VariantAttributeInput(name="Size", options=["S", "M"])],
            variants=[VariantInput(options={"Size": "S"}), VariantInput(options={"Size": "M"})],
        ),
    )
    child = parent.variants[0]
    assert child.hs_code is None
    assert child.fbr("hs_code") == "6109.1000"

    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "GST 18%"))
    inv = DocumentService(db).create(
        org.id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            lines=[DocumentLineInput(product_id=child.id, description=child.name,
                                     quantity=Decimal("2"), unit_price=Decimal("100"), tax_rate_id=tax.id)],
        ),
    )
    assert inv.lines[0].tax_amount == Decimal("36")
    payload = FbrInvoiceBuilder(db).build(inv, org)
    assert payload["items"][0]["hsCode"] == "6109.1000"
    assert payload["items"][0]["salesTaxApplicable"] == 36.0


def test_seller_and_buyer_prefer_cnic(db):
    _seed_refs(db)
    org, party_id, pid = _setup(db)
    org.cnic = "35202-1234567-8"
    buyer = db.get(Party, party_id)
    buyer.cnic = "42101-7654321-1"
    db.flush()
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "GST 18%"))
    invoice = DocumentService(db).create(
        org.id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=party_id,
            lines=[DocumentLineInput(product_id=pid, description="Widget", quantity=Decimal("1"),
                                     unit_price=Decimal("100"), tax_rate_id=tax.id)],
        ),
    )
    payload = FbrInvoiceBuilder(db).build(invoice, org)
    assert payload["sellerNTNCNIC"] == "3520212345678"
    assert payload["buyerNTNCNIC"] == "4210176543211"
