import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle } from "lucide-react";
import { useRisks } from "@/lib/api/hooks/useAnalytics";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/risks")({ component: Page });

const SEV: Record<string, string> = {
  high: "bg-destructive/15 text-destructive border-destructive/30",
  medium: "bg-warning/15 text-warning border-warning/30",
  low: "bg-muted text-muted-foreground border-border",
};

function Page() {
  const { workspaceId } = Route.useParams();
  const { data: risks = [], isLoading } = useRisks(workspaceId);
  const sorted = [...risks].sort((a, b) => (a.severity === "high" ? -1 : 1));

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader title="Risks" description="Track blockers and slipping work. Ranked by severity." />
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading risks…</p>
      ) : (
        <div className="space-y-3">
          {sorted.map((r) => (
            <Card key={r.id} className="glass-card p-5">
              <div className="flex items-start gap-3">
                <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", SEV[r.severity])}><AlertTriangle size={18} /></div>
                <div className="flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-semibold">{r.title}</h3>
                    <Badge className={cn("rounded-full capitalize", SEV[r.severity])}>{r.severity}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{r.impact}</p>
                  <div className="mt-2 text-xs text-muted-foreground">Owner: <span className="font-medium text-foreground">{r.owner}</span></div>
                </div>
              </div>
            </Card>
          ))}
          {sorted.length === 0 && (
            <Card className="glass-card p-5">
              <p className="text-sm text-muted-foreground">
                No blocked tasks right now. Mark tasks as Blockers from the task dialog, or extract blockers from meetings — then open them via the Blockers button on Kanban.
              </p>
            </Card>
          )}
        </div>
      )}
    </DashboardLayout>
  );
}
