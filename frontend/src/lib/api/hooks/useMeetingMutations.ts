import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as meetingApi from "../services/meetings";
import type { CreateMeetingPayload } from "../services/meetings";

export function useMeetingMutations(workspaceId: string) {
  const qc = useQueryClient();

  const invalidate = (meetingId?: string) => {
    qc.invalidateQueries({ queryKey: ["meetings", workspaceId] });
    qc.invalidateQueries({ queryKey: ["dashboard", workspaceId] });
    qc.invalidateQueries({ queryKey: ["tasks", workspaceId] });
    if (meetingId) {
      qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
      qc.invalidateQueries({ queryKey: ["transcript", meetingId] });
    }
  };

  const create = useMutation({
    mutationFn: (payload: CreateMeetingPayload) => meetingApi.createMeeting(workspaceId, payload),
    onSuccess: () => invalidate(),
  });

  const start = useMutation({
    mutationFn: (meetingId: string) => meetingApi.startMeeting(meetingId),
    onSuccess: (_, meetingId) => invalidate(meetingId),
  });

  const stop = useMutation({
    mutationFn: (meetingId: string) => meetingApi.stopMeeting(meetingId),
    onSuccess: (_, meetingId) => invalidate(meetingId),
  });

  const cancel = useMutation({
    mutationFn: (meetingId: string) => meetingApi.cancelMeeting(meetingId),
    onSuccess: (_, meetingId) => invalidate(meetingId),
  });

  const reprocess = useMutation({
    mutationFn: (meetingId: string) => meetingApi.reprocessMeeting(meetingId),
    onSuccess: (_, meetingId) => invalidate(meetingId),
  });

  const remove = useMutation({
    mutationFn: (meetingId: string) => meetingApi.deleteMeeting(meetingId),
    onSuccess: (_, meetingId) => invalidate(meetingId),
  });

  const upload = useMutation({
    mutationFn: ({ meetingId, file }: { meetingId: string; file: File }) =>
      meetingApi.uploadMeetingTranscript(meetingId, file),
    onSuccess: (meeting) => invalidate(meeting.id),
  });

  return { create, start, stop, cancel, reprocess, remove, upload };
}
