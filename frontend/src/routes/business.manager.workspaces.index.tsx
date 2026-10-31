import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Logo } from "@/components/brand/Logo";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/lib/auth-context";
import { useWorkspace } from "@/lib/workspace-context";
import { Plus, Users, ArrowRight, Trash2, Copy } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/business/manager/workspaces/")({ component: Page });

function Page() {
  const { user, isLoading } = useAuth();
  const { workspaces, createWorkspace, deleteWorkspace, deleteAll } = useWorkspace();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  useEffect(() => { if (!isLoading && !user) navigate({ to: "/auth" }); }, [user, isLoading, navigate]);
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }
  if (!user) return null;

  const managerWs = workspaces.filter((w) => w.role === "manager");

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border/60 px-6">
        <Link to="/"><Logo /></Link>
        <Button variant="ghost" size="sm" className="ml-auto" onClick={() => navigate({ to: "/profile" })}>Profile</Button>
      </header>
      <div className="mx-auto max-w-6xl p-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Your Projects</h1>
            <p className="mt-1 text-sm text-muted-foreground">Workspaces where you're a manager.</p>
          </div>
          <div className="flex gap-2">
            {managerWs.length > 0 && (
              <AlertDialog>
                <AlertDialogTrigger asChild><Button variant="outline" size="sm" className="rounded-xl"><Trash2 size={14} /> Delete all</Button></AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader><AlertDialogTitle>Delete all workspaces?</AlertDialogTitle><AlertDialogDescription>This cannot be undone.</AlertDialogDescription></AlertDialogHeader>
                  <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={async () => { await deleteAll(); toast.success("All workspaces deleted"); }}>Delete</AlertDialogAction></AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            )}
            <Button size="sm" className="gradient-primary rounded-xl" onClick={() => setOpen(true)}><Plus size={14} /> Create workspace</Button>
          </div>
        </div>

        {managerWs.length === 0 ? (
          <div className="space-y-4">
            <Card className="glass-card p-12 text-center">
              <h3 className="text-lg font-semibold">No workspaces yet</h3>
              <p className="mt-1 text-sm text-muted-foreground">Create your first workspace to get started.</p>
              <Button className="mt-4 gradient-primary rounded-xl" onClick={() => setOpen(true)}><Plus size={14} /> Create workspace</Button>
            </Card>
            <Card className="glass-card border-primary/20 bg-primary/5 p-6">
              <h4 className="font-semibold">Getting started as a manager</h4>
              <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                <li>1. Create a workspace and share the invite code with your team.</li>
                <li>2. Schedule your first meeting — Consilium transcribes and extracts tasks live.</li>
                <li>3. Review the Kanban board and let AI agents handle PRDs, risks, and monitoring.</li>
              </ul>
            </Card>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {managerWs.map((w) => (
              <Card key={w.id} className="glass-card hover-lift group p-5">
                <div className="flex items-start justify-between">
                  <div className="h-10 w-10 gradient-primary rounded-xl shadow-glow" />
                  <Badge variant="outline" className="gap-1 rounded-full"><Users size={11} /> {w.memberCount}</Badge>
                </div>
                <h3 className="mt-4 text-lg font-bold">{w.name}</h3>
                <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="font-mono">{w.inviteCode}</span>
                  <button onClick={() => { navigator.clipboard.writeText(w.inviteCode); toast.success("Code copied"); }} className="hover:text-foreground"><Copy size={11} /></button>
                </div>
                <div className="mt-4 flex items-center gap-2">
                  <Button size="sm" className="flex-1 gradient-primary rounded-xl" onClick={() => navigate({ to: `/business/manager/workspaces/${w.id}/dashboard` })}>
                    Enter <ArrowRight size={14} />
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild><Button variant="ghost" size="icon" className="rounded-xl"><Trash2 size={14} /></Button></AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader><AlertDialogTitle>Delete {w.name}?</AlertDialogTitle><AlertDialogDescription>All meetings, tasks and data will be lost.</AlertDialogDescription></AlertDialogHeader>
                      <AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={async () => { await deleteWorkspace(w.id); toast.success("Workspace deleted"); }}>Delete</AlertDialogAction></AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Create workspace</DialogTitle></DialogHeader>
          <Input placeholder="Workspace name" value={name} onChange={(e) => setName(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button className="gradient-primary" onClick={async () => {
              if (!name.trim()) return;
              const ws = await createWorkspace(name, "manager");
              setOpen(false); setName("");
              toast.success("Workspace created");
              navigate({ to: `/business/manager/workspaces/${ws.id}/dashboard` });
            }}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
