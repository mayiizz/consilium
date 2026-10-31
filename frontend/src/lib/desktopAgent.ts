const DAEMON_BASE =
  import.meta.env.VITE_DAEMON_URL ?? "http://127.0.0.1:9477";

const WS_BASE =
  import.meta.env.VITE_WS_URL ??
  `ws://${typeof window !== "undefined" ? window.location.hostname : "localhost"}:8000`;

export interface DaemonHealth {
  ok: boolean;
  active: boolean;
  meetingId: string | null;
}

export interface StartAgentResult {
  ok: boolean;
  error?: string;
  alreadyActive?: boolean;
}

export async function checkDaemonHealth(): Promise<DaemonHealth | null> {
  try {
    const res = await fetch(`${DAEMON_BASE}/health`, { signal: AbortSignal.timeout(2000) });
    if (!res.ok) return null;
    return (await res.json()) as DaemonHealth;
  } catch {
    return null;
  }
}

export async function startDesktopAgent(meetingId: string, token: string): Promise<StartAgentResult> {
  try {
    const health = await checkDaemonHealth();
    if (!health?.ok) {
      return { ok: false, error: "Audio daemon is not running" };
    }
    if (health.active && health.meetingId === meetingId) {
      return { ok: true, alreadyActive: true };
    }

    const res = await fetch(`${DAEMON_BASE}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ meetingId, token, wsUrl: WS_BASE }),
      signal: AbortSignal.timeout(20000),
    });
    const data = (await res.json().catch(() => ({}))) as { ok?: boolean; error?: string; message?: string };
    if (res.ok && data.ok) {
      return { ok: true };
    }
    return { ok: false, error: data.error || data.message || `Daemon returned ${res.status}` };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not reach audio daemon";
    return { ok: false, error: message };
  }
}

export async function stopDesktopAgent(): Promise<void> {
  try {
    await fetch(`${DAEMON_BASE}/stop`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: AbortSignal.timeout(5000),
    });
  } catch {
    // Daemon may already be stopped
  }
}

export const DAEMON_START_CMD = "python -m desktop.daemon";
