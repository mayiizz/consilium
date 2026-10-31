import hashlib
import hmac
from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.task_key import extract_task_keys

logger = get_logger(__name__)


def verify_github_signature(payload: bytes, signature: Optional[str], secret: str) -> bool:
    if not signature or not secret:
        return False
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def get_webhook_secret(workspace_secret: Optional[str] = None) -> str:
    settings = get_settings()
    return workspace_secret or settings.github_webhook_secret or ""


def parse_task_key_from_payload(payload: dict, event_type: str = "") -> Optional[str]:
    keys = parse_task_keys_from_payload(payload, event_type)
    return keys[0] if keys else None


def parse_task_keys_from_payload(payload: dict, event_type: str = "") -> List[str]:
    text_parts: List[str] = []
    if event_type == "check_run":
        check_run = payload.get("check_run", {})
        text_parts.extend([check_run.get("name", ""), check_run.get("output", {}).get("title", "") or ""])
    if "pull_request" in payload:
        pr = payload["pull_request"]
        text_parts.extend([pr.get("title", ""), pr.get("body", "") or ""])
    if "head_commit" in payload:
        commit = payload["head_commit"]
        text_parts.extend([commit.get("message", "")])
    for c in payload.get("commits") or []:
        text_parts.append(c.get("message", "") or "")
    return extract_task_keys(" ".join(text_parts))


def is_pr_merged(payload: dict) -> bool:
    if payload.get("action") != "closed":
        return False
    pr = payload.get("pull_request", {})
    return bool(pr.get("merged"))


def get_ci_status(payload: dict) -> str:
    if payload.get("workflow_run"):
        wr = payload["workflow_run"]
        conclusion = (wr.get("conclusion") or "").strip().lower()
        if conclusion == "success":
            return "passed"
        if conclusion == "failure":
            return "failed"
        return conclusion or "pending"
    check_run = payload.get("check_run", {})
    conclusion = check_run.get("conclusion")
    if conclusion == "success":
        return "passed"
    if conclusion == "failure":
        return "failed"
    status = check_run.get("status")
    if status == "completed":
        return conclusion or "unknown"
    return "pending"
