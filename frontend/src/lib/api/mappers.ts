import type {
  Document,
  Meeting,
  MeetingStatus,
  Member,
  Priority,
  Risk,
  RoadmapPhase,
  Role,
  Task,
  TaskStatus,
  TranscriptLine,
  Workspace,
} from "../types";
import { parseApiDate } from "../safe-dates";
import { taskDescriptionForDisplay } from "../taskDescription";

const STATUS_TO_FRONT: Record<string, TaskStatus> = {
  "To Do": "todo",
  "In Progress": "in_progress",
  "In Review": "in_review",
  Done: "done",
  Blockers: "blocked",
};

const STATUS_TO_BACK: Record<TaskStatus, string> = {
  todo: "To Do",
  in_progress: "In Progress",
  in_review: "In Review",
  done: "Done",
  blocked: "Blockers",
};

export function mapTaskStatus(status: string): TaskStatus {
  return STATUS_TO_FRONT[status] ?? "todo";
}

export function mapTaskStatusToApi(status: TaskStatus): string {
  return STATUS_TO_BACK[status];
}

export function mapRole(role: string): Role {
  return role === "lead" ? "manager" : "member";
}

export function mapRoleToApi(role: Role): string {
  return role === "manager" ? "lead" : "member";
}

function avatarUrl(seed: string) {
  return `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(seed)}`;
}

export function mapTask(raw: Record<string, unknown>): Task {
  const git = raw.git_evidence as Record<string, unknown> | undefined;
  let githubRef: Task["githubRef"];
  if (git?.pr_number) {
    const ci = String(git.ci_status ?? git.github_ci_conclusion ?? "unknown");
    githubRef = {
      repo: String(git.pr_url ?? "").split("/").slice(-2).join("/") || "repo",
      pr: Number(git.pr_number),
      ci: ci === "passed" || ci === "success" ? "passing" : ci === "failed" || ci === "failure" ? "failing" : "pending",
    };
  }
  const githubCi =
    git?.github_ci_conclusion || git?.github_ci_updated_at
      ? {
          conclusion: git.github_ci_conclusion ? String(git.github_ci_conclusion) : String(git.ci_status ?? ""),
          updatedAt: git.github_ci_updated_at ? String(git.github_ci_updated_at) : undefined,
          workflowUrl: git.github_ci_workflow_url ? String(git.github_ci_workflow_url) : undefined,
          headSha: git.github_ci_head_sha ? String(git.github_ci_head_sha) : undefined,
        }
      : undefined;
  const gitLog = Array.isArray(git?.log) ? (git.log as Array<Record<string, unknown>>) : [];
  const isAuto = Boolean(raw.is_auto_generated);
  const descUserSet = Boolean(raw.description_user_set);
  const displayDesc = taskDescriptionForDisplay(
    raw.description ? String(raw.description) : null,
    isAuto,
    descUserSet,
  );
  return {
    id: String(raw.id),
    title: String(raw.title),
    description: displayDesc ?? undefined,
    status: mapTaskStatus(String(raw.status)),
    priority: String(raw.priority ?? "medium") as Priority,
    assignee: raw.assignee_id
      ? {
          id: String(raw.assignee_id),
          name: String(raw.assignee_name ?? "Unknown"),
          avatar: avatarUrl(String(raw.assignee_name ?? "user")),
        }
      : raw.assignee_name
        ? {
            id: "",
            name: String(raw.assignee_name),
            avatar: avatarUrl(String(raw.assignee_name)),
          }
        : undefined,
    dueDate: raw.due_date ? new Date(String(raw.due_date)) : undefined,
    dueDateSource: raw.due_date_source
      ? (String(raw.due_date_source) as Task["dueDateSource"])
      : undefined,
    aiGenerated: isAuto,
    descriptionUserSet: descUserSet,
    sourceMeetingId: raw.source_meeting_id
      ? String(raw.source_meeting_id)
      : raw.meeting_id
        ? String(raw.meeting_id)
        : undefined,
    lastActivityAt: raw.last_activity_at ? new Date(String(raw.last_activity_at)) : undefined,
    meetingId: raw.meeting_id ? String(raw.meeting_id) : undefined,
    taskKey: raw.task_key ? String(raw.task_key) : undefined,
    githubRef,
    githubCi,
    gitEvidenceLog: gitLog.map((e) => ({
      message: e.message ? String(e.message) : undefined,
      event: e.event ? String(e.event) : undefined,
      url: e.url ? String(e.url) : undefined,
      actor: e.actor ? String(e.actor) : undefined,
      sha: e.sha ? String(e.sha) : undefined,
      at: e.at ? String(e.at) : undefined,
    })),
  };
}

export function mapMeeting(raw: Record<string, unknown>): Meeting {
  const start = raw.started_at ?? raw.scheduled_at ?? raw.created_at;
  const attendees = Array.isArray(raw.attendees)
    ? (raw.attendees as Array<Record<string, unknown>>).map((a) => ({
        id: String(a.user_id),
        name: String(a.name),
        avatar: String(a.avatar ?? avatarUrl(String(a.name))),
        joinTime: parseApiDate(a.join_time),
        leaveTime: parseApiDate(a.leave_time),
      }))
    : Array.isArray(raw.participants)
      ? (raw.participants as Array<Record<string, string>>).map((p) => ({
          id: String(p.id),
          name: String(p.name),
          avatar: String(p.avatar ?? avatarUrl(p.name)),
        }))
      : [];
  const url = raw.meeting_url ?? raw.video_link ?? raw.jitsi_url;
  return {
    id: String(raw.id),
    title: String(raw.title),
    description: raw.description ? String(raw.description) : undefined,
    platform: raw.platform ? (String(raw.platform) as Meeting["platform"]) : undefined,
    status: String(raw.status) as MeetingStatus,
    startTime: parseApiDate(start) ?? new Date(),
    startedAt: parseApiDate(raw.started_at),
    endedAt: parseApiDate(raw.ended_at),
    duration: raw.duration ? Number(raw.duration) : undefined,
    participants: attendees,
    meetingUrl: url ? String(url) : undefined,
    jitsiUrl: url ? String(url) : undefined,
    summary: raw.summary ? String(raw.summary) : undefined,
    keyDecisions: Array.isArray(raw.key_decisions) ? (raw.key_decisions as string[]) : [],
    actionItems: Array.isArray(raw.action_items) ? (raw.action_items as string[]) : [],
    transcriptCount: raw.transcript_count != null ? Number(raw.transcript_count) : undefined,
    createdBy: raw.created_by ? String(raw.created_by) : undefined,
    isUpload: Boolean(raw.is_upload),
    originalFileName: raw.original_file_name ? String(raw.original_file_name) : undefined,
  };
}

export function mapWorkspace(raw: Record<string, unknown>): Workspace {
  const members = raw.members as Array<Record<string, unknown>> | undefined;
  const lead = members?.find((m) => m.role === "lead");
  const settings = (raw.settings as Record<string, unknown> | undefined) ?? {};
  return {
    id: String(raw.id),
    name: String(raw.name),
    inviteCode: String(raw.invite_code ?? ""),
    ownerId: lead ? String(lead.user_id) : "",
    memberCount: Number(raw.member_count ?? members?.length ?? 0),
    role: mapRole(String(raw.role ?? "member")),
    gitEnabled: settings.git_enabled !== false,
    requirePrMerge: settings.require_pr_merge !== false,
    requireCiPass: Boolean(settings.require_ci_pass),
    pushModeEnabled: Boolean(settings.push_mode_enabled),
  };
}

export function mapMember(raw: Record<string, unknown>): Member {
  return {
    id: String(raw.id ?? raw.user_id),
    name: String(raw.name),
    email: String(raw.email ?? ""),
    role: String(raw.role),
    avatar: String(raw.avatar ?? avatarUrl(String(raw.name))),
    skills: Array.isArray(raw.skills) ? (raw.skills as string[]) : [],
    tasksAssigned: Number(raw.tasks_assigned ?? 0),
    tasksCompleted: Number(raw.tasks_completed ?? 0),
  };
}

export function mapDocument(raw: Record<string, unknown>): Document {
  const bytes = Number(raw.file_size ?? 0);
  const size =
    raw.size != null
      ? String(raw.size)
      : bytes >= 1024 * 1024
        ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
        : `${Math.max(1, Math.round(bytes / 1024))} KB`;
  const typeRaw = String(raw.type ?? "other");
  const typeMap: Record<string, Document["type"]> = {
    requirements: "prd",
    user_story: "brief",
    architecture: "architecture",
    other: "other",
    prd: "prd",
    brief: "brief",
    meeting: "meeting",
    research: "research",
  };
  return {
    id: String(raw.id),
    title: String(raw.name ?? raw.title ?? raw.filename ?? "Document"),
    type: typeMap[typeRaw] ?? "other",
    updatedAt: new Date(String(raw.updated_at ?? raw.created_at)),
    author: String(raw.author ?? raw.uploaded_by ?? "Unknown"),
    size,
  };
}

export function mapRoadmapPhase(raw: Record<string, unknown>): RoadmapPhase {
  const milestones = (raw.milestones as Array<Record<string, unknown>> | undefined) ?? [];
  return {
    id: String(raw.id),
    name: String(raw.name),
    status: String(raw.status) as RoadmapPhase["status"],
    q: String(raw.q),
    progress: Number(raw.progress ?? 0),
    milestones: milestones.map((m) => ({
      name: String(m.name),
      status: String(m.status) as "done" | "active" | "planned",
      taskCount: Number(m.task_count ?? m.taskCount ?? 0),
    })),
  };
}

export function mapRisk(raw: Record<string, unknown>): Risk {
  return {
    id: String(raw.id),
    title: String(raw.title),
    severity: String(raw.severity) as Risk["severity"],
    owner: String(raw.owner),
    impact: String(raw.impact),
  };
}

export function mapTranscriptChunk(chunk: Record<string, unknown>, index: number): TranscriptLine {
  let speaker = String(chunk.speaker ?? chunk.speaker_label ?? "").trim();
  let text = String(chunk.text ?? "");
  if (!speaker) {
    const parsed = parseSpeakerFromText(text);
    if (parsed) {
      speaker = parsed.speaker;
      text = parsed.text;
    }
  } else {
    // Avoid "Rahul" label + "**Rahul:** …" body duplication
    const stripped = stripLeadingSpeaker(text, speaker);
    if (stripped) text = stripped;
  }
  const offsetMs = Number(chunk.audio_offset_ms);
  return {
    speaker,
    text,
    t: Number.isFinite(offsetMs) && offsetMs > 0 ? offsetMs / 1000 : Number(chunk.audio_offset_ms ?? 0) / 1000 || 0,
  };
}

function parseSpeakerFromText(raw: string): { speaker: string; text: string } | null {
  const line = raw.trim();
  // **Name:** body  |  Name: body
  const m = line.match(/^\*{0,2}\[?([A-Za-z][A-Za-z0-9 .'-]{0,40})\]?\*{0,2}\s*:\s*(.+)$/s);
  if (!m) return null;
  const speaker = m[1].replace(/\*+/g, "").trim();
  let text = m[2].trim().replace(/^\*+/, "").replace(/\*+$/, "").trim();
  if (!speaker || speaker.length > 40) return null;
  return { speaker, text: text || line };
}

function stripLeadingSpeaker(text: string, speaker: string): string | null {
  const esc = speaker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`^\\*{0,2}\\[?${esc}\\]?\\*{0,2}\\s*:\\s*`, "i");
  if (!re.test(text.trim())) return null;
  return text.trim().replace(re, "").replace(/^\*+/, "").replace(/\*+$/, "").trim();
}

export function formatTranscriptText(lines: TranscriptLine[]): string {
  return lines
    .map((line) => {
      const text = line.text.trim();
      if (!text) return "";
      const speaker = line.speaker?.trim();
      return speaker ? `${speaker}: ${text}` : text;
    })
    .filter(Boolean)
    .join("\n");
}
