from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.documents.enums import DocumentType
from app.modules.documents.models import TaxRate
from app.modules.documents.print.mapper import amount_in_words, branding_for, document_to_print
from app.modules.documents.print.service import DocumentPrintService
from app.modules.documents.print.skins import render_document_html
from app.modules.documents.schemas import DocumentCreate, DocumentLineInput, LotAllocationInput
from app.modules.documents.service import DocumentService
from app.modules.inventory.models import StockLot
from app.modules.locations.models import Location
from app.modules.orgs.models import Organization
from app.modules.orgs.service import OrgService
from app.modules.parties.models import Party
from app.modules.products.models import Product
from app.modules.users.models import User


def _setup(db):
    user = User(email="pr@test.io", hashed_password=hash_password("password123"))
    db.add(user)
    db.flush()
    org = OrgService(db).create_org_with_owner(owner=user, name="Acme Traders")
    org.ntn = "1234567-8"
    org.strn = "3277876111111"
    db.flush()
    customer = Party(org_id=org.id, is_customer=True, name="Beta Corp", ntn="7654321-0")
    product = Product(
        org_id=org.id,
        name="Widget",
        type="single",
        track_inventory=False,
        sale_price=Decimal("100"),
    )
    db.add_all([customer, product])
    db.flush()
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "Exempt"))
    doc = DocumentService(db).create(
        org.id,
        DocumentType.INVOICE,
        DocumentCreate(
            party_id=customer.id,
            lines=[
                DocumentLineInput(
                    product_id=product.id, description="Widget", quantity=Decimal(2),
                    unit_price=Decimal("100"), tax_rate_id=tax.id,
                )
            ],
        ),
    )
    return org, doc


def test_amount_in_words():
    assert amount_in_words(Decimal("140000"), "PKR") == "Rupees One Hundred Forty Thousand Only"
    assert amount_in_words(Decimal("0"), "PKR") == "Rupees Zero Only"


def test_document_maps_to_print_shape(db):
    org, doc = _setup(db)
    printed = document_to_print(doc, org)
    assert printed.title == "Tax Invoice"
    assert printed.document_no == doc.number
    assert printed.parties[0].heading == "Bill to"
    assert printed.parties[0].name == "Beta Corp"
    assert "NTN: 7654321-0" in printed.parties[0].lines
    assert "NTN: 1234567-8" in printed.company.lines
    assert len(printed.rows) == 1
    assert printed.rows[0].cells["description"] == "Widget"
    assert any(t.label == "Total" and t.emphasize for t in printed.totals)
    assert printed.amount_in_words.startswith("Rupees")


def test_bill_maps_with_vendor_heading(db):
    org, _ = _setup(db)
    vendor = Party(org_id=org.id, is_vendor=True, name="Supplier")
    product = db.scalar(select(Product).where(Product.org_id == org.id))
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "Exempt"))
    db.add(vendor)
    db.flush()
    bill = DocumentService(db).create(
        org.id,
        DocumentType.BILL,
        DocumentCreate(
            party_id=vendor.id,
            lines=[
                DocumentLineInput(
                    product_id=product.id, description="Widget", quantity=Decimal(1),
                    unit_price=Decimal("50"), tax_rate_id=tax.id,
                )
            ],
        ),
    )
    printed = document_to_print(bill, org)
    assert printed.title == "Bill"
    assert printed.parties[0].heading == "Vendor"


def test_physical_document_prints_lot_and_expiry_but_invoice_does_not(db):
    org, invoice = _setup(db)
    customer = invoice.party
    product = db.scalar(select(Product).where(Product.org_id == org.id))
    product.track_inventory = True
    product.tracking_mode = "lot"
    location = db.scalar(select(Location).where(Location.org_id == org.id))
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org.id, TaxRate.name == "Exempt"))
    lot = StockLot(
        org_id=org.id,
        product_id=product.id,
        lot_number="BATCH-001",
        expiry_date=date(2027, 12, 31),
    )
    db.add(lot)
    db.flush()
    challan = DocumentService(db).create(
        org.id,
        DocumentType.DELIVERY_CHALLAN,
        DocumentCreate(
            party_id=customer.id,
            warehouse_id=location.id,
            lines=[
                DocumentLineInput(
                    product_id=product.id,
                    description="Widget",
                    quantity=Decimal(2),
                    unit_price=Decimal("100"),
                    tax_rate_id=tax.id,
                    lot_allocations=[
                        LotAllocationInput(lot_id=lot.id, quantity=Decimal(2))
                    ],
                )
            ],
        ),
    )

    printed = document_to_print(challan, org)
    assert any(column.key == "tracking" for column in printed.columns)
    assert printed.rows[0].cells["tracking"] == "BATCH-001 × 2 · Exp 31 Dec 2027"
    assert all(column.key != "tracking" for column in document_to_print(invoice, org).columns)


def test_renders_self_contained_html(db):
    org, doc = _setup(db)
    html = render_document_html(document_to_print(doc, org), branding_for(org), "corporate")
    assert html.startswith("<!doctype html>")
    assert doc.number in html
    assert "Acme Traders" in html
    assert "Tax Invoice" in html
    assert "--accent:" in html
    # self-contained: no external stylesheet or script references
    assert "<link" not in html and "<script" not in html


def test_thermal_skin_renders(db):
    org, doc = _setup(db)
    html = render_document_html(document_to_print(doc, org), branding_for(org), "thermal")
    assert doc.number in html


def test_pdf_keeps_powered_by_only_in_page_footer(db):
    org, doc = _setup(db)
    org.keep_branding = True
    db.flush()
    captured = {}
    service = DocumentPrintService(db)

    def fake_pdf(html, paper, footer):
        captured.update(html=html, paper=paper, footer=footer)
        return b"pdf"

    service.pdf.html_to_pdf = fake_pdf
    content, _ = service.render_pdf(
        org.id, doc.id, DocumentType.INVOICE, "corporate", "A4"
    )

    assert content == b"pdf"
    assert "Powered by VinesFlow" not in captured["html"]
    assert "Powered by VinesFlow" in captured["footer"]


def test_preview_endpoint(client, db, register, org_id_of, h):
    token = register()
    org_id = org_id_of(token)
    headers = h(token, org_id)
    org = db.scalar(select(Organization).where(Organization.id == org_id))
    customer = Party(org_id=org_id, is_customer=True, name="Beta")
    product = Product(org_id=org_id, name="W", type="single", track_inventory=False)
    db.add_all([customer, product])
    db.flush()
    tax = db.scalar(select(TaxRate).where(TaxRate.org_id == org_id, TaxRate.name == "Exempt"))
    created = client.post(
        "/api/v1/invoices",
        headers=headers,
        json={
            "party_id": customer.id,
            "lines": [
                {"product_id": product.id, "description": "W", "quantity": 1,
                 "unit_price": 100, "tax_rate_id": tax.id}
            ],
        },
    ).json()["data"]

    res = client.get(f"/api/v1/invoices/{created['id']}/preview", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert created["number"] in res.text
    assert org.name in res.text
