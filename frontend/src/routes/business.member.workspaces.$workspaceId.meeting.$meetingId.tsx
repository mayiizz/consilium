import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { MeetingInfoPanel } from "@/components/meetings/MeetingInfoPanel";
import { MeetingAttendanceTab } from "@/components/meetings/MeetingAttendanceTab";
import { LiveTranscriptView } from "@/components/meetings/LiveTranscriptView";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { useMeeting, useTranscript } from "@/lib/api/hooks/useMeetings";
import { useMeetingAttendance } from "@/lib/api/hooks/useMeetingAttendance";
import { useMeetingSocket } from "@/lib/api/hooks/useMeetingSocket";
import { useBrowserMicTranscript } from "@/lib/api/hooks/useBrowserMicTranscript";
import { useAuth } from "@/lib/auth-context";
import { format } from "date-fns";
import { ArrowLeft, ExternalLink } from "lucide-react";

export const Route = createFileRoute("/business/member/workspaces/$workspaceId/meeting/$meetingId")({ component: Page });

function Page() {
  const { workspaceId, meetingId } = Route.useParams();
  const { user } = useAuth();
  const { data: meeting, isLoading, refetch } = useMeeting(meetingId);
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
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [visibleLines]);

  if (isLoading || !meeting) {
    return (
      <DashboardLayout role="member" workspaceId={workspaceId}>
        <p className="p-6 text-sm text-muted-foreground">Loading…</p>
      </DashboardLayout>
    );
  }

  const url = meeting.meetingUrl ?? meeting.jitsiUrl;
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
    <DashboardLayout role="member" workspaceId={workspaceId}>
      <Link
        to={`/business/member/workspaces/${workspaceId}/meetings`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft size={14} /> Back
      </Link>
      <PageHeader
        title={meeting.title}
        description={format(meeting.startTime, "EEE, MMM d HH:mm")}
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={meeting.status} />
            {url && (
              <Button
                size="sm"
                variant="outline"
                className="rounded-xl"
                onClick={() => window.open(url, "_blank", "noopener,noreferrer")}
              >
                <ExternalLink size={14} /> Join
              </Button>
            )}
          </div>
        }
      />
      <MeetingInfoPanel meeting={meeting} />
      <Card className="glass-card p-5">
        <Tabs defaultValue="transcript">
          <TabsList>
            <TabsTrigger value="transcript">Transcript</TabsTrigger>
            <TabsTrigger value="summary">Summary</TabsTrigger>
            <TabsTrigger value="decisions">Decisions</TabsTrigger>
            <TabsTrigger value="attendance">Attendance</TabsTrigger>
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
              <LiveTranscriptView
                lines={visibleLines}
                emptyLabel={isActive ? "No transcript yet — speak into your mic." : "No transcript available."}
              />
            </div>
          </TabsContent>
          <TabsContent value="summary">
            <p className="text-sm text-muted-foreground">{meeting.summary || "No summary yet."}</p>
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
        </Tabs>
      </Card>
    </DashboardLayout>
  );
}
