import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Button } from "../components/Button";
import { createEnvironment, deleteEnvironment, getProject, listEnvironments, updateEnvironment } from "../services/projectsApi";
import type { Environment, EnvironmentInput } from "../types/projects";

const emptyEnvironment: EnvironmentInput = { name: "", environment_type: "Stanza", area_m2: "", height_m: "", width_m: "", length_m: "", notes: "" };

export function ProjectDetailPage() {
  const { projectId = "" } = useParams();
  const client = useQueryClient();
  const [form, setForm] = useState<EnvironmentInput>(emptyEnvironment);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const project = useQuery({ queryKey: ["project", projectId], queryFn: () => getProject(projectId), enabled: Boolean(projectId) });
  const environments = useQuery({ queryKey: ["project-environments", projectId], queryFn: () => listEnvironments(projectId), enabled: Boolean(projectId) });
  const save = useMutation({
    mutationFn: () => editingId ? updateEnvironment(editingId, form) : createEnvironment(projectId, form),
    onSuccess: async () => { await client.invalidateQueries({ queryKey: ["project-environments", projectId] }); setForm(emptyEnvironment); setEditingId(null); setShowForm(false); },
  });
  const remove = useMutation({ mutationFn: deleteEnvironment, onSuccess: () => client.invalidateQueries({ queryKey: ["project-environments", projectId] }) });

  const edit = (environment: Environment) => {
    setForm({ name: environment.name, environment_type: environment.environment_type, area_m2: environment.area_m2, height_m: environment.height_m, width_m: environment.width_m, length_m: environment.length_m, notes: environment.notes });
    setEditingId(environment.id); setShowForm(true);
  };

  if (project.isLoading) return <section className="empty-state"><h2>Caricamento progetto...</h2></section>;
  if (project.isError) return <section className="empty-state error-box"><h2>Progetto non disponibile</h2><p>{String(project.error)}</p><Link to="/projects">Torna ai progetti</Link></section>;

  return <>
    <header className="project-hq-hero"><div className="project-hq-copy"><Link to="/projects">← I miei progetti</Link><span className="project-hq-kicker">WORKSPACE PROGETTO</span><h1>{project.data?.name}</h1><p>{project.data?.description || "Nessuna descrizione inserita."}</p><div className="project-hq-tags"><b>{project.data?.project_type}</b><b>{project.data?.status}</b><b>{project.data?.customer || "Progetto personale"}</b></div></div><div className="project-readiness-ring"><div><strong>{project.data?.progress ?? 0}%</strong><span>Avanzamento</span></div></div></header>
    <section className="project-hq-actions"><Button onClick={() => { setForm(emptyEnvironment); setEditingId(null); setShowForm(true); }}>+ Aggiungi ambiente</Button></section>
    {showForm ? <form className="inline-entity-form" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}><h2>{editingId ? "Modifica ambiente" : "Nuovo ambiente"}</h2><div className="project-form-grid">
      <label><span>Nome</span><input required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
      <label><span>Tipo</span><input required minLength={2} value={form.environment_type} onChange={(e) => setForm({ ...form, environment_type: e.target.value })} /></label>
      <label><span>Superficie m²</span><input type="number" min="0.01" step="0.01" value={form.area_m2} onChange={(e) => setForm({ ...form, area_m2: e.target.value })} /></label>
      <label><span>Altezza m</span><input type="number" min="0.01" step="0.01" value={form.height_m} onChange={(e) => setForm({ ...form, height_m: e.target.value })} /></label>
      <label><span>Larghezza m</span><input type="number" min="0.01" step="0.01" value={form.width_m} onChange={(e) => setForm({ ...form, width_m: e.target.value })} /></label>
      <label><span>Lunghezza m</span><input type="number" min="0.01" step="0.01" value={form.length_m} onChange={(e) => setForm({ ...form, length_m: e.target.value })} /></label>
      <label className="wide"><span>Note</span><textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></label>
    </div>{save.isError ? <div className="notice error">{String(save.error)}</div> : null}<div className="project-form-actions"><Button className="button-secondary" type="button" onClick={() => setShowForm(false)}>Annulla</Button><Button disabled={save.isPending}>Salva</Button></div></form> : null}
    <div className="section-heading"><div><span>STRUTTURA</span><h2>Ambienti</h2></div><small>{environments.data?.length ?? 0} ambienti</small></div>
    {environments.isLoading ? <section className="empty-state"><h2>Caricamento ambienti...</h2></section> : null}
    {environments.isError ? <section className="empty-state error-box"><h2>Errore ambienti</h2><p>{String(environments.error)}</p></section> : null}
    {remove.isError ? <section className="empty-state error-box"><h2>Eliminazione non riuscita</h2><p>{String(remove.error)}</p></section> : null}
    {!environments.isLoading && !environments.isError && environments.data?.length === 0 ? <section className="empty-state"><h2>Il progetto è ancora vuoto</h2><p>Aggiungi il primo ambiente.</p></section> : null}
    <section className="environment-list">{(environments.data ?? []).map((environment) => <article className="environment-card" key={environment.id}><header><div><span>{environment.environment_type}</span><h2>{environment.name}</h2><p>{environment.area_m2 ? `${environment.area_m2} m²` : "Misure non inserite"}</p></div></header><div className="project-card-actions"><Link className="button" to={`/environments/${environment.id}`}>Apri ambiente</Link><button type="button" onClick={() => edit(environment)}>Modifica</button><button type="button" onClick={() => { if (window.confirm(`Eliminare ${environment.name} e tutti gli oggetti?`)) remove.mutate(environment.id); }}>Elimina</button></div></article>)}</section>
  </>;
}
