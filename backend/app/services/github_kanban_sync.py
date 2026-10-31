"""GitHub webhook handling: map repo → workspace, parse task keys, CI (workflow_run), merge → DONE + git_evidence."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from beanie import PydanticObjectId

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.task import GitEvidenceEntry, Task, TaskStatus
from app.models.workspace import Workspace
from app.services.task_key import extract_task_keys

logger = get_logger(__name__)

_DONE_KW = re.compile(r"(?i)\b(fix|closes|complete|done)\b")


@dataclass
class GitHubSyncResult:
    ok: bool = True
    skipped: Optional[str] = None
    event: Optional[str] = None
    task_keys: List[str] = field(default_factory=list)
    tasks_updated: int = 0
    tasks_finalized_after_ci: int = 0
    sync_already_applied_status: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


def _github_headers(token: str) -> Dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token.strip()}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _github_get_pull(owner: str, repo: str, number: int, token: str) -> Optional[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{int(number)}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=_github_headers(token))
    except Exception as e:
        logger.warning("GitHub GET pull failed: %s", e)
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception:
        return None


async def _github_list_pulls_for_commit(
    owner: str, repo: str, commit_sha: str, token: str
) -> List[dict]:
    if not commit_sha:
        return []
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/pulls"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers=_github_headers(token))
    except Exception as e:
        logger.warning("GitHub list pulls for commit failed: %s", e)
        return []
    if r.status_code != 200:
        return []
    try:
        data = r.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


async def _resolve_pr_for_workflow_run(
    payload: dict, owner: str, repo: str, token: str
) -> Optional[dict]:
    wr = payload.get("workflow_run") or {}
    head_sha = (wr.get("head_sha") or "").strip()
    embedded = wr.get("pull_requests") or []
    if isinstance(embedded, list) and embedded:
        num = embedded[0].get("number")
        if isinstance(num, int) and token:
            pr = await _github_get_pull(owner, repo, num, token)
            if pr:
                return pr
    if token and head_sha:
        pulls = await _github_list_pulls_for_commit(owner, repo, head_sha, token)
        for p in pulls:
            num = p.get("number")
            if isinstance(num, int):
                pr = await _github_get_pull(owner, repo, num, token)
                if pr:
                    return pr
    return None


def _repo_full_name(payload: dict) -> str:
    repo = payload.get("repository") or {}
    return (repo.get("full_name") or "").strip().lower()


def _workflow_name_allowed(name: str) -> bool:
    settings = get_settings()
    raw = (settings.github_ci_workflow_name_allowlist or "").strip()
    if not raw:
        return True
    allowed = {x.strip().lower() for x in raw.split(",") if x.strip()}
    return (name or "").strip().lower() in allowed


def _require_ci_for_done(ws: Workspace) -> bool:
    settings = get_settings()
    if ws.settings.require_ci_pass:
        return True
    return bool(settings.github_require_ci_success_for_done)


def _require_pr_merge(ws: Workspace) -> bool:
    if ws.settings.push_mode_enabled:
        return False
    return ws.settings.require_pr_merge


def _evidence_entry(
    *,
    event: str,
    sha: Optional[str],
    url: Optional[str],
    actor: str,
    message: str,
) -> GitEvidenceEntry:
    return GitEvidenceEntry(
        source="github",
        event=event,
        sha=sha or "",
        url=url or "",
        actor=actor or "",
        message=(message or "")[:2000],
        at=datetime.now(timezone.utc),
    )


def _append_evidence(task: Task, entry: GitEvidenceEntry) -> None:
    task.git_evidence.log.append(entry)
    if len(task.git_evidence.log) > 20:
        task.git_evidence.log = task.git_evidence.log[-20:]


async def _find_tasks_by_keys(workspace_id: PydanticObjectId, keys: List[str]) -> List[Task]:
    out: List[Task] = []
    for key in keys:
        k = (key or "").strip().upper()
        if not k:
            continue
        task = await Task.find_one(
            Task.workspace_id == workspace_id,
            Task.task_key == k,
            Task.deleted_at == None,
        )
        if task:
            out.append(task)
    return out


async def _mark_tasks_done(
    workspace_id: PydanticObjectId,
    keys: List[str],
    evidence: GitEvidenceEntry,
    pr: Optional[dict] = None,
) -> int:
    now = datetime.now(timezone.utc)
    n = 0
    for key in keys:
        k = (key or "").strip().upper()
        if not k:
            continue
        task = await Task.find_one(
            Task.workspace_id == workspace_id,
            Task.task_key == k,
            Task.deleted_at == None,
        )
        if not task or task.status == TaskStatus.DONE:
            continue
        task.status = TaskStatus.DONE
        task.updated_at = now
        if pr:
            task.git_evidence.pr_number = pr.get("number")
            task.git_evidence.pr_url = pr.get("html_url")
            task.git_evidence.pr_title = pr.get("title")
            task.git_evidence.merged_at = now
            task.git_evidence.merged_by = (pr.get("merged_by") or {}).get("login")
            task.git_evidence.commit_sha = pr.get("merge_commit_sha") or (
                (pr.get("head") or {}).get("sha")
            )
        _append_evidence(task, evidence)
        await task.save()
        n += 1
    return n


async def _finalize_gated_merge(
    workspace_id: PydanticObjectId,
    keys: List[str],
    pr: dict,
    merge_evidence: GitEvidenceEntry,
) -> int:
    head_sha = ((pr.get("head") or {}).get("sha") or "").strip()
    if not head_sha:
        return 0
    n = 0
    for key in keys:
        k = (key or "").strip().upper()
        if not k:
            continue
        task = await Task.find_one(
            Task.workspace_id == workspace_id,
            Task.task_key == k,
            Task.deleted_at == None,
        )
        if not task or task.status == TaskStatus.DONE:
            continue
        if (task.git_evidence.github_ci_conclusion or "").lower() != "success":
            continue
        if (task.git_evidence.github_ci_head_sha or "").strip() != head_sha:
            continue
        task.status = TaskStatus.DONE
        task.updated_at = datetime.now(timezone.utc)
        task.git_evidence.pr_number = pr.get("number")
        task.git_evidence.pr_url = pr.get("html_url")
        task.git_evidence.pr_title = pr.get("title")
        task.git_evidence.merged_at = datetime.now(timezone.utc)
        task.git_evidence.merged_by = (pr.get("merged_by") or {}).get("login")
        task.git_evidence.commit_sha = pr.get("merge_commit_sha") or head_sha
        _append_evidence(task, merge_evidence)
        await task.save()
        n += 1
    return n


async def _apply_workflow_ci_to_tasks(
    workspace_id: PydanticObjectId,
    keys: List[str],
    head_sha: str,
    conclusion: str,
    workflow_run_id: Optional[int],
    workflow_url: str,
    workflow_name: str,
    actor: str,
) -> None:
    now = datetime.now(timezone.utc)
    ev = _evidence_entry(
        event="workflow_run",
        sha=head_sha,
        url=workflow_url,
        actor=actor,
        message=f"{workflow_name}: {conclusion}",
    )
    ci_status = "passed" if conclusion == "success" else "failed" if conclusion == "failure" else conclusion
    for key in keys:
        k = (key or "").strip().upper()
        if not k:
            continue
        task = await Task.find_one(
            Task.workspace_id == workspace_id,
            Task.task_key == k,
            Task.deleted_at == None,
        )
        if not task:
            continue
        task.git_evidence.github_ci_head_sha = head_sha
        task.git_evidence.github_ci_conclusion = conclusion
        task.git_evidence.github_ci_updated_at = now
        task.git_evidence.github_ci_workflow_url = workflow_url or ""
        if workflow_run_id is not None:
            task.git_evidence.github_ci_workflow_run_id = workflow_run_id
        task.git_evidence.ci_status = ci_status
        task.git_evidence.ci_url = workflow_url
        task.updated_at = now
        _append_evidence(task, ev)
        if conclusion == "failure" and task.status != TaskStatus.DONE:
            task.status = TaskStatus.BLOCKERS
        await task.save()


async def _handle_pull_request(ws: Workspace, payload: dict) -> GitHubSyncResult:
    settings = get_settings()
    pr = payload.get("pull_request") or {}
    action = (payload.get("action") or "").strip()
    if action != "closed":
        return GitHubSyncResult(skipped="pr_not_closed")

    merged = bool(pr.get("merged"))
    pat = (settings.github_pat or ws.github_access_token or "").strip()
    repo_name = _repo_full_name(payload)
    owner, repo = "", ""
    if repo_name and "/" in repo_name:
        owner, repo = repo_name.split("/", 1)
    if pat and owner and repo:
        num = pr.get("number")
        if isinstance(num, int):
            api_merged = await _github_get_pull(owner, repo, num, pat)
            if api_merged is not None:
                merged = bool(api_merged.get("merged"))

    if not merged:
        return GitHubSyncResult(skipped="pr_not_merged")

    text = f"{pr.get('title') or ''}\n{pr.get('body') or ''}"
    keys = extract_task_keys(text)
    if not keys:
        return GitHubSyncResult(skipped="no_task_keys_in_pr")

    actor = (payload.get("sender") or {}).get("login") or ""
    merge_ev = _evidence_entry(
        event="pull_request",
        sha=pr.get("merge_commit_sha") or (pr.get("head") or {}).get("sha"),
        url=pr.get("html_url"),
        actor=actor,
        message=pr.get("title") or "",
    )

    if not _require_ci_for_done(ws):
        updated = await _mark_tasks_done(ws.id, keys, merge_ev, pr=pr)
        return GitHubSyncResult(
            event="pull_request",
            task_keys=keys,
            tasks_updated=updated,
            sync_already_applied_status=updated > 0,
        )

    updated = await _finalize_gated_merge(ws.id, keys, pr, merge_ev)
    for key in keys:
        task = await Task.find_one(
            Task.workspace_id == ws.id, Task.task_key == key.upper(), Task.deleted_at == None
        )
        if task:
            task.git_evidence.pr_number = pr.get("number")
            task.git_evidence.pr_url = pr.get("html_url")
            task.git_evidence.pr_title = pr.get("title")
            _append_evidence(task, merge_ev)
            await task.save()

    return GitHubSyncResult(
        event="pull_request",
        task_keys=keys,
        tasks_updated=updated,
        sync_already_applied_status=updated > 0,
        extra={"ci_gate": True},
    )


async def _handle_workflow_run(ws: Workspace, payload: dict) -> GitHubSyncResult:
    settings = get_settings()
    action = (payload.get("action") or "").strip()
    if action != "completed":
        return GitHubSyncResult(skipped="workflow_run_not_completed")

    wr = payload.get("workflow_run") or {}
    wf_name = (wr.get("name") or "").strip()
    if not _workflow_name_allowed(wf_name):
        return GitHubSyncResult(skipped="workflow_name_not_allowlisted", extra={"workflow": wf_name})

    conclusion = (wr.get("conclusion") or "").strip().lower()
    if not conclusion:
        return GitHubSyncResult(skipped="no_conclusion")

    head_sha = (wr.get("head_sha") or "").strip()
    if not head_sha:
        return GitHubSyncResult(skipped="no_head_sha")

    repo_name = _repo_full_name(payload)
    if not repo_name or "/" not in repo_name:
        return GitHubSyncResult(skipped="no_repo")
    owner, repo = repo_name.split("/", 1)
    pat = (settings.github_pat or ws.github_access_token or "").strip()

    pr = await _resolve_pr_for_workflow_run(payload, owner, repo, pat) if pat else None
    if not pr:
        return GitHubSyncResult(skipped="no_pr_context_for_workflow")

    pr_head = ((pr.get("head") or {}).get("sha") or "").strip()
    title = pr.get("title") or ""
    body = pr.get("body") or ""
    keys = extract_task_keys(f"{title}\n{body}")
    if not keys:
        return GitHubSyncResult(skipped="no_task_keys_in_pr", extra={"workflow": wf_name})

    wf_id = wr.get("id")
    wf_run_id = int(wf_id) if isinstance(wf_id, int) else None
    wf_url = (wr.get("html_url") or "").strip()
    actor_obj = wr.get("actor") or payload.get("sender") or {}
    actor = actor_obj.get("login") if isinstance(actor_obj, dict) else ""

    if conclusion in ("success", "failure"):
        await _apply_workflow_ci_to_tasks(
            ws.id,
            keys,
            head_sha,
            "success" if conclusion == "success" else "failure",
            wf_run_id,
            wf_url,
            wf_name,
            actor if isinstance(actor, str) else "",
        )

    result = GitHubSyncResult(
        event="workflow_run",
        task_keys=keys,
        extra={"conclusion": conclusion, "workflow": wf_name, "pr": pr},
    )

    if conclusion == "success" and _require_ci_for_done(ws) and pat:
        merge_ev = _evidence_entry(
            event="pull_request",
            sha=pr.get("merge_commit_sha") or pr_head or head_sha,
            url=pr.get("html_url"),
            actor=actor if isinstance(actor, str) else "",
            message=title,
        )
        done_n = await _finalize_gated_merge(ws.id, keys, pr, merge_ev)
        result.tasks_finalized_after_ci = done_n
        result.tasks_updated = done_n
        result.sync_already_applied_status = done_n > 0

    return result


async def _handle_push(ws: Workspace, payload: dict) -> GitHubSyncResult:
    settings = get_settings()
    require_pr = _require_pr_merge(ws) and settings.github_require_pr_merge_for_done

    repo = payload.get("repository") or {}
    default = (repo.get("default_branch") or "main").strip()
    ref = (payload.get("ref") or "").strip()
    # Still attach commit evidence on feature branches; only Done-on-push is default-branch gated.
    on_default = ref == f"refs/heads/{default}"

    actor = (payload.get("pusher") or {}).get("name") or (payload.get("sender") or {}).get("login") or ""
    updated_total = 0
    evidence_total = 0
    keys_hit: List[str] = []

    for c in payload.get("commits") or []:
        msg = c.get("message") or ""
        keys = extract_task_keys(msg)
        if not keys:
            continue
        ev = _evidence_entry(
            event="push",
            sha=c.get("id"),
            url=c.get("url"),
            actor=actor,
            message=msg.split("\n", 1)[0].strip(),
        )
        # Always attach commit activity when the task key is present.
        tasks = await _find_tasks_by_keys(ws.id, keys)
        for task in tasks:
            _append_evidence(task, ev)
            if c.get("id"):
                task.git_evidence.commit_sha = str(c.get("id"))
            task.last_activity_at = datetime.now(timezone.utc)
            task.updated_at = datetime.now(timezone.utc)
            await task.save()
            evidence_total += 1
            keys_hit.append(task.task_key)

        # Mark Done only when keywords appear and push-mode / PR-merge settings allow it.
        if on_default and _DONE_KW.search(msg) and not require_pr:
            updated_total += await _mark_tasks_done(ws.id, keys, ev)

    if not keys_hit:
        return GitHubSyncResult(skipped="push_no_matching_commits")
    return GitHubSyncResult(
        event="push",
        task_keys=keys_hit,
        tasks_updated=max(updated_total, evidence_total),
        sync_already_applied_status=updated_total > 0,
        extra={"evidence_appended": evidence_total, "marked_done": updated_total},
    )


async def handle_event(
    payload: dict,
    workspace: Workspace,
    event_type: str,
) -> GitHubSyncResult:
    if not getattr(workspace.settings, "git_enabled", True):
        return GitHubSyncResult(skipped="git_disabled")
    if not workspace.github_webhook_enabled and not workspace.github_repo:
        return GitHubSyncResult(skipped="webhook_not_enabled")

    if event_type == "pull_request":
        return await _handle_pull_request(workspace, payload)
    if event_type == "workflow_run":
        return await _handle_workflow_run(workspace, payload)
    if event_type == "push":
        return await _handle_push(workspace, payload)
    return GitHubSyncResult(skipped="unsupported_event", extra={"event": event_type})


def extract_keys_from_payload(payload: dict, event_type: str, resolved_pr: Optional[dict] = None) -> List[str]:
    """Extract task keys from webhook payload (including workflow_run via resolved PR)."""
    if event_type == "workflow_run" and resolved_pr:
        text = f"{resolved_pr.get('title') or ''}\n{resolved_pr.get('body') or ''}"
        return extract_task_keys(text)
    text_parts: List[str] = []
    if "pull_request" in payload:
        pr = payload["pull_request"]
        text_parts.extend([pr.get("title", ""), pr.get("body", "") or ""])
    if "head_commit" in payload:
        commit = payload["head_commit"]
        text_parts.extend([commit.get("message", "")])
    for c in payload.get("commits") or []:
        text_parts.append(c.get("message", "") or "")
    return extract_task_keys(" ".join(text_parts))
