from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from beanie import PydanticObjectId
from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.integrations.github_app import (
    get_webhook_secret,
    parse_task_keys_from_payload,
    verify_github_signature,
)
from app.models.github_webhook_event import GitHubWebhookEvent
from app.models.task import Task
from app.models.workspace import Workspace
from app.schemas import GitHubConnectRequest, GitHubRepoResponse, GitHubRepoSelectionRequest, GitHubStatusResponse
from app.services.permissions import get_workspace_or_404, require_workspace_lead


class GitHubService:
    def _webhook_url(self) -> str:
        settings = get_settings()
        base = (settings.github_redirect_uri or "").strip()
        if base and "/api/github/callback" in base:
            return base.replace("/api/github/callback", "/github/webhook")
        return "http://localhost:8000/github/webhook"

    async def connect(
        self, workspace_id: str, user_id: PydanticObjectId, data: GitHubConnectRequest
    ) -> GitHubStatusResponse:
        await require_workspace_lead(workspace_id, user_id)
        ws = await get_workspace_or_404(workspace_id)
        ws.github_app_installation_id = data.installation_id
        ws.github_repo = data.repo
        ws.github_webhook_enabled = True
        ws.updated_at = datetime.now(timezone.utc)
        await ws.save()
        return self._status_response(ws)

    async def disconnect(self, workspace_id: str, user_id: PydanticObjectId) -> GitHubStatusResponse:
        await require_workspace_lead(workspace_id, user_id)
        ws = await get_workspace_or_404(workspace_id)
        ws.github_app_installation_id = None
        ws.github_repo = None
        ws.github_webhook_secret = None
        ws.github_access_token = None
        ws.github_user_login = None
        ws.github_webhook_enabled = False
        ws.updated_at = datetime.now(timezone.utc)
        await ws.save()
        return GitHubStatusResponse(connected=False, webhook_url=self._webhook_url())

    def _status_response(self, ws: Workspace) -> GitHubStatusResponse:
        settings = get_settings()
        connected = bool(ws.github_access_token or ws.github_app_installation_id or ws.github_repo)
        return GitHubStatusResponse(
            connected=connected,
            repo=ws.github_repo,
            installation_id=ws.github_app_installation_id,
            webhook_url=self._webhook_url(),
            last_event=ws.github_webhook_last_event,
            github_user_login=ws.github_user_login,
            webhook_enabled=ws.github_webhook_enabled,
            oauth_configured=bool(settings.github_client_id and settings.github_redirect_uri),
        )

    async def status(self, workspace_id: str, user_id: PydanticObjectId) -> GitHubStatusResponse:
        await require_workspace_lead(workspace_id, user_id)
        ws = await get_workspace_or_404(workspace_id)
        return self._status_response(ws)

    async def oauth_connect_url(self, workspace_id: str) -> RedirectResponse:
        settings = get_settings()
        if not (settings.github_client_id and settings.github_redirect_uri):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_REDIRECT_URI.",
            )
        params = {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri.strip(),
            "scope": "repo read:user",
            "state": workspace_id,
        }
        url = "https://github.com/login/oauth/authorize?" + urlencode(params)
        return RedirectResponse(url)

    async def oauth_callback(self, code: str, state: str) -> RedirectResponse:
        settings = get_settings()
        if not settings.github_client_id or not settings.github_client_secret:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="GitHub OAuth not configured")

        workspace_id = state.strip()
        try:
            ws_oid = PydanticObjectId(workspace_id)
        except Exception:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid workspace id in state")

        ws = await Workspace.get(ws_oid)
        if not ws or ws.deleted_at:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri.strip(),
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Failed to obtain access token")

            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_resp.raise_for_status()
            user = user_resp.json()

        ws.github_access_token = access_token
        ws.github_user_login = user.get("login")
        ws.github_app_installation_id = ws.github_app_installation_id or "oauth"
        ws.updated_at = datetime.now(timezone.utc)
        await ws.save()

        base = (settings.frontend_url or "http://localhost:5173").rstrip("/")
        redirect_url = f"{base}/business/manager/workspaces/{workspace_id}/integrations?github=connected"
        return RedirectResponse(redirect_url)

    async def _require_token(self, workspace_id: str, user_id: PydanticObjectId) -> tuple[Workspace, str]:
        await require_workspace_lead(workspace_id, user_id)
        ws = await get_workspace_or_404(workspace_id)
        token = (ws.github_access_token or "").strip()
        if not token:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="GitHub is not connected for this workspace")
        return ws, token

    async def list_repos(self, workspace_id: str, user_id: PydanticObjectId) -> List[GitHubRepoResponse]:
        _, token = await self._require_token(workspace_id, user_id)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user/repos?per_page=100&sort=updated",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            )
            resp.raise_for_status()
            repos = resp.json()
        return [
            GitHubRepoResponse(
                id=r.get("id"),
                name=r.get("name"),
                full_name=r.get("full_name"),
                owner=(r.get("owner") or {}).get("login") or "",
                private=bool(r.get("private")),
            )
            for r in repos
        ]

    async def select_repo(
        self, workspace_id: str, user_id: PydanticObjectId, data: GitHubRepoSelectionRequest
    ) -> GitHubStatusResponse:
        ws, token = await self._require_token(workspace_id, user_id)
        async with httpx.AsyncClient() as client:
            repo_resp = await client.get(
                f"https://api.github.com/repos/{data.owner}/{data.name}",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            )
            repo_resp.raise_for_status()
            repo = repo_resp.json()

        ws.github_repo = (repo.get("full_name") or "").strip().lower() or None
        ws.github_webhook_enabled = True
        ws.updated_at = datetime.now(timezone.utc)
        await ws.save()
        return self._status_response(ws)

    async def handle_webhook(self, request: Request) -> Dict[str, Any]:
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256")
        delivery_id = request.headers.get("X-GitHub-Delivery", "")
        event_type = request.headers.get("X-GitHub-Event", "unknown")

        if event_type == "ping":
            return {"status": "ok", "event": "ping"}

        existing = await GitHubWebhookEvent.find_one(GitHubWebhookEvent.delivery_id == delivery_id)
        if existing:
            return {"status": "duplicate", "delivery_id": delivery_id}

        import json

        payload = json.loads(body)
        repo_full = (payload.get("repository", {}).get("full_name") or "").strip().lower()
        workspace = None
        if repo_full:
            workspace = await Workspace.find_one(
                Workspace.github_repo == repo_full,
                Workspace.deleted_at == None,
            )
            if not workspace:
                # Legacy workspaces may have stored mixed-case full_name.
                async for candidate in Workspace.find(Workspace.deleted_at == None):
                    if (candidate.github_repo or "").strip().lower() == repo_full:
                        candidate.github_repo = repo_full
                        await candidate.save()
                        workspace = candidate
                        break
        secret = get_webhook_secret(workspace.github_webhook_secret if workspace else None)
        if secret and not verify_github_signature(body, signature, secret):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

        ws_id = workspace.id if workspace else PydanticObjectId()
        event = GitHubWebhookEvent(
            workspace_id=ws_id,
            event_type=event_type,
            delivery_id=delivery_id or f"unknown-{datetime.now(timezone.utc).timestamp()}",
            payload=payload,
        )

        sync_result = None
        task_keys: List[str] = []
        if workspace:
            from app.services.github_kanban_sync import handle_event

            sync_result = await handle_event(payload, workspace, event_type)
            task_keys = list(sync_result.task_keys or [])
            if not task_keys:
                task_keys = parse_task_keys_from_payload(payload, event_type)

            if event_type == "workflow_run" and sync_result.extra.get("pr"):
                payload = {**payload, "_resolved_pr": sync_result.extra["pr"]}

            workspace.github_webhook_last_event = event_type
            workspace.github_webhook_last_at = datetime.now(timezone.utc)
            await workspace.save()

            task = None
            if task_keys:
                task = await Task.find_one(
                    Task.workspace_id == workspace.id,
                    Task.task_key == task_keys[0].upper(),
                    Task.deleted_at == None,
                )
                if task:
                    event.task_id = task.id

        event.task_key = task_keys[0] if task_keys else None
        event.processed = True
        event.processed_at = datetime.now(timezone.utc)
        await event.insert()

        return {
            "status": "ok",
            "task_keys": task_keys,
            "sync": {
                "skipped": sync_result.skipped if sync_result else None,
                "tasks_updated": sync_result.tasks_updated if sync_result else 0,
            },
        }


github_service = GitHubService()
