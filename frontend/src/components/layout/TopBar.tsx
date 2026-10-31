import { useEffect, useState } from "react";
import { Search, LogOut, UserIcon, Radio } from "lucide-react";
import { format } from "date-fns";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth-context";
import { useNavigate } from "@tanstack/react-router";
import { useMeetings } from "@/lib/api/hooks/useMeetings";
import { NotificationBell } from "@/components/layout/NotificationBell";

export function TopBar({ workspaceId }: { workspaceId?: string }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [now, setNow] = useState(new Date());
  const { data: meetings = [] } = useMeetings(workspaceId ?? "");

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const liveMeeting = meetings.find((m) => m.status === "live");

  return (
    <header className="glass sticky top-0 z-30 flex h-16 items-center gap-4 px-6">
      <div className="relative w-72">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input placeholder="Search tasks, meetings, people…" className="rounded-xl bg-muted/50 pl-9 border-transparent focus-visible:border-primary/40" />
      </div>
      <div className="ml-auto flex items-center gap-4">
        <div className="hidden md:flex items-center gap-3 text-sm">
          <span className="font-mono font-semibold tabular-nums">{format(now, "HH:mm:ss")}</span>
          <span className="text-muted-foreground">{format(now, "EEE, MMM d")}</span>
        </div>
        {liveMeeting && (
          <div className="hidden lg:flex items-center gap-2 rounded-full bg-success/10 px-3 py-1.5 text-xs font-medium text-success">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
            </span>
            <Radio size={12} /> Live: {liveMeeting.title}
          </div>
        )}
        <NotificationBell />
        <DropdownMenu>
          <DropdownMenuTrigger>
            <Avatar className="h-9 w-9 ring-2 ring-primary/20">
              <AvatarImage src={user?.avatar} />
              <AvatarFallback>{user?.name?.[0] || "U"}</AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="font-semibold">{user?.name}</div>
              <div className="text-xs font-normal text-muted-foreground">{user?.email}</div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => navigate({ to: "/profile" })}>
              <UserIcon size={14} /> Profile
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => { logout(); navigate({ to: "/" }); }}>
              <LogOut size={14} /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
