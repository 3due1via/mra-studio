import { useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { Button } from "../components/Button";
import { createEnvironment, createObject, listEnvironments, listObjects, listProjects } from "../services/projectsApi";
import type { EnvironmentInput, MraObjectInput } from "../types/projects";

const emptyEnvironment: EnvironmentInput = { name: "", environment_type: "Stanza", area_m2: "", height_m: "", width_m: "", length_m: "", notes: "" };
const emptyObject: MraObjectInput = { category: "Arredo", name: "", brand: "", model: "", serial_number: "", description: "", status: "active", metadata_json: {} };

const formatDate = (value?: string) => value ? new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "—";

export function ProjectDetailPage() {
  const { projectId = "" } = useParams();
  const client = useQueryClient();
  const [environmentForm, setEnvironmentForm] = useState<EnvironmentInput>(emptyEnvironment);
  const [objectForms, setObjectForms] = useState<Record<string, MraObjectInput>>({});
  const [addingEnvironment, setAddingEnvironment] = useState(false);
  const [addingObjectTo, setAddingObjectTo] = useState<string | null>(null);

  const projects = useQuery({ queryKey: ["projects"], queryFn: listProjects });
  const project = projects.data?.find((item) => item.id === projectId);
  const environments = useQuery({ queryKey: ["project-environments", projectId], queryFn: () => listEnvironments(projectId), enabled: Boolean(projectId) });
  const objectQueries = useQueries({ queries: (environments.data ?? []).map((environment) => ({ queryKey: ["environment-objects", environment.id], queryFn: () => listObjects(environment.id) })) });

  const addEnvironment = useMutation({ mutationFn: (values: EnvironmentInput) => createEnvironment(projectId, values), onSuccess: async () => { await client.invalidateQueries({ queryKey: ["project-environments", projectId] }); setEnvironmentForm(emptyEnvironment); setAddingEnvironment(false); } });
  const addObject = useMutation({ mutationFn: ({ environmentId, values }: { environmentId: string; values: MraObjectInput }) => createObject(environmentId, values), onSuccess: async (_, variables) => { await client.invalidateQueries({ queryKey: ["environment-objects", variables.environmentId] }); setAddingObjectTo(null); } });

  const dashboard = useMemo(() => {
    const environmentList = environments.data ?? [];
    const objects = objectQueries.flatMap((query) => query.data ?? []);
    const measured = environmentList.filter((item) => Boolean(item.area_m2)).length;
    const described = objects.filter((item) => Boolean(item.description || item.brand || item.model)).length;
    const readiness = Math.min(100, Math.round((environmentList.length ? 30 : 0) + Math.min(environmentList.length * 8, 30) + Math.min(objects.length * 5, 30) + (measured ? 5 : 0) + (described ? 5 : 0)));
    const activities = [
      ...objects.map((item) => ({ title: `Oggetto aggiunto: ${item.name}`, detail: item.category, date: item.created_at, icon: "◆" })),
      ...environmentList.map((item) => ({ title: `Ambiente creato: ${item.name}`, detail: item.environment_type, date: item.created_at, icon: "⌂" })),
    ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).slice(0, 6);
    return { environments: environmentList.length, objects: objects.length, measured, described, readiness, activities };
  }, [environments.data, objectQueries]);

  if (!project && !projects.isLoading) return <section className="empty-state error-box"><h2>Progetto non trovato</h2><Link to="/projects">Torna ai progetti</Link></section>;

  return (
    <>
      <header className="project-hq-hero">
        <div className="project-hq-copy"><Link to="/projects">← I miei progetti</Link><span className="project-hq-kicker">QUARTIER GENERALE DEL PROGETTO</span><h1>{project?.name ?? "Caricamento..."}</h1><p>{project?.description || "Organizza ambienti, oggetti e prossime attività in un unico spazio operativo."}</p><div className="project-hq-tags"><b>{project?.project_type ?? "Progetto"}</b><b>{project?.status ?? "draft"}</b><b>Aggiornato {formatDate(project?.updated_at)}</b></div></div>
        <div className="project-readiness-ring" style={{ "--progress": `${dashboard.readiness * 3.6}deg` } as CSSProperties}><div><strong>{dashboard.readiness}%</strong><span>Preparazione</span></div></div>
      </header>

      <section className="project-hq-actions"><Button onClick={() => setAddingEnvironment(true)}>+ Aggiungi ambiente</Button><Button className="button-secondary">Ottimizza disposizione</Button><Button className="button-secondary">Pronto al lavoro</Button><Button className="button-secondary">Apri assistente</Button></section>

      <section className="project-kpi-grid">
        <article><span className="kpi-icon blue">⌂</span><div><strong>{dashboard.environments}</strong><span>Ambienti</span><small>{dashboard.measured} con misure inserite</small></div></article>
        <article><span className="kpi-icon gold">◆</span><div><strong>{dashboard.objects}</strong><span>Oggetti registrati</span><small>{dashboard.described} già descritti</small></div></article>
        <article><span className="kpi-icon green">✓</span><div><strong>{dashboard.readiness}%</strong><span>Pronto al lavoro</span><small>{dashboard.readiness >= 80 ? "Progetto ben preparato" : "Continua a completare i dati"}</small></div></article>
        <article><span className="kpi-icon purple">AI</span><div><strong>{dashboard.activities.length}</strong><span>Attività recenti</span><small>Ultimi aggiornamenti registrati</small></div></article>
      </section>

      <section className="project-hq-grid">
        <div className="project-main-column">
          {addingEnvironment ? <form className="inline-entity-form" onSubmit={(e) => { e.preventDefault(); addEnvironment.mutate(environmentForm); }}><h2>Nuovo ambiente</h2><div className="project-form-grid"><label><span>Nome</span><input required value={environmentForm.name} onChange={(e) => setEnvironmentForm({ ...environmentForm, name: e.target.value })} placeholder="Es. Zona lavoro" /></label><label><span>Tipo</span><select value={environmentForm.environment_type} onChange={(e) => setEnvironmentForm({ ...environmentForm, environment_type: e.target.value })}>{["Stanza", "Garage", "Officina", "Cucina", "Bagno", "Giardino", "Magazzino", "Altro"].map((value) => <option key={value}>{value}</option>)}</select></label><label><span>Superficie m²</span><input value={environmentForm.area_m2} onChange={(e) => setEnvironmentForm({ ...environmentForm, area_m2: e.target.value })} /></label><label><span>Altezza m</span><input value={environmentForm.height_m} onChange={(e) => setEnvironmentForm({ ...environmentForm, height_m: e.target.value })} /></label></div><div className="project-form-actions"><Button className="button-secondary" type="button" onClick={() => setAddingEnvironment(false)}>Annulla</Button><Button>Aggiungi</Button></div></form> : null}

          <div className="section-heading"><div><span>MAPPA DEL PROGETTO</span><h2>Ambienti e oggetti</h2></div><small>{dashboard.environments} ambienti · {dashboard.objects} oggetti</small></div>

          {environments.data?.length === 0 ? <section className="empty-state"><h2>Il progetto è ancora vuoto</h2><p>Aggiungi il primo ambiente: una stanza, un garage, un'officina o un'area di lavoro.</p><Button onClick={() => setAddingEnvironment(true)}>Aggiungi ambiente</Button></section> : null}

          <section className="environment-list">
            {(environments.data ?? []).map((environment, index) => {
              const objects = objectQueries[index]?.data ?? [];
              const form = objectForms[environment.id] ?? emptyObject;
              return <article className="environment-card" key={environment.id}><header><div><span>{environment.environment_type}</span><h2>{environment.name}</h2><p>{environment.area_m2 ? `${environment.area_m2} m²` : "Misure non inserite"}</p></div><strong>{objects.length} oggetti</strong></header><div className="object-chip-grid">{objects.map((item) => <div className="object-chip" key={item.id}><span>{item.category}</span><strong>{item.name}</strong><small>{[item.brand, item.model].filter(Boolean).join(" · ") || "Dati da completare"}</small></div>)}<button className="add-object-card" type="button" onClick={() => setAddingObjectTo(environment.id)}>+<span>Aggiungi oggetto</span></button></div>{addingObjectTo === environment.id ? <form className="object-inline-form" onSubmit={(e) => { e.preventDefault(); addObject.mutate({ environmentId: environment.id, values: form }); }}><label><span>Nome oggetto</span><input required value={form.name} onChange={(e) => setObjectForms({ ...objectForms, [environment.id]: { ...form, name: e.target.value } })} placeholder="Es. Saldatrice MIG" /></label><label><span>Categoria</span><input value={form.category} onChange={(e) => setObjectForms({ ...objectForms, [environment.id]: { ...form, category: e.target.value } })} /></label><label><span>Marca</span><input value={form.brand} onChange={(e) => setObjectForms({ ...objectForms, [environment.id]: { ...form, brand: e.target.value } })} /></label><label><span>Modello</span><input value={form.model} onChange={(e) => setObjectForms({ ...objectForms, [environment.id]: { ...form, model: e.target.value } })} /></label><div><Button className="button-secondary" type="button" onClick={() => setAddingObjectTo(null)}>Annulla</Button><Button>Aggiungi</Button></div></form> : null}</article>;
            })}
          </section>
        </div>

        <aside className="project-side-column">
          <section className="project-side-card"><header><span>PROSSIMA MOSSA</span><h2>Cosa conviene fare ora</h2></header><div className="next-step-box"><b>{dashboard.environments === 0 ? "Crea il primo ambiente" : dashboard.objects === 0 ? "Inserisci gli oggetti principali" : dashboard.readiness < 80 ? "Completa misure e descrizioni" : "Avvia Pronto al lavoro"}</b><p>{dashboard.environments === 0 ? "Parti dalla struttura reale del progetto." : dashboard.objects === 0 ? "Registra macchine, arredi, impianti e attrezzature." : dashboard.readiness < 80 ? "Più dati inserisci, più precisi saranno i suggerimenti MRA." : "Il progetto è pronto per checklist, materiali e sicurezza."}</p></div><Button className="button-secondary">Continua con MRA</Button></section>

          <section className="project-side-card"><header><span>ATTIVITÀ RECENTI</span><h2>Ultimi aggiornamenti</h2></header><div className="project-activity-list">{dashboard.activities.length ? dashboard.activities.map((activity, index) => <div key={`${activity.title}-${index}`}><i>{activity.icon}</i><div><b>{activity.title}</b><span>{activity.detail} · {formatDate(activity.date)}</span></div></div>) : <p className="muted-copy">Le attività appariranno quando aggiungerai ambienti e oggetti.</p>}</div></section>

          <section className="project-side-card project-ai-card"><header><span>ASSISTENTE TECNICO</span><h2>Mister Repair</h2></header><p>“Ho analizzato il progetto. Posso aiutarti a completare i dati, preparare il lavoro e ottimizzare la disposizione.”</p><Button>Apri assistente</Button></section>
        </aside>
      </section>
    </>
  );
}
