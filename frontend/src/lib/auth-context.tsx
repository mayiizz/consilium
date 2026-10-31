import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Role } from "./types";
import {
  fetchMe,
  loadStoredUser,
  loginApi,
  logoutApi,
  registerApi,
  storeUser,
  type AuthUser,
} from "./api/services/auth";

export type { AuthUser };

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (data: Omit<AuthUser, "id"> & { password: string }) => Promise<AuthUser>;
  logout: () => void;
  updateUser: (patch: Partial<AuthUser>) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const stored = loadStoredUser();
      if (stored) setUser(stored);
      const me = await fetchMe();
      if (me) setUser(me);
      setIsLoading(false);
    })();
  }, []);

  const persist = (u: AuthUser | null) => {
    setUser(u);
    storeUser(u);
  };

  const login: AuthContextValue["login"] = async (email, password) => {
    const u = await loginApi(email, password);
    persist(u);
    return u;
  };

  const register: AuthContextValue["register"] = async (data) => {
    const u = await registerApi(data);
    persist(u);
    return u;
  };

  const logout = () => {
    logoutApi().finally(() => persist(null));
  };

  const updateUser = (patch: Partial<AuthUser>) => {
    if (!user) return;
    persist({ ...user, ...patch });
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
