import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useRoadmap } from "@/lib/api/hooks/useAnalytics";
import { enrichRoadmapPhases } from "@/lib/demo/sprintDemo";
import { CheckCircle2, Circle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/roadmap")({ component: Page });

const MILESTONE_STATUS = {
  done: "bg-success/15 text-success border-success/30",
  active: "bg-primary/15 text-primary border-primary/30",
  planned: "bg-muted text-muted-foreground",
};

function Page() {
  const { workspaceId } = Route.useParams();
  const { data: phases = [], isLoading } = useRoadmap(workspaceId);
  const enriched = enrichRoadmapPhases(phases);

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader title="Roadmap" description="5-day sprint from architecture to stakeholder demo." />
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading roadmap…</p>
      ) : (
        <div className="relative space-y-4 pl-8">
          <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-gradient-to-b from-primary via-secondary to-border" />
          {enriched.map((p) => {
            const Icon = p.status === "done" ? CheckCircle2 : p.status === "active" ? Clock : Circle;
            return (
              <Card key={p.id} className="glass-card relative p-5">
                <div className="absolute -left-[26px] top-5 flex h-6 w-6 items-center justify-center rounded-full bg-background">
                  <Icon size={20} className={p.status === "done" ? "text-success" : p.status === "active" ? "text-primary animate-pulse" : "text-muted-foreground"} />
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="font-bold">{p.name}</h3>
                    {p.subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{p.subtitle}</p>}
                  </div>
                  <Badge variant="outline" className="rounded-full">{p.q}</Badge>
                </div>
                <div className="mt-3 flex items-center gap-3">
                  <Progress value={p.progress} className="h-2 flex-1" />
                  <span className="text-xs font-medium text-muted-foreground">{p.progress}%</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {p.milestones.length > 0 ? (
                    p.milestones.map((m) => (
                      <Badge key={m.name} variant="outline" className={cn("rounded-full", MILESTONE_STATUS[m.status])}>
                        {m.name} · {m.taskCount}
                      </Badge>
                    ))
                  ) : (
                    <Badge variant="outline" className="rounded-full text-muted-foreground">No milestones yet</Badge>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </DashboardLayout>
  );
}
