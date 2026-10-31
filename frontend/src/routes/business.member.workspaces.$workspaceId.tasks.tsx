import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { TaskCard } from "@/components/TaskCard";
import { useTasks } from "@/lib/api/hooks/useTasks";
import { useAuth } from "@/lib/auth-context";

export const Route = createFileRoute("/business/member/workspaces/$workspaceId/tasks")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  const { user } = useAuth();
  const { data: tasks = [], isLoading } = useTasks(workspaceId);
  const myTasks = tasks.filter((t) => {
    if (!t.assignee || !user) return false;
    return t.assignee.name.toLowerCase().includes(user.name.toLowerCase().split(" ")[0]);
  });
  const display = myTasks.length > 0 ? myTasks : tasks;

  return (
    <DashboardLayout role="member" workspaceId={workspaceId}>
      <PageHeader title="My tasks" description="Tasks assigned to you." />
      <div className="grid gap-3 md:grid-cols-2">
        {isLoading ? <p className="text-sm text-muted-foreground">Loading…</p> : display.map((t) => <TaskCard key={t.id} task={t} workspaceId={workspaceId} rolePrefix="member" />)}
      </div>
    </DashboardLayout>
  );
}
