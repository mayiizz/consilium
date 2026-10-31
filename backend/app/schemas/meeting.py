from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class TranscriptChunkResponse(BaseModel):
    chunk_id: str
    timestamp: datetime
    audio_offset_ms: int
    text: str
    speaker: Optional[str] = None
    confidence: float = 1.0
    source: str = "live"
    # Legacy aliases for existing clients
    speaker_label: Optional[str] = None
    stt_confidence: float = 1.0


class MeetingAttendeeResponse(BaseModel):
    user_id: str
    name: str
    avatar: Optional[str] = None
    join_time: datetime
    leave_time: Optional[datetime] = None


class CreateMeetingRequest(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = None
    platform: Optional[str] = "jitsi"
    meeting_type: Optional[str] = "instant"
    video_link: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    generate_link: bool = True


class UpdateMeetingRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    video_link: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    platform: Optional[str] = None


class MeetingResponse(ORMBase):
    id: str
    workspace_id: str
    title: str
    description: Optional[str] = None
    platform: Optional[str] = None
    status: str
    video_link: Optional[str] = None
    meeting_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration: int = 0
    summary: Optional[str] = None
    action_items: List[str] = Field(default_factory=list)
    key_decisions: List[str] = Field(default_factory=list)
    attendees: List[MeetingAttendeeResponse] = Field(default_factory=list)
    transcript_count: int = 0
    created_by: Optional[str] = None
    is_upload: bool = False
    created_at: datetime
    updated_at: datetime


class MeetingSummaryResponse(BaseModel):
    summary: Optional[str] = None
    action_items: List[str] = Field(default_factory=list)
    key_decisions: List[str] = Field(default_factory=list)


class TranscriptResponse(BaseModel):
    items: List[TranscriptChunkResponse]
    total: int
    page: int
    page_size: int
