import hashlib
import re
import secrets
import string
from typing import Optional

from app.services.task_key import extract_task_keys as _extract_task_keys
from app.services.task_key import task_key_pattern

TASK_KEY_PATTERN = task_key_pattern()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or secrets.token_hex(4)


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def extract_task_keys(text: str) -> list[str]:
    return _extract_task_keys(text)


def generate_unique_slug(base: str, existing_check) -> str:
    slug = slugify(base)
    candidate = slug
    counter = 1
    while existing_check(candidate):
        candidate = f"{slug}-{counter}"
        counter += 1
    return candidate
