from __future__ import annotations

from typing import Callable

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.core.exceptions import BadRequestError, NotFoundError, ServiceUnavailableError
from app.modules.fbr.client import FbrClient
from app.modules.fbr.enums import FbrEnvironment, FbrProvince
from app.modules.fbr.invoice import FbrInvoiceBuilder
from app.modules.fbr.models import NONE_MARK, FbrReferenceData
from app.modules.fbr.schemas import FbrOption, FbrReferenceRead
from app.modules.documents.models import Document
from app.modules.orgs.models import Organization


class FbrService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def provinces(self) -> list[FbrOption]:
        return [FbrOption(value=p.value, label=p.value.title()) for p in FbrProvince]

    def _reference_token(self, org_id: int) -> str:
        if settings.FBR_REFERENCE_TOKEN:
            return settings.FBR_REFERENCE_TOKEN
        org = self.db.get(Organization, org_id)
        encrypted = None
        if org is not None:
            encrypted = (
                org.fbr_sandbox_token
                if org.fbr_environment == "sandbox"
                else org.fbr_production_token
            ) or org.fbr_sandbox_token or org.fbr_production_token
        if not encrypted:
            raise ServiceUnavailableError("No FBR token configured")
        return decrypt_secret(encrypted)

    def _cached_reference(
        self,
        cache_type: str,
        parent_type: str,
        parent_code: str,
        fetch: Callable[[], list[dict]],
    ) -> list[FbrReferenceRead]:
        cached = list(
            self.db.scalars(
                select(FbrReferenceData).where(
                    FbrReferenceData.type == cache_type,
                    FbrReferenceData.parent_code == parent_code,
                )
            )
        )
        if cached:
            return [
                FbrReferenceRead(code=r.code, description=r.description, parent_code=parent_code)
                for r in cached
                if r.code != NONE_MARK
            ]
        try:
            rows = fetch()
        except ServiceUnavailableError:
            return []
        to_store = rows or [{"code": NONE_MARK, "description": None}]
        self.db.execute(
            pg_insert(FbrReferenceData)
            .values(
                [
                    {
                        "type": cache_type,
                        "code": item["code"],
                        "description": item.get("description"),
                        "parent_type": parent_type,
                        "parent_code": parent_code,
                    }
                    for item in to_store
                ]
            )
            .on_conflict_do_nothing(constraint="uq_fbr_reference_type_code_parent")
        )
        self.db.commit()
        return [
            FbrReferenceRead(code=item["code"], description=item.get("description"), parent_code=parent_code)
            for item in rows
        ]

    def hs_uom(self, org_id: int, hs_code: str) -> list[FbrReferenceRead]:
        def fetch() -> list[dict]:
            rows = FbrClient(self._reference_token(org_id)).hs_uom(hs_code) or []
            return [{"code": str(r["uoM_ID"]), "description": r.get("description")} for r in rows]

        return self._cached_reference("hs_uom", "hs_code", hs_code, fetch)

    def sro_items(self, org_id: int, sro_id: str) -> list[FbrReferenceRead]:
        from datetime import date

        def fetch() -> list[dict]:
            rows = FbrClient(self._reference_token(org_id)).sro_items(sro_id, date.today().isoformat())
            seen: set[str] = set()
            items: list[dict] = []
            for row in rows or []:
                serial = str(row["srO_ITEM_DESC"])
                if serial in seen:
                    continue
                seen.add(serial)
                items.append({"code": serial, "description": serial})
            return items

        return self._cached_reference("sro_serial", "sro_schedule", sro_id, fetch)

    def reference(
        self, ref_type: str, parent: str | None, search: str | None, limit: int
    ) -> list[FbrReferenceData]:
        stmt = select(FbrReferenceData).where(
            FbrReferenceData.type == ref_type, FbrReferenceData.is_active.is_(True)
        )
        if parent is not None:
            stmt = stmt.where(FbrReferenceData.parent_code == parent)
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(FbrReferenceData.code.ilike(like), FbrReferenceData.description.ilike(like))
            )
        return list(self.db.scalars(stmt.order_by(FbrReferenceData.code).limit(limit)))

    def summary(self) -> dict[str, int]:
        rows = self.db.execute(
            select(FbrReferenceData.type, func.count()).group_by(FbrReferenceData.type)
        ).all()
        return {ref_type: count for ref_type, count in rows}

    def _org_client(self, org: Organization) -> FbrClient:
        environment = org.fbr_environment or "production"
        encrypted = (
            org.fbr_production_token if environment == "production" else org.fbr_sandbox_token
        )
        if not encrypted:
            raise BadRequestError(f"No {environment} FBR token is configured")
        return FbrClient(decrypt_secret(encrypted), FbrEnvironment(environment))

    @staticmethod
    def _fbr_errors(response: dict | None) -> list[dict]:
        vr = (response or {}).get("validationResponse", {}) or {}
        if vr.get("statusCode") == "00" or vr.get("status") == "Valid":
            return []
        errors: list[dict] = []
        if vr.get("error"):
            errors.append({"item": None, "msg": str(vr["error"])})
        for item in vr.get("invoiceStatuses", []) or []:
            if item.get("error"):
                errors.append({"item": item.get("itemSNo"), "msg": str(item["error"])})
        return errors or [{"item": None, "msg": "FBR marked the invoice as invalid"}]

    def submit_invoice(self, org_id: int, doc: Document) -> dict | None:
        from app.modules.settings.service import SettingsService

        org = self.db.get(Organization, org_id)
        if org is None or not org.fbr_enabled:
            return None
        require_validate = bool(
            SettingsService(self.db).get(org_id, "fbr", "validate_before_submit", True)
        )
        payload = FbrInvoiceBuilder(self.db).build(doc, org)
        client = self._org_client(org)
        if require_validate:
            errors = self._fbr_errors(client.validate_invoice(payload))
            if errors:
                raise BadRequestError("FBR validation failed", code="fbr_validation", details=errors)
        result = client.post_invoice(payload)
        errors = self._fbr_errors(result)
        if errors:
            raise BadRequestError("FBR submission failed", code="fbr_submission", details=errors)
        return {"invoice_number": result.get("invoiceNumber"), "response": result}

    def validate_document(
        self, org_id: int, doc_id: int, scenario_id: str | None = None
    ) -> dict:
        org = self.db.get(Organization, org_id)
        if org is None or not org.fbr_enabled:
            raise BadRequestError("FBR e-invoicing is not enabled for this organization")
        doc = self.db.get(Document, doc_id)
        if doc is None or doc.org_id != org_id:
            raise NotFoundError("Document not found")
        payload = FbrInvoiceBuilder(self.db).build(doc, org, scenario_id)
        response = self._org_client(org).validate_invoice(payload)
        errors = self._fbr_errors(response)
        return {"valid": not errors, "errors": errors, "payload": payload, "response": response}
