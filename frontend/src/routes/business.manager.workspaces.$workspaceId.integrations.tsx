import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Github, Copy, CheckCircle2, Webhook } from "lucide-react";
import { toast } from "sonner";
import {
  getGitHubStatus,
  connectGitHub,
  disconnectGitHub,
  getGitHubOAuthUrl,
  listGitHubRepos,
  selectGitHubRepo,
} from "@/lib/api/services/github";
import { updateWorkspace } from "@/lib/api/services/workspaces";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useWorkspace } from "@/lib/workspace-context";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/integrations")({
  component: Page,
});

function Page() {
  const { workspaceId } = Route.useParams();
  const qc = useQueryClient();
  const { workspaces, refreshWorkspaces } = useWorkspace();
  const workspace = workspaces.find((w) => w.id === workspaceId);
  const [repos, setRepos] = useState<Array<{ full_name: string }>>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  const [gitEnabled, setGitEnabled] = useState(true);
  const [requirePrMerge, setRequirePrMerge] = useState(true);
  const [requireCiPass, setRequireCiPass] = useState(false);
  const [pushMode, setPushMode] = useState(false);

  const { data: gh, isLoading } = useQuery({
    queryKey: ["github", workspaceId],
    queryFn: () => getGitHubStatus(workspaceId),
  });

  const connectMut = useMutation({
    mutationFn: (repo: string) => connectGitHub(workspaceId, repo),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["github", workspaceId] });
      toast.success("GitHub connected");
    },
  });

  const disconnectMut = useMutation({
    mutationFn: () => disconnectGitHub(workspaceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["github", workspaceId] });
      toast.success("Disconnected");
    },
  });

  const selectRepoMut = useMutation({
    mutationFn: (fullName: string) => {
      const [owner, name] = fullName.split("/");
      return selectGitHubRepo(workspaceId, owner, name);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["github", workspaceId] });
      toast.success("Repository linked");
    },
  });

  const settingsMut = useMutation({
    mutationFn: (next: {
      gitEnabled: boolean;
      requirePrMerge: boolean;
      requireCiPass: boolean;
      pushMode: boolean;
    }) =>
      updateWorkspace(workspaceId, {
        settings: {
          git_enabled: next.gitEnabled,
          require_pr_merge: next.requirePrMerge,
          require_ci_pass: next.requireCiPass,
          push_mode_enabled: next.pushMode,
        },
      }),
    onSuccess: async () => {
      await refreshWorkspaces();
      qc.invalidateQueries({ queryKey: ["github", workspaceId] });
      toast.success("Integration settings saved");
    },
  });

  useEffect(() => {
    if (!workspace) return;
    setGitEnabled(workspace.gitEnabled);
    setRequirePrMerge(workspace.requirePrMerge);
    setRequireCiPass(workspace.requireCiPass);
    setPushMode(workspace.pushModeEnabled);
  }, [workspace]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("github") === "connected") {
      toast.success("GitHub OAuth connected — select a repository");
      listGitHubRepos(workspaceId)
        .then((r) => {
          setRepos(r);
          if (r.length > 0) setSelectedRepo(r[0].full_name);
        })
        .catch(() => toast.error("Could not load repositories"));
    }
  }, [workspaceId]);

  const webhook = gh?.webhook_url ?? `${window.location.origin.replace(":3000", ":8000")}/github/webhook`;
  const connected = gh?.connected ?? false;
  const repo = gh?.repo ?? "";
  const oauthConfigured = gh?.oauth_configured ?? false;

  const startOAuth = () => {
    window.location.href = getGitHubOAuthUrl(workspaceId);
  };

  const loadRepos = async () => {
    try {
      const r = await listGitHubRepos(workspaceId);
      setRepos(r);
      if (r.length > 0) setSelectedRepo(r[0].full_name);
    } catch {
      toast.error("Connect GitHub first");
    }
  };

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader title="Integrations" description="Connect Consilium to where your team already works." />
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="glass-card p-6">
            <div className="flex items-start gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-foreground text-background">
                <Github size={22} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">GitHub</h3>
                  {connected && (
                    <Badge className="gap-1 border-success/30 bg-success/15 text-success">
                      <CheckCircle2 size={11} /> Connected
                    </Badge>
                  )}
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Optional. When on, Kanban shows copyable task keys for commits and PRs can move cards.
                  When off, the board has no Git IDs or GitHub status.
                </p>
                {gh?.github_user_login && (
                  <p className="mt-1 text-xs text-muted-foreground">Signed in as @{gh.github_user_login}</p>
                )}
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between rounded-xl border border-border/60 p-3">
                <div>
                  <Label>Use Git</Label>
                  <p className="text-xs text-muted-foreground">
                    Show task keys to copy on Kanban and apply GitHub PR/CI updates.
                  </p>
                </div>
                <Switch
                  checked={gitEnabled}
                  onCheckedChange={(v) => {
                    setGitEnabled(v);
                    settingsMut.mutate({
                      gitEnabled: v,
                      requirePrMerge,
                      requireCiPass,
                      pushMode,
                    });
                  }}
                />
              </div>
              {!gitEnabled ? (
                <p className="text-xs text-muted-foreground">
                  Git is off. Kanban will not show IDs to copy, PR links, or CI. Connect GitHub after you turn this on.
                </p>
              ) : (
                <>
              {oauthConfigured ? (
                <Button className="gradient-primary rounded-xl" onClick={startOAuth}>
                  Connect with GitHub
                </Button>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Set GITHUB_CLIENT_ID and GITHUB_REDIRECT_URI in backend .env for OAuth.
                </p>
              )}
              <Button variant="outline" className="rounded-xl" onClick={loadRepos} disabled={!connected}>
                Load repositories
              </Button>
              {repos.length > 0 && (
                <div className="space-y-1.5">
                  <Label>Repository</Label>
                  <Select value={selectedRepo} onValueChange={setSelectedRepo}>
                    <SelectTrigger className="rounded-xl">
                      <SelectValue placeholder="Select repo" />
                    </SelectTrigger>
                    <SelectContent>
                      {repos.map((r) => (
                        <SelectItem key={r.full_name} value={r.full_name}>
                          {r.full_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    className="rounded-xl"
                    onClick={() => selectedRepo && selectRepoMut.mutate(selectedRepo)}
                    disabled={selectRepoMut.isPending}
                  >
                    Save repository
                  </Button>
                </div>
              )}
              {repo && !repos.length && (
                <p className="text-sm text-muted-foreground">Linked repo: <code>{repo}</code></p>
              )}
              <div className="flex items-center justify-between rounded-xl border border-border/60 p-3">
                <div>
                  <Label>Require merged PR for Done</Label>
                  <p className="text-xs text-muted-foreground">Ignore push-only commits unless push mode is on.</p>
                </div>
                <Switch checked={requirePrMerge} onCheckedChange={setRequirePrMerge} />
              </div>
              <div className="flex items-center justify-between rounded-xl border border-border/60 p-3">
                <div>
                  <Label>Require CI pass</Label>
                  <p className="text-xs text-muted-foreground">Done only after workflow_run success.</p>
                </div>
                <Switch checked={requireCiPass} onCheckedChange={setRequireCiPass} />
              </div>
              <div className="flex items-center justify-between rounded-xl border border-border/60 p-3">
                <div>
                  <Label>Push mode</Label>
                  <p className="text-xs text-muted-foreground">Allow default-branch pushes with fix/closes keywords.</p>
                </div>
                <Switch checked={pushMode} onCheckedChange={setPushMode} />
              </div>
              <Button
                variant="secondary"
                className="rounded-xl"
                onClick={() =>
                  settingsMut.mutate({
                    gitEnabled,
                    requirePrMerge,
                    requireCiPass,
                    pushMode,
                  })
                }
              >
                Save validation settings
              </Button>
              {connected && (
                <Button
                  variant="outline"
                  className="rounded-xl"
                  onClick={() => disconnectMut.mutate()}
                  disabled={disconnectMut.isPending}
                >
                  Disconnect
                </Button>
              )}
                </>
              )}
            </div>
          </Card>

          {gitEnabled ? (
          <Card className="glass-card p-6">
            <div className="flex items-center gap-2">
              <Webhook size={18} />
              <h3 className="font-semibold">Webhook URL</h3>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Add this URL in GitHub → repo → Settings → Webhooks. Events: Pull requests, Workflow runs, Pushes
              (optional).
            </p>
            <div className="mt-3 flex gap-2">
              <code className="flex-1 truncate rounded-lg border bg-muted/50 p-2 text-xs">{webhook}</code>
              <Button
                size="icon"
                variant="outline"
                onClick={() => {
                  void navigator.clipboard.writeText(webhook);
                  toast.success("Copied");
                }}
              >
                <Copy size={14} />
              </Button>
            </div>
            {gh?.last_event && (
              <p className="mt-2 text-xs text-muted-foreground">Last event: {gh.last_event}</p>
            )}
          </Card>
          ) : null}
        </div>
      )}
    </DashboardLayout>
  );
}
