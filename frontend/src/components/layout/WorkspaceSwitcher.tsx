import { useState } from "react";
import { ChevronsUpDown, Plus, LogIn, Check } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/lib/workspace-context";
import { toast } from "sonner";

export function WorkspaceSwitcher({ role }: { role: "manager" | "member" }) {
  const { workspaces, currentWorkspace, setCurrentWorkspaceById, createWorkspace, joinWorkspace } = useWorkspace();
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);
  const [joinOpen, setJoinOpen] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  const onPick = (id: string) => {
    setCurrentWorkspaceById(id);
    const ws = workspaces.find((w) => w.id === id);
    if (ws) navigate({ to: `/business/${ws.role}/workspaces/${ws.id}/dashboard` });
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger className="flex w-full items-center justify-between gap-2 rounded-xl border border-border/60 bg-muted/40 px-3 py-2.5 text-sm hover:bg-muted">
          <div className="flex-1 truncate text-left">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Workspace</div>
            <div className="truncate font-semibold">{currentWorkspace?.name || "No workspace"}</div>
          </div>
          <ChevronsUpDown size={14} className="text-muted-foreground" />
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-60" align="start">
          <DropdownMenuLabel>Your workspaces</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {workspaces.map((w) => (
            <DropdownMenuItem key={w.id} onClick={() => onPick(w.id)}>
              <span className="flex-1 truncate">{w.name}</span>
              {w.id === currentWorkspace?.id && <Check size={14} className="text-primary" />}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          {role === "manager" ? (
            <DropdownMenuItem onClick={() => setCreateOpen(true)}>
              <Plus size={14} /> Create workspace
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onClick={() => setJoinOpen(true)}>
              <LogIn size={14} /> Join workspace
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create a workspace</DialogTitle>
            <DialogDescription>Give your project a home. You can invite teammates after.</DialogDescription>
          </DialogHeader>
          <Input placeholder="Workspace name" value={name} onChange={(e) => setName(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              className="gradient-primary"
              onClick={() => {
                if (!name.trim()) return;
                const ws = createWorkspace(name, "manager");
                setCreateOpen(false);
                setName("");
                toast.success("Workspace created");
                navigate({ to: `/business/manager/workspaces/${ws.id}/dashboard` });
              }}
            >
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={joinOpen} onOpenChange={setJoinOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Join a workspace</DialogTitle>
            <DialogDescription>Enter the invite code from your manager.</DialogDescription>
          </DialogHeader>
          <Input placeholder="Invite code" value={code} onChange={(e) => setCode(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setJoinOpen(false)}>Cancel</Button>
            <Button
              className="gradient-primary"
              onClick={() => {
                if (!code.trim()) return;
                const ws = joinWorkspace(code);
                setJoinOpen(false);
                setCode("");
                if (ws) {
                  toast.success("Joined workspace");
                  navigate({ to: `/business/member/workspaces/${ws.id}/dashboard` });
                }
              }}
            >
              Join
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
