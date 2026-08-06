import type { KnowledgeCardInput } from "../types/knowledge";
import { KnowledgeQualityPanel } from "./KnowledgeQualityPanel";

const statusLabels: Record<KnowledgeCardInput["status"], string> = {
  draft: "Bozza",
  review: "In revisione",
  verified: "Verificata",
  approved: "Approvata",
  published: "Pubblicata",
  archived: "Archiviata",
  rejected: "Rifiutata",
};

type Props = {
  values: KnowledgeCardInput;
  isDirty: boolean;
  isEditing: boolean;
};

export function KnowledgeInspectorPanel({ values, isDirty, isEditing }: Props) {
  return (
    <aside className="knowledge-pro-inspector">
      <section className="knowledge-pro-summary-card">
        <div className="knowledge-pro-summary-heading">
          <div>
            <span className="knowledge-pro-navigation-kicker">PANORAMICA</span>
            <h3>{values.title.trim() || "Nuova scheda"}</h3>
          </div>
          <span className={`status-badge status-${values.status}`}>
            {statusLabels[values.status]}
          </span>
        </div>

        <dl className="knowledge-pro-summary-grid">
          <div>
            <dt>Codice</dt>
            <dd>{values.code.trim() || "Da assegnare"}</dd>
          </div>
          <div>
            <dt>Categoria</dt>
            <dd>{values.category.trim() || "Non indicata"}</dd>
          </div>
          <div>
            <dt>Versione</dt>
            <dd>{values.version || "1.0.0"}</dd>
          </div>
          <div>
            <dt>Tipo</dt>
            <dd>{isEditing ? "Scheda esistente" : "Nuova scheda"}</dd>
          </div>
        </dl>
      </section>

      <KnowledgeQualityPanel values={values} isDirty={isDirty} />

      <section className="knowledge-pro-assistant-card">
        <div className="knowledge-pro-assistant-icon">AI</div>
        <div>
          <span className="knowledge-pro-navigation-kicker">ASSISTENTE TECNICO</span>
          <h3>Controllo rapido</h3>
          <p>
            Completa titolo, categoria, diagnosi, procedura e sicurezza per rendere la scheda pronta alla revisione.
          </p>
        </div>
      </section>
    </aside>
  );
}
