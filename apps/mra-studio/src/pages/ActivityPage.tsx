import { useEffect, useState } from "react";
import { ApiError } from "../services/apiClient";
import { getAuditEvent, listAuditEvents } from "../services/auditApi";
import type { AuditEvent, AuditFilters } from "../types/audit";
import { useSearchParams } from "react-router-dom";

export const auditActionLabels: Record<string, string> = {
  "auth.login.succeeded": "Accesso riuscito", "auth.login.failed": "Accesso non riuscito", "auth.account.locked": "Account bloccato",
  "auth.logout.succeeded": "Disconnessione",
  "user.created": "Utente creato", "user.updated": "Utente modificato", "user.role.changed": "Ruolo modificato", "user.activated": "Utente attivato",
  "user.deactivated": "Utente disattivato", "user.password.changed": "Password utente modificata", "user.sessions.revoked": "Sessioni utente revocate",
  "knowledge_card.created": "Scheda creata", "knowledge_card.updated": "Scheda modificata", "knowledge_card.deleted": "Scheda eliminata",
  "knowledge_revision.restored": "Revisione ripristinata", "knowledge_relation.created": "Relazione creata", "knowledge_relation.deleted": "Relazione eliminata",
  "project.created": "Progetto creato", "project.updated": "Progetto modificato", "project.deleted": "Progetto eliminato",
  "environment.created": "Ambiente creato", "environment.updated": "Ambiente modificato", "environment.deleted": "Ambiente eliminato",
  "mra_object.created": "Oggetto MRA creato", "mra_object.updated": "Oggetto MRA modificato", "mra_object.deleted": "Oggetto MRA eliminato",
  "intervention.created": "Intervento creato", "intervention.updated": "Intervento modificato", "intervention.assigned": "Intervento assegnato",
  "intervention.status.changed": "Stato intervento modificato", "intervention.reopened": "Intervento riaperto", "intervention.cancelled": "Intervento annullato",
  "intervention.knowledge.linked": "Knowledge collegata all'intervento", "intervention.knowledge.unlinked": "Knowledge scollegata dall'intervento",
  "operation.failed": "Operazione non riuscita",
};
const actionLabel = (action: string) => auditActionLabels[action] ?? "Evento non riconosciuto";

export function ActivityPage() {
  const [searchParams] = useSearchParams();
  const initialFilters: AuditFilters = { entity_type: searchParams.get("entity_type") || undefined, entity_id: searchParams.get("entity_id") || undefined };
  const [filters, setFilters] = useState<AuditFilters>(initialFilters); const [draft, setDraft] = useState<AuditFilters>(initialFilters);
  const [items, setItems] = useState<AuditEvent[]>([]); const [cursor, setCursor] = useState<string | null>(null); const [selected, setSelected] = useState<AuditEvent | null>(null);
  const [loading, setLoading] = useState(true); const [loadingMore, setLoadingMore] = useState(false); const [error, setError] = useState("");
  const load = async (next?: string) => { next ? setLoadingMore(true) : setLoading(true); setError(""); try { const page = await listAuditEvents(filters, next); setItems((old) => next ? [...old, ...page.items] : page.items); setCursor(page.next_cursor); } catch (reason) { setError(reason instanceof Error ? reason.message : "Impossibile caricare le attività."); } finally { setLoading(false); setLoadingMore(false); } };
  useEffect(() => { void load(); }, [filters]);
  const open = async (id: string) => { setError(""); try { setSelected(await getAuditEvent(id)); } catch (reason) { setError(reason instanceof ApiError && reason.status === 404 ? "Evento non più disponibile." : "Impossibile caricare il dettaglio."); } };
  return <section className="page"><header className="page-header"><div><p className="eyebrow">AMMINISTRAZIONE</p><h1>Registro attività</h1></div></header>
    <form className="audit-filters" onSubmit={(event) => { event.preventDefault(); setFilters(draft); }}><input aria-label="Azione" placeholder="Azione" value={draft.action ?? ""} onChange={(e) => setDraft({ ...draft, action: e.target.value })}/><input aria-label="Tipo entità" placeholder="Tipo entità" value={draft.entity_type ?? ""} onChange={(e) => setDraft({ ...draft, entity_type: e.target.value })}/><select aria-label="Esito" value={draft.outcome ?? ""} onChange={(e) => setDraft({ ...draft, outcome: e.target.value as AuditFilters["outcome"] })}><option value="">Tutti gli esiti</option><option value="success">Successo</option><option value="failure">Errore</option></select><button type="submit">Filtra</button><button type="button" onClick={() => { setDraft({}); setFilters({}); }}>Azzera</button></form>
    {loading && <p>Caricamento attività…</p>}{error && <p className="auth-error" role="alert">{error}</p>}{!loading && !error && items.length === 0 && <p>Nessun risultato.</p>}
    {items.length > 0 && <div className="audit-table"><table><thead><tr><th>Quando</th><th>Attore</th><th>Azione</th><th>Entità</th><th>Esito</th></tr></thead><tbody>{items.map((item) => <tr key={item.id} onClick={() => void open(item.id)}><td>{new Date(item.occurred_at).toLocaleString()}</td><td>{item.actor_email_snapshot ?? "evento anonimo"}</td><td>{actionLabel(item.action)}</td><td>{item.entity_type} {item.entity_id ?? ""}{item.action.endsWith(".deleted") ? " · Entità eliminata" : ""}</td><td>{item.outcome}</td></tr>)}</tbody></table></div>}
    {cursor && <button disabled={loadingMore} onClick={() => void load(cursor)}>{loadingMore ? "Caricamento…" : "Pagina successiva"}</button>}
    {selected && <aside className="editor-card"><button onClick={() => setSelected(null)}>Chiudi</button><h2>{actionLabel(selected.action)}</h2><p>{selected.actor_email_snapshot ?? "evento anonimo"}</p><p>Campi: {selected.changed_fields.join(", ") || "nessuno"}</p><pre>{JSON.stringify(selected.changes, null, 2)}</pre><small>Request ID: {selected.request_id}</small><details><summary>Dettaglio tecnico</summary><code>{selected.action}</code></details>{typeof selected.metadata_json.code === "string" && <p>Codice: {selected.metadata_json.code}</p>}</aside>}
  </section>;
}
