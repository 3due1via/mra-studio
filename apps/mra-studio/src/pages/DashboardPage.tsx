import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "../components/PageHeader";
import { listKnowledgeCards } from "../services/knowledgeApi";

export function DashboardPage() {
  const cards = useQuery({
    queryKey: ["knowledge-cards", "dashboard"],
    queryFn: () => listKnowledgeCards(),
  });

  const values = cards.data ?? [];
  const metrics = [
    ["Knowledge Card", String(values.length), "Salvate in PostgreSQL"],
    ["Bozze", String(values.filter((card) => card.status === "draft").length), "Contenuti in lavorazione"],
    ["In revisione", String(values.filter((card) => card.status === "review").length), "Da controllare"],
    ["Pubblicate", String(values.filter((card) => card.status === "published").length), "Contenuti disponibili"],
  ];

  return (
    <>
      <PageHeader
        eyebrow="MRA CONTROL CENTER"
        title="Dashboard"
        description="Controlla lo stato del Knowledge Engine e dei contenuti salvati."
      />
      <section className="metric-grid">
        {metrics.map(([label, value, note]) => (
          <article className="metric-card" key={label}>
            <span>{label}</span>
            <strong>{cards.isLoading ? "…" : value}</strong>
            <small>{note}</small>
          </article>
        ))}
      </section>
      <section className="panel">
        <p className="eyebrow">ATTIVITÀ</p>
        <h2>Knowledge Workspace attivo</h2>
        <p>Apri Knowledge dal menu, crea una scheda e verifica la persistenza reale nel database.</p>
      </section>
    </>
  );
}
