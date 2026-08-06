from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.brands.models import Brand
from app.modules.brands.schemas import BrandCreate, BrandUpdate


class BrandService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, org_id: int) -> list[Brand]:
        return list(
            self.db.scalars(
                select(Brand).where(Brand.org_id == org_id).order_by(Brand.name)
            ).all()
        )

    def get(self, org_id: int, brand_id: int) -> Brand:
        row = self.db.scalar(
            select(Brand).where(Brand.id == brand_id, Brand.org_id == org_id)
        )
        if row is None:
            raise NotFoundError("Brand not found")
        return row

    def _ensure_unique_name(self, org_id: int, name: str, exclude_id: int | None = None) -> None:
        q = select(Brand.id).where(Brand.org_id == org_id, Brand.name == name)
        if exclude_id is not None:
            q = q.where(Brand.id != exclude_id)
        if self.db.scalar(q) is not None:
            raise ConflictError("A brand with that name already exists")

    def create(self, org_id: int, payload: BrandCreate) -> Brand:
        self._ensure_unique_name(org_id, payload.name)
        row = Brand(org_id=org_id, **payload.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update(self, org_id: int, brand_id: int, payload: BrandUpdate) -> Brand:
        row = self.get(org_id, brand_id)
        if payload.name is not None:
            self._ensure_unique_name(org_id, payload.name, exclude_id=brand_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, org_id: int, brand_id: int) -> None:
        from app.modules.products.models import Product

        row = self.get(org_id, brand_id)
        if self.db.scalar(
            select(Product.id).where(Product.brand_id == brand_id).limit(1)
        ):
            raise ConflictError("Brand is used by items; deactivate it instead")
        self.db.delete(row)
        self.db.commit()
