import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { listKnowledgeCards } from "../services/knowledgeApi";
import type { KnowledgeCard } from "../types/knowledge";
import { interventionSummary } from "../services/interventionsApi";

const demoCards = [
  { title: "Motorino tergicristallo", code: "MEC-TRG-001", status: "In revisione", progress: 75, image: "⚙" },
  { title: "Compressore A/C", code: "IMP-AC-023", status: "Bozza", progress: 40, image: "◉" },
  { title: "Sensore ABS anteriore", code: "ELE-ABS-009", status: "In revisione", progress: 60, image: "⌁" },
  { title: "Centralina motore BOSCH", code: "ELE-ECU-045", status: "Pubblicata", progress: 100, image: "▦" },
];

function statusLabel(status: KnowledgeCard["status"]) {
  const labels: Record<string, string> = {
    draft: "Bozza", review: "In revisione", verified: "Verificata", approved: "Approvata",
    published: "Pubblicata", archived: "Archiviata", rejected: "Rifiutata",
  };
  return labels[status] ?? status;
}

export function DashboardPage() {
  const cards = useQuery({ queryKey: ["knowledge-cards", "dashboard"], queryFn: () => listKnowledgeCards() });
  const interventions = useQuery({ queryKey: ["interventions-summary"], queryFn: interventionSummary });
  const values = cards.data ?? [];
  const visibleCards = useMemo(() => values.slice(0, 4), [values]);

  const stats = [
    { icon: "▤", label: "TOTALE SCHEDE", value: values.length || 12458, note: "+124 questa settimana", tone: "blue" },
    { icon: "▧", label: "MEDIA COLLEGATI", value: 3921, note: "+68 questa settimana", tone: "purple" },
    { icon: "◇", label: "QUALITÀ MEDIA", value: "94%", note: "+5% rispetto a ieri", tone: "green" },
    { icon: "⌁", label: "REVISIONI IN CORSO", value: values.filter((card) => card.status === "review").length || 23, note: "8 in scadenza", tone: "orange" },
    { icon: "♙", label: "UTENTI ATTIVI", value: 14, note: "● Online ora", tone: "cyan" },
  ];

  return (
    <div className="mra-dashboard">
      <section className="dashboard-stats" aria-label="Riepilogo interventi">
        {interventions.isLoading ? <p>Caricamento interventi…</p> : interventions.isError ? <p role="alert">Riepilogo interventi non disponibile.</p> : [
          ["Aperti", interventions.data?.open ?? 0], ["In corso", interventions.data?.in_progress ?? 0], ["Scaduti", interventions.data?.overdue ?? 0], ["Completati (30 giorni)", interventions.data?.recently_completed ?? 0],
        ].map(([label,value]) => <Link to="/interventions" className="dash-stat blue" key={label}><div><span>{label}</span><strong>{value}</strong></div></Link>)}
      </section>
      <section className="mra-hero">
        <div className="hero-copy">
          <p>👨‍🔧 MR. ACADEMY</p>
          <h1>Ciao Francesco.</h1>
          <h2>Cosa costruiamo o ripariamo oggi?</h2>
          <div className="hero-pills">
            <span>🎤 Parla con me</span>
            <span>📷 Mostrami un problema</span>
            <span>📹 Avvia videoconsulenza</span>
            <span>🚨 MRA SOS</span>
          </div>
        </div>
        <div className="volume-shield"><small>OGGI</small><strong>3</strong></div>
        <Link className="new-card-hero" to="/knowledge">📚 Apri Knowledge <span>⌄</span></Link>
      </section>

      <section className="dashboard-stats">
        {stats.map((stat) => (
          <article className={`dash-stat ${stat.tone}`} key={stat.label}>
            <div className="stat-icon">{stat.icon}</div>
            <div><span>{stat.label}</span><strong>{cards.isLoading && stat.label === "TOTALE SCHEDE" ? "…" : stat.value}</strong><small>{stat.note}</small></div>
            <div className="mini-chart"><i /><i /><i /><i /><i /><i /><i /></div>
          </article>
        ))}
      </section>

      <section className="dashboard-split">
        <div className="dashboard-stack">
          <section className="dash-panel featured-panel">
            <header><strong>☷ IN EVIDENZA</strong><Link to="/knowledge">Vedi tutte →</Link></header>
            <div className="featured-grid">
              {(visibleCards.length ? visibleCards.map((card) => ({
                title: card.title, code: card.code, status: statusLabel(card.status), progress: card.status === "published" ? 100 : card.status === "review" ? 75 : 40, image: "⚙",
              })) : demoCards).map((card) => (
                <article className="technical-card" key={card.code}>
                  <div className="tech-thumb"><span>{card.image}</span><b>⋮</b></div>
                  <h3>{card.title}</h3><small>{card.code}</small>
                  <div className="card-status-row"><span className={`status-pill ${card.status.toLowerCase().replaceAll(" ", "-")}`}>{card.status}</span><b>{card.progress}%</b></div>
                  <div className="progress-track"><i style={{ width: `${card.progress}%` }} /></div>
                </article>
              ))}
            </div>
          </section>

          <section className="dash-panel media-panel">
            <header><strong>☷ ULTIMI MEDIA AGGIUNTI</strong><button type="button">Vedi tutti →</button></header>
            <div className="media-grid">
              {[
                ["▶", "Video smontaggio completo", "Motorino tergicristallo", "03:42"],
                ["▧", "Galleria immagini", "Compressore A/C", "12 foto"],
                ["PDF", "Schema elettrico", "Centralina motore", "PDF"],
                ["PDF", "Coppie di serraggio", "Sospensioni anteriori", "PDF"],
                ["▶", "Diagnosi centralina", "BOSCH EDC17", "05:18"],
              ].map(([symbol, title, subtitle, badge]) => (
                <article key={title}><div className="media-thumb"><strong>{symbol}</strong><b>{badge}</b></div><h4>{title}</h4><small>{subtitle}</small></article>
              ))}
            </div>
          </section>
        </div>

        <section className="dash-panel graph-panel">
          <header><strong>MAPPA COLLEGAMENTI</strong><button type="button">Apri mappa →</button></header>
          <div className="graph-canvas">
            <span className="graph-line line-1" /><span className="graph-line line-2" /><span className="graph-line line-3" /><span className="graph-line line-4" />
            <div className="graph-center"><span>⚙</span><strong>Motorino<br/>tergicristallo</strong></div>
            <div className="graph-node node-a"><b>▧</b><span>Schemi elettrici</span></div>
            <div className="graph-node node-b"><b>♙</b><span>Procedura smontaggio</span></div>
            <div className="graph-node node-c"><b>▣</b><span>Ricambi compatibili</span></div>
            <div className="graph-node node-d"><b>⌕</b><span>Coppie di serraggio</span></div>
            <div className="graph-node node-e"><b>!</b><span>Guasti comuni</span></div>
            <div className="graph-node node-f"><b>▶</b><span>Video tutorial</span></div>
            <div className="graph-node node-g"><b>✓</b><span>Test e verifiche</span></div>
          </div>
        </section>
      </section>

      <section className="dash-panel quick-panel">
        <header><strong>✣ AZIONI RAPIDE</strong></header>
        <div className="quick-grid">
          {[
            ["＋", "Nuova scheda", "Crea una nuova scheda tecnica", "/knowledge", "blue"],
            ["⇧", "Importa media", "Carica immagini, video o PDF", "/media", "cyan"],
            ["✦", "Assistente tecnico", "Chiedi aiuto all’AI", "/assistant", "purple"],
            ["↶", "Nuova revisione", "Avvia una procedura di revisione", "/revisions", "orange"],
            ["⌘", "Mappa collegamenti", "Esplora tutte le connessioni", "/graph", "blue"],
            ["⌕", "Ricerca avanzata", "Cerca in tutti i contenuti", "/knowledge", "gold"],
          ].map(([icon, label, note, path, tone]) => (
            <Link to={path} className={`quick-card ${tone}`} key={label}><b>{icon}</b><div><strong>{label}</strong><small>{note}</small></div></Link>
          ))}
        </div>
      </section>

      <nav className="category-strip" aria-label="Categorie principali">
        <strong>CATEGORIE PRINCIPALI</strong>
        {[
          ["⚒", "Meccanica"], ["▦", "Elettronica"], ["▰", "Carrozzeria"], ["♧", "Impianti"], ["⌁", "Diagnosi"], ["❄", "Climatizzazione"], ["⌇", "Sospensioni"],
        ].map(([icon, label]) => <button type="button" key={label}><b>{icon}</b>{label}</button>)}
      </nav>
    </div>
  );
}
