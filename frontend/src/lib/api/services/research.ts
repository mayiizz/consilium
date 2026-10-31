import { API_BASE, getAccessToken } from "../client";
import { apiFetch } from "../client";

export type ResearchType =
  | "general"
  | "student_project"
  | "academic"
  | "technical"
  | "competitor_analysis";

export type ResearchSource = {
  url: string;
  title: string;
  extractionMethod: string;
  extractedContent: string;
  sourceType?: string;
  verificationStatus?: string;
  retrievedAt: string;
  error?: string | null;
};

export type ResearchTable = {
  title?: string;
  headers?: string[];
  rows?: string[][];
};

export type ResearchVisual = {
  url: string;
  caption?: string;
  source_url?: string;
  sourceUrl?: string;
};

export type ResearchJob = {
  id: string;
  workspaceId: string;
  topic: string;
  constraints: string;
  status: "pending" | "running" | "done" | "failed" | string;
  documentId?: string | null;
  error?: string | null;
  sourcesCount: number;
  summaryPreview: string;
  phase: string;
  researchType: ResearchType | string;
  sources: ResearchSource[];
  findings: Record<string, unknown>[];
  tables: ResearchTable[];
  visuals: ResearchVisual[];
  planNotes: string;
  createdAt: string;
  updatedAt: string;
};

function mapSource(raw: Record<string, unknown>): ResearchSource {
  return {
    url: String(raw.url ?? ""),
    title: String(raw.title ?? ""),
    extractionMethod: String(raw.extraction_method ?? "tinyfish"),
    extractedContent: String(raw.extracted_content ?? ""),
    sourceType: raw.source_type ? String(raw.source_type) : undefined,
    verificationStatus: raw.verification_status ? String(raw.verification_status) : undefined,
    retrievedAt: String(raw.retrieved_at ?? ""),
    error: raw.error ? String(raw.error) : null,
  };
}

function mapJob(raw: Record<string, unknown>): ResearchJob {
  const sources = Array.isArray(raw.sources)
    ? (raw.sources as Record<string, unknown>[]).map(mapSource)
    : [];
  const tables = Array.isArray(raw.tables) ? (raw.tables as ResearchTable[]) : [];
  const visualsRaw = Array.isArray(raw.visuals) ? (raw.visuals as Record<string, unknown>[]) : [];
  const visuals: ResearchVisual[] = visualsRaw.map((v) => ({
    url: String(v.url ?? ""),
    caption: v.caption ? String(v.caption) : undefined,
    sourceUrl: v.source_url ? String(v.source_url) : v.sourceUrl ? String(v.sourceUrl) : undefined,
  }));
  return {
    id: String(raw.id),
    workspaceId: String(raw.workspace_id),
    topic: String(raw.topic ?? ""),
    constraints: String(raw.constraints ?? ""),
    status: String(raw.status ?? "pending"),
    documentId: raw.document_id ? String(raw.document_id) : null,
    error: raw.error ? String(raw.error) : null,
    sourcesCount: Number(raw.sources_count ?? 0),
    summaryPreview: String(raw.summary_preview ?? ""),
    phase: String(raw.phase ?? "planning"),
    researchType: String(raw.research_type ?? "general"),
    sources,
    findings: Array.isArray(raw.findings) ? (raw.findings as Record<string, unknown>[]) : [],
    tables,
    visuals,
    planNotes: String(raw.plan_notes ?? ""),
    createdAt: String(raw.created_at),
    updatedAt: String(raw.updated_at),
  };
}

export type ResearchChatJobSnapshot = {
  id: string;
  topic: string;
  status: string;
  phase: string;
  researchType: string;
  sourcesCount: number;
  summaryPreview: string;
  documentId?: string | null;
  error?: string | null;
  sources: ResearchSource[];
  tables: ResearchTable[];
};

export type ResearchChatMessage = {
  messageId: string;
  role: "user" | "assistant" | string;
  content: string;
  timestamp: string;
  usedWeb: boolean;
  researchJobId?: string | null;
  job?: ResearchChatJobSnapshot | null;
};

function mapChatJob(raw: Record<string, unknown> | null | undefined): ResearchChatJobSnapshot | null {
  if (!raw) return null;
  const sources = Array.isArray(raw.sources)
    ? (raw.sources as Record<string, unknown>[]).map(mapSource)
    : [];
  const tables = Array.isArray(raw.tables) ? (raw.tables as ResearchTable[]) : [];
  return {
    id: String(raw.id),
    topic: String(raw.topic ?? ""),
    status: String(raw.status ?? "pending"),
    phase: String(raw.phase ?? "planning"),
    researchType: String(raw.research_type ?? "general"),
    sourcesCount: Number(raw.sources_count ?? 0),
    summaryPreview: String(raw.summary_preview ?? ""),
    documentId: raw.document_id ? String(raw.document_id) : null,
    error: raw.error ? String(raw.error) : null,
    sources,
    tables,
  };
}

function mapChatMessage(raw: Record<string, unknown>): ResearchChatMessage {
  return {
    messageId: String(raw.message_id ?? ""),
    role: String(raw.role ?? "assistant"),
    content: String(raw.content ?? ""),
    timestamp: String(raw.timestamp ?? new Date().toISOString()),
    usedWeb: Boolean(raw.used_web),
    researchJobId: raw.research_job_id ? String(raw.research_job_id) : null,
    job: mapChatJob(raw.job as Record<string, unknown> | undefined),
  };
}

export async function sendResearchChat(
  workspaceId: string,
  message: string,
): Promise<ResearchChatMessage & { usedWeb: boolean; researchJobId?: string | null }> {
  const data = await apiFetch<Record<string, unknown>>(`/workspaces/${workspaceId}/research/chat`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });
  const msg = mapChatMessage((data.message as Record<string, unknown>) ?? data);
  return {
    ...msg,
    usedWeb: Boolean(data.used_web ?? msg.usedWeb),
    researchJobId: data.research_job_id ? String(data.research_job_id) : msg.researchJobId,
  };
}

export async function getResearchChatHistory(workspaceId: string): Promise<ResearchChatMessage[]> {
  const data = await apiFetch<Record<string, unknown>>(
    `/workspaces/${workspaceId}/research/chat/history`,
  );
  return ((data.messages as Record<string, unknown>[]) ?? []).map(mapChatMessage);
}

export async function clearResearchChat(workspaceId: string): Promise<void> {
  await apiFetch(`/workspaces/${workspaceId}/research/chat/clear`, { method: "POST" });
}

export async function listResearchJobs(workspaceId: string): Promise<ResearchJob[]> {
  const data = await apiFetch<Record<string, unknown>>(`/workspaces/${workspaceId}/research`);
  return ((data.items as Record<string, unknown>[]) ?? []).map(mapJob);
}

export async function createResearchJob(
  workspaceId: string,
  topic: string,
  constraints = "",
  researchType: ResearchType | string = "general",
): Promise<ResearchJob> {
  const data = await apiFetch<Record<string, unknown>>(`/workspaces/${workspaceId}/research`, {
    method: "POST",
    body: JSON.stringify({ topic, constraints, research_type: researchType }),
  });
  return mapJob(data);
}

export async function getResearchJob(workspaceId: string, jobId: string): Promise<ResearchJob> {
  const data = await apiFetch<Record<string, unknown>>(
    `/workspaces/${workspaceId}/research/${jobId}`,
  );
  return mapJob(data);
}

export async function retryResearchJob(workspaceId: string, jobId: string): Promise<ResearchJob> {
  const data = await apiFetch<Record<string, unknown>>(
    `/workspaces/${workspaceId}/research/${jobId}/retry`,
    { method: "POST" },
  );
  return mapJob(data);
}

export async function downloadResearchExport(
  workspaceId: string,
  jobId: string,
  format: "md" | "json" | "csv" | "pdf",
): Promise<void> {
  const token = getAccessToken();
  const res = await fetch(
    `${API_BASE}/workspaces/${workspaceId}/research/${jobId}/export?format=${format}`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    },
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Export failed (${res.status})`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = /filename="?([^"]+)"?/i.exec(disposition);
  const filename = match?.[1] || `research.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function previewDocument(documentId: string): Promise<{
  id: string;
  name: string;
  type: string;
  mimeType: string;
  text: string;
}> {
  const data = await apiFetch<Record<string, unknown>>(`/documents/${documentId}/preview`);
  return {
    id: String(data.id),
    name: String(data.name ?? ""),
    type: String(data.type ?? "other"),
    mimeType: String(data.mime_type ?? ""),
    text: String(data.text ?? ""),
  };
}
