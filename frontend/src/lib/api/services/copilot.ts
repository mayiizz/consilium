import { apiFetch } from "../client";

export async function sendCopilotMessage(workspaceId: string, message: string, meetingId?: string) {
  return apiFetch<{
    message_id: string;
    role: string;
    content: string;
    timestamp: string;
    kanban_refresh?: {
      meetings?: number;
      created?: number;
      updated?: number;
      review_required?: number;
      deleted?: number;
    };
  }>(`/workspaces/${workspaceId}/copilot/chat`, {
    method: "POST",
    body: JSON.stringify({ message, meeting_id: meetingId }),
  });
}

export async function sendCopilotFeedback(workspaceId: string, messageId: string, feedback: "up" | "down") {
  return apiFetch("/copilot/feedback", {
    method: "POST",
    body: JSON.stringify({ workspace_id: workspaceId, message_id: messageId, feedback }),
  });
}

export async function getCopilotHistory(workspaceId: string) {
  const data = await apiFetch<{ messages: Array<{ role: string; content: string; message_id: string }> }>(
    `/workspaces/${workspaceId}/copilot/history`,
  );
  return data.messages ?? [];
}
