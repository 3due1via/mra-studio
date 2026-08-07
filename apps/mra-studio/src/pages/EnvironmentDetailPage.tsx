import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Button } from "../components/Button";
import { createObject, deleteObject, getEnvironment, listObjects, updateObject } from "../services/projectsApi";
import type { MraObject, MraObjectInput } from "../types/projects";
import { useAuth } from "../auth/AuthContext";

const emptyObject: MraObjectInput = { category: "", name: "", brand: "", model: "", serial_number: "", description: "", status: "active", metadata_json: {} };

export function EnvironmentDetailPage() {
  const { user } = useAuth(); const canEdit = user?.role !== "viewer"; const canDelete = user?.role === "admin";
  const { environmentId = "" } = useParams();
  const client = useQueryClient();
  const [form, setForm] = useState<MraObjectInput>(emptyObject);
  const [metadataText, setMetadataText] = useState("{}");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const environment = useQuery({ queryKey: ["environment", environmentId], queryFn: () => getEnvironment(environmentId), enabled: Boolean(environmentId) });
  const objects = useQuery({ queryKey: ["environment-objects", environmentId], queryFn: () => listObjects(environmentId), enabled: Boolean(environmentId) });
  const save = useMutation({
    mutationFn: () => {
      const metadata = JSON.parse(metadataText) as Record<string, unknown>;
      if (Array.isArray(metadata) || metadata === null || typeof metadata !== "object") throw new Error("I metadati devono essere un oggetto JSON.");
      const payload = { ...form, metadata_json: metadata };
      return editingId ? updateObject(editingId, payload) : createObject(environmentId, payload);
    },
    onSuccess: async () => { await client.invalidateQueries({ queryKey: ["environment-objects", environmentId] }); setForm(emptyObject); setMetadataText("{}"); setEditingId(null); setShowForm(false); },
  });
  const remove = useMutation({ mutationFn: deleteObject, onSuccess: () => client.invalidateQueries({ queryKey: ["environment-objects", environmentId] }) });

  const edit = (item: MraObject) => {
    setForm({ category: item.category, name: item.name, brand: item.brand, model: item.model, serial_number: item.serial_number, description: item.description, status: item.status, metadata_json: item.metadata_json });
    setMetadataText(JSON.stringify(item.metadata_json, null, 2)); setEditingId(item.id); setShowForm(true);
  };

  if (environment.isLoading) return <section className="empty-state"><h2>Caricamento ambiente...</h2></section>;
  if (environment.isError) return <section className="empty-state error-box"><h2>Ambiente non disponibile</h2><p>{String(environment.error)}</p><Link to="/projects">Torna ai progetti</Link></section>;

  return <>
    <header className="project-hq-hero"><div className="project-hq-copy"><Link to={`/projects/${environment.data?.project_id}`}>← Torna al progetto</Link><span className="project-hq-kicker">AMBIENTE</span><h1>{environment.data?.name}</h1><p>{environment.data?.notes || "Nessuna nota inserita."}</p><div className="project-hq-tags"><b>{environment.data?.environment_type}</b><b>{environment.data?.area_m2 ? `${environment.data.area_m2} m²` : "Superficie non inserita"}</b><b>{environment.data?.width_m && environment.data?.length_m ? `${environment.data.width_m} × ${environment.data.length_m} m` : "Dimensioni da completare"}</b></div></div></header>
    {canEdit && <section className="project-hq-actions"><Button onClick={() => { setForm(emptyObject); setMetadataText("{}"); setEditingId(null); setShowForm(true); }}>+ Registra oggetto</Button></section>}
    {showForm ? <form className="inline-entity-form" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}><h2>{editingId ? "Modifica oggetto" : "Nuovo oggetto"}</h2><div className="project-form-grid">
      <label><span>Nome</span><input required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label><span>Categoria</span><input required minLength={2} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} /></label><label><span>Marca</span><input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} /></label><label><span>Modello</span><input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} /></label><label><span>Seriale</span><input value={form.serial_number} onChange={(e) => setForm({ ...form, serial_number: e.target.value })} /></label><label><span>Stato</span><select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as MraObjectInput["status"] })}>{["active", "maintenance", "inactive", "retired"].map((value) => <option key={value}>{value}</option>)}</select></label><label className="wide"><span>Descrizione</span><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label><label className="wide"><span>Metadati JSON</span><textarea value={metadataText} onChange={(e) => setMetadataText(e.target.value)} /></label>
    </div>{save.isError ? <div className="notice error">{String(save.error)}</div> : null}<div className="project-form-actions"><Button className="button-secondary" type="button" onClick={() => setShowForm(false)}>Annulla</Button><Button disabled={save.isPending}>Salva</Button></div></form> : null}
    <div className="section-heading"><div><span>ASSET REGISTRY</span><h2>Oggetti registrati</h2></div><small>{objects.data?.length ?? 0} oggetti</small></div>
    {objects.isLoading ? <section className="empty-state"><h2>Caricamento oggetti...</h2></section> : null}
    {objects.isError ? <section className="empty-state error-box"><h2>Errore oggetti</h2><p>{String(objects.error)}</p></section> : null}
    {remove.isError ? <section className="empty-state error-box"><h2>Eliminazione non riuscita</h2><p>{String(remove.error)}</p></section> : null}
    {!objects.isLoading && !objects.isError && objects.data?.length === 0 ? <section className="empty-state"><h2>Nessun oggetto registrato</h2><p>Aggiungi il primo asset tecnico dell'ambiente.</p></section> : null}
    <section className="project-card-grid">{(objects.data ?? []).map((item) => <article className="project-card" key={item.id}><div className="project-card-cover"><span>{item.category}</span><b>{item.status}</b></div><div className="project-card-content"><h2>{item.name}</h2><p>{item.description || "Nessuna descrizione."}</p><div className="project-meta"><span>{[item.brand, item.model].filter(Boolean).join(" · ") || "Marca e modello non inseriti"}</span><span>{item.serial_number || "Nessun seriale"}</span></div><div className="project-card-actions">{canEdit && <button type="button" onClick={() => edit(item)}>Modifica</button>}{canDelete && <button type="button" onClick={() => { if (window.confirm(`Eliminare ${item.name}?`)) remove.mutate(item.id); }}>Elimina</button>}</div></div></article>)}</section>
  </>;
}
