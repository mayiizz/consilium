import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { TaskCard } from "@/components/TaskCard";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useTasks } from "@/lib/api/hooks/useTasks";
import { STATUS_LABELS, STATUS_ORDER } from "@/lib/constants";
import type { TaskStatus } from "@/lib/types";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/tasks")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  const [filter, setFilter] = useState<"all" | TaskStatus>("all");
  const { data: tasks = [], isLoading } = useTasks(workspaceId);
  const filtered = filter === "all" ? tasks : tasks.filter((t) => t.status === filter);

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader title="Tasks" description="All workspace tasks in one view." />
      <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          {STATUS_ORDER.map((s) => <TabsTrigger key={s} value={s}>{STATUS_LABELS[s]}</TabsTrigger>)}
        </TabsList>
      </Tabs>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {isLoading ? <p className="text-sm text-muted-foreground">Loading…</p> : filtered.map((t) => <TaskCard key={t.id} task={t} workspaceId={workspaceId} />)}
      </div>
    </DashboardLayout>
  );
}
