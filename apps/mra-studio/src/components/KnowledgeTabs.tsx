export type KnowledgeTab =
  | "general"
  | "description"
  | "diagnosis"
  | "procedure"
  | "relations"
  | "revisions";

type Props = {
  activeTab: KnowledgeTab;
  onChange: (tab: KnowledgeTab) => void;
};

const tabs: Array<{ id: KnowledgeTab; label: string; description: string }> = [
  { id: "general", label: "Generale", description: "Identità e stato" },
  { id: "description", label: "Descrizione", description: "Sintesi tecnica" },
  { id: "diagnosis", label: "Diagnosi", description: "Sintomi e cause" },
  { id: "procedure", label: "Procedura", description: "Intervento e sicurezza" },
  { id: "relations", label: "Relazioni", description: "Knowledge Graph" },
  { id: "revisions", label: "Revisioni", description: "Cronologia e ripristino" },
];

export function KnowledgeTabs({ activeTab, onChange }: Props) {
  return (
    <nav className="knowledge-tabs" aria-label="Sezioni Knowledge Editor">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={activeTab === tab.id ? "knowledge-tab active" : "knowledge-tab"}
          onClick={() => onChange(tab.id)}
          aria-current={activeTab === tab.id ? "page" : undefined}
        >
          <strong>{tab.label}</strong>
          <span>{tab.description}</span>
        </button>
      ))}
    </nav>
  );
}
