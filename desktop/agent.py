"""Consilium desktop audio capture agent — CLI entry point."""

from __future__ import annotations

import argparse
import signal
import sys
from pathlib import Path

# Repo root must be on sys.path for `desktop.*` imports.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from desktop.session import MeetingSession


def main() -> None:
    parser = argparse.ArgumentParser(description="Consilium meeting audio agent")
    parser.add_argument("--meeting-id", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--ws-url", default="ws://localhost:8000")
    parser.add_argument("--whisper-model", default="tiny")
    args = parser.parse_args()

    session = MeetingSession(
        meeting_id=args.meeting_id,
        token=args.token,
        ws_url=args.ws_url,
        whisper_model=args.whisper_model,
    )

    def shutdown(*_) -> None:
        session.stop("Stopping…")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    session.start()
    print("[agent] Capturing audio. Press Ctrl+C to stop.")
    session.wait()
    session.stop()


if __name__ == "__main__":
    main()
