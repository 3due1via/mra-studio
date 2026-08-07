import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { createUser, listUsers, revokeSessions, updateUser } from "../services/authApi";
import type { Role } from "../types/auth";
import { ApiError } from "../services/apiClient";

export function UsersPage() {
  const [error, setError] = useState("");
  const client = useQueryClient(); const query = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const refresh = () => client.invalidateQueries({ queryKey: ["users"] });
  const showError = (reason: unknown) => setError(reason instanceof ApiError && reason.status === 403 ? "Non hai i permessi necessari." : reason instanceof Error ? reason.message : "Operazione non riuscita.");
  const create = useMutation({ mutationFn: () => createUser({ email: prompt("Email") ?? "", display_name: prompt("Nome") ?? "", password: prompt("Password temporanea (min. 12 caratteri)") ?? "", role: (prompt("Ruolo: admin, editor o viewer", "viewer") ?? "viewer") as Role }), onSuccess: refresh, onError: showError });
  const toggle = useMutation({ mutationFn: ({ id, active }: { id: string; active: boolean }) => updateUser(id, { is_active: active }), onSuccess: refresh, onError: showError });
  const revoke = useMutation({ mutationFn: revokeSessions, onError: showError });
  const changeRole = async (id: string, role: Role) => { setError(""); try { await updateUser(id, { role }); await refresh(); } catch (reason) { showError(reason); } };
  return <section className="page"><header className="page-header"><div><p className="eyebrow">AMMINISTRAZIONE</p><h1>Utenti e permessi</h1></div><button onClick={() => create.mutate()}>Nuovo utente</button></header>{query.isLoading && <p>Caricamento utenti…</p>}{query.error && <p className="auth-error">{query.error.message}</p>}{error && <p className="auth-error" role="alert">{error}</p>}{query.data?.length === 0 && <p>Nessun utente.</p>}<div className="user-grid">{query.data?.map((user) => <article className="editor-card" key={user.id}><h3>{user.display_name}</h3><p>{user.email}</p><label>Ruolo<select value={user.role} onChange={(event) => void changeRole(user.id, event.target.value as Role)}><option value="admin">admin</option><option value="editor">editor</option><option value="viewer">viewer</option></select></label><p>{user.is_active ? "attivo" : "disabilitato"}</p><div className="row-actions"><button onClick={() => toggle.mutate({ id: user.id, active: !user.is_active })}>{user.is_active ? "Disabilita" : "Riattiva"}</button><button onClick={() => revoke.mutate(user.id)}>Revoca sessioni</button></div></article>)}</div></section>;
}
