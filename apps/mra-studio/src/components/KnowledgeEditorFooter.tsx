type Props = {
  status: string;
  version: string;
  isEditing: boolean;
};

export function KnowledgeEditorFooter({ status, version, isEditing }: Props) {
  return (
    <footer className="knowledge-editor-footer">
      <div>
        <span>Modalità</span>
        <strong>{isEditing ? "Modifica" : "Creazione"}</strong>
      </div>
      <div>
        <span>Stato</span>
        <strong>{status || "draft"}</strong>
      </div>
      <div>
        <span>Versione</span>
        <strong>{version || "1.0.0"}</strong>
      </div>
    </footer>
  );
}
