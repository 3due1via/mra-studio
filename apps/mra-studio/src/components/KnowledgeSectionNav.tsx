import type { KnowledgeTab } from "./KnowledgeTabs";

type Props = {
  activeSection: KnowledgeTab;
  onChange: (section: KnowledgeTab) => void;
  hasSavedCard: boolean;
};

const sections: Array<{
  id: KnowledgeTab;
  icon: string;
  label: string;
  description: string;
  savedOnly?: boolean;
}> = [
  { id: "general", icon: "01", label: "Dati generali", description: "Identità, categoria e stato" },
  { id: "description", icon: "02", label: "Descrizione", description: "Sintesi e funzionamento" },
  { id: "diagnosis", icon: "03", label: "Diagnosi", description: "Sintomi, cause e controlli" },
  { id: "procedure", icon: "04", label: "Procedura", description: "Intervento e sicurezza" },
  { id: "relations", icon: "05", label: "Collegamenti", description: "Schede e contenuti correlati", savedOnly: true },
  { id: "revisions", icon: "06", label: "Storico modifiche", description: "Revisioni e ripristino", savedOnly: true },
];

export function KnowledgeSectionNav({ activeSection, onChange, hasSavedCard }: Props) {
  return (
    <aside className="knowledge-pro-navigation" aria-label="Struttura della scheda">
      <div className="knowledge-pro-navigation-heading">
        <span className="knowledge-pro-navigation-kicker">STRUTTURA</span>
        <strong>Scheda tecnica</strong>
      </div>

      <nav className="knowledge-pro-navigation-list">
        {sections.map((section) => {
          const disabled = Boolean(section.savedOnly && !hasSavedCard);
          const active = activeSection === section.id;

          return (
            <button
              key={section.id}
              type="button"
              className={`knowledge-pro-navigation-item${active ? " active" : ""}`}
              disabled={disabled}
              onClick={() => onChange(section.id)}
              title={disabled ? "Salva prima la scheda per usare questa sezione" : undefined}
            >
              <span className="knowledge-pro-navigation-index">{section.icon}</span>
              <span className="knowledge-pro-navigation-copy">
                <strong>{section.label}</strong>
                <small>{disabled ? "Disponibile dopo il primo salvataggio" : section.description}</small>
              </span>
              <span className="knowledge-pro-navigation-arrow">›</span>
            </button>
          );
        })}
      </nav>

      <div className="knowledge-pro-navigation-help">
        <strong>Scorciatoia</strong>
        <span>Premi Ctrl + S per salvare.</span>
      </div>
    </aside>
  );
}
