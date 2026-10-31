import { Sparkles, GitPullRequest, CheckCircle2, AlertCircle, Clock, ArrowUpRight } from "lucide-react";
import { format, isBefore, startOfDay } from "date-fns";
import { Link } from "@tanstack/react-router";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { PRIORITY_COLOR } from "@/lib/constants";
import type { Task } from "@/lib/types";
import { TaskGitReference } from "@/components/tasks/TaskGitReference";
import { useWorkspaceGitEnabled } from "@/lib/workspace-context";

export function TaskCard({
  task,
  workspaceId,
  rolePrefix = "manager",
  onClick,
}: {
  task: Task;
  workspaceId?: string;
  rolePrefix?: "manager" | "member";
  onClick?: () => void;
}) {
  const gitEnabled = useWorkspaceGitEnabled(workspaceId);
  const ciIcon =
    task.githubRef?.ci === "passing" ? CheckCircle2 : task.githubRef?.ci === "failing" ? AlertCircle : Clock;
  const CiIcon = ciIcon;
  const overdue =
    !!task.dueDate && task.status !== "done" && isBefore(startOfDay(task.dueDate), startOfDay(new Date()));

  return (
    <div
      onClick={onClick}
      className="group cursor-pointer rounded-2xl border border-border/60 bg-card p-3.5 shadow-card transition-all hover:border-primary/40 hover:shadow-elevated"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="text-sm font-semibold leading-snug">{task.title}</div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          {task.aiGenerated && (
            <Badge
              variant="outline"
              className="gap-1 rounded-full border-primary/30 bg-primary/10 px-1.5 py-0 text-[10px] text-primary"
            >
              <Sparkles size={10} /> AI
            </Badge>
          )}
        </div>
      </div>

      {gitEnabled && task.githubRef && (
        <div className="mt-2 flex items-center gap-1.5 rounded-md bg-muted/60 px-2 py-1 text-[11px] text-muted-foreground">
          <GitPullRequest size={11} />
          <span className="font-mono">
            {task.githubRef.repo}#{task.githubRef.pr}
          </span>
          <CiIcon
            size={11}
            className={cn(
              task.githubRef.ci === "passing" && "text-success",
              task.githubRef.ci === "failing" && "text-destructive",
              task.githubRef.ci === "pending" && "text-warning",
            )}
          />
        </div>
      )}

      {gitEnabled ? (
        <TaskGitReference
          variant="card"
          taskKey={task.taskKey}
          gitEvidence={task.gitEvidenceLog}
          githubCiConclusion={task.githubCi?.conclusion}
          githubCiUpdatedAt={task.githubCi?.updatedAt}
          githubCiWorkflowUrl={task.githubCi?.workflowUrl}
          githubCiHeadSha={task.githubCi?.headSha}
          commitTitle={task.title}
        />
      ) : null}

      {task.aiGenerated && task.sourceMeetingId && workspaceId && (
        <Link
          to={`/business/${rolePrefix}/workspaces/$workspaceId/meeting/$meetingId`}
          params={{ workspaceId, meetingId: task.sourceMeetingId }}
          className="mt-2 flex items-center gap-1 text-[10px] text-primary hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          <ArrowUpRight size={10} />
          From meeting
        </Link>
      )}

      <div className="mt-3 flex items-center justify-between gap-2">
        <Badge className={cn("rounded-full border-0 px-2 py-0 text-[10px] capitalize", PRIORITY_COLOR[task.priority])}>
          {task.priority}
        </Badge>
        <div className="flex items-center gap-2">
          {task.dueDate && (
            <span
              className={cn(
                "inline-flex items-center gap-1 text-[11px]",
                overdue ? "font-semibold text-destructive" : "text-muted-foreground",
              )}
              title={
                task.dueDateSource === "transcript"
                  ? "Due date marked from meeting transcript"
                  : task.dueDateSource === "user"
                    ? "Manually set due date"
                    : "Due date"
              }
            >
              <Clock size={10} />
              {format(task.dueDate, "MMM d")}
              {task.dueDateSource === "transcript" && (
                <span className="rounded bg-primary/10 px-1 text-[9px] font-medium text-primary">AI</span>
              )}
            </span>
          )}
          {task.assignee && (
            <Avatar className="h-6 w-6 ring-2 ring-background">
              <AvatarImage src={task.assignee.avatar} />
              <AvatarFallback className="text-[10px]">{task.assignee.name[0]}</AvatarFallback>
            </Avatar>
          )}
        </div>
      </div>
    </div>
  );
}
