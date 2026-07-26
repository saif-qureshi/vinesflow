from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session


class LedgerPoster(Protocol):
    def post_document(self, db: Session, document) -> None: ...
    def reverse_document(self, db: Session, document) -> None: ...
    def post_payment(self, db: Session, payment) -> None: ...
    def reverse_payment(self, db: Session, payment) -> None: ...
    def post_inventory_adjustment(
        self, db: Session, *, org_id, value, account_id, posting_date, source_id
    ) -> None: ...


class NullLedgerPoster:
    def post_document(self, db: Session, document) -> None:
        return None

    def reverse_document(self, db: Session, document) -> None:
        return None

    def post_payment(self, db: Session, payment) -> None:
        return None

    def reverse_payment(self, db: Session, payment) -> None:
        return None

    def post_inventory_adjustment(
        self, db: Session, *, org_id, value, account_id, posting_date, source_id
    ) -> None:
        return None


ledger_poster: LedgerPoster = NullLedgerPoster()


def set_ledger_poster(poster: LedgerPoster) -> None:
    """Swap the active poster (called once at app startup to bind the real GL)."""
    global ledger_poster
    ledger_poster = poster
