"""Celery tasks for research jobs and due-date reminders."""

from app.core.logging import get_logger
from app.workers.celery_app import celery_app
from app.workers.tasks.extraction import _init_db, _run_async

logger = get_logger(__name__)


@celery_app.task(name="research.run_job", bind=True, max_retries=1)
def run_research_job(self, job_id: str) -> dict:
    async def _run():
        await _init_db()
        from app.services.research_agent_service import research_agent_service

        return await research_agent_service.run_job(job_id)

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.exception("run_research_job failed", extra={"job_id": job_id})
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="notifications.send_due_reminders")
def send_due_reminders() -> dict:
    async def _run():
        await _init_db()
        from app.services.notification_service import notification_service

        return await notification_service.send_due_soon_reminders()

    try:
        return _run_async(_run())
    except Exception:
        logger.exception("send_due_reminders failed")
        return {"sent": 0, "error": "failed"}
