import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Logo } from "@/components/brand/Logo";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { useAuth } from "@/lib/auth-context";
import { useWorkspace } from "@/lib/workspace-context";
import { LogIn, Users, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/business/member/workspaces/")({ component: Page });

function Page() {
  const { user, isLoading } = useAuth();
  const { workspaces, joinWorkspace } = useWorkspace();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [code, setCode] = useState("");

  useEffect(() => { if (!isLoading && !user) navigate({ to: "/auth" }); }, [user, isLoading, navigate]);
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }
  if (!user) return null;

  const memberWs = workspaces.filter((w) => w.role === "member");

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border/60 px-6">
        <Link to="/"><Logo /></Link>
      </header>
      <div className="mx-auto max-w-6xl p-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Joined Projects</h1>
            <p className="mt-1 text-sm text-muted-foreground">Workspaces you've been invited to.</p>
          </div>
          <Button size="sm" className="gradient-primary rounded-xl" onClick={() => setOpen(true)}><LogIn size={14} /> Join workspace</Button>
        </div>

        {memberWs.length === 0 ? (
          <div className="space-y-4">
            <Card className="glass-card p-12 text-center">
              <h3 className="text-lg font-semibold">No workspaces yet</h3>
              <p className="mt-1 text-sm text-muted-foreground">Ask your manager for an invite code.</p>
              <Button className="mt-4 gradient-primary rounded-xl" onClick={() => setOpen(true)}>Join workspace</Button>
            </Card>
            <Card className="glass-card border-primary/20 bg-primary/5 p-6">
              <h4 className="font-semibold">How to join a workspace</h4>
              <p className="mt-2 text-sm text-muted-foreground">
                Your manager will share an invite code like <span className="font-mono font-medium text-foreground">ACME-7K2X</span> or <span className="font-mono font-medium text-foreground">HELIOS-99</span>.
                Paste it above to join instantly — no email invite required.
              </p>
            </Card>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {memberWs.map((w) => (
              <Card key={w.id} className="glass-card hover-lift p-5">
                <div className="flex items-start justify-between">
                  <div className="h-10 w-10 gradient-primary rounded-xl shadow-glow" />
                  <Badge variant="outline" className="gap-1 rounded-full"><Users size={11} /> {w.memberCount}</Badge>
                </div>
                <h3 className="mt-4 text-lg font-bold">{w.name}</h3>
                <div className="mt-2 text-xs text-muted-foreground"><span className="font-mono">{w.inviteCode}</span></div>
                <Button size="sm" className="mt-4 w-full gradient-primary rounded-xl" onClick={() => navigate({ to: `/business/member/workspaces/${w.id}/dashboard` })}>
                  Enter <ArrowRight size={14} />
                </Button>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Join workspace</DialogTitle></DialogHeader>
          <Input placeholder="Invite code" value={code} onChange={(e) => setCode(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button className="gradient-primary" onClick={async () => {
              if (!code.trim()) return;
              const ws = await joinWorkspace(code);
              setOpen(false); setCode("");
              if (ws) { toast.success("Joined workspace"); navigate({ to: `/business/member/workspaces/${ws.id}/dashboard` }); }
              else toast.error("Invalid invite code");
            }}>Join</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}