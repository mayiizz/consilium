import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

from beanie import PydanticObjectId
from fastapi import HTTPException, UploadFile, status

from app.integrations.groq import GroqLLMService
from app.models.meeting import (
    Meeting,
    MeetingAttendee,
    MeetingPlatform,
    MeetingStatus,
    TranscriptChunk,
)
from app.models.user import User
from app.schemas import (
    CreateMeetingRequest,
    MeetingAttendeeResponse,
    MeetingResponse,
    MeetingSummaryResponse,
    TranscriptChunkResponse,
    TranscriptResponse,
    UpdateMeetingRequest,
)
from app.core.websocket_manager import ws_manager
from app.services.permissions import get_workspace_or_404, require_workspace_lead, require_workspace_member

logger = get_logger(__name__)


def _avatar_url(seed: str) -> str:
    return f"https://api.dicebear.com/7.x/avataaars/svg?seed={seed}"


async def _resolve_attendees(meeting: Meeting) -> List[MeetingAttendeeResponse]:
    result: List[MeetingAttendeeResponse] = []
    for a in meeting.attendees:
        if not a.user_id:
            continue
        user = await User.get(a.user_id)
        if not user:
            continue
        result.append(
            MeetingAttendeeResponse(
                user_id=str(a.user_id),
                name=user.name,
                avatar=user.avatar or _avatar_url(user.name),
                join_time=a.join_time,
                leave_time=a.leave_time,
            )
        )
    return result


async def _meeting_response(meeting: Meeting) -> MeetingResponse:
    attendees = await _resolve_attendees(meeting)
    return MeetingResponse(
        id=str(meeting.id),
        workspace_id=str(meeting.workspace_id),
        title=meeting.title,
        description=meeting.description,
        platform=meeting.platform.value if meeting.platform else None,
        status=meeting.status.value,
        video_link=meeting.video_link,
        meeting_url=meeting.video_link,
        scheduled_at=meeting.scheduled_at,
        started_at=meeting.started_at,
        ended_at=meeting.ended_at,
        duration=meeting.duration,
        summary=meeting.summary,
        action_items=meeting.action_items,
        key_decisions=meeting.key_decisions,
        attendees=attendees,
        transcript_count=len(meeting.transcript_chunks),
        created_by=meeting.created_by,
        is_upload=meeting.is_upload,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


def _chunk_to_response(c: TranscriptChunk) -> TranscriptChunkResponse:
    speaker = c.speaker
    text = c.text
    if not (speaker or "").strip():
        from app.services.transcript_speaker_parse import parse_speaker_line

        parsed_speaker, parsed_body = parse_speaker_line(text)
        if parsed_speaker:
            speaker = parsed_speaker
            text = parsed_body
    return TranscriptChunkResponse(
        chunk_id=c.chunk_id,
        timestamp=c.timestamp,
        audio_offset_ms=c.audio_offset_ms,
        text=text,
        speaker=speaker,
        confidence=c.confidence,
        source=c.source,
        speaker_label=speaker,
        stt_confidence=c.confidence,
    )


def _parse_platform(value: Optional[str]) -> MeetingPlatform:
    if not value:
        return MeetingPlatform.JITSI
    try:
        return MeetingPlatform(value)
    except ValueError:
        return MeetingPlatform.CUSTOM


class MeetingService:
    def __init__(self) -> None:
        self.llm = GroqLLMService()

    async def create(
        self, workspace_id: str, user_id: PydanticObjectId, data: CreateMeetingRequest
    ) -> MeetingResponse:
        await require_workspace_lead(workspace_id, user_id)
        await get_workspace_or_404(workspace_id)

        platform = _parse_platform(data.platform)
        video_link = data.video_link
        if not video_link and data.generate_link:
            video_link = f"https://meet.jit.si/consilium-{uuid.uuid4()}"

        scheduled_at = data.scheduled_at
        if data.meeting_type == "instant" and not scheduled_at:
            scheduled_at = datetime.now(timezone.utc)

        meeting = Meeting(
            workspace_id=PydanticObjectId(workspace_id),
            title=data.title,
            description=data.description,
            platform=platform,
            video_link=video_link,
            scheduled_at=scheduled_at,
            created_by=str(user_id),
        )
        await meeting.insert()
        return await _meeting_response(meeting)

    async def list_for_workspace(self, workspace_id: str, user_id: PydanticObjectId) -> List[MeetingResponse]:
        await require_workspace_member(workspace_id, user_id)
        meetings = await Meeting.find(
            Meeting.workspace_id == PydanticObjectId(workspace_id),
            Meeting.deleted_at == None,
        ).sort(-Meeting.created_at).to_list()
        return [await _meeting_response(m) for m in meetings]

    async def get(self, meeting_id: str, user_id: PydanticObjectId) -> MeetingResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_member(str(meeting.workspace_id), user_id)
        return await _meeting_response(meeting)

    async def update(
        self, meeting_id: str, user_id: PydanticObjectId, data: UpdateMeetingRequest
    ) -> MeetingResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_lead(str(meeting.workspace_id), user_id)
        if data.title:
            meeting.title = data.title
        if data.description is not None:
            meeting.description = data.description
        if data.video_link is not None:
            meeting.video_link = data.video_link
        if data.scheduled_at is not None:
            meeting.scheduled_at = data.scheduled_at
        if data.platform is not None:
            meeting.platform = _parse_platform(data.platform)
        meeting.updated_at = datetime.now(timezone.utc)
        await meeting.save()
        return await _meeting_response(meeting)

    async def delete(self, meeting_id: str, user_id: PydanticObjectId) -> int:
        """Soft-delete meeting and related tasks."""
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_lead(str(meeting.workspace_id), user_id)
        if meeting.status == MeetingStatus.LIVE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Stop the meeting before deleting it",
            )
        removed_tasks = await self._cascade_delete_related(meeting)
        meeting.soft_delete()
        await meeting.save()

        workspace_id = str(meeting.workspace_id)
        try:
            from app.services.kanban_automation import rebuild_kanban_for_workspace

            await rebuild_kanban_for_workspace(workspace_id, fresh=False)
        except Exception:
            logger.exception(
                "Kanban rebuild failed after meeting delete",
                extra={"meeting_id": str(meeting.id), "workspace_id": workspace_id},
            )

        return removed_tasks

    async def _soft_delete_task(self, task) -> None:
        task.soft_delete()
        await task.save()

    async def _cascade_delete_related(self, meeting: Meeting) -> int:
        from app.models.task import Task

        meeting_id = str(meeting.id)
        meeting_oid = meeting.id

        tasks_by_meeting = await Task.find(
            Task.meeting_id == meeting_oid,
            Task.deleted_at == None,
        ).to_list()
        tasks_by_source = await Task.find(
            Task.source_meeting_id == meeting_oid,
            Task.deleted_at == None,
        ).to_list()
        tasks_by_sync = await Task.find(
            Task.workspace_id == meeting.workspace_id,
            Task.deleted_at == None,
            Task.synced_from_meeting_ids == meeting_id,
        ).to_list()

        seen: set[str] = set()
        removed = 0
        for task in tasks_by_meeting + tasks_by_source + tasks_by_sync:
            tid = str(task.id)
            if tid in seen:
                continue
            seen.add(tid)
            await self._soft_delete_task(task)
            removed += 1

        return removed

    async def start(self, meeting_id: str, user_id: PydanticObjectId) -> MeetingResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_lead(str(meeting.workspace_id), user_id)
        if meeting.status in (MeetingStatus.LIVE, MeetingStatus.READY):
            return await _meeting_response(meeting)
        if meeting.status not in (MeetingStatus.SCHEDULED,):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Meeting cannot be started")
        meeting.status = MeetingStatus.READY
        meeting.updated_at = datetime.now(timezone.utc)
        await meeting.save()
        return await _meeting_response(meeting)

    async def cancel(self, meeting_id: str, user_id: PydanticObjectId) -> MeetingResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_lead(str(meeting.workspace_id), user_id)
        if meeting.status in (MeetingStatus.ENDED, MeetingStatus.LIVE):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Meeting cannot be cancelled")
        meeting.status = MeetingStatus.CANCELLED
        meeting.updated_at = datetime.now(timezone.utc)
        await meeting.save()
        return await _meeting_response(meeting)

    async def stop(self, meeting_id: str, user_id: PydanticObjectId) -> MeetingResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_lead(str(meeting.workspace_id), user_id)
        now = datetime.now(timezone.utc)
        meeting.status = MeetingStatus.ENDED
        meeting.ended_at = now
        if meeting.started_at:
            started = meeting.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            meeting.duration = int((now - started).total_seconds())
        meeting.updated_at = now
        await meeting.save()

        await self._process_artifacts_sync(meeting_id)

        return await _meeting_response(meeting)

    async def reprocess(self, meeting_id: str, user_id: PydanticObjectId) -> MeetingSummaryResponse:
        """Regenerate summary, action items, decisions, and tasks from transcript."""
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_lead(str(meeting.workspace_id), user_id)
        if meeting.status != MeetingStatus.ENDED:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Only ended meetings can be reprocessed",
            )
        if not meeting.full_transcript().strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Meeting has no transcript to process",
            )
        # Summary-only reprocess avoids duplicate task-extraction Groq calls (rate limits).
        await self._process_artifacts_sync(meeting_id)
        meeting = await self._get_meeting(meeting_id)
        return MeetingSummaryResponse(
            summary=meeting.summary,
            action_items=meeting.action_items,
            key_decisions=meeting.key_decisions,
        )

    _artifact_locks: dict[str, asyncio.Lock] = {}

    async def _process_artifacts_sync(self, meeting_id: str) -> None:
        lock = self._artifact_locks.setdefault(meeting_id, asyncio.Lock())
        async with lock:
            from app.workers.tasks.extraction import _process_meeting_artifacts
            await _process_meeting_artifacts(meeting_id)

    async def upload(
        self, meeting_id: str, user_id: PydanticObjectId, file: UploadFile
    ) -> MeetingResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_lead(str(meeting.workspace_id), user_id)
        content = await file.read()
        from app.services.file_text_extractor import extract_text_from_upload

        text, kind = await extract_text_from_upload(
            content,
            filename=file.filename,
            content_type=file.content_type,
        )
        from app.services.transcript_speaker_parse import transcript_lines_to_chunks

        parsed = transcript_lines_to_chunks(text)
        chunks = [
            TranscriptChunk(
                chunk_id=str(uuid.uuid4()),
                speaker=row.get("speaker"),
                text=row["text"],
                source=f"upload:{kind}",
                audio_offset_ms=int(row.get("audio_offset_ms") or 0),
            )
            for row in parsed
            if (row.get("text") or "").strip()
        ]
        if not chunks:
            chunks = [
                TranscriptChunk(
                    chunk_id=str(uuid.uuid4()),
                    text=text[:8000] if text else "[Empty upload]",
                    source=f"upload:{kind}",
                )
            ]
        from app.services.due_date_intelligence import parse_meeting_calendar_from_transcript

        started, ended, _anchor = parse_meeting_calendar_from_transcript(text)
        meeting.transcript_chunks = chunks
        meeting.is_upload = True
        meeting.original_file_name = file.filename
        meeting.status = MeetingStatus.ENDED
        meeting.started_at = started or meeting.started_at
        meeting.ended_at = ended or datetime.now(timezone.utc)
        if started and not meeting.scheduled_at:
            meeting.scheduled_at = started
        meeting.updated_at = datetime.now(timezone.utc)
        await meeting.save()
        await self._process_artifacts_sync(meeting_id)
        return await _meeting_response(meeting)

    async def _upsert_attendee(self, meeting: Meeting, user_id: PydanticObjectId) -> None:
        now = datetime.now(timezone.utc)
        for attendee in meeting.attendees:
            if attendee.user_id == user_id:
                if attendee.leave_time is not None:
                    attendee.leave_time = None
                    attendee.join_time = now
                return
        meeting.attendees.append(MeetingAttendee(user_id=user_id, join_time=now))
        meeting.updated_at = now

    async def _broadcast_attendance(self, meeting_id: str) -> None:
        await ws_manager.broadcast(meeting_id, {"type": "attendance_update"})

    async def join_attendance(self, meeting_id: str, user_id: PydanticObjectId) -> MeetingResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_member(str(meeting.workspace_id), user_id)
        await self._upsert_attendee(meeting, user_id)
        await meeting.save()
        await self._broadcast_attendance(meeting_id)
        return await _meeting_response(meeting)

    async def leave_attendance(self, meeting_id: str, user_id: PydanticObjectId) -> MeetingResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_member(str(meeting.workspace_id), user_id)
        now = datetime.now(timezone.utc)
        for attendee in meeting.attendees:
            if attendee.user_id == user_id and attendee.leave_time is None:
                attendee.leave_time = now
        meeting.updated_at = now
        await meeting.save()
        await self._broadcast_attendance(meeting_id)
        return await _meeting_response(meeting)

    async def transition_to_live(self, meeting: Meeting) -> bool:
        """Transition ready → live. Returns True if status changed."""
        if meeting.status == MeetingStatus.SCHEDULED:
            meeting.status = MeetingStatus.READY
        if meeting.status != MeetingStatus.READY:
            return False
        meeting.status = MeetingStatus.LIVE
        meeting.started_at = datetime.now(timezone.utc)
        meeting.updated_at = datetime.now(timezone.utc)
        await meeting.save()
        return True

    async def register_ws_attendee(self, meeting: Meeting, user_id: PydanticObjectId) -> None:
        await self._upsert_attendee(meeting, user_id)
        await meeting.save()
        await self._broadcast_attendance(str(meeting.id))

    async def leave_ws_attendee(self, meeting_id: str, user_id: PydanticObjectId) -> None:
        meeting = await self._get_meeting(meeting_id)
        now = datetime.now(timezone.utc)
        for a in meeting.attendees:
            if a.user_id == user_id and a.leave_time is None:
                a.leave_time = now
        meeting.updated_at = now
        await meeting.save()

    async def append_transcript_chunk(
        self, meeting_id: str, chunk_data: Dict[str, Any]
    ) -> tuple[TranscriptChunk, bool]:
        """Append chunk. Returns (chunk, went_live)."""
        meeting = await self._get_meeting(meeting_id)
        went_live = False
        if meeting.status == MeetingStatus.READY:
            went_live = await self.transition_to_live(meeting)

        speaker = chunk_data.get("speaker") or chunk_data.get("speaker_label")
        confidence = chunk_data.get("confidence", chunk_data.get("stt_confidence", 1.0))
        chunk_id = chunk_data.get("chunk_id") or str(uuid.uuid4())

        chunk = TranscriptChunk(
            chunk_id=str(chunk_id),
            text=chunk_data.get("text", ""),
            speaker=speaker,
            confidence=float(confidence),
            audio_offset_ms=int(chunk_data.get("audio_offset_ms", 0)),
            source=chunk_data.get("source", "live"),
        )
        meeting.transcript_chunks.append(chunk)
        meeting.updated_at = datetime.now(timezone.utc)
        await meeting.save()
        return chunk, went_live

    def chunk_broadcast_payloads(self, chunk: TranscriptChunk) -> List[Dict[str, Any]]:
        dumped = chunk.model_dump(mode="json")
        legacy = {
            **dumped,
            "speaker_label": chunk.speaker,
            "stt_confidence": chunk.confidence,
        }
        return [
            {"type": "transcript_chunk", "chunk": legacy},
            {
                "type": "transcript",
                "text": chunk.text,
                "speaker": chunk.speaker,
                "timestamp": chunk.timestamp.isoformat(),
            },
        ]

    async def get_transcript(
        self, meeting_id: str, user_id: PydanticObjectId, page: int = 1, page_size: int = 50
    ) -> TranscriptResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_member(str(meeting.workspace_id), user_id)
        start = (page - 1) * page_size
        chunks = meeting.transcript_chunks[start : start + page_size]
        items = [_chunk_to_response(c) for c in chunks]
        return TranscriptResponse(
            items=items,
            total=len(meeting.transcript_chunks),
            page=page,
            page_size=page_size,
        )

    async def get_summary(self, meeting_id: str, user_id: PydanticObjectId) -> MeetingSummaryResponse:
        meeting = await self._get_meeting(meeting_id)
        await require_workspace_member(str(meeting.workspace_id), user_id)
        return MeetingSummaryResponse(
            summary=meeting.summary,
            action_items=meeting.action_items,
            key_decisions=meeting.key_decisions,
        )

    async def _get_meeting(self, meeting_id: str) -> Meeting:
        meeting = await Meeting.get(PydanticObjectId(meeting_id))
        if not meeting or meeting.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        return meeting


meeting_service = MeetingService()
