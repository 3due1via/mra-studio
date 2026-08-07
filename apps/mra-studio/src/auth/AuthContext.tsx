import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import * as authApi from "../services/authApi";
import type { User } from "../types/auth";
import { setUnauthorizedHandler } from "./authEvents";

type AuthState = { user: User | null; loading: boolean; login(email: string, password: string): Promise<void>; logout(): Promise<void> };
const Context = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient(); const navigate = useNavigate(); const location = useLocation();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const clearIdentity = useCallback(() => { queryClient.clear(); setUser(null); }, [queryClient]);
  useEffect(() => {
    setUnauthorizedHandler(() => { clearIdentity(); if (location.pathname !== "/login") navigate("/login", { replace: true }); });
    return () => setUnauthorizedHandler(null);
  }, [clearIdentity, location.pathname, navigate]);
  useEffect(() => { authApi.currentUser().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false)); }, []);
  const value = useMemo<AuthState>(() => ({
    user, loading,
    login: async (email, password) => { clearIdentity(); const result = await authApi.login(email, password); setUser(result.user); },
    logout: async () => { try { await authApi.logout(); } finally { clearIdentity(); navigate("/login", { replace: true }); } },
  }), [user, loading, clearIdentity, navigate]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
