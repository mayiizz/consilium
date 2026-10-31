export type Role = "manager" | "member";
export type TaskStatus = "todo" | "in_progress" | "in_review" | "done" | "blocked";
export type Priority = "low" | "medium" | "high" | "urgent";
export type MeetingStatus = "scheduled" | "ready" | "live" | "ended" | "cancelled";
export type MeetingPlatform = "google_meet" | "zoom" | "teams" | "jitsi" | "custom";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar: string;
  skills: string[];
}

export interface Workspace {
  id: string;
  name: string;
  inviteCode: string;
  ownerId: string;
  memberCount: number;
  role: Role;
  gitEnabled: boolean;
  requirePrMerge: boolean;
  requireCiPass: boolean;
  pushModeEnabled: boolean;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: Priority;
  assignee?: { id: string; name: string; avatar: string };
  dueDate?: Date;
  dueDateSource?: "transcript" | "user" | null;
  aiGenerated?: boolean;
  descriptionUserSet?: boolean;
  sourceMeetingId?: string;
  lastActivityAt?: Date;
  meetingId?: string;
  taskKey?: string;
  githubRef?: { repo: string; pr: number; ci: "passing" | "failing" | "pending" };
  githubCi?: {
    conclusion?: string;
    updatedAt?: string;
    workflowUrl?: string;
    headSha?: string;
  };
  gitEvidenceLog?: Array<{
    message?: string;
    event?: string;
    url?: string;
    actor?: string;
    sha?: string;
    at?: string;
  }>;
}

export interface Meeting {
  id: string;
  title: string;
  description?: string;
  platform?: MeetingPlatform;
  status: MeetingStatus;
  startTime: Date;
  startedAt?: Date;
  endedAt?: Date;
  duration?: number;
  participants: Array<{ id: string; name: string; avatar: string; joinTime?: Date; leaveTime?: Date }>;
  meetingUrl?: string;
  jitsiUrl?: string;
  summary?: string;
  keyDecisions?: string[];
  actionItems?: string[];
  transcriptCount?: number;
  createdBy?: string;
  isUpload?: boolean;
  originalFileName?: string;
}

export interface Member {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar: string;
  skills: string[];
  tasksAssigned: number;
  tasksCompleted: number;
}

export type DocumentType = "prd" | "brief" | "architecture" | "meeting" | "research" | "other";

export interface Document {
  id: string;
  title: string;
  type: DocumentType;
  updatedAt: Date;
  author: string;
  size: string;
}

export interface RoadmapPhase {
  id: string;
  name: string;
  status: "done" | "active" | "planned";
  milestones: { name: string; status: "done" | "active" | "planned"; taskCount: number }[];
  q: string;
  progress: number;
}

export interface Risk {
  id: string;
  title: string;
  severity: "high" | "medium" | "low";
  owner: string;
  impact: string;
}

export interface TranscriptLine {
  speaker: string;
  text: string;
  t: number;
}
