import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { useTeam } from "@/lib/api/hooks/useAnalytics";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/team")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  const { data: members = [], isLoading } = useTeam(workspaceId);

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader title="Team" description="Members, roles, and workload." />
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading team…</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {members.map((m) => {
            const pct = Math.round((m.tasksCompleted / m.tasksAssigned) * 100);
            return (
              <Card key={m.id} className="glass-card p-5">
                <div className="flex items-center gap-3">
                  <Avatar className="h-12 w-12"><AvatarImage src={m.avatar} /><AvatarFallback>{m.name[0]}</AvatarFallback></Avatar>
                  <div>
                    <h3 className="font-semibold">{m.name}</h3>
                    <p className="text-xs text-muted-foreground">{m.email}</p>
                  </div>
                </div>
                <Badge variant="outline" className="mt-3 rounded-full">{m.role}</Badge>
                <div className="mt-3 flex flex-wrap gap-1">
                  {m.skills.map((s) => <Badge key={s} variant="secondary" className="text-[10px]">{s}</Badge>)}
                </div>
                <div className="mt-4">
                  <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                    <span>Tasks</span><span>{m.tasksCompleted}/{m.tasksAssigned}</span>
                  </div>
                  <Progress value={pct} className="h-1.5" />
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </DashboardLayout>
  );
}
