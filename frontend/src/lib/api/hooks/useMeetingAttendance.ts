import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import * as meetingApi from "../services/meetings";

export function useMeetingAttendance(meetingId: string, isActive = false) {
  const qc = useQueryClient();
  const joinedRef = useRef(false);

  useEffect(() => {
    if (!meetingId) return;

    if (!isActive) {
      if (joinedRef.current) {
        meetingApi.leaveAttendance(meetingId).catch(() => {});
        joinedRef.current = false;
      }
      return;
    }

    meetingApi
      .joinAttendance(meetingId)
      .then(() => {
        joinedRef.current = true;
        qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
      })
      .catch(() => {});

    return () => {
      if (joinedRef.current) {
        meetingApi.leaveAttendance(meetingId).catch(() => {});
        joinedRef.current = false;
      }
    };
  }, [meetingId, isActive, qc]);
}
