import { useQuery } from "@tanstack/react-query";
import * as meetingApi from "../services/meetings";

export function useMeetings(workspaceId: string) {
  return useQuery({
    queryKey: ["meetings", workspaceId],
    queryFn: () => meetingApi.listMeetings(workspaceId),
    enabled: !!workspaceId,
    refetchInterval: 30000,
  });
}

export function useMeeting(meetingId: string, refetchWhenActive = false) {
  return useQuery({
    queryKey: ["meeting", meetingId],
    queryFn: () => meetingApi.getMeeting(meetingId),
    enabled: !!meetingId,
    refetchInterval: refetchWhenActive ? 3000 : false,
  });
}

export function useTranscript(meetingId: string, enabled = true, pollMs = 5000) {
  return useQuery({
    queryKey: ["transcript", meetingId],
    queryFn: () => meetingApi.getTranscript(meetingId),
    enabled: !!meetingId && enabled,
    refetchInterval: enabled ? pollMs : false,
  });
}
