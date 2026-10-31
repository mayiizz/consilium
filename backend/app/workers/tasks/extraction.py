import asyncio
from datetime import datetime, timezone

from beanie import PydanticObjectId

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


async def _init_db():
    from app.core.database import init_models
    from app.core.redis import connect_redis
    await init_models()
    try:
        await connect_redis()
    except Exception:
        pass


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _fallback_summary_from_transcript(transcript: str) -> dict:
    lines = [line.strip() for line in transcript.split("\n") if line.strip()]
    preview = " ".join(lines[:3])[:500]
    return {
        "summary": preview or "Meeting ended. No transcript content to summarize.",
        "action_items": lines[:3],
        "key_decisions": [],
    }


def _parse_confidence(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"high", "medium", "low"}:
            return {"high": 0.9, "medium": 0.6, "low": 0.3}[lowered]
        try:
            return float(value)
        except ValueError:
            return 0.5
    return 0.5


def _fallback_tasks_from_transcript(transcript: str, action_items: list | None = None) -> list:
    if action_items:
        return [
            {
                "title": item,
                "description": item,
                "status": "To Do",
                "confidence": 0.5,
                "evidence": item,
            }
            for item in action_items[:5]
        ]
    lines = [line.strip() for line in transcript.split("\n") if len(line.strip()) > 10]
    return [
        {
            "title": line[:80],
            "description": line,
            "status": "To Do",
            "confidence": 0.4,
            "evidence": line,
        }
        for line in lines[:5]
    ]


async def _process_meeting_artifacts(meeting_id: str) -> dict:
    """Generate summary, decisions, action items, and sync Kanban from transcript."""
    await _init_db()
    from app.integrations.groq import GroqLLMService, GroqUnavailableError
    from app.models.meeting import Meeting

    meeting = await Meeting.get(PydanticObjectId(meeting_id))
    if not meeting or meeting.deleted_at:
        return {"meeting_id": meeting_id, "error": "not_found"}

    kanban_result: dict = {}
    transcript = meeting.full_transcript()
    if transcript:
        llm = GroqLLMService()
        summary_data = _fallback_summary_from_transcript(transcript)
        try:
            summary_data = await llm.summarize_meeting(transcript)
        except GroqUnavailableError as exc:
            logger.warning("Groq unavailable; using fallback summary", extra={"meeting_id": meeting_id})
            summary_data = _fallback_summary_from_transcript(transcript)
            if "rate limit" in str(exc).lower():
                summary_data["summary"] = (
                    "Meeting ended. AI summary temporarily unavailable (Groq rate limit). "
                    "Use Regenerate summary in a moment."
                )
            else:
                summary_data["summary"] = (
                    "Meeting ended. AI summary unavailable (GROQ_API_KEY not set in the running API process)."
                )
        except Exception:
            logger.exception("Summary generation failed; using fallback", extra={"meeting_id": meeting_id})

        meeting.summary = summary_data.get("summary") or _fallback_summary_from_transcript(transcript)["summary"]
        meeting.action_items = summary_data.get("action_items", [])
        meeting.key_decisions = summary_data.get("key_decisions", [])
        meeting.updated_at = datetime.now(timezone.utc)
        await meeting.save()

        from app.services.kanban_automation import rebuild_kanban_for_workspace

        try:
            kanban_result = await rebuild_kanban_for_workspace(
                str(meeting.workspace_id),
                trigger_meeting_id=meeting_id,
                fresh=False,
            )
        except Exception:
            logger.exception("Kanban rebuild failed after meeting end", extra={"meeting_id": meeting_id})
            kanban_result = {}

        # If LLM extract created nothing but summary has action items, seed the board.
        if int(kanban_result.get("created") or 0) == 0 and meeting.action_items:
            try:
                seeded = await _seed_kanban_from_action_items(meeting)
                if seeded:
                    kanban_result = {**kanban_result, "created": seeded, "seeded_from_action_items": True}
            except Exception:
                logger.exception(
                    "Action-item Kanban seed failed",
                    extra={"meeting_id": meeting_id},
                )

    created = kanban_result.get("created", 0)
    updated = kanban_result.get("updated", 0)
    return {
        "meeting_id": meeting_id,
        "tasks_created": created,
        "tasks_moved": updated,
        "kanban": kanban_result,
    }


def _parse_action_item_assignee(item: str) -> tuple[str, str]:
    """'Karthik: do X' → (Karthik, do X). Otherwise assignee blank and full string is title."""
    text = (item or "").strip()
    if ":" in text:
        left, right = text.split(":", 1)
        name = left.strip()
        rest = right.strip()
        if name and rest and len(name.split()) <= 3 and not name.lower().startswith("http"):
            return name, rest[:200]
    return "", text[:200]


async def _seed_kanban_from_action_items(meeting) -> int:
    """Create auto Kanban tasks from meeting.action_items when LLM extract produced none."""
    from app.services.kanban_beanie_store import BeanieKanbanStore, workspace_member_users
    from app.services.kanban_agentic_automation import _resolve_assignee_user_id

    items = [str(x).strip() for x in (meeting.action_items or []) if str(x).strip()]
    if not items:
        return 0
    store = BeanieKanbanStore(str(meeting.workspace_id))
    existing = await store.find_auto_tasks()
    existing_titles = {(t.get("title") or "").strip().lower() for t in existing}
    members = await workspace_member_users(str(meeting.workspace_id))
    mid = str(meeting.id)
    created = 0
    for raw in items[:12]:
        assignee_name, title = _parse_action_item_assignee(raw)
        if not title:
            continue
        if title.lower() in existing_titles:
            continue
        aid, display = _resolve_assignee_user_id(assignee_name, members)
        await store.insert_task(
            {
                "title": title[:200],
                "status": "todo",
                "assignee_id": aid,
                "assignee_name": display or assignee_name or None,
                "due_date": None,
                "source_meeting_id": mid,
                "synced_from_meeting_ids": [mid],
                "confidence": 0.55,
                "description": raw,
            }
        )
        existing_titles.add(title.lower())
        created += 1
    return created


@celery_app.task(name="app.workers.tasks.extraction.process_meeting_artifacts", bind=True, max_retries=3)
def process_meeting_artifacts(self, meeting_id: str) -> dict:
    return _run_async(_process_meeting_artifacts(meeting_id))


@celery_app.task(name="app.workers.tasks.extraction.extract_tasks_pass1", bind=True, max_retries=3)
def extract_tasks_pass1(self, workspace_id: str, fresh: bool = True) -> dict:
    return _run_async(_extract_tasks_pass1(workspace_id, fresh=fresh))


async def _extract_tasks_pass1(workspace_id: str, *, fresh: bool = True) -> dict:
    await _init_db()
    from app.services.kanban_automation import rebuild_kanban_for_workspace

    result = await rebuild_kanban_for_workspace(workspace_id, fresh=fresh)
    return {
        "workspace_id": workspace_id,
        "created": result.get("created", 0),
        "updated": result.get("updated", 0),
        "fresh": fresh,
    }


@celery_app.task(name="app.workers.tasks.extraction.move_tasks_pass2", bind=True, max_retries=3)
def move_tasks_pass2(self, workspace_id: str) -> dict:
    return _run_async(_move_tasks_pass2(workspace_id))


async def _move_tasks_pass2(workspace_id: str) -> dict:
    await _init_db()
    from app.models.meeting import Meeting, MeetingStatus

    meeting = await Meeting.find(
        Meeting.workspace_id == PydanticObjectId(workspace_id),
        Meeting.deleted_at == None,
        Meeting.status == MeetingStatus.ENDED,
    ).sort(-Meeting.created_at).first_or_none()
    if not meeting:
        return {"moved": 0}
    from app.services.kanban_automation import rebuild_kanban_for_workspace

    result = await rebuild_kanban_for_workspace(
        workspace_id, trigger_meeting_id=str(meeting.id), fresh=False
    )
    return {"moved": result.get("updated", 0)}


@celery_app.task(name="app.workers.tasks.extraction.process_meeting", bind=True, max_retries=3)
def process_meeting(self, meeting_id: str) -> dict:
    return process_meeting_artifacts.apply_async(args=[meeting_id]).get()


def _meeting_workspace_sync(meeting_id: str) -> str:
    return _run_async(_get_meeting_workspace(meeting_id))


async def _get_meeting_workspace(meeting_id: str) -> str:
    await _init_db()
    from app.models.meeting import Meeting
    meeting = await Meeting.get(PydanticObjectId(meeting_id))
    return str(meeting.workspace_id) if meeting else ""
