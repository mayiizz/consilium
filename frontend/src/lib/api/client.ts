/** TanStack Start + Nitro dev server does not use Vite's server.proxy — call the API directly in dev. */
export const API_BASE =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000/api" : "/api");

const ACCESS_KEY = "consilium.auth.token";
const REFRESH_KEY = "consilium.auth.refresh";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Turn FastAPI error payloads into a short user-facing string. */
export function formatApiError(err: unknown, fallback: string): string {
  let msg: string | null = null;
  if (err instanceof ApiError) {
    const raw = err.detail ?? err.message;
    msg = formatApiDetail(raw) ?? (typeof raw === "string" ? raw : null);
  } else if (err instanceof Error && err.message) {
    msg = err.message;
  }
  return msg?.trim() || fallback;
}

function formatApiDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((item) => {
        if (typeof item === "object" && item && "msg" in item) {
          const loc = "loc" in item && Array.isArray(item.loc) ? item.loc.at(-1) : null;
          const field = typeof loc === "string" ? `${loc}: ` : "";
          return `${field}${String(item.msg)}`;
        }
        return null;
      })
      .filter(Boolean);
    if (msgs.length) return msgs.join(". ");
  }
  return null;
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) {
          clearTokens();
          return null;
        }
        const data = await res.json();
        setTokens(data.access_token, data.refresh_token);
        return data.access_token as string;
      } catch {
        clearTokens();
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  // Browser must set multipart boundary for FormData — never force JSON Content-Type.
  if (options.body && !headers["Content-Type"] && !isFormData) {
    headers["Content-Type"] = "application/json";
  }
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  const isAuthCredentialRequest =
    path === "/auth/login" ||
    path === "/auth/register" ||
    path.endsWith("/auth/login") ||
    path.endsWith("/auth/register");

  if (res.status === 401 && retry && !isAuthCredentialRequest) {
    const newToken = await refreshAccessToken();
    if (newToken) return apiFetch<T>(path, options, false);
    throw new ApiError("Unauthorized", 401);
  }

  if (!res.ok) {
    let detail: unknown;
    try {
      const err = await res.json();
      detail = err.detail ?? err.error ?? err;
    } catch {
      detail = res.statusText;
    }
    const parsed =
      typeof detail === "string" ? detail : formatApiDetail(detail);
    const message =
      parsed?.trim() ||
      (res.status === 404
        ? "Cannot reach the API. Make sure the backend is running on port 8000."
        : res.status >= 500
          ? "Server error. Please try again."
          : "Request failed");
    throw new ApiError(message, res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

export function getWsUrl(meetingId: string): string {
  const token = getAccessToken();
  const base = import.meta.env.VITE_WS_URL ?? `ws://${typeof window !== "undefined" ? window.location.hostname : "localhost"}:8000`;
  return `${base}/ws/meetings/${meetingId}?token=${token ?? ""}`;
}
