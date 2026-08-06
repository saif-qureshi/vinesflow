from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.manufacturers.models import Manufacturer
from app.modules.manufacturers.schemas import ManufacturerCreate, ManufacturerUpdate


class ManufacturerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, org_id: int) -> list[Manufacturer]:
        return list(
            self.db.scalars(
                select(Manufacturer).where(Manufacturer.org_id == org_id).order_by(Manufacturer.name)
            ).all()
        )

    def get(self, org_id: int, manufacturer_id: int) -> Manufacturer:
        row = self.db.scalar(
            select(Manufacturer).where(Manufacturer.id == manufacturer_id, Manufacturer.org_id == org_id)
        )
        if row is None:
            raise NotFoundError("Manufacturer not found")
        return row

    def _ensure_unique_name(self, org_id: int, name: str, exclude_id: int | None = None) -> None:
        q = select(Manufacturer.id).where(Manufacturer.org_id == org_id, Manufacturer.name == name)
        if exclude_id is not None:
            q = q.where(Manufacturer.id != exclude_id)
        if self.db.scalar(q) is not None:
            raise ConflictError("A manufacturer with that name already exists")

    def create(self, org_id: int, payload: ManufacturerCreate) -> Manufacturer:
        self._ensure_unique_name(org_id, payload.name)
        row = Manufacturer(org_id=org_id, **payload.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update(self, org_id: int, manufacturer_id: int, payload: ManufacturerUpdate) -> Manufacturer:
        row = self.get(org_id, manufacturer_id)
        if payload.name is not None:
            self._ensure_unique_name(org_id, payload.name, exclude_id=manufacturer_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, org_id: int, manufacturer_id: int) -> None:
        from app.modules.products.models import Product

        row = self.get(org_id, manufacturer_id)
        if self.db.scalar(
            select(Product.id).where(Product.manufacturer_id == manufacturer_id).limit(1)
        ):
            raise ConflictError("Manufacturer is used by items; deactivate it instead")
        self.db.delete(row)
        self.db.commit()
