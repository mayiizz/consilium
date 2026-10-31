"""Intelligent due-date marking from meeting transcript evidence."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional, Tuple

_WEEKDAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

# Strong deadline cues — not ambient "tomorrow" alone
_DEADLINE_INTENT_RE = re.compile(
    r"\b("
    r"by|before|until|due|deadline|eod|cob|close of business|"
    r"end of (the )?day|end of today|end of day\s*\d+|"
    r"aim to|complete by|finish by|ship by|deliver by|have .{0,40} by|"
    r"day after tomorrow|"
    r"by\s+tomorrow|before\s+tomorrow|due\s+tomorrow|until\s+tomorrow|"
    r"finish(ed)?\s+tomorrow|complete(d)?\s+tomorrow|deliver\s+tomorrow|"
    r"this (monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"by\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)|"
    r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|week)|"
    r"in\s+\d+\s+days?"
    r")\b",
    re.I,
)

_TODAY_COMMIT_RE = re.compile(
    r"("
    r"\b(i'?ll|i will|we'?ll|we will|will|going to|need to|should|must|let'?s)\b"
    r".{0,60}\b(today|tonight|this evening|eod|end of (the )?day)\b"
    r"|"
    r"\b(today|tonight|this evening)\b"
    r".{0,60}\b(i'?ll|i will|set up|finish|complete|deliver|ship|done|results|create|implement)\b"
    r"|"
    r"\bby (the end of )?today\b"
    r"|"
    r"\bend of today\b"
    r"|"
    r"\b(set up|finish|complete|deliver|ship|create|implement).{0,40}\btoday\b"
    r")",
    re.I | re.S,
)

_TOMORROW_COMMIT_RE = re.compile(
    r"("
    r"\b(i'?ll|i will|we'?ll|we will|will|need to|must|should|finish|complete|deliver|ship|due)\b"
    r".{0,60}\btomorrow\b"
    r"|"
    r"\btomorrow\b.{0,40}\b(i'?ll|finish|complete|deliver|ship|done|ready|check what)\b"
    r"|"
    r"\b(by|before|until|due)\s+tomorrow\b"
    r")",
    re.I | re.S,
)

_CLOCK_RE = re.compile(
    r"\b(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<ampm>AM|PM)\b",
    re.I,
)
_ABS_DATE_RE = re.compile(
    r"\b(?P<y>20\d{2})-(?P<mo>\d{2})-(?P<d>\d{2})\b"
    r"|"
    r"\b(?P<d2>\d{1,2})[/-](?P<mo2>\d{1,2})[/-](?P<y2>20\d{2})\b"
)


def has_deadline_intent(text: str) -> bool:
    t = text or ""
    if not t.strip():
        return False
    if _DEADLINE_INTENT_RE.search(t):
        return True
    if _TODAY_COMMIT_RE.search(t):
        return True
    if _TOMORROW_COMMIT_RE.search(t):
        return True
    return False


def _next_weekday_on_or_after(anchor: date, target_weekday: int) -> date:
    delta = (target_weekday - anchor.weekday()) % 7
    return anchor + timedelta(days=delta)


def infer_due_date_iso(text: str, anchor: date) -> Optional[str]:
    """Map deadline phrases in text to YYYY-MM-DD using meeting reference date."""
    t = (text or "").strip()
    if not t or not has_deadline_intent(t):
        return None
    low = t.lower()

    m_abs = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", low)
    if m_abs:
        return f"{m_abs.group(1)}-{m_abs.group(2)}-{m_abs.group(3)}"
    m_abs2 = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", low)
    if m_abs2:
        d, mo, y = int(m_abs2.group(1)), int(m_abs2.group(2)), int(m_abs2.group(3))
        if d > 12:
            day, month = d, mo
        elif mo > 12:
            day, month = mo, d
        else:
            day, month = d, mo
        try:
            return date(y, month, day).isoformat()
        except ValueError:
            pass

    m_in = re.search(r"\bin\s+(\d+)\s+days?\b", low)
    if m_in:
        return (anchor + timedelta(days=int(m_in.group(1)))).isoformat()

    if re.search(r"\bday after tomorrow\b", low):
        return (anchor + timedelta(days=2)).isoformat()

    if _TOMORROW_COMMIT_RE.search(t) or re.search(
        r"\b(by|before|until|due)\s+tomorrow\b", low
    ):
        return (anchor + timedelta(days=1)).isoformat()

    if re.search(r"\bnext week\b", low):
        return (anchor + timedelta(days=7)).isoformat()

    if _TODAY_COMMIT_RE.search(t) or re.search(
        r"\b(eod|cob|end of (the )?day|end of today|end of day\s*\d+)\b",
        low,
    ):
        return anchor.isoformat()

    for i, day_name in enumerate(_WEEKDAY_NAMES):
        if not re.search(rf"\b{day_name}s?\b", low):
            continue
        if re.search(rf"\bnext\s+{day_name}s?\b", low):
            return (_next_weekday_on_or_after(anchor, i) + timedelta(days=7)).isoformat()
        if re.search(
            rf"\b(this|by|on|before|until|due|deadline)\s+{day_name}s?\b",
            low,
        ) or re.search(
            rf"\b{day_name}s?\b.{{0,20}}\b(morning|evening|night|eod)\b",
            low,
        ):
            return _next_weekday_on_or_after(anchor, i).isoformat()
    return None


def resolve_task_due_date(
    raw_due: Optional[str],
    title: str,
    anchor: date,
    evidence: str = "",
) -> Optional[str]:
    """Only mark dues grounded in evidence (or title with intent). Reject bare LLM guesses."""
    evidence = (evidence or "").strip()
    title = (title or "").strip()
    from_evidence = infer_due_date_iso(evidence, anchor) if evidence else None
    if from_evidence:
        return from_evidence

    from_title = infer_due_date_iso(title, anchor) if title else None
    if from_title and evidence and has_deadline_intent(evidence):
        return from_title
    if from_title and not evidence:
        return from_title

    s = (raw_due or "").strip()
    if not s or s.lower() in {"null", "none", "n/a", "-"}:
        return None

    # Absolute ISO from LLM — only if the date appears in evidence, or evidence resolves a relative due
    m = re.fullmatch(r"(20\d{2})-(\d{2})-(\d{2})", s)
    if m:
        iso = s
        if evidence and iso in evidence:
            return iso
        if evidence:
            rel = infer_due_date_iso(evidence, anchor)
            if rel:
                return rel
        return None

    if evidence and has_deadline_intent(evidence):
        return infer_due_date_iso(s, anchor) or infer_due_date_iso(evidence, anchor)
    return None


def infer_due_near_assignee(
    transcript: str,
    assignee: str,
    title: str,
    anchor: date,
) -> Optional[str]:
    """
    Scan transcript for lines about this assignee/title that carry deadline intent.
    Used when the extract evidence snippet missed the date phrase.
    """
    if not (transcript or "").strip():
        return None
    a = (assignee or "").strip().lower()
    first = a.split()[0] if a else ""
    stop = {"with", "from", "that", "this", "will", "have", "into", "using", "make", "create", "setup"}
    title_tokens = [w for w in re.findall(r"[a-z0-9]{3,}", (title or "").lower()) if w not in stop]
    lines = [ln.strip() for ln in transcript.split("\n") if ln.strip()]
    best: Optional[str] = None
    for i, ln in enumerate(lines):
        low = ln.lower()
        hit_person = bool(first) and first in low
        token_hits = sum(1 for t in title_tokens if t in low)
        hit_title = token_hits >= 1 if len(title_tokens) <= 2 else token_hits >= 2
        if not (hit_person or hit_title):
            continue
        window = "\n".join(lines[max(0, i - 2) : i + 4])
        due = infer_due_date_iso(window, anchor) or infer_due_date_iso(ln, anchor)
        if due:
            if hit_person:
                return due
            best = best or due
    return best


def parse_meeting_calendar_from_transcript(
    text: str,
    fallback: Optional[datetime] = None,
) -> Tuple[Optional[datetime], Optional[datetime], Optional[date]]:
    """
    Infer started_at / ended_at / anchor date from transcript clocks and absolute dates.
    Returns (started_at, ended_at, anchor_date).
    """
    fallback = fallback or datetime.now(timezone.utc)
    anchor_day = fallback.date()
    m_date = _ABS_DATE_RE.search(text or "")
    if m_date:
        if m_date.group("y"):
            try:
                anchor_day = date(int(m_date.group("y")), int(m_date.group("mo")), int(m_date.group("d")))
            except ValueError:
                pass
        else:
            d, mo, y = int(m_date.group("d2")), int(m_date.group("mo2")), int(m_date.group("y2"))
            day, month = (d, mo) if d > 12 or mo <= 12 else (mo, d)
            try:
                anchor_day = date(y, month, day)
            except ValueError:
                pass

    clocks: list[Tuple[int, int]] = []
    for m in _CLOCK_RE.finditer(text or ""):
        h = int(m.group("h"))
        minute = int(m.group("m"))
        ampm = (m.group("ampm") or "").upper()
        if ampm == "PM" and h < 12:
            h += 12
        if ampm == "AM" and h == 12:
            h = 0
        clocks.append((h, minute))

    started = ended = None
    if clocks:
        h0, m0 = clocks[0]
        h1, m1 = clocks[-1]
        started = datetime(anchor_day.year, anchor_day.month, anchor_day.day, h0, m0, tzinfo=timezone.utc)
        ended = datetime(anchor_day.year, anchor_day.month, anchor_day.day, h1, m1, tzinfo=timezone.utc)
        if ended < started:
            ended = ended + timedelta(days=1)
    return started, ended, anchor_day
