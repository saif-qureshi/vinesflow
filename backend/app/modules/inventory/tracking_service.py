from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.inventory.models import (
    SerialUnit,
    StockLevel,
    StockLot,
    StockMovement,
    StockMovementSerial,
)
from app.modules.inventory.schemas import LotStockRead, StockLotCreate
from app.modules.products.models import Product


class TrackingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def normalize_lot_number(value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise BadRequestError("Lot number is required")
        return normalized

    @staticmethod
    def normalize_serials(values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values if value.strip()]
        if len(normalized) != len(set(normalized)):
            raise BadRequestError("Serial numbers must be unique within a line")
        return normalized

    def _product(self, org_id: int, product_id: int) -> Product:
        product = self.db.scalar(
            select(Product).where(Product.id == product_id, Product.org_id == org_id)
        )
        if product is None:
            raise NotFoundError("Item not found")
        return product

    def get_lot(self, org_id: int, lot_id: int, product_id: int | None = None) -> StockLot:
        stmt = select(StockLot).where(StockLot.id == lot_id, StockLot.org_id == org_id)
        if product_id is not None:
            stmt = stmt.where(StockLot.product_id == product_id)
        lot = self.db.scalar(stmt)
        if lot is None:
            raise NotFoundError("Lot not found for this item")
        return lot

    def create_lot(self, org_id: int, payload: StockLotCreate) -> StockLot:
        product = self._product(org_id, payload.product_id)
        if product.tracking_mode != "lot":
            raise BadRequestError("This item is not tracked by lot")
        number = self.normalize_lot_number(payload.lot_number)
        existing = self.db.scalar(
            select(StockLot.id).where(
                StockLot.org_id == org_id,
                StockLot.product_id == payload.product_id,
                StockLot.lot_number == number,
            )
        )
        if existing is not None:
            raise ConflictError("This lot number already exists for the item")
        if (
            payload.manufactured_date
            and payload.expiry_date
            and payload.expiry_date < payload.manufactured_date
        ):
            raise BadRequestError("Expiry date cannot be before the manufacturing date")
        lot = StockLot(
            org_id=org_id,
            product_id=payload.product_id,
            lot_number=number,
            manufactured_date=payload.manufactured_date,
            expiry_date=payload.expiry_date,
            note=payload.note,
            is_active=True,
        )
        self.db.add(lot)
        self.db.flush()
        return lot

    def save_lot(self, org_id: int, payload: StockLotCreate) -> StockLot:
        lot = self.create_lot(org_id, payload)
        self.db.commit()
        self.db.refresh(lot)
        return lot

    def resolve_lot(
        self,
        org_id: int,
        product_id: int,
        *,
        lot_id: int | None,
        lot_number: str | None,
        manufactured_date=None,
        expiry_date=None,
        allow_create: bool,
    ) -> StockLot:
        if lot_id is not None:
            return self.get_lot(org_id, lot_id, product_id)
        if not lot_number:
            raise BadRequestError("Select an existing lot or enter a new lot number")
        number = self.normalize_lot_number(lot_number)
        lot = self.db.scalar(
            select(StockLot).where(
                StockLot.org_id == org_id,
                StockLot.product_id == product_id,
                StockLot.lot_number == number,
            )
        )
        if lot is not None:
            return lot
        if not allow_create:
            raise NotFoundError("Lot not found for this item")
        return self.create_lot(
            org_id,
            StockLotCreate(
                product_id=product_id,
                lot_number=number,
                manufactured_date=manufactured_date,
                expiry_date=expiry_date,
            ),
        )

    def list_lots(
        self,
        org_id: int,
        product_id: int,
        *,
        location_id: int | None = None,
        bin_id: int | None = None,
        unbinned: bool = False,
    ) -> list[LotStockRead]:
        self._product(org_id, product_id)
        levels = (
            select(
                StockLevel.lot_id,
                func.coalesce(func.sum(StockLevel.quantity), 0).label("quantity"),
            )
            .where(
                StockLevel.org_id == org_id,
                StockLevel.product_id == product_id,
                StockLevel.lot_id.is_not(None),
            )
            .group_by(StockLevel.lot_id)
        )
        if location_id is not None:
            levels = levels.where(StockLevel.location_id == location_id)
        if bin_id is not None:
            levels = levels.where(StockLevel.bin_id == bin_id)
        elif unbinned:
            levels = levels.where(StockLevel.bin_id.is_(None))
        level_rows = {lot_id: Decimal(quantity) for lot_id, quantity in self.db.execute(levels)}
        lots = self.db.scalars(
            select(StockLot)
            .where(StockLot.org_id == org_id, StockLot.product_id == product_id)
            .order_by(StockLot.expiry_date.asc().nulls_last(), StockLot.lot_number)
        )
        return [
            LotStockRead.model_validate(lot).model_copy(
                update={"quantity": level_rows.get(lot.id, Decimal("0"))}
            )
            for lot in lots
        ]

    def list_serials(
        self,
        org_id: int,
        product_id: int,
        *,
        location_id: int | None = None,
        bin_id: int | None = None,
        unbinned: bool = False,
        status: str | None = None,
        search: str | None = None,
    ) -> list[SerialUnit]:
        self._product(org_id, product_id)
        stmt = select(SerialUnit).where(
            SerialUnit.org_id == org_id, SerialUnit.product_id == product_id
        )
        if location_id is not None:
            stmt = stmt.where(SerialUnit.location_id == location_id)
        if bin_id is not None:
            stmt = stmt.where(SerialUnit.bin_id == bin_id)
        elif unbinned:
            stmt = stmt.where(SerialUnit.bin_id.is_(None))
        if status:
            stmt = stmt.where(SerialUnit.status == status)
        if search:
            stmt = stmt.where(SerialUnit.serial_number.ilike(f"%{search.strip()}%"))
        return list(self.db.scalars(stmt.order_by(SerialUnit.serial_number).limit(200)))

    def apply_serial_movement(
        self,
        org_id: int,
        product_id: int,
        location_id: int,
        bin_id: int | None,
        serial_numbers: list[str],
        movement: StockMovement,
        *,
        direction: int,
        movement_type: str,
        reverse: bool,
    ) -> None:
        numbers = self.normalize_serials(serial_numbers)
        units = {
            unit.serial_number: unit
            for unit in self.db.scalars(
                select(SerialUnit).where(
                    SerialUnit.org_id == org_id,
                    SerialUnit.product_id == product_id,
                    SerialUnit.serial_number.in_(numbers),
                )
            )
        }
        for number in numbers:
            unit = units.get(number)
            if direction > 0:
                if unit is None:
                    if reverse or movement_type == "sales_return":
                        raise BadRequestError(f"Serial {number} does not belong to this item")
                    unit = SerialUnit(
                        org_id=org_id,
                        product_id=product_id,
                        serial_number=number,
                        status="in_stock",
                    )
                    self.db.add(unit)
                    self.db.flush()
                else:
                    allowed_status = "sold" if reverse or movement_type == "sales_return" else None
                    if allowed_status is None or unit.status != allowed_status:
                        raise ConflictError(f"Serial {number} already exists")
                    unit.status = "in_stock"
                unit.location_id = location_id
                unit.bin_id = bin_id
            else:
                if unit is None or unit.status != "in_stock":
                    raise BadRequestError(f"Serial {number} is not in stock")
                if unit.location_id != location_id or unit.bin_id != bin_id:
                    raise BadRequestError(f"Serial {number} is not in the selected warehouse/bin")
                if reverse and movement_type == "sales_return":
                    unit.status = "sold"
                elif reverse:
                    unit.status = "void"
                elif movement_type in {"sale", "delivery"}:
                    unit.status = "sold"
                else:
                    unit.status = "removed"
                unit.location_id = None
                unit.bin_id = None
            self.db.add(
                StockMovementSerial(movement_id=movement.id, serial_unit_id=unit.id)
            )

    def validate_serials_available(
        self,
        org_id: int,
        product_id: int,
        location_id: int,
        bin_id: int | None,
        serial_numbers: list[str],
    ) -> None:
        numbers = self.normalize_serials(serial_numbers)
        units = list(
            self.db.scalars(
                select(SerialUnit).where(
                    SerialUnit.org_id == org_id,
                    SerialUnit.product_id == product_id,
                    SerialUnit.serial_number.in_(numbers),
                    SerialUnit.status == "in_stock",
                    SerialUnit.location_id == location_id,
                )
            )
        )
        matched = {
            unit.serial_number
            for unit in units
            if (unit.bin_id == bin_id or (unit.bin_id is None and bin_id is None))
        }
        missing = set(numbers) - matched
        if missing:
            raise BadRequestError(
                f"Serial numbers are not available in the selected warehouse/bin: "
                f"{', '.join(sorted(missing))}"
            )

    def validate_serials_receivable(
        self,
        org_id: int,
        product_id: int,
        serial_numbers: list[str],
        *,
        sales_return: bool,
    ) -> None:
        numbers = self.normalize_serials(serial_numbers)
        units = {
            unit.serial_number: unit
            for unit in self.db.scalars(
                select(SerialUnit).where(
                    SerialUnit.org_id == org_id,
                    SerialUnit.product_id == product_id,
                    SerialUnit.serial_number.in_(numbers),
                )
            )
        }
        if sales_return:
            invalid = [
                number
                for number in numbers
                if units.get(number) is None or units[number].status != "sold"
            ]
        else:
            invalid = [number for number in numbers if number in units]
        if invalid:
            action = "not eligible for return" if sales_return else "already exist"
            raise ConflictError(f"Serial numbers {action}: {', '.join(sorted(invalid))}")

    def transfer_serials(
        self,
        org_id: int,
        product_id: int,
        from_location_id: int,
        from_bin_id: int | None,
        to_location_id: int,
        to_bin_id: int | None,
        serial_numbers: list[str],
        movements: tuple[StockMovement, StockMovement],
    ) -> None:
        numbers = self.normalize_serials(serial_numbers)
        self.validate_serials_available(
            org_id, product_id, from_location_id, from_bin_id, numbers
        )
        units = list(
            self.db.scalars(
                select(SerialUnit).where(
                    SerialUnit.org_id == org_id,
                    SerialUnit.product_id == product_id,
                    SerialUnit.serial_number.in_(numbers),
                )
            )
        )
        for unit in units:
            unit.location_id = to_location_id
            unit.bin_id = to_bin_id
            for movement in movements:
                self.db.add(
                    StockMovementSerial(movement_id=movement.id, serial_unit_id=unit.id)
                )
