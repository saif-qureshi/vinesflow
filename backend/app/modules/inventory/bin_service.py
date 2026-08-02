from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.modules.documents.models import DocumentLine
from app.modules.inventory.models import Bin, StockLevel, StockMovement
from app.modules.inventory.schemas import BinCreate, BinUpdate
from app.modules.locations.models import Location


class BinService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _location(self, org_id: int, location_id: int) -> Location:
        location = self.db.scalar(
            select(Location).where(Location.id == location_id, Location.org_id == org_id)
        )
        if location is None:
            raise NotFoundError("Warehouse not found")
        return location

    def get(self, org_id: int, bin_id: int) -> Bin:
        bin_ = self.db.scalar(select(Bin).where(Bin.id == bin_id, Bin.org_id == org_id))
        if bin_ is None:
            raise NotFoundError("Bin not found")
        return bin_

    def list(
        self, org_id: int, *, location_id: int | None = None, active_only: bool = False
    ) -> list[Bin]:
        stmt = select(Bin).where(Bin.org_id == org_id)
        if location_id is not None:
            self._location(org_id, location_id)
            stmt = stmt.where(Bin.location_id == location_id)
        if active_only:
            stmt = stmt.where(Bin.is_active.is_(True))
        return list(self.db.scalars(stmt.order_by(Bin.location_id, Bin.code)))

    def _unique_code(
        self, org_id: int, location_id: int, code: str, *, exclude_id: int | None = None
    ) -> str:
        normalized = code.strip().upper()
        if not normalized:
            raise BadRequestError("Bin code is required")
        stmt = select(Bin.id).where(
            Bin.org_id == org_id,
            Bin.location_id == location_id,
            Bin.code == normalized,
        )
        if exclude_id is not None:
            stmt = stmt.where(Bin.id != exclude_id)
        if self.db.scalar(stmt) is not None:
            raise ConflictError("A bin with that code already exists in this warehouse")
        return normalized

    @staticmethod
    def _name(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise BadRequestError("Bin name is required")
        return normalized

    def create(self, org_id: int, payload: BinCreate) -> Bin:
        location = self._location(org_id, payload.location_id)
        if not location.is_active:
            raise ConflictError("Cannot add a bin to an inactive warehouse")
        bin_ = Bin(
            org_id=org_id,
            location_id=payload.location_id,
            code=self._unique_code(org_id, payload.location_id, payload.code),
            name=self._name(payload.name),
            is_active=payload.is_active,
        )
        self.db.add(bin_)
        self.db.commit()
        self.db.refresh(bin_)
        return bin_

    def update(self, org_id: int, bin_id: int, payload: BinUpdate) -> Bin:
        bin_ = self.get(org_id, bin_id)
        if payload.code is not None:
            bin_.code = self._unique_code(
                org_id, bin_.location_id, payload.code, exclude_id=bin_.id
            )
        if payload.name is not None:
            bin_.name = self._name(payload.name)
        if payload.is_active is False and bin_.is_active:
            has_stock = self.db.scalar(
                select(StockLevel.id)
                .where(StockLevel.bin_id == bin_id, StockLevel.quantity != 0)
                .limit(1)
            )
            if has_stock is not None:
                raise ConflictError("Move all stock out of this bin before deactivating it")
        if payload.is_active is True and not bin_.is_active:
            location = self._location(org_id, bin_.location_id)
            if not location.is_active:
                raise ConflictError("Cannot activate a bin in an inactive warehouse")
        if payload.is_active is not None:
            bin_.is_active = payload.is_active
        self.db.commit()
        self.db.refresh(bin_)
        return bin_

    def delete(self, org_id: int, bin_id: int) -> None:
        bin_ = self.get(org_id, bin_id)
        has_history = self.db.scalar(
            select(StockMovement.id).where(StockMovement.bin_id == bin_id).limit(1)
        )
        used_by_draft = self.db.scalar(
            select(DocumentLine.id).where(DocumentLine.bin_id == bin_id).limit(1)
        )
        has_level = self.db.scalar(
            select(StockLevel.id).where(StockLevel.bin_id == bin_id).limit(1)
        )
        if has_history or used_by_draft or has_level:
            raise ConflictError("Bin has inventory history; deactivate it instead")
        self.db.delete(bin_)
        self.db.commit()

    def validate_for_location(
        self, org_id: int, location_id: int, bin_id: int | None, *, active: bool = True
    ) -> Bin | None:
        if bin_id is None:
            return None
        stmt = select(Bin).where(
            Bin.id == bin_id,
            Bin.org_id == org_id,
            Bin.location_id == location_id,
        )
        if active:
            stmt = stmt.where(Bin.is_active.is_(True))
        bin_ = self.db.scalar(stmt)
        if bin_ is None:
            raise NotFoundError("Bin not found in the selected warehouse")
        return bin_
