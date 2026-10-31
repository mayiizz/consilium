import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useWorkspace } from "@/lib/workspace-context";
import { toast } from "sonner";

export const Route = createFileRoute("/join/workspace/$code")({ component: Page });

function Page() {
  const { code } = Route.useParams();
  const { user, isLoading } = useAuth();
  const { joinWorkspace } = useWorkspace();
  const navigate = useNavigate();

  useEffect(() => {
    if (isLoading) return;
    if (!user) { navigate({ to: "/auth" }); return; }
    (async () => {
      const ws = await joinWorkspace(code);
      if (ws) {
        toast.success(`Joined ${ws.name}`);
        navigate({ to: `/business/member/workspaces/${ws.id}/dashboard` });
      } else {
        toast.error("Invalid invite code");
        navigate({ to: "/business/member/workspaces" });
      }
    })();
  }, [user, isLoading, code, joinWorkspace, navigate]);

  return <div className="flex min-h-screen items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>;
}
