import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { MeetingInfoPanel } from "@/components/meetings/MeetingInfoPanel";
import { MeetingAttendanceTab } from "@/components/meetings/MeetingAttendanceTab";
import { LiveTranscriptView } from "@/components/meetings/LiveTranscriptView";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/StatusBadge";
import { TaskCard } from "@/components/TaskCard";
import { useMeeting, useTranscript } from "@/lib/api/hooks/useMeetings";
import { useMeetingMutations } from "@/lib/api/hooks/useMeetingMutations";
import { useMeetingAttendance } from "@/lib/api/hooks/useMeetingAttendance";
import { useMeetingSocket } from "@/lib/api/hooks/useMeetingSocket";
import { useBrowserMicTranscript } from "@/lib/api/hooks/useBrowserMicTranscript";
import { useTasks } from "@/lib/api/hooks/useTasks";
import { formatApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth-context";
import { sendCopilotMessage } from "@/lib/api/services/copilot";
import { ArrowLeft, ExternalLink, Loader2, Mic, Send, Sparkles, Square, Trash2, Upload } from "lucide-react";
import { safeFormatDate } from "@/lib/safe-dates";
import { toast } from "sonner";
import { UploadTranscriptDialog } from "@/components/meetings/UploadTranscriptDialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/meeting/$meetingId")({ component: Page });

function Page() {
  const { workspaceId, meetingId } = Route.useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: meeting, isLoading, isError, refetch } = useMeeting(meetingId);
  const { data: tasks = [] } = useTasks(workspaceId);
  const { start, stop, cancel, reprocess, remove } = useMeetingMutations(workspaceId);
  const meetingTasks = tasks.filter(
    (t) => t.meetingId === meetingId || t.sourceMeetingId === meetingId,
  );
  const isLive = meeting?.status === "live";
  const isReady = meeting?.status === "ready";
  const isActive = isLive || isReady;
  const { data: staticTranscript = [] } = useTranscript(meetingId, !!meeting, isActive ? 2000 : 5000);
  const { lines: wsLines, setLines, connected, sendChunk } = useMeetingSocket(meetingId, isActive);
  const { status: micStatus, error: micError, interim: micInterim } = useBrowserMicTranscript({
    enabled: isActive,
    speakerName: user?.name ?? "",
    connected,
    sendChunk,
  });
  const [q, setQ] = useState("");
  const [qaLoading, setQaLoading] = useState(false);
  const [qaReply, setQaReply] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useMeetingAttendance(meetingId, isActive);

  const visibleLines =
    isActive && wsLines.length >= staticTranscript.length ? wsLines : staticTranscript;

  useEffect(() => {
    if (staticTranscript.length) setLines(staticTranscript);
  }, [staticTranscript, setLines]);

  useEffect(() => {
    if (!isActive) return;
    const t = setInterval(() => refetch(), 3000);
    return () => clearInterval(t);
  }, [isActive, refetch]);

  useEffect(() => {
    if (meeting?.status === "ended" && !meeting.summary) {
      const t = setInterval(() => refetch(), 3000);
      return () => clearInterval(t);
    }
  }, [meeting?.status, meeting?.summary, refetch]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [visibleLines]);

  const onStart = async () => {
    try {
      const updated = await start.mutateAsync(meetingId);
      const url = updated.meetingUrl ?? updated.jitsiUrl;
      if (url) window.open(url, "_blank", "noopener,noreferrer");
      toast.success("Meeting started — your mic is transcribing as you");
    } catch (err) {
      toast.error(formatApiError(err, "Could not start meeting"));
    }
  };

  const onStop = async () => {
    try {
      await stop.mutateAsync(meetingId);
      toast.success("Meeting ended — summary and Kanban tasks are syncing…");
    } catch (err) {
      toast.error(formatApiError(err, "Could not stop meeting"));
    }
  };

  const onCancel = async () => {
    try {
      await cancel.mutateAsync(meetingId);
      toast.success("Meeting cancelled");
    } catch (err) {
      toast.error(formatApiError(err, "Could not cancel meeting"));
    }
  };

  const needsReprocess =
    meeting?.status === "ended" &&
    (meeting.summary?.includes("GROQ_API_KEY not set") ||
      meeting.summary?.includes("AI summary unavailable"));

  const onReprocess = async () => {
    try {
      await reprocess.mutateAsync(meetingId);
      await refetch();
      toast.success("Summary and tasks regenerated");
    } catch (err) {
      toast.error(formatApiError(err, "Could not regenerate summary"));
    }
  };

  const onDelete = async () => {
    try {
      const res = await remove.mutateAsync(meetingId);
      toast.success(res.message ?? "Meeting deleted");
      navigate({ to: `/business/manager/workspaces/${workspaceId}/meetings` });
    } catch (err) {
      toast.error(formatApiError(err, "Could not delete meeting"));
    }
  };

  const onAsk = async () => {
    if (!q.trim() || qaLoading) return;
    setQaLoading(true);
    try {
      const res = await sendCopilotMessage(workspaceId, q.trim(), meetingId);
      setQaReply(res.content);
      setQ("");
    } catch (err) {
      toast.error(formatApiError(err, "Could not get answer"));
    } finally {
      setQaLoading(false);
    }
  };

  if (isError) {
    return (
      <DashboardLayout role="manager" workspaceId={workspaceId}>
        <div className="p-6 text-center">
          <p className="mb-3 text-sm text-muted-foreground">Meeting not found or was deleted.</p>
          <Button
            variant="outline"
            className="rounded-xl"
            onClick={() => navigate({ to: `/business/manager/workspaces/${workspaceId}/meetings` })}
          >
            Back to meetings
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  if (isLoading || !meeting) {
    return (
      <DashboardLayout role="manager" workspaceId={workspaceId}>
        <p className="p-6 text-sm text-muted-foreground">Loading…</p>
      </DashboardLayout>
    );
  }

  const micHint =
    !isActive
      ? "Recorded transcript"
      : !connected
        ? "Connecting…"
        : micStatus === "listening"
          ? `Web Speech listening as ${user?.name ?? "you"}${micInterim ? ` — ${micInterim}` : " — speak to transcribe"}`
          : micStatus === "denied"
            ? micError || "Allow microphone access to transcribe"
            : micStatus === "unsupported"
              ? micError || "Use Chrome or Edge for Web Speech transcription"
              : micError || "Starting Web Speech mic…";

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <Link
        to={`/business/manager/workspaces/${workspaceId}/meetings`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft size={14} /> Back
      </Link>
      <PageHeader
        title={meeting.title}
        description={safeFormatDate(meeting.startTime, "EEE, MMM d HH:mm")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={meeting.status} />
            {(meeting.meetingUrl || meeting.jitsiUrl) && (
              <Button
                size="sm"
                variant="outline"
                className="rounded-xl"
                onClick={() => window.open(meeting.meetingUrl ?? meeting.jitsiUrl, "_blank", "noopener,noreferrer")}
              >
                <ExternalLink size={14} /> Open call
              </Button>
            )}
            {(meeting.status === "scheduled" || isReady || meeting.status === "ended") && !isLive && (
              <Button size="sm" variant="outline" className="rounded-xl" onClick={() => setUploadOpen(true)}>
                <Upload size={14} /> Upload file
              </Button>
            )}
            {!isActive && meeting.status === "scheduled" && (
              <Button size="sm" className="gradient-primary rounded-xl" onClick={onStart} disabled={start.isPending}>
                {start.isPending ? <Loader2 size={14} className="animate-spin" /> : <Mic size={14} />}
                Start meeting
              </Button>
            )}
            {(meeting.status === "scheduled" || isReady) && !isLive && (
              <Button size="sm" variant="outline" className="rounded-xl" onClick={onCancel} disabled={cancel.isPending}>
                Cancel
              </Button>
            )}
            {isLive && (
              <Button size="sm" variant="destructive" className="rounded-xl" onClick={onStop} disabled={stop.isPending}>
                <Square size={14} /> Stop meeting
              </Button>
            )}
            {!isLive && (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    className="rounded-xl text-destructive hover:text-destructive"
                    disabled={remove.isPending}
                  >
                    {remove.isPending ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                    Delete
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete {meeting.title}?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This removes the meeting and all related tasks, transcript, summary, and
                      pending agent reviews from the project. This cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      onClick={onDelete}
                    >
                      Delete meeting
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
          </div>
        }
      />

      <UploadTranscriptDialog
        workspaceId={workspaceId}
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        meetingId={meetingId}
        meetingTitle={meeting.title}
      />

      <MeetingInfoPanel meeting={meeting} />
      {meeting.isUpload && meeting.originalFileName && (
        <p className="mb-4 text-xs text-muted-foreground">
          Uploaded from <span className="font-medium text-foreground">{meeting.originalFileName}</span>
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 glass-card p-5">
          <Tabs defaultValue="transcript">
            <TabsList>
              <TabsTrigger value="transcript">Transcript</TabsTrigger>
              <TabsTrigger value="summary">Summary</TabsTrigger>
              <TabsTrigger value="actions">Action items</TabsTrigger>
              <TabsTrigger value="decisions">Decisions</TabsTrigger>
              <TabsTrigger value="attendance">Attendance</TabsTrigger>
              <TabsTrigger value="qa">Q&A</TabsTrigger>
            </TabsList>
            <TabsContent value="transcript">
              <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
                {isActive && micStatus === "listening" && (
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
                  </span>
                )}
                {micHint}
              </div>
              <div ref={scrollRef} className="max-h-[420px] overflow-y-auto rounded-xl bg-muted/30 p-4">
                <LiveTranscriptView lines={visibleLines} />
              </div>
            </TabsContent>
            <TabsContent value="summary">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                {meeting.status === "ended" && (
                  <Button
                    variant="outline"
                    size="sm"
                    className="rounded-xl"
                    onClick={onReprocess}
                    disabled={reprocess.isPending}
                  >
                    {reprocess.isPending ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                    {needsReprocess ? "Regenerate summary" : "Refresh summary"}
                  </Button>
                )}
              </div>
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                {meeting.summary || "No summary yet."}
              </p>
            </TabsContent>
            <TabsContent value="actions">
              <ul className="space-y-2">
                {(meeting.actionItems ?? []).map((a, i) => (
                  <li key={i} className="text-sm text-muted-foreground">• {a}</li>
                ))}
                {!(meeting.actionItems?.length) && <p className="text-sm text-muted-foreground">No action items yet.</p>}
              </ul>
            </TabsContent>
            <TabsContent value="decisions">
              <ul className="space-y-2">
                {(meeting.keyDecisions ?? []).map((d, i) => (
                  <li key={i} className="text-sm text-muted-foreground">• {d}</li>
                ))}
                {!(meeting.keyDecisions?.length) && <p className="text-sm text-muted-foreground">No decisions yet.</p>}
              </ul>
            </TabsContent>
            <TabsContent value="attendance">
              <MeetingAttendanceTab meeting={meeting} />
            </TabsContent>
            <TabsContent value="qa">
              <div className="space-y-3">
                <div className="flex gap-2">
                  <Input
                    value={q}
                    onChange={(e) => setQ(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && onAsk()}
                    placeholder="Ask about this meeting…"
                    className="rounded-xl"
                  />
                  <Button size="icon" className="gradient-primary rounded-xl" onClick={onAsk} disabled={qaLoading}>
                    {qaLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                  </Button>
                </div>
                {qaReply && <p className="whitespace-pre-wrap text-sm text-muted-foreground">{qaReply}</p>}
              </div>
            </TabsContent>
          </Tabs>
        </Card>

        <Card className="glass-card p-5">
          <h3 className="mb-3 text-sm font-semibold">Tasks from this meeting</h3>
          <div className="space-y-2">
            {meetingTasks.map((t) => (
              <TaskCard key={t.id} task={t} workspaceId={workspaceId} />
            ))}
            {meetingTasks.length === 0 && (
              <p className="text-sm text-muted-foreground">
                {meeting.status === "ended"
                  ? "No Kanban tasks linked yet. Open Kanban and click Automate board / Extract from meetings."
                  : "Tasks appear after the meeting ends."}
              </p>
            )}
          </div>
        </Card>
      </div>
    </DashboardLayout>
  );
}
