import { Copy, ExternalLink, Github } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface TaskGitEvidenceEntry {
  source?: string;
  event?: string;
  sha?: string;
  url?: string;
  actor?: string;
  message?: string;
  at?: string;
}

interface TaskGitReferenceProps {
  taskKey?: string | null;
  gitEvidence?: TaskGitEvidenceEntry[] | null;
  variant: "card" | "dialog";
  commitTitle?: string;
  githubCiConclusion?: string | null;
  githubCiUpdatedAt?: string | null;
  githubCiWorkflowUrl?: string | null;
  githubCiHeadSha?: string | null;
}

function ciBadgeClass(conclusion: string): string {
  const c = conclusion.toLowerCase();
  if (c === "success" || c === "passed")
    return "bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-200/80";
  if (c === "failure" || c === "failed")
    return "bg-destructive/15 text-destructive dark:bg-destructive/25 border-destructive/30";
  if (c === "cancelled" || c === "skipped")
    return "bg-muted text-muted-foreground border-border";
  return "bg-amber-100 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200 border-amber-200/60";
}

export function TaskGitReference({
  taskKey,
  gitEvidence,
  variant,
  commitTitle = "",
  githubCiConclusion,
  githubCiUpdatedAt,
  githubCiWorkflowUrl,
  githubCiHeadSha,
}: TaskGitReferenceProps) {
  const key = (taskKey || "").trim();
  const ci = (githubCiConclusion || "").trim().toLowerCase();
  const hasCi = Boolean(ci);
  const ciTime =
    githubCiUpdatedAt && !Number.isNaN(Date.parse(githubCiUpdatedAt))
      ? formatDistanceToNow(new Date(githubCiUpdatedAt), { addSuffix: true })
      : null;

  const copyText = (text: string) => {
    void navigator.clipboard.writeText(text);
  };

  if (variant === "card") {
    if (!key && !hasCi) return null;
    return (
      <div
        className="mt-1.5 space-y-1 border-t border-border/60 pt-1"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        {key ? (
          <div className="flex items-center gap-1">
            <Github className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden />
            <code className="min-w-0 flex-1 truncate font-mono text-[10px]">{key}</code>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-6 w-6 shrink-0 p-0"
              onClick={(e) => {
                e.stopPropagation();
                copyText(key);
              }}
              aria-label="Copy task key"
            >
              <Copy className="h-3 w-3" />
            </Button>
          </div>
        ) : null}
        {hasCi ? (
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className={cn("px-1.5 py-0 text-[10px] font-normal", ciBadgeClass(ci))}>
              CI: {githubCiConclusion}
            </Badge>
            {ciTime ? <span className="text-[10px] text-muted-foreground">{ciTime}</span> : null}
            {githubCiWorkflowUrl ? (
              <a
                href={githubCiWorkflowUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex shrink-0 items-center gap-0.5 text-[10px] text-primary"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="h-2.5 w-2.5" />
                Run
              </a>
            ) : null}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-2 rounded-md border bg-muted/40 px-3 py-2">
      <p className="flex items-center gap-1.5 text-xs font-medium text-foreground">
        <Github className="h-3.5 w-3.5" aria-hidden />
        Git integration
      </p>
      {key ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <code className="rounded border bg-background px-2 py-1 font-mono text-xs">{key}</code>
            <Button type="button" variant="secondary" size="sm" className="h-7 text-xs" onClick={() => copyText(key)}>
              Copy key
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => {
                const line = `${key}: ${commitTitle.trim()}`.trim();
                copyText(line);
              }}
            >
              Copy for commit
            </Button>
          </div>
          <p className="text-xs leading-relaxed text-muted-foreground">
            Put this key in a merged pull request title or description. With CI gating enabled, Done requires
            workflow_run success for that PR.
          </p>
        </>
      ) : (
        <p className="text-xs text-muted-foreground">Task key appears after board sync from meetings.</p>
      )}
      {gitEvidence && gitEvidence.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-foreground">Recent Git activity</p>
          <ul className="max-h-28 space-y-1 overflow-y-auto rounded-md border bg-background/50 p-2 text-xs">
            {[...gitEvidence].reverse().slice(0, 5).map((ev, i) => (
              <li key={i} className="break-words text-muted-foreground">
                {ev.url ? (
                  <a href={ev.url} target="_blank" rel="noreferrer" className="text-primary underline">
                    Link
                  </a>
                ) : null}
                {ev.url ? " · " : null}
                {ev.message || ev.event || "event"}
                {ev.actor ? ` — ${ev.actor}` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
