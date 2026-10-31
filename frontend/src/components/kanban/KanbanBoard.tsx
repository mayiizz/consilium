import { useState, useMemo } from "react";
import { Link } from "@tanstack/react-router";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
  useDroppable,
  useDraggable,
} from "@dnd-kit/core";
import {
  Sparkles,
  GripVertical,
  Loader2,
  AlertTriangle,
  ArrowUpRight,
  Ban,
  RefreshCw,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { TaskCard } from "@/components/TaskCard";
import { TaskGitReference } from "@/components/tasks/TaskGitReference";
import { STATUS_LABELS, STATUS_ORDER, STATUS_ACCENT, BOARD_COLUMNS } from "@/lib/constants";
import type { Priority, Task, TaskStatus } from "@/lib/types";
import { useTasks, useMoveTask, useExtractTasks, useRebuildTasks, useUpdateTask } from "@/lib/api/hooks/useTasks";
import { useMeetings } from "@/lib/api/hooks/useMeetings";
import { KanbanReviewQueue } from "@/components/kanban/KanbanReviewQueue";
import { taskDescriptionForDisplay } from "@/lib/taskDescription";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useWorkspaceGitEnabled } from "@/lib/workspace-context";

const PRIORITIES: Priority[] = ["low", "medium", "high", "urgent"];

function SourceMeetingLink({
  workspaceId,
  meetingId,
  rolePrefix = "manager",
}: {
  workspaceId: string;
  meetingId: string;
  rolePrefix?: "manager" | "member";
}) {
  return (
    <Link
      to={`/business/${rolePrefix}/workspaces/$workspaceId/meeting/$meetingId`}
      params={{ workspaceId, meetingId }}
      className="mt-1 flex items-center gap-1 text-[10px] text-primary hover:underline px-1"
      onClick={(e) => e.stopPropagation()}
    >
      <ArrowUpRight className="h-2.5 w-2.5" />
      From meeting
    </Link>
  );
}

function Column({
  status,
  tasks,
  workspaceId,
  onOpenTask,
}: {
  status: TaskStatus;
  tasks: Task[];
  workspaceId: string;
  onOpenTask: (t: Task) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div className="flex w-72 shrink-0 flex-col">
      <div className="mb-2 flex items-center gap-2 px-1">
        <span className={cn("h-1 w-full rounded-full", STATUS_ACCENT[status])} />
      </div>
      <div className="mb-2 flex items-center gap-2 px-1">
        <h3 className="text-sm font-bold">{STATUS_LABELS[status]}</h3>
        <span className="text-xs text-muted-foreground">{tasks.length}</span>
      </div>
      <div
        ref={setNodeRef}
        className={cn(
          "flex flex-1 flex-col gap-2 rounded-2xl border-2 border-t-4 bg-muted/30 p-2 transition-colors min-h-[420px]",
          status === "todo" && "border-t-muted-foreground/40 border-transparent",
          status === "in_progress" && "border-t-primary border-transparent",
          status === "in_review" && "border-t-warning border-transparent",
          status === "done" && "border-t-success border-transparent",
          isOver && "border-primary/40 bg-primary/5",
        )}
      >
        {tasks.map((t) => (
          <DraggableTask key={t.id} task={t} workspaceId={workspaceId} onOpen={() => onOpenTask(t)} />
        ))}
        {tasks.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-border/60 text-xs text-muted-foreground">
            Drop tasks here
          </div>
        )}
      </div>
    </div>
  );
}

function DraggableTask({
  task,
  workspaceId,
  onOpen,
}: {
  task: Task;
  workspaceId: string;
  onOpen: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: task.id });
  const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined;
  const overdue =
    task.dueDate && task.dueDate < new Date() && task.status !== "done";

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn("flex gap-1", isDragging && "opacity-40")}
    >
      <button
        type="button"
        className="flex-shrink-0 self-stretch rounded-md px-0.5 text-muted-foreground hover:bg-muted cursor-grab active:cursor-grabbing touch-none"
        aria-label="Drag to move"
        {...listeners}
        {...attributes}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="min-w-0 flex-1">
        <TaskCard task={task} workspaceId={workspaceId} onClick={onOpen} />
        {overdue && (
          <p className="mt-1 flex items-center gap-1 text-[10px] text-destructive px-1">
            <AlertTriangle className="h-2.5 w-2.5" />
            Overdue {formatDistanceToNow(task.dueDate!, { addSuffix: true })}
          </p>
        )}
        {task.aiGenerated && task.sourceMeetingId && (
          <SourceMeetingLink workspaceId={workspaceId} meetingId={task.sourceMeetingId} />
        )}
      </div>
    </div>
  );
}

export function KanbanBoard({
  workspaceId,
  showExtract = true,
}: {
  workspaceId: string;
  showExtract?: boolean;
}) {
  const gitEnabled = useWorkspaceGitEnabled(workspaceId);
  const { data: meetings = [] } = useMeetings(workspaceId);
  const hasLiveMeeting = meetings.some((m) => m.status === "live" || m.status === "ready");
  const { data: tasks = [], isLoading } = useTasks(workspaceId, {
    refetchInterval: hasLiveMeeting ? 5000 : false,
  });
  const moveMutation = useMoveTask(workspaceId);
  const extractMutation = useExtractTasks(workspaceId);
  const rebuildMutation = useRebuildTasks(workspaceId);
  const updateMutation = useUpdateTask(workspaceId);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [blockersOpen, setBlockersOpen] = useState(false);
  const [dialogTask, setDialogTask] = useState<Task | null>(null);
  const [dTitle, setDTitle] = useState("");
  const [dDescription, setDDescription] = useState("");
  const [dStatus, setDStatus] = useState<TaskStatus>("todo");
  const [dPriority, setDPriority] = useState<Priority>("medium");
  const [dAssigneeName, setDAssigneeName] = useState("");
  const [dDue, setDDue] = useState("");
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const blockedTasks = useMemo(() => tasks.filter((t) => t.status === "blocked"), [tasks]);

  const openTaskDialog = (task: Task) => {
    setDialogTask(task);
    setDTitle(task.title);
    setDDescription(task.description ?? "");
    setDStatus(task.status);
    setDPriority(task.priority);
    setDAssigneeName(task.assignee?.name ?? "");
    setDDue(task.dueDate ? task.dueDate.toISOString().slice(0, 10) : "");
    setDialogOpen(true);
  };

  const saveTaskDetail = () => {
    if (!dialogTask || !dTitle.trim()) return;
    updateMutation.mutate(
      {
        taskId: dialogTask.id,
        data: {
          title: dTitle.trim(),
          description: dDescription.trim() || "",
          status: dStatus,
          priority: dPriority,
          assignee_name: dAssigneeName.trim() || null,
          due_date: dDue.trim() ? `${dDue.trim()}T00:00:00.000Z` : null,
        },
      },
      {
        onSuccess: () => {
          setDialogOpen(false);
          setDialogTask(null);
          toast.success("Task updated");
        },
        onError: () => toast.error("Failed to update task"),
      },
    );
  };

  const onStart = (e: DragStartEvent) => setActiveId(String(e.active.id));
  const onEnd = (e: DragEndEvent) => {
    setActiveId(null);
    const overId = e.over?.id;
    if (!overId) return;
    const validStatuses = new Set(BOARD_COLUMNS);
    const overStatus: TaskStatus | null = validStatuses.has(overId as TaskStatus)
      ? (overId as TaskStatus)
      : (tasks.find((t) => t.id === overId && t.status !== "blocked")?.status ?? null);
    if (!overStatus || overStatus === "blocked") return;
    const taskId = String(e.active.id);
    const task = tasks.find((t) => t.id === taskId);
    if (!task || task.status === overStatus) return;
    moveMutation.mutate(
      { taskId, status: overStatus },
      { onError: () => toast.error("Failed to move task") },
    );
  };

  const toastAutomationResult = (res: {
    message?: string;
    result?: {
      meetings?: number;
      created?: number;
      updated?: number;
      review_required?: number;
      deleted?: number;
    };
  }) => {
    const r = res.result;
    if (r && (r.created != null || r.updated != null || r.meetings != null)) {
      const meetingsCount = r.meetings ?? 0;
      const created = r.created ?? 0;
      const updated = r.updated ?? 0;
      const review = r.review_required ?? 0;
      const deleted = r.deleted ?? 0;
      const parts = [`Created ${created}, updated ${updated} from ${meetingsCount} meeting(s)`];
      if (review > 0) parts.push(`${review} pending review`);
      if (deleted > 0) parts.push(`${deleted} removed`);
      toast.success(parts.join(" · "));
    } else {
      toast.success(res.message || "Board automation complete");
    }
  };

  const extract = () => {
    extractMutation.mutate(undefined, {
      onSuccess: toastAutomationResult,
      onError: () => toast.error("Extraction failed"),
    });
  };

  const syncBoard = () => {
    rebuildMutation.mutate(undefined, {
      onSuccess: toastAutomationResult,
      onError: () => toast.error("Board sync failed"),
    });
  };

  const activeTask = tasks.find((t) => t.id === activeId);
  const displayDescription = useMemo(() => {
    if (!dialogTask) return null;
    return taskDescriptionForDisplay(
      dDescription,
      Boolean(dialogTask.aiGenerated),
      dialogTask.descriptionUserSet,
    );
  }, [dialogTask, dDescription]);

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading board…</p>;

  return (
    <div>
      {showExtract && <KanbanReviewQueue workspaceId={workspaceId} />}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          Drag cards between columns. Automation uses transcript RAG + workspace docs to extract and move tasks.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="rounded-xl border-destructive/40 text-destructive hover:bg-destructive/10"
            onClick={() => setBlockersOpen(true)}
          >
            <Ban size={14} />
            Blockers
            <Badge variant="secondary" className="ml-1 h-5 min-w-5 rounded-full px-1.5 text-[10px]">
              {blockedTasks.length}
            </Badge>
          </Button>
          {showExtract && (
            <>
              <Button
                size="sm"
                variant="outline"
                className="rounded-xl"
                onClick={syncBoard}
                disabled={rebuildMutation.isPending || extractMutation.isPending}
              >
                {rebuildMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <RefreshCw size={14} />
                )}
                {rebuildMutation.isPending ? "Syncing…" : "Automate board"}
              </Button>
              <Button
                size="sm"
                className="gradient-primary rounded-xl"
                onClick={extract}
                disabled={extractMutation.isPending || rebuildMutation.isPending}
              >
                {extractMutation.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Sparkles size={14} />
                )}
                {extractMutation.isPending ? "Extracting…" : "Extract from meetings"}
              </Button>
            </>
          )}
        </div>
      </div>
      <DndContext sensors={sensors} collisionDetection={closestCorners} onDragStart={onStart} onDragEnd={onEnd}>
        <div className="flex gap-4 overflow-x-auto pb-4">
          {BOARD_COLUMNS.map((s) => (
            <Column
              key={s}
              status={s}
              tasks={tasks.filter((t) => t.status === s)}
              workspaceId={workspaceId}
              onOpenTask={openTaskDialog}
            />
          ))}
        </div>
        <DragOverlay>{activeTask && <TaskCard task={activeTask} />}</DragOverlay>
      </DndContext>

      <Dialog open={blockersOpen} onOpenChange={setBlockersOpen}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>Blockers</DialogTitle>
            <DialogDescription>
              {blockedTasks.length === 0
                ? "No blocked tasks right now."
                : `${blockedTasks.length} blocked task${blockedTasks.length === 1 ? "" : "s"}. Click one to edit or unblock.`}
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 space-y-2 overflow-y-auto py-2">
            {blockedTasks.map((t) => (
              <button
                key={t.id}
                type="button"
                className="w-full text-left rounded-xl border border-destructive/20 bg-destructive/5 p-3 hover:bg-destructive/10 transition-colors"
                onClick={() => {
                  setBlockersOpen(false);
                  openTaskDialog(t);
                }}
              >
                <div className="flex items-start gap-2">
                  <Ban className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold truncate">{t.title}</div>
                    {t.assignee?.name && (
                      <div className="mt-0.5 text-xs text-muted-foreground">{t.assignee.name}</div>
                    )}
                    {t.description && (
                      <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{t.description}</p>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBlockersOpen(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Task details</DialogTitle>
            <DialogDescription>Edit title, status, assignee, and due date.</DialogDescription>
          </DialogHeader>
          {dialogTask && (
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="task-title">Title</Label>
                <Input id="task-title" value={dTitle} onChange={(e) => setDTitle(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="task-desc">Description</Label>
                <Textarea
                  id="task-desc"
                  value={dDescription}
                  onChange={(e) => setDDescription(e.target.value)}
                  placeholder={displayDescription ? undefined : "Auto-generated descriptions are hidden until you add text."}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select value={dStatus} onValueChange={(v) => setDStatus(v as TaskStatus)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {STATUS_ORDER.map((s) => (
                        <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Priority</Label>
                  <Select value={dPriority} onValueChange={(v) => setDPriority(v as Priority)}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {PRIORITIES.map((p) => (
                        <SelectItem key={p} value={p}>{p}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="assignee">Assignee</Label>
                  <Input
                    id="assignee"
                    value={dAssigneeName}
                    onChange={(e) => setDAssigneeName(e.target.value)}
                    placeholder="Name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="due">Due date</Label>
                  <Input id="due" type="date" value={dDue} onChange={(e) => setDDue(e.target.value)} />
                </div>
              </div>
              {dialogTask.aiGenerated && dialogTask.sourceMeetingId && (
                <SourceMeetingLink workspaceId={workspaceId} meetingId={dialogTask.sourceMeetingId} />
              )}
              {gitEnabled && dialogTask.taskKey && (
                <TaskGitReference
                  variant="dialog"
                  taskKey={dialogTask.taskKey}
                  gitEvidence={dialogTask.gitEvidenceLog}
                  githubCiConclusion={dialogTask.githubCi?.conclusion}
                  githubCiUpdatedAt={dialogTask.githubCi?.updatedAt}
                  githubCiWorkflowUrl={dialogTask.githubCi?.workflowUrl}
                  githubCiHeadSha={dialogTask.githubCi?.headSha}
                  commitTitle={dialogTask.title}
                />
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={saveTaskDetail} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
