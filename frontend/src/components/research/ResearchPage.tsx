import { useCallback, useEffect, useRef, useState } from "react";
import { Download, Globe, Loader2, Microscope, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { MarkdownPreview } from "@/components/documents/MarkdownPreview";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { formatApiError } from "@/lib/api/client";
import {
  clearResearchChat,
  downloadResearchExport,
  getResearchChatHistory,
  getResearchJob,
  previewDocument,
  sendResearchChat,
  type ResearchChatJobSnapshot,
  type ResearchChatMessage,
  type ResearchJob,
} from "@/lib/api/services/research";

const WELCOME: ResearchChatMessage = {
  messageId: "welcome",
  role: "assistant",
  content:
    "Hi — I'm Research Chat. I can read this workspace’s Documents, research reports, tasks, and meetings. Ask me to summarize a report or rewrite a pricing table — TinyFish only runs when you need fresh web sources.",
  timestamp: new Date().toISOString(),
  usedWeb: false,
};

const PHASES = ["planning", "discovering", "browsing", "extracting", "analyzing", "generating", "completed"] as const;

function PhaseChips({ phase, status }: { phase: string; status: string }) {
  if (status === "done" || status === "failed") return null;
  const current = PHASES.includes(phase as (typeof PHASES)[number]) ? phase : "planning";
  const idx = PHASES.indexOf(current as (typeof PHASES)[number]);
  return (
    <ol className="mt-2 flex flex-wrap gap-1">
      {PHASES.map((step, i) => (
        <li
          key={step}
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] capitalize",
            i === idx ? "bg-primary/15 text-primary" : i < idx ? "bg-muted text-muted-foreground" : "text-muted-foreground/50",
          )}
        >
          {step}
        </li>
      ))}
    </ol>
  );
}

function JobCard({
  job,
  workspaceId,
  onOpenReport,
  onExport,
  exportingId,
}: {
  job: ResearchChatJobSnapshot | ResearchJob;
  workspaceId: string;
  onOpenReport: (documentId: string, topic: string) => void;
  onExport: (jobId: string, format: "md" | "json" | "csv" | "pdf") => void;
  exportingId: string | null;
}) {
  const id = job.id;
  const topic = "topic" in job ? job.topic : "";
  const status = job.status;
  const phase = job.phase;
  const sources = job.sources ?? [];
  const tables = job.tables ?? [];
  const summary =
    "summaryPreview" in job ? job.summaryPreview : (job as ResearchJob).summaryPreview;
  const documentId =
    "documentId" in job ? job.documentId : (job as ResearchJob).documentId;
  const error = "error" in job ? job.error : null;
  const sourcesCount =
    "sourcesCount" in job ? job.sourcesCount : (job as ResearchJob).sourcesCount;

  return (
    <div className="mt-2 w-full max-w-xl rounded-2xl border border-border/60 bg-background/80 p-3 text-left">
      <div className="flex flex-wrap items-center gap-2">
        <Globe size={14} className="text-primary" />
        <span className="text-xs font-medium">Web research</span>
        <Badge variant="outline" className="rounded-full capitalize text-[10px]">
          {status}
        </Badge>
        {sourcesCount > 0 ? (
          <span className="text-[10px] text-muted-foreground">{sourcesCount} sources</span>
        ) : null}
      </div>
      {topic ? <p className="mt-1 text-xs font-medium text-foreground/90">{topic}</p> : null}
      <PhaseChips phase={phase} status={status} />
      {error ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}
      {sources.length > 0 ? (
        <ul className="mt-2 space-y-1">
          {sources.slice(0, 5).map((src) => (
            <li key={src.url} className="truncate text-[11px]">
              {src.error ? (
                <span className="text-destructive">Failed: {src.title || src.url}</span>
              ) : (
                <a
                  href={src.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-primary underline-offset-2 hover:underline"
                >
                  {src.sourceType ? `[${src.sourceType}] ` : ""}
                  {src.title || src.url}
                </a>
              )}
            </li>
          ))}
        </ul>
      ) : null}
      {tables.length > 0 ? (
        <p className="mt-2 text-[11px] text-muted-foreground">
          {tables.length} table{tables.length === 1 ? "" : "s"} extracted
        </p>
      ) : null}
      {summary ? <p className="mt-2 line-clamp-3 text-xs text-muted-foreground">{summary}</p> : null}
      {status === "done" && documentId ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          <Button
            size="sm"
            variant="outline"
            className="h-7 rounded-lg text-xs"
            onClick={() => onOpenReport(documentId, topic || "Research report")}
          >
            Open report
          </Button>
          {(["md", "json", "csv", "pdf"] as const).map((fmt) => (
            <Button
              key={fmt}
              size="sm"
              variant="ghost"
              className="h-7 rounded-lg text-[10px] uppercase"
              disabled={exportingId === `${id}:${fmt}`}
              onClick={() => onExport(id, fmt)}
            >
              {exportingId === `${id}:${fmt}` ? (
                <Loader2 size={10} className="animate-spin" />
              ) : (
                <Download size={10} />
              )}
              {fmt}
            </Button>
          ))}
        </div>
      ) : null}
      {/* keep workspaceId referenced for future actions */}
      <span className="sr-only">{workspaceId}</span>
    </div>
  );
}

type UiMessage = ResearchChatMessage & { pending?: boolean };

export function ResearchPage({ workspaceId }: { workspaceId: string }) {
  const [messages, setMessages] = useState<UiMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewTitle, setPreviewTitle] = useState("");
  const [previewText, setPreviewText] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [exportingId, setExportingId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }));
  }, []);

  const mergeJobIntoMessages = useCallback((job: ResearchJob) => {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.researchJobId !== job.id && m.job?.id !== job.id) return m;
        return {
          ...m,
          job: {
            id: job.id,
            topic: job.topic,
            status: job.status,
            phase: job.phase,
            researchType: String(job.researchType),
            sourcesCount: job.sourcesCount,
            summaryPreview: job.summaryPreview,
            documentId: job.documentId,
            error: job.error,
            sources: job.sources,
            tables: job.tables,
          },
        };
      }),
    );
  }, []);

  const startPollingJobs = useCallback(
    (jobIds: string[]) => {
      const ids = [...new Set(jobIds.filter(Boolean))];
      if (ids.length === 0) return;
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(() => {
        void (async () => {
          let anyBusy = false;
          for (const id of ids) {
            try {
              const job = await getResearchJob(workspaceId, id);
              mergeJobIntoMessages(job);
              if (job.status === "pending" || job.status === "running") anyBusy = true;
            } catch {
              // ignore transient poll errors
            }
          }
          if (!anyBusy && pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        })();
      }, 3500);
    },
    [mergeJobIntoMessages, workspaceId],
  );

  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    getResearchChatHistory(workspaceId)
      .then((history) => {
        if (cancelled) return;
        if (history.length > 0) {
          setMessages(history);
          const busy = history
            .map((m) => m.job)
            .filter((j): j is ResearchChatJobSnapshot => !!j)
            .filter((j) => j.status === "pending" || j.status === "running")
            .map((j) => j.id);
          if (busy.length) startPollingJobs(busy);
        } else {
          setMessages([WELCOME]);
        }
      })
      .catch(() => {
        if (!cancelled) setMessages([WELCOME]);
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });
    return () => {
      cancelled = true;
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [workspaceId, startPollingJobs]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  const openReport = async (documentId: string, topicLabel: string) => {
    setPreviewOpen(true);
    setPreviewTitle(topicLabel);
    setPreviewText("");
    setPreviewLoading(true);
    try {
      const preview = await previewDocument(documentId);
      setPreviewTitle(preview.name || topicLabel);
      setPreviewText(preview.text);
    } catch (err) {
      toast.error(formatApiError(err, "Could not load report"));
      setPreviewOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const exportJob = async (jobId: string, format: "md" | "json" | "csv" | "pdf") => {
    setExportingId(`${jobId}:${format}`);
    try {
      await downloadResearchExport(workspaceId, jobId, format);
      toast.success(`Downloaded ${format.toUpperCase()}`);
    } catch (err) {
      toast.error(formatApiError(err, "Could not download export"));
    } finally {
      setExportingId(null);
    }
  };

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    const userMsg: UiMessage = {
      messageId: `local-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
      usedWeb: false,
    };
    setMessages((m) => [...m.filter((x) => x.messageId !== "welcome"), userMsg]);
    setLoading(true);
    try {
      const res = await sendResearchChat(workspaceId, text);
      setMessages((m) => [
        ...m,
        {
          messageId: res.messageId,
          role: "assistant",
          content: res.content,
          timestamp: res.timestamp,
          usedWeb: res.usedWeb,
          researchJobId: res.researchJobId,
          job: res.job,
        },
      ]);
      if (res.researchJobId) {
        startPollingJobs([res.researchJobId]);
      }
    } catch (err) {
      toast.error(formatApiError(err, "Could not send message"));
      setMessages((m) => [
        ...m,
        {
          messageId: `err-${Date.now()}`,
          role: "assistant",
          content: "Sorry — I couldn't process that. Please try again.",
          timestamp: new Date().toISOString(),
          usedWeb: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    try {
      await clearResearchChat(workspaceId);
      setMessages([WELCOME]);
      toast.success("Chat cleared");
    } catch (err) {
      toast.error(formatApiError(err, "Could not clear chat"));
    }
  };

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <div className="flex h-[calc(100vh-6rem)] min-h-[480px] flex-col">
        <div className="mb-3 flex items-start justify-between gap-3">
          <PageHeader
            title="Research"
            description="Uses Documents, reports, tasks, and meetings. TinyFish browses the web only when live sources are needed."
          />
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0 rounded-xl text-muted-foreground"
            onClick={() => void clearChat()}
          >
            <Trash2 size={14} />
            Clear
          </Button>
        </div>

        <Card className="glass-card flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
            {historyLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 size={14} className="animate-spin" /> Loading conversation…
              </div>
            ) : (
              messages.map((m) => {
                const isUser = m.role === "user";
                return (
                  <div
                    key={m.messageId}
                    className={cn("flex flex-col", isUser ? "items-end" : "items-start")}
                  >
                    <div
                      className={cn(
                        "max-w-[min(100%,42rem)] whitespace-pre-wrap rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
                        isUser
                          ? "gradient-primary text-white"
                          : "bg-muted/80 text-foreground",
                      )}
                    >
                      {!isUser && m.usedWeb ? (
                        <div className="mb-1.5 flex items-center gap-1 text-[10px] font-medium uppercase tracking-wide text-primary">
                          <Microscope size={10} />
                          TinyFish when needed
                        </div>
                      ) : null}
                      {m.content}
                    </div>
                    {!isUser && m.job ? (
                      <JobCard
                        job={m.job}
                        workspaceId={workspaceId}
                        onOpenReport={openReport}
                        onExport={exportJob}
                        exportingId={exportingId}
                      />
                    ) : null}
                  </div>
                );
              })
            )}
            {loading ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 size={12} className="animate-spin" /> Thinking…
              </div>
            ) : null}
            <div ref={bottomRef} />
          </div>

          <div className="border-t border-border/60 p-3 sm:p-4">
            <div className="flex items-end gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void send();
                  }
                }}
                placeholder="Ask a question, or request web research on a topic…"
                className="min-h-[48px] max-h-36 resize-none rounded-2xl"
                rows={2}
                disabled={loading}
              />
              <Button
                size="icon"
                className="gradient-primary h-11 w-11 shrink-0 rounded-2xl"
                onClick={() => void send()}
                disabled={loading || !input.trim()}
                aria-label="Send"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              </Button>
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Enter to send · Shift+Enter for a new line · Web research runs only when needed
            </p>
          </div>
        </Card>
      </div>

      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{previewTitle || "Research report"}</DialogTitle>
          </DialogHeader>
          {previewLoading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 size={16} className="animate-spin" /> Loading…
            </div>
          ) : (
            <MarkdownPreview markdown={previewText} />
          )}
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
}
