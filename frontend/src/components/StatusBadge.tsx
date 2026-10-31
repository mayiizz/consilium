import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { MeetingStatus } from "@/lib/types";

const styles: Record<MeetingStatus, string> = {
  live: "bg-success/15 text-success border-success/30",
  ready: "bg-primary/15 text-primary border-primary/30",
  scheduled: "bg-muted text-muted-foreground border-border",
  ended: "bg-secondary/15 text-secondary border-secondary/30",
  cancelled: "bg-muted text-muted-foreground border-border",
};

export function StatusBadge({ status }: { status: MeetingStatus }) {
  return (
    <Badge variant="outline" className={cn("gap-1.5 rounded-full capitalize", styles[status])}>
      {status === "live" && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
        </span>
      )}
      {status}
    </Badge>
  );
}
