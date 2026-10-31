import { Loader2, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useKanbanReviewQueue,
  useApproveKanbanReview,
  useRejectKanbanReview,
} from "@/lib/api/hooks/useKanbanReview";
import { toast } from "sonner";

export function KanbanReviewQueue({ workspaceId }: { workspaceId: string }) {
  const { data: items = [], isLoading } = useKanbanReviewQueue(workspaceId);
  const approve = useApproveKanbanReview(workspaceId);
  const reject = useRejectKanbanReview(workspaceId);

  if (isLoading) return null;
  if (items.length === 0) return null;

  return (
    <div className="mb-4 rounded-2xl border border-warning/30 bg-warning/5 p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Tasks pending review</h3>
        <Badge variant="outline" className="rounded-full text-[10px]">
          {items.length}
        </Badge>
      </div>
      <div className="space-y-2">
        {items.map((item) => {
          const c = item.candidate ?? {};
          const busy = approve.isPending || reject.isPending;
          return (
            <div
              key={item.id}
              className="flex flex-col gap-2 rounded-xl border border-border/60 bg-card p-3 sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{c.title || "Untitled task"}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {c.assignee ? `Assignee: ${c.assignee}` : "No assignee"}
                  {c.confidence != null ? ` · Confidence ${Math.round(c.confidence * 100)}%` : ""}
                </p>
                {c.evidence && (
                  <p className="mt-1 line-clamp-2 text-[11px] italic text-muted-foreground">
                    &ldquo;{c.evidence}&rdquo;
                  </p>
                )}
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="rounded-xl"
                  disabled={busy}
                  onClick={() =>
                    reject.mutate(item.id, {
                      onSuccess: () => toast.success("Review item dismissed"),
                      onError: () => toast.error("Failed to reject"),
                    })
                  }
                >
                  <X size={14} />
                  Reject
                </Button>
                <Button
                  size="sm"
                  className="gradient-primary rounded-xl"
                  disabled={busy}
                  onClick={() =>
                    approve.mutate(item.id, {
                      onSuccess: () => toast.success("Task added to board"),
                      onError: () => toast.error("Failed to approve"),
                    })
                  }
                >
                  {approve.isPending ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                  Approve
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
