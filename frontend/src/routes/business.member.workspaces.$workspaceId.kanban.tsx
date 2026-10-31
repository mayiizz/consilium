import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { KanbanBoard } from "@/components/kanban/KanbanBoard";

export const Route = createFileRoute("/business/member/workspaces/$workspaceId/kanban")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  return (
    <DashboardLayout role="member" workspaceId={workspaceId}>
      <PageHeader title="Kanban Board" />
      <KanbanBoard workspaceId={workspaceId} showExtract={false} />
    </DashboardLayout>
  );
}
