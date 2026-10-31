import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { StatusBadge } from "@/components/StatusBadge";
import { useDashboard } from "@/lib/api/hooks/useAnalytics";
import { Calendar, ListTodo, CheckCircle2, AlertTriangle } from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";

export const Route = createFileRoute("/business/member/workspaces/$workspaceId/dashboard")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  const { data, isLoading } = useDashboard(workspaceId);

  if (isLoading || !data) {
    return (
      <DashboardLayout role="member" workspaceId={workspaceId}>
        <p className="text-sm text-muted-foreground p-6">Loading dashboard…</p>
      </DashboardLayout>
    );
  }

  const { upcomingMeetings, recentMeetings, taskCounts, overdue } = data;
  const myActive = taskCounts.in_progress + taskCounts.in_review;

  return (
    <DashboardLayout role="member" workspaceId={workspaceId}>
      <PageHeader title="Your workspace" description="Tasks and meetings assigned to you." />
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="glass-card p-5"><div className="text-xs text-muted-foreground">My active tasks</div><div className="text-2xl font-bold">{myActive}</div></Card>
        <Card className="glass-card p-5"><div className="text-xs text-muted-foreground">To do</div><div className="text-2xl font-bold">{taskCounts.todo}</div></Card>
        <Card className="glass-card p-5"><div className="text-xs text-muted-foreground">Overdue</div><div className="text-2xl font-bold text-destructive">{overdue}</div></Card>
      </div>
      <Card className="mt-6 glass-card p-5">
        <h3 className="mb-4 font-semibold">Upcoming meetings</h3>
        <div className="space-y-3">
          {upcomingMeetings.map((m) => (
            <div key={m.id} className="flex items-center gap-3 rounded-xl border border-border/60 p-3">
              <Calendar size={16} className="text-muted-foreground" />
              <div className="flex-1">
                <div className="font-medium">{m.title}</div>
                <div className="text-xs text-muted-foreground">{format(m.startTime, "EEE, MMM d · HH:mm")}</div>
              </div>
              <StatusBadge status={m.status} />
            </div>
          ))}
          {upcomingMeetings.length === 0 && <p className="text-sm text-muted-foreground">No upcoming meetings.</p>}
        </div>
      </Card>
      <Card className="mt-6 glass-card p-5">
        <h3 className="mb-4 font-semibold">Recent summaries</h3>
        {recentMeetings.map((m) => (
          <div key={m.id} className="py-3 border-b border-border/60 last:border-0">
            <div className="font-medium">{m.title}</div>
            <div className="text-xs text-muted-foreground">{formatDistanceToNow(m.startTime, { addSuffix: true })}</div>
            {m.summary && <p className="mt-1 text-sm text-muted-foreground">{m.summary}</p>}
          </div>
        ))}
      </Card>
    </DashboardLayout>
  );
}
