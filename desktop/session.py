"""Reusable meeting capture session (CLI + daemon)."""

from __future__ import annotations

import threading
from typing import Callable, Optional

from desktop.audio_capture import CHUNK_SECONDS, TARGET_RATE, AudioCapture
from desktop.transcriber import Transcriber
from desktop.ws_client import MeetingWsClient


class MeetingSession:
    def __init__(
        self,
        meeting_id: str,
        token: str,
        ws_url: str = "ws://localhost:8000",
        whisper_model: str = "tiny",
        on_disconnect: Optional[Callable[[], None]] = None,
    ) -> None:
        self.meeting_id = meeting_id
        self.token = token
        self.ws_url = ws_url
        self.whisper_model = whisper_model
        self._on_disconnect = on_disconnect

        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._transcriber = Transcriber(model_size=whisper_model)
        self._offset_ms = 0
        self._capture: Optional[AudioCapture] = None
        self._ws: Optional[MeetingWsClient] = None
        self._ping_thread: Optional[threading.Thread] = None
        self._active = False

    @property
    def active(self) -> bool:
        return self._active and not self._stop_event.is_set()

    def start(self) -> None:
        with self._lock:
            if self.active:
                return

            self._stop_event.clear()
            self._offset_ms = 0

            def on_disconnect() -> None:
                self.stop(
                    "WebSocket disconnected (backend reload or meeting ended). "
                    "Transcript saved so far."
                )
                if self._on_disconnect:
                    self._on_disconnect()

            self._ws = MeetingWsClient(
                self.ws_url,
                self.meeting_id,
                self.token,
                on_disconnect=on_disconnect,
            )

            def on_chunk(pcm) -> None:
                if self._stop_event.is_set():
                    return
                text, confidence = self._transcriber.transcribe(pcm, TARGET_RATE)
                if text and self._ws:
                    if not self._ws.publish_chunk(text, confidence, self._offset_ms):
                        self.stop("Could not publish transcript — stopping capture.")
                        return
                    print(f"[transcript] {text[:80]}{'…' if len(text) > 80 else ''}")
                self._offset_ms += CHUNK_SECONDS * 1000

            self._capture = AudioCapture(on_chunk)
            self._ws.connect()
            self._ping_thread = threading.Thread(
                target=self._ws.ping_loop,
                args=(self._stop_event,),
                daemon=True,
            )
            self._ping_thread.start()
            self._capture.start()
            self._active = True
            print(f"[agent] Capturing audio for meeting {self.meeting_id}")

    def stop(self, reason: str = "Stopped") -> None:
        with self._lock:
            self._shutdown_unlocked(reason)

    def wait(self) -> None:
        self._stop_event.wait()

    def _shutdown_unlocked(self, reason: str) -> None:
        if self._stop_event.is_set() and not self._active:
            return
        if self._active or not self._stop_event.is_set():
            print(f"[agent] {reason}")
        self._stop_event.set()
        self._active = False
        if self._capture:
            self._capture.stop()
            self._capture = None
        if self._ws:
            self._ws.close()
            self._ws = None
