import { createFileRoute } from "@tanstack/react-router";
import { DocumentsPage } from "@/components/documents/DocumentsPage";

export const Route = createFileRoute("/business/member/workspaces/$workspaceId/documents")({
  component: Page,
});

function Page() {
  const { workspaceId } = Route.useParams();
  return <DocumentsPage workspaceId={workspaceId} role="member" />;
}
