from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field

from app.models.base import AuditMixin, utcnow


class MeetingStatus(str, Enum):
    SCHEDULED = "scheduled"
    READY = "ready"
    LIVE = "live"
    ENDED = "ended"
    CANCELLED = "cancelled"


class MeetingPlatform(str, Enum):
    GOOGLE_MEET = "google_meet"
    ZOOM = "zoom"
    TEAMS = "teams"
    JITSI = "jitsi"
    CUSTOM = "custom"


class TranscriptChunk(BaseModel):
    chunk_id: str
    speaker: Optional[str] = None
    text: str
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=utcnow)
    audio_offset_ms: int = 0
    source: str = "live"


class MeetingAttendee(BaseModel):
    user_id: Optional[PydanticObjectId] = None
    speaker_label: str = ""
    join_time: datetime = Field(default_factory=utcnow)
    leave_time: Optional[datetime] = None


class Meeting(Document, AuditMixin):
    workspace_id: PydanticObjectId
    title: str
    description: Optional[str] = None
    platform: Optional[MeetingPlatform] = MeetingPlatform.JITSI
    status: MeetingStatus = MeetingStatus.SCHEDULED
    video_link: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: int = 0
    transcript_chunks: List[TranscriptChunk] = Field(default_factory=list)
    summary: Optional[str] = None
    action_items: List[str] = Field(default_factory=list)
    key_decisions: List[str] = Field(default_factory=list)
    attendees: List[MeetingAttendee] = Field(default_factory=list)
    is_upload: bool = False
    original_file_name: Optional[str] = None

    class Settings:
        name = "meetings"

    def full_transcript(self) -> str:
        return "\n".join(c.text for c in self.transcript_chunks if c.text.strip())
