from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "longevai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.jobs"],
)
celery_app.conf.task_always_eager = settings.celery_eager_mode
celery_app.conf.task_eager_propagates = True

celery_app.conf.task_routes = {
    "app.tasks.jobs.ingest_sources": {"queue": "ingest"},
    "app.tasks.jobs.triage_document": {"queue": "llm"},
    "app.tasks.jobs.analyze_document": {"queue": "llm"},
    "app.tasks.jobs.verify_document": {"queue": "llm"},
    "app.tasks.jobs.cleanup_idempotency": {"queue": "default"},
}
celery_app.conf.beat_schedule = {
    "poll-sources-every-30-min": {
        "task": "app.tasks.jobs.ingest_sources",
        "schedule": crontab(minute="*/30"),
    },
    "cleanup-idempotency-daily": {
        "task": "app.tasks.jobs.cleanup_idempotency",
        "schedule": crontab(minute=0, hour=2),
    },
}
