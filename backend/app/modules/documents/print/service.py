from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.pdf import PdfService, page_footer_html
from app.core.storage import Storage, get_storage
from app.modules.documents.enums import DocumentStatus, DocumentType
from app.modules.documents.models import Document
from app.modules.documents.print.mapper import branding_for, document_to_print
from app.modules.documents.print.skins import render_document_html
from app.modules.documents.service import DocumentService
from app.modules.orgs.models import Organization

# Bump to invalidate every cached PDF (e.g. after a skin template fix).
_PDF_CACHE_VERSION = "3"


class DocumentPrintService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.documents = DocumentService(db)
        self.pdf = PdfService()
        self.storage = get_storage()

    def _org(self, org_id: int) -> Organization:
        org = self.db.scalar(select(Organization).where(Organization.id == org_id))
        if org is None:
            raise NotFoundError("Organization not found")
        return org

    def render_html(self, org_id: int, doc_id: int, doc_type: DocumentType, skin: str) -> str:
        doc = self.documents.get_of_type(org_id, doc_id, doc_type)
        org = self._org(org_id)
        return render_document_html(document_to_print(doc, org), branding_for(org), skin)

    def render_pdf(
        self, org_id: int, doc_id: int, doc_type: DocumentType, skin: str, paper: str
    ) -> tuple[bytes, str]:
        doc = self.documents.get_of_type(org_id, doc_id, doc_type)
        filename = f"{doc.number}.pdf"

        cache_key = self._pdf_cache_key(org_id, doc, skin, paper)
        if cache_key:
            cached = _cache_get(self.storage, cache_key)
            if cached is not None:
                return cached, filename

        org = self._org(org_id)
        branding = branding_for(org)
        body_branding = branding.model_copy(update={"footer_text": None})
        html = render_document_html(document_to_print(doc, org), body_branding, skin)
        footer = page_footer_html(branding.footer_text) if branding.footer_text else None
        content = self.pdf.html_to_pdf(html, paper, footer)

        if cache_key:
            _cache_put(self.storage, cache_key, content)
        return content, filename

    def _pdf_cache_key(self, org_id: int, doc: Document, skin: str, paper: str) -> str | None:
        if doc.status == DocumentStatus.DRAFT:
            return None
        raw = ":".join(
            [
                _PDF_CACHE_VERSION,
                str(doc.id),
                doc.updated_at.isoformat(),
                skin,
                paper,
                settings.JWT_SECRET,
            ]
        )
        digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
        return f"{settings.MEDIA_KEY_PREFIX}org-{org_id}/pdf-cache/{digest}.pdf"


def _cache_get(storage: Storage, key: str) -> bytes | None:
    try:
        return storage.get_bytes(key)
    except Exception:
        return None


def _cache_put(storage: Storage, key: str, content: bytes) -> None:
    try:
        storage.put_bytes(key, content, content_type="application/pdf")
    except Exception:
        return
