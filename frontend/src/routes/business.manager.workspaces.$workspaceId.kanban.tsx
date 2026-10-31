import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { KanbanBoard } from "@/components/kanban/KanbanBoard";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/kanban")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader title="Kanban Board" description="Automate from meetings with RAG, then drag to refine. Low-confidence tasks land in the review queue." />
      <KanbanBoard workspaceId={workspaceId} showExtract />
    </DashboardLayout>
  );
}
