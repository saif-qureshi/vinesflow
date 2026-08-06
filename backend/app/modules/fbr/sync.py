from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.modules.fbr.client import REFERENCE_ENDPOINTS, FbrClient
from app.modules.fbr.enums import FbrReferenceType
from app.modules.fbr.models import NONE_MARK, FbrReferenceData


def _pick(row: dict, *keys: str) -> Any:
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


class FbrReferenceSyncService:
    def __init__(self, db: Session, client: FbrClient) -> None:
        self.db = db
        self.client = client

    def sync_all(self, log=print) -> dict[str, int]:
        synced_at = datetime.now(UTC)
        counts: dict[str, int] = {}

        doc_types = self.client.get(REFERENCE_ENDPOINTS["doc_types"])
        counts[FbrReferenceType.DOC_TYPE] = self._upsert(
            [
                {"type": FbrReferenceType.DOC_TYPE, "code": str(_pick(d, "docTypeId")),
                 "description": _pick(d, "docDescription")}
                for d in doc_types if _pick(d, "docTypeId") is not None
            ],
            synced_at,
        )
        log(f"doc types: {counts[FbrReferenceType.DOC_TYPE]}")

        hs_codes = self.client.get(REFERENCE_ENDPOINTS["hs_codes"])
        counts[FbrReferenceType.HS_CODE] = self._upsert(
            [
                {"type": FbrReferenceType.HS_CODE, "code": str(_pick(h, "hS_CODE", "hs_Code")),
                 "description": _pick(h, "description")}
                for h in hs_codes if _pick(h, "hS_CODE", "hs_Code") is not None
            ],
            synced_at,
        )
        log(f"hs codes: {counts[FbrReferenceType.HS_CODE]}")

        uoms = self.client.get(REFERENCE_ENDPOINTS["uoms"])
        counts[FbrReferenceType.UOM] = self._upsert(
            [
                {"type": FbrReferenceType.UOM, "code": str(_pick(u, "uoM_ID", "uom_ID")),
                 "description": _pick(u, "description")}
                for u in uoms if _pick(u, "uoM_ID", "uom_ID") is not None
            ],
            synced_at,
        )
        log(f"uoms: {counts[FbrReferenceType.UOM]}")

        sale_types = self.client.get(REFERENCE_ENDPOINTS["sale_types"])
        counts[FbrReferenceType.SALE_TYPE] = self._upsert(
            [
                {"type": FbrReferenceType.SALE_TYPE, "code": str(_pick(s, "transactioN_TYPE_ID")),
                 "description": _pick(s, "transactioN_DESC", "transaction_DESC")}
                for s in sale_types if _pick(s, "transactioN_TYPE_ID") is not None
            ],
            synced_at,
        )
        log(f"sale types: {counts[FbrReferenceType.SALE_TYPE]}")

        sro_item_codes = self.client.get(REFERENCE_ENDPOINTS["sro_item_codes"])
        counts[FbrReferenceType.SRO_ITEM] = self._upsert(
            [
                {"type": FbrReferenceType.SRO_ITEM, "code": str(_pick(s, "srO_ITEM_ID")),
                 "description": _pick(s, "srO_ITEM_DESC")}
                for s in sro_item_codes if _pick(s, "srO_ITEM_ID") is not None
            ],
            synced_at,
        )
        log(f"sro item codes: {counts[FbrReferenceType.SRO_ITEM]}")

        counts[FbrReferenceType.TAX_RATE] = self._sync_tax_rates(sale_types, synced_at, log)
        counts[FbrReferenceType.SRO_SCHEDULE] = self._sync_sro_schedules(synced_at, log)

        self.db.commit()
        return counts

    def _sync_tax_rates(self, sale_types, synced_at, log) -> int:
        date = datetime.now().strftime("%d-%b-%Y")
        rows = []
        for sale_type in sale_types:
            trans_id = _pick(sale_type, "transactioN_TYPE_ID")
            if trans_id is None:
                continue
            try:
                rates = self.client.get(
                    REFERENCE_ENDPOINTS["sale_type_to_rate"],
                    {"date": date, "transTypeId": trans_id},
                )
            except Exception:
                continue
            for rate in rates or []:
                rate_id = _pick(rate, "ratE_ID")
                if rate_id is None:
                    continue
                rows.append({
                    "type": FbrReferenceType.TAX_RATE,
                    "code": str(rate_id),
                    "description": _pick(rate, "ratE_DESC"),
                    "value": _pick(rate, "ratE_VALUE") or 0,
                    "parent_type": FbrReferenceType.SALE_TYPE,
                    "parent_code": str(trans_id),
                })
        count = self._upsert(rows, synced_at)
        log(f"tax rates: {count}")
        return count

    def _sync_sro_schedules(self, synced_at, log) -> int:
        date = datetime.now().strftime("%d-%b-%Y")
        rates = self.db.query(FbrReferenceData).filter(
            FbrReferenceData.type == FbrReferenceType.TAX_RATE
        ).all()
        rows = []
        for rate in rates:
            if (rate.description or "").strip() == "18%":
                continue
            try:
                schedules = self.client.get(
                    REFERENCE_ENDPOINTS["sro_schedule"], {"rate_id": rate.code, "date": date}
                )
            except Exception:
                continue
            for schedule in schedules or []:
                sro_id = _pick(schedule, "srO_ID", "SRO_ID")
                if sro_id is None:
                    continue
                rows.append({
                    "type": FbrReferenceType.SRO_SCHEDULE,
                    "code": str(sro_id),
                    "description": _pick(schedule, "srO_DESC", "SRO_DESC"),
                    "parent_type": FbrReferenceType.TAX_RATE,
                    "parent_code": str(rate.code),
                })
        count = self._upsert(rows, synced_at)
        log(f"sro schedules: {count}")
        return count

    def _fetch_retry(self, fn, attempts: int = 3, delay: float = 1.5):
        import time

        for attempt in range(attempts):
            try:
                return fn() or []
            except Exception:
                if attempt < attempts - 1:
                    time.sleep(delay)
        return None

    def sync_sro_items(self, log=print) -> int:
        synced_at = datetime.now(UTC)
        date_str = datetime.now().strftime("%Y-%m-%d")
        done = {
            pc
            for (pc,) in self.db.query(FbrReferenceData.parent_code)
            .filter(FbrReferenceData.type == "sro_serial")
            .distinct()
        }
        pending = [
            code
            for (code,) in self.db.query(FbrReferenceData.code).filter(
                FbrReferenceData.type == FbrReferenceType.SRO_SCHEDULE
            )
            if code not in done
        ]
        rows = []
        for code in pending:
            items = self._fetch_retry(lambda code=code: self.client.sro_items(code, date_str))
            if items is None:
                continue
            seen: set[str] = set()
            serials = []
            for item in items:
                serial = str(_pick(item, "srO_ITEM_DESC"))
                if serial and serial not in seen:
                    seen.add(serial)
                    serials.append(serial)
            for serial in serials or [NONE_MARK]:
                rows.append({
                    "type": "sro_serial",
                    "code": serial,
                    "description": None if serial == NONE_MARK else serial,
                    "parent_type": FbrReferenceType.SRO_SCHEDULE,
                    "parent_code": code,
                })
        count = self._upsert(rows, synced_at)
        self.db.commit()
        log(f"sro serials: {count} rows for {len(pending)} schedules")
        return count

    def sync_hs_uom(self, log=print, limit: int | None = None, workers: int = 6) -> int:
        from concurrent.futures import ThreadPoolExecutor

        synced_at = datetime.now(UTC)
        done = {
            pc
            for (pc,) in self.db.query(FbrReferenceData.parent_code)
            .filter(FbrReferenceData.type == "hs_uom")
            .distinct()
        }
        codes = [
            code
            for (code,) in self.db.query(FbrReferenceData.code).filter(
                FbrReferenceData.type == FbrReferenceType.HS_CODE
            )
            if code not in done
        ]
        if limit:
            codes = codes[:limit]
        log(f"hs_uom: {len(codes)} to fetch, {len(done)} already done")

        def fetch_one(hs_code):
            return hs_code, self._fetch_retry(lambda: self.client.hs_uom(hs_code))

        batch: list[dict] = []
        stored = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for index, (hs_code, result) in enumerate(pool.map(fetch_one, codes), 1):
                if result is None:
                    continue
                if result:
                    for row in result:
                        uom_id = _pick(row, "uoM_ID", "uom_ID")
                        if uom_id is None:
                            continue
                        batch.append({
                            "type": "hs_uom",
                            "code": str(uom_id),
                            "description": _pick(row, "description"),
                            "parent_type": FbrReferenceType.HS_CODE,
                            "parent_code": hs_code,
                        })
                else:
                    batch.append({
                        "type": "hs_uom",
                        "code": NONE_MARK,
                        "description": None,
                        "parent_type": FbrReferenceType.HS_CODE,
                        "parent_code": hs_code,
                    })
                stored += 1
                if len(batch) >= 300:
                    self._upsert(batch, synced_at)
                    self.db.commit()
                    batch = []
                if index % 200 == 0:
                    log(f"  hs_uom {index}/{len(codes)}")
        if batch:
            self._upsert(batch, synced_at)
            self.db.commit()
        log(f"hs_uom: fetched {stored}/{len(codes)}")
        return stored

    def _upsert(self, rows: list[dict], synced_at: datetime) -> int:
        if not rows:
            return 0
        deduped: dict[tuple[str, str, str], dict] = {}
        for row in rows:
            entry = {
                "type": str(row["type"]),
                "code": str(row["code"]),
                "description": row.get("description"),
                "value": row.get("value"),
                "parent_type": str(row["parent_type"]) if row.get("parent_type") else None,
                "parent_code": str(row.get("parent_code") or ""),
                "is_active": True,
                "synced_at": synced_at,
            }
            deduped[(entry["type"], entry["code"], entry["parent_code"])] = entry
        payload = list(deduped.values())
        for start in range(0, len(payload), 500):
            chunk = payload[start : start + 500]
            stmt = pg_insert(FbrReferenceData).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_fbr_reference_type_code_parent",
                set_={
                    "description": stmt.excluded.description,
                    "value": stmt.excluded.value,
                    "parent_type": stmt.excluded.parent_type,
                    "is_active": stmt.excluded.is_active,
                    "synced_at": stmt.excluded.synced_at,
                },
            )
            self.db.execute(stmt)
        return len(payload)
