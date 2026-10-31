import { API_BASE, apiFetch } from "../client";

export async function getGitHubStatus(workspaceId: string) {
  return apiFetch<{
    connected: boolean;
    repo?: string;
    webhook_url?: string;
    last_event?: string;
    github_user_login?: string;
    webhook_enabled?: boolean;
    oauth_configured?: boolean;
  }>(`/workspaces/${workspaceId}/github/status`);
}

export function getGitHubOAuthUrl(workspaceId: string) {
  // API_BASE already includes `/api` (e.g. http://127.0.0.1:8000/api)
  return `${API_BASE}/github/connect?workspace_id=${encodeURIComponent(workspaceId)}`;
}

export async function listGitHubRepos(workspaceId: string) {
  return apiFetch<Array<{ id: number; name: string; full_name: string; owner: string; private: boolean }>>(
    `/workspaces/${workspaceId}/github/repos`,
  );
}

export async function selectGitHubRepo(workspaceId: string, owner: string, name: string) {
  return apiFetch(`/workspaces/${workspaceId}/github/repo`, {
    method: "POST",
    body: JSON.stringify({ owner, name }),
  });
}

export async function connectGitHub(workspaceId: string, repo: string, installationId?: string) {
  return apiFetch(`/workspaces/${workspaceId}/github/connect`, {
    method: "POST",
    body: JSON.stringify({ repo, installation_id: installationId ?? "local-dev" }),
  });
}

export async function disconnectGitHub(workspaceId: string) {
  return apiFetch(`/workspaces/${workspaceId}/github/disconnect`, { method: "DELETE" });
}

export async function validateGitTask(workspaceId: string, taskId: string) {
  return apiFetch(`/workspaces/${workspaceId}/github/validate/${taskId}`);
}
