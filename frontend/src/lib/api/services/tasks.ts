import { apiFetch } from "../client";
import { mapTask, mapTaskStatusToApi } from "../mappers";
import type { Task, TaskStatus } from "../../types";

export async function listTasks(workspaceId: string): Promise<Task[]> {
  const data = await apiFetch<Record<string, unknown>[]>(`/workspaces/${workspaceId}/tasks`);
  return data.map((t) => mapTask(t));
}

export async function moveTask(taskId: string, status: TaskStatus): Promise<Task> {
  const data = await apiFetch<Record<string, unknown>>(`/tasks/${taskId}/move`, {
    method: "POST",
    body: JSON.stringify({ status: mapTaskStatusToApi(status) }),
  });
  return mapTask(data);
}

export interface ExtractTasksResponse {
  message: string;
  job_id?: string;
  result?: {
    meetings?: number;
    created?: number;
    updated?: number;
    review_required?: number;
    deleted?: number;
  };
}

export async function extractTasks(workspaceId: string): Promise<ExtractTasksResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/extract`, { method: "POST" });
}

/** Re-run RAG + board sync without a full fresh wipe of review state. */
export async function rebuildTasks(workspaceId: string): Promise<ExtractTasksResponse> {
  return apiFetch(`/workspaces/${workspaceId}/tasks/rebuild`, { method: "POST" });
}

export interface UpdateTaskPayload {
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  priority?: string;
  assignee_id?: string | null;
  assignee_name?: string | null;
  due_date?: string | null;
  blocker_reason?: string | null;
}

export async function updateTask(taskId: string, data: UpdateTaskPayload): Promise<Task> {
  const body: Record<string, unknown> = { ...data };
  if (data.status) {
    body.status = mapTaskStatusToApi(data.status);
  }
  const res = await apiFetch<Record<string, unknown>>(`/tasks/${taskId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return mapTask(res);
}

export async function createTask(workspaceId: string, title: string): Promise<Task> {
  const data = await apiFetch<Record<string, unknown>>(`/workspaces/${workspaceId}/tasks`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });
  return mapTask(data);
}
