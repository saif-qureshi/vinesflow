from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core import ledger as _ledger
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.pagination import decode_cursor, encode_cursor, paginate_cursor
from app.modules.activities.service import ActivityService
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import Document, DocumentLine
from app.modules.inventory.models import Reason, StockLevel, StockMovement
from app.modules.inventory.schemas import (
    InventoryItemRead,
    InventoryListQuery,
    ItemStockRead,
    OpeningStockInput,
    OpeningStockLocationRead,
    OpeningStockRead,
    ReasonCreate,
    StockAdjustInput,
    StockByLocation,
    StockTransferInput,
)
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
        self.ledger = _ledger.ledger_poster

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
        if (
            self.db.scalar(
                select(Location.id).where(
                    Location.id == location_id,
                    Location.org_id == org_id,
                    Location.is_active.is_(True),
                )
            )
            is None
        ):
            raise NotFoundError("Location not found")
        return product

    def _validate_location(self, org_id: int, location_id: int) -> None:
        if (
            self.db.scalar(
                select(Location.id).where(
                    Location.id == location_id,
                    Location.org_id == org_id,
                    Location.is_active.is_(True),
                )
            )
            is None
        ):
            raise NotFoundError("Location not found")

    def _level(self, org_id: int, product_id: int, location_id: int) -> StockLevel:
        level = self.db.scalar(
            select(StockLevel)
            .where(
                StockLevel.org_id == org_id,
                StockLevel.product_id == product_id,
                StockLevel.location_id == location_id,
            )
            .with_for_update()
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

    def _apply(
        self,
        org_id,
        product_id,
        location_id,
        qty_delta,
        type_,
        note,
        reason=None,
        unit_cost=None,
        value_delta=None,
    ) -> StockMovement:
        movement = StockMovement(
            org_id=org_id,
            product_id=product_id,
            location_id=location_id,
            qty_delta=qty_delta,
            type=type_,
            note=note,
            reason=reason,
            unit_cost=unit_cost,
            value_delta=value_delta,
        )
        self.db.add(movement)
        level = self._level(org_id, product_id, location_id)
        level.quantity = level.quantity + qty_delta
        return movement

    def post_document_movement(
        self,
        org_id,
        product_id,
        location_id,
        qty_delta,
        type_,
        reference_type,
        reference_id,
        unit_cost=None,
    ) -> None:
        level = self._level(org_id, product_id, location_id)
        new_quantity = level.quantity + qty_delta
        if new_quantity < _ZERO:
            raise BadRequestError("Not enough stock at the selected location")
        self.db.add(
            StockMovement(
                org_id=org_id,
                product_id=product_id,
                location_id=location_id,
                qty_delta=qty_delta,
                type=type_,
                reference_type=reference_type,
                reference_id=reference_id,
                unit_cost=unit_cost,
            )
        )
        level.quantity = new_quantity

    def _record(self, org_id, action, product, delta, location_id) -> None:
        self.activity.record(
            org_id,
            action,
            "stock",
            product.name,
            entity_id=product.id,
            context={"qty": str(delta), "location_id": location_id},
        )

    def adjust(self, org_id: int, payload: StockAdjustInput) -> None:
        product = self._validate(org_id, payload.product_id, payload.location_id)
        if payload.mode == "value":
            value = payload.value_delta or _ZERO
            if value == _ZERO:
                raise BadRequestError("Enter a value adjustment")
            movement = self._apply(
                org_id,
                payload.product_id,
                payload.location_id,
                _ZERO,
                "revaluation",
                payload.note,
                reason=payload.reason,
                value_delta=value,
            )
        else:
            if payload.qty_delta == _ZERO:
                raise BadRequestError("Enter a quantity to adjust")
            unit_cost = (
                payload.unit_cost if payload.unit_cost is not None else product.purchase_price
            )
            movement = self._apply(
                org_id,
                payload.product_id,
                payload.location_id,
                payload.qty_delta,
                "adjustment",
                payload.note,
                reason=payload.reason,
                unit_cost=unit_cost,
            )
            value = (unit_cost or _ZERO) * payload.qty_delta
        self.db.flush()
        self._record(org_id, "adjusted", product, payload.qty_delta, payload.location_id)
        self.ledger.post_inventory_adjustment(
            self.db,
            org_id=org_id,
            value=value,
            account_id=payload.account_id,
            posting_date=payload.date or date.today(),
            source_id=movement.id,
        )
        self.db.commit()

    def transfer(self, org_id: int, payload: StockTransferInput) -> None:
        if payload.from_location_id == payload.to_location_id:
            raise BadRequestError("Source and destination locations must differ")
        product = self._validate(org_id, payload.product_id, payload.from_location_id)
        self._validate_location(org_id, payload.to_location_id)
        available = self._on_hand_at(org_id, payload.product_id, payload.from_location_id)
        if available < payload.quantity:
            raise BadRequestError("Not enough stock at the source location")
        self._apply(
            org_id,
            payload.product_id,
            payload.from_location_id,
            -payload.quantity,
            "transfer",
            payload.note,
        )
        self._apply(
            org_id,
            payload.product_id,
            payload.to_location_id,
            payload.quantity,
            "transfer",
            payload.note,
        )
        self._record(org_id, "transferred", product, payload.quantity, payload.to_location_id)
        self.db.commit()

    def _opening_state(
        self, org_id: int, product_id: int
    ) -> dict[int, tuple[Decimal, Decimal, Decimal | None]]:
        """Return quantity, recognized value and latest rate per location."""
        movements = self.db.scalars(
            select(StockMovement)
            .where(
                StockMovement.org_id == org_id,
                StockMovement.product_id == product_id,
                StockMovement.type == "opening",
            )
            .order_by(StockMovement.id)
        )
        state: dict[int, tuple[Decimal, Decimal, Decimal | None]] = {}
        for movement in movements:
            quantity, value, unit_cost = state.get(movement.location_id, (_ZERO, _ZERO, None))
            quantity += movement.qty_delta
            if movement.value_delta is not None:
                value += movement.value_delta
            elif movement.unit_cost is not None:
                value += movement.qty_delta * movement.unit_cost
            unit_cost = movement.unit_cost
            state[movement.location_id] = (quantity, value, unit_cost)
        return state

    def _opening_editable(self, org_id: int, product_id: int) -> bool:
        return (
            self.db.scalar(
                select(StockMovement.id)
                .where(
                    StockMovement.org_id == org_id,
                    StockMovement.product_id == product_id,
                    StockMovement.type != "opening",
                )
                .limit(1)
            )
            is None
        )

    def opening_stock(self, org_id: int, product_id: int) -> OpeningStockRead:
        product = self.db.scalar(
            select(Product).where(Product.id == product_id, Product.org_id == org_id)
        )
        if product is None:
            raise NotFoundError("Item not found")
        state = self._opening_state(org_id, product_id)
        return OpeningStockRead(
            product_id=product_id,
            editable=self._opening_editable(org_id, product_id),
            entries=[
                OpeningStockLocationRead(
                    location_id=location_id,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    value=value,
                )
                for location_id, (quantity, value, unit_cost) in sorted(state.items())
                if quantity != _ZERO or value != _ZERO
            ],
        )

    def set_opening_stock(self, org_id: int, payload: OpeningStockInput) -> OpeningStockRead:
        product = self.db.scalar(
            select(Product)
            .where(Product.id == payload.product_id, Product.org_id == org_id)
            .with_for_update()
        )
        if product is None:
            raise NotFoundError("Item not found")
        if product.type == "variable":
            raise BadRequestError("Set opening stock on each variant, not the variant group")
        if product.nature != "good" or not product.track_inventory:
            raise BadRequestError("Opening stock is only available for inventory-tracked goods")
        if not self._opening_editable(org_id, product.id):
            raise ConflictError(
                "Opening stock is locked because this item already has inventory transactions; "
                "use Adjust Stock instead"
            )

        requested: dict[int, tuple[Decimal, Decimal | None]] = {}
        for entry in payload.entries:
            if entry.location_id in requested:
                raise BadRequestError("Each warehouse can appear only once")
            self._validate_location(org_id, entry.location_id)
            requested[entry.location_id] = (entry.quantity, entry.unit_cost)

        current = self._opening_state(org_id, product.id)
        movements: list[StockMovement] = []
        value_delta = _ZERO
        for location_id in sorted(requested):
            old_quantity, old_value, _ = current.get(location_id, (_ZERO, _ZERO, None))
            new_quantity, new_cost = requested[location_id]
            new_value = new_quantity * new_cost if new_cost is not None else _ZERO
            quantity_delta = new_quantity - old_quantity
            location_value_delta = new_value - old_value
            if quantity_delta == _ZERO and location_value_delta == _ZERO:
                continue
            movement = self._apply(
                org_id,
                product.id,
                location_id,
                quantity_delta,
                "opening",
                "Opening stock",
                unit_cost=new_cost,
                value_delta=(
                    location_value_delta if new_cost is not None or old_value != _ZERO else None
                ),
            )
            movements.append(movement)
            value_delta += location_value_delta

        if movements:
            self.db.flush()
            source_id = movements[0].id
            for movement in movements:
                movement.reference_type = "stock_opening"
                movement.reference_id = source_id
            self.activity.record(
                org_id,
                "set opening stock",
                "product",
                product.name,
                entity_id=product.id,
                context={"value_delta": str(value_delta)},
            )
            self.ledger.post_opening_stock(
                self.db,
                org_id=org_id,
                value=value_delta,
                posting_date=payload.date or date.today(),
                source_id=source_id,
                product_name=product.name,
            )
        self.db.commit()
        return self.opening_stock(org_id, product.id)

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
            by_location=[
                StockByLocation(location_id=k, quantity=v) for k, v in by_location.items()
            ],
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

    def movements(
        self, org_id: int, product_id: int, query
    ) -> tuple[list[StockMovement], str | None, bool]:
        stmt = select(StockMovement).where(
            StockMovement.org_id == org_id, StockMovement.product_id == product_id
        )
        return paginate_cursor(self.db, stmt, StockMovement.id, query)

    def list(
        self, org_id: int, query: InventoryListQuery
    ) -> tuple[list[InventoryItemRead], str | None, bool]:
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
