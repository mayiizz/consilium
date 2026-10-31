"""
Deterministic transcription cleaning helpers.
"""
from __future__ import annotations

import re
from typing import Iterable

_FILLER_PHRASES: list[str] = [
    "am i audible",
    "okay guys",
    "good morning",
    "yes",
    "okay",
]

_COMMON_STT_ERRORS: dict[str, str] = {
    "project score": "project scope",
    "december": "testing",
}


def _normalize_sentence(s: str) -> str:
    t = (s or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", "", t)
    return t.strip()


def _apply_common_corrections(text: str) -> str:
    out = text
    for wrong, right in _COMMON_STT_ERRORS.items():
        out = re.sub(rf"\b{re.escape(wrong)}\b", right, out, flags=re.IGNORECASE)
    return out


def _remove_filler_sentences(sentences: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for s in sentences:
        t = (s or "").strip()
        if not t:
            continue
        t_norm = t.lower()
        if any(fp in t_norm for fp in _FILLER_PHRASES):
            for fp in _FILLER_PHRASES:
                if fp in t_norm:
                    t = re.sub(rf"(?i)\b{re.escape(fp)}\b[,:;]?\s*", "", t).strip()
            if not t:
                continue
        cleaned.append(t)
    return cleaned


def clean_transcription_text(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    t = re.sub(r"\s+", " ", raw)
    t = _apply_common_corrections(t)
    parts = re.split(r"[\n]+|(?<=[.!?])\s+", t)
    parts = [p.strip() for p in parts if (p or "").strip()]
    parts = _remove_filler_sentences(parts)
    deduped: list[str] = []
    seen: set[str] = set()
    for p in parts:
        norm = _normalize_sentence(p)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        deduped.append(p)
    return " ".join(deduped).strip()
