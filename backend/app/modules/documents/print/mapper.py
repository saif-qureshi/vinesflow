from __future__ import annotations

import base64
import mimetypes
from datetime import date
from decimal import Decimal
from pathlib import Path

from num2words import num2words

from app.core.config import settings
from app.modules.documents.enums import DocumentType
from app.modules.documents.models import Document
from app.modules.fbr.qr import qr_data_uri
from app.modules.documents.print.print_document import (
    PrintBranding,
    PrintCompany,
    PrintColumn,
    PrintContact,
    PrintDocument,
    PrintMetaField,
    PrintParty,
    PrintRow,
    PrintTotalLine,
)
from app.modules.orgs.models import Organization

TITLES = {
    DocumentType.INVOICE: "Tax Invoice",
    DocumentType.BILL: "Bill",
    DocumentType.SALES_ORDER: "Sales Order",
    DocumentType.DELIVERY_CHALLAN: "Delivery Challan",
    DocumentType.PURCHASE_ORDER: "Purchase Order",
    DocumentType.GOODS_RECEIPT: "Goods Receipt Note",
    DocumentType.CREDIT_NOTE: "Credit Note",
}

_CURRENCY_WORDS = {"PKR": ("Rupees", "Paisa")}


def _money(value: Decimal | None) -> str:
    return f"{(value or Decimal('0')):,.2f}"


def _fmt_date(value: date | None) -> str:
    return value.strftime("%d %b %Y") if value else "—"


def _qty(value: Decimal | None) -> str:
    number = value or Decimal("0")
    normalized = number.normalize()
    return f"{normalized:f}" if normalized == normalized.to_integral() else f"{number:,.3f}"


def _address_lines(address: dict | None) -> list[str]:
    if not address:
        return []
    parts = [
        address.get("line1"),
        address.get("line2"),
        ", ".join(p for p in [address.get("city"), address.get("state")] if p) or None,
        ", ".join(p for p in [address.get("country"), address.get("postal_code")] if p) or None,
        address.get("phone"),
    ]
    return [str(p) for p in parts if p]


def amount_in_words(total: Decimal, currency: str) -> str:
    major, minor = _CURRENCY_WORDS.get(currency.upper(), ("", ""))
    whole = int(total)
    fraction = int((total - whole) * 100)
    words = num2words(whole, lang="en").replace(" and ", " ").title()
    text = f"{major} {words}".strip()
    if fraction:
        text += f" and {num2words(fraction, lang='en').title()} {minor}".rstrip()
    return f"{text} Only"


def _logo_data_url(org: Organization) -> str | None:
    if not org.logo_url or settings.STORAGE_BACKEND != "local":
        return None
    marker = "/media/files/"
    if marker not in org.logo_url:
        return None
    key = org.logo_url.split(marker, 1)[1]
    root = Path(settings.MEDIA_LOCAL_DIR).resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return None
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _company(org: Organization) -> PrintCompany:
    lines = _address_lines(org.address)
    if org.ntn:
        lines.append(f"NTN: {org.ntn}")
    if org.strn:
        lines.append(f"STRN: {org.strn}")
    return PrintCompany(name=org.name, logo_data_url=_logo_data_url(org), lines=lines)


_FBR_LOGO_PATH = Path(__file__).parent / "assets" / "fbr-logo.png"


def _fbr_qr(content: str) -> str:
    return qr_data_uri(content)


def _fbr_logo() -> str | None:
    if not _FBR_LOGO_PATH.exists():
        return None
    mime = mimetypes.guess_type(str(_FBR_LOGO_PATH))[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(_FBR_LOGO_PATH.read_bytes()).decode()}"


def document_to_print(doc: Document, org: Organization) -> PrintDocument:
    is_purchase = doc.type in (
        DocumentType.BILL,
        DocumentType.PURCHASE_ORDER,
        DocumentType.GOODS_RECEIPT,
    )
    party = doc.party
    party_lines = _address_lines(doc.billing_address)
    if party is not None:
        if party.ntn:
            party_lines.append(f"NTN: {party.ntn}")
        if party.strn:
            party_lines.append(f"STRN: {party.strn}")
        if party.email:
            party_lines.append(party.email)

    meta = [
        PrintMetaField(label="Date", value=_fmt_date(doc.issue_date)),
        PrintMetaField(label="Due date", value=_fmt_date(doc.due_date)),
    ]
    if doc.reference:
        meta.append(PrintMetaField(label="Reference", value=doc.reference))
    if doc.type == DocumentType.CREDIT_NOTE and doc.fbr_reason:
        reason = doc.fbr_reason
        if doc.fbr_reason_remarks:
            reason = f"{reason} — {doc.fbr_reason_remarks}"
        meta.append(PrintMetaField(label="Reason", value=reason))
    if doc.fbr_invoice_number:
        meta.append(PrintMetaField(label="FBR IRN", value=doc.fbr_invoice_number))

    columns = [
        PrintColumn(key="description", label="Description"),
        PrintColumn(key="qty", label="Qty", align="right"),
        PrintColumn(key="rate", label="Rate", align="right"),
        PrintColumn(key="discount", label="Discount", align="right"),
        PrintColumn(key="tax", label="Tax", align="right"),
        PrintColumn(key="amount", label="Amount", align="right"),
    ]
    rows = [
        PrintRow(
            cells={
                "description": line.description,
                "qty": _qty(line.quantity),
                "rate": _money(line.unit_price),
                "discount": _money(line.discount) if line.discount else "—",
                "tax": _money(line.tax_amount),
                "amount": _money(line.line_total),
            }
        )
        for line in doc.lines
    ]

    totals = [PrintTotalLine(label="Subtotal", value=_money(doc.subtotal))]
    if doc.discount_total:
        totals.append(PrintTotalLine(label="Discount", value=f"-{_money(doc.discount_total)}"))
    totals.append(PrintTotalLine(label="Tax", value=_money(doc.tax_total)))
    if doc.shipping:
        totals.append(PrintTotalLine(label="Shipping", value=_money(doc.shipping)))
    if doc.adjustment:
        totals.append(PrintTotalLine(label="Adjustment", value=_money(doc.adjustment)))
    totals.append(PrintTotalLine(label="Total", value=_money(doc.total), emphasize=True))
    if doc.amount_paid:
        totals.append(PrintTotalLine(label="Amount paid", value=_money(doc.amount_paid)))
        totals.append(PrintTotalLine(label="Balance due", value=_money(doc.total - doc.amount_paid)))

    contact = _address_lines(org.address)
    return PrintDocument(
        title=TITLES.get(doc.type, doc.type.replace("_", " ").title()),
        document_no=doc.number,
        company=_company(org),
        parties=[
            PrintParty(
                heading="Vendor" if is_purchase else "Bill to",
                name=party.name if party else "—",
                lines=party_lines,
            )
        ],
        meta=meta,
        columns=columns,
        rows=rows,
        totals=totals,
        currency=doc.currency,
        amount_in_words=amount_in_words(doc.total, doc.currency),
        footer_contact=PrintContact(address=", ".join(contact) or None) if contact else None,
        notes=doc.notes,
        stamp_image_data_url=_fbr_qr(doc.fbr_invoice_number) if doc.fbr_invoice_number else None,
        stamp_overlay_data_url=_fbr_logo() if doc.fbr_invoice_number else None,
    )


def branding_for(org: Organization) -> PrintBranding:
    return PrintBranding(
        accent_color=org.accent_color or "#0f766e",
        show_logo=True,
        footer_text="Powered by VinesFlow" if org.keep_branding else None,
        terms=None,
    )
