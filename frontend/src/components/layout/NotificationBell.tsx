import { formatDistanceToNow } from "date-fns";
import { Bell } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "@/lib/api/hooks/useNotifications";
import { cn } from "@/lib/utils";

export function NotificationBell() {
  const { data } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();
  const items = data?.items ?? [];
  const unread = data?.unreadCount ?? 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="relative rounded-xl p-2 hover:bg-muted">
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-destructive-foreground">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between gap-2">
          <span>Notifications</span>
          {unread > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={(e) => {
                e.preventDefault();
                markAll.mutate();
              }}
            >
              Mark all read
            </Button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {items.length === 0 ? (
          <DropdownMenuItem className="text-sm text-muted-foreground" disabled>
            No notifications yet
          </DropdownMenuItem>
        ) : (
          items.slice(0, 12).map((n) => (
            <DropdownMenuItem
              key={n.id}
              className={cn(
                "flex cursor-pointer flex-col items-start gap-0.5 py-2",
                !n.readAt && "bg-primary/5",
              )}
              onClick={() => {
                if (!n.readAt) markRead.mutate(n.id);
              }}
            >
              <span className="text-sm font-medium">{n.title}</span>
              {n.body ? (
                <span className="line-clamp-2 text-xs text-muted-foreground">{n.body}</span>
              ) : null}
              <span className="text-[10px] text-muted-foreground">
                {formatDistanceToNow(new Date(n.createdAt), { addSuffix: true })}
              </span>
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
