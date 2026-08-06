from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.salespeople.models import Salesperson
from app.modules.salespeople.schemas import SalespersonCreate, SalespersonUpdate


class SalespersonService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, org_id: int) -> list[Salesperson]:
        return list(
            self.db.scalars(
                select(Salesperson)
                .where(Salesperson.org_id == org_id)
                .order_by(Salesperson.name)
            ).all()
        )

    def get(self, org_id: int, salesperson_id: int) -> Salesperson:
        row = self.db.scalar(
            select(Salesperson).where(
                Salesperson.id == salesperson_id, Salesperson.org_id == org_id
            )
        )
        if row is None:
            raise NotFoundError("Salesperson not found")
        return row

    def _ensure_unique_name(self, org_id: int, name: str, exclude_id: int | None = None) -> None:
        q = select(Salesperson.id).where(
            Salesperson.org_id == org_id, Salesperson.name == name
        )
        if exclude_id is not None:
            q = q.where(Salesperson.id != exclude_id)
        if self.db.scalar(q) is not None:
            raise ConflictError("A salesperson with that name already exists")

    def create(self, org_id: int, payload: SalespersonCreate) -> Salesperson:
        self._ensure_unique_name(org_id, payload.name)
        row = Salesperson(org_id=org_id, **payload.model_dump())
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update(
        self, org_id: int, salesperson_id: int, payload: SalespersonUpdate
    ) -> Salesperson:
        row = self.get(org_id, salesperson_id)
        if payload.name is not None:
            self._ensure_unique_name(org_id, payload.name, exclude_id=salesperson_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, org_id: int, salesperson_id: int) -> None:
        from app.modules.documents.models import Document

        row = self.get(org_id, salesperson_id)
        if self.db.scalar(
            select(Document.id).where(Document.salesperson_id == salesperson_id).limit(1)
        ):
            raise ConflictError("Salesperson is credited on documents; deactivate instead")
        self.db.delete(row)
        self.db.commit()
