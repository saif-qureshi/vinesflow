"""Celery application: SQS broker in production, inline (eager) execution in dev.

Register new task modules in TASK_MODULES (or app/modules/<x>/tasks.py). Long-job
progress is tracked in Postgres — SQS provides no result backend.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

TASK_MODULES = [
    "app.tasks.health",
]


def _broker_transport_options() -> dict:
    options: dict = {
        "region": settings.SQS_REGION or settings.S3_REGION or "ap-south-1",
        "visibility_timeout": settings.CELERY_VISIBILITY_TIMEOUT,
        "wait_time_seconds": 20,
        "polling_interval": 1,
    }
    if settings.SQS_QUEUE_URL:
        options["predefined_queues"] = {settings.SQS_QUEUE_NAME: {"url": settings.SQS_QUEUE_URL}}
    return options


celery_app = Celery("vineflow", broker="sqs://", include=TASK_MODULES)

celery_app.conf.update(
    task_default_queue=settings.SQS_QUEUE_NAME,
    broker_transport_options=_broker_transport_options(),
    result_backend=None,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
)
