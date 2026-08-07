import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [error, setError] = useState(""); const [pending, setPending] = useState(false);
  if (user) return <Navigate to="/dashboard" replace />;
  const submit = async (event: FormEvent) => { event.preventDefault(); setPending(true); setError(""); try { await login(email, password); navigate((location.state as { from?: string } | null)?.from ?? "/dashboard", { replace: true }); } catch (reason) { setError(reason instanceof Error ? reason.message : "Accesso non riuscito."); } finally { setPending(false); } };
  return <main className="auth-page"><form className="auth-card" onSubmit={submit}><h1>MRA Studio</h1><p>Accedi al workspace</p><label>Email<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required /></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>{error && <p className="auth-error" role="alert">{error}</p>}<button type="submit" disabled={pending}>{pending ? "Accesso…" : "Accedi"}</button></form></main>;
}
