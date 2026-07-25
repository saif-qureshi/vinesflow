from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.pagination import decode_cursor, encode_cursor, paginate_cursor
from app.modules.activities.service import ActivityService
from app.modules.inventory.models import Reason, StockLevel, StockMovement
from app.modules.inventory.schemas import (
    InventoryItemRead,
    InventoryListQuery,
    ItemStockRead,
    OpeningStockInput,
    ReasonCreate,
    StockAdjustInput,
    StockByLocation,
    StockTransferInput,
)
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import Document, DocumentLine
from app.modules.locations.models import Location
from app.modules.products.models import Product

_ZERO = Decimal("0")

DEFAULT_REASONS = [
    "Stock on fire",
    "Stolen goods",
    "Damaged goods",
    "Stock Written off",
    "Stocktaking results",
    "Inventory Revaluation",
]


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.activity = ActivityService(db)

    def seed_reasons(self, org_id: int) -> None:
        existing = set(self.db.scalars(select(Reason.name).where(Reason.org_id == org_id)))
        self.db.add_all(
            Reason(org_id=org_id, name=name, is_system=True)
            for name in DEFAULT_REASONS
            if name not in existing
        )
        self.db.flush()

    def list_reasons(self, org_id: int) -> list[Reason]:
        return list(
            self.db.scalars(select(Reason).where(Reason.org_id == org_id).order_by(Reason.name))
        )

    def create_reason(self, org_id: int, payload: ReasonCreate) -> Reason:
        if self.db.scalar(
            select(Reason.id).where(Reason.org_id == org_id, Reason.name == payload.name)
        ):
            raise ConflictError("A reason with that name already exists")
        reason = Reason(org_id=org_id, name=payload.name, is_system=False)
        self.db.add(reason)
        self.db.commit()
        self.db.refresh(reason)
        return reason

    def delete_reason(self, org_id: int, reason_id: int) -> None:
        reason = self.db.scalar(
            select(Reason).where(Reason.id == reason_id, Reason.org_id == org_id)
        )
        if reason is None:
            raise NotFoundError("Reason not found")
        if reason.is_system:
            raise ConflictError("Default reasons cannot be deleted")
        self.db.delete(reason)
        self.db.commit()

    def _validate(self, org_id: int, product_id: int, location_id: int) -> Product:
        product = self.db.scalar(
            select(Product).where(Product.id == product_id, Product.org_id == org_id)
        )
        if product is None:
            raise NotFoundError("Item not found")
        if product.type == "variable":
            raise BadRequestError("Stock is tracked on the individual variants, not the group")
        if self.db.scalar(
            select(Location.id).where(Location.id == location_id, Location.org_id == org_id)
        ) is None:
            raise NotFoundError("Location not found")
        return product

    def _validate_location(self, org_id: int, location_id: int) -> None:
        if self.db.scalar(
            select(Location.id).where(Location.id == location_id, Location.org_id == org_id)
        ) is None:
            raise NotFoundError("Location not found")

    def _level(self, org_id: int, product_id: int, location_id: int) -> StockLevel:
        level = self.db.scalar(
            select(StockLevel).where(
                StockLevel.org_id == org_id,
                StockLevel.product_id == product_id,
                StockLevel.location_id == location_id,
            )
        )
        if level is None:
            level = StockLevel(
                org_id=org_id, product_id=product_id, location_id=location_id, quantity=_ZERO
            )
            self.db.add(level)
            self.db.flush()
        return level

    def _on_hand_at(self, org_id: int, product_id: int, location_id: int) -> Decimal:
        qty = self.db.scalar(
            select(StockLevel.quantity).where(
                StockLevel.org_id == org_id,
                StockLevel.product_id == product_id,
                StockLevel.location_id == location_id,
            )
        )
        return qty if qty is not None else _ZERO

    def _apply(self, org_id, product_id, location_id, qty_delta, type_, note, reason=None) -> None:
        self.db.add(
            StockMovement(
                org_id=org_id, product_id=product_id, location_id=location_id,
                qty_delta=qty_delta, type=type_, note=note, reason=reason,
            )
        )
        level = self._level(org_id, product_id, location_id)
        level.quantity = level.quantity + qty_delta

    def post_document_movement(
        self, org_id, product_id, location_id, qty_delta, type_, reference_type, reference_id, unit_cost=None
    ) -> None:
        self.db.add(
            StockMovement(
                org_id=org_id, product_id=product_id, location_id=location_id,
                qty_delta=qty_delta, type=type_, reference_type=reference_type,
                reference_id=reference_id, unit_cost=unit_cost,
            )
        )
        level = self._level(org_id, product_id, location_id)
        level.quantity = level.quantity + qty_delta

    def _record(self, org_id, action, product, delta, location_id) -> None:
        self.activity.record(
            org_id, action, "stock", product.name, entity_id=product.id,
            context={"qty": str(delta), "location_id": location_id},
        )

    def adjust(self, org_id: int, payload: StockAdjustInput) -> None:
        product = self._validate(org_id, payload.product_id, payload.location_id)
        self._apply(
            org_id, payload.product_id, payload.location_id,
            payload.qty_delta, "adjustment", payload.note, reason=payload.reason,
        )
        self._record(org_id, "adjusted", product, payload.qty_delta, payload.location_id)
        self.db.commit()

    def set_opening(self, org_id: int, payload: OpeningStockInput) -> None:
        product = self._validate(org_id, payload.product_id, payload.location_id)
        self._apply(
            org_id, payload.product_id, payload.location_id,
            payload.quantity, "opening", payload.note,
        )
        self._record(org_id, "set opening", product, payload.quantity, payload.location_id)
        self.db.commit()

    def transfer(self, org_id: int, payload: StockTransferInput) -> None:
        if payload.from_location_id == payload.to_location_id:
            raise BadRequestError("Source and destination locations must differ")
        product = self._validate(org_id, payload.product_id, payload.from_location_id)
        self._validate_location(org_id, payload.to_location_id)
        available = self._on_hand_at(org_id, payload.product_id, payload.from_location_id)
        if available < payload.quantity:
            raise BadRequestError("Not enough stock at the source location")
        self._apply(org_id, payload.product_id, payload.from_location_id, -payload.quantity, "transfer", payload.note)
        self._apply(org_id, payload.product_id, payload.to_location_id, payload.quantity, "transfer", payload.note)
        self._record(org_id, "transferred", product, payload.quantity, payload.to_location_id)
        self.db.commit()

    def item_stock(self, org_id: int, product_id: int) -> ItemStockRead:
        rows = self.db.execute(
            select(StockLevel.location_id, StockLevel.quantity).where(
                StockLevel.org_id == org_id, StockLevel.product_id == product_id
            )
        ).all()
        by_location: dict[int, Decimal] = {}
        total = _ZERO
        for location_id, quantity in rows:
            total += quantity
            by_location[location_id] = by_location.get(location_id, _ZERO) + quantity
        opening = self.db.scalar(
            select(func.coalesce(func.sum(StockMovement.qty_delta), 0)).where(
                StockMovement.org_id == org_id,
                StockMovement.product_id == product_id,
                StockMovement.type == "opening",
            )
        )
        committed = self._open_order_qty(org_id, product_id, DocumentType.SALES_ORDER)
        incoming = self._open_order_qty(org_id, product_id, DocumentType.PURCHASE_ORDER)
        return ItemStockRead(
            on_hand=total,
            opening_stock=opening or _ZERO,
            committed=committed,
            available=total - committed,
            to_be_shipped=committed,
            to_be_received=incoming,
            by_location=[StockByLocation(location_id=k, quantity=v) for k, v in by_location.items()],
        )

    def _open_order_qty(self, org_id: int, product_id: int, doc_type: DocumentType) -> Decimal:
        """Quantity on open (finalized, not yet converted) orders of a type:
        sales orders commit stock, purchase orders are incoming."""
        qty = self.db.scalar(
            select(func.coalesce(func.sum(DocumentLine.quantity), 0))
            .select_from(DocumentLine)
            .join(Document, Document.id == DocumentLine.document_id)
            .where(
                Document.org_id == org_id,
                Document.type == doc_type,
                Document.status == DocumentStatus.SENT,
                DocumentLine.product_id == product_id,
            )
        )
        return qty if qty is not None else _ZERO

    def on_hand(self, org_id: int, product_id: int, location_id: int) -> Decimal:
        self._validate_location(org_id, location_id)
        return self._on_hand_at(org_id, product_id, location_id)

    def movements(self, org_id: int, product_id: int, query) -> tuple[list[StockMovement], str | None, bool]:
        stmt = select(StockMovement).where(
            StockMovement.org_id == org_id, StockMovement.product_id == product_id
        )
        return paginate_cursor(self.db, stmt, StockMovement.id, query)

    def list(self, org_id: int, query: InventoryListQuery) -> tuple[list[InventoryItemRead], str | None, bool]:
        levels = select(
            StockLevel.product_id,
            func.coalesce(func.sum(StockLevel.quantity), 0).label("qty"),
        ).where(StockLevel.org_id == org_id)
        if query.location_id is not None:
            levels = levels.where(StockLevel.location_id == query.location_id)
        levels = levels.group_by(StockLevel.product_id).subquery()

        on_hand = func.coalesce(levels.c.qty, 0)
        stmt = (
            select(Product, on_hand.label("on_hand"))
            .outerjoin(levels, levels.c.product_id == Product.id)
            .options(joinedload(Product.uom))
            .where(
                Product.org_id == org_id,
                Product.type == "single",
                Product.track_inventory.is_(True),
            )
        )
        if query.search:
            like = f"%{query.search.strip()}%"
            stmt = stmt.where(or_(Product.name.ilike(like), Product.sku.ilike(like)))
        if query.low_stock:
            stmt = stmt.where(Product.reorder_point.isnot(None), on_hand < Product.reorder_point)
        if query.cursor:
            last_id = decode_cursor(query.cursor)
            if last_id is not None:
                stmt = stmt.where(Product.id < last_id)

        rows = self.db.execute(stmt.order_by(Product.id.desc()).limit(query.limit + 1)).all()
        has_more = len(rows) > query.limit
        rows = rows[: query.limit]
        next_cursor = encode_cursor(rows[-1][0].id) if has_more and rows else None

        items = []
        for product, qty in rows:
            quantity = Decimal(qty) if qty is not None else _ZERO
            is_low = product.reorder_point is not None and quantity < product.reorder_point
            items.append(
                InventoryItemRead(
                    id=product.id,
                    name=product.name,
                    sku=product.sku,
                    is_variant=product.parent_id is not None,
                    uom_symbol=product.uom.symbol if product.uom else None,
                    reorder_point=product.reorder_point,
                    on_hand=quantity,
                    is_low=is_low,
                )
            )
        return items, next_cursor, has_more
