import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) return <main className="auth-page"><p>Verifica sessione…</p></main>;
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}

export function AdminRoute() {
  const { user } = useAuth();
  return user?.role === "admin" ? <Outlet /> : <Navigate to="/forbidden" replace />;
}

export const canEditInterventions = (role: "admin" | "editor" | "viewer" | null | undefined) => role === "editor" || role === "admin";

export function EditorRoute() {
  const { user } = useAuth();
  return canEditInterventions(user?.role) ? <Outlet /> : <Navigate to="/interventions" replace />;
}
