import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useWorkspace } from "@/lib/workspace-context";
import * as workspaceApi from "@/lib/api/services/workspaces";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Copy, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useState } from "react";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/settings")({ component: Page });

function Page() {
  const { workspaceId } = Route.useParams();
  const { workspaces, deleteWorkspace, refreshWorkspaces } = useWorkspace();
  const ws = workspaces.find((w) => w.id === workspaceId);
  const navigate = useNavigate();
  const [name, setName] = useState(ws?.name ?? "");
  const [repo, setRepo] = useState("consilium/web");

  if (!ws) return null;

  const save = async () => {
    try {
      await workspaceApi.updateWorkspace(workspaceId, { name, github_repo: repo });
      await refreshWorkspaces();
      toast.success("Settings saved");
    } catch {
      toast.error("Failed to save");
    }
  };

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader title="Workspace settings" description="Manage your workspace and integrations." />
      <div className="space-y-6">
        <Card className="glass-card p-5">
          <h3 className="mb-4 font-semibold">General</h3>
          <div className="space-y-3">
            <div className="space-y-1.5"><Label>Workspace name</Label><Input value={name} onChange={(e) => setName(e.target.value)} /></div>
            <div className="space-y-1.5">
              <Label>Invite code</Label>
              <div className="flex gap-2">
                <Input value={ws.inviteCode} readOnly className="font-mono" />
                <Button variant="outline" onClick={() => { navigator.clipboard.writeText(ws.inviteCode); toast.success("Copied"); }}><Copy size={14} /></Button>
              </div>
            </div>
            <div className="space-y-1.5"><Label>Linked GitHub repo</Label><Input value={repo} onChange={(e) => setRepo(e.target.value)} /></div>
            <Button className="gradient-primary rounded-xl" onClick={save}>Save changes</Button>
          </div>
        </Card>
        <Card className="border-destructive/30 bg-destructive/5 p-5">
          <h3 className="font-semibold text-destructive">Danger zone</h3>
          <p className="mt-1 text-sm text-muted-foreground">Deleting a workspace is permanent.</p>
          <AlertDialog>
            <AlertDialogTrigger asChild><Button variant="destructive" className="mt-3 rounded-xl"><Trash2 size={14} /> Delete workspace</Button></AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader><AlertDialogTitle>Delete {ws.name}?</AlertDialogTitle><AlertDialogDescription>All meetings, tasks, and data will be lost.</AlertDialogDescription></AlertDialogHeader>
              <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={async () => { await deleteWorkspace(ws.id); toast.success("Workspace deleted"); navigate({ to: "/business/manager/workspaces" }); }}>Delete</AlertDialogAction></AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </Card>
      </div>
    </DashboardLayout>
  );
}
