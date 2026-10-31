import { useEffect, useRef, useState } from "react";

type SpeechRecognitionLike = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((ev: SpeechRecognitionEventLike) => void) | null;
  onerror: ((ev: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionEventLike = {
  resultIndex: number;
  results: ArrayLike<{
    isFinal: boolean;
    0: { transcript: string; confidence: number };
  }>;
};

function getSpeechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionLike;
    webkitSpeechRecognition?: new () => SpeechRecognitionLike;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Errors that should stop permanently (permission / unsupported). */
const FATAL_ERRORS = new Set(["not-allowed", "service-not-allowed"]);

/** Chrome often ends a session after these; we restart. */
const RECOVERABLE_ERRORS = new Set([
  "aborted",
  "no-speech",
  "network",
  "audio-capture",
  "bad-grammar",
  "language-not-supported",
]);

export type MicTranscriptStatus = "idle" | "listening" | "unsupported" | "denied" | "error";

/**
 * Live transcription via the browser Web Speech API only (no Whisper).
 *
 * Chrome ends continuous recognition periodically (silence / network).
 * This hook restarts with backoff, recreates the recognizer when needed,
 * and resumes when the tab becomes visible again.
 */
export function useBrowserMicTranscript({
  enabled,
  speakerName,
  connected,
  sendChunk,
}: {
  enabled: boolean;
  speakerName: string;
  connected: boolean;
  sendChunk: (chunk: {
    text: string;
    speaker: string;
    confidence?: number;
    chunk_id?: string;
  }) => boolean;
}) {
  const [status, setStatus] = useState<MicTranscriptStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [interim, setInterim] = useState("");

  const shouldRun = useRef(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const restartTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const watchdogTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const restartAttempt = useRef(0);
  const lastResultAt = useRef(0);
  const starting = useRef(false);
  const sendChunkRef = useRef(sendChunk);
  const speakerRef = useRef(speakerName);

  sendChunkRef.current = sendChunk;
  speakerRef.current = speakerName;

  useEffect(() => {
    const clearRestart = () => {
      if (restartTimer.current) {
        clearTimeout(restartTimer.current);
        restartTimer.current = null;
      }
    };

    const stopRecognition = () => {
      clearRestart();
      const rec = recognitionRef.current;
      recognitionRef.current = null;
      if (!rec) return;
      try {
        rec.onresult = null;
        rec.onerror = null;
        rec.onend = null;
        rec.abort();
      } catch {
        try {
          rec.stop();
        } catch {
          // ignore
        }
      }
    };

    if (!enabled || !speakerName.trim()) {
      shouldRun.current = false;
      stopRecognition();
      if (watchdogTimer.current) {
        clearInterval(watchdogTimer.current);
        watchdogTimer.current = null;
      }
      setStatus("idle");
      setInterim("");
      setError(null);
      return;
    }

    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setStatus("unsupported");
      setError("Live mic transcription needs Chrome or Edge (Web Speech API).");
      return;
    }

    if (!connected) {
      shouldRun.current = false;
      stopRecognition();
      setStatus("idle");
      setInterim("");
      return;
    }

    shouldRun.current = true;
    restartAttempt.current = 0;
    lastResultAt.current = Date.now();
    // Chrome often hard-stops continuous recognition around ~60s; recycle before that.
    let lastRecycleAt = Date.now();

    const scheduleRestart = (delayMs = 250) => {
      if (!shouldRun.current) return;
      clearRestart();
      const delay = Math.min(delayMs + restartAttempt.current * 200, 3000);
      restartTimer.current = setTimeout(() => {
        restartTimer.current = null;
        if (!shouldRun.current) return;
        // Prefer a fresh instance — Chrome often refuses start() on a dead session.
        stopRecognition();
        startFresh();
      }, delay);
    };

    const startFresh = () => {
      if (!shouldRun.current || starting.current) return;
      starting.current = true;
      try {
        const recognition = new Ctor();
        recognitionRef.current = recognition;
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onresult = (ev) => {
          lastResultAt.current = Date.now();
          restartAttempt.current = 0;
          let interimText = "";
          for (let i = ev.resultIndex; i < ev.results.length; i++) {
            const result = ev.results[i];
            const text = String(result?.[0]?.transcript ?? "").trim();
            if (!text) continue;
            if (!result.isFinal) {
              interimText += (interimText ? " " : "") + text;
              continue;
            }
            setInterim("");
            const confidence = Number(result[0]?.confidence ?? 0.9);
            sendChunkRef.current({
              text,
              speaker: speakerRef.current.trim(),
              confidence: Number.isFinite(confidence) ? confidence : 0.9,
              chunk_id: crypto.randomUUID(),
            });
          }
          if (interimText) setInterim(interimText);
        };

        recognition.onerror = (ev) => {
          const code = ev.error || "error";
          if (FATAL_ERRORS.has(code)) {
            shouldRun.current = false;
            setStatus("denied");
            setError("Microphone permission denied. Allow mic access for this site.");
            clearRestart();
            return;
          }
          // Recoverable: let onend restart, or schedule if onend does not fire.
          if (RECOVERABLE_ERRORS.has(code) || code === "network") {
            setError(null);
            scheduleRestart(code === "network" ? 800 : 300);
            return;
          }
          // Unknown — keep trying rather than leaving the meeting silent.
          setError(`Mic hiccup (${code}) — restarting…`);
          scheduleRestart(500);
        };

        recognition.onend = () => {
          if (!shouldRun.current) {
            setStatus("idle");
            setInterim("");
            return;
          }
          // Chrome ends continuous sessions after ~silence; restart with a short delay.
          restartAttempt.current += 1;
          setStatus("listening");
          scheduleRestart(200);
        };

        recognition.start();
        setStatus("listening");
        setError(null);
        lastResultAt.current = Date.now();
        lastRecycleAt = Date.now();
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Could not start mic transcription";
        // InvalidStateError if already started — try again shortly with a new instance.
        setError(msg);
        scheduleRestart(400);
      } finally {
        starting.current = false;
      }
    };

    startFresh();

    watchdogTimer.current = setInterval(() => {
      if (!shouldRun.current) return;
      if (document.visibilityState === "hidden") return;
      if (!recognitionRef.current) {
        scheduleRestart(100);
        return;
      }
      if (Date.now() - lastRecycleAt > 50_000) {
        lastRecycleAt = Date.now();
        scheduleRestart(50);
      }
    }, 4000);

    const onVisibility = () => {
      if (!shouldRun.current) return;
      if (document.visibilityState === "visible") {
        lastResultAt.current = Date.now();
        scheduleRestart(150);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      shouldRun.current = false;
      document.removeEventListener("visibilitychange", onVisibility);
      if (watchdogTimer.current) {
        clearInterval(watchdogTimer.current);
        watchdogTimer.current = null;
      }
      stopRecognition();
      setInterim("");
    };
  }, [enabled, speakerName, connected]);

  return { status, error, interim };
}
