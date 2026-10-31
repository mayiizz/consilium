import { apiFetch } from "../client";
import { mapDocument, mapMember, mapMeeting, mapRisk, mapRoadmapPhase, mapTask } from "../mappers";
import type { Document, Member, Meeting, Risk, RoadmapPhase, Task, TaskStatus } from "../../types";
import { mapTaskStatus } from "../mappers";

export interface DashboardData {
  liveMeeting?: Meeting;
  upcomingMeetings: Meeting[];
  recentMeetings: Meeting[];
  members: Member[];
  teamScore: number;
  taskCounts: Record<TaskStatus, number>;
  overdue: number;
}

export async function fetchDashboard(workspaceId: string): Promise<DashboardData> {
  const data = await apiFetch<Record<string, unknown>>(`/workspaces/${workspaceId}/dashboard`);
  const stats = data.stats as Record<string, unknown>;
  const byStatus = (stats.tasks_by_status as Record<string, number>) ?? {};
  const taskCounts: Record<TaskStatus, number> = {
    todo: byStatus["To Do"] ?? 0,
    in_progress: byStatus["In Progress"] ?? 0,
    in_review: byStatus["In Review"] ?? 0,
    done: byStatus["Done"] ?? 0,
    blocked: byStatus["Blockers"] ?? 0,
  };
  return {
    liveMeeting: data.live_meeting ? mapMeeting(data.live_meeting as Record<string, unknown>) : undefined,
    upcomingMeetings: ((data.upcoming_meetings as Record<string, unknown>[]) ?? []).map(mapMeeting),
    recentMeetings: ((data.recent_meetings as Record<string, unknown>[]) ?? []).map(mapMeeting),
    members: ((data.members as Record<string, unknown>[]) ?? []).map(mapMember),
    teamScore: Number(data.team_score ?? 0),
    taskCounts,
    overdue: Number(stats.overdue_tasks ?? 0),
  };
}

export async function fetchAnalytics(workspaceId: string) {
  return apiFetch<{
    velocity: Array<{ week: string; completed: number }>;
    burndown: Array<{ week: string; planned: number; completed: number; remaining?: number }>;
    tasks_by_assignee: Record<string, number>;
    meeting_stats: {
      total?: number;
      scheduled?: number;
      live?: number;
      ended?: number;
      cancelled?: number;
      tasks_total?: number;
      tasks_done?: number;
    };
  }>(`/workspaces/${workspaceId}/analytics`);
}

export async function fetchRoadmap(workspaceId: string): Promise<RoadmapPhase[]> {
  const data = await apiFetch<{ phases: Record<string, unknown>[] }>(`/workspaces/${workspaceId}/roadmap`);
  return (data.phases ?? []).map(mapRoadmapPhase);
}

export async function fetchRisks(workspaceId: string): Promise<Risk[]> {
  const data = await apiFetch<{ risks: Record<string, unknown>[] }>(`/workspaces/${workspaceId}/risks`);
  return (data.risks ?? []).map(mapRisk);
}

export async function fetchTeam(workspaceId: string): Promise<Member[]> {
  const ws = await apiFetch<Record<string, unknown>>(`/workspaces/${workspaceId}`);
  const members = (ws.members as Record<string, unknown>[]) ?? [];
  const allTasks = await apiFetch<Record<string, unknown>[]>(`/workspaces/${workspaceId}/tasks`);
    return members.map((m) => {
    const uid = String(m.user_id);
    const assigned = allTasks.filter((t) => String(t.assignee_id) === uid).length;
    const completed = allTasks.filter(
      (t) => String(t.assignee_id) === uid && mapTaskStatus(String(t.status)) === "done",
    ).length;
    return mapMember({
      ...m,
      id: uid,
      name: m.name,
      email: m.email,
      skills: m.skills,
      tasks_assigned: assigned,
      tasks_completed: completed,
      role: m.role === "lead" ? "Tech Lead" : "Member",
    });
  });
}

export async function listDocuments(workspaceId: string): Promise<Document[]> {
  const data = await apiFetch<Record<string, unknown>[]>(`/workspaces/${workspaceId}/documents`);
  return data.map(mapDocument);
}

export async function uploadDocument(workspaceId: string, file: File): Promise<Document> {
  const form = new FormData();
  form.append("file", file);
  const data = await apiFetch<Record<string, unknown>>(`/workspaces/${workspaceId}/documents`, {
    method: "POST",
    body: form,
  });
  return mapDocument(data);
}
