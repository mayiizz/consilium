import { apiFetch } from "../client";
import { mapMeeting, mapTranscriptChunk } from "../mappers";
import type { Meeting, MeetingPlatform, TranscriptLine } from "../../types";

export interface CreateMeetingPayload {
  title: string;
  description?: string;
  platform?: MeetingPlatform;
  meeting_type?: "instant" | "scheduled";
  video_link?: string;
  scheduled_at?: string;
  generate_link?: boolean;
}

export async function listMeetings(workspaceId: string): Promise<Meeting[]> {
  const data = await apiFetch<Record<string, unknown>[]>(`/workspaces/${workspaceId}/meetings`);
  return data.map((m) => mapMeeting(m));
}

export async function getMeeting(meetingId: string): Promise<Meeting> {
  const data = await apiFetch<Record<string, unknown>>(`/meetings/${meetingId}`);
  return mapMeeting(data);
}

export async function createMeeting(workspaceId: string, payload: CreateMeetingPayload): Promise<Meeting> {
  const data = await apiFetch<Record<string, unknown>>(`/workspaces/${workspaceId}/meetings`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return mapMeeting(data);
}

export async function startMeeting(meetingId: string): Promise<Meeting> {
  const data = await apiFetch<Record<string, unknown>>(`/meetings/${meetingId}/start`, { method: "POST" });
  return mapMeeting(data);
}

export async function stopMeeting(meetingId: string): Promise<Meeting> {
  const data = await apiFetch<Record<string, unknown>>(`/meetings/${meetingId}/stop`, { method: "POST" });
  return mapMeeting(data);
}

export async function cancelMeeting(meetingId: string): Promise<Meeting> {
  const data = await apiFetch<Record<string, unknown>>(`/meetings/${meetingId}/cancel`, { method: "POST" });
  return mapMeeting(data);
}

export async function deleteMeeting(meetingId: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/meetings/${meetingId}`, { method: "DELETE" });
}

export async function joinAttendance(meetingId: string): Promise<Meeting> {
  const data = await apiFetch<Record<string, unknown>>(`/meetings/${meetingId}/attendance/join`, { method: "POST" });
  return mapMeeting(data);
}

export async function leaveAttendance(meetingId: string): Promise<Meeting> {
  const data = await apiFetch<Record<string, unknown>>(`/meetings/${meetingId}/attendance/leave`, { method: "POST" });
  return mapMeeting(data);
}

export async function getTranscript(meetingId: string): Promise<TranscriptLine[]> {
  const data = await apiFetch<{ items: Record<string, unknown>[] }>(
    `/meetings/${meetingId}/transcript?page_size=200`,
  );
  return (data.items ?? []).map((c, i) => mapTranscriptChunk(c, i));
}

export async function reprocessMeeting(meetingId: string): Promise<{
  summary?: string;
  action_items: string[];
  key_decisions: string[];
}> {
  return apiFetch(`/meetings/${meetingId}/reprocess`, { method: "POST" });
}

/** Upload a UTF-8 transcript (.txt/.md). Ends the meeting and runs summary + kanban automation. */
export async function uploadMeetingTranscript(meetingId: string, file: File): Promise<Meeting> {
  const form = new FormData();
  form.append("file", file);
  const data = await apiFetch<Record<string, unknown>>(`/meetings/${meetingId}/upload`, {
    method: "POST",
    body: form,
  });
  return mapMeeting(data);
}
