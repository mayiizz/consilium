"""Compare auto-generated tasks to meeting transcripts; persist drift report."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId

from app.models.meeting import Meeting
from app.models.task import Task
from app.services.kanban_agentic_automation import _validate_transcript_evidence

logger = logging.getLogger(__name__)


def _title_tokens(title: str) -> List[str]:
    t = (title or "").lower()
    return [w for w in re.split(r"\W+", t) if len(w) > 2][:12]


async def _transcript_for_meeting(meeting_id: str) -> str:
    m = await Meeting.get(PydanticObjectId(meeting_id))
    if not m or m.deleted_at:
        return ""
    return m.full_transcript()


def _task_supported_by_transcript(title: str, description: Optional[str], corpus: str) -> bool:
    if not corpus.strip():
        return False
    desc = (description or "").strip()
    if desc and _validate_transcript_evidence(desc[:800], corpus):
        return True
    tokens = _title_tokens(title)
    if len(tokens) < 2:
        return title.strip().lower() in corpus.lower() if title.strip() else False
    corp_l = corpus.lower()
    hits = sum(1 for w in tokens if w in corp_l)
    return hits >= max(2, min(3, len(tokens) // 2))


async def reconcile_workspace_tasks(
    workspace_id: str,
    trigger_meeting_id: Optional[str] = None,
) -> Dict[str, Any]:
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import get_settings

    settings = get_settings()
    now = datetime.now(timezone.utc)
    ws_oid = PydanticObjectId(workspace_id)
    tasks = await Task.find(
        Task.workspace_id == ws_oid,
        Task.is_auto_generated == True,
        Task.deleted_at == None,
    ).to_list()

    corpus_by_meeting: Dict[str, str] = {}
    orphan_tasks: List[Dict[str, Any]] = []

    for t in tasks:
        mid = str(t.source_meeting_id or t.meeting_id or "").strip()
        if not mid:
            continue
        if mid not in corpus_by_meeting:
            corpus_by_meeting[mid] = await _transcript_for_meeting(mid)
        corpus = corpus_by_meeting[mid]
        title = str(t.title or "")
        desc = t.description
        if not _task_supported_by_transcript(title, desc if isinstance(desc, str) else None, corpus):
            orphan_tasks.append(
                {
                    "task_id": str(t.id),
                    "title": title,
                    "source_meeting_id": mid,
                }
            )

    doc = {
        "workspace_id": workspace_id,
        "project_id": workspace_id,
        "trigger_meeting_id": trigger_meeting_id,
        "created_at": now,
        "orphan_task_count": len(orphan_tasks),
        "orphan_tasks": orphan_tasks[:200],
    }
    try:
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_db_name]
        await db.transcript_task_reconciliation.insert_one(doc)
        client.close()
    except Exception:
        logger.exception("Failed to persist transcript_task_reconciliation workspace_id=%s", workspace_id)

    return {
        "workspace_id": workspace_id,
        "orphan_task_count": len(orphan_tasks),
        "orphan_tasks": orphan_tasks[:50],
    }
