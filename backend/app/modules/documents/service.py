from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core import ledger as _ledger
from app.core.exceptions import AppError, BadRequestError, ConflictError, NotFoundError
from app.core.pagination import paginate_cursor
from app.modules.activities.service import ActivityService
from app.modules.documents.enums import (
    DEFAULT_PREFIXES,
    DocumentPaymentStatus,
    DocumentStatus,
    DocumentType,
)
from app.modules.documents.models import (
    Bill,
    CreditNote,
    DeliveryChallan,
    Document,
    DocumentLine,
    DocumentLineLotAllocation,
    DocumentLineSerial,
    GoodsReceipt,
    Invoice,
    PurchaseOrder,
    SalesOrder,
    TaxRate,
)
from app.modules.documents.numbering import assign_number, numbering_format, preview_number
from app.modules.documents.schemas import (
    DocumentCreate,
    DocumentLineInput,
    DocumentListQuery,
    DocumentUpdate,
    SellableItemRead,
    TaxRateCreate,
)
from app.modules.fbr.models import FbrSubmissionAttempt
from app.modules.inventory.service import InventoryService
from app.modules.inventory.tracking_service import TrackingService
from app.modules.locations.models import Location
from app.modules.parties.models import Party
from app.modules.products.models import Product

_ZERO = Decimal("0")
_CENTS = Decimal("0.01")
_HUNDRED = Decimal("100")

DEFAULT_TAX_RATES = [("GST 18%", Decimal("18")), ("Exempt", Decimal("0"))]

DOCUMENT_CLASSES: dict[DocumentType, type[Document]] = {
    DocumentType.SALES_ORDER: SalesOrder,
    DocumentType.DELIVERY_CHALLAN: DeliveryChallan,
    DocumentType.INVOICE: Invoice,
    DocumentType.CREDIT_NOTE: CreditNote,
    DocumentType.PURCHASE_ORDER: PurchaseOrder,
    DocumentType.GOODS_RECEIPT: GoodsReceipt,
    DocumentType.BILL: Bill,
}

# What a finalized document can be turned into.
CONVERSIONS: dict[DocumentType, list[DocumentType]] = {
    DocumentType.SALES_ORDER: [DocumentType.DELIVERY_CHALLAN, DocumentType.INVOICE],
    DocumentType.DELIVERY_CHALLAN: [DocumentType.INVOICE],
    DocumentType.INVOICE: [DocumentType.CREDIT_NOTE],
    DocumentType.PURCHASE_ORDER: [DocumentType.GOODS_RECEIPT, DocumentType.BILL],
    DocumentType.GOODS_RECEIPT: [DocumentType.BILL],
}

# Orders stop committing / expecting stock once a converted document is finalized.
CLOSED_ON_CONVERT = {DocumentType.SALES_ORDER, DocumentType.PURCHASE_ORDER}

SALES_TYPES = {
    DocumentType.SALES_ORDER,
    DocumentType.DELIVERY_CHALLAN,
    DocumentType.INVOICE,
    DocumentType.SALES_RECEIPT,
    DocumentType.CREDIT_NOTE,
}

FINANCIAL_TYPES = {DocumentType.INVOICE, DocumentType.BILL}
FBR_TYPES = {DocumentType.INVOICE, DocumentType.CREDIT_NOTE}
BIN_ENABLED_TYPES = {
    DocumentType.DELIVERY_CHALLAN,
    DocumentType.INVOICE,
    DocumentType.CREDIT_NOTE,
    DocumentType.GOODS_RECEIPT,
    DocumentType.BILL,
}


def _q(value: Decimal) -> Decimal:
    return Decimal(value).quantize(_CENTS)


def _fbr_line_tax(
    rate_desc: str, rate_value: Decimal, taxable: Decimal, quantity: Decimal
) -> Decimal:
    desc = (rate_desc or "").strip().lower()
    if "%" in desc:
        return _q(taxable * rate_value / _HUNDRED)
    if "rs" in desc:
        return _q(rate_value * quantity)
    return _ZERO


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.activity = ActivityService(db)
        self.inventory = InventoryService(db)
        self.tracking = TrackingService(db)
        self.ledger = _ledger.ledger_poster

    # --- Seeding ----------------------------------------------------------

    def seed_tax_rates(self, org_id: int) -> None:
        existing = set(self.db.scalars(select(TaxRate.name).where(TaxRate.org_id == org_id)))
        self.db.add_all(
            TaxRate(org_id=org_id, name=name, rate=rate, is_system=True)
            for name, rate in DEFAULT_TAX_RATES
            if name not in existing
        )
        self.db.flush()

    # --- Tax rates --------------------------------------------------------

    def list_tax_rates(self, org_id: int) -> list[TaxRate]:
        return list(
            self.db.scalars(select(TaxRate).where(TaxRate.org_id == org_id).order_by(TaxRate.id))
        )

    def create_tax_rate(self, org_id: int, payload: TaxRateCreate) -> TaxRate:
        if self.db.scalar(
            select(TaxRate.id).where(TaxRate.org_id == org_id, TaxRate.name == payload.name)
        ):
            raise ConflictError("A tax rate with that name already exists")
        rate = TaxRate(
            org_id=org_id, name=payload.name, rate=payload.rate, is_active=payload.is_active
        )
        self.db.add(rate)
        self.db.commit()
        self.db.refresh(rate)
        return rate

    # --- Sellable items (document line picker) ----------------------------

    def sellable_items(
        self, org_id: int, search: str | None, limit: int, warehouse_id: int | None = None
    ) -> list[SellableItemRead]:
        stmt = select(Product).where(
            Product.org_id == org_id,
            Product.type == "single",
            Product.is_active.is_(True),
        )
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
        products = list(self.db.scalars(stmt.order_by(Product.name).limit(limit)))
        rate_rows = self._fbr_rate_rows(p.fbr("tax_rate_code") for p in products)
        stock = self._stock_levels(org_id, [p.id for p in products], warehouse_id)
        return [
            SellableItemRead(
                id=p.id,
                name=p.name,
                sku=p.sku,
                description=p.description or (p.parent.description if p.parent else None),
                image_url=self._item_image(p),
                uom_symbol=p.uom.symbol if p.uom else None,
                sale_price=p.sale_price,
                purchase_price=p.purchase_price,
                fbr_rate=(
                    rate_rows[p.fbr("tax_rate_code")].description
                    if p.fbr("tax_rate_code") in rate_rows
                    else None
                ),
                track_inventory=p.track_inventory,
                tracking_mode=p.tracking_mode,
                stock=stock.get(p.id, _ZERO) if p.track_inventory else None,
            )
            for p in products
        ]

    def stock_on_hand(
        self, org_id: int, product_ids: list[int], warehouse_id: int | None
    ) -> dict[int, Decimal]:
        return self._stock_levels(org_id, product_ids, warehouse_id)

    def _set_explicit_number(self, doc: Document, number: str) -> None:
        doc.number = number
        savepoint = self.db.begin_nested()
        try:
            self.db.add(doc)
            self.db.flush()
            savepoint.commit()
        except IntegrityError as exc:
            savepoint.rollback()
            raise ConflictError(f"Number '{number}' is already in use") from exc

    def next_number(self, org_id: int, doc_type: DocumentType) -> str:
        prefix, start, restart = numbering_format(
            self.db, org_id, str(doc_type), DEFAULT_PREFIXES[doc_type]
        )
        return preview_number(
            self.db,
            Document.number,
            prefix,
            start,
            restart,
            date.today().year,
            Document.org_id == org_id,
            Document.type == doc_type,
        )

    def _stock_levels(self, org_id: int, product_ids: list[int], warehouse_id: int | None) -> dict:
        from sqlalchemy import func

        from app.modules.inventory.models import StockLevel

        if not product_ids:
            return {}
        stmt = select(StockLevel.product_id, func.sum(StockLevel.quantity)).where(
            StockLevel.org_id == org_id, StockLevel.product_id.in_(product_ids)
        )
        if warehouse_id:
            stmt = stmt.where(StockLevel.location_id == warehouse_id)
        stmt = stmt.group_by(StockLevel.product_id)
        return {pid: qty for pid, qty in self.db.execute(stmt)}

    def _fbr_rate_rows(self, codes) -> dict:
        from app.modules.fbr.models import FbrReferenceData

        wanted = {c for c in codes if c}
        if not wanted:
            return {}
        rows = self.db.scalars(
            select(FbrReferenceData).where(
                FbrReferenceData.type == "tax_rate", FbrReferenceData.code.in_(wanted)
            )
        )
        return {row.code: row for row in rows}

    @staticmethod
    def _item_image(product: Product) -> str | None:
        if product.media:
            return product.media[0].url
        if product.parent and product.parent.media:
            return product.parent.media[0].url
        return None

    def apply_settlement(self, doc: Document, delta: Decimal) -> None:
        paid = doc.amount_paid + delta
        if paid < _ZERO:
            paid = _ZERO
        doc.amount_paid = paid
        if paid <= _ZERO:
            doc.payment_status = DocumentPaymentStatus.UNPAID
        elif paid >= doc.total:
            doc.payment_status = DocumentPaymentStatus.PAID
        else:
            doc.payment_status = DocumentPaymentStatus.PARTIAL

    def _tax_map(self, org_id: int, lines: list[DocumentLineInput]) -> dict[int, TaxRate]:
        ids = {line.tax_rate_id for line in lines if line.tax_rate_id is not None}
        if not ids:
            return {}
        rates = {
            r.id: r
            for r in self.db.scalars(
                select(TaxRate).where(TaxRate.org_id == org_id, TaxRate.id.in_(ids))
            )
        }
        if len(rates) != len(ids):
            raise NotFoundError("One or more tax rates were not found")
        return rates

    def _validate_products(self, org_id: int, lines: list[DocumentLineInput]) -> None:
        ids = {line.product_id for line in lines if line.product_id is not None}
        if not ids:
            return
        found = set(
            self.db.scalars(select(Product.id).where(Product.org_id == org_id, Product.id.in_(ids)))
        )
        if ids - found:
            raise NotFoundError("One or more items were not found")

    def _build_lines(
        self, org_id: int, doc_type: DocumentType, line_inputs: list[DocumentLineInput]
    ) -> tuple[list[DocumentLine], Decimal, Decimal, Decimal]:
        self._validate_products(org_id, line_inputs)
        tax_map = self._tax_map(org_id, line_inputs)
        product_ids = {line.product_id for line in line_inputs if line.product_id is not None}
        products = {
            product.id: product
            for product in self.db.scalars(
                select(Product).where(Product.org_id == org_id, Product.id.in_(product_ids))
            )
        }
        lines: list[DocumentLine] = []
        subtotal = discount_total = tax_total = _ZERO
        for i, line in enumerate(line_inputs):
            base = _q(line.quantity * line.unit_price)
            if line.discount_type == "percent":
                discount = _q(base * line.discount_value / _HUNDRED)
            else:
                discount = _q(line.discount_value)
            discount = min(discount, base)
            taxable = base - discount
            rate = tax_map[line.tax_rate_id].rate if line.tax_rate_id is not None else _ZERO
            tax = _q(taxable * rate / _HUNDRED)
            product = products.get(line.product_id)
            if doc_type not in BIN_ENABLED_TYPES and (line.lot_allocations or line.serial_numbers):
                raise BadRequestError(
                    "Lots and serial numbers are selected when goods are received or dispatched"
                )
            if line.lot_allocations and (product is None or product.tracking_mode != "lot"):
                raise BadRequestError("Lot allocations require a lot-tracked item")
            if line.serial_numbers and (product is None or product.tracking_mode != "serial"):
                raise BadRequestError("Serial numbers require a serial-tracked item")
            document_line = DocumentLine(
                product_id=line.product_id,
                bin_id=line.bin_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                discount_type=line.discount_type,
                discount_value=line.discount_value,
                discount=discount,
                tax_rate_id=line.tax_rate_id,
                tax_amount=tax,
                line_total=taxable + tax,
                sort_order=i,
            )
            if product is not None and line.lot_allocations:
                allow_create = DOCUMENT_CLASSES[doc_type].stock_direction > 0
                resolved_allocations = [
                    (
                        self.tracking.resolve_lot(
                            org_id,
                            product.id,
                            lot_id=allocation.lot_id,
                            lot_number=allocation.lot_number,
                            manufactured_date=allocation.manufactured_date,
                            expiry_date=allocation.expiry_date,
                            allow_create=allow_create,
                        ),
                        allocation.quantity,
                    )
                    for allocation in line.lot_allocations
                ]
                lot_ids = [lot.id for lot, _ in resolved_allocations]
                if len(lot_ids) != len(set(lot_ids)):
                    raise BadRequestError("A lot can only be allocated once on each line")
                document_line.lot_allocations = [
                    DocumentLineLotAllocation(lot_id=lot.id, quantity=quantity)
                    for lot, quantity in resolved_allocations
                ]
            if product is not None and line.serial_numbers:
                document_line.serials = [
                    DocumentLineSerial(serial_number=serial_number)
                    for serial_number in self.tracking.normalize_serials(line.serial_numbers)
                ]
            lines.append(document_line)
            subtotal += base
            discount_total += discount
            tax_total += tax
        return lines, subtotal, discount_total, tax_total

    def _validate_line_bins(
        self,
        org_id: int,
        doc_type: DocumentType,
        warehouse_id: int | None,
        lines: list[DocumentLine],
    ) -> None:
        bin_ids = {line.bin_id for line in lines if line.bin_id is not None}
        if not bin_ids:
            return
        if doc_type not in BIN_ENABLED_TYPES:
            raise BadRequestError(
                "Bins are selected when goods are received or dispatched, not on orders"
            )
        product_ids = {line.product_id for line in lines if line.bin_id is not None}
        tracked_ids = set(
            self.db.scalars(
                select(Product.id).where(
                    Product.org_id == org_id,
                    Product.id.in_([product_id for product_id in product_ids if product_id]),
                    Product.track_inventory.is_(True),
                )
            )
        )
        if None in product_ids or tracked_ids != product_ids:
            raise BadRequestError("Bins can only be selected for inventory-tracked items")
        if warehouse_id is None:
            raise BadRequestError("Select a warehouse before selecting a bin")
        for bin_id in bin_ids:
            self.inventory.bins.validate_for_location(org_id, warehouse_id, bin_id)

    def _apply_totals(
        self,
        doc: Document,
        subtotal: Decimal,
        discount_total: Decimal,
        tax_total: Decimal,
        further_total: Decimal = _ZERO,
    ) -> None:
        doc.subtotal = subtotal
        doc.discount_total = discount_total
        doc.tax_total = tax_total
        doc.further_tax_total = further_total
        doc.total = (
            subtotal - discount_total + tax_total + further_total + doc.shipping + doc.adjustment
        )

    def _org_fbr_enabled(self, org_id: int) -> bool:
        from app.modules.orgs.models import Organization

        return bool(
            self.db.scalar(select(Organization.fbr_enabled).where(Organization.id == org_id))
        )

    def _apply_fbr_tax(
        self, org_id: int, lines: list[DocumentLine], party: Party | None
    ) -> tuple[Decimal, Decimal]:
        further_rate = _ZERO if (party and party.strn) else Decimal("3")
        product_ids = [line.product_id for line in lines if line.product_id]
        products = (
            {p.id: p for p in self.db.scalars(select(Product).where(Product.id.in_(product_ids)))}
            if product_ids
            else {}
        )
        rate_rows = self._fbr_rate_rows(p.fbr("tax_rate_code") for p in products.values())

        tax_total = further_total = _ZERO
        for line in lines:
            product = products.get(line.product_id)
            taxable = _q(line.quantity * line.unit_price) - line.discount
            rate = rate_rows.get(product.fbr("tax_rate_code")) if product else None
            sales_tax = (
                _fbr_line_tax(rate.description, rate.value or _ZERO, taxable, line.quantity)
                if rate
                else _ZERO
            )
            further = _q(taxable * further_rate / _HUNDRED)
            line.tax_amount = sales_tax
            line.further_tax = further
            line.line_total = taxable + sales_tax + further
            tax_total += sales_tax
            further_total += further
        return tax_total, further_total

    def _get_party(self, org_id: int, party_id: int, doc_type: DocumentType) -> Party:
        party = self.db.scalar(select(Party).where(Party.id == party_id, Party.org_id == org_id))
        if party is None:
            label = "Customer" if doc_type in SALES_TYPES else "Vendor"
            raise NotFoundError(f"{label} not found")
        return party

    def _default_location(self, org_id: int) -> int | None:
        return self.db.scalar(
            select(Location.id)
            .where(Location.org_id == org_id, Location.is_active.is_(True))
            .order_by(Location.is_default.desc(), Location.id)
        )

    def _validate_warehouse(self, org_id: int, warehouse_id: int) -> None:
        location_id = self.db.scalar(
            select(Location.id).where(
                Location.id == warehouse_id,
                Location.org_id == org_id,
                Location.is_active.is_(True),
            )
        )
        if location_id is None:
            raise NotFoundError("Warehouse not found")

    def _default_due(self, issue_date: date, party: Party) -> date | None:
        if party.payment_term_days:
            return issue_date + timedelta(days=party.payment_term_days)
        return None

    @staticmethod
    def _validate_type_fields(
        doc_type: DocumentType, payload: DocumentCreate | DocumentUpdate
    ) -> None:
        fields = payload.model_fields_set

        def supplied(name: str) -> bool:
            return name in fields and getattr(payload, name) is not None

        if supplied("due_date") and doc_type not in FINANCIAL_TYPES:
            raise BadRequestError("Due date is only available for invoices and bills")
        if supplied("expected_shipment_date") and doc_type != DocumentType.SALES_ORDER:
            raise BadRequestError("Expected shipment date is only available for sales orders")
        fbr_fields = ("fbr_sale_origin", "fbr_sale_destination", "fbr_scenario_id")
        if any(supplied(field) for field in fbr_fields) and doc_type not in FBR_TYPES:
            raise BadRequestError(
                "FBR filing fields are only available for invoices and credit notes"
            )
        reason_fields = ("fbr_reason", "fbr_reason_remarks")
        if any(supplied(field) for field in reason_fields) and doc_type != DocumentType.CREDIT_NOTE:
            raise BadRequestError("FBR reason fields are only available for credit notes")

    def get(self, org_id: int, doc_id: int) -> Document:
        doc = self.db.scalar(
            select(Document)
            .where(Document.id == doc_id, Document.org_id == org_id)
            .options(joinedload(Document.party))
        )
        if doc is None:
            raise NotFoundError("Document not found")
        return doc

    def get_of_type(self, org_id: int, doc_id: int, doc_type: DocumentType) -> Document:
        doc = self.get(org_id, doc_id)
        if doc.type != doc_type:
            raise NotFoundError("Document not found")
        return doc

    def _get_for_update(self, org_id: int, doc_id: int) -> Document:
        doc = self.db.scalar(
            select(Document)
            .where(Document.id == doc_id, Document.org_id == org_id)
            .with_for_update()
        )
        if doc is None:
            raise NotFoundError("Document not found")
        return doc

    def create(self, org_id: int, doc_type: DocumentType, payload: DocumentCreate) -> Document:
        self._validate_type_fields(doc_type, payload)
        doc_cls = DOCUMENT_CLASSES[doc_type]
        party = self._get_party(org_id, payload.party_id, doc_type)
        if payload.warehouse_id is not None:
            self._validate_warehouse(org_id, payload.warehouse_id)
        issue_date = payload.issue_date or date.today()
        due_date = (
            payload.due_date or self._default_due(issue_date, party)
            if doc_type in FINANCIAL_TYPES
            else None
        )
        prefix, start, restart = numbering_format(
            self.db, org_id, str(doc_type), DEFAULT_PREFIXES[doc_type]
        )
        doc = doc_cls(
            org_id=org_id,
            status=DocumentStatus.DRAFT,
            party_id=party.id,
            warehouse_id=payload.warehouse_id,
            issue_date=issue_date,
            due_date=due_date,
            expected_shipment_date=(
                payload.expected_shipment_date if doc_type == DocumentType.SALES_ORDER else None
            ),
            reference=payload.reference,
            notes=payload.notes,
            terms=payload.terms,
            shipping=_q(payload.shipping),
            adjustment=_q(payload.adjustment),
            billing_address=party.billing_address,
            shipping_address=party.shipping_address,
            fbr_sale_origin=payload.fbr_sale_origin if doc_type in FBR_TYPES else None,
            fbr_sale_destination=payload.fbr_sale_destination if doc_type in FBR_TYPES else None,
            fbr_scenario_id=payload.fbr_scenario_id if doc_type in FBR_TYPES else None,
            fbr_reason=(payload.fbr_reason if doc_type == DocumentType.CREDIT_NOTE else None),
            fbr_reason_remarks=(
                payload.fbr_reason_remarks if doc_type == DocumentType.CREDIT_NOTE else None
            ),
        )
        lines, subtotal, discount_total, tax_total = self._build_lines(
            org_id, doc_type, payload.lines
        )
        self._validate_line_bins(org_id, doc_type, doc.warehouse_id, lines)
        doc.lines = lines
        further_total = _ZERO
        if doc_type in (DocumentType.INVOICE, DocumentType.CREDIT_NOTE) and self._org_fbr_enabled(
            org_id
        ):
            tax_total, further_total = self._apply_fbr_tax(org_id, lines, party)
        self._apply_totals(doc, subtotal, discount_total, tax_total, further_total)
        if payload.number and payload.number.strip():
            self._set_explicit_number(doc, payload.number.strip())
        else:
            assign_number(
                self.db,
                doc,
                Document.number,
                prefix,
                start,
                restart,
                issue_date.year,
                Document.org_id == org_id,
                Document.type == doc_type,
            )
        self.activity.record(org_id, "created", doc_type, doc.number, entity_id=doc.id)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def list_documents(
        self, org_id: int, doc_type: DocumentType, query: DocumentListQuery
    ) -> tuple[list[Document], str | None, bool]:
        stmt = select(Document).where(Document.org_id == org_id, Document.type == doc_type)
        if query.status:
            stmt = stmt.where(Document.status == query.status)
        if query.payment_status:
            stmt = stmt.where(Document.payment_status == query.payment_status)
        if query.party_id is not None:
            stmt = stmt.where(Document.party_id == query.party_id)
        if query.search:
            like = f"%{query.search.strip()}%"
            stmt = stmt.where(or_(Document.number.ilike(like), Document.reference.ilike(like)))
        return paginate_cursor(self.db, stmt, Document.id, query)

    def update(
        self, org_id: int, doc_id: int, doc_type: DocumentType, payload: DocumentUpdate
    ) -> Document:
        self._validate_type_fields(doc_type, payload)
        doc = self.get_of_type(org_id, doc_id, doc_type)
        if doc.status != DocumentStatus.DRAFT:
            raise BadRequestError("Only draft documents can be edited")
        fields = payload.model_fields_set
        if "number" in fields and payload.number and payload.number.strip():
            new_number = payload.number.strip()
            if new_number != doc.number:
                clash = self.db.scalar(
                    select(Document.id).where(
                        Document.org_id == org_id,
                        Document.type == doc_type,
                        Document.number == new_number,
                        Document.id != doc.id,
                    )
                )
                if clash:
                    raise ConflictError(f"Number '{new_number}' is already in use")
                doc.number = new_number
        if "party_id" in fields and payload.party_id is not None:
            party = self._get_party(org_id, payload.party_id, doc_type)
            doc.party_id = party.id
            doc.billing_address = party.billing_address
            doc.shipping_address = party.shipping_address
        if "warehouse_id" in fields and payload.warehouse_id is not None:
            self._validate_warehouse(org_id, payload.warehouse_id)
        for field in (
            "issue_date",
            "reference",
            "warehouse_id",
            "notes",
            "terms",
        ):
            if field in fields:
                setattr(doc, field, getattr(payload, field))
        if doc_type in FINANCIAL_TYPES and "due_date" in fields:
            doc.due_date = payload.due_date
        if doc_type == DocumentType.SALES_ORDER and "expected_shipment_date" in fields:
            doc.expected_shipment_date = payload.expected_shipment_date
        if doc_type in FBR_TYPES:
            for field in ("fbr_sale_origin", "fbr_sale_destination", "fbr_scenario_id"):
                if field in fields:
                    setattr(doc, field, getattr(payload, field))
        if doc_type == DocumentType.CREDIT_NOTE:
            for field in ("fbr_reason", "fbr_reason_remarks"):
                if field in fields:
                    setattr(doc, field, getattr(payload, field))
        if payload.shipping is not None:
            doc.shipping = _q(payload.shipping)
        if payload.adjustment is not None:
            doc.adjustment = _q(payload.adjustment)
        if payload.lines is not None:
            lines, subtotal, discount_total, tax_total = self._build_lines(
                org_id, doc_type, payload.lines
            )
            self._validate_line_bins(org_id, doc_type, doc.warehouse_id, lines)
            doc.lines = lines
            further_total = _ZERO
            if doc_type in (
                DocumentType.INVOICE,
                DocumentType.CREDIT_NOTE,
            ) and self._org_fbr_enabled(org_id):
                party = self.db.get(Party, doc.party_id)
                tax_total, further_total = self._apply_fbr_tax(org_id, lines, party)
            self._apply_totals(doc, subtotal, discount_total, tax_total, further_total)
        else:
            self._validate_line_bins(org_id, doc_type, doc.warehouse_id, list(doc.lines))
            self._apply_totals(
                doc, doc.subtotal, doc.discount_total, doc.tax_total, doc.further_tax_total
            )
        self.activity.record(org_id, "updated", doc_type, doc.number, entity_id=doc.id)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def _source_moved_stock(self, doc: Document) -> bool:
        """True when the document this one came from already moved the goods, so
        finalizing must not move the same stock twice. Only applies when both
        move it the same way (challan -> invoice); a reversal such as
        invoice -> credit note has to move stock itself."""
        if doc.source_document_id is None:
            return False
        source = self.db.get(Document, doc.source_document_id)
        if source is None or not source.stock_posted:
            return False
        return source.stock_direction == doc.stock_direction

    def _validate_tracking(self, org_id: int, doc: Document, *, moves_stock: bool) -> None:
        if not moves_stock:
            return
        product_ids = {line.product_id for line in doc.lines if line.product_id is not None}
        products = {
            product.id: product
            for product in self.db.scalars(
                select(Product).where(Product.org_id == org_id, Product.id.in_(product_ids))
            )
        }
        for line in doc.lines:
            product = products.get(line.product_id)
            if product is None or not product.track_inventory:
                continue
            if product.tracking_mode == "lot":
                allocated = sum(
                    (allocation.quantity for allocation in line.lot_allocations), _ZERO
                )
                if allocated != line.quantity:
                    raise BadRequestError(
                        f"Allocate exactly {line.quantity} units across lots for {product.name}"
                    )
                if line.serials:
                    raise BadRequestError(f"{product.name} is tracked by lot, not serial number")
                if doc.stock_direction < 0:
                    for allocation in line.lot_allocations:
                        if (
                            allocation.lot.expiry_date
                            and allocation.lot.expiry_date < doc.issue_date
                        ):
                            raise BadRequestError(
                                f"Lot {allocation.lot.lot_number} for {product.name} is expired"
                            )
            elif product.tracking_mode == "serial":
                if line.quantity != line.quantity.to_integral_value():
                    raise BadRequestError(
                        f"Serial-tracked item {product.name} requires whole units"
                    )
                if len(line.serials) != int(line.quantity):
                    raise BadRequestError(
                        f"Enter exactly {int(line.quantity)} serial numbers for {product.name}"
                    )
                if line.lot_allocations:
                    raise BadRequestError(f"{product.name} is tracked by serial number, not lot")
                numbers = [serial.serial_number for serial in line.serials]
                if doc.stock_direction < 0:
                    self.tracking.validate_serials_available(
                        org_id,
                        product.id,
                        doc.warehouse_id,
                        line.bin_id,
                        numbers,
                    )
                else:
                    self.tracking.validate_serials_receivable(
                        org_id,
                        product.id,
                        numbers,
                        sales_return=doc.type == DocumentType.CREDIT_NOTE,
                    )
            elif line.lot_allocations or line.serials:
                raise BadRequestError(f"{product.name} does not use lot or serial tracking")

    def _apply_credit(self, org_id: int, doc: Document) -> None:
        """A credit note settles the invoice it was raised against, so the
        customer no longer owes for goods they returned."""
        if doc.type != DocumentType.CREDIT_NOTE or doc.source_document_id is None:
            return
        source = self.db.get(Document, doc.source_document_id)
        if source is None or source.org_id != org_id or source.status != DocumentStatus.SENT:
            return
        outstanding = source.total - source.amount_paid
        if doc.total > outstanding:
            raise BadRequestError(f"Credit exceeds the balance due on {source.number}")
        self.apply_settlement(source, doc.total)
        doc.settled_amount = doc.total

    def _reverse_credit(self, doc: Document) -> None:
        if doc.settled_amount <= _ZERO or doc.source_document_id is None:
            return
        source = self.db.get(Document, doc.source_document_id)
        if source is not None:
            self.apply_settlement(source, -doc.settled_amount)
        doc.settled_amount = _ZERO

    def _guard_fbr_credit_note(self, org_id: int, source: Document) -> None:
        if not source.fbr_invoice_number:
            raise BadRequestError("The original invoice was not filed with FBR")
        if not source.buyer_registered:
            raise BadRequestError(
                "FBR credit notes require a sales-tax-registered buyer (with STRN); "
                "this customer is unregistered"
            )
        existing = self.db.scalar(
            select(Document.id).where(
                Document.org_id == org_id,
                Document.type == DocumentType.CREDIT_NOTE,
                Document.source_document_id == source.id,
            )
        )
        if existing:
            raise BadRequestError("A credit note already exists for this invoice")
        if source.issue_date and date.today() > source.issue_date + timedelta(days=180):
            raise BadRequestError("Credit notes must be issued within 180 days of the invoice")

    def _guard_source_for_finalize(self, org_id: int, doc: Document) -> Document | None:
        if doc.source_document_id is None:
            return None
        source = self.db.scalar(
            select(Document).where(
                Document.id == doc.source_document_id,
                Document.org_id == org_id,
            )
        )
        if source is None:
            raise BadRequestError("Source document was not found")
        if doc.type not in CONVERSIONS.get(source.type, []):
            raise BadRequestError("Document is not a valid conversion of its source")
        valid_statuses = {DocumentStatus.SENT}
        if source.type in CLOSED_ON_CONVERT:
            valid_statuses.add(DocumentStatus.CLOSED)
        if source.status not in valid_statuses:
            raise BadRequestError(f"Source document {source.number} is no longer active")
        if doc.party_id != source.party_id:
            raise BadRequestError(f"Converted document must use the same party as {source.number}")
        self._guard_converted_lines(source, doc)
        return source

    @staticmethod
    def _line_quantities(doc: Document) -> dict[tuple, Decimal]:
        quantities: dict[tuple, Decimal] = {}
        for line in doc.lines:
            signature = (
                line.product_id,
                line.description,
                line.unit_price,
                line.discount_type,
                line.discount_value,
                line.tax_rate_id,
            )
            quantities[signature] = quantities.get(signature, _ZERO) + line.quantity
        return quantities

    def _guard_converted_lines(self, source: Document, target: Document) -> None:
        source_quantities = self._line_quantities(source)
        target_quantities = self._line_quantities(target)
        if target.type == DocumentType.CREDIT_NOTE:
            if any(
                signature not in source_quantities or quantity > source_quantities[signature]
                for signature, quantity in target_quantities.items()
            ):
                raise BadRequestError(
                    f"Credit note lines must match quantities and prices on {source.number}"
                )
            return
        if target_quantities != source_quantities:
            raise BadRequestError(
                f"Converted document lines must match source document {source.number}"
            )

    def _active_dependent(
        self, org_id: int, source_id: int, *, exclude_id: int | None = None
    ) -> Document | None:
        stmt = select(Document).where(
            Document.org_id == org_id,
            Document.source_document_id == source_id,
            Document.status != DocumentStatus.VOID,
        )
        if exclude_id is not None:
            stmt = stmt.where(Document.id != exclude_id)
        return self.db.scalar(stmt.order_by(Document.id).limit(1))

    def _guard_no_active_dependents(self, org_id: int, doc: Document) -> None:
        dependent = self._active_dependent(org_id, doc.id)
        if dependent is not None:
            raise BadRequestError(
                f"Cannot void {doc.number} while {dependent.number} is active; "
                "void or delete the dependent document first"
            )

    def _guard_no_active_conversion(self, org_id: int, source: Document) -> None:
        dependent = self._active_dependent(org_id, source.id)
        if dependent is not None:
            raise BadRequestError(f"{source.number} already has active document {dependent.number}")

    def _reopen_order_source(self, org_id: int, doc: Document) -> None:
        if doc.source_document_id is None:
            return
        source = self.db.scalar(
            select(Document).where(
                Document.id == doc.source_document_id,
                Document.org_id == org_id,
            )
        )
        if (
            source is not None
            and source.type in CLOSED_ON_CONVERT
            and source.status == DocumentStatus.CLOSED
            and self._active_dependent(org_id, source.id, exclude_id=doc.id) is None
        ):
            source.status = DocumentStatus.SENT

    def convert(
        self, org_id: int, doc_id: int, source_type: DocumentType, target_type: DocumentType
    ) -> Document:
        source = self._get_for_update(org_id, doc_id)
        if source.type != source_type:
            raise NotFoundError("Document not found")
        if target_type not in CONVERSIONS.get(source_type, []):
            raise BadRequestError("That document cannot be converted to this type")
        if source.status != DocumentStatus.SENT:
            raise BadRequestError("Only a finalized document can be converted")
        self._guard_no_active_conversion(org_id, source)
        if target_type == DocumentType.CREDIT_NOTE and self._org_fbr_enabled(org_id):
            self._guard_fbr_credit_note(org_id, source)

        target_cls = DOCUMENT_CLASSES[target_type]
        preserve_bins = (
            source.stock_posted and source.stock_direction == target_cls.stock_direction
        )
        line_inputs = [
            DocumentLineInput(
                product_id=line.product_id,
                bin_id=line.bin_id if preserve_bins else None,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                discount_type=line.discount_type,
                discount_value=line.discount_value,
                tax_rate_id=line.tax_rate_id,
                lot_allocations=(
                    [
                        {
                            "lot_id": allocation.lot_id,
                            "quantity": allocation.quantity,
                        }
                        for allocation in line.lot_allocations
                    ]
                    if preserve_bins
                    else []
                ),
                serial_numbers=(
                    [serial.serial_number for serial in line.serials] if preserve_bins else []
                ),
            )
            for line in source.lines
        ]
        lines, subtotal, discount_total, tax_total = self._build_lines(
            org_id, target_type, line_inputs
        )
        prefix, start, restart = numbering_format(
            self.db, org_id, str(target_type), DEFAULT_PREFIXES[target_type]
        )
        target_issue_date = date.today()
        target_party = self.db.get(Party, source.party_id)
        target_due_date = (
            self._default_due(target_issue_date, target_party)
            if target_type in FINANCIAL_TYPES and target_party is not None
            else None
        )

        target = DOCUMENT_CLASSES[target_type](
            org_id=org_id,
            status=DocumentStatus.DRAFT,
            party_id=source.party_id,
            warehouse_id=source.warehouse_id,
            issue_date=target_issue_date,
            due_date=target_due_date,
            expected_shipment_date=None,
            reference=source.reference,
            notes=source.notes,
            terms=source.terms,
            shipping=source.shipping,
            adjustment=source.adjustment,
            billing_address=source.billing_address,
            shipping_address=source.shipping_address,
            source_document_id=source.id,
            fbr_sale_origin=(source.fbr_sale_origin if target_type in FBR_TYPES else None),
            fbr_sale_destination=(
                source.fbr_sale_destination if target_type in FBR_TYPES else None
            ),
            fbr_scenario_id=(source.fbr_scenario_id if target_type in FBR_TYPES else None),
            fbr_reason=("Return of Goods" if target_type == DocumentType.CREDIT_NOTE else None),
        )
        target.lines = lines
        further_total = _ZERO
        if target_type in (
            DocumentType.INVOICE,
            DocumentType.CREDIT_NOTE,
        ) and self._org_fbr_enabled(org_id):
            party = self.db.get(Party, source.party_id)
            tax_total, further_total = self._apply_fbr_tax(org_id, lines, party)
        self._apply_totals(target, subtotal, discount_total, tax_total, further_total)
        assign_number(
            self.db,
            target,
            Document.number,
            prefix,
            start,
            restart,
            date.today().year,
            Document.org_id == org_id,
            Document.type == target_type,
        )

        self.activity.record(
            org_id,
            "converted",
            source.type,
            source.number,
            entity_id=source.id,
            context={"to": target_type, "number": target.number},
        )
        self.db.commit()
        self.db.refresh(target)
        return target

    def finalize(
        self, org_id: int, doc_id: int, expected_type: DocumentType | None = None
    ) -> Document:
        doc = self._get_for_update(org_id, doc_id)
        if expected_type and doc.type != expected_type:
            raise NotFoundError("Document not found")
        if doc.status != DocumentStatus.DRAFT:
            raise BadRequestError("Only draft documents can be finalized")
        if not doc.lines:
            raise BadRequestError("Cannot finalize a document with no lines")
        source = self._guard_source_for_finalize(org_id, doc)
        moves_stock = doc.stock_direction != 0 and not self._source_moved_stock(doc)
        if moves_stock and any(line.product_id for line in doc.lines):
            if doc.warehouse_id is None:
                doc.warehouse_id = self._default_location(org_id)
            if doc.warehouse_id is None:
                raise BadRequestError("No warehouse available to move stock")
        if doc.warehouse_id is not None:
            self._validate_warehouse(org_id, doc.warehouse_id)
        self._validate_tracking(org_id, doc, moves_stock=moves_stock)
        if moves_stock and doc.stock_direction < 0:
            self._preflight_outbound_stock(org_id, doc)
        if doc.type in (DocumentType.INVOICE, DocumentType.CREDIT_NOTE):
            from app.modules.fbr.service import FbrService

            try:
                result = FbrService(self.db).submit_invoice(org_id, doc)
            except AppError as exc:
                failed_org_id = doc.org_id
                failed_document_id = doc.id
                self.db.rollback()
                self.db.add(
                    FbrSubmissionAttempt(
                        org_id=failed_org_id,
                        document_id=failed_document_id,
                        status="failed",
                        error=exc.message,
                    )
                )
                self.db.commit()
                raise
            if result:
                doc.fbr_invoice_number = result["invoice_number"]
                doc.fbr_response = result["response"]
                doc.fbr_submitted_at = datetime.now(UTC)
                self.db.add(
                    FbrSubmissionAttempt(
                        org_id=doc.org_id,
                        document_id=doc.id,
                        status="submitted",
                    )
                )
        self._apply_credit(org_id, doc)
        if moves_stock:
            self._post_stock(org_id, doc, reverse=False)
            doc.stock_posted = True
        self.ledger.post_document(self.db, doc)
        doc.status = DocumentStatus.SENT
        if source is not None and source.type in CLOSED_ON_CONVERT:
            source.status = DocumentStatus.CLOSED
        self.activity.record(org_id, "finalized", doc.type, doc.number, entity_id=doc.id)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def void(self, org_id: int, doc_id: int, expected_type: DocumentType | None = None) -> Document:
        doc = self._get_for_update(org_id, doc_id)
        if expected_type and doc.type != expected_type:
            raise NotFoundError("Document not found")
        if doc.status in (DocumentStatus.DRAFT, DocumentStatus.VOID):
            raise BadRequestError("Only a finalized document can be voided")
        self._guard_no_active_dependents(org_id, doc)
        if doc.type == DocumentType.INVOICE and doc.fbr_invoice_number:
            raise BadRequestError(
                "A filed FBR invoice cannot be voided; issue a credit note instead"
            )
        if doc.amount_paid > _ZERO:
            raise BadRequestError("Cannot void a document with recorded payments")
        if doc.stock_posted:
            self._post_stock(org_id, doc, reverse=True)
            doc.stock_posted = False
        self._reverse_credit(doc)
        self.ledger.reverse_document(self.db, doc)
        doc.status = DocumentStatus.VOID
        self._reopen_order_source(org_id, doc)
        self.activity.record(org_id, "voided", doc.type, doc.number, entity_id=doc.id)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def delete(self, org_id: int, doc_id: int, expected_type: DocumentType | None = None) -> None:
        doc = self.get(org_id, doc_id)
        if expected_type and doc.type != expected_type:
            raise NotFoundError("Document not found")
        if doc.status != DocumentStatus.DRAFT:
            raise BadRequestError("Only draft documents can be deleted")
        self.activity.record(org_id, "deleted", doc.type, doc.number, entity_id=doc.id)
        self.db.delete(doc)
        self._reopen_order_source(org_id, doc)
        self.db.commit()

    def _preflight_outbound_stock(self, org_id: int, doc: Document) -> None:
        if doc.warehouse_id is None:
            return
        product_ids = {line.product_id for line in doc.lines if line.product_id is not None}
        products = {
            product.id: product
            for product in self.db.scalars(
                select(Product).where(
                    Product.org_id == org_id,
                    Product.id.in_(product_ids),
                    Product.track_inventory.is_(True),
                )
            )
        }
        required: dict[tuple[int, int | None], Decimal] = {}
        for line in doc.lines:
            product = products.get(line.product_id)
            if product is None:
                continue
            if product.tracking_mode == "lot":
                for allocation in line.lot_allocations:
                    available = self.inventory.on_hand_in_lot(
                        org_id,
                        product.id,
                        doc.warehouse_id,
                        line.bin_id,
                        allocation.lot_id,
                    )
                    if available < allocation.quantity:
                        raise BadRequestError(
                            f"Not enough stock in lot {allocation.lot.lot_number} "
                            f"for {product.name}"
                        )
            elif product.tracking_mode == "serial":
                continue
            else:
                key = (line.product_id, line.bin_id)
                required[key] = required.get(key, _ZERO) + line.quantity
        for (product_id, bin_id), quantity in required.items():
            available = self.inventory.on_hand_in_bin(org_id, product_id, doc.warehouse_id, bin_id)
            if available < quantity:
                raise BadRequestError(
                    f"Not enough stock for {products[product_id].name} at the selected warehouse"
                )

    def _post_stock(self, org_id: int, doc: Document, reverse: bool) -> None:
        if doc.stock_direction == 0 or doc.warehouse_id is None:
            return
        trackable = sorted(
            (line for line in doc.lines if line.product_id is not None),
            key=lambda line: line.product_id,
        )
        if not trackable:
            return
        products = {
            p.id: p
            for p in self.db.scalars(
                select(Product).where(
                    Product.org_id == org_id,
                    Product.id.in_([line.product_id for line in trackable]),
                )
            )
        }
        direction = -doc.stock_direction if reverse else doc.stock_direction
        for line in trackable:
            product = products.get(line.product_id)
            if product is None or not product.track_inventory:
                continue
            unit_cost = line.unit_price if doc.stock_direction > 0 else product.purchase_price
            if product.tracking_mode == "lot":
                for allocation in line.lot_allocations:
                    self.inventory.post_document_movement(
                        org_id=org_id,
                        product_id=line.product_id,
                        location_id=doc.warehouse_id,
                        qty_delta=direction * allocation.quantity,
                        type_=doc.movement_type,
                        reference_type=doc.type,
                        reference_id=doc.id,
                        unit_cost=unit_cost,
                        bin_id=line.bin_id,
                        lot_id=allocation.lot_id,
                    )
            else:
                movement = self.inventory.post_document_movement(
                    org_id=org_id,
                    product_id=line.product_id,
                    location_id=doc.warehouse_id,
                    qty_delta=direction * line.quantity,
                    type_=doc.movement_type,
                    reference_type=doc.type,
                    reference_id=doc.id,
                    unit_cost=unit_cost,
                    bin_id=line.bin_id,
                )
                if product.tracking_mode == "serial":
                    self.tracking.apply_serial_movement(
                        org_id,
                        product.id,
                        doc.warehouse_id,
                        line.bin_id,
                        [serial.serial_number for serial in line.serials],
                        movement,
                        direction=direction,
                        movement_type=doc.movement_type,
                        reverse=reverse,
                    )
