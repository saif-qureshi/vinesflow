"""A tiny service container — the single place that constructs services.

Instead of hand-writing one FastAPI provider per service, `Provide` resolves
any service class by injecting a request-scoped DB session:

    svc: OrgService = Depends(Provide(OrgService))

Services only need an ``__init__(self, db)``; they never import FastAPI. Outside
of a request (CLI, scripts) just instantiate them directly: ``OrgService(db)``.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db


def Provide[T](service_cls: Callable[[Session], T]) -> Callable[..., T]:
    def _resolver(db: Session = Depends(get_db)) -> T:
        return service_cls(db)

    return _resolver
