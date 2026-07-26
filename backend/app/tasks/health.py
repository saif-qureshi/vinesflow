from __future__ import annotations

from sqlalchemy import text

from app.celery_app import celery_app
from app.tasks import worker_session


@celery_app.task(name="health.ping")
def ping() -> str:
    return "pong"


@celery_app.task(name="health.db_ping")
def db_ping() -> int:
    with worker_session() as db:
        return db.scalar(text("SELECT 1"))
