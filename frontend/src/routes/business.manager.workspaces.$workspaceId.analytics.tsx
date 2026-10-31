import { createFileRoute } from "@tanstack/react-router";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { STATUS_LABELS, STATUS_ORDER } from "@/lib/constants";
import { useAnalytics, useTeam } from "@/lib/api/hooks/useAnalytics";
import { useTasks } from "@/lib/api/hooks/useTasks";
import { useMeetings } from "@/lib/api/hooks/useMeetings";
import { Calendar, CheckCircle2, AlertTriangle, TrendingUp } from "lucide-react";

export const Route = createFileRoute("/business/manager/workspaces/$workspaceId/analytics")({ component: Page });

const COLORS = ["hsl(215 16% 47%)", "hsl(239 84% 67%)", "hsl(38 92% 50%)", "hsl(158 64% 42%)", "hsl(0 84% 60%)"];

function Page() {
  const { workspaceId } = Route.useParams();
  const { data: analytics, isLoading: loadingAnalytics } = useAnalytics(workspaceId);
  const { data: tasks = [], isLoading: loadingTasks } = useTasks(workspaceId);
  const { data: members = [] } = useTeam(workspaceId);
  const { data: meetings = [] } = useMeetings(workspaceId);

  const pieData = STATUS_ORDER.map((s) => ({
    name: STATUS_LABELS[s],
    value: tasks.filter((t) => t.status === s).length,
  })).filter((d) => d.value > 0);

  const taskDone = tasks.filter((t) => t.status === "done").length;
  const taskBlocked = tasks.filter((t) => t.status === "blocked").length;
  const planned = analytics?.burndown?.[0]?.planned ?? tasks.length;
  const burndown = (analytics?.burndown ?? []).map((row) => ({
    ...row,
    remaining: row.remaining ?? Math.max(0, (row.planned ?? planned) - row.completed),
  }));
  const velocity = analytics?.velocity ?? [];
  const endedMeetings =
    analytics?.meeting_stats?.ended ?? meetings.filter((m) => m.status === "ended").length;
  const upcomingMeetings =
    analytics?.meeting_stats?.scheduled ?? meetings.filter((m) => m.status === "scheduled").length;
  const liveMeetings =
    analytics?.meeting_stats?.live ?? meetings.filter((m) => m.status === "live").length;
  const meetingTotal = analytics?.meeting_stats?.total ?? meetings.length;
  const meetingActivity = [
    { label: "Completed", count: endedMeetings },
    { label: "Upcoming", count: upcomingMeetings },
    { label: "Live", count: liveMeetings },
  ];

  const kpis = [
    { label: "Tasks completed", value: taskDone, icon: CheckCircle2, tone: "text-success" },
    {
      label: "In flight",
      value: Math.max(0, tasks.length - taskDone - taskBlocked),
      icon: TrendingUp,
      tone: "text-primary",
    },
    { label: "Blockers", value: taskBlocked, icon: AlertTriangle, tone: "text-destructive" },
    { label: "Meetings", value: meetingTotal, icon: Calendar, tone: "text-muted-foreground" },
  ];

  const loading = loadingAnalytics || loadingTasks;

  return (
    <DashboardLayout role="manager" workspaceId={workspaceId}>
      <PageHeader title="Analytics" description="Live velocity, burndown, and team throughput from your workspace data." />
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading analytics…</p>
      ) : (
        <>
          <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {kpis.map((k) => (
              <Card key={k.label} className="glass-card flex items-center gap-3 p-4">
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl bg-muted ${k.tone}`}>
                  <k.icon size={18} />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{k.label}</p>
                  <p className="text-2xl font-bold tabular-nums">{k.value}</p>
                </div>
              </Card>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="glass-card p-5">
              <h3 className="mb-4 font-semibold">Task distribution</h3>
              {pieData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={3}>
                        {pieData.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-1.5">
                    {pieData.map((d, i) => (
                      <div key={d.name} className="flex items-center gap-2 text-xs">
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                        <span className="flex-1">{d.name}</span>
                        <span className="font-semibold tabular-nums">{d.value}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No tasks yet — extract from meetings to populate.</p>
              )}
            </Card>

            <Card className="lg:col-span-2 glass-card p-5">
              <div className="mb-4 flex items-center justify-between gap-2">
                <h3 className="font-semibold">Sprint burndown</h3>
                <Badge variant="outline" className="rounded-full text-[10px]">
                  Last 14 days · scope {planned}
                </Badge>
              </div>
              {burndown.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={burndown}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" />
                    <XAxis dataKey="week" stroke="hsl(215 16% 47%)" fontSize={12} />
                    <YAxis stroke="hsl(215 16% 47%)" fontSize={12} allowDecimals={false} />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="planned"
                      name="Scope"
                      stroke="hsl(215 16% 47%)"
                      strokeDasharray="4 4"
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="completed"
                      name="Completed"
                      stroke="hsl(239 84% 67%)"
                      strokeWidth={3}
                      dot={{ r: 3 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="remaining"
                      name="Remaining"
                      stroke="hsl(38 92% 50%)"
                      strokeWidth={2}
                      dot={{ r: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-muted-foreground">No burndown data yet.</p>
              )}
            </Card>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card className="glass-card p-5">
              <h3 className="mb-4 font-semibold">Velocity (tasks completed / week)</h3>
              {velocity.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={velocity}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" />
                    <XAxis dataKey="week" fontSize={11} />
                    <YAxis fontSize={12} allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="completed" name="Completed" fill="hsl(239 84% 67%)" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-sm text-muted-foreground">No completed tasks yet.</p>
              )}
            </Card>

            <Card className="glass-card p-5">
              <h3 className="mb-4 font-semibold">Meeting activity</h3>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={meetingActivity}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" />
                  <XAxis dataKey="label" fontSize={12} />
                  <YAxis fontSize={12} allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" name="Meetings" fill="hsl(158 64% 42%)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <Card className="mt-6 glass-card p-5">
            <h3 className="mb-4 font-semibold">Per-member completion</h3>
            {members.length === 0 ? (
              <p className="text-sm text-muted-foreground">No team members yet.</p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {members.map((m) => {
                  const pct = m.tasksAssigned > 0 ? Math.round((m.tasksCompleted / m.tasksAssigned) * 100) : 0;
                  return (
                    <div key={m.id}>
                      <div className="mb-1.5 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Avatar className="h-6 w-6">
                            <AvatarImage src={m.avatar} />
                            <AvatarFallback>{m.name[0]}</AvatarFallback>
                          </Avatar>
                          <span className="text-sm font-medium">{m.name}</span>
                        </div>
                        <span className="text-xs text-muted-foreground tabular-nums">
                          {m.tasksCompleted}/{m.tasksAssigned} · {pct}%
                        </span>
                      </div>
                      <Progress value={pct} className="h-2" />
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </>
      )}
    </DashboardLayout>
  );
}
