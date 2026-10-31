"""Move inactive Kanban tasks to blockers when enabled via settings."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId

from app.core.config import get_settings
from app.models.task import Task, TaskStatus
from app.services.kanban_beanie_store import STATUS_TO_KANBAN_SLUG, task_to_dict


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def effective_last_activity(task: dict) -> Optional[datetime]:
    for key in ("last_activity_at", "updated_at", "created_at"):
        v = task.get(key)
        if v is not None and isinstance(v, datetime):
            return v
    return None


def task_is_stale(task: dict, cutoff: datetime) -> bool:
    la = effective_last_activity(task)
    if la is None:
        return False
    return _as_utc(la) < _as_utc(cutoff)


def inactivity_evidence(days: int) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "source": "system",
        "event": "inactivity",
        "sha": "",
        "url": "",
        "actor": "",
        "at": now,
        "message": f"No activity for {days} days; moved to Blockers.",
    }


async def mark_stale_tasks_in_workspace(workspace_id: str) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.stale_task_auto_blockers_enabled:
        return {"enabled": False, "marked": 0}

    days = max(1, min(int(settings.stale_task_inactivity_days or 3), 365))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    ws_oid = PydanticObjectId(workspace_id)
    active_slugs = {"todo", "in_progress", "in_review"}
    tasks = await Task.find(
        Task.workspace_id == ws_oid,
        Task.is_auto_generated == True,
        Task.deleted_at == None,
    ).to_list()

    marked = 0
    now = datetime.now(timezone.utc)
    for task in tasks:
        row = task_to_dict(task)
        if row.get("status") not in active_slugs:
            continue
        if not task_is_stale(row, cutoff):
            continue
        task.status = TaskStatus.BLOCKERS
        task.updated_at = now
        task.last_activity_at = now
        ev = inactivity_evidence(days)
        task.git_evidence.log.append(
            __import__("app.models.task", fromlist=["GitEvidenceEntry"]).GitEvidenceEntry(
                source=ev["source"],
                event=ev["event"],
                message=ev["message"],
                at=now,
            )
        )
        await task.save()
        marked += 1

    return {"enabled": True, "marked": marked, "cutoff_iso": cutoff.isoformat(), "days": days}
