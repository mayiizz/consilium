from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas import (
    CreateMeetingRequest,
    MeetingResponse,
    MeetingSummaryResponse,
    MessageResponse,
    TranscriptResponse,
    UpdateMeetingRequest,
)
from app.services.meeting_service import meeting_service

router = APIRouter(tags=["meetings"])


@router.post("/api/workspaces/{workspace_id}/meetings", response_model=MeetingResponse)
async def create_meeting(
    workspace_id: str,
    data: CreateMeetingRequest,
    user: User = Depends(get_current_user),
) -> MeetingResponse:
    return await meeting_service.create(workspace_id, user.id, data)


@router.get("/api/workspaces/{workspace_id}/meetings", response_model=List[MeetingResponse])
async def list_meetings(
    workspace_id: str, user: User = Depends(get_current_user)
) -> List[MeetingResponse]:
    return await meeting_service.list_for_workspace(workspace_id, user.id)


@router.get("/api/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str, user: User = Depends(get_current_user)
) -> MeetingResponse:
    return await meeting_service.get(meeting_id, user.id)


@router.put("/api/meetings/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    data: UpdateMeetingRequest,
    user: User = Depends(get_current_user),
) -> MeetingResponse:
    return await meeting_service.update(meeting_id, user.id, data)


@router.delete("/api/meetings/{meeting_id}", response_model=MessageResponse)
async def delete_meeting(
    meeting_id: str, user: User = Depends(get_current_user)
) -> MessageResponse:
    removed_tasks = await meeting_service.delete(meeting_id, user.id)
    if removed_tasks:
        return MessageResponse(
            message=f"Meeting deleted ({removed_tasks} related task{'s' if removed_tasks != 1 else ''} removed)"
        )
    return MessageResponse(message="Meeting deleted")


@router.post("/api/meetings/{meeting_id}/start", response_model=MeetingResponse)
async def start_meeting(
    meeting_id: str, user: User = Depends(get_current_user)
) -> MeetingResponse:
    return await meeting_service.start(meeting_id, user.id)


@router.post("/api/meetings/{meeting_id}/stop", response_model=MeetingResponse)
async def stop_meeting(
    meeting_id: str, user: User = Depends(get_current_user)
) -> MeetingResponse:
    return await meeting_service.stop(meeting_id, user.id)


@router.post("/api/meetings/{meeting_id}/cancel", response_model=MeetingResponse)
async def cancel_meeting(
    meeting_id: str, user: User = Depends(get_current_user)
) -> MeetingResponse:
    return await meeting_service.cancel(meeting_id, user.id)


@router.post("/api/meetings/{meeting_id}/attendance/join", response_model=MeetingResponse)
async def join_attendance(
    meeting_id: str, user: User = Depends(get_current_user)
) -> MeetingResponse:
    return await meeting_service.join_attendance(meeting_id, user.id)


@router.post("/api/meetings/{meeting_id}/attendance/leave", response_model=MeetingResponse)
async def leave_attendance(
    meeting_id: str, user: User = Depends(get_current_user)
) -> MeetingResponse:
    return await meeting_service.leave_attendance(meeting_id, user.id)


@router.post("/api/meetings/{meeting_id}/upload", response_model=MeetingResponse)
async def upload_recording(
    meeting_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> MeetingResponse:
    return await meeting_service.upload(meeting_id, user.id, file)


@router.get("/api/meetings/{meeting_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    meeting_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
) -> TranscriptResponse:
    return await meeting_service.get_transcript(meeting_id, user.id, page, page_size)


@router.get("/api/meetings/{meeting_id}/summary", response_model=MeetingSummaryResponse)
async def get_summary(
    meeting_id: str, user: User = Depends(get_current_user)
) -> MeetingSummaryResponse:
    return await meeting_service.get_summary(meeting_id, user.id)


@router.post("/api/meetings/{meeting_id}/reprocess", response_model=MeetingSummaryResponse)
async def reprocess_meeting(
    meeting_id: str, user: User = Depends(get_current_user)
) -> MeetingSummaryResponse:
    return await meeting_service.reprocess(meeting_id, user.id)
