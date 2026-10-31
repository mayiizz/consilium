import type { RoadmapPhase } from "@/lib/types";

const SPRINT_PHASES: Record<
  string,
  { name: string; subtitle: string; milestones?: Record<string, string> }
> = {
  p1: {
    name: "Foundation & API contracts",
    subtitle: "Day 1 — architecture alignment, DB schemas, CI/CD, Next.js shell",
    milestones: {
      "To Do": "Scaffold & tooling",
      "In Progress": "API contracts",
      Done: "Shipped foundations",
    },
  },
  p2: {
    name: "Core integration",
    subtitle: "Day 2 — auth, analytics API, ML pipeline wiring, frontend tables",
    milestones: {
      "To Do": "Backlog",
      "In Progress": "Live integration",
      "In Review": "PR review",
    },
  },
  p3: {
    name: "Performance & polish",
    subtitle: "Day 3 — Redis cache, skeleton loaders, load-test fixes",
    milestones: {
      Blockers: "Active blockers",
      "To Do": "Polish queue",
    },
  },
  p4: {
    name: "Stakeholder demo",
    subtitle: "Days 4–5 — feature freeze, rehearsal, external demo",
    milestones: {
      "To Do": "Demo prep",
    },
  },
};

export function enrichRoadmapPhases(phases: RoadmapPhase[]): EnrichedRoadmapPhase[] {
  if (phases.length === 0) {
    return [
      {
        id: "p1",
        name: "Foundation & API contracts",
        status: "done",
        q: "Week 1",
        progress: 100,
        milestones: [{ name: "Architecture kickoff", status: "done", taskCount: 3 }],
      },
      {
        id: "p2",
        name: "Core integration",
        status: "active",
        q: "Week 1",
        progress: 68,
        milestones: [
          { name: "ML pipeline", status: "active", taskCount: 2 },
          { name: "Dashboard tables", status: "active", taskCount: 1 },
        ],
      },
      {
        id: "p3",
        name: "Performance & polish",
        status: "planned",
        q: "Week 1",
        progress: 35,
        milestones: [{ name: "Redis + skeleton UI", status: "planned", taskCount: 3 }],
      },
      {
        id: "p4",
        name: "Stakeholder demo",
        status: "planned",
        q: "Week 1",
        progress: 10,
        milestones: [{ name: "Demo rehearsal", status: "planned", taskCount: 2 }],
      },
    ];
  }

  return phases.map((p, index) => {
    const meta = SPRINT_PHASES[p.id] ?? {
      name: p.name,
      subtitle: "",
    };
    const fallbackId = `p${index + 1}`;
    const resolved = SPRINT_PHASES[p.id] ?? SPRINT_PHASES[fallbackId];

    return {
      ...p,
      name: resolved?.name ?? p.name,
      q: index < 3 ? `Day ${index + 1}` : "Day 4–5",
      milestones: p.milestones.map((m) => ({
        ...m,
        name: resolved?.milestones?.[m.name] ?? m.name.replace(/_/g, " "),
      })),
      subtitle: resolved?.subtitle ?? meta.subtitle,
    };
  });
}

export type EnrichedRoadmapPhase = RoadmapPhase & { subtitle?: string };

/** Prefer live API series; never invent fake sprint curves. */
export function buildBurndownSeries(
  apiBurndown: Array<{ week: string; planned: number; completed: number; remaining?: number }>,
  taskTotal: number,
  _taskDone: number,
) {
  if (!apiBurndown.length) {
    return [
      {
        week: "Now",
        planned: taskTotal,
        completed: 0,
        remaining: taskTotal,
      },
    ];
  }
  return apiBurndown.map((row) => ({
    ...row,
    remaining: row.remaining ?? Math.max(0, (row.planned ?? taskTotal) - row.completed),
  }));
}

export function buildVelocitySeries(
  apiVelocity: Array<{ week: string; completed: number }>,
  _taskDone: number,
) {
  return apiVelocity;
}
