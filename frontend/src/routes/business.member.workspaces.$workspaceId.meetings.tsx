import { createFileRoute, Link } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { useMeetings } from "@/lib/api/hooks/useMeetings";
import { Calendar } from "lucide-react";
import { format } from "date-fns";

export const Route = createFileRoute("/business/member/workspaces/$workspaceId/meetings")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  const { data: meetings = [], isLoading } = useMeetings(workspaceId);

  return (
    <DashboardLayout role="member" workspaceId={workspaceId}>
      <PageHeader title="Meetings" description="Upcoming and past meetings you're part of." />
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <div className="space-y-3">
          {meetings.map((m) => (
            <Link key={m.id} to={`/business/member/workspaces/${workspaceId}/meeting/${m.id}`}>
              <Card className="glass-card p-4 flex items-center gap-3 cursor-pointer hover-lift">
                <Calendar size={16} className="text-muted-foreground" />
                <div className="flex-1">
                  <div className="font-medium">{m.title}</div>
                  <div className="text-xs text-muted-foreground">{format(m.startTime, "EEE, MMM d · HH:mm")}</div>
                </div>
                <StatusBadge status={m.status} />
              </Card>
            </Link>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
