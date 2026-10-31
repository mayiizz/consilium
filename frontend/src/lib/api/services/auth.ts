import { apiFetch, setTokens, clearTokens } from "../client";
import type { Role } from "../../types";
import { AVATAR_OPTIONS } from "../../constants";

const USER_KEY = "consilium.auth.user";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: Role | null;
  avatar: string;
  skills: string[];
}

export function loadStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function storeUser(user: AuthUser | null) {
  if (typeof window === "undefined") return;
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  else localStorage.removeItem(USER_KEY);
}

export async function registerApi(data: {
  name: string;
  email: string;
  password: string;
  role: Role;
  skills: string[];
  avatar: string;
}): Promise<AuthUser> {
  const tokens = await apiFetch<{ access_token: string; refresh_token: string }>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify({ name: data.name, email: data.email, password: data.password }),
    },
    false,
  );
  setTokens(tokens.access_token, tokens.refresh_token);
  const me = await apiFetch<Record<string, unknown>>("/auth/me");
  const user: AuthUser = {
    id: String(me.id),
    name: String(me.name),
    email: String(me.email),
    role: data.role,
    avatar: data.avatar || AVATAR_OPTIONS[0].url,
    skills: data.skills,
  };
  storeUser(user);
  return user;
}

export async function loginApi(email: string, password: string): Promise<AuthUser> {
  const tokens = await apiFetch<{ access_token: string; refresh_token: string }>(
    "/auth/login",
    {
      method: "POST",
      body: JSON.stringify({ email, password }),
    },
    false,
  );
  setTokens(tokens.access_token, tokens.refresh_token);
  const me = await apiFetch<Record<string, unknown>>("/auth/me");
  const stored = loadStoredUser();
  const user: AuthUser = {
    id: String(me.id),
    name: String(me.name),
    email: String(me.email),
    role: stored?.id === String(me.id) ? stored.role : null,
    avatar: String(me.avatar ?? stored?.avatar ?? AVATAR_OPTIONS[0].url),
    skills: (me.skills as string[]) ?? stored?.skills ?? [],
  };
  storeUser(user);
  return user;
}

export async function fetchMe(): Promise<AuthUser | null> {
  try {
    const me = await apiFetch<Record<string, unknown>>("/auth/me");
    const stored = loadStoredUser();
    const user: AuthUser = {
      id: String(me.id),
      name: String(me.name),
      email: String(me.email),
      role: stored?.role ?? null,
      avatar: String(me.avatar ?? stored?.avatar ?? AVATAR_OPTIONS[0].url),
      skills: (me.skills as string[]) ?? stored?.skills ?? [],
    };
    storeUser(user);
    return user;
  } catch {
    return null;
  }
}

export async function logoutApi() {
  const refresh = localStorage.getItem("consilium.auth.refresh");
  try {
    if (refresh) {
      await apiFetch("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refresh }),
      });
    }
  } finally {
    clearTokens();
    storeUser(null);
  }
}
