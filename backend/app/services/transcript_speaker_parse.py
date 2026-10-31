"""Parse speaker labels and clock times from uploaded transcript lines."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

# **Name:** text  |  Name: text  |  [Name]: text
_SPEAKER_RE = re.compile(
    r"^\s*(?:\*\*)?\[?(?P<name>[A-Za-z][A-Za-z0-9 .'-]{0,40})\]?(?:\*\*)?\s*:\s*(?P<body>.+)\s*$"
)
# **[10:00 AM — Meeting Started]** or [10:08 AM]
_CLOCK_RE = re.compile(
    r"\[?\s*(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<ampm>AM|PM)?",
    re.IGNORECASE,
)

_SKIP_PREFIXES = (
    "#",
    "**project:",
    "**day:",
    "**duration:",
    "**participants:",
    "project:",
    "day:",
    "duration:",
    "participants:",
    "---",
    "***",
)


def _strip_md(s: str) -> str:
    return re.sub(r"\*+", "", s).strip()


def _looks_like_metadata(line: str) -> bool:
    low = line.strip().lower()
    if not low or low in {"---", "***", "—", "-"}:
        return True
    if any(low.startswith(p) for p in _SKIP_PREFIXES):
        return True
    # Pure section header like **[10:00 AM — Meeting Started]**
    if low.startswith("[") or (low.startswith("**[") and "—" in low):
        return True
    return False


def parse_speaker_line(line: str) -> Tuple[Optional[str], str]:
    """Return (speaker, text). Speaker may be None."""
    raw = (line or "").strip()
    if not raw:
        return None, ""
    cleaned = raw
    # Unwrap full-line bold like **Rahul: hello**
    if cleaned.startswith("**") and cleaned.endswith("**") and cleaned.count("**") == 2:
        cleaned = cleaned[2:-2].strip()

    m = _SPEAKER_RE.match(cleaned)
    if not m:
        # Try after stripping leading ** only
        cleaned2 = re.sub(r"^\*\*", "", cleaned)
        cleaned2 = re.sub(r"\*\*$", "", cleaned2).strip()
        m = _SPEAKER_RE.match(cleaned2)
    if not m:
        return None, raw

    name = _strip_md(m.group("name"))
    body = m.group("body").strip()
    body = re.sub(r"^\*\*", "", body)
    body = re.sub(r"\*\*$", "", body).strip()
    # Reject false positives like times or URLs
    if not name or name.lower() in {"http", "https", "note", "time"}:
        return None, raw
    if len(name) > 40:
        return None, raw
    return name, body or raw


def parse_clock_to_ms(line: str, base_minutes: Optional[int] = None) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse first clock in line to minutes-from-midnight and ms offset from base.
    Returns (minutes_from_midnight, offset_ms_from_base).
    """
    m = _CLOCK_RE.search(line or "")
    if not m:
        return None, None
    h = int(m.group("h"))
    minute = int(m.group("m"))
    ampm = (m.group("ampm") or "").upper()
    if ampm == "PM" and h < 12:
        h += 12
    if ampm == "AM" and h == 12:
        h = 0
    absolute = h * 60 + minute
    if base_minutes is None:
        return absolute, 0
    delta = absolute - base_minutes
    if delta < 0:
        delta += 24 * 60
    return absolute, delta * 60_000


def transcript_lines_to_chunks(text: str) -> List[dict]:
    """
    Split extracted upload text into chunk dicts:
    {speaker, text, audio_offset_ms}
    Skips empty/metadata-only lines.
    """
    lines = [ln for ln in (text or "").split("\n")]
    chunks: List[dict] = []
    base_minutes: Optional[int] = None
    current_offset_ms = 0

    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            continue

        abs_m, off = parse_clock_to_ms(stripped, base_minutes)
        if abs_m is not None:
            if base_minutes is None:
                base_minutes = abs_m
                current_offset_ms = 0
            elif off is not None:
                current_offset_ms = off

        if _looks_like_metadata(stripped):
            # Skip markdown titles / metadata; keep only timed section markers
            if stripped.lstrip().startswith("#"):
                continue
            note = _strip_md(stripped)
            if note.startswith("[") and note.endswith("]"):
                note = note[1:-1].strip()
            low = note.lower()
            if ("meeting started" in low or "meeting ended" in low) or (
                ("am" in low or "pm" in low) and ("—" in note or " - " in note)
            ):
                chunks.append(
                    {
                        "speaker": "Note",
                        "text": note,
                        "audio_offset_ms": current_offset_ms,
                    }
                )
            continue

        speaker, body = parse_speaker_line(stripped)
        if not body:
            continue
        chunks.append(
            {
                "speaker": speaker,
                "text": body,
                "audio_offset_ms": current_offset_ms,
            }
        )

    if not chunks and (text or "").strip():
        chunks.append({"speaker": None, "text": text.strip()[:8000], "audio_offset_ms": 0})
    return chunks
