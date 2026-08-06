import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { createProject, deleteProject, listProjects } from "../services/projectsApi";
import type { ProjectInput } from "../types/projects";

const emptyProject: ProjectInput = {
  name: "",
  project_type: "Casa",
  customer: "",
  description: "",
  status: "draft",
  progress: 0,
};

export function ProjectsPage() {
  const client = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ProjectInput>(emptyProject);
  const [search, setSearch] = useState("");

  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const create = useMutation({
    mutationFn: createProject,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: ["projects"] });
      setForm(emptyProject);
      setShowForm(false);
    },
  });
  const remove = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => client.invalidateQueries({ queryKey: ["projects"] }),
  });

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return (projects.data ?? []).filter((item) =>
      !query || [item.name, item.project_type, item.customer].some((value) => value.toLowerCase().includes(query)),
    );
  }, [projects.data, search]);

  return (
    <>
      <PageHeader
        eyebrow="AREA DI LAVORO"
        title="I miei progetti"
        description="Organizza case, officine, macchine, ambienti e lavori in un unico posto."
        actions={<Button onClick={() => setShowForm((value) => !value)}>+ Nuovo progetto</Button>}
      />

      <section className="projects-summary-grid">
        <article><strong>{projects.data?.length ?? 0}</strong><span>Progetti totali</span></article>
        <article><strong>{projects.data?.filter((p) => p.status === "active").length ?? 0}</strong><span>In lavorazione</span></article>
        <article><strong>{projects.data?.filter((p) => p.status === "completed").length ?? 0}</strong><span>Completati</span></article>
        <article><strong>{Math.round((projects.data ?? []).reduce((sum, p) => sum + p.progress, 0) / Math.max(projects.data?.length ?? 0, 1))}%</strong><span>Avanzamento medio</span></article>
      </section>

      {showForm ? (
        <form className="project-create-card" onSubmit={(event) => { event.preventDefault(); create.mutate(form); }}>
          <div className="project-form-heading"><div><span>NUOVO PROGETTO</span><h2>Da cosa vuoi partire?</h2></div><button type="button" onClick={() => setShowForm(false)}>×</button></div>
          <div className="project-type-grid">
            {["Casa", "Stanza", "Officina", "Garage", "Bar", "Giardino", "Macchina", "Altro"].map((type) => (
              <button key={type} type="button" className={form.project_type === type ? "selected" : ""} onClick={() => setForm({ ...form, project_type: type })}>{type}</button>
            ))}
          </div>
          <div className="project-form-grid">
            <label><span>Nome del progetto</span><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Es. Officina moto nel garage" /></label>
            <label><span>Cliente o proprietario</span><input value={form.customer} onChange={(e) => setForm({ ...form, customer: e.target.value })} placeholder="Facoltativo" /></label>
            <label className="wide"><span>Descrizione</span><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Descrivi in poche parole cosa vuoi realizzare..." /></label>
          </div>
          {create.isError ? <div className="notice error">{String(create.error)}</div> : null}
          <div className="project-form-actions"><Button className="button-secondary" type="button" onClick={() => setShowForm(false)}>Annulla</Button><Button disabled={create.isPending}>{create.isPending ? "Creazione..." : "Crea progetto"}</Button></div>
        </form>
      ) : null}

      <section className="projects-toolbar panel"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Cerca per nome, tipo o cliente..." /></section>

      {projects.isLoading ? <section className="empty-state"><h2>Caricamento progetti...</h2></section> : null}
      {projects.isError ? <section className="empty-state error-box"><h2>Errore API</h2><p>{String(projects.error)}</p></section> : null}
      {!projects.isLoading && visible.length === 0 ? <section className="empty-state"><div className="empty-project-icon">⌂</div><h2>Nessun progetto</h2><p>Crea il primo progetto e suddividilo in ambienti e oggetti.</p><Button onClick={() => setShowForm(true)}>Crea il primo progetto</Button></section> : null}

      <section className="project-card-grid">
        {visible.map((project) => (
          <article className="project-card" key={project.id}>
            <div className="project-card-cover"><span>{project.project_type}</span><b>{project.status === "active" ? "In lavorazione" : project.status === "completed" ? "Completato" : "Bozza"}</b></div>
            <div className="project-card-content">
              <h2>{project.name}</h2><p>{project.description || "Nessuna descrizione inserita."}</p>
              <div className="project-meta"><span>{project.customer || "Progetto personale"}</span><span>{project.progress}%</span></div>
              <div className="project-progress"><i style={{ width: `${project.progress}%` }} /></div>
              <div className="project-card-actions"><a className="button" href={`/projects/${project.id}`}>Apri progetto</a><button type="button" onClick={() => { if (window.confirm(`Eliminare ${project.name}?`)) remove.mutate(project.id); }}>Elimina</button></div>
            </div>
          </article>
        ))}
      </section>
    </>
  );
}
