import { type ReactNode, useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";
import { AppSidebar } from "./AppSidebar";
import { TopBar } from "./TopBar";
import { Copilot } from "./Copilot";
import { useAuth } from "@/lib/auth-context";
import { useWorkspace } from "@/lib/workspace-context";
import { Loader2 } from "lucide-react";

interface Props {
  role: "manager" | "member";
  workspaceId: string;
  children: ReactNode;
}

export function DashboardLayout({ role, workspaceId, children }: Props) {
  const { user, isLoading } = useAuth();
  const { workspaces, setCurrentWorkspaceById } = useWorkspace();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !user) navigate({ to: "/auth" });
  }, [user, isLoading, navigate]);

  useEffect(() => {
    if (workspaceId) setCurrentWorkspaceById(workspaceId);
  }, [workspaceId, setCurrentWorkspaceById]);

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  const wsExists = workspaces.some((w) => w.id === workspaceId);
  if (workspaces.length > 0 && !wsExists) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="text-lg font-semibold">Workspace not found</div>
        <p className="text-sm text-muted-foreground">You may not have access. Try switching workspaces.</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-background">
      <AppSidebar role={role} workspaceId={workspaceId} />
      <div className="flex flex-1 flex-col">
        <TopBar workspaceId={workspaceId} />
        <main className="flex-1 overflow-y-auto p-6 animate-fade-in">{children}</main>
      </div>
      <Copilot workspaceId={workspaceId} />
    </div>
  );
}
