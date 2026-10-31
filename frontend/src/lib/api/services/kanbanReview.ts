import { apiFetch } from "../client";

export interface KanbanReviewItem {
  id: string;
  meeting_id?: string | null;
  candidate: {
    title?: string;
    assignee?: string;
    confidence?: number;
    evidence?: string;
    status?: string;
    due_date?: string;
  };
  reason: string;
  created_at?: string;
}

export async function listKanbanReviewQueue(workspaceId: string): Promise<KanbanReviewItem[]> {
  const data = await apiFetch<{ items: KanbanReviewItem[] }>(
    `/workspaces/${workspaceId}/kanban/review-queue`,
  );
  return data.items ?? [];
}

export async function approveKanbanReview(workspaceId: string, reviewId: string): Promise<{ task_id?: string }> {
  return apiFetch(`/workspaces/${workspaceId}/kanban/review-queue/${reviewId}/approve`, {
    method: "POST",
  });
}

export async function rejectKanbanReview(workspaceId: string, reviewId: string): Promise<void> {
  await apiFetch(`/workspaces/${workspaceId}/kanban/review-queue/${reviewId}/reject`, {
    method: "POST",
  });
}
