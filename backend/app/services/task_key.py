"""Stable per-task keys for Git commit/PR references (e.g. MM-A1B2C3D4)."""
from __future__ import annotations

import re
from typing import List, Set

from app.core.config import get_settings


def task_key_prefix() -> str:
    settings = get_settings()
    p = (settings.github_task_key_prefix or "MM").strip().upper()
    return re.sub(r"[^A-Z0-9]", "", p) or "MM"


def task_key_pattern() -> re.Pattern[str]:
    pref = re.escape(task_key_prefix())
    return re.compile(rf"\b{pref}-[A-Z0-9]{{8,32}}\b", re.IGNORECASE)


def extract_task_keys(text: str) -> List[str]:
    if not (text or "").strip():
        return []
    pat = task_key_pattern()
    seen: Set[str] = set()
    out: List[str] = []
    for m in pat.finditer(text):
        raw = m.group(0).upper()
        if raw not in seen:
            seen.add(raw)
            out.append(raw)
    return out


def generate_task_key_suffix(length: int = 8) -> str:
    import secrets
    import string

    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def ensure_task_key_on_task(task) -> str:
    """Ensure Beanie Task has a persisted task_key; return canonical key."""
    from app.core.security import generate_task_key
    from app.models.task import Task

    if (task.task_key or "").strip():
        return task.task_key.upper()
    key = generate_task_key()
    while await Task.find_one(Task.task_key == key):
        key = generate_task_key()
    task.task_key = key
    await task.save()
    return key
