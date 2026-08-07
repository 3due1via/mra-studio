import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Button } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { createProject, deleteProject, listProjects, updateProject } from "../services/projectsApi";
import type { Project, ProjectInput } from "../types/projects";

const emptyProject: ProjectInput = { name: "", project_type: "Casa", customer: "", description: "", status: "draft", progress: 0 };

export function ProjectsPage() {
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [form, setForm] = useState<ProjectInput>(emptyProject);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const save = useMutation({
    mutationFn: () => editingId ? updateProject(editingId, form) : createProject(form),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["projects"] });
      setForm(emptyProject); setEditingId(null); setShowForm(false);
    },
  });
  const remove = useMutation({ mutationFn: deleteProject, onSuccess: () => client.invalidateQueries({ queryKey: ["projects"] }) });

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (projects.data ?? []).filter((item) => !query || [item.name, item.project_type, item.customer].some((value) => value.toLowerCase().includes(query)));
  }, [projects.data, search]);

  const edit = (project: Project) => {
    setForm({ name: project.name, project_type: project.project_type, customer: project.customer, description: project.description, status: project.status, progress: project.progress });
    setEditingId(project.id); setShowForm(true);
  };

  return <>
    <PageHeader eyebrow="AREA DI LAVORO" title="I miei progetti" description="Organizza ambienti e oggetti tecnici in un unico workspace." actions={<Button onClick={() => { setForm(emptyProject); setEditingId(null); setShowForm(true); }}>+ Nuovo progetto</Button>} />
    {showForm ? <form className="project-create-card" onSubmit={(event) => { event.preventDefault(); save.mutate(); }}>
      <div className="project-form-heading"><div><span>{editingId ? "MODIFICA PROGETTO" : "NUOVO PROGETTO"}</span><h2>Dati principali</h2></div><button type="button" onClick={() => setShowForm(false)}>×</button></div>
      <div className="project-form-grid">
        <label><span>Nome</span><input required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
        <label><span>Tipo</span><input required minLength={2} value={form.project_type} onChange={(e) => setForm({ ...form, project_type: e.target.value })} /></label>
        <label><span>Cliente</span><input value={form.customer} onChange={(e) => setForm({ ...form, customer: e.target.value })} /></label>
        <label><span>Stato</span><select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as ProjectInput["status"] })}>{["draft", "active", "paused", "completed", "archived"].map((value) => <option key={value}>{value}</option>)}</select></label>
        <label><span>Avanzamento</span><input type="number" min={0} max={100} value={form.progress} onChange={(e) => setForm({ ...form, progress: Number(e.target.value) })} /></label>
        <label className="wide"><span>Descrizione</span><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
      </div>
      {save.isError ? <div className="notice error">{String(save.error)}</div> : null}
      <div className="project-form-actions"><Button className="button-secondary" type="button" onClick={() => setShowForm(false)}>Annulla</Button><Button disabled={save.isPending}>{save.isPending ? "Salvataggio..." : "Salva"}</Button></div>
    </form> : null}
    <section className="projects-toolbar panel"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Cerca per nome, tipo o cliente..." /></section>
    {projects.isLoading ? <section className="empty-state"><h2>Caricamento progetti...</h2></section> : null}
    {projects.isError ? <section className="empty-state error-box"><h2>Errore API</h2><p>{String(projects.error)}</p></section> : null}
    {remove.isError ? <section className="empty-state error-box"><h2>Eliminazione non riuscita</h2><p>{String(remove.error)}</p></section> : null}
    {!projects.isLoading && !projects.isError && visible.length === 0 ? <section className="empty-state"><h2>Nessun progetto</h2><p>Crea il primo progetto per iniziare.</p></section> : null}
    <section className="project-card-grid">{visible.map((project) => <article className="project-card" key={project.id}>
      <div className="project-card-cover"><span>{project.project_type}</span><b>{project.status}</b></div>
      <div className="project-card-content"><h2>{project.name}</h2><p>{project.description || "Nessuna descrizione."}</p><div className="project-meta"><span>{project.customer || "Progetto personale"}</span><span>{project.progress}%</span></div><div className="project-progress"><i style={{ width: `${project.progress}%` }} /></div>
        <div className="project-card-actions"><Link className="button" to={`/projects/${project.id}`}>Apri</Link><button type="button" onClick={() => edit(project)}>Modifica</button><button type="button" onClick={() => { if (window.confirm(`Eliminare ${project.name} e tutti i contenuti?`)) remove.mutate(project.id); }}>Elimina</button></div>
      </div></article>)}</section>
  </>;
}
