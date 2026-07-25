from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.documents.enums import DocumentType
from app.modules.documents.models import Document
from app.modules.fbr.models import FbrReferenceData
from app.modules.orgs.models import Organization
from app.modules.products.models import Product


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _address(addr) -> str:
    addr = _as_dict(addr)
    parts = [addr.get("line1"), addr.get("line2"), addr.get("city"), addr.get("state")]
    return ", ".join(p for p in parts if p)


def _num(value) -> float:
    return float(value or 0)


def _digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isalnum())


class FbrInvoiceBuilder:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._refs: dict[tuple[str, str], FbrReferenceData | None] = {}

    def _ref(self, ref_type: str, code: str | None) -> FbrReferenceData | None:
        if not code:
            return None
        key = (ref_type, code)
        if key not in self._refs:
            self._refs[key] = self.db.scalar(
                select(FbrReferenceData)
                .where(FbrReferenceData.type == ref_type, FbrReferenceData.code == code)
                .limit(1)
            )
        return self._refs[key]

    def _desc(self, ref_type: str, code: str | None) -> str:
        row = self._ref(ref_type, code)
        return (row.description if row else "") or ""

    def build(self, doc: Document, org: Organization, scenario_id: str | None = None) -> dict:
        party = doc.party
        product_ids = [line.product_id for line in doc.lines if line.product_id]
        products = {
            p.id: p
            for p in self.db.scalars(select(Product).where(Product.id.in_(product_ids)))
        } if product_ids else {}

        buyer_address = _as_dict(party.billing_address) if party else {}
        buyer_id = (party.ntn or party.cnic) if party else None
        registration = "Registered" if (party and party.strn) else "Unregistered"

        is_credit = doc.type == DocumentType.CREDIT_NOTE
        invoice_ref = ""
        if is_credit and doc.source_document_id:
            source = self.db.get(Document, doc.source_document_id)
            invoice_ref = (source.fbr_invoice_number or "") if source else ""

        items = []
        for line in doc.lines:
            product = products.get(line.product_id)
            base = round(_num(line.quantity) * _num(line.unit_price) - _num(line.discount), 2)
            sales_tax = _num(line.tax_amount)
            further_tax = _num(line.further_tax)
            items.append({
                "hsCode": (product.fbr("hs_code") if product else "") or "",
                "productDescription": line.description,
                "rate": self._desc("tax_rate", product.fbr("tax_rate_code")) if product else "",
                "uoM": self._desc("uom", product.fbr("uom_code")) if product else "",
                "quantity": _num(line.quantity),
                "valueSalesExcludingST": base,
                "salesTaxApplicable": sales_tax,
                "salesTaxWithheldAtSource": 0,
                "extraTax": "",
                "furtherTax": further_tax,
                "sroScheduleNo": self._desc("sro_schedule", product.fbr("sro_schedule_code")) if product else "",
                "fedPayable": 0,
                "discount": _num(line.discount),
                "saleType": self._desc("sale_type", product.fbr("sale_type_code")) if product else "",
                "sroItemSerialNo": (product.fbr("sro_item_serial") if product else "") or "",
                "totalValues": round(base + sales_tax + further_tax, 2),
            })

        payload = {
            "invoiceType": "Debit Note" if is_credit else "Sale Invoice",
            "invoiceDate": doc.issue_date.isoformat() if doc.issue_date else "",
            "sellerNTNCNIC": _digits(org.ntn),
            "sellerBusinessName": org.name,
            "sellerProvince": doc.fbr_sale_origin or org.fbr_province or "",
            "sellerAddress": _address(org.address),
            "buyerNTNCNIC": _digits(buyer_id),
            "buyerBusinessName": party.name if party else "",
            "buyerProvince": doc.fbr_sale_destination or buyer_address.get("state") or "",
            "buyerAddress": _address(buyer_address),
            "buyerRegistrationType": registration,
            "invoiceRefNo": invoice_ref,
            "items": items,
        }
        resolved_scenario = doc.fbr_scenario_id or scenario_id
        if resolved_scenario:
            payload["scenarioId"] = resolved_scenario
        return payload
