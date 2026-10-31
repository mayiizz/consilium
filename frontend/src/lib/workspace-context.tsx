import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import type { Role, Workspace } from "./types";
import * as workspaceApi from "./api/services/workspaces";
import { useAuth } from "./auth-context";

interface WorkspaceContextValue {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  isLoading: boolean;
  refreshWorkspaces: () => Promise<void>;
  setCurrentWorkspaceById: (id: string) => void;
  createWorkspace: (name: string, role: Role) => Promise<Workspace>;
  joinWorkspace: (code: string) => Promise<Workspace | null>;
  deleteWorkspace: (id: string) => Promise<void>;
  deleteAll: () => Promise<void>;
}

const Ctx = createContext<WorkspaceContextValue | null>(null);
const CURRENT_KEY = "consilium.workspace.current";

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshWorkspaces = useCallback(async () => {
    if (!user) {
      setWorkspaces([]);
      setIsLoading(false);
      return;
    }
    try {
      const list = await workspaceApi.listWorkspaces();
      setWorkspaces(list);
    } catch {
      setWorkspaces([]);
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refreshWorkspaces();
    const cur = typeof window !== "undefined" ? localStorage.getItem(CURRENT_KEY) : null;
    if (cur) setCurrentId(cur);
  }, [refreshWorkspaces]);

  const setCurrentWorkspaceById = useCallback((id: string) => {
    setCurrentId(id);
    if (typeof window !== "undefined") localStorage.setItem(CURRENT_KEY, id);
  }, []);

  const createWorkspace: WorkspaceContextValue["createWorkspace"] = async (name, role) => {
    const ws = await workspaceApi.createWorkspace(name);
    const withRole = { ...ws, role };
    setWorkspaces((prev) => [...prev, withRole]);
    setCurrentWorkspaceById(ws.id);
    return withRole;
  };

  const joinWorkspace: WorkspaceContextValue["joinWorkspace"] = async (code) => {
    try {
      const ws = await workspaceApi.joinWorkspace(code);
      setWorkspaces((prev) => {
        if (prev.some((w) => w.id === ws.id)) return prev;
        return [...prev, ws];
      });
      setCurrentWorkspaceById(ws.id);
      return ws;
    } catch {
      return null;
    }
  };

  const deleteWorkspace = async (id: string) => {
    await workspaceApi.deleteWorkspace(id);
    setWorkspaces((prev) => prev.filter((w) => w.id !== id));
    if (currentId === id) setCurrentId(null);
  };

  const deleteAll = async () => {
    await Promise.all(workspaces.map((w) => workspaceApi.deleteWorkspace(w.id)));
    setWorkspaces([]);
    setCurrentId(null);
  };

  const currentWorkspace = workspaces.find((w) => w.id === currentId) ?? workspaces[0] ?? null;

  return (
    <Ctx.Provider
      value={{
        workspaces,
        currentWorkspace,
        isLoading,
        refreshWorkspaces,
        setCurrentWorkspaceById,
        createWorkspace,
        joinWorkspace,
        deleteWorkspace,
        deleteAll,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}

/** GitHub task keys, copy-id, and PR/CI on Kanban when workspace Use Git is on. */
export function useWorkspaceGitEnabled(workspaceId?: string) {
  const { workspaces, currentWorkspace } = useWorkspace();
  const ws = (workspaceId && workspaces.find((w) => w.id === workspaceId)) || currentWorkspace;
  return ws?.gitEnabled !== false;
}
