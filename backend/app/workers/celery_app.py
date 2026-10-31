import asyncio

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "consilium",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.extraction",
        "app.workers.tasks.research",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "send-due-reminders-hourly": {
            "task": "notifications.send_due_reminders",
            "schedule": crontab(minute=0),  # every hour
        },
    },
)


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)
