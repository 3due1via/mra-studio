type Props = {
  status: string;
  version: string;
  isEditing: boolean;
  isDirty: boolean;
};

export function KnowledgeEditorFooter({
  status,
  version,
  isEditing,
  isDirty,
}: Props) {
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
      <div>
        <span>Salvataggio</span>
        <strong>{isDirty ? "Da salvare" : "Aggiornato"}</strong>
      </div>
      <div className="keyboard-hint">
        <span>Scorciatoia</span>
        <strong>Ctrl + S</strong>
      </div>
    </footer>
  );
}
