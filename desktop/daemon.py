"""Local HTTP daemon — browser triggers capture on Start meeting."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# Repo root must be on sys.path for `desktop.*` imports.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from desktop.session import MeetingSession

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 9477

ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}


class DaemonState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session: Optional[MeetingSession] = None

    def health(self) -> dict:
        with self._lock:
            session = self._session
            if session and session.active:
                return {"ok": True, "active": True, "meetingId": session.meeting_id}
            return {"ok": True, "active": False, "meetingId": None}

    def start_session(
        self,
        meeting_id: str,
        token: str,
        ws_url: str,
        whisper_model: str = "tiny",
    ) -> dict:
        with self._lock:
            if self._session and self._session.active:
                if self._session.meeting_id == meeting_id:
                    return {"ok": True, "meetingId": meeting_id, "message": "Already capturing"}
                self._session.stop("Switching to new meeting…")
                self._session = None

            session_ref: list[MeetingSession] = []

            def on_disconnect() -> None:
                if session_ref:
                    self._on_session_end(session_ref[0])

            session = MeetingSession(
                meeting_id=meeting_id,
                token=token,
                ws_url=ws_url,
                whisper_model=whisper_model,
                on_disconnect=on_disconnect,
            )
            session_ref.append(session)
            try:
                session.start()
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
            self._session = session
            return {"ok": True, "meetingId": meeting_id, "message": "Capture started"}

    def stop_session(self) -> dict:
        with self._lock:
            if not self._session or not self._session.active:
                return {"ok": True, "message": "No active capture"}
            meeting_id = self._session.meeting_id
            self._session.stop("Stopped by UI")
            self._session = None
            return {"ok": True, "meetingId": meeting_id, "message": "Capture stopped"}

    def _on_session_end(self, session: MeetingSession) -> None:
        with self._lock:
            if self._session is session:
                self._session = None


STATE = DaemonState()


def _cors_origin(handler: BaseHTTPRequestHandler) -> str:
    origin = handler.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        return origin
    # Allow LAN/dev hosts talking to the local daemon (e.g. http://192.168.x.x:3000)
    if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
        return origin
    if origin.startswith("http://192.168.") or origin.startswith("http://10."):
        return origin
    return "http://localhost:3000"


class DaemonHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"[daemon] {self.address_string()} {format % args}")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self))
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, STATE.health())
            return
        self._send_json(404, {"ok": False, "error": "Not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._read_json()
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "error": "Invalid JSON"})
            return

        if path == "/start":
            meeting_id = str(body.get("meetingId", "")).strip()
            token = str(body.get("token", "")).strip()
            ws_url = str(body.get("wsUrl", "ws://localhost:8000")).strip()
            whisper_model = str(body.get("whisperModel", "tiny")).strip()
            if not meeting_id or not token:
                self._send_json(400, {"ok": False, "error": "meetingId and token are required"})
                return
            result = STATE.start_session(meeting_id, token, ws_url, whisper_model)
            status = 200 if result.get("ok") else 500
            self._send_json(status, result)
            return

        if path == "/stop":
            result = STATE.stop_session()
            self._send_json(200, result)
            return

        self._send_json(404, {"ok": False, "error": "Not found"})


def main() -> None:
    server = ThreadingHTTPServer((DAEMON_HOST, DAEMON_PORT), DaemonHandler)
    print(f"[daemon] Listening on http://{DAEMON_HOST}:{DAEMON_PORT}")
    print("[daemon] Leave running — Start meeting in the browser will auto-transcribe.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[daemon] Shutting down…")
        STATE.stop_session()
        server.shutdown()


if __name__ == "__main__":
    main()
