import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { NewMeetingDialog } from "@/components/meetings/NewMeetingDialog";
import { UploadTranscriptDialog } from "@/components/meetings/UploadTranscriptDialog";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { StatusBadge } from "@/components/StatusBadge";
import { useDashboard } from "@/lib/api/hooks/useAnalytics";
import { Upload, Calendar, Radio, ListTodo, CheckCircle2, AlertTriangle, TrendingUp } from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/dashboard")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  const { data, isLoading } = useDashboard(workspaceId);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  if (isLoading || !data) {
    return (
      <DashboardLayout role="manager" workspaceId={workspaceId}>
        <p className="text-sm text-muted-foreground p-6">Loading dashboard…</p>
      </DashboardLayout>
    );
  }

  const { liveMeeting: live, upcomingMeetings: upcoming, recentMeetings: recent, members, teamScore, taskCounts, overdue } = data;

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader
        title="Welcome back, Captain"
        description="Here's what's happening across your team today."
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              className="rounded-xl"
              onClick={() => setUploadOpen(true)}
            >
              <Upload size={14} /> Upload file
            </Button>
            <Button size="sm" className="gradient-primary rounded-xl" onClick={() => setDialogOpen(true)}>
              <Calendar size={14} /> Schedule meeting
            </Button>
          </>
        }
      />
      <NewMeetingDialog workspaceId={workspaceId} open={dialogOpen} onOpenChange={setDialogOpen} defaultTab="scheduled" />
      <UploadTranscriptDialog workspaceId={workspaceId} open={uploadOpen} onOpenChange={setUploadOpen} />

      {live && (
        <Card className="mb-6 border-success/30 bg-success/5 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-success/15">
                <Radio className="h-5 w-5 animate-pulse text-success" />
              </div>
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-success">Live now</div>
                <div className="font-semibold">{live.title}</div>
              </div>
            </div>
            <Button
              size="sm"
              className="bg-success text-success-foreground hover:bg-success/90 rounded-xl"
              onClick={() => live.jitsiUrl && window.open(live.jitsiUrl, "_blank", "noopener,noreferrer")}
            >
              Join meeting
            </Button>
          </div>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={ListTodo} label="To Do" value={taskCounts.todo} color="muted-foreground" />
        <StatCard icon={TrendingUp} label="In Progress" value={taskCounts.in_progress} color="primary" trend="+3 this week" />
        <StatCard icon={CheckCircle2} label="Completed" value={taskCounts.done} color="success" trend="+5 this week" />
        <StatCard icon={AlertTriangle} label="Overdue" value={overdue} color="destructive" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2 glass-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold">Upcoming meetings</h3>
            <Badge variant="outline" className="rounded-full">{upcoming.length} scheduled</Badge>
          </div>
          <div className="space-y-3">
            {upcoming.map((m) => (
              <div key={m.id} className="flex items-center gap-3 rounded-xl border border-border/60 p-3 hover:border-primary/30">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-foreground">
                  <Calendar size={16} />
                </div>
                <div className="flex-1">
                  <div className="font-medium">{m.title}</div>
                  <div className="text-xs text-muted-foreground">{format(m.startTime, "EEE, MMM d · HH:mm")}</div>
                </div>
                <div className="flex -space-x-2">
                  {m.participants.slice(0, 3).map((p) => (
                    <Avatar key={p.id} className="h-7 w-7 ring-2 ring-background"><AvatarImage src={p.avatar} /><AvatarFallback>{p.name[0]}</AvatarFallback></Avatar>
                  ))}
                </div>
                <StatusBadge status={m.status} />
              </div>
            ))}
            {upcoming.length === 0 && <p className="text-sm text-muted-foreground">No upcoming meetings.</p>}
          </div>
        </Card>

        <Card className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold">Team score</h3>
            <span className="text-2xl font-extrabold gradient-text">{teamScore}%</span>
          </div>
          <Progress value={teamScore} className="h-2" />
          <p className="mt-3 text-xs text-muted-foreground">Throughput is up 12% vs last sprint. Two members at-risk for capacity.</p>
          <div className="mt-4 space-y-3">
            {members.slice(0, 3).map((m) => {
              const pct = Math.round((m.tasksCompleted / m.tasksAssigned) * 100);
              return (
                <div key={m.id}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2"><Avatar className="h-5 w-5"><AvatarImage src={m.avatar} /></Avatar>{m.name}</div>
                    <span className="text-muted-foreground">{m.tasksCompleted}/{m.tasksAssigned}</span>
                  </div>
                  <Progress value={pct} className="h-1.5" />
                </div>
              );
            })}
          </div>
        </Card>
      </div>

      <Card className="mt-6 glass-card p-5">
        <h3 className="mb-4 font-semibold">Recent meetings</h3>
        <div className="divide-y divide-border/60">
          {recent.map((m) => (
            <div key={m.id} className="flex items-center justify-between gap-3 py-3">
              <div>
                <div className="font-medium">{m.title}</div>
                <div className="text-xs text-muted-foreground">{formatDistanceToNow(m.startTime, { addSuffix: true })}{m.duration ? ` · ${m.duration}m` : ""}</div>
              </div>
              <StatusBadge status={m.status} />
            </div>
          ))}
          {recent.length === 0 && <p className="text-sm text-muted-foreground py-3">No recent meetings.</p>}
        </div>
      </Card>
    </DashboardLayout>
  );
}

const STAT_STYLES: Record<string, string> = {
  "muted-foreground": "bg-muted text-muted-foreground",
  primary: "bg-primary/10 text-primary",
  success: "bg-success/10 text-success",
  destructive: "bg-destructive/10 text-destructive",
};

function StatCard({ icon: Icon, label, value, color, trend }: { icon: React.ComponentType<{ size?: number }>; label: string; value: number; color: string; trend?: string }) {
  return (
    <Card className="glass-card p-5">
      <div className="flex items-center gap-3">
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${STAT_STYLES[color] || "bg-muted text-muted-foreground"}`}>
          <Icon size={18} />
        </div>
        <div>
          <div className="text-xs text-muted-foreground">{label}</div>
          <div className="text-2xl font-extrabold tabular-nums">{value}</div>
        </div>
      </div>
      {trend && <div className="mt-3 text-xs text-success">{trend}</div>}
    </Card>
  );
}
