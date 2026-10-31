import { apiFetch } from "../client";

export type AppNotification = {
  id: string;
  workspaceId: string;
  type: string;
  title: string;
  body: string;
  taskId?: string | null;
  researchJobId?: string | null;
  readAt?: string | null;
  createdAt: string;
};

export type NotificationList = {
  items: AppNotification[];
  unreadCount: number;
  total: number;
};

function mapNotification(raw: Record<string, unknown>): AppNotification {
  return {
    id: String(raw.id),
    workspaceId: String(raw.workspace_id),
    type: String(raw.type),
    title: String(raw.title ?? ""),
    body: String(raw.body ?? ""),
    taskId: raw.task_id ? String(raw.task_id) : null,
    researchJobId: raw.research_job_id ? String(raw.research_job_id) : null,
    readAt: raw.read_at ? String(raw.read_at) : null,
    createdAt: String(raw.created_at),
  };
}

export async function listNotifications(): Promise<NotificationList> {
  const data = await apiFetch<Record<string, unknown>>("/notifications");
  const items = ((data.items as Record<string, unknown>[]) ?? []).map(mapNotification);
  return {
    items,
    unreadCount: Number(data.unread_count ?? 0),
    total: Number(data.total ?? items.length),
  };
}

export async function markNotificationRead(id: string): Promise<AppNotification> {
  const data = await apiFetch<Record<string, unknown>>(`/notifications/${id}/read`, {
    method: "POST",
  });
  return mapNotification(data);
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiFetch("/notifications/read-all", { method: "POST" });
}
