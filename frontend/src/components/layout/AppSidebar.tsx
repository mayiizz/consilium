import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard, Video, ListTodo, KanbanSquare, Users, BarChart3, GitBranch,
  Map as MapIcon, AlertTriangle, Settings, FolderOpen, Crown, Microscope,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/brand/Logo";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

type NavItem = { to: string; label: string; icon: any; badge?: number };

function buildManagerNav(wsId: string): NavItem[] {
  const base = `/business/manager/workspaces/${wsId}`;
  return [
    { to: `${base}/dashboard`, label: "Dashboard", icon: LayoutDashboard },
    { to: `${base}/meetings`, label: "Meetings", icon: Video, badge: 1 },
    { to: `${base}/tasks`, label: "Tasks", icon: ListTodo },
    { to: `${base}/kanban`, label: "Kanban", icon: KanbanSquare },
    { to: `${base}/documents`, label: "Documents", icon: FolderOpen },
    { to: `${base}/research`, label: "Research", icon: Microscope },
    { to: `${base}/team`, label: "Team", icon: Users },
    { to: `${base}/analytics`, label: "Analytics", icon: BarChart3 },
    { to: `${base}/integrations`, label: "Integrations", icon: GitBranch },
    { to: `${base}/roadmap`, label: "Roadmap", icon: MapIcon },
    { to: `${base}/risks`, label: "Risks", icon: AlertTriangle },
    { to: `${base}/settings`, label: "Settings", icon: Settings },
  ];
}

function buildMemberNav(wsId: string): NavItem[] {
  const base = `/business/member/workspaces/${wsId}`;
  return [
    { to: `${base}/dashboard`, label: "Dashboard", icon: LayoutDashboard },
    { to: `${base}/meetings`, label: "Meetings", icon: Video },
    { to: `${base}/tasks`, label: "My Tasks", icon: ListTodo },
    { to: `${base}/kanban`, label: "Kanban", icon: KanbanSquare },
    { to: `${base}/documents`, label: "Documents", icon: FolderOpen },
  ];
}

export function AppSidebar({ role, workspaceId }: { role: "manager" | "member"; workspaceId: string }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const nav = role === "manager" ? buildManagerNav(workspaceId) : buildMemberNav(workspaceId);

  return (
    <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-border/60 bg-sidebar">
      <div className="p-4">
        <Logo subtitle="Business Dashboard" />
      </div>
      <div className="px-3 pb-3">
        <WorkspaceSwitcher role={role} />
      </div>
      <div className="px-3 pt-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
        {role}
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {nav.map((item) => {
          const active = pathname === item.to;
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "group relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-accent text-accent-foreground active-pulse" : "text-foreground/70 hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon size={16} className={cn(active ? "text-primary" : "text-muted-foreground group-hover:text-foreground")} />
              <span className="flex-1 truncate">{item.label}</span>
              {item.badge && (
                <span className="rounded-full bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground">{item.badge}</span>
              )}
            </Link>
          );
        })}
      </nav>
      <div className="p-3">
        <div className="rounded-2xl gradient-primary p-4 text-white shadow-glow">
          <Crown size={18} className="mb-2" />
          <div className="text-sm font-bold">Upgrade to Pro</div>
          <div className="mt-1 text-xs opacity-90">Unlimited meetings, all agents, priority support.</div>
          <button className="mt-3 w-full rounded-lg bg-white/15 px-3 py-1.5 text-xs font-semibold backdrop-blur hover:bg-white/25">
            See plans
          </button>
        </div>
      </div>
    </aside>
  );
}
