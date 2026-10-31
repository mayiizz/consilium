import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { getWsUrl } from "../client";
import type { TranscriptLine } from "../../types";
import { mapTranscriptChunk } from "../mappers";

export function useMeetingSocket(meetingId: string, enabled: boolean) {
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retries = useRef(0);
  const seenChunkIds = useRef(new Set<string>());
  const qc = useQueryClient();

  useEffect(() => {
    if (!enabled || !meetingId) return;

    let cancelled = false;
    seenChunkIds.current = new Set();

    const connect = () => {
      const ws = new WebSocket(getWsUrl(meetingId));
      wsRef.current = ws;

      ws.onopen = () => {
        if (cancelled) return;
        setConnected(true);
        retries.current = 0;
        // Mark meeting live without the desktop agent.
        try {
          ws.send(JSON.stringify({ type: "agent_connected" }));
        } catch {
          // ignore
        }
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === "transcript_chunk" && data.chunk) {
            const chunkId = String(data.chunk.chunk_id ?? "");
            if (chunkId && seenChunkIds.current.has(chunkId)) return;
            if (chunkId) seenChunkIds.current.add(chunkId);
            setLines((prev) => [...prev, mapTranscriptChunk(data.chunk, prev.length)]);
            qc.invalidateQueries({ queryKey: ["transcript", meetingId] });
            qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
          } else if (data.type === "meeting_status") {
            qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
          } else if (data.type === "attendance_update") {
            qc.invalidateQueries({ queryKey: ["meeting", meetingId] });
          }
        } catch {
          // ignore malformed payloads
        }
      };

      ws.onclose = () => {
        setConnected(false);
        if (!cancelled && retries.current < 5) {
          const delay = Math.min(1000 * 2 ** retries.current, 30000);
          retries.current += 1;
          setTimeout(connect, delay);
        }
      };
    };

    connect();
    return () => {
      cancelled = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [meetingId, enabled, qc]);

  const sendChunk = useCallback(
    (chunk: {
      text: string;
      speaker: string;
      confidence?: number;
      chunk_id?: string;
      audio_offset_ms?: number;
    }) => {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return false;
      const chunkId = chunk.chunk_id || crypto.randomUUID();
      seenChunkIds.current.add(chunkId);
      ws.send(
        JSON.stringify({
          type: "transcript_chunk",
          chunk: {
            chunk_id: chunkId,
            text: chunk.text,
            speaker: chunk.speaker,
            confidence: chunk.confidence ?? 0.9,
            audio_offset_ms: chunk.audio_offset_ms ?? 0,
            source: "live",
          },
        }),
      );
      // Optimistic local append so the speaker sees their line immediately;
      // broadcast uses the same chunk_id and is deduped above.
      setLines((prev) => [
        ...prev,
        {
          speaker: chunk.speaker,
          text: chunk.text,
          t: (chunk.audio_offset_ms ?? prev.length * 2000) / 1000,
        },
      ]);
      return true;
    },
    [],
  );

  return { lines, connected, setLines, sendChunk };
}
