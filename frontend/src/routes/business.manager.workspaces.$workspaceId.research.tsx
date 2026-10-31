import { createFileRoute } from "@tanstack/react-router";
import { ResearchPage } from "@/components/research/ResearchPage";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/research")({
  component: Page,
});

function Page() {
  const { workspaceId } = Route.useParams();
  return <ResearchPage workspaceId={workspaceId} />;
}
