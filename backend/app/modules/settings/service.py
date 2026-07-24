from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.modules.settings.models import Setting
from app.modules.settings.schemas import NumberingEntryUpdate


class SettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, org_id: int, group: str, key: str, fallback: Any = None) -> Any:
        row = self.db.scalar(
            select(Setting).where(
                Setting.org_id == org_id, Setting.group == group, Setting.key == key
            )
        )
        return row.value if row is not None else fallback

    def get_group(self, org_id: int, group: str) -> dict[str, Any]:
        rows = self.db.scalars(
            select(Setting).where(Setting.org_id == org_id, Setting.group == group)
        )
        return {row.key: row.value for row in rows}

    def set(self, org_id: int, group: str, key: str, value: Any) -> None:
        stmt = pg_insert(Setting).values(org_id=org_id, group=group, key=key, value=value)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_setting_org_group_key", set_={"value": stmt.excluded.value}
        )
        self.db.execute(stmt)

    def set_group(self, org_id: int, group: str, values: dict[str, Any]) -> dict[str, Any]:
        for key, value in values.items():
            self.set(org_id, group, key, value)
        self.db.commit()
        return self.get_group(org_id, group)

    def numbering_spec(self) -> list[tuple[str, str, str]]:
        from app.modules.documents.enums import (
            DEFAULT_PREFIXES,
            PAYMENT_PREFIXES,
            DocumentType,
            PaymentDirection,
        )

        return [
            (str(DocumentType.INVOICE), "Invoice", DEFAULT_PREFIXES[DocumentType.INVOICE]),
            (str(DocumentType.CREDIT_NOTE), "Credit Note", DEFAULT_PREFIXES[DocumentType.CREDIT_NOTE]),
            (str(DocumentType.SALES_ORDER), "Sales Order", DEFAULT_PREFIXES[DocumentType.SALES_ORDER]),
            (str(DocumentType.DELIVERY_CHALLAN), "Delivery Challan", DEFAULT_PREFIXES[DocumentType.DELIVERY_CHALLAN]),
            (str(DocumentType.PURCHASE_ORDER), "Purchase Order", DEFAULT_PREFIXES[DocumentType.PURCHASE_ORDER]),
            (str(DocumentType.GOODS_RECEIPT), "Goods Receipt", DEFAULT_PREFIXES[DocumentType.GOODS_RECEIPT]),
            (str(DocumentType.BILL), "Bill", DEFAULT_PREFIXES[DocumentType.BILL]),
            ("payment_received", "Payment Received", PAYMENT_PREFIXES[PaymentDirection.RECEIVED]),
            ("payment_made", "Payment Made", PAYMENT_PREFIXES[PaymentDirection.MADE]),
        ]

    def numbering_entries(self, org_id: int) -> list[dict[str, Any]]:
        stored = self.get_group(org_id, "numbering")
        entries = []
        for key, label, default_prefix in self.numbering_spec():
            value = stored.get(key) or {}
            entries.append(
                {
                    "key": key,
                    "label": label,
                    "prefix": str(value.get("prefix") or default_prefix),
                    "start": str(value.get("start") or "0001"),
                    "restart": str(value.get("restart") or "none"),
                }
            )
        return entries

    def set_numbering(self, org_id: int, entries: list[NumberingEntryUpdate]) -> list[dict[str, Any]]:
        allowed = {key for key, _, _ in self.numbering_spec()}
        for entry in entries:
            if entry.key not in allowed:
                raise BadRequestError(f"Unknown numbering key: {entry.key}")
        for entry in entries:
            self.set(
                org_id,
                "numbering",
                entry.key,
                {"prefix": entry.prefix, "start": entry.start, "restart": entry.restart},
            )
        self.db.commit()
        return self.numbering_entries(org_id)

    def seed_numbering(self, org_id: int) -> None:
        existing = set(self.get_group(org_id, "numbering"))
        for key, _, default_prefix in self.numbering_spec():
            if key not in existing:
                self.set(
                    org_id,
                    "numbering",
                    key,
                    {"prefix": default_prefix, "start": "0001", "restart": "none"},
                )
        self.db.flush()
