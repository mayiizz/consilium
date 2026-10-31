"""
Agentic Kanban automation pipeline.

Flow:
1) Triggered after meeting transcripts are available.
2) Cumulative history: LLM extracts only **confirmed** assignments (direct ownership or request + verbal
   acceptance). Suggestions / unconfirmed asks are not Kanban tasks.
3) First pass applies new/merged tasks to Mongo (match by title + assignee).
4) Second pass: current Kanban board (all auto tasks) + **latest meeting transcript only** → Groq returns
   column moves (todo / in_progress / in_review / done / blockers) grounded in verbatim evidence (validated in-process;
   not stored on the task document).
5) Informal action items from the latest pass are logged only (not persisted as tasks).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from groq import Groq

from app.core.config import get_settings
from app.services.kanban_beanie_store import KanbanBeanieStore, workspace_member_users

logger = logging.getLogger(__name__)

KANBAN_STATUSES = {"todo", "in_progress", "in_review", "done", "blockers"}
MAX_CHARS_PER_CHUNK = 30_000


def _settings():
    return get_settings()


def _kanban_extract_max_tokens() -> int:
    v = int(_settings().task_automation_extract_max_tokens or 3072)
    return max(512, min(v, 8192))


def _kanban_board_sync_max_tokens() -> int:
    v = int(_settings().task_automation_board_sync_max_tokens or 2048)
    return max(256, min(v, 8192))

# Higher = further along; used when merging duplicate extractions across chunks.
_STATUS_RANK = {"todo": 1, "in_progress": 2, "in_review": 3, "blockers": 4, "done": 5}

_WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


@dataclass
class ExtractedTask:
    title: str
    assignee: Optional[str]
    status: str
    due_date: Optional[str]
    blockers: List[str]
    confidence: float
    source_meeting_id: str
    evidence: str = ""  # verbatim transcript excerpt; in-memory for dedup/LLM only (not persisted as description)
    evidence_meeting_id: str = ""  # meeting section the evidence came from
    meeting_ordinal: int = 0  # 0 = oldest in bundle; higher = more recent


def _clean_transcript(text: str) -> str:
    """
    Normalize + clean transcription for task extraction.

    This preserves the original heuristic cleaning (timestamps/speaker tags),
    then applies deterministic filler/STT-error cleanup.
    """
    t = (text or "").strip()
    if not t:
        return ""
    # Remove common timestamp prefixes like [00:12:01], 00:12, 00:12:01
    t = re.sub(r"(?m)^\s*\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*", "", t)
    # Remove simple speaker tags like "John:" at line starts.
    t = re.sub(r"(?m)^\s*[A-Za-z][\w .'-]{0,40}:\s*", "", t)
    # Collapse repeated spaces.
    t = re.sub(r"[ \t]+", " ", t)

    from app.services.transcription_cleaning import clean_transcription_text

    return clean_transcription_text(t)


def _chunk_text(text: str, size: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    if len(text) <= size:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        # Prefer sentence/newline boundary
        if end < len(text):
            nl = text.rfind("\n", start, end)
            dot = text.rfind(". ", start, end)
            boundary = max(nl, dot)
            if boundary > start + int(size * 0.6):
                end = boundary + 1
        chunks.append(text[start:end].strip())
        start = end
    return [c for c in chunks if c]


def _normalize_status(s: Optional[str]) -> str:
    raw = (s or "").strip().lower()
    mapping = {
        "todo": "todo",
        "to_do": "todo",
        "to do": "todo",
        "open": "todo",
        "pending": "todo",
        "in progress": "in_progress",
        "in_progress": "in_progress",
        "doing": "in_progress",
        "working on": "in_progress",
        "review": "in_review",
        "in review": "in_review",
        "in_review": "in_review",
        "done": "done",
        "completed": "done",
        "complete": "done",
        "finished": "done",
        "finishing": "in_progress",
        "shipped": "done",
        "wrapped": "done",
        "closed": "done",
        "resolved": "done",
        "finalized": "done",
        "merged": "done",
        "delivered": "done",
        "blocked": "blockers",
        "blocker": "blockers",
        "blockers": "blockers",
        "stuck": "blockers",
    }
    return mapping.get(raw, "todo")


def _status_rank(status: str) -> int:
    return _STATUS_RANK.get(_normalize_status(status), 1)


def _next_weekday_on_or_after(anchor: date, target_weekday: int) -> date:
    """target_weekday: Monday=0 .. Sunday=6."""
    from app.services.due_date_intelligence import _next_weekday_on_or_after as _impl

    return _impl(anchor, target_weekday)


def _has_deadline_intent(text: str) -> bool:
    from app.services.due_date_intelligence import has_deadline_intent

    return has_deadline_intent(text)


def _infer_due_date_iso(text: str, anchor: date) -> Optional[str]:
    from app.services.due_date_intelligence import infer_due_date_iso

    return infer_due_date_iso(text, anchor)


def _resolve_task_due_date(
    raw_due: Optional[str],
    title: str,
    anchor: date,
    evidence: str = "",
) -> Optional[str]:
    from app.services.due_date_intelligence import resolve_task_due_date

    return resolve_task_due_date(raw_due, title, anchor, evidence)


def _collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _validate_transcript_evidence(evidence: str, chunk: str) -> str:
    """Keep only evidence that actually appears in the chunk (verbatim transcription)."""
    ev = (evidence or "").strip()
    if not ev or not chunk:
        return ""
    if ev in chunk:
        return ev
    ec, ch = _collapse_ws(ev), _collapse_ws(chunk)
    if ec and ec in ch:
        idx = ch.find(ec)
        if idx >= 0:
            return ch[idx : idx + len(ec)]
    return ""


def _fallback_transcript_snippet(chunk: str, assignee: str, title: str, max_chars: int = 1500) -> str:
    """Deterministic lines from transcript mentioning assignee / task — no LLM prose."""
    if not (chunk or "").strip():
        return ""
    parts = re.split(r"(?<=[.!?])\s+", chunk)
    a = (assignee or "").strip().lower()
    title_tokens = [w for w in re.split(r"\W+", (title or "").lower()) if len(w) > 2][:8]
    picked: List[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        pl = p.lower()
        if a and a in pl:
            picked.append(p)
        elif title_tokens and sum(1 for w in title_tokens if w in pl) >= 2:
            picked.append(p)
    text = " ".join(picked[:10]).strip()
    if not text:
        text = chunk.strip()[:max_chars]
    return text[:max_chars]


def _assignees_equivalent(a: Optional[str], b: Optional[str]) -> bool:
    if not a or not b:
        return False
    a, b = str(a).strip(), str(b).strip()
    if not a or not b:
        return False
    if a.lower() == b.lower():
        return True
    if a.lower() in b.lower() or b.lower() in a.lower():
        return True
    return _similarity(a, b) >= 0.86


_INTRO_ROLE_PATTERNS = re.compile(
    r"\b(i\s*'?m|i\s+am|my name is|my name's|call me|introduce myself|"
    r"nice to meet|good to meet|pleased to meet|a bit about me|little about myself|"
    r"i\s+(work on|handle|lead|manage|focus on|specialize in)|my role is|i'm the\s+\w+\s+(lead|manager|engineer))\b",
    re.I,
)
_ROLE_ONLY_TITLE = re.compile(
    r"^(backend|frontend|full[\s-]?stack|mobile|qa|quality assurance|testing|test|devops|sre|"
    r"ui|ux|product|data|ml|ai)(\s+(engineering|development|developer|dev|tester|engineer))?$",
    re.I,
)


def _is_team_placeholder(name: Optional[str]) -> bool:
    if name is None:
        return True
    s = str(name).strip().lower()
    if not s:
        return True
    return bool(
        re.match(
            r"^(team|everyone|all of us|the team|group|we|unspecified|tbd|general)\b",
            s,
        )
    )


def _is_intro_or_role_noise(title: str, evidence: str) -> bool:
    """Filter intros / icebreakers mistaken as tasks (e.g. 'backend development')."""
    t = (title or "").strip()
    blob = f"{t} {evidence or ''}"
    if _INTRO_ROLE_PATTERNS.search(blob):
        if not re.search(
            r"\b(will|must|need to|assigned|action item|deadline|due|deliver|ship|complete the|"
            r"follow up|by friday|eod)\b",
            blob,
            re.I,
        ):
            return True
    if _ROLE_ONLY_TITLE.match(t) and len(t) < 48:
        return True
    if re.search(r"\b(introduce yourself|round of intros|icebreaker)\b", blob, re.I):
        return True
    return False


def _infer_evidence_meeting_id(evidence: str, chunk: str, meeting_id_order: List[str]) -> str:
    """Map evidence snippet to the last meeting header seen before it in this chunk."""
    if not evidence or not meeting_id_order:
        return meeting_id_order[-1]
    probe = evidence[:120].strip()
    if not probe:
        return meeting_id_order[-1]
    pos = chunk.find(probe)
    if pos < 0:
        ec = _collapse_ws(probe)
        cc = _collapse_ws(chunk)
        if ec and ec in cc:
            pos = cc.find(ec)
        else:
            return meeting_id_order[-1]
    prefix = chunk[:pos] if pos >= 0 else chunk
    last = meeting_id_order[-1]
    for mid in meeting_id_order:
        if f"meeting_id={mid}" in prefix:
            last = mid
    return last


def _task_row_matches(a: ExtractedTask, b: ExtractedTask) -> bool:
    if _similarity(a.title, b.title) < 0.82:
        return False
    if _assignees_equivalent(a.assignee, b.assignee):
        return True
    if _is_team_placeholder(a.assignee) or _is_team_placeholder(b.assignee):
        return True
    if _similarity(a.title, b.title) >= 0.92:
        return True
    return False


def _dedup_extracted_global(rows: List[ExtractedTask]) -> List[ExtractedTask]:
    """
    Merge the same logical task across meetings. Later ordinals win for status, assignee, due_date.
    """
    rows_asc = sorted(rows, key=lambda x: x.meeting_ordinal)
    merged: List[ExtractedTask] = []
    for t in rows_asc:
        existing = next((m for m in merged if _task_row_matches(m, t)), None)
        if not existing:
            merged.append(
                ExtractedTask(
                    title=t.title,
                    assignee=t.assignee,
                    status=t.status,
                    due_date=t.due_date,
                    blockers=list(t.blockers),
                    confidence=t.confidence,
                    source_meeting_id=t.source_meeting_id,
                    evidence=t.evidence,
                    evidence_meeting_id=t.evidence_meeting_id,
                    meeting_ordinal=t.meeting_ordinal,
                )
            )
            continue
        if t.meeting_ordinal >= existing.meeting_ordinal:
            if _status_rank(t.status) >= _status_rank(existing.status):
                existing.status = t.status
            if t.assignee and (
                not existing.assignee
                or _is_team_placeholder(existing.assignee)
                or (t.meeting_ordinal > existing.meeting_ordinal and not _is_team_placeholder(t.assignee))
            ):
                if not _is_team_placeholder(t.assignee):
                    existing.assignee = t.assignee
                elif not existing.assignee or _is_team_placeholder(existing.assignee):
                    existing.assignee = t.assignee or existing.assignee
            if t.due_date and (
                not existing.due_date or t.meeting_ordinal > existing.meeting_ordinal
            ):
                existing.due_date = t.due_date
            if t.evidence:
                existing.evidence = _merge_transcript_description(existing.evidence, t.evidence)
            existing.meeting_ordinal = max(existing.meeting_ordinal, t.meeting_ordinal)
            existing.evidence_meeting_id = t.evidence_meeting_id or existing.evidence_meeting_id
            existing.source_meeting_id = t.source_meeting_id or existing.source_meeting_id
            if t.confidence > existing.confidence:
                existing.confidence = t.confidence
            if t.blockers:
                existing.blockers = sorted(set(existing.blockers + t.blockers))
        else:
            if t.evidence and t.evidence not in (existing.evidence or ""):
                existing.evidence = _merge_transcript_description(existing.evidence, t.evidence)
            if t.blockers:
                existing.blockers = sorted(set(existing.blockers + t.blockers))
    return merged


def _normalize_assignee(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    s = re.sub(r"\s+", " ", str(name)).strip()
    # "Arjun S." -> "Arjun"
    parts = s.split(" ")
    if len(parts) >= 2 and len(parts[-1]) <= 2:
        return parts[0]
    return s


def _parse_due_date_iso(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    s = str(date_str).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        # fallback date only
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return None


def _similarity(a: str, b: str) -> float:
    na = re.sub(r"\s+", " ", (a or "").strip().lower())
    nb = re.sub(r"\s+", " ", (b or "").strip().lower())
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _extract_json_list(raw: str) -> List[dict]:
    txt = (raw or "").strip()
    if txt.startswith("```"):
        lines = txt.split("\n")
        txt = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    data = json.loads(txt)
    if isinstance(data, dict) and "tasks" in data and isinstance(data["tasks"], list):
        return data["tasks"]
    if isinstance(data, list):
        return data
    return []


async def clean_orphaned_kanban_tasks(workspace_id: str) -> int:
    """Remove auto-generated tasks when synced meetings no longer exist."""
    store = KanbanBeanieStore(workspace_id)
    meetings = await store.list_meetings()
    valid_ids = {str(m["_id"]) for m in meetings}
    deleted = 0
    for t in await store.find_auto_tasks():
        mids = t.get("synced_from_meeting_ids") or []
        if not mids:
            sm = t.get("source_meeting_id")
            mids = [sm] if sm else []
        if not any(mid in valid_ids for mid in mids if mid):
            await store.delete_orphan_task(str(t["_id"]))
            deleted += 1
    return deleted


async def rebuild_kanban_from_meeting_history(
    workspace_id: str,
    trigger_meeting_id: Optional[str] = None,
    fresh: bool = False,
) -> dict:
    """
    Rebuild auto Kanban tasks: (1) cumulative transcripts → confirmed-assignment extraction + dedupe;
    (2) full board snapshot + latest meeting transcript → Groq column updates; informal items logged only.
    """
    store = KanbanBeanieStore(workspace_id)
    meetings = await store.list_meetings()
    if not meetings:
        deleted = await store.delete_auto_tasks()
        return {"meetings": 0, "created": 0, "updated": 0, "review_required": 0, "deleted": deleted}

    if fresh:
        await store.delete_auto_tasks()

    valid_meeting_ids = [str(m["_id"]) for m in meetings]
    latest_meeting_id = valid_meeting_ids[-1]
    meeting_by_id: Dict[str, dict] = {str(m["_id"]): m for m in meetings}
    meeting_ref_dates: Dict[str, date] = {}
    ordinal_by_meeting_id: Dict[str, int] = {}
    catalog_lines: List[str] = []
    bundle_sections: List[str] = []
    latest_meeting_cleaned = ""
    meeting_cleaned_by_id: Dict[str, str] = {}

    for i, m in enumerate(meetings):
        mid = str(m["_id"])
        ordinal_by_meeting_id[mid] = i
        mts = _meeting_assignment_timestamp(m)
        ref_d = mts.date() if isinstance(mts, datetime) else date.today()
        meeting_ref_dates[mid] = ref_d
        latest_flag = " LATEST" if mid == latest_meeting_id else ""
        catalog_lines.append(
            f"- meeting_id={mid} reference_date={ref_d.isoformat()} ordinal={i}{latest_flag}"
        )
        text = await store.meeting_transcript(mid)
        cleaned = _clean_transcript(text)
        if not cleaned:
            continue
        meeting_cleaned_by_id[mid] = cleaned
        if mid == latest_meeting_id:
            latest_meeting_cleaned = cleaned
        bundle_sections.append(
            f"=== Meeting meeting_id={mid} reference_date={ref_d.isoformat()} ordinal={i}{latest_flag} ===\n"
            f"{cleaned}"
        )

    meeting_catalog_text = "\n".join(catalog_lines)
    full_bundle = "\n\n".join(bundle_sections)

    created = 0
    updated = 0
    review_required = 0
    actions_taken: List[dict] = []
    existing: List[dict] = await store.find_auto_tasks()

    cfg = _settings()
    low_threshold = cfg.task_automation_low_confidence_threshold
    match_threshold = cfg.task_automation_match_threshold
    now = datetime.now(timezone.utc)
    members = await workspace_member_users(workspace_id)

    extracted_agg: List[ExtractedTask] = []
    chunks: List[str] = []
    if full_bundle.strip():
        use_rag = bool(cfg.kanban_rag_enabled)
        if use_rag:
            try:
                from app.services.transcript_rag import (
                    TranscriptRAGIndex,
                    build_fallback_tail,
                    retrieve_context_for_kanban,
                )

                idx = TranscriptRAGIndex.from_meeting_texts(
                    meeting_cleaned_by_id, ordinal_by_meeting_id
                )
                if idx is not None:
                    ctx, best_sc = retrieve_context_for_kanban(idx, latest_meeting_id)
                    min_sim = float(cfg.kanban_rag_min_similarity or 0.0)
                    tail_n = int(cfg.kanban_rag_fallback_tail_chars or 8000)
                    tail = build_fallback_tail(latest_meeting_cleaned, tail_n)
                    if len((ctx or "").strip()) < 400 or best_sc < min_sim:
                        if tail.strip():
                            fb = (
                                f"=== Meeting meeting_id={latest_meeting_id} "
                                f"(recent transcript fallback) ===\n{tail}"
                            )
                            ctx = f"{ctx}\n\n{fb}".strip() if (ctx or "").strip() else fb
                    if (ctx or "").strip():
                        chunks = [ctx.strip()]
                    else:
                        chunks = _chunk_text(full_bundle)
                else:
                    chunks = _chunk_text(full_bundle)
            except Exception as e:
                logger.warning("Kanban RAG failed, using legacy transcript chunks: %s", e)
                chunks = _chunk_text(full_bundle)
        else:
            chunks = _chunk_text(full_bundle)

        if not chunks:
            chunks = _chunk_text(full_bundle)

        # Append workspace document text so automation can use PRDs / notes.
        if bool(cfg.kanban_document_rag_enabled):
            try:
                from app.services.document_service import document_service

                docs_ctx = await document_service.list_extracted_texts(
                    workspace_id,
                    max_chars=int(cfg.kanban_document_rag_max_chars or 6000),
                )
                if docs_ctx.strip():
                    doc_block = f"=== Workspace documents (RAG context) ===\n{docs_ctx.strip()}"
                    if chunks:
                        chunks[0] = f"{chunks[0]}\n\n{doc_block}"
                    else:
                        chunks = [doc_block]
            except Exception as e:
                logger.warning("Kanban document RAG failed: %s", e)

        for chunk in chunks:
            subchunks = _chunk_text(chunk, 16_000) if len(chunk) > 18_000 else [chunk]
            for sc in subchunks:
                try:
                    extracted_agg.extend(
                        _extract_tasks_with_llm(
                            sc,
                            meeting_catalog_text,
                            latest_meeting_id,
                            meeting_ref_dates,
                            valid_meeting_ids,
                            ordinal_by_meeting_id,
                        )
                    )
                except Exception as e:
                    logger.exception(
                        "Task extraction failed workspace_id=%s cumulative chunk (len=%s): %s",
                        workspace_id,
                        len(sc),
                        e,
                    )

    extracted = _dedup_extracted_global(extracted_agg)
    extracted = [t for t in extracted if (t.assignee or "").strip()]

    for item in extracted:
        ev_mid = (item.evidence_meeting_id or item.source_meeting_id or latest_meeting_id).strip()
        if ev_mid not in meeting_by_id:
            ev_mid = latest_meeting_id
        sync_ids = {latest_meeting_id, ev_mid, (trigger_meeting_id or "").strip()}
        sync_ids.discard("")

        if item.confidence < low_threshold:
            review_required += 1
            await store.insert_review_queue(
                {
                    "meeting_id": latest_meeting_id,
                    "candidate": item.__dict__,
                    "reason": "low_confidence",
                }
            )
            actions_taken.append({"task": item.title, "action": "queued_for_review"})
            continue

        match, score = _best_match(item, existing)
        due_dt = _parse_due_date_iso(item.due_date)
        assignee_id, assignee_display = _resolve_assignee_user_id(item.assignee or "", members)
        display_assignee_name = assignee_display or (item.assignee or "")

        if _extract_match_accepted(item, match, score, match_threshold):
            updates: Dict[str, Any] = {}
            if _normalize_status(match.get("status")) != item.status:
                updates["status"] = item.status
            aid_changed = assignee_id != match.get("assignee_id")
            an_changed = (display_assignee_name or "").strip() != (match.get("assignee_name") or "").strip()
            if aid_changed or an_changed:
                updates["assignee_id"] = assignee_id
                updates["assignee_name"] = display_assignee_name
            if due_dt is not None and (match.get("due_date") or None) != due_dt:
                updates["due_date"] = due_dt
                updates["due_date_source"] = "transcript"
            elif not match.get("due_date"):
                from app.services.due_date_intelligence import infer_due_near_assignee

                body = meeting_cleaned_by_id.get(ev_mid) or meeting_cleaned_by_id.get(latest_meeting_id) or ""
                anchor = meeting_ref_dates.get(ev_mid, meeting_ref_dates[latest_meeting_id])
                near = infer_due_near_assignee(
                    body, display_assignee_name or item.assignee or "", item.title, anchor
                )
                parsed_near = _parse_due_date_iso(near) if near else None
                if parsed_near:
                    updates["due_date"] = parsed_near
                    updates["due_date_source"] = "transcript"
            # Do not clear an existing due date when extract returns None
            had_field_changes = bool(updates)
            add_each = [x for x in sync_ids if x]
            set_doc = {**updates, "last_activity_at": now}
            await store.update_task(str(match["_id"]), set_doc, add_meeting_ids=add_each)
            match.update(set_doc)
            sfm = set(match.get("synced_from_meeting_ids") or [])
            sfm.update(add_each)
            match["synced_from_meeting_ids"] = list(sfm)
            if had_field_changes:
                updated += 1
            actions_taken.append({"task": item.title, "action": "updated", "score": score})
            continue

        src_mid = (item.source_meeting_id or ev_mid or latest_meeting_id).strip()
        if src_mid not in meeting_by_id:
            src_mid = latest_meeting_id
        new_doc = {
            "title": item.title,
            "status": item.status if item.status in KANBAN_STATUSES else "todo",
            "assignee_id": assignee_id,
            "assignee_name": display_assignee_name,
            "due_date": due_dt,
            "due_date_source": "transcript" if due_dt else None,
            "source_meeting_id": src_mid,
            "synced_from_meeting_ids": sorted(sync_ids),
            "confidence": item.confidence,
        }
        # If extract missed the due phrase, scan nearby transcript lines
        if not due_dt:
            from app.services.due_date_intelligence import infer_due_near_assignee

            body = meeting_cleaned_by_id.get(ev_mid) or meeting_cleaned_by_id.get(latest_meeting_id) or ""
            anchor = meeting_ref_dates.get(ev_mid, meeting_ref_dates[latest_meeting_id])
            near = infer_due_near_assignee(body, display_assignee_name or item.assignee or "", item.title, anchor)
            if near:
                parsed_near = _parse_due_date_iso(near)
                if parsed_near:
                    new_doc["due_date"] = parsed_near
                    new_doc["due_date_source"] = "transcript"
        tid = await store.insert_task(new_doc)
        row = {**new_doc, "_id": tid}
        created += 1
        existing.append(row)
        actions_taken.append({"task": item.title, "action": "created"})

    board_sync_result: dict = {"task_updates": [], "informal_action_items": []}
    if (latest_meeting_cleaned or "").strip():
        board_rows = await store.find_auto_tasks()
        snap = _board_snapshot_for_llm(board_rows)
        lt_send = latest_meeting_cleaned
        if bool(cfg.kanban_rag_board_sync_enabled):
            try:
                from app.services.transcript_rag import retrieve_board_sync_context

                rag_ctx, rag_sc = retrieve_board_sync_context(
                    latest_meeting_id, latest_meeting_cleaned
                )
                min_sim = float(cfg.kanban_rag_min_similarity or 0.0)
                if (rag_ctx or "").strip() and rag_sc >= min_sim and len((rag_ctx or "").strip()) > 200:
                    lt_send = rag_ctx.strip()
            except Exception as e:
                logger.warning("Board sync RAG skipped, using full latest transcript: %s", e)
        if len(lt_send) > 120_000:
            lt_send = lt_send[:120_000]
        try:
            board_sync_result = _groq_sync_board_with_latest_transcript(
                lt_send,
                meeting_ref_dates[latest_meeting_id],
                latest_meeting_id,
                snap,
            )
        except Exception as e:
            logger.exception("Board sync Groq failed workspace_id=%s: %s", workspace_id, e)

        add_mids = [latest_meeting_id, (trigger_meeting_id or "").strip()]
        add_mids = [x for x in add_mids if x]
        evidence_source = latest_meeting_cleaned

        for u in board_sync_result.get("task_updates") or []:
            tid = str(u.get("task_id") or "").strip()
            if not tid:
                continue
            ev = str(u.get("transcript_evidence") or "").strip()
            if not _validate_transcript_evidence(ev, evidence_source):
                continue
            try:
                conf_u = float(u.get("confidence") if u.get("confidence") is not None else 0.65)
            except (TypeError, ValueError):
                conf_u = 0.65
            if conf_u < low_threshold:
                continue
            doc = await store.find_task(tid, auto_only=True)
            if not doc:
                continue

            new_st = _normalize_status(u.get("new_status"))
            updates2: Dict[str, Any] = {}
            if _normalize_status(doc.get("status")) != new_st:
                updates2["status"] = new_st

            raw_du = u.get("due_date")
            ev_u = str(u.get("transcript_evidence") or "").strip()
            ref_d = meeting_ref_dates[latest_meeting_id]
            if raw_du is not None and str(raw_du).strip() and str(raw_du).strip().lower() not in (
                "null",
                "none",
            ):
                due_iso = _resolve_task_due_date(
                    str(raw_du).strip(),
                    str(doc.get("title") or ""),
                    ref_d,
                    ev_u,
                )
                if due_iso:
                    new_dt = _parse_due_date_iso(due_iso)
                    if new_dt:
                        old_key = _task_due_for_snapshot(doc.get("due_date"))
                        new_key = new_dt.date().isoformat()
                        if old_key != new_key:
                            updates2["due_date"] = new_dt
            elif ev_u and _has_deadline_intent(ev_u):
                due_iso = _resolve_task_due_date(None, str(doc.get("title") or ""), ref_d, ev_u)
                if due_iso:
                    new_dt = _parse_due_date_iso(due_iso)
                    if new_dt and _task_due_for_snapshot(doc.get("due_date")) != due_iso:
                        updates2["due_date"] = new_dt

            blockers_raw = u.get("blockers") or []
            blocker_parts = [str(x).strip() for x in blockers_raw if str(x).strip()]
            if blocker_parts or new_st == "blockers":
                new_blocker_reason = "; ".join(blocker_parts) if blocker_parts else None
                if new_blocker_reason and (doc.get("blocker_reason") or "").strip() != new_blocker_reason:
                    updates2["blocker_reason"] = new_blocker_reason

            if not updates2:
                continue

            had_field_updates = bool(updates2)
            set_doc2 = {**updates2, "last_activity_at": now}
            await store.update_task(tid, set_doc2, add_meeting_ids=add_mids)
            if had_field_updates:
                updated += 1
            actions_taken.append(
                {
                    "task_id": tid,
                    "action": "latest_meeting_board_sync",
                    "fields": list(updates2.keys()),
                }
            )

    await store.write_run_log(
        latest_meeting_id,
        {
            "trigger_meeting_id": trigger_meeting_id,
            "cumulative_bundle_chars": len(full_bundle),
            "chunks": len(chunks),
            "extracted_count": len(extracted),
            "actions": actions_taken,
            "board_sync_informal_action_items": board_sync_result.get("informal_action_items") or [],
            "board_sync_task_updates_returned": len(board_sync_result.get("task_updates") or []),
        },
    )

    deleted = await clean_orphaned_kanban_tasks(workspace_id)
    try:
        from app.services.transcript_task_reconciliation import reconcile_workspace_tasks

        await reconcile_workspace_tasks(workspace_id, trigger_meeting_id=trigger_meeting_id)
    except Exception:
        logger.exception("Reconciliation failed workspace_id=%s", workspace_id)

    return {
        "meetings": len(meetings),
        "created": created,
        "updated": updated,
        "review_required": review_required,
        "deleted": deleted,
        "valid_meeting_ids": valid_meeting_ids,
    }


async def rebuild_kanban_for_workspace(
    workspace_id: str,
    *,
    trigger_meeting_id: Optional[str] = None,
    fresh: bool = False,
) -> dict:
    return await rebuild_kanban_from_meeting_history(
        workspace_id,
        trigger_meeting_id=trigger_meeting_id,
        fresh=fresh,
    )


validate_transcript_evidence = _validate_transcript_evidence


def _resolve_assignee_user_id(assignee_display: str, members: List[dict]) -> Tuple[Optional[str], str]:
    """Match transcript assignee to a workspace member. Returns (user_id or None, display name)."""
    ad = (assignee_display or "").strip()
    if not ad:
        return None, ""
    norm = _normalize_assignee(ad) or ad
    best_id: Optional[str] = None
    best_score = 0.0
    best_name = ad
    for m in members:
        mn = m["name"]
        s = _similarity(norm, mn)
        if norm.lower() in mn.lower() or mn.lower().split()[0] == norm.lower():
            s = max(s, 0.88)
        if s > best_score:
            best_score, best_id, best_name = s, m["id"], mn
    if best_score >= 0.72 and best_id:
        return best_id, best_name
    return None, ad


def _meeting_assignment_timestamp(m: dict) -> datetime:
    """Prefer real meeting schedule/start/end — never invent a random future date."""
    for key in ("ended_at", "started_at", "scheduled_at"):
        val = m.get(key)
        if val:
            return val
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get_groq_client() -> Groq:
    s = _settings()
    if not s.groq_api_key:
        raise ValueError("GROQ_API_KEY is not set")
    return Groq(api_key=s.groq_api_key)


def _automation_model_candidates() -> List[str]:
    s = _settings()
    out: List[str] = []
    for m in (
        (s.task_automation_model or "").strip(),
        (s.groq_summary_model or "").strip(),
        (s.groq_model or "").strip(),
        "openai/gpt-oss-120b",
        "qwen/qwen3-32b",
    ):
        if m and m not in out:
            out.append(m)
    return out


def _groq_chat_create(client: Groq, *, messages: list, temperature: float, max_tokens: int, json_mode: bool = True):
    """Try configured automation models; on model_not_found fall through to the next."""
    last_err: Exception | None = None
    for model in _automation_model_candidates():
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "model_not_found" in msg or "does not exist" in msg or "404" in msg:
                logger.warning("Kanban Groq model unavailable (%s); trying next", model)
                continue
            if json_mode:
                logger.warning("Kanban Groq JSON mode failed on %s (%s); retrying without", model, e)
                try:
                    kwargs.pop("response_format", None)
                    return client.chat.completions.create(**kwargs)
                except Exception as e2:
                    last_err = e2
                    msg2 = str(e2).lower()
                    if "model_not_found" in msg2 or "does not exist" in msg2 or "404" in msg2:
                        logger.warning("Kanban Groq model unavailable (%s); trying next", model)
                        continue
                    raise
            raise
    if last_err:
        raise last_err
    raise RuntimeError("No Groq automation model configured")


def _merge_transcript_description(old: Optional[str], new_ev: str) -> str:
    """Merge verbatim evidence snippets on ExtractedTask only (not persisted to Mongo description)."""
    o = (old or "").strip()
    n = (new_ev or "").strip()
    if not n:
        return o
    if not o:
        return n
    if n in o:
        return o
    if o in n:
        return n
    return (o + "\n\n—\n" + n).strip()


def _strip_json_fences(txt: str) -> str:
    t = (txt or "").strip()
    if t.startswith("```"):
        lines = t.split("\n")
        t = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])
    return t.strip()


def _task_due_for_snapshot(due: Any) -> Optional[str]:
    if due is None:
        return None
    if isinstance(due, datetime):
        return due.date().isoformat()
    if isinstance(due, date):
        return due.isoformat()
    s = str(due).strip()
    return s[:10] if len(s) >= 10 and s[4] == "-" else (s or None)


def _board_snapshot_for_llm(tasks: List[dict]) -> List[dict]:
    out: List[dict] = []
    for t in tasks:
        out.append(
            {
                "task_id": str(t.get("_id", "")),
                "title": (t.get("title") or "").strip(),
                "assignee_name": (t.get("assignee_name") or "").strip(),
                "status": _normalize_status(t.get("status")),
                "due_date": _task_due_for_snapshot(t.get("due_date")),
            }
        )
    return out


def _parse_board_sync_response(raw: str) -> dict:
    txt = _strip_json_fences(raw or "")
    for candidate in (txt,):
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {"task_updates": [], "informal_action_items": []}


def _groq_sync_board_with_latest_transcript(
    latest_transcript: str,
    reference_date: date,
    latest_meeting_id: str,
    board_snapshot: List[dict],
) -> dict:
    """
    Single Groq JSON call: full Kanban snapshot + latest meeting transcript → column updates + informal items.
    """
    payload = {
        "latest_meeting_id": latest_meeting_id,
        "reference_date": reference_date.isoformat(),
        "kanban_board": board_snapshot,
        "latest_meeting_transcript": latest_transcript,
    }
    sys_prompt = """You are updating a Kanban board from the LATEST meeting only.

Input JSON (in the user message) contains:
- kanban_board: every task already on the board (task_id, title, assignee_name, status, due_date).
- latest_meeting_transcript: transcript for the most recent meeting only (may be a retrieved excerpt of the most relevant lines, not the full recording).
- reference_date: calendar date of that meeting (for interpreting "today", "tomorrow", "this Friday" in due dates).

Output ONE JSON object only, no markdown:
{
  "task_updates": [
    {
      "task_id": "string (must match a task_id from kanban_board)",
      "new_status": "todo" | "in_progress" | "in_review" | "done" | "blockers",
      "due_date": "YYYY-MM-DD" | null,
      "blockers": ["string"],
      "transcript_evidence": "verbatim contiguous excerpt from latest_meeting_transcript only",
      "confidence": 0.0-1.0
    }
  ],
  "informal_action_items": ["string", ...]
}

Rules for task_updates:
- Only include a task if the latest meeting clearly discusses THAT task (same work as title/assignee) and justifies a change.
- Move to "done" only when the transcript clearly states completion (done, shipped, merged, finished, completed, etc.) for that work.
- Move to "in_progress" when someone states they are actively working on it.
- Move to "blockers" when blocked / stuck / waiting on external dependency is explicit.
- Move to "todo" when reset to not started or newly clarified as not done (rare).
- You may update due_date ONLY when transcript_evidence itself states a deadline for that task (by Friday, tomorrow, EOD, due …). Otherwise leave due_date null — never invent or assume dates.
- transcript_evidence MUST be copied verbatim from latest_meeting_transcript. If you cannot quote it, do not emit the update.
- Do not invent tasks; do not remove tasks. Omit tasks with no change.
- confidence reflects how explicit the transcript is.

Rules for informal_action_items:
- Ideas, suggestions, "we should", "maybe", unassigned asks, or requests with NO clear acceptance from the named person → list here as short strings.
- Do NOT duplicate work that is already covered by task_updates.

If nothing changes, return {"task_updates":[],"informal_action_items":[]}."""

    user_content = json.dumps(payload, ensure_ascii=False)
    provider = (_settings().task_automation_provider or "groq").strip().lower()
    if provider != "groq":
        logger.warning("Unsupported TASK_AUTOMATION_PROVIDER=%s, fallback to groq", provider)
    client = _get_groq_client()
    resp = _groq_chat_create(
        client,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        max_tokens=_kanban_board_sync_max_tokens(),
        json_mode=True,
    )
    raw = resp.choices[0].message.content or "{}"
    return _parse_board_sync_response(raw)


def _extract_tasks_with_llm(
    chunk_text: str,
    meeting_catalog_text: str,
    latest_meeting_id: str,
    meeting_ref_dates: Dict[str, date],
    meeting_id_order: List[str],
    ordinal_by_meeting_id: Dict[str, int],
) -> List[ExtractedTask]:
    """
    Extraction over a chunk that may contain MULTIPLE meetings (cumulative project transcript).
    """
    catalog_dates = "\n".join(
        f"  - meeting_id={mid}: reference_date={meeting_ref_dates[mid].isoformat()} (use this date as 'today' for phrases like tomorrow/EOD in THAT meeting's section)"
        for mid in meeting_id_order
        if mid in meeting_ref_dates
    )
    schema_prompt = """You extract ONLY **confirmed Kanban tasks** from meeting transcript excerpts (possibly from several meetings, oldest-first context in the user message).
A row belongs on the Kanban board only when there is **clear individual ownership AND commitment**.

Output ONE JSON object only: {"tasks":[...]}

Each task:
{
  "title": string (concrete deliverable, not a job title or stack name),
  "assignee": string (one person's name as spoken — NEVER "Team", "we", "someone", or a role label),
  "confirmation_basis": "direct_assignment" | "request_and_acceptance",
  "status": "todo"|"in_progress"|"in_review"|"done"|"blockers",
  "due_date": "YYYY-MM-DD"|null,
  "blockers": string[],
  "transcript_evidence": string,
  "evidence_meeting_id": string,
  "confidence": number
}

QUALIFIES as confirmed (include):
- **direct_assignment**: Someone is explicitly given ownership (e.g. "Amit will handle the backend", "I'll own the API", "Sarah's on the deck for Friday").
- **request_and_acceptance**: A direct request to a named person AND that same person clearly accepts in the same meeting (e.g. "Amit, can you take the designing?" → "Yes" / "Sure, I'll do it" / "On it"). transcript_evidence must cover BOTH parts or the clearest joint snippet.

DO NOT output (these are informal action items, not Kanban tasks):
- General discussion, ideas, "we should", "it would be nice", "maybe someone can" with no named assignee + commitment.
- A request to a person who does not accept or deflects.
- Assigning work to a role with no named person ("the backend team should…") unless a specific person is named and commits.
- Intros / icebreakers / "my role is X" with no task commitment.

Cross-meeting:
- **Latest meeting wins** when the same work is discussed again.
- If meeting 1 only had a vague idea but meeting 2 has a **named person committing**, output ONE merged task with evidence from the meeting where commitment became clear.

The user message contains the meeting catalog, per-meeting reference dates, latest meeting_id, and transcript excerpt(s) (sections marked with === Meeting meeting_id=... ===).

transcript_evidence: verbatim contiguous excerpt from those transcript sections only (no paraphrase). Include enough to show ownership/commitment.

evidence_meeting_id: meeting_id from the === Meeting ... meeting_id=... === header for the section containing transcript_evidence.

EXCLUDE: standalone intros; titles that are only role labels (e.g. "Backend development") with intro context.

due_date: null unless transcript_evidence for THIS task states a deadline (by Friday, tomorrow, EOD, "I'll finish X today", "by end of today"). Never invent dates from ambient words like "today is Day 1". When a relative phrase is present, convert using reference_date of evidence_meeting_id.

confidence: how explicit the commitment is (0.0–1.0)."""
    provider = (_settings().task_automation_provider or "groq").strip().lower()
    if provider != "groq":
        logger.warning("Unsupported TASK_AUTOMATION_PROVIDER=%s, fallback to groq", provider)
    client = _get_groq_client()
    user_blob = (
        f"Meeting catalog:\n{meeting_catalog_text}\n\n"
        f"Per-meeting reference dates:\n{catalog_dates}\n\n"
        f"Latest meeting_id: {latest_meeting_id}\n\n"
        f"=== Transcript excerpt(s) for task extraction ===\n{chunk_text}"
    )
    resp = _groq_chat_create(
        client,
        messages=[
            {"role": "system", "content": schema_prompt},
            {"role": "user", "content": user_blob},
        ],
        temperature=0.1,
        max_tokens=_kanban_extract_max_tokens(),
        json_mode=True,
    )
    raw = resp.choices[0].message.content or '{"tasks":[]}'
    rows = _extract_json_list(raw)
    out: List[ExtractedTask] = []
    for r in rows:
        title  = str(r.get("title") or "").strip()
        if not title:
            continue
        assignee_raw = r.get("assignee")
        aname = ""
        if assignee_raw is not None and str(assignee_raw).strip():
            aname = _normalize_assignee(assignee_raw) or str(assignee_raw).strip()
        if not aname or _is_team_placeholder(aname):
            continue
        basis = str(r.get("confirmation_basis") or "").strip().lower()
        if basis not in ("direct_assignment", "request_and_acceptance"):
            continue
        conf_raw = r.get("confidence", 0.7)
        try:
            conf = max(0.0, min(1.0, float(conf_raw)))
        except (TypeError, ValueError):
            conf = 0.7
        rd = r.get("due_date")
        raw_due = str(rd).strip() if rd is not None and str(rd).strip() else None
        ev_raw = r.get("transcript_evidence")
        evidence = _validate_transcript_evidence(str(ev_raw or "").strip(), chunk_text)
        if not evidence:
            evidence = _fallback_transcript_snippet(chunk_text, aname, title)
        if not (evidence or "").strip():
            continue
        ev_mid = str(r.get("evidence_meeting_id") or r.get("meeting_id") or "").strip()
        if ev_mid not in meeting_ref_dates:
            ev_mid = _infer_evidence_meeting_id(evidence, chunk_text, meeting_id_order)
        ord_key = ordinal_by_meeting_id.get(ev_mid, ordinal_by_meeting_id.get(latest_meeting_id, 0))
        anchor = meeting_ref_dates.get(ev_mid, meeting_ref_dates[latest_meeting_id])
        due_iso = _resolve_task_due_date(raw_due, title, anchor, evidence)
        if _is_intro_or_role_noise(title, evidence):
            continue
        out.append(
            ExtractedTask(
                title=title,
                assignee=aname,
                status=_normalize_status(r.get("status")),
                due_date=due_iso,
                blockers=[str(x).strip() for x in (r.get("blockers") or []) if str(x).strip()],
                confidence=conf,
                source_meeting_id=ev_mid,
                evidence=evidence.strip(),
                evidence_meeting_id=ev_mid,
                meeting_ordinal=ord_key,
            )
        )
    return out


def _best_match(extracted: ExtractedTask, existing_tasks: List[dict]) -> Tuple[Optional[dict], float]:
    best, score = None, 0.0
    for t in existing_tasks:
        s = _similarity(extracted.title, t.get("title") or "")
        t_an = (t.get("assignee_name") or "").strip()
        ex_an = (extracted.assignee or "").strip()
        if ex_an and t_an:
            if _assignees_equivalent(extracted.assignee, t_an):
                s += 0.24
            elif _similarity(extracted.assignee, t_an) >= 0.72:
                s += 0.1
        if _is_team_placeholder(extracted.assignee) or _is_team_placeholder(t_an):
            if s >= 0.5:
                s += 0.22
        if s > score:
            score, best = s, t
    return best, score


def _extract_match_accepted(
    extracted: ExtractedTask, match: Optional[dict], score: float, threshold: float
) -> bool:
    if not match:
        return False
    if score >= threshold:
        return True
    if score >= 0.64 and _similarity(extracted.title, match.get("title") or "") >= 0.9:
        t_an = (match.get("assignee_name") or "").strip()
        if extracted.assignee and t_an and _assignees_equivalent(extracted.assignee, t_an):
            return True
    tit_sim = _similarity(extracted.title, match.get("title") or "")
    t_an = (match.get("assignee_name") or "").strip()
    if score >= 0.62 and tit_sim >= 0.86:
        if _is_team_placeholder(extracted.assignee) or _is_team_placeholder(t_an):
            return True
    return False

