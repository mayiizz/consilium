"""WebSocket client for publishing transcript chunks."""

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Callable, Optional
from urllib.parse import quote

try:
    import websocket
except ImportError:
    websocket = None  # type: ignore


class MeetingWsClient:
    def __init__(
        self,
        ws_url: str,
        meeting_id: str,
        token: str,
        on_disconnect: Optional[Callable[[], None]] = None,
        max_reconnect_attempts: int = 3,
    ) -> None:
        if websocket is None:
            raise RuntimeError("websocket-client not installed. Run: pip install websocket-client")
        if meeting_id.startswith("YOUR_") or token.startswith("YOUR_"):
            raise ValueError(
                "Replace placeholder --meeting-id and --token with real values "
                "from the meeting page (copy the launch command)."
            )
        base = ws_url.rstrip("/")
        self.url = f"{base}/ws/meetings/{meeting_id}?token={quote(token, safe='')}&role=agent"
        self._ws: Optional[websocket.WebSocket] = None
        self._lock = threading.Lock()
        self._on_disconnect = on_disconnect
        self._max_reconnect_attempts = max_reconnect_attempts
        self._disconnect_notified = False

    def connect(self) -> None:
        try:
            self._ws = websocket.create_connection(self.url, timeout=10)
        except Exception as exc:
            msg = str(exc)
            if "403" in msg:
                raise ConnectionError(
                    "WebSocket forbidden (403). Use a valid JWT access token and meeting id "
                    "from the meeting detail page."
                ) from exc
            if "401" in msg or "4001" in msg:
                raise ConnectionError(
                    "WebSocket auth failed. Copy a fresh token from browser localStorage "
                    "(consilium.auth.token) after signing in."
                ) from exc
            raise
        self._disconnect_notified = False
        with self._lock:
            if not self._send_unlocked({"type": "agent_connected"}):
                raise ConnectionError("Failed to handshake with meeting WebSocket")
        print("[agent] Connected to meeting WebSocket")

    @property
    def connected(self) -> bool:
        return self._ws is not None

    def close(self) -> None:
        with self._lock:
            self._close_socket()

    def publish_chunk(self, text: str, confidence: float, audio_offset_ms: int) -> bool:
        if not text.strip():
            return True
        payload = {
            "type": "transcript_chunk",
            "chunk": {
                "chunk_id": str(uuid.uuid4()),
                "text": text,
                "confidence": confidence,
                "speaker": None,
                "audio_offset_ms": audio_offset_ms,
                "source": "live",
            },
        }
        return self._send(payload)

    def _close_socket(self) -> None:
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

    def _send_unlocked(self, data: dict) -> bool:
        if not self._ws:
            return False
        try:
            self._ws.send(json.dumps(data))
            return True
        except Exception:
            self._close_socket()
            return False

    def _reconnect_unlocked(self) -> bool:
        for attempt in range(self._max_reconnect_attempts):
            delay = min(2**attempt, 5)
            print(
                f"[agent] WebSocket lost — reconnecting in {delay}s "
                f"({attempt + 1}/{self._max_reconnect_attempts})…"
            )
            time.sleep(delay)
            try:
                self._ws = websocket.create_connection(self.url, timeout=10)
                if self._send_unlocked({"type": "agent_connected"}):
                    print("[agent] WebSocket reconnected")
                    self._disconnect_notified = False
                    return True
            except Exception:
                self._close_socket()
        return False

    def _notify_disconnect(self) -> None:
        if self._disconnect_notified:
            return
        self._disconnect_notified = True
        if self._on_disconnect:
            self._on_disconnect()

    def _send(self, data: dict) -> bool:
        with self._lock:
            if self._send_unlocked(data):
                return True
            if self._reconnect_unlocked() and self._send_unlocked(data):
                return True
            self._notify_disconnect()
            return False

    def ping_loop(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            if not self._send({"type": "ping"}):
                break
            stop_event.wait(30)
