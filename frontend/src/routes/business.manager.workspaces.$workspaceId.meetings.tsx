import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { NewMeetingDialog } from "@/components/meetings/NewMeetingDialog";
import { UploadTranscriptDialog } from "@/components/meetings/UploadTranscriptDialog";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
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
import { useMeetings } from "@/lib/api/hooks/useMeetings";
import { useMeetingMutations } from "@/lib/api/hooks/useMeetingMutations";
import { formatApiError } from "@/lib/api/client";
import { Calendar, Loader2, Plus, Trash2, Upload } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import type { Meeting } from "@/lib/types";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/meetings")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  const { data: meetings = [], isLoading } = useMeetings(workspaceId);
  const { remove } = useMeetingMutations(workspaceId);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const onDelete = async (meeting: Meeting) => {
    if (meeting.status === "live") {
      toast.error("Stop the meeting before deleting it");
      return;
    }
    setDeletingId(meeting.id);
    try {
      const res = await remove.mutateAsync(meeting.id);
      toast.success(res.message ?? "Meeting deleted");
    } catch (err) {
      toast.error(formatApiError(err, "Could not delete meeting"));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader
        title="Meetings"
        description="Schedule, join, and review every sync."
        actions={
          <div className="flex gap-2">
            <Button size="sm" variant="outline" className="rounded-xl" onClick={() => setUploadOpen(true)}>
              <Upload size={14} /> Upload file
            </Button>
            <Button size="sm" className="gradient-primary rounded-xl" onClick={() => setDialogOpen(true)}>
              <Plus size={14} /> New meeting
            </Button>
          </div>
        }
      />
      <NewMeetingDialog workspaceId={workspaceId} open={dialogOpen} onOpenChange={setDialogOpen} />
      <UploadTranscriptDialog workspaceId={workspaceId} open={uploadOpen} onOpenChange={setUploadOpen} />
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading meetings…</p>
      ) : (
        <>
          {(() => {
            const upcoming = meetings.filter((m) => m.status === "scheduled" || m.status === "ready");
            const live = meetings.filter((m) => m.status === "live");
            const past = meetings.filter((m) => m.status === "ended" || m.status === "cancelled");

            const renderCard = (m: Meeting) => (
              <Card key={m.id} className="glass-card hover-lift p-5">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    to={`/business/manager/workspaces/${workspaceId}/meeting/${m.id}`}
                    className="flex min-w-0 flex-1 items-center gap-3"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent">
                      <Calendar size={16} />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold truncate">{m.title}</h3>
                      <p className="text-xs text-muted-foreground">{format(m.startTime, "EEE, MMM d · HH:mm")}</p>
                    </div>
                  </Link>
                  <div className="flex shrink-0 items-center gap-1">
                    <StatusBadge status={m.status} />
                    {m.status !== "live" && (
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 rounded-lg text-muted-foreground hover:text-destructive"
                            disabled={deletingId === m.id}
                            aria-label={`Delete ${m.title}`}
                          >
                            {deletingId === m.id ? (
                              <Loader2 size={14} className="animate-spin" />
                            ) : (
                              <Trash2 size={14} />
                            )}
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete {m.title}?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This removes the meeting and all related tasks, transcript, summary, and
                              pending reviews from the project.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              onClick={() => onDelete(m)}
                            >
                              Delete meeting
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    )}
                  </div>
                </div>
                {m.summary && (
                  <Link to={`/business/manager/workspaces/${workspaceId}/meeting/${m.id}`}>
                    <p className="mt-3 text-sm text-muted-foreground line-clamp-2">{m.summary}</p>
                  </Link>
                )}
              </Card>
            );

            return (
              <div className="space-y-8">
                {live.length > 0 && (
                  <section>
                    <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-primary">Live now</h2>
                    <div className="grid gap-4 md:grid-cols-2">{live.map(renderCard)}</div>
                  </section>
                )}
                <section>
                  <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Upcoming</h2>
                  <div className="grid gap-4 md:grid-cols-2">
                    {upcoming.map(renderCard)}
                    {upcoming.length === 0 && (
                      <p className="text-sm text-muted-foreground col-span-2">No upcoming meetings scheduled.</p>
                    )}
                  </div>
                </section>
                <section>
                  <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">Past</h2>
                  <div className="grid gap-4 md:grid-cols-2">
                    {past.map(renderCard)}
                    {past.length === 0 && (
                      <p className="text-sm text-muted-foreground col-span-2">No past meetings yet.</p>
                    )}
                  </div>
                </section>
                {meetings.length === 0 && <p className="text-sm text-muted-foreground">No meetings yet.</p>}
              </div>
            );
          })()}
        </>
      )}
    </DashboardLayout>
  );
}
