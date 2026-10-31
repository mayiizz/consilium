import { apiFetch } from "../client";
import { mapWorkspace } from "../mappers";
import type { Workspace } from "../../types";

export async function listWorkspaces(): Promise<Workspace[]> {
  const data = await apiFetch<Record<string, unknown>[]>("/workspaces");
  return data.map((w) => mapWorkspace(w));
}

export async function createWorkspace(name: string): Promise<Workspace> {
  const data = await apiFetch<Record<string, unknown>>("/workspaces", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  return mapWorkspace(data);
}

export async function joinWorkspace(code: string): Promise<Workspace> {
  const data = await apiFetch<Record<string, unknown>>("/workspaces/join", {
    method: "POST",
    body: JSON.stringify({ invite_code: code }),
  });
  return mapWorkspace(data);
}

export async function deleteWorkspace(id: string): Promise<void> {
  await apiFetch(`/workspaces/${id}`, { method: "DELETE" });
}

export async function updateWorkspace(id: string, body: Record<string, unknown>): Promise<Workspace> {
  const data = await apiFetch<Record<string, unknown>>(`/workspaces/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return mapWorkspace(data);
}

export async function regenerateInviteCode(id: string): Promise<string> {
  const data = await apiFetch<{ invite_code: string }>(`/workspaces/${id}/regenerate-code`, {
    method: "POST",
  });
  return data.invite_code;
}

export async function getWorkspace(id: string): Promise<Record<string, unknown>> {
  return apiFetch(`/workspaces/${id}`);
}
