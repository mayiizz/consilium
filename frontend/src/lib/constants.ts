import type { DocumentType, Priority, TaskStatus } from "./types";

const avatar = (seed: string) =>
  `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(seed)}`;

export const AVATAR_OPTIONS = [
  "Alex", "Jordan", "Sam", "Taylor", "Riley", "Casey", "Morgan", "Avery",
  "Quinn", "Drew", "Sage", "River",
].map((s) => ({ seed: s, url: avatar(s) }));

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  prd: "PRD",
  brief: "Brief",
  architecture: "Architecture",
  meeting: "Meeting",
  research: "Research",
  other: "Other",
};

export const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "To Do",
  in_progress: "In Progress",
  in_review: "In Review",
  done: "Done",
  blocked: "Blockers",
};

export const STATUS_ORDER: TaskStatus[] = ["todo", "in_progress", "in_review", "done", "blocked"];

/** Columns shown on the Kanban board (Blockers are opened via the Blockers button). */
export const BOARD_COLUMNS: TaskStatus[] = ["todo", "in_progress", "in_review", "done"];

export const STATUS_ACCENT: Record<TaskStatus, string> = {
  todo: "bg-muted-foreground",
  in_progress: "bg-primary",
  in_review: "bg-warning",
  done: "bg-success",
  blocked: "bg-destructive",
};

export const PRIORITY_COLOR: Record<Priority, string> = {
  low: "bg-muted text-muted-foreground",
  medium: "bg-accent text-accent-foreground",
  high: "bg-warning/15 text-warning",
  urgent: "bg-destructive/15 text-destructive",
};
